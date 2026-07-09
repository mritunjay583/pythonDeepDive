# Part 8 — Function Calls

## 8.1 The CALL Opcode

When Python executes `result = func(arg1, arg2)`:

```
Bytecode:
  LOAD_GLOBAL    func          ← push function object
  LOAD_FAST      arg1          ← push first argument  
  LOAD_FAST      arg2          ← push second argument
  CALL           2             ← call with 2 arguments
  STORE_FAST     result        ← store return value
```

The CALL opcode:
1. Pops the callable + arguments from the stack
2. Determines call protocol (Python function? C function? callable object?)
3. For Python functions: creates frame, binds args, executes bytecode
4. Pushes the return value onto the caller's stack

---

## 8.2 The Call Protocol (Simplified)

```c
// What CALL does (highly simplified from ceval.c):
PyObject *callable = stack[-(nargs + 1)];  // Bottom of call args

if (PyFunction_Check(callable)) {
    // FAST PATH: Python function → frame-based call
    _PyInterpreterFrame *new_frame = create_frame(callable, args, nargs);
    // ... push frame, execute ...
}
else if (PyCFunction_Check(callable)) {
    // C built-in function → direct C call (no frame!)
    result = ((PyCFunction)callable->ml_meth)(self, args);
}
else if (Py_TYPE(callable)->tp_vectorcall_offset) {
    // Vectorcall protocol (PEP 590) — fast generic call
    vectorcallfunc vcall = *(vectorcallfunc*)(((char*)callable) + tp_vectorcall_offset);
    result = vcall(callable, args_array, nargs, kwnames);
}
else {
    // Slow path: tp_call
    result = Py_TYPE(callable)->tp_call(callable, args_tuple, kwargs_dict);
}
```

---

## 8.3 Frame Creation for Python Functions

```c
// Creating a frame for a Python function call:
_PyInterpreterFrame *
_PyEvalFrameDefault_create_frame(PyFunctionObject *func, PyObject **args, int nargs)
{
    PyCodeObject *code = (PyCodeObject *)func->func_code;
    
    // Allocate frame (localsplus = locals + cells + frees + stack):
    int total_slots = code->co_nlocals + code->co_ncellvars + 
                      code->co_nfreevars + code->co_stacksize;
    _PyInterpreterFrame *frame = allocate_frame(total_slots);
    
    // Initialize frame:
    frame->f_code = code;
    frame->f_globals = func->func_globals;
    frame->f_builtins = func->func_builtins;
    frame->f_locals = NULL;  // Created lazily if locals() called
    frame->prev_instr = code->co_code - 1;  // Before first instruction
    frame->stacktop = frame->localsplus + code->co_nlocals + ...;
    
    // Bind arguments to local slots:
    for (int i = 0; i < nargs; i++) {
        frame->localsplus[i] = args[i];
        Py_INCREF(args[i]);
    }
    
    // Initialize remaining locals to NULL (UnboundLocalError if accessed):
    for (int i = nargs; i < code->co_nlocals; i++) {
        frame->localsplus[i] = NULL;
    }
    
    // Set up cell variables (create cell objects):
    for (int i = 0; i < code->co_ncellvars; i++) {
        frame->localsplus[code->co_nlocals + i] = PyCell_New(NULL);
    }
    
    // Copy free variable cells from closure:
    PyObject *closure = func->func_closure;
    for (int i = 0; i < code->co_nfreevars; i++) {
        frame->localsplus[code->co_nlocals + code->co_ncellvars + i] = 
            PyTuple_GET_ITEM(closure, i);
        Py_INCREF(PyTuple_GET_ITEM(closure, i));
    }
    
    return frame;
}
```

---

## 8.4 The localsplus Array Layout

