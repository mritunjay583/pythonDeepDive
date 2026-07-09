# Part 9 — Frames and the Call Stack

## 9.1 What Is a Frame?

A **frame** (historically PyFrameObject, now `_PyInterpreterFrame` in 3.11+) represents one active function execution. It contains:
- Which code object is being executed
- Where in the bytecode we are (instruction pointer)
- The local variables + operand stack (localsplus array)
- Reference to globals and builtins dicts
- Link to the previous frame (caller)

---

## 9.2 The _PyInterpreterFrame Structure (3.11+)

```c
// Include/internal/pycore_frame.h
typedef struct _PyInterpreterFrame {
    PyCodeObject *f_code;         // Code being executed
    struct _PyInterpreterFrame *previous;  // Caller's frame (linked list)
    PyObject *f_funcobj;          // Function object (for closures, globals)
    PyObject *f_globals;          // Global namespace dict
    PyObject *f_builtins;         // Builtins namespace dict
    PyObject *f_locals;           // Local namespace dict (lazy, usually NULL)
    PyFrameObject *frame_obj;     // Python-visible frame (lazy, for inspect)
    _Py_CODEUNIT *prev_instr;    // Last executed instruction pointer
    int stacktop;                 // Top of value stack index
    uint16_t return_offset;       // Offset to return to in caller
    char owner;                   // Who owns this frame's memory
    
    PyObject *localsplus[1];     // Flexible array: locals + cells + frees + stack
} _PyInterpreterFrame;
```

---

## 9.3 Frame Memory Layout

```
_PyInterpreterFrame:
┌──────────────────────────────────────────────────────────────┐
│ f_code          → PyCodeObject                               │
│ previous        → caller's frame                             │
│ f_funcobj       → PyFunctionObject                           │
│ f_globals       → module.__dict__                            │
│ f_builtins      → builtins.__dict__                          │
│ f_locals        → NULL (created lazily by locals())          │
│ frame_obj       → NULL (created lazily by sys._getframe())   │
│ prev_instr      → bytecode position                          │
│ stacktop        → stack pointer index                        │
├──────────────────────────────────────────────────────────────┤
│ localsplus[0]   → local var 0 (1st parameter)               │
│ localsplus[1]   → local var 1 (2nd parameter)               │
│ ...             → remaining locals                           │
│ localsplus[n]   → cell var 0 (PyCellObject*)                │
│ ...             → free vars (PyCellObject*)                  │
│ localsplus[m]   → stack slot 0 (operand stack starts here)  │
│ localsplus[m+1] → stack slot 1                              │
│ ...             → up to co_stacksize slots                   │
└──────────────────────────────────────────────────────────────┘
```

---

## 9.4 The Call Stack

```python
def a():
    return b()

def b():
    return c()

def c():
    return 42

result = a()
```

During execution of `c()`:
```
Call Stack (linked via 'previous' pointers):

_PyInterpreterFrame for c()
  │ f_code = c's code object
  │ localsplus = [... | stack: ... ]
  │ previous ──────────────────────────────┐
                                            │
_PyInterpreterFrame for b()               ←─┘
  │ f_code = b's code object
  │ previous ──────────────────────────────┐
                                            │
_PyInterpreterFrame for a()               ←─┘
  │ f_code = a's code object
  │ previous ──────────────────────────────┐
                                            │
_PyInterpreterFrame for <module>          ←─┘
  │ f_code = module's code object
  │ previous = NULL (bottom of stack)
```

---

## 9.5 Frame Allocation (3.11+ Optimization)

Before 3.11: every frame was a heap-allocated PyFrameObject (~400 bytes).

Since 3.11: frames are allocated on the **C stack** or a **per-thread frame stack**:

```c
// Frame is allocated on the thread's frame stack (pre-allocated memory):
_PyInterpreterFrame *frame = &thread_state->datastack[offset];
// NO malloc/free! Just pointer arithmetic!
// Frame "lives" on the data stack until the function returns.
// Then the space is reclaimed by moving the stack pointer back.
```

Benefits:
- No malloc/free per function call (~30% faster function calls)
- Better cache locality (frames are contiguous in memory)
- Smaller overhead per frame

The heap-allocated PyFrameObject is created **lazily** only if:
- `sys._getframe()` is called
- `traceback` needs it (exception occurred)
- A debugger/profiler requests it
- `locals()` is called

---

## 9.6 Frame Reuse

For simple functions that don't need persistent frames, the interpreter reuses frame space:

```python
def simple(x):
    return x + 1

# Called 1M times:
for i in range(1000000):
    simple(i)

# Each call REUSES the same frame memory (just overwrites localsplus)
# No allocation per call!
```

---

## 9.7 Accessing Frames from Python

```python
import sys

def show_frame():
    frame = sys._getframe()  # Get current frame
    print(f"Function: {frame.f_code.co_name}")
    print(f"Line: {frame.f_lineno}")
    print(f"Locals: {frame.f_locals}")
    
    # Walk the call stack:
    f = frame
    while f is not None:
        print(f"  {f.f_code.co_name} at line {f.f_lineno}")
        f = f.f_back

show_frame()
```

---

## 9.8 Interview Questions — Part 9

**Q1**: What is a frame in CPython?
**A**: A runtime structure representing one function execution. Contains code object, instruction pointer, local variables, operand stack, and a link to the caller's frame.

**Q2**: How did Python 3.11 optimize frame allocation?
**A**: Frames are now allocated on a per-thread data stack (pre-allocated memory, pointer arithmetic) instead of individual heap allocations. PyFrameObject is only created lazily when needed (sys._getframe, traceback, debugger).

**Q3**: What is the localsplus array?
**A**: A single contiguous C array containing: local variables, cell variables, free variables, AND the operand stack — all in one allocation within the frame.

**Q4**: How are frames connected?
**A**: Via the `previous` pointer — a singly-linked list. Each frame points to its caller. Walking this list gives the full call stack (used by traceback, debuggers).

**Q5**: When is a heap-allocated PyFrameObject created?
**A**: Lazily — only when Python code requests it: sys._getframe(), exception tracebacks, debuggers, or locals() calls. Most frames never need a Python-visible object.
