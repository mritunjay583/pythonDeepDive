# Part 5 — Frame Suspension: The Core Mechanism

## 5.1 Why Generators Can Pause

Normal functions can't pause because their frame lives on the **C call stack** (or CPython's per-thread data stack). When the C function `_PyEval_EvalFrameDefault` returns, the frame is gone.

Generators solve this by keeping the frame on the **heap** inside the PyGenObject. The eval loop can exit (return to caller) while the frame persists, ready to be re-entered later.

```
NORMAL FUNCTION CALL:
┌─────────────────────────────────┐
│ C Stack / Data Stack            │
│                                 │
│ ┌─────────────────────────────┐ │
│ │ Frame for func()            │ │ ← Created when called
│ │ prev_instr, locals, stack   │ │
│ └─────────────────────────────┘ │
│                                 │ ← DESTROYED when func returns!
└─────────────────────────────────┘

GENERATOR:
┌─────────────────────────────────┐
│ Heap                            │
│                                 │
│ PyGenObject                     │
│ ├── gi_frame ──→ ┌───────────┐ │
│ │                │ Frame     │ │ ← Lives on HEAP
│ │                │ prev_instr│ │ ← Instruction pointer preserved
│ │                │ locals    │ │ ← Local variables preserved
│ │                │ stack     │ │ ← Operand stack preserved
│ │                └───────────┘ │
│ └── gi_code, gi_name, ...      │
└─────────────────────────────────┘
  Frame persists between yields!
  Re-entered on next()/send()
```

---

## 5.2 What Gets Preserved on Yield

When YIELD_VALUE executes:

```c
// Python/ceval.c (simplified):
case YIELD_VALUE: {
    PyObject *retval = POP();           // 1. Pop yielded value from stack
    
    // 2. Save frame state:
    frame->prev_instr = next_instr - 1; // Save EXACT position (the yield instruction)
    frame->stacktop = (int)(stack_pointer - frame->localsplus);  // Stack height
    
    // 3. Detach frame from active execution:
    gen->gi_frame = frame;              // Store frame in generator
    tstate->current_frame = frame->previous;  // Return to caller's frame
    
    // 4. Return yielded value to caller (whoever called next()):
    return retval;
}
```

**What's preserved in the frame:**
| Field | What it stores | Purpose |
|-------|---------------|---------|
| `prev_instr` | Pointer to the YIELD_VALUE instruction | Resume point |
| `localsplus[0..n-1]` | Local variable values | Function state |
| `localsplus[n..m]` | Cell/free variable cells | Closure state |
| `localsplus[m..top]` | Operand stack | Expression state |
| `stacktop` | Stack pointer position | How deep the stack was |

---

## 5.3 What Happens on Resume (next/send)

```c
// Objects/genobject.c (simplified):
static PyObject *
gen_send_ex2(PyGenObject *gen, PyObject *arg, int exc, int closing)
{
    _PyInterpreterFrame *frame = gen->gi_frame;
    
    // 1. Verify generator is in valid state:
    if (frame == NULL) {
        // Already closed → StopIteration
        return NULL;
    }
    if (gen->gi_running) {
        // Already running (reentrant call!) → ValueError
        PyErr_SetString(PyExc_ValueError, "generator already executing");
        return NULL;
    }
    
    // 2. Push the sent value onto the generator's operand stack:
    //    (This becomes the result of the yield expression)
    _PyFrame_StackPush(frame, Py_NewRef(arg));
    
    // 3. Mark as running:
    gen->gi_running = 1;
    gen->gi_frame = NULL;  // Frame is "in use" now
    
    // 4. Make this frame the active one:
    frame->previous = tstate->current_frame;
    tstate->current_frame = frame;
    
    // 5. Resume execution (re-enter the eval loop!):
    PyObject *result = _PyEval_EvalFrame(tstate, frame, exc);
    
    // 6. After yield or return:
    gen->gi_running = 0;
    
    if (result == NULL) {
        // Generator returned or raised exception → closed
        gen->gi_frame = NULL;  // Release frame
        gen->gi_closed = 1;
        // Frame memory will be freed
    } else {
        // Generator yielded → frame saved back
        // (YIELD_VALUE already did gen->gi_frame = frame)
    }
    
    return result;
}
```