```
localsplus[]:
┌──────────────────────────────────────────────────────────────────┐
│ local vars (co_nlocals) │ cells (co_ncellvars) │ frees │ stack  │
│ [x] [y] [z] ...        │ [cell0] [cell1] ...  │ ...   │ [][][]│
└──────────────────────────────────────────────────────────────────┘
 ├── LOAD_FAST i ────────┤├── LOAD_DEREF ───────────────┤
                                                          ├ operand stack

Arguments fill the first co_argcount + co_kwonlyargcount + varargs positions.
Then other locals.
Then cell variables (PyCellObject*).
Then free variables (PyCellObject* from closure).
Then the operand stack (co_stacksize PyObject* slots).
```

---

## 8.5 Parameter Binding

```python
def f(a, b, c=10, *args, key=None, **kwargs):
    pass

f(1, 2, 3, 4, 5, key="val", extra=True)
```

Binding:
```
a = 1                    (positional → localsplus[0])
b = 2                    (positional → localsplus[1])
c = 3                    (positional with default → localsplus[2])
args = (4, 5)            (*args → localsplus[3])
key = "val"              (keyword → localsplus[4])
kwargs = {"extra": True} (**kwargs → localsplus[5])
```

CPython handles this in `_PyEval_MakeFrameVector` with complex argument parsing logic covering all the edge cases (positional, keyword, defaults, *args, **kwargs, positional-only, keyword-only).

---

## 8.6 Return Value

```c
case RETURN_VALUE: {
    PyObject *retval = POP();   // Pop return value from callee's stack
    
    // Cleanup frame:
    // - Decref all remaining locals
    // - Decref all remaining stack items
    // - Pop this frame from the call stack
    
    // Push retval onto CALLER's stack:
    PUSH(retval);  // (on the caller's stack pointer)
    
    // Resume caller's execution at next instruction after CALL
    break;
}
```

---

## 8.7 Recursion and the Call Stack

```python
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

factorial(5)
```

Call stack at deepest point:
```
Frame: factorial(1) ← currently executing
  ↑ caller
Frame: factorial(2)
  ↑ caller
Frame: factorial(3)
  ↑ caller
Frame: factorial(4)
  ↑ caller
Frame: factorial(5)
  ↑ caller
Frame: <module> (top-level)
```

Each frame consumes memory. Default recursion limit: `sys.getrecursionlimit()` = 1000. Exceeding it: `RecursionError`.

---

## 8.8 Vectorcall Protocol (PEP 590)

The traditional call protocol creates a tuple for args + dict for kwargs → expensive!

Vectorcall passes arguments as a **C array** directly:

```c
// Traditional: costly tuple+dict creation
result = tp_call(callable, args_tuple, kwargs_dict);

// Vectorcall: zero-copy argument passing
result = vectorcall(callable, args_array, nargs, kwnames_tuple);
// args_array: C array of PyObject* (no tuple allocation!)
// nargs: count (with PY_VECTORCALL_ARGUMENTS_OFFSET flag for self)
// kwnames_tuple: just the keyword names (values are in the array)
```

~20% faster for typical function calls (avoids allocating/freeing arg tuples).

---

## 8.9 Interview Questions — Part 8

**Q1**: What does the CALL opcode do?
**A**: Pops callable + arguments from stack, determines call protocol, creates a new frame for Python functions (or calls C functions directly), executes the callee, and pushes the return value onto the caller's stack.

**Q2**: Where are function arguments stored during execution?
**A**: In the frame's `localsplus` array, at indices 0 through co_argcount-1 (for positional args), then keyword-only, then *args, then **kwargs.

**Q3**: What is the vectorcall protocol?
**A**: PEP 590's optimized calling convention. Passes arguments as a C array of PyObject* (no tuple/dict creation). ~20% faster for typical calls.

**Q4**: What happens when the recursion limit is exceeded?
**A**: Each function call creates a frame consuming memory. When call depth exceeds `sys.getrecursionlimit()` (default 1000), CPython raises RecursionError to prevent C stack overflow.

**Q5**: What's in a frame's localsplus array?
**A**: `[local variables | cell variables | free variables | operand stack]` — all in one contiguous C array. LOAD_FAST accesses the locals portion, LOAD_DEREF accesses cells/frees, and the stack grows from the end.
