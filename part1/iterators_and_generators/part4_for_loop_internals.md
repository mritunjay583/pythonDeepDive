# Part 4 — How for Loops Actually Work

## 4.1 From Python to Bytecode

```python
for x in items:
    print(x)
```

Compiles to:
```
LOAD_FAST        items
GET_ITER                      # iter(items) → push iterator
FOR_ITER         <exit>       # next(iterator) → push value OR jump to exit
STORE_FAST       x            # x = value
LOAD_GLOBAL      print
LOAD_FAST        x
CALL             1
POP_TOP
JUMP_BACKWARD    <FOR_ITER>   # Back to FOR_ITER
<exit>:
END_FOR                       # Pop iterator from stack
```

---

## 4.2 GET_ITER Opcode

```c
// Python/ceval.c
case GET_ITER: {
    PyObject *iterable = TOP();           // Peek at TOS (the iterable)
    PyObject *iter = PyObject_GetIter(iterable);  // Call __iter__()
    if (iter == NULL) goto error;
    SET_TOP(iter);                        // Replace iterable with iterator on stack
    Py_DECREF(iterable);                  // Done with the iterable itself
    DISPATCH();
}
```

After GET_ITER: stack has the iterator object (not the original iterable).

---

## 4.3 FOR_ITER Opcode

```c
// The heart of iteration:
case FOR_ITER: {
    PyObject *iter = TOP();               // Peek at iterator (stays on stack!)
    PyObject *next = (*Py_TYPE(iter)->tp_iternext)(iter);  // Call __next__
    
    if (next != NULL) {
        // Got a value — push it and continue loop body
        PUSH(next);
        DISPATCH();
    }
    
    // next == NULL — check for StopIteration
    if (_PyErr_Occurred(tstate)) {
        if (!_PyErr_ExceptionMatches(tstate, PyExc_StopIteration)) {
            goto error;  // Real error! Propagate.
        }
        _PyErr_Clear(tstate);  // Swallow StopIteration
    }
    
    // Loop exhausted — jump past loop body
    STACK_SHRINK(1);  // Pop the iterator
    Py_DECREF(iter);
    JUMPBY(oparg);    // Jump to exit label
    DISPATCH();
}
```

Key insights:
1. The iterator stays on the stack throughout the loop (only popped at exit)
2. `tp_iternext` is called directly (not through Python's next() overhead)
3. StopIteration is caught and cleared silently
4. Any other exception propagates normally

---

## 4.4 Complete Execution Trace

```python
for x in [10, 20, 30]:
    print(x)
```

```
Step 1: LOAD_FAST [10,20,30]     Stack: [[10,20,30]]
Step 2: GET_ITER                  Stack: [list_iterator(index=0)]
Step 3: FOR_ITER                  → next() returns 10
                                  Stack: [list_iterator, 10]
Step 4: STORE_FAST x              Stack: [list_iterator]  x=10
Step 5: ... print(x) ...         prints 10
Step 6: JUMP_BACKWARD → FOR_ITER
Step 7: FOR_ITER                  → next() returns 20
                                  Stack: [list_iterator, 20]
Step 8: STORE_FAST x              x=20
Step 9: ... print(x) ...         prints 20
Step 10: JUMP_BACKWARD → FOR_ITER
Step 11: FOR_ITER                 → next() returns 30
                                  Stack: [list_iterator, 30]
Step 12: STORE_FAST x             x=30
Step 13: ... print(x) ...        prints 30
Step 14: JUMP_BACKWARD → FOR_ITER
Step 15: FOR_ITER                 → next() returns NULL (StopIteration!)
                                  Pop iterator. Jump to exit.
Step 16: END_FOR                  Loop complete.
```

---

## 4.5 Interview Questions — Part 4

**Q1**: What two opcodes implement the for loop? **A**: GET_ITER (calls iter() once at start) and FOR_ITER (calls next() each iteration, jumps on exhaustion).

**Q2**: Where does the iterator live during the loop? **A**: On the operand stack. GET_ITER pushes it; it stays there through all iterations; FOR_ITER pops it when StopIteration is received.

**Q3**: Why does FOR_ITER call tp_iternext directly? **A**: Performance. Avoids the overhead of the Python-level next() built-in dispatch. Direct C function pointer call.

**Q4**: What happens if the iterator raises TypeError during the loop? **A**: FOR_ITER checks: if the exception is NOT StopIteration, it's a real error → propagates up (goto error). Only StopIteration is swallowed.
