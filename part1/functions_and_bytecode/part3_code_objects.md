# Part 3 — Code Objects

## 3.1 What Is a Code Object?

A **code object** (PyCodeObject) is the compiled, immutable representation of a block of Python code. It contains the bytecode, constants, variable names, and metadata — everything the interpreter needs to execute the code, EXCEPT runtime state (globals, closures, argument values).

```python
def add(x, y):
    return x + y

# The code object:
code = add.__code__
type(code)         # <class 'code'>
code.co_code       # b'\x97\x00|\x00|\x01z\x00\x00\x00S\x00' (bytecode bytes)
code.co_consts     # (None,)
code.co_varnames   # ('x', 'y')
code.co_argcount   # 2
```

---

## 3.2 PyCodeObject — Every Field

```c
// Include/cpython/code.h (simplified, Python 3.12+)
struct PyCodeObject {
    PyObject_HEAD
    
    // === Execution metadata ===
    int co_argcount;           // Number of positional-only + positional-or-keyword args
    int co_posonlyargcount;    // Number of positional-only args (PEP 570)
    int co_kwonlyargcount;     // Number of keyword-only args
    int co_nlocals;            // Total number of local variables (including args)
    int co_stacksize;          // Maximum operand stack depth needed
    int co_flags;              // Flags (CO_OPTIMIZED, CO_NEWLOCALS, CO_VARARGS, etc.)
    int co_firstlineno;        // First line number of the source code
    
    // === Bytecode ===
    PyObject *co_code;         // Bytecode instructions (bytes object)
    
    // === Constants and names ===
    PyObject *co_consts;       // Tuple of constants used in code
    PyObject *co_names;        // Tuple of names (globals, attributes)
    PyObject *co_varnames;     // Tuple of local variable names
    PyObject *co_cellvars;     // Tuple of cell variable names
    PyObject *co_freevars;     // Tuple of free variable names
    
    // === Source information ===
    PyObject *co_filename;     // Source file name (str)
    PyObject *co_name;         // Function/class name (str)
    PyObject *co_qualname;     // Qualified name (str)
    PyObject *co_linetable;    // Line number table (compressed mapping)
    PyObject *co_exceptiontable; // Exception handling table
    
    // === Internal / optimization ===
    _PyCoCached *_co_cached;   // Cached data for specialization
    uint32_t _co_firsttraceable; // First traceable instruction offset
    char *_co_linearray;       // Per-instruction line numbers
    int _co_nplaincellvars;    // Number of non-argument cell vars
    Py_ssize_t co_nfreevars;   // Precomputed len(co_freevars)
    Py_ssize_t co_ncellvars;   // Precomputed len(co_cellvars)
    // ...
};
```

---

## 3.3 Field Deep Dive

### `co_code` — The Bytecode

The actual machine instructions for the CPython virtual machine:
```python
import dis
def add(x, y):
    return x + y

dis.dis(add)
#  0 RESUME          0
#  2 LOAD_FAST       0 (x)
#  4 LOAD_FAST       1 (y)
#  6 BINARY_OP       0 (+)
# 10 RETURN_VALUE

add.__code__.co_code
# b'\x97\x00|\x00|\x01z\x00\x00\x00S\x00'
# Each instruction: 2 bytes (opcode + arg) in Python 3.6+
```

### `co_consts` — Constants

All literal values used in the function body:
```python
def example():
    x = 42
    y = "hello"
    z = (1, 2, 3)
    return None

example.__code__.co_consts
# (None, 42, 'hello', (1, 2, 3))
# None is always present (implicit return)
```

Nested code objects are also constants:
```python
def outer():
    def inner():
        pass
    return inner

outer.__code__.co_consts
# (None, <code object inner at 0x...>)
```

### `co_names` — Global/Attribute Names

Names resolved via LOAD_GLOBAL, LOAD_ATTR, STORE_GLOBAL:
```python
def example():
    print(len(x))     # 'print', 'len', 'x' are global names
    obj.method()       # 'obj' is global, 'method' is attribute name

example.__code__.co_names
# ('print', 'len', 'x', 'obj', 'method')
```

### `co_varnames` — Local Variable Names

Names of all local variables (including parameters):
```python
def add(x, y):
    result = x + y
    return result

add.__code__.co_varnames
# ('x', 'y', 'result')
# Parameters come first, then other locals
# Index in this tuple = LOAD_FAST/STORE_FAST operand!
```

### `co_cellvars` and `co_freevars`

```python
def outer(a):
    b = 10
    def inner(c):
        return a + b + c
    return inner

outer.__code__.co_cellvars   # ('a', 'b') — captured by inner
outer.__code__.co_freevars   # () — outer captures nothing

inner_code = outer.__code__.co_consts[1]
inner_code.co_cellvars       # ()
inner_code.co_freevars       # ('a', 'b') — captured from outer
```

### `co_stacksize` — Maximum Stack Depth

