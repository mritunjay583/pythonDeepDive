# Part 3 — Shallow Copy

## 3.1 Definition

A **shallow copy** creates a NEW container object with its own identity, but the elements inside are SHARED (same references as the original).

```python
a = [1, [2, 3], {"x": 4}]
b = a.copy()  # Shallow copy

# NEW container:
a is b         # False — different list objects

# SHARED elements:
a[0] is b[0]   # True — same int object
a[1] is b[1]   # True — same inner list!
a[2] is b[2]   # True — same dict!
```

---

## 3.2 Methods That Create Shallow Copies

```python
# For lists:
b = a.copy()           # list.copy() method
b = a[:]               # full slice
b = list(a)            # constructor from iterable
b = [x for x in a]    # comprehension (slightly different — iterates)

# For dicts:
b = d.copy()           # dict.copy() method
b = dict(d)            # constructor
b = {**d}              # unpacking
b = {k: v for k, v in d.items()}  # comprehension

# For sets:
b = s.copy()           # set.copy() method
b = set(s)             # constructor

# Generic:
import copy
b = copy.copy(a)       # Works for any type
```

All produce the same result: new container, shared element references.

---

## 3.3 Memory Diagram

```python
a = [[1, 2], [3, 4], "hello"]
b = a.copy()
```

```
'a' ──→ List_A (refcnt=1)
         ob_item → [ptr0, ptr1, ptr2]
                     │      │      │
                     ▼      ▼      ▼
                  [1,2]  [3,4]  "hello"   ← SHARED objects
                     ↑      ↑      ↑         (refcnt increased by 1)
                     │      │      │
'b' ──→ List_B (refcnt=1)  ← NEW list object!
         ob_item → [ptr0, ptr1, ptr2]  ← NEW pointer array!
```

- List_A and List_B are different objects (different id, different refcnt)
- But they point to the SAME inner lists and string
- Inner list [1,2] has refcnt = 2 (from List_A[0] and List_B[0])

---

## 3.4 What's Independent vs Shared

### Independent (container-level operations):
```python
a = [[1, 2], [3, 4]]
b = a.copy()

b.append([5, 6])     # Only b grows
print(a)             # [[1, 2], [3, 4]] — a unchanged

b[0] = [99, 99]     # Replace b's pointer at index 0
print(a[0])          # [1, 2] — a's pointer unchanged
```

### Shared (element-level mutations):
```python
a = [[1, 2], [3, 4]]
b = a.copy()

b[0].append(99)      # Mutate the SHARED inner list!
print(a[0])          # [1, 2, 99] — a sees it! Same inner list!

b[1][0] = 999        # Mutate shared inner list
print(a[1])          # [999, 4] — a sees it!
```

**Rule**: Shallow copy gives independence for the **container** (add/remove/replace elements), but NOT for the **elements themselves** (if they're mutable).

---

## 3.5 When Shallow Copy Is Sufficient

Shallow copy is safe when elements are **immutable**:

```python
# Safe — integers are immutable:
a = [1, 2, 3, 4, 5]
b = a.copy()
b[0] = 99        # Replaces pointer, not mutation
print(a[0])      # 1 — unaffected

# Safe — strings are immutable:
a = ["hello", "world"]
b = a.copy()
b[0] = "goodbye"  # Rebinds b[0], doesn't mutate "hello"
print(a[0])       # "hello" — unaffected

# Safe — tuples are immutable:
a = [(1, 2), (3, 4)]
b = a.copy()
# Can't mutate tuples, so sharing is safe
```

Shallow copy is UNSAFE when elements are **mutable**:
```python
# Unsafe — inner lists are mutable:
a = [[1, 2], [3, 4]]
b = a.copy()
b[0].append(99)   # MUTATES shared inner list!
# Use deepcopy for nested mutables
```

---

## 3.6 Dict Shallow Copy

```python
original = {"name": "Alice", "scores": [90, 85, 92]}
copy_d = original.copy()

# Independent at top level:
copy_d["age"] = 30
print("age" in original)  # False — only in copy

# Shared mutable values:
copy_d["scores"].append(88)
print(original["scores"])  # [90, 85, 92, 88] — SHARED!
```

Dict `.copy()` copies the key-value pointer mapping, but values are shared references.

---

## 3.7 Internal Implementation

### list.copy() (C level):
```c
// Objects/listobject.c
static PyObject *
list_copy_impl(PyListObject *self) {
    return list_slice(self, 0, Py_SIZE(self));
    // Creates new list, copies all pointers, increfs each element
}
```

### dict.copy() (C level):
```c
// Objects/dictobject.c  
static PyObject *
dict_copy_impl(PyDictObject *self) {
    PyObject *copy = PyDict_New();
    // Insert each key-value pair (same key/value objects, incref'd)
    if (PyDict_Merge(copy, (PyObject *)self, 1) < 0) { ... }
    return copy;
}
```

### copy.copy() (Python level):
```python
# Lib/copy.py (simplified)
def copy(x):
    # 1. Try x.__copy__() if it exists
    copier = getattr(x, "__copy__", None)
    if copier is not None:
        return copier()
    
    # 2. Look up type in dispatch table
    cls = type(x)
    copier = _copy_dispatch.get(cls)
    if copier:
        return copier(x)
    
    # 3. Fall back to generic copy via __reduce__
    reductor = getattr(x, "__reduce_ex__", None)
    rv = reductor(4)
    return _reconstruct(x, None, *rv)
```

---

## 3.8 Performance

```python
import timeit

a = list(range(10000))

# Shallow copy methods — all roughly equivalent speed:
timeit.timeit(lambda: a.copy())       # ~50 μs
timeit.timeit(lambda: a[:])           # ~50 μs
timeit.timeit(lambda: list(a))        # ~55 μs (slightly more overhead)
timeit.timeit(lambda: copy.copy(a))   # ~60 μs (dispatch overhead)
```

Cost: O(n) — must copy n pointers and Py_INCREF each element.
Memory: O(n) — new pointer array of same size.

---

## 3.9 Interview Questions — Part 3

**Q1**: What does a shallow copy copy?
**A**: The container structure (new object, new internal array) but NOT the contained elements. Elements are shared between original and copy.

**Q2**: After `b = a.copy()` for a list of lists, does `b[0].append(x)` affect `a`?
**A**: Yes! `b[0]` and `a[0]` reference the same inner list. Mutating through either is visible through both.

**Q3**: Is `a[:]` the same as `a.copy()`?
**A**: For lists, yes — both create shallow copies. For other types, `[:]` may not be defined but `.copy()` is.

**Q4**: Why is shallow copy O(n)?
**A**: Must copy n pointers from old array to new array, and Py_INCREF each element (n reference count updates).

**Q5**: When is shallow copy sufficient?
**A**: When all elements are immutable (int, str, tuple, frozenset) or when you only need container-level independence.
