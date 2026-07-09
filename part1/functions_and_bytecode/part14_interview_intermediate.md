# Part 14 — Interview Questions: Intermediate (50)

**Q1**: How does the symbol table phase determine local vs global vs free? **A**: Walks AST and classifies each name: assigned in this scope→LOCAL, explicitly `global`→GLOBAL, read from enclosing scope→FREE, assigned here and read by inner function→CELL.

**Q2**: What is the difference between co_code and the "bytecode"? **A**: co_code is the bytes object containing the raw bytecode. "Bytecode" refers to the logical instructions (opcode + arg pairs within co_code).

**Q3**: How does constant folding work? **A**: The compiler evaluates constant expressions at compile time: `2*3+1` → stores `7` in co_consts. Only for literals and simple operations.

**Q4**: What is the CFG (Control Flow Graph) in the compiler? **A**: The compiler builds a graph of basic blocks (straight-line code). Each block ends with a jump/return. The CFG is then linearized into the final bytecode sequence.

**Q5**: How does the compiler handle nested functions? **A**: Each function body is compiled to its own code object (recursive call to compiler). The inner code object is placed in the outer's co_consts. At runtime, MAKE_FUNCTION wraps it.

**Q6**: What is the EXTENDED_ARG opcode? **A**: Prefix opcode that extends the next instruction's argument beyond 255 (8 bits). `EXTENDED_ARG hi; OPCODE lo` gives effective arg = (hi << 8) | lo.

**Q7**: Explain how `a, b = b, a` works in bytecode. **A**: `LOAD_FAST b; LOAD_FAST a; ROT_TWO; STORE_FAST a; STORE_FAST b` (or `SWAP` in newer versions). Evaluates RHS tuple, then assigns. Equivalent to building a tuple and unpacking.

**Q8**: How does list comprehension compile differently from a for loop? **A**: Comprehensions compile to a separate code object (their own scope). Uses LIST_APPEND for direct append (bypasses method lookup). The code object is called implicitly.

**Q9**: What is the RESUME opcode? **A**: First instruction of every code object (3.11+). Does nothing but enables tracing/profiling hooks and marks the entry point.

**Q10**: How does exception handling work in bytecode? **A**: co_exceptiontable maps instruction ranges to handler addresses. On error: lookup table for matching handler, jump there, push exception onto stack.

**Q11**: What is the peephole optimizer? **A**: Post-compilation pass that simplifies bytecode: removes dead jumps, folds constants missed by the compiler, eliminates unreachable code.

**Q12**: How does `with` statement compile? **A**: Calls __enter__ before the block, sets up exception table to call __exit__ on any exit path (normal or exception).

**Q13**: How does `yield` transform a function? **A**: Sets CO_GENERATOR flag. Instead of executing immediately, calling the function creates a generator object. Each YIELD_VALUE suspends the frame, RESUME restores it on next().

**Q14**: What is frame.f_locals? **A**: A dict representation of local variables. Created lazily when locals() is called (expensive! copies localsplus to a new dict).

**Q15**: Why is locals() slow? **A**: Must build a new dict from the fast locals array. Each call allocates a dict and copies all local name→value pairs.

**Q16**: How does Python implement `global x` internally? **A**: The compiler emits LOAD_GLOBAL/STORE_GLOBAL instead of LOAD_FAST/STORE_FAST. The variable is never in localsplus — always looked up in f_globals dict.

**Q17**: What is the __build_class__ function? **A**: Built-in called by the compiler when `class` statement is encountered. It creates the class by calling the metaclass with (name, bases, namespace).

**Q18**: How does CPython detect UnboundLocalError? **A**: localsplus[i] is NULL for uninitialized locals. LOAD_FAST checks for NULL and raises UnboundLocalError if found.

**Q19**: What is co_nlocals? **A**: Total count of local variables (parameters + other locals). Determines how many slots in localsplus before cells start.

**Q20**: How does *args get bound? **A**: Excess positional arguments are collected into a tuple and stored at the localsplus slot for the *args parameter.

**Q21**: How does **kwargs get bound? **A**: Unmatched keyword arguments are collected into a new dict and stored at the **kwargs slot.

**Q22**: What is the difference between LOAD_METHOD and LOAD_ATTR? **A**: LOAD_METHOD is specialized for method calls: it pushes (method, self) if the lookup is a regular method. Avoids creating a bound method object for immediate calls.

**Q23**: How does the compiler handle `try/except`? **A**: Emits instructions with an exception table mapping code ranges to handler offsets. On exception: search table, jump to handler, push exception.

**Q24**: What optimizations does the specializing interpreter do for LOAD_ATTR? **A**: Specializes to LOAD_ATTR_INSTANCE_VALUE (known instance attribute offset), LOAD_ATTR_MODULE (module dict cached), LOAD_ATTR_SLOT (__slots__ offset).

**Q25**: How does import work in bytecode? **A**: IMPORT_NAME opcode calls the import machinery. The imported module is pushed onto the stack, then STORE_FAST/STORE_NAME binds the name.

**Q26-50**: *(Cover: generator send/throw, async/await compilation, comprehension scoping rules, walrus operator bytecode, match/case compilation, f-string bytecode evolution, BINARY_SUBSCR specialization, BUILD_STRING for f-strings, LIST_EXTEND vs multiple appends, dict merge operator bytecode, assignment expressions, star unpacking in bytecode, augmented assignment bytecode, truth testing optimization, small int caching in constants.)*