The compiler computes the maximum number of items that will be on the operand stack at any point during execution:
```python
def complex_expr():
    return a + b * c + d

# Stack at deepest point:
# LOAD a → [a]
# LOAD b → [a, b]
# LOAD c → [a, b, c]    ← depth 3!
# BINARY_MUL → [a, b*c]
# BINARY_ADD → [a+b*c]
# LOAD d → [a+b*c, d]   ← depth 2
# BINARY_ADD → [result]
# co_stacksize = 3
```

### `co_flags` — Behavior Flags

```python
CO_OPTIMIZED    = 0x0001  # Uses fast locals (LOAD_FAST/STORE_FAST)
CO_NEWLOCALS    = 0x0002  # Creates new local namespace (normal functions)
CO_VARARGS      = 0x0004  # Has *args parameter
CO_VARKEYWORDS  = 0x0008  # Has **kwargs parameter
CO_NESTED       = 0x0010  # Nested function (has free variables)
CO_GENERATOR    = 0x0020  # Generator function (has yield)
CO_NOFREE       = 0x0040  # No cell or free variables
CO_COROUTINE    = 0x0100  # Async coroutine (async def)
CO_ASYNC_GENERATOR = 0x0200  # Async generator
```

---

## 3.4 Why Code Objects Are Immutable

1. **Sharing**: Multiple function objects can share one code object (closures, re-execution of `def`)
2. **Security**: Modifying bytecode at runtime would be catastrophic
3. **Caching**: .pyc files cache code objects — they must be stable
4. **Optimization**: Compiler can make assumptions about immutability
5. **Thread safety**: Immutable objects don't need synchronization

```python
def factory():
    def f():
        return 42
    return f

a = factory()
b = factory()
a.__code__ is b.__code__  # True! Same immutable code object, different function objects
```

---

## 3.5 Inspecting Code Objects

```python
import dis, sys

def example(x, y, *args, key=None, **kwargs):
    """Docstring"""
    z = x + y
    for item in args:
        z += item
    return z

code = example.__code__

print(f"Name:        {code.co_name}")        # 'example'
print(f"Filename:    {code.co_filename}")     # '<...>'
print(f"Arg count:   {code.co_argcount}")     # 2 (x, y only)
print(f"KW-only:     {code.co_kwonlyargcount}") # 1 (key)
print(f"Locals:      {code.co_nlocals}")      # 6 (x,y,args,key,kwargs,z,item)
print(f"Stack size:  {code.co_stacksize}")    # depends on expression depth
print(f"Flags:       {code.co_flags:#06x}")   # CO_OPTIMIZED|CO_NEWLOCALS|CO_VARARGS|CO_VARKEYWORDS
print(f"Constants:   {code.co_consts}")       # (docstring, None, ...)
print(f"Varnames:    {code.co_varnames}")     # ('x','y','args','key','kwargs','z','item')
print(f"Names:       {code.co_names}")        # () (no globals accessed)

dis.dis(code)  # Full bytecode disassembly
```

---

## 3.6 Code Object Creation

Code objects are created by the compiler (Python/compile.c), NOT at runtime:

```
Source: "def add(x, y): return x + y"
         │
         │ [compile.c]
         ▼
AST for the function body
         │
         │ [compiler_function]
         ▼
Bytecode bytes: RESUME, LOAD_FAST 0, LOAD_FAST 1, BINARY_OP, RETURN_VALUE
         │
         │ [_PyCode_New]
         ▼
PyCodeObject {
    co_code = bytecode bytes,
    co_consts = (None,),
    co_varnames = ('x', 'y'),
    co_argcount = 2,
    ...
}
```

This PyCodeObject is then stored as a constant in the enclosing code object's `co_consts` tuple. At runtime, MAKE_FUNCTION pops it and wraps it in a PyFunctionObject.

---

## 3.7 Interview Questions — Part 3

**Q1**: What is a code object?
**A**: The immutable, compiled representation of a Python code block (function body, module, class body). Contains bytecode, constants, variable names, and metadata. Does NOT contain runtime state (globals, closures, argument values).

**Q2**: What's the difference between co_names and co_varnames?
**A**: co_varnames = local variables (accessed with LOAD_FAST/STORE_FAST). co_names = global/attribute names (accessed with LOAD_GLOBAL/LOAD_ATTR).

**Q3**: Why is the code object immutable?
**A**: Multiple function objects may share it, .pyc files cache it, the compiler relies on it not changing, and immutability provides thread safety.

**Q4**: Where are nested function code objects stored?
**A**: In the enclosing code object's co_consts tuple. `outer.__code__.co_consts` contains the inner function's code object.

**Q5**: What does co_stacksize represent?
**A**: The maximum number of items on the operand stack at any point during execution. The compiler statically determines this by analyzing all possible paths.

**Q6**: How are function parameters represented in the code object?
**A**: As the first entries in co_varnames. co_argcount tells how many are positional, co_kwonlyargcount tells keyword-only count, co_flags indicates *args (CO_VARARGS) and **kwargs (CO_VARKEYWORDS).
