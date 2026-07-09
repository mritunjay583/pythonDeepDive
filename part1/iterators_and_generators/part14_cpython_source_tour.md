# Part 14 — CPython Source Tour

## 14.1 Key Files

| File | Content |
|------|---------|
| `Objects/iterobject.c` | PySeqIter (generic __getitem__ iterator), PyCallIter (iter(callable, sentinel)) |
| `Objects/genobject.c` | PyGenObject, coroutines, async generators (~2000 lines) |
| `Objects/listobject.c` | _PyListIterObject (list_iterator) |
| `Objects/dictobject.c` | Dict key/value/item iterators |
| `Objects/rangeobject.c` | range and range_iterator |
| `Objects/tupleobject.c` | Tuple iterator |
| `Objects/setobject.c` | Set iterator |
| `Objects/unicodeobject.c` | String (str_iterator) |
| `Python/ceval.c` | GET_ITER, FOR_ITER, YIELD_VALUE, SEND opcodes |
| `Modules/itertoolsmodule.c` | All itertools (C implementations, ~4000 lines) |

## 14.2 Objects/genobject.c — Key Functions

```c
// Creating a generator (called by RETURN_GENERATOR opcode):
PyObject *_Py_MakeCoro(PyFunctionObject *func)
{
    PyGenObject *gen = PyObject_GC_New(PyGenObject, &PyGen_Type);
    gen->gi_frame = frame;  // Attach frame
    gen->gi_code = func->func_code;
    gen->gi_name = func->func_name;
    gen->gi_qualname = func->func_qualname;
    gen->gi_weakreflist = NULL;
    gen->gi_exc_state = NULL;
    gen->gi_closed = 0;
    _PyObject_GC_TRACK(gen);
    return (PyObject *)gen;
}

// Resuming a generator (next/send):
static PyObject *gen_send_ex2(PyGenObject *gen, PyObject *arg, ...)
{
    _PyInterpreterFrame *frame = gen->gi_frame;
    if (frame == NULL) {
        // Generator is closed
        PyErr_SetNone(PyExc_StopIteration);
        return NULL;
    }
    // Push arg onto generator's stack (becomes yield result):
    _PyFrame_StackPush(frame, arg);
    // Resume execution:
    gen->gi_exc_state = tstate->exc_info;
    result = _PyEval_EvalFrame(tstate, frame, 0);
    gen->gi_exc_state = NULL;
    
    if (result == NULL) {
        // Generator finished or raised
        gen->gi_frame = NULL;  // Release frame
        gen->gi_closed = 1;
    }
    return result;
}
```

## 14.3 FOR_ITER Opcode (Python/ceval.c)

```c
case FOR_ITER: {
    PyObject *iter = TOP();
    PyObject *next = (*Py_TYPE(iter)->tp_iternext)(iter);
    if (next != NULL) {
        PUSH(next);
        DISPATCH();
    }
    if (_PyErr_Occurred(tstate)) {
        if (!_PyErr_ExceptionMatches(tstate, PyExc_StopIteration))
            goto error;
        _PyErr_Clear(tstate);
    }
    STACK_SHRINK(1);
    Py_DECREF(iter);
    JUMPBY(oparg);  // Jump past loop body
    DISPATCH();
}
```

## 14.4 YIELD_VALUE Opcode

```c
case YIELD_VALUE: {
    PyObject *retval = POP();
    PyGenObject *gen = frame_get_generator(frame);
    gen->gi_frame = frame;           // Save frame
    frame->prev_instr = next_instr;  // Save instruction pointer
    tstate->current_frame = frame->previous;  // Return to caller
    return retval;                   // Return yielded value
}
```

## 14.5 Interview Questions — Part 14

**Q1**: Where is the generator send/resume logic? **A**: `Objects/genobject.c`, function `gen_send_ex2`. Pushes the sent value onto the generator's stack, then calls `_PyEval_EvalFrame` to resume.

**Q2**: How does FOR_ITER detect loop end? **A**: Calls `tp_iternext`. If NULL returned: checks for StopIteration (swallows it, jumps past loop). Any other exception propagates.

**Q3**: What does YIELD_VALUE do to the frame? **A**: Saves the frame reference in the generator object, saves instruction pointer, pops this frame from the active call stack, returns the yielded value to the caller.
