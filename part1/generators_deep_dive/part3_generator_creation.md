# Part 3 — Generator Creation: What Really Happens

## 3.1 At Compile Time

When the compiler encounters `yield` anywhere in a function body, it:

1. Sets `CO_GENERATOR` flag on the code object's `co_flags`
2. Emits `RETURN_GENERATOR` as the first real opcode (after RESUME)
3. Emits `YIELD_VALUE` at each yield point
4. Implicit `return None` at the end becomes `LOAD_CONST None; RETURN_VALUE` (which triggers StopIteration)

```python
import dis
def gen(x):
    y = x + 1
    yield y
    yield y * 2

dis.dis(gen)
```

```
  0 RESUME                0          ← Entry point marker
  2 RETURN_GENERATOR                 ← Create gen object, DON'T execute body!
  4 POP_TOP                          ← (cleanup after RETURN_GENERATOR re-entry)
  ─── First next() enters HERE ───
  6 RESUME                1          ← Re-entry after generator created
  8 LOAD_FAST             0 (x)
 10 LOAD_CONST            1 (1)
 12 BINARY_OP             0 (+)
 16 STORE_FAST            1 (y)
 18 LOAD_FAST             1 (y)
 20 YIELD_VALUE           1          ← Suspend, return y
 22 RESUME                1          ← Resume point for second next()
 24 POP_TOP                          ← Discard sent value (None from next())
 26 LOAD_FAST             1 (y)
 28 LOAD_CONST            2 (2)
 30 BINARY_OP             5 (*)
 34 YIELD_VALUE           1          ← Suspend, return y*2
 36 RESUME                1
 38 POP_TOP
 40 LOAD_CONST            0 (None)
 42 RETURN_VALUE                     ← End → StopIteration
```

---

## 3.2 At Runtime: Calling the Generator Function

```python
g = gen(10)  # What happens here?
```

### Step 1: Normal function call setup
- CALL opcode evaluates `gen` and argument `10`
- Creates a new frame for `gen` with `x = 10` bound

### Step 2: RETURN_GENERATOR opcode executes

```c
// Python/bytecodes.c (3.12+):
inst(RETURN_GENERATOR) {
    assert(PyFunction_Check(frame->f_funcobj));
    PyGenObject *gen = (PyGenObject *)_Py_MakeCoro(
        (PyFunctionObject *)frame->f_funcobj);
    if (gen == NULL) goto error;
    
    // Generator now OWNS the frame:
    gen->gi_frame = frame;
    
    // Return the generator to the caller WITHOUT executing body:
    frame = tstate->current_frame = frame->previous;
    _PyFrame_StackPush(frame, (PyObject *)gen);
    goto resume_frame;
}
```

### Step 3: _Py_MakeCoro creates the PyGenObject

```c
// Objects/genobject.c:
PyObject *
_Py_MakeCoro(PyFunctionObject *func)
{
    // Determine type: generator, coroutine, or async generator
    int cflags = ((PyCodeObject *)func->func_code)->co_flags;
    
    PyGenObject *gen;
    if (cflags & CO_GENERATOR) {
        gen = PyObject_GC_New(PyGenObject, &PyGen_Type);
    } else if (cflags & CO_COROUTINE) {
        gen = (PyGenObject *)PyObject_GC_New(PyCoroObject, &PyCoro_Type);
    } else {
        gen = (PyGenObject *)PyObject_GC_New(PyAsyncGenObject, &PyAsyncGen_Type);
    }
    
    // Initialize fields:
    gen->gi_frame = NULL;      // Will be set by caller
    gen->gi_code = Py_NewRef(func->func_code);
    gen->gi_name = Py_NewRef(func->func_name);
    gen->gi_qualname = Py_NewRef(func->func_qualname);
    gen->gi_weakreflist = NULL;
    gen->gi_exc_state = (PyObject *)Py_None;
    gen->gi_closed = 0;
    gen->gi_running_async = 0;
    
    _PyObject_GC_TRACK(gen);
    return (PyObject *)gen;
}
```

---

## 3.3 Memory State After Creation

```python
g = gen(10)
# At this point:
```

```
'g' ──→ PyGenObject (~112 bytes, heap)
          │
          ├── ob_refcnt: 1 (just 'g')
          ├── ob_type: → PyGen_Type
          ├── gi_frame ──→ _PyInterpreterFrame (heap)
          │                 ├── f_code → gen's code object
          │                 ├── prev_instr → RETURN_GENERATOR (start position)
          │                 ├── localsplus:
          │                 │   [0] x = 10  ← argument already bound!
          │                 │   [1] y = NULL ← not yet assigned
          │                 │   [stack...] = empty
          │                 └── stacktop = (stack base)
          ├── gi_code ──→ <code object gen>
          ├── gi_name: "gen"
          ├── gi_qualname: "gen"
          ├── gi_closed: False
          ├── gi_running: False
          └── gi_weakreflist: NULL

State: GEN_CREATED
Body has NOT executed. y is NULL. Only x is bound (from the call).
```

---

## 3.4 The Key Insight: Arguments ARE Bound

Even though the body hasn't executed, **arguments are already in the frame's localsplus**. This is because argument binding happens during the CALL opcode (before RETURN_GENERATOR):

```python
def gen(a, b, c=99):
    yield a + b + c

g = gen(1, 2)
# Frame already has: localsplus = [a=1, b=2, c=99, ...]
# Body hasn't run, but parameters are ready.
```

---

## 3.5 Reference Count Implications

At creation time:
- PyGenObject: refcnt=1 (from `g`)
- Frame's localsplus[0] (arg `x`): Py_INCREF'd during CALL argument binding
- gen's code object: Py_INCREF'd by gi_code
- gi_name string: Py_INCREF'd

If `del g` without consuming: generator destructor is called, which calls `gen_dealloc` → `gen_close` (throws GeneratorExit to run finally blocks) → frees frame → decrefs all locals.

---

## 3.6 Interview Questions — Part 3

**Q1**: What opcode creates the generator object? **A**: `RETURN_GENERATOR`. It calls `_Py_MakeCoro()`, which allocates a PyGenObject, attaches the current frame to it, and returns the generator to the caller without executing the function body.

**Q2**: Are function arguments available before the first next()? **A**: Yes! Arguments are bound to the frame's localsplus during the CALL opcode (before RETURN_GENERATOR). The frame has args set, just the body hasn't run.

**Q3**: What is the generator's state immediately after creation? **A**: GEN_CREATED. gi_frame points to a valid frame (with args bound), gi_closed=False, gi_running=False. No bytecode from the body has executed yet.

**Q4**: Where is the generator's frame allocated? **A**: On the heap (via PyObject_GC_New or the data stack in 3.11+, then transferred to heap). Must be on heap because it outlives the creating function call.

**Q5**: What happens if you `del g` without consuming the generator? **A**: gen_dealloc is called: throws GeneratorExit into the generator (triggering finally blocks), then frees the frame and decrefs all references (locals, args, code object).
