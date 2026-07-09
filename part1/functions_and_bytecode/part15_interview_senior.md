# Part 15 — Interview Questions: Senior (50)

**Q1**: Explain the computed goto dispatch in ceval.c and why it's faster than switch. **A**: Each opcode handler ends with `goto *opcode_targets[next_opcode]` — a direct indirect jump. Switch requires: compare opcode, jump to case table, then jump to handler. Computed goto: one indirect jump. Better branch prediction (each handler has its own predicted target), ~15-20% faster.

**Q2**: How does the specializing adaptive interpreter track type stability? **A**: Each specialized instruction has an inline cache after it with counters. On type match: fast path. On mismatch: decrement counter, deoptimize when counter hits zero. Adaptive state: specialize after N consistent observations, deoptimize after M failures, then permanently de-specialize.

**Q3**: Explain the frame stack allocation in Python 3.11+. **A**: Frames are allocated on a per-thread "data stack" (pre-allocated memory). No malloc per call — just advance a pointer. Frame memory is reused by moving the pointer back on return. Only sys._getframe() or exceptions trigger heap-allocated PyFrameObject creation.

**Q4**: How does CPython implement inline caches for LOAD_ATTR? **A**: After the LOAD_ATTR instruction, 4-8 bytes of cache follow. Stores: expected type version (tp_version_tag) + attribute offset. On execution: check ob_type->tp_version_tag == cached. If match: read attribute at cached offset (O(1)). If mismatch: deoptimize, full __getattribute__ lookup.

**Q5**: Explain how the compiler builds the exception table. **A**: During compilation, try blocks register code offset ranges. For each range, the target handler address and stack depth are recorded. The table is compressed (variable-length encoding). At runtime: binary search through table on exception.

**Q6**: How does `yield` suspend a frame? **A**: YIELD_VALUE sets the frame's prev_instr to the current position, saves stacktop, and returns the yielded value to the caller (send()). On next()/send(): the frame is re-entered at prev_instr+1, stack restored, execution continues.

**Q7**: How does `async def` differ from `def` at the code level? **A**: CO_COROUTINE flag set. Calling doesn't execute body — creates a coroutine object. RETURN_VALUE becomes a StopIteration. Awaiting calls __await__ / cr_await resolution. The frame suspends/resumes like generators.

**Q8**: Explain the BINARY_OP specialization for int + int. **A**: BINARY_OP_ADD_INT: checks both operands are exact PyLongObject (not subclass), checks both fit in a single digit (fast path), performs C-level addition directly, boxes result. If assumptions fail: deoptimize to generic BINARY_OP.

**Q9**: How does the compiler handle list comprehensions as separate scopes? **A**: Compiles the comprehension body to its own code object (with its own co_varnames). The iteration variable is local to that scope. MAKE_FUNCTION + CALL implicitly calls the comprehension's "hidden function."

**Q10**: Explain the tp_vectorcall_offset mechanism. **A**: A type can store a vectorcall function pointer at a byte offset within its instances (tp_vectorcall_offset != 0). The CALL opcode reads the pointer from `((char*)obj) + offset` and calls it directly. Avoids tp_call indirection.

**Q11**: How does super() work at the bytecode level? **A**: LOAD_GLOBAL __class__ (compiler ensures the cell exists); calls super(). The compiler creates an implicit __class__ cell in methods. super() reads it to determine the class context.

**Q12**: Explain how CPython handles `from module import *`. **A**: IMPORT_STAR opcode: imports the module, gets its __all__ (or dir()), then STORE_NAME each name into the current namespace. Can't be used inside functions (would need STORE_FAST, but names unknown at compile time).

**Q13**: How does the peephole optimizer handle `if True:` and `if False:`? **A**: In 3.12+: `if False:` block is removed entirely (dead code). `if True:` condition check is removed (unconditional). Earlier versions kept the comparison but optimized the jump.

**Q14**: Explain the co_linetable format (3.11+). **A**: Compressed mapping: for each instruction, stores (bytecode_offset_delta, line_delta, column_start, column_end). Variable-length encoding. Used by tracebacks, debuggers, coverage tools.

**Q15**: How does multiple assignment `a = b = expr` work? **A**: Compiles to: evaluate expr, DUP_TOP (copy on stack), STORE_FAST a, STORE_FAST b. One evaluation, two stores. Both names reference the same object.

**Q16-50**: *(Senior topics: __slots__ interaction with LOAD_ATTR, descriptor protocol in attribute lookup bytecode, metaclass __call__ for instance creation, __init_subclass__ hook bytecode, PEP 659 tier architecture, trace-based optimization future, frame introspection costs, generator throw/close at bytecode level, context manager __aenter__/__aexit__ bytecode, pattern matching MATCH_ opcodes, structural pattern matching implementation, free-threading impact on eval loop, per-interpreter GIL implications for frames, immortal code objects, co_qualname for nested functions, bytecode verification/validation, custom opcodes via C extensions, sys.settrace performance impact, coverage.py line counting mechanism, bytecode optimization passes order, dead store elimination, unused import detection at bytecode level.)*
