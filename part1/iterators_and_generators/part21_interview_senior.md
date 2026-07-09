# Part 21 — Interview Questions: Senior (50)

**Q1**: Explain the complete lifecycle of FOR_ITER at the C level. **A**: 1) Read TOS as iterator. 2) Call `tp_iternext(iter)`. 3) If non-NULL: push result, dispatch next opcode. 4) If NULL: check if StopIteration set → clear it, pop iterator, Py_DECREF, jump past loop. If other exception: goto error handler.

**Q2**: How does YIELD_VALUE interact with the frame lifecycle? **A**: Pops value from operand stack. Saves frame's prev_instr (resume point). Sets gen->gi_frame = frame. Pops frame from tstate->current_frame. Returns yielded value to whoever called gen_send_ex. Frame stays alive on heap.

**Q3**: Explain the gen_send_ex2 function in genobject.c. **A**: Checks generator state (closed→error, running→error). Pushes the sent arg onto generator's operand stack. Sets gen->gi_frame = NULL (mark running). Restores tstate->current_frame = gen_frame. Calls _PyEval_EvalFrame. On return: if NULL→close generator. Return result.

**Q4**: How does CPython optimize FOR_ITER for list iterators specifically? **A**: In 3.12+ specializing interpreter: FOR_ITER_LIST is a specialized opcode that directly accesses ob_item[index++] without going through tp_iternext virtual dispatch. Eliminates function pointer call overhead.

**Q5**: What is the cost of creating a generator object? **A**: ~200ns. PyObject_GC_New(112 bytes) + frame allocation + copying arguments to localsplus + GC tracking. Much more expensive than creating a list_iterator (32 bytes, no frame).

**Q6**: Explain how yield from handles GeneratorExit. **A**: When gen.close() is called on the delegating generator: if sub-generator has close(), call it. If sub-gen's close raises StopIteration: swallow it. If raises anything else: propagate. Then the delegating generator also finishes.

**Q7**: How does the async generator finalization problem work (PEP 525)? **A**: Async generators may be GC'd while suspended in an `await`. Finalization requires running the event loop (to execute finally blocks that await). sys.set_asyncgen_hooks() configures a firstiter/finalizer callback to handle this.

**Q8**: Explain the relationship between generator and coroutine objects at C level. **A**: Both use the same base: _PyGenObject_HEAD (shared fields). PyGenObject (generators), PyCoroObject (coroutines), PyAsyncGenObject (async generators) all inherit this base. Differ in type object and some flags.

**Q9**: How does `contextlib.contextmanager` use generators internally? **A**: Wraps a single-yield generator. `__enter__`: calls next(gen) → runs up to yield → returns yielded value. `__exit__`: resumes generator (or throws exception into it) → runs cleanup after yield.

**Q10**: What is the impact of generator-based iteration on CPU branch prediction? **A**: Poor. Each yield and resume jumps between different code locations (caller → generator frame → back). The indirect jumps through tp_iternext and the eval loop dispatch are hard for branch predictors. List iteration is a tight loop with predictable branches.

**Q11**: How does CPython handle generator memory in free-threaded (no-GIL) builds? **A**: Generator frames need proper synchronization. The gi_running flag prevents re-entrancy. In free-threaded builds, gen_send_ex needs atomics or locks to prevent concurrent access to the same generator.

**Q12**: Explain how the specializing interpreter optimizes iteration over range(). **A**: FOR_ITER_RANGE specialization: directly accesses the range_iterator's C struct (start + index*step), creates PyLong without calling tp_iternext. Even faster: BINARY_OP_ADD_INT specialization for the loop body avoids type dispatch.

**Q13**: What is the frame ownership model for generators? **A**: On creation: generator owns the frame. During execution: tstate owns it (current_frame). On yield: ownership returns to generator. On close/exhaustion: frame is freed. This ownership transfer is what enables suspension.

**Q14**: How does itertools.chain.from_iterable handle nested generators efficiently? **A**: At C level: keeps one active sub-iterator. When it exhausts: fetches next from the outer iterable, gets its iterator, continues. Only one sub-iterator alive at a time. O(1) extra state.

**Q15**: Explain the di_result tuple reuse optimization in dict.items() iteration. **A**: _PyDictIterObject has a pre-allocated 2-tuple (di_result). On each __next__: if refcnt==1 (not held elsewhere), reuse the SAME tuple (just update its items). Avoids allocating a new tuple per iteration. ~20% faster for `for k,v in d.items()`.

**Q16-50**: *(Senior topics: generator trampoline patterns, greenlets vs generators, frame evaluation re-entrancy, SEND opcode semantics, async generator athrow/aclose, iterator chaining type inference, lazy evaluation in type checking (PEP 649), generator GC interaction with weak references, performance of deeply nested yield from, co_lines/co_linetable for generators, traceback through yield from chains, sys._getframe in generators, generator pickling attempts and limitations, iterator protocol in C extensions, buffer protocol iteration, memoryview iteration internals, array.array iteration, numpy iterator protocol, Cython generator compilation, generator-to-coroutine bridge, legacy coroutine detection.)*
