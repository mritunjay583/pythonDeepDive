# Part 17 — Bytecode Prediction Exercises (51-100)

### Q51: Closure capture
```python
def outer(x):
    def inner():
        return x
    return inner
```
**Key bytecode for outer:**
```
MAKE_CELL 0 (x)
RESUME 0
LOAD_FAST 0 (x)       # Initially stored in cell
STORE_DEREF 0 (x)     # (depends on version — may be implicit)
LOAD_CLOSURE 0 (x)    # Push cell object
BUILD_TUPLE 1          # (cell,) for closure
LOAD_CONST 1 (<code inner>)
MAKE_FUNCTION 8        # 8 = has closure
STORE_FAST 1 (inner)
LOAD_FAST 1 (inner)
RETURN_VALUE
```
**Key bytecode for inner:** `LOAD_DEREF 0 (x); RETURN_VALUE`

### Q52: Multiple assignment
```python
def f():
    a = b = 42
```
**Bytecode:** `LOAD_CONST 42; COPY 1; STORE_FAST 0 (a); STORE_FAST 1 (b)`
(COPY duplicates TOS)

### Q53: Augmented assignment
```python
def f(x):
    x += 1
    return x
```
**Bytecode:** `LOAD_FAST x; LOAD_CONST 1; BINARY_OP +=; STORE_FAST x; LOAD_FAST x; RETURN_VALUE`

### Q54: Tuple unpacking
```python
def f():
    a, b, c = 1, 2, 3
```
**Bytecode:** `LOAD_CONST (1,2,3); UNPACK_SEQUENCE 3; STORE_FAST a; STORE_FAST b; STORE_FAST c`

### Q55: Star unpacking
```python
def f():
    a, *b, c = [1, 2, 3, 4, 5]
```
**Bytecode:** `LOAD_CONST [1,2,3,4,5]; UNPACK_EX 1_1; STORE_FAST a; STORE_FAST b; STORE_FAST c`
(UNPACK_EX: before_star=1, after_star=1)

### Q56: f-string
```python
def f(name):
    return f"Hello, {name}!"
```
**Bytecode:**
```
LOAD_CONST "Hello, "
LOAD_FAST name
FORMAT_VALUE 0
LOAD_CONST "!"
BUILD_STRING 3
RETURN_VALUE
```

### Q57: Walrus operator
```python
def f(data):
    if (n := len(data)) > 10:
        return n
```
**Bytecode:**
```
LOAD_GLOBAL len
LOAD_FAST data
CALL 1
COPY 1          # duplicate for comparison AND assignment
STORE_FAST n    # n := result
LOAD_CONST 10
COMPARE_OP >
POP_JUMP_IF_FALSE ...
LOAD_FAST n
RETURN_VALUE
```

### Q58: Assert statement
```python
def f(x):
    assert x > 0, "must be positive"
```
**Bytecode (when __debug__ is True):**
```
LOAD_FAST x
LOAD_CONST 0
COMPARE_OP >
POP_JUMP_IF_TRUE <skip>
LOAD_ASSERTION_ERROR
LOAD_CONST "must be positive"
CALL 1
RAISE_VARARGS 1
```
(With `-O` flag: assert is completely removed!)

### Q59: del statement
```python
def f():
    x = 42
    del x
```
**Bytecode:** `LOAD_CONST 42; STORE_FAST x; DELETE_FAST x` (sets localsplus[x] = NULL)

### Q60: global declaration
```python
x = 0
def f():
    global x
    x = 42
```
**f's bytecode:** `LOAD_CONST 42; STORE_GLOBAL x` (NOT STORE_FAST!)

### Q61: nonlocal
```python
def outer():
    x = 0
    def inner():
        nonlocal x
        x = 1
    inner()
    return x
```
**inner's bytecode:** `LOAD_CONST 1; STORE_DEREF x` (writes to shared cell)
**outer after inner():** `LOAD_DEREF x` reads `1` from the cell.

### Q62: Class definition
```python
class Foo:
    x = 42
```
**Bytecode:**
```
LOAD_BUILD_CLASS
LOAD_CONST <code object Foo>
MAKE_FUNCTION 0
LOAD_CONST 'Foo'
CALL 2                    # __build_class__(func, 'Foo')
STORE_NAME Foo
```

### Q63: Property access
```python
def f(obj):
    return obj.name
```
**Bytecode:** `LOAD_FAST obj; LOAD_ATTR name; RETURN_VALUE`

### Q64: Attribute assignment
```python
def f(obj, val):
    obj.x = val
```
**Bytecode:** `LOAD_FAST val; LOAD_FAST obj; STORE_ATTR x`
(Note: value pushed FIRST, then object — STORE_ATTR pops both)

### Q65: Subscript access
```python
def f(lst, i):
    return lst[i]
```
**Bytecode:** `LOAD_FAST lst; LOAD_FAST i; BINARY_SUBSCR; RETURN_VALUE`

### Q66: Subscript assignment
```python
def f(lst, i, val):
    lst[i] = val
```
**Bytecode:** `LOAD_FAST val; LOAD_FAST lst; LOAD_FAST i; STORE_SUBSCR`

### Q67: Slice
```python
def f(lst):
    return lst[1:3]
```
**Bytecode:** `LOAD_FAST lst; LOAD_CONST 1; LOAD_CONST 3; BUILD_SLICE 2; BINARY_SUBSCR; RETURN_VALUE`

### Q68: Dict comprehension
```python
def f(data):
    return {k: v for k, v in data.items()}
```
**Key:** Creates `<dictcomp>` code object. Inside uses `MAP_ADD` opcode.

### Q69: Generator function
```python
def gen(n):
    for i in range(n):
        yield i
```
**Key:** co_flags has CO_GENERATOR. Body has YIELD_VALUE opcode. Calling gen(5) returns a generator object (doesn't execute body).

### Q70: Lambda in list
```python
funcs = [lambda x: x + i for i in range(3)]
```
**Key:** MAKE_FUNCTION inside FOR_ITER loop. All lambdas share same LOAD_DEREF for `i` (the closure trap!).

### Q71-100: *(Additional patterns: async def, await, async for, async with, match/case statements, type annotations, dataclass creation, super(), __init__ bytecode, method resolution, multiple inheritance, exception chaining, finally cleanup, context manager protocol, generator.send(), generator.throw(), yield from, walrus in comprehensions, nested comprehensions, conditional imports, __all__ and import *, exec/eval bytecode.)*
