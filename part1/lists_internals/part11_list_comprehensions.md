# Part 11 — List Comprehensions

## 11.1 What Makes Comprehensions Special Internally

List comprehensions aren't just syntactic sugar for a for-loop with append. CPython generates **specialized bytecode** that bypasses the normal `list.append` method dispatch.

```python
# These produce the same result but execute differently:

# Loop version:
result = []
for i in range(1000):
    result.append(i * 2)

# Comprehension version:
result = [i * 2 for i in range(1000)]
```

---

## 11.2 Bytecode Comparison

### Loop with append:
```python
import dis

def loop_version():
    result = []
    for i in range(5):
        result.append(i * 2)
    return result

dis.dis(loop_version)
```

```
  # Build empty list
  BUILD_LIST          0
  STORE_FAST          0 (result)
  
  # Set up loop
  LOAD_GLOBAL         0 (range)
  LOAD_CONST          1 (5)
  CALL_FUNCTION       1
  GET_ITER
  FOR_ITER            ...
  STORE_FAST          1 (i)
  
  # Method call: result.append(i * 2)
  LOAD_FAST           0 (result)
  LOAD_ATTR           1 (append)    ← attribute lookup!
  LOAD_FAST           1 (i)
  LOAD_CONST          2 (2)
  BINARY_MULTIPLY
  CALL_FUNCTION       1              ← function call overhead!
  POP_TOP
  JUMP_ABSOLUTE       ...
  
  LOAD_FAST           0 (result)
  RETURN_VALUE
```

### List comprehension:
```python
def comp_version():
    return [i * 2 for i in range(5)]

dis.dis(comp_version)
```

```
  # The comprehension compiles to a separate code object
  LOAD_CONST          1 (<code object <listcomp>>)
  MAKE_FUNCTION       0
  LOAD_GLOBAL         0 (range)
  LOAD_CONST          2 (5)
  CALL_FUNCTION       1
  GET_ITER
  CALL_FUNCTION       1
  RETURN_VALUE
```

Inside the `<listcomp>` code object:
```
  BUILD_LIST          0
  LOAD_FAST           0 (.0)    ← the iterator
  FOR_ITER            ...
  STORE_FAST          1 (i)
  LOAD_FAST           1 (i)
  LOAD_CONST          0 (2)
  BINARY_MULTIPLY
  LIST_APPEND         2          ← DIRECT list append bytecode!
  JUMP_ABSOLUTE       ...
  RETURN_VALUE
```

---

## 11.3 The Key Difference: LIST_APPEND

The `LIST_APPEND` bytecode instruction directly calls the C function to append, bypassing:
1. **Attribute lookup** (`LOAD_ATTR 'append'`) — dictionary lookup on the list type
2. **Method object creation** — creating a bound method object
3. **CALL_FUNCTION overhead** — Python function call protocol
4. **Argument handling** — packing/unpacking function arguments

```c
// What LIST_APPEND does (ceval.c):
case TARGET(LIST_APPEND): {
    PyObject *v = POP();
    PyObject *list = PEEK(oparg);
    int err = PyList_Append(list, v);  // Direct C call
    Py_DECREF(v);
    if (err != 0) goto error;
    DISPATCH();
}
```

Compared to `result.append(x)` which goes through:
1. `LOAD_FAST` (result)
2. `LOAD_ATTR` (append) → type dictionary lookup → bound method creation
3. `CALL_FUNCTION` → argument parsing → PyList_Append → cleanup

---

## 11.4 Memory Allocation Strategy

### Loop with append:
- Starts with `allocated = 0`
- Triggers overallocation at each growth: 0→4→8→16→24→32→...
- For 1000 items: ~15 reallocations

### Comprehension (CPython 3.9+):
- CPython can sometimes determine the size from the iterator
- For `range(n)`, the length hint is available
- `BUILD_LIST` with known size can pre-allocate

Actually, the comprehension still uses `LIST_APPEND` which triggers normal growth. BUT:
- `__length_hint__()` protocol allows pre-sizing in some cases
- When the iterable has a known length, CPython may pre-allocate

For `range(n)`:
```c
// CPython can query: len_hint = PyObject_LengthHint(iterable, 8)
// This returns n for range(n), allowing pre-allocation
```

In practice, comprehensions still grow dynamically but with less overhead per operation.

---

## 11.5 Performance Measurement

```python
import timeit

n = 10000

# Method 1: Loop with append
t1 = timeit.timeit('''
result = []
for i in range(10000):
    result.append(i * 2)
''', number=1000)

# Method 2: List comprehension
t2 = timeit.timeit('[i * 2 for i in range(10000)]', number=1000)

# Method 3: map()
t3 = timeit.timeit('list(map(lambda i: i * 2, range(10000)))', number=1000)

# Typical results:
# Loop:           ~1.0s (baseline)
# Comprehension:  ~0.6s (40% faster)
# map+lambda:     ~0.9s (slightly faster than loop, lambda has overhead)
```

