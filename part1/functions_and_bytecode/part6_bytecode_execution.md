# Part 6 — Bytecode Execution (ceval.c)

## 6.1 The Main Interpreter Loop

The heart of CPython is a giant `switch` statement in `Python/ceval.c` (or `Python/generated_cases.c.h` in 3.12+):

```c
// Python/ceval.c (massively simplified):
PyObject *
_PyEval_EvalFrameDefault(PyThreadState *tstate, _PyInterpreterFrame *frame, int throwflag)
{
    // Setup: get instruction pointer, stack pointer
    _Py_CODEUNIT *next_instr = frame->prev_instr + 1;
    PyObject **stack_pointer = frame->stacktop;
    
    // THE MAIN LOOP:
    for (;;) {
        // Fetch instruction:
        uint8_t opcode = _Py_OPCODE(*next_instr);
        uint8_t oparg = _Py_OPARG(*next_instr);
        next_instr++;
        
        // Dispatch:
        switch (opcode) {
        
        case LOAD_FAST: {
            PyObject *value = GETLOCAL(oparg);
            if (value == NULL) goto unbound_local_error;
            Py_INCREF(value);
            PUSH(value);
            break;
        }
        
        case STORE_FAST: {
            PyObject *value = POP();
            PyObject *old = GETLOCAL(oparg);
            SETLOCAL(oparg, value);  // Sets + Py_XDECREF(old)
            break;
        }
        
        case LOAD_CONST: {
            PyObject *value = GETITEM(co_consts, oparg);
            Py_INCREF(value);
            PUSH(value);
            break;
        }
        
        case BINARY_OP: {
            PyObject *right = POP();
            PyObject *left = TOP();  // Peek (will be replaced)
            PyObject *result = binary_ops[oparg](left, right);
            Py_DECREF(left);
            Py_DECREF(right);
            SET_TOP(result);
            if (result == NULL) goto error;
            break;
        }
        
        case RETURN_VALUE: {
            PyObject *retval = POP();
            // ... frame cleanup ...
            return retval;
        }
        
        case CALL: {
            // ... complex call protocol (see Part 8) ...
            break;
        }
        
        // ... 150+ more opcodes ...
        }
    }
}
```

---

## 6.2 Dispatch Mechanism

### Threaded Code (computed goto):

CPython uses GCC's computed goto extension for faster dispatch:

```c
// Instead of switch(opcode):
static void *opcode_targets[] = {
    [LOAD_FAST] = &&TARGET_LOAD_FAST,
    [STORE_FAST] = &&TARGET_STORE_FAST,
    // ... one label per opcode
};

// Dispatch:
goto *opcode_targets[opcode];

TARGET_LOAD_FAST: {
    // ... implementation ...
    DISPATCH();  // goto *opcode_targets[next_opcode]
}
```

Computed goto is ~15-20% faster than a switch statement because:
- No bounds checking on the switch variable
- CPU branch predictor works better with indirect jumps
- Each opcode handler ends with its own dispatch (better instruction cache)

---

## 6.3 The Stack Operations (Macros)

```c
#define STACK_LEVEL()    (stack_pointer - frame->localsplus - frame->stacktop_offset)
#define PUSH(v)          (*stack_pointer++ = (v))
#define POP()            (*--stack_pointer)
#define TOP()            (stack_pointer[-1])
#define SET_TOP(v)       (stack_pointer[-1] = (v))
#define PEEK(n)          (stack_pointer[-(n)])
#define GETLOCAL(i)      (frame->localsplus[i])
#define SETLOCAL(i, val) do { \
    PyObject *_old = frame->localsplus[i]; \
    frame->localsplus[i] = (val); \
    Py_XDECREF(_old); \
} while(0)
```

---

## 6.4 Execution Trace Example

```python
def add(x, y):
    z = x + y
    return z

result = add(3, 4)
```

Inside `add(3, 4)` frame execution:
```
IP   Opcode         Stack            Locals [x, y, z]
─────────────────────────────────────────────────────────────
0    RESUME 0       []               [3, 4, NULL]
2    LOAD_FAST 0    [3]              [3, 4, NULL]    ← push x
4    LOAD_FAST 1    [3, 4]           [3, 4, NULL]    ← push y
6    BINARY_OP +    [7]              [3, 4, NULL]    ← 3+4=7
10   STORE_FAST 2   []               [3, 4, 7]      ← z = 7
12   LOAD_FAST 2    [7]              [3, 4, 7]      ← push z
14   RETURN_VALUE   → returns 7      (frame destroyed)
```

---

## 6.5 Error Handling in the Eval Loop

```c
case LOAD_FAST: {
    PyObject *value = GETLOCAL(oparg);
    if (value == NULL) {
        // Variable referenced before assignment!
        format_exc_check_arg(tstate, PyExc_UnboundLocalError,
            "local variable '%s' referenced before assignment",
            co_varnames[oparg]);
        goto error;
    }
    // ...
}

// 'error' label: exception handling
error:
    // 1. Check if there's a matching except handler (exception table)
    // 2. If yes: jump to handler, push exception onto stack
    // 3. If no: unwind frame, propagate to caller
```

---

## 6.6 The GIL Check

Every N instructions (or on backward jumps), the eval loop checks:
```c
// Periodic check (simplified):
if (--tstate->eval_breaker) {
    // Check for:
    // - Signal handlers (Ctrl+C)
    // - GIL release request (another thread waiting)
    // - Async exceptions
    // - GC collection needed
    if (should_release_gil()) {
        release_GIL();
        // Other thread runs here
        acquire_GIL();
    }
}
```

This is why Python threads can't truly run in parallel — the GIL is released/acquired periodically during bytecode execution.

---

## 6.7 Interview Questions — Part 6

**Q1**: What is the main interpreter loop in CPython?
**A**: A giant switch (or computed goto) in `ceval.c` that fetches opcodes one by one, dispatches to handlers, and repeats. This is the "heartbeat" of Python execution.

**Q2**: Why does CPython use computed goto instead of switch?
**A**: ~15-20% faster. Each opcode handler ends with its own dispatch jump. Better branch prediction, no bounds check, better instruction cache utilization.

**Q3**: What are PUSH/POP in the eval loop?
**A**: Macros that move the stack pointer: `PUSH(*sp++ = v)`, `POP(*--sp)`. The operand stack is a C array of PyObject* within the frame's localsplus.

**Q4**: Where does the GIL get released during execution?
**A**: Periodically during the eval loop (every N instructions or on backward jumps). The interpreter checks `eval_breaker` and releases the GIL if another thread is waiting.

**Q5**: How are exceptions handled in the eval loop?
**A**: On error, the interpreter consults the exception table (co_exceptiontable) to find a matching handler. If found: jump to it. If not: unwind the frame and propagate to the caller.
