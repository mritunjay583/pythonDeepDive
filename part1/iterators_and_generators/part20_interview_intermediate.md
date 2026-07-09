# Part 20 — Interview Questions: Intermediate (50)

**Q1**: How does the for loop translate to bytecode? **A**: GET_ITER (calls iter), then repeated FOR_ITER (calls tp_iternext, pushes value or jumps on exhaustion). JUMP_BACKWARD loops. END_FOR cleans up.

**Q2**: What C slots implement the iterator protocol? **A**: `tp_iter` (getiterfunc, returns iterator) and `tp_iternext` (iternextfunc, returns next value or NULL).

**Q3**: How does tp_iternext signal exhaustion at C level? **A**: Returns NULL. The StopIteration exception may be set but the NULL pointer is what ceval.c checks (faster than exception matching).

**Q4**: What is the memory layout of a list_iterator? **A**: PyObject_HEAD (16B) + it_index (8B) + it_seq pointer (8B) = 32 bytes. Tracks position and holds reference to list.

**Q5**: How does a generator's frame persist between yields? **A**: The frame is allocated on the heap (inside PyGenObject). YIELD_VALUE saves instruction pointer + stack state. On resume: frame re-enters the eval loop.

**Q6**: What is the size of a PyGenObject? **A**: ~112 bytes for the object itself + the frame (varies by co_nlocals + co_stacksize). Significantly larger than simple iterators.

**Q7**: Why is generator iteration slower than list iteration per element? **A**: Each yield: save frame, exit eval loop, return to caller. Each resume: re-enter eval loop, restore frame. ~100-200ns overhead vs ~30ns for list iterator's index++.

**Q8**: What is PEP 479 and why does it matter? **A**: Makes StopIteration inside a generator body raise RuntimeError. Prevents silent generator termination from leaked StopIteration from sub-iterators. Default since Python 3.7.

**Q9**: How does dict iteration detect modification? **A**: Dict iterator stores `di_used` (entry count at creation). Each __next__ compares with dict.ma_used. If different → RuntimeError.

**Q10**: What does `yield from` do at the bytecode level? **A**: GET_YIELD_FROM_ITER + SEND loop. Forwards values from sub-iterator to caller, forwarding send/throw/close transparently.

**Q11**: How does itertools achieve better performance than generators? **A**: Implemented in C (Modules/itertoolsmodule.c). No Python frame overhead, no bytecode dispatch, direct C loops.

**Q12**: What is the two-argument form of iter()? **A**: `iter(callable, sentinel)` creates a callable_iterator that calls the function until the result equals sentinel. Used for reading until EOF, etc.

**Q13**: How does async iteration differ from sync? **A**: `__anext__` returns an awaitable (coroutine). The event loop can run other tasks between iterations. Uses `StopAsyncIteration` (not StopIteration).

**Q14**: What is `RETURN_GENERATOR` opcode? **A**: In 3.12+, creates the PyGenObject from the current frame at function entry. Replaces the old mechanism. Body is NOT executed until first next().

**Q15**: Why does range() support O(1) `in` operator? **A**: range.__contains__ computes membership arithmetically: `(value - start) % step == 0 and start <= value < stop`. No iteration needed!

**Q16**: How does itertools.groupby maintain O(1) memory? **A**: Only stores the current key and current group. Once you advance past a group, its items are gone. Requires pre-sorted input for complete grouping.

**Q17**: What happens to a generator when it's garbage collected while suspended? **A**: GC calls gen.close() → throws GeneratorExit → finally blocks execute → resources cleaned up. This is why generators with `try/finally` are safe.

**Q18**: How does `yield from` handle send/throw? **A**: Transparently forwards: caller.send(v) → sub_gen.send(v). caller.throw(e) → sub_gen.throw(e). Like a transparent proxy.

**Q19**: What is the return value of yield from? **A**: The value from the sub-generator's `return` statement (which becomes StopIteration.value).

**Q20**: Why can't you iterate a generator expression multiple times? **A**: A genexp creates ONE generator object. Generators are iterators (single-use). __iter__ returns self — no way to "reset."

**Q21-50**: *(Cover: comprehension scoping, iterator algebra, generator delegation depth, coroutine vs generator, async generator finalization, generator-based coroutines pre-async, contextlib.contextmanager using generators, itertools recipes, _PySeqIter fallback, iterator unpacking (a, b, *rest = iter), exhaustion detection, lazy imports, generator memory profiling, chained exception handling in generators, generator stack traces, subgenerator return value, weak references to generators, frame object access from generators, gi_yieldfrom attribute, iterator interop with C extensions.)*