---

## 5.4 Memory Diagram: A Generator at Yield Point

```python
def counter(start):
    n = start
    while True:
        received = yield n   # Suspended HERE
        if received:
            n = received
        else:
            n += 1

c = counter(10)
next(c)      # Returns 10, suspended at yield
c.send(50)   # Returns 50, suspended at yield again
```

After `c.send(50)`, with c suspended:

```
'c' → PyGenObject (heap, ~112 bytes):
       ├── ob_refcnt: 1
       ├── ob_type: → PyGen_Type
       ├── gi_frame → ┌──────────────────────────────────────────────┐
       │               │ _PyInterpreterFrame                          │
       │               │                                              │
       │               │ f_code → <code object 'counter'>             │
       │               │ prev_instr → YIELD_VALUE instruction         │
       │               │                                              │
       │               │ localsplus:                                   │
       │               │   [0] start = 10     (parameter, unchanged)  │
       │               │   [1] n = 50         (updated by send!)      │
       │               │   [2] received = 50  (from last send)        │
       │               │                                              │
       │               │ operand stack: [50]  (yield expression value)│
       │               │ stacktop: 1                                  │
       │               └──────────────────────────────────────────────┘
       ├── gi_code: → <code object 'counter'>
       ├── gi_name: "counter"
       ├── gi_qualname: "counter"
       ├── gi_closed: False
       ├── gi_running: False
       └── gi_exc_state: NULL
```

---

## 5.5 The Heap vs Stack Distinction

```
WHY normal frames are on stack (fast but temporary):
  - Function call: push frame, execute, pop frame
  - Frame exists only during one continuous execution
  - Stack allocation: O(1), just move pointer
  - No GC involvement needed
  
WHY generator frames must be on heap (persistent):
  - Frame must survive across multiple eval loop entries/exits
  - Must persist while generator object is alive (possibly forever!)
  - Must be independently addressable (gen->gi_frame pointer)
  - Must be tracked by GC (generators can form reference cycles)
  - Trade-off: malloc/free overhead, but necessary for suspension
```

Python 3.11+ optimization: normal function frames are on the per-thread data stack (not individual mallocs). Generator frames are still independently allocated (because they must outlive their creating call).

---

## 5.6 The Critical Invariant

```
At all times, exactly ONE of these is true:
1. gen->gi_frame != NULL AND gen->gi_running == False
   → Generator is SUSPENDED (frame saved, waiting for next/send)

2. gen->gi_frame == NULL AND gen->gi_running == True  
   → Generator is RUNNING (frame is on the active call stack)

3. gen->gi_frame == NULL AND gen->gi_closed == True
   → Generator is CLOSED (frame freed, cannot resume)

4. gen->gi_frame != NULL AND gen->gi_running == False AND never started
   → Generator is CREATED (frame exists but never entered)
```

---

## 5.7 Interview Questions — Part 5

**Q1**: Where does a generator's frame live? **A**: On the heap, inside the PyGenObject. Unlike normal function frames which live on the per-thread data stack and are destroyed on return.

**Q2**: What exactly is preserved between yields? **A**: The instruction pointer (prev_instr), all local variables (localsplus), the operand stack state (partially evaluated expressions), and cell/free variables (closures).

**Q3**: What does YIELD_VALUE do to the frame? **A**: Saves prev_instr (resume point), saves stacktop (stack height), stores frame reference in gen->gi_frame, pops frame from active call stack, returns yielded value.

**Q4**: How does gen.send(value) inject a value? **A**: Pushes `value` onto the generator's saved operand stack before resuming. When the YIELD_VALUE instruction "completes" on resume, this value becomes the yield expression's result.

**Q5**: Why can't you call next() on a running generator? **A**: gen->gi_running is checked. If True (generator is already executing), ValueError is raised. This prevents reentrant execution which would corrupt the frame state.

**Q6**: What's the cost of frame suspension? **A**: ~100-200ns per yield (save frame state + return from eval loop + re-enter eval loop on resume). The frame allocation itself is ~200ns at generator creation. Much more than list_iterator's 30ns/element.
