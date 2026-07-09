# Part 13 — Interview Questions: Beginner (50)

**Q1**: What is a code object? **A**: Compiled bytecode + metadata for a block of Python code. Immutable. Created by the compiler.

**Q2**: What is a function object? **A**: A runtime wrapper around a code object + globals + closure + defaults. Created by `def` at runtime.

**Q3**: What does `def` do at runtime? **A**: Creates a PyFunctionObject wrapping a pre-compiled code object, then binds it to the function name.

**Q4**: Is a lambda different from def internally? **A**: No. Same PyFunctionObject + PyCodeObject. Only differences: __name__ = "<lambda>", body limited to one expression.

**Q5**: What does `dis.dis(func)` show? **A**: The bytecode instructions of the function's code object — opcodes, arguments, and human-readable annotations.

**Q6**: What is bytecode? **A**: A sequence of low-level instructions for CPython's virtual machine. Each instruction is 2 bytes (opcode + argument).

**Q7**: Is CPython's VM stack-based or register-based? **A**: Stack-based. Operations push/pop from an operand stack.

**Q8**: What does LOAD_FAST do? **A**: Pushes a local variable (from localsplus array by index) onto the operand stack. O(1) array access.

**Q9**: What does STORE_FAST do? **A**: Pops a value from the stack and stores it in the localsplus array at the specified index.

**Q10**: What does LOAD_CONST do? **A**: Pushes a constant from co_consts (by index) onto the stack.

**Q11**: What does RETURN_VALUE do? **A**: Pops the top of stack and returns it to the caller. The frame is then destroyed.

**Q12**: What is co_consts? **A**: A tuple of all constant values used in the code (literals, None, nested code objects).

**Q13**: What is co_varnames? **A**: A tuple of local variable names. The index in this tuple = the LOAD_FAST/STORE_FAST operand.

**Q14**: What is co_names? **A**: A tuple of names used for global lookups (LOAD_GLOBAL) and attribute access (LOAD_ATTR).

**Q15**: What is a frame? **A**: A runtime structure for one function execution — contains locals, stack, code reference, instruction pointer.

**Q16**: What is the call stack? **A**: A linked list of frames representing nested function calls. Each frame points to its caller.

**Q17**: What is the recursion limit? **A**: Maximum call stack depth (default 1000). Exceeding it raises RecursionError.

**Q18**: What does CALL do? **A**: Calls a function with arguments from the stack. Creates a new frame for Python functions.

**Q19**: What is MAKE_FUNCTION? **A**: Creates a PyFunctionObject from a code object (and optionally closure/defaults) on the stack.

**Q20**: What is a closure? **A**: A function that captures variables from its enclosing scope via cell objects.

**Q21**: What is a cell object? **A**: A tiny wrapper (24 bytes) holding a pointer to a captured variable's value. Shared between closures.

**Q22**: What does LOAD_DEREF do? **A**: Loads a value through a cell object (closure variable access).

**Q23**: What does STORE_DEREF do? **A**: Stores a value through a cell object (closure variable modification).

**Q24**: What is co_cellvars? **A**: Tuple of variable names in this function that are captured by inner functions.

**Q25**: What is co_freevars? **A**: Tuple of variable names this function captures from an enclosing scope.

**Q26**: What is a decorator at the bytecode level? **A**: A function call: push decorator, create function, call decorator(func), store result.

**Q27**: In what order are stacked decorators applied? **A**: Bottom-up (innermost first). `@a @b def f()` = `f = a(b(f))`.

**Q28**: What does functools.wraps do? **A**: Copies __name__, __doc__, __module__, __qualname__ from the original function to the wrapper.

**Q29**: What is `__code__`? **A**: The code object attribute of a function. `func.__code__` gives the PyCodeObject.

**Q30**: What is `__globals__`? **A**: The function's reference to its module's global dictionary. Used for LOAD_GLOBAL resolution.

**Q31**: What is `__defaults__`? **A**: Tuple of default argument values. Evaluated once at function-definition time.

**Q32**: What is `__closure__`? **A**: Tuple of cell objects for captured variables. None if no closure.

**Q33**: What is `callable(x)`? **A**: Returns True if x has a tp_call slot (can be called as a function).

**Q34**: How does `obj()` work for custom classes? **A**: Calls `type(obj).__call__(obj)` — looks up __call__ on the type and invokes it.

**Q35**: What is vectorcall? **A**: PEP 590's optimized call protocol. Passes args as C array (no tuple creation). ~20% faster.

**Q36**: What is co_stacksize? **A**: Maximum operand stack depth needed during execution. Computed statically by the compiler.

**Q37**: What is co_flags? **A**: Bitmask of function properties: CO_VARARGS, CO_VARKEYWORDS, CO_GENERATOR, CO_COROUTINE, etc.

**Q38**: What is the .pyc file? **A**: Cached compiled code object (marshalled). Skips recompilation on import if source unchanged.

**Q39**: What does `compile()` built-in do? **A**: Compiles source string to a code object (same pipeline as import, but explicit).

**Q40**: What is `exec()`? **A**: Executes a code object (or string) in a given namespace. Creates a frame and runs bytecode.

**Q41**: What is `eval()`? **A**: Like exec() but for single expressions. Returns the expression's value.

**Q42**: What happens to local variables after a function returns? **A**: The frame is destroyed. Locals (in localsplus) are decref'd. Objects with refcnt→0 are freed.

**Q43**: Why are local variables faster than globals? **A**: Locals use LOAD_FAST (array index, O(1)). Globals use LOAD_GLOBAL (dict lookup, ~3-5× slower).

**Q44**: What is the `nonlocal` keyword? **A**: Declares that a name refers to a variable in an enclosing scope (makes it a free variable, accessed via cell).

**Q45**: What is the `global` keyword? **A**: Declares that a name refers to the module-level global (uses LOAD_GLOBAL/STORE_GLOBAL instead of LOAD_FAST).

**Q46**: What does BINARY_OP do? **A**: Pops two operands, performs the operation (+ - * / etc.), pushes the result.

**Q47**: What does POP_JUMP_IF_FALSE do? **A**: Pops TOS, if falsy jumps to the target address. Used for if/while/and/or.

**Q48**: What does FOR_ITER do? **A**: Calls __next__ on TOS iterator. If StopIteration: pops iterator and jumps past loop. Else: pushes next value.

**Q49**: How does `break` work in bytecode? **A**: JUMP to the instruction after the loop (compiler resolves the target at compile time).

**Q50**: How does `continue` work in bytecode? **A**: JUMP back to the loop header (FOR_ITER or JUMP_BACKWARD to the while condition check).
