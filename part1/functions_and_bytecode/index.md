# CPython Functions, Bytecode & Virtual Machine — Complete Reference

An advanced systems-programming-level document covering the complete lifecycle of Python code: from source text through compilation to bytecode, through execution on the stack-based virtual machine, including function objects, closures, frames, and the call protocol.

## Table of Contents

| # | File | Topic |
|---|------|-------|
| 1 | [part1_function_objects.md](part1_function_objects.md) | Why functions are objects, PyFunctionObject, creation, identity |
| 2 | [part2_closures_and_nested.md](part2_closures_and_nested.md) | Cell objects, free variables, closure memory layout, lambdas |
| 3 | [part3_code_objects.md](part3_code_objects.md) | PyCodeObject, every field explained, immutability, dis module |
| 4 | [part4_compilation_pipeline.md](part4_compilation_pipeline.md) | Source → Tokens → AST → CFG → Bytecode → Code Object |
| 5 | [part5_bytecode_fundamentals.md](part5_bytecode_fundamentals.md) | Opcodes, stack machine, operand stack, instruction format |
| 6 | [part6_bytecode_execution.md](part6_bytecode_execution.md) | ceval.c main loop, dispatch, LOAD/STORE, arithmetic, jumps |
| 7 | [part7_adaptive_specialization.md](part7_adaptive_specialization.md) | Python 3.11+ specializing interpreter, inline caches, quickening |
| 8 | [part8_function_calls.md](part8_function_calls.md) | CALL opcode, frame creation, parameter binding, return values |
| 9 | [part9_frames_and_stack.md](part9_frames_and_stack.md) | PyFrameObject, call stack, locals+stack array, frame reuse |
| 10 | [part10_decorators_internals.md](part10_decorators_internals.md) | Decorator desugaring, stacking, functools.wraps, class decorators |
| 11 | [part11_callable_protocol.md](part11_callable_protocol.md) | __call__, tp_call, vectorcall (PEP 590), partial, method binding |
| 12 | [part12_cpython_source_tour.md](part12_cpython_source_tour.md) | Key files: ceval.c, compile.c, funcobject.c, codeobject.c |
| 13 | [part13_interview_beginner.md](part13_interview_beginner.md) | 50 beginner questions with answers |
| 14 | [part14_interview_intermediate.md](part14_interview_intermediate.md) | 50 intermediate questions with answers |
| 15 | [part15_interview_senior.md](part15_interview_senior.md) | 50 senior questions with answers |
| 16 | [part16_bytecode_prediction_a.md](part16_bytecode_prediction_a.md) | Bytecode prediction exercises 1-50 |
| 17 | [part17_bytecode_prediction_b.md](part17_bytecode_prediction_b.md) | Bytecode prediction exercises 51-100 |
| 18 | [part18_exercises.md](part18_exercises.md) | Memory tracing, opcode tracing, frame tracing, compiler exercises |

## Prerequisites

- ✅ Python Object Model (PyObject, PyVarObject)
- ✅ Reference Counting & GC
- ✅ Lists, Dicts, Strings internals
- ✅ PyMalloc

## Key Source Files

```
Python/compile.c          → Compiler: AST → Code Object
Python/symtable.c         → Symbol table analysis (scoping)
Python/flowgraph.c        → Control flow graph construction
Python/instruction_sequence.c → Bytecode emission
Python/ceval.c            → THE main interpreter loop (eval loop)
Python/bytecodes.c        → Opcode definitions (3.12+)
Python/generated_cases.c.h → Auto-generated dispatch (3.12+)
Objects/funcobject.c      → PyFunctionObject implementation
Objects/codeobject.c      → PyCodeObject implementation
Objects/frameobject.c     → PyFrameObject implementation
Include/cpython/code.h    → Code object struct definition
Include/cpython/funcobject.h → Function object struct definition
Include/opcode.h          → Opcode numbers
Lib/dis.py               → Disassembler (Python-level)
Lib/inspect.py           → Code/frame introspection
```

## Quick Reference

```
╔══════════════════════════════════════════════════════════════════════════╗
║                    THE EXECUTION MODEL                                   ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  SOURCE CODE                                                             ║
║       │  tokenize (Lib/tokenize.py, Parser/tokenizer.c)                 ║
║       ▼                                                                  ║
║  TOKEN STREAM                                                            ║
║       │  parse (Parser/parser.c — PEG parser since 3.9)                 ║
║       ▼                                                                  ║
║  AST (Abstract Syntax Tree)                                              ║
║       │  compile (Python/compile.c)                                     ║
║       │    ├── symtable analysis (scoping: local/global/free/cell)       ║
║       │    ├── control flow graph                                       ║
║       │    └── bytecode emission                                        ║
║       ▼                                                                  ║
║  CODE OBJECT (PyCodeObject)                                              ║
║       │  co_code = bytecode bytes                                       ║
║       │  co_consts = constants tuple                                    ║
║       │  co_names = global/attr names                                   ║
║       │  co_varnames = local variable names                             ║
║       │                                                                  ║
║       │  At runtime: MAKE_FUNCTION wraps code object                    ║
║       ▼                                                                  ║
║  FUNCTION OBJECT (PyFunctionObject)                                      ║
║       │  func_code = the code object                                    ║
║       │  func_globals = module's global dict                            ║
║       │  func_closure = tuple of cell objects (if closure)              ║
║       │                                                                  ║
║       │  At call time: CALL creates frame                               ║
║       ▼                                                                  ║
║  FRAME (PyFrameObject / _PyInterpreterFrame)                             ║
║       │  f_code = code object                                           ║
║       │  f_locals = local variables (fast locals array)                  ║
║       │  f_globals = global dict                                        ║
║       │  f_builtins = builtins dict                                     ║
║       │  localsplus[] = locals + cell/free + stack                      ║
║       │                                                                  ║
║       │  Execution: ceval.c main loop                                   ║
║       ▼                                                                  ║
║  BYTECODE INTERPRETER (Python/ceval.c)                                   ║
║       │  Fetch opcode → dispatch → execute → next                       ║
║       │  Stack-based: push/pop PyObject* on operand stack               ║
║       │  Specialized: adaptive opcodes (3.11+)                          ║
║       ▼                                                                  ║
║  RESULT (return value: PyObject*)                                        ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  KEY OPCODES:                                                            ║
║    LOAD_FAST i        → push localsplus[i]                              ║
║    STORE_FAST i       → pop → localsplus[i]                             ║
║    LOAD_GLOBAL i      → push globals[co_names[i]]                       ║
║    LOAD_CONST i       → push co_consts[i]                               ║
║    CALL n             → call function with n args                        ║
║    RETURN_VALUE       → pop, return to caller                            ║
║    MAKE_FUNCTION      → create function from code object                 ║
║    BINARY_OP op       → pop 2, compute, push result                     ║
║    JUMP_IF_FALSE off  → conditional jump                                ║
║    FOR_ITER           → advance iterator or jump                        ║
║                                                                          ║
║  FUNCTION CALL PROTOCOL:                                                 ║
║    1. Evaluate callable + arguments                                     ║
║    2. CALL opcode invoked                                               ║
║    3. For Python functions:                                              ║
║       a. Create new frame (localsplus = locals + cells + stack)          ║
║       b. Bind arguments to local slots                                  ║
║       c. Push frame onto call stack                                     ║
║       d. Execute bytecode of callee                                     ║
║       e. RETURN_VALUE pops frame, pushes result to caller's stack       ║
║    4. For C functions: call the C function directly (no frame)          ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
```