Why comprehensions win:
1. No `LOAD_ATTR` for `append` — saves dictionary lookup per iteration
2. No `CALL_FUNCTION` — saves function call setup/teardown per iteration
3. `LIST_APPEND` is a single C function call with minimal overhead
4. The comprehension runs in its own local scope (faster variable access in CPython)

---

## 11.6 Comprehension Scope

Since Python 3.x, list comprehensions have their own scope:

```python
x = 10
result = [x for x in range(5)]
print(x)  # 10 — x in comprehension doesn't leak!
```

This means:
- The comprehension creates a temporary function/code object
- Variables inside (like `x`) are local to that scope
- The enclosing scope is not polluted
- Slight overhead for scope creation (negligible for non-trivial iterations)

In Python 2, comprehension variables leaked into the enclosing scope (a design mistake).

---

## 11.7 Nested Comprehensions

```python
# Flatten a matrix
matrix = [[1,2,3], [4,5,6], [7,8,9]]
flat = [x for row in matrix for x in row]
# flat = [1, 2, 3, 4, 5, 6, 7, 8, 9]
```

Bytecode for nested comprehension is still `LIST_APPEND` based — it's nested loops with the same optimization, not nested comprehension objects.

---

## 11.8 Generator Expression Comparison

```python
# List comprehension: creates full list in memory
squares = [x**2 for x in range(1000000)]  # ~8MB in memory

# Generator expression: lazy, one item at a time
squares_gen = (x**2 for x in range(1000000))  # ~120 bytes!
```

Memory comparison:
```
List comprehension:
- Allocates list + pointer array + all result objects upfront
- [x**2 for x in range(n)] → O(n) memory immediately

Generator expression:
- Creates generator object (~120 bytes)
- Produces one item at a time on demand
- O(1) memory (excluding what the consumer stores)
```

When to use each:
- **Comprehension**: need random access, multiple iterations, or the full list
- **Generator**: single pass, huge data, or feeding into another function like `sum()`

```python
# Good: generator feeds directly into sum, no list created
total = sum(x**2 for x in range(1000000))

# Wasteful: creates temporary list just to sum it
total = sum([x**2 for x in range(1000000)])
```

---

## 11.9 Conditional Comprehensions

```python
# Filter:
evens = [x for x in range(100) if x % 2 == 0]

# Transform + filter:
result = [x**2 for x in range(100) if x % 2 == 0]
```

The `if` clause adds a conditional jump in bytecode but doesn't change the fundamental LIST_APPEND optimization:

```
FOR_ITER
STORE_FAST (x)
LOAD_FAST (x)
LOAD_CONST (2)
BINARY_MODULO
LOAD_CONST (0)
COMPARE_OP (==)
POP_JUMP_IF_FALSE    ← skip LIST_APPEND if condition false
... compute x**2 ...
LIST_APPEND
JUMP_ABSOLUTE
```

---

## 11.10 dict/set Comprehensions (Comparison)

```python
# Dict comprehension — uses MAP_ADD bytecode
d = {k: v for k, v in pairs}

# Set comprehension — uses SET_ADD bytecode
s = {x**2 for x in range(10)}
```

Same principle: specialized bytecode instructions bypass method lookup overhead.

---

## 11.11 When NOT to Use Comprehensions

1. **Complex logic**: If the body is more than one expression, a loop is clearer
2. **Side effects**: Comprehensions should produce values, not perform actions
3. **Very large results you don't need all at once**: Use a generator instead
4. **Debugging**: Harder to step through than a loop

```python
# BAD: side effect in comprehension (unclear intent)
[print(x) for x in data]

# GOOD: explicit loop for side effects
for x in data:
    print(x)
```

---

## 11.12 Interview Questions — Part 11

**Q1**: Why are list comprehensions faster than equivalent loops with append?
**A**: Comprehensions use the `LIST_APPEND` bytecode which directly calls PyList_Append in C, avoiding: (1) attribute lookup of `.append`, (2) bound method creation, (3) Python function call overhead per iteration.

**Q2**: Do list comprehensions pre-allocate the result list?
**A**: Not always. They start empty and grow using the normal dynamic array growth. However, CPython may use `__length_hint__()` to pre-size when the iterator's length is known.

**Q3**: What's the memory difference between `[x for x in big_iter]` and `(x for x in big_iter)`?
**A**: The list comprehension materializes all results in memory immediately (O(n)). The generator expression creates only a small generator object (~120 bytes) and produces items lazily on demand (O(1) memory).

**Q4**: Do comprehension variables leak into the enclosing scope?
**A**: Not in Python 3. Comprehensions have their own scope. In Python 2, the iteration variable leaked (design bug fixed in Python 3).

**Q5**: Is `list(x for x in range(n))` the same as `[x for x in range(n)]`?
**A**: Semantically yes (same result). Performance: the comprehension is faster because `list(gen)` has generator protocol overhead (calling `__next__` repeatedly). The comprehension uses `LIST_APPEND` directly.
