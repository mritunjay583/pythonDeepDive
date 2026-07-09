# Objective

Act as a CPython core developer, compiler engineer, virtual machine architect, and computer science professor.

Create an advanced systems-programming-level document that teaches how Python functions work internally, how source code becomes bytecode, how bytecode is executed, and how function calls are implemented in CPython.

Assume I already understand:

* Python Object Model
* References
* Mutability
* Memory Management
* PyObject
* PyVarObject
* Lists
* Dictionaries
* Strings
* CPython Memory Allocator

Do not repeat previous topics except where necessary.

---

# Teaching Style

For every concept:

* Start from first principles.
* Explain the motivation.
* Explain naive implementations.
* Explain why CPython chose its design.
* Explain implementation details.
* Explain tradeoffs.
* Explain production implications.
* Explain interview questions.
* Draw detailed ASCII memory diagrams.
* Reference CPython source code.

Always distinguish:

* Python Language Semantics
* CPython Implementation

---

# Topics

## Part 1 — Function Objects

Explain:

* Why functions are objects
* Function creation
* Function identity
* Closures
* Nested functions
* Lambdas
* Callable objects
* functools.partial

Memory diagrams.

---

## Part 2 — Code Objects

Teach:

PyCodeObject

Explain every field:

* co_code
* co_consts
* co_names
* co_varnames
* co_cellvars
* co_freevars
* co_stacksize
* co_flags
* co_filename
* co_firstlineno

Explain why code objects are immutable.

---

## Part 3 — Compilation Pipeline

Explain:

Source Code

↓

Tokenizer

↓

Lexer

↓

Parser

↓

AST

↓

Compiler

↓

Bytecode

↓

Code Object

↓

PVM

Walk through every stage.

---

## Part 4 — Bytecode

Teach deeply.

Explain:

* Opcodes
* dis module
* Stack-based VM
* Operand stack
* Local variables
* Global variables
* Fast locals
* Adaptive bytecode (Python 3.11+)
* Inline caches
* Specialization

Walk through execution instruction by instruction.

---

## Part 5 — Function Calls

Explain:

* CALL opcode
* Frame creation
* Parameter binding
* Local namespace
* Return values
* Recursion
* Call stack

---

## Part 6 — Closures

Explain:

* Cell objects
* Free variables
* Closure memory layout
* LOAD_DEREF
* STORE_DEREF

---

## Part 7 — Decorators

Explain how decorators work internally.

No syntax-only explanations.

Translate decorators into actual function transformations.

---

## Part 8 — CPython Source

Walk through:

Objects/codeobject.c

Objects/funcobject.c

Python/compile.c

Python/ceval.c

Python/bytecodes.c

Explain important functions.

---

## Part 9 — Interview Questions

50 Beginner

50 Intermediate

50 Senior

100 bytecode prediction problems.

---

## Part 10 — Exercises

Memory tracing

Opcode tracing

Frame tracing

Manual bytecode interpretation

Compiler exercises
