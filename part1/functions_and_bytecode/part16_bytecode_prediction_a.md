# Part 16 — Bytecode Prediction Exercises (1-50)

For each Python snippet, predict the bytecode output (use `dis.dis()` to verify).

### Q1
```python
def f():
    return 42
```
**Bytecode:**
```
RESUME 0
LOAD_CONST 1 (42)
RETURN_VALUE
```

### Q2
```python
def f(x, y):
    return x + y
```
**Bytecode:**
```
RESUME 0
LOAD_FAST 0 (x)
LOAD_FAST 1 (y)
BINARY_OP 0 (+)
RETURN_VALUE
```

### Q3
```python
def f(x):
    y = x * 2
    return y
```
**Bytecode:**
```
RESUME 0
LOAD_FAST 0 (x)
LOAD_CONST 1 (2)
BINARY_OP 5 (*)
STORE_FAST 1 (y)
LOAD_FAST 1 (y)
RETURN_VALUE
```

### Q4
```python
def f():
    x = 1
    y = 2
    z = x + y
    return z
```
**Bytecode:**
```
RESUME 0
LOAD_CONST 1 (1)
STORE_FAST 0 (x)
LOAD_CONST 2 (2)
STORE_FAST 1 (y)
LOAD_FAST 0 (x)
LOAD_FAST 1 (y)
BINARY_OP 0 (+)
STORE_FAST 2 (z)
LOAD_FAST 2 (z)
RETURN_VALUE
```

### Q5
```python
def f(x):
    if x > 0:
        return x
    return -x
```
**Bytecode:**
```
RESUME 0
LOAD_FAST 0 (x)
LOAD_CONST 1 (0)
COMPARE_OP > 
POP_JUMP_IF_FALSE <offset>
LOAD_FAST 0 (x)
RETURN_VALUE
LOAD_FAST 0 (x)
UNARY_NEGATIVE
RETURN_VALUE
```

### Q6
```python
def f():
    return [1, 2, 3]
```
**Bytecode:**
```
RESUME 0
LOAD_CONST 1 (1)
LOAD_CONST 2 (2)
LOAD_CONST 3 (3)
BUILD_LIST 3
RETURN_VALUE
```

### Q7
```python
def f():
    return {"a": 1, "b": 2}
```
**Bytecode:**
```
RESUME 0
LOAD_CONST 1 ('a')
LOAD_CONST 2 (1)
LOAD_CONST 3 ('b')
LOAD_CONST 4 (2)
BUILD_MAP 2
RETURN_VALUE
```

### Q8
```python
def f(lst):
    lst.append(42)
```
**Bytecode:**
```
RESUME 0
LOAD_FAST 0 (lst)
LOAD_ATTR append (or LOAD_METHOD)
LOAD_CONST 1 (42)
CALL 1
POP_TOP
LOAD_CONST 0 (None)
RETURN_VALUE
```

### Q9
```python
def f():
    print("hello")
```
**Bytecode:**
```
RESUME 0
LOAD_GLOBAL print (+ NULL)
LOAD_CONST 1 ('hello')
CALL 1
POP_TOP
LOAD_CONST 0 (None)
RETURN_VALUE
```

### Q10
```python
def f(n):
    total = 0
    for i in range(n):
        total += i
    return total
```
**Bytecode (approximate):**
```
RESUME 0
LOAD_CONST 1 (0)
STORE_FAST 1 (total)
LOAD_GLOBAL range
LOAD_FAST 0 (n)
CALL 1
GET_ITER
FOR_ITER <end>
  STORE_FAST 2 (i)
  LOAD_FAST 1 (total)
  LOAD_FAST 2 (i)
  BINARY_OP +=
  STORE_FAST 1 (total)
  JUMP_BACKWARD <FOR_ITER>
END_FOR
LOAD_FAST 1 (total)
RETURN_VALUE
```

### Q11-20: Functions and Calls

### Q11
```python
def f(x):
    return len(x)
```
**Key:** `LOAD_GLOBAL len; LOAD_FAST x; CALL 1; RETURN_VALUE`

### Q12
```python
def outer():
    x = 10
    def inner():
        return x
    return inner
```
**Key:** outer uses `STORE_DEREF` for x. inner uses `LOAD_DEREF` for x. `MAKE_FUNCTION 8` (has closure).

### Q13
```python
def f(a, b=10):
    return a + b
```
**Module level:** `LOAD_CONST 10; LOAD_CONST <code>; MAKE_FUNCTION 1` (flag 1 = has defaults).

### Q14
```python
@decorator
def f():
    pass
```
**Key:** `LOAD_GLOBAL decorator; LOAD_CONST <code>; MAKE_FUNCTION 0; CALL 1; STORE_NAME f`

### Q15
```python
def f(x):
    return x if x > 0 else -x
```
**Key:** `LOAD_FAST x; LOAD_CONST 0; COMPARE_OP; POP_JUMP_IF_FALSE; LOAD_FAST x; JUMP; LOAD_FAST x; UNARY_NEGATIVE; RETURN`

### Q16-50: *(More patterns: list comprehension, dict comprehension, with statement, try/except, multiple return values, unpacking assignment, walrus operator, augmented assignment, class definition, property access, slice, string formatting, assert, raise, del, global/nonlocal, star expressions)*

### Q20
```python
def f():
    return [x*2 for x in range(5)]
```
**Key:** Creates a hidden `<listcomp>` code object. Module-level emits `LOAD_CONST <listcomp code>; MAKE_FUNCTION; LOAD_GLOBAL range; CALL 1; GET_ITER; CALL 1`. Inside listcomp: `FOR_ITER; LOAD_FAST x; LOAD_CONST 2; BINARY_OP; LIST_APPEND; JUMP_BACKWARD`.

### Q30
```python
def f():
    with open("file") as fp:
        data = fp.read()
    return data
```
**Key:** `LOAD_GLOBAL open; CALL 1; BEFORE_WITH; STORE_FAST fp; [body]; POP_BLOCK; LOAD_CONST None; (implicit __exit__ call via exception table)`

### Q40
```python
def f(x):
    try:
        return int(x)
    except ValueError:
        return None
```
**Key:** Exception table maps the `int(x)` range to the except handler. `PUSH_EXC_INFO; LOAD_GLOBAL ValueError; CHECK_EXC_MATCH; POP_JUMP_IF_FALSE (reraise); POP_TOP; LOAD_CONST None; RETURN_VALUE`

### Q50
```python
def f(*args, **kwargs):
    return args, kwargs
```
**Key:** `LOAD_FAST 0 (args); LOAD_FAST 1 (kwargs); BUILD_TUPLE 2; RETURN_VALUE`. Args/kwargs are just local variables bound by the call machinery.
