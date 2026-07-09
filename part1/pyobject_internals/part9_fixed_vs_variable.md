# Part 9 — Fixed-Size vs Variable-Size Objects

## 9.1 The Classification Rule

Every Python type in CPython falls into one of two categories:

| Category | Header | tp_itemsize | Instance size |
|----------|--------|-------------|---------------|
| **Fixed-size** | PyObject (16 bytes) | 0 | Constant — same for ALL instances |
| **Variable-size** | PyVarObject (24 bytes) | > 0 | Varies — depends on content |

The rule is simple:
- If `tp_itemsize == 0` → fixed-size → uses PyObject header
- If `tp_itemsize > 0` → variable-size → uses PyVarObject header

---

## 9.2 Fixed-Size Types

These types have the same memory footprint regardless of their value:

### float

```c
typedef struct {
    PyObject ob_base;       // 16 bytes
    double ob_fval;         // 8 bytes
} PyFloatObject;            // ALWAYS 24 bytes
```

```
float(3.14) and float(999999.999999) → same size:
┌──────────────────────────┐
│ ob_refcnt    (8 bytes)   │
│ ob_type → PyFloat_Type   │
│ ob_fval = 3.14           │  (or 999999.999999)
└──────────────────────────┘
Total: 24 bytes — always, for ANY float value
```

`sys.getsizeof(3.14) == sys.getsizeof(1e308) == 24`

### bool

```c
// Bool is a subclass of int (PyLongObject), but True/False are singletons
// In practice: True and False are pre-allocated PyLongObjects
// sys.getsizeof(True) == 28 (same as small int)
```

Booleans are actually integers in CPython:
```python
>>> isinstance(True, int)
True
>>> True + True
2
```

### NoneType

```c
// The None singleton:
PyObject _Py_NoneStruct = {
    _Py_IMMORTAL_REFCNT,
    &_PyNone_Type
};
// JUST the header — 16 bytes. No additional data at all.
```

```
None in memory:
┌──────────────────────────┐
│ ob_refcnt = IMMORTAL     │  8 bytes
│ ob_type → NoneType       │  8 bytes
└──────────────────────────┘
Total: 16 bytes (minimum possible Python object)
```

### complex

```c
typedef struct {
    PyObject ob_base;       // 16 bytes
    Py_complex cval;        // 16 bytes (two doubles: real + imag)
} PyComplexObject;          // ALWAYS 32 bytes
```

### type (PyTypeObject itself)

Type objects are technically variable-size (they use PyVarObject_HEAD), but instances of user-defined classes are fixed-size. The type object describing a class has a fixed layout.

---

## 9.3 Variable-Size Types

These types have different memory footprints depending on their content:

### int (PyLongObject)

```c
// Include/cpython/longintrepr.h (simplified for clarity)
typedef struct {
    PyObject ob_base;       // 16 bytes
    Py_ssize_t ob_size;     // 8 bytes (number of digits × sign)
    digit ob_digit[1];      // Variable: |ob_size| × 4 bytes each
} PyLongObject;
```

Integers grow as needed:
```python
sys.getsizeof(0)         # 24 bytes (0 digits, just header)
sys.getsizeof(1)         # 28 bytes (1 digit = 4 bytes)
sys.getsizeof(2**30)     # 32 bytes (2 digits = 8 bytes)
sys.getsizeof(2**60)     # 36 bytes (3 digits)
sys.getsizeof(2**3000)   # 424 bytes (100+ digits)
```

```
int(42):
┌──────────────────────────┐
│ ob_refcnt    (8 bytes)   │
│ ob_type → PyLong_Type    │
│ ob_size = 1              │  (one digit, positive)
│ ob_digit[0] = 42        │  (4 bytes, 30-bit digit)
│ padding      (4 bytes)   │
└──────────────────────────┘
Total: 28 bytes (+ 4 padding = 32 aligned)

int(2**60):
┌──────────────────────────┐
│ ob_refcnt    (8 bytes)   │
│ ob_type → PyLong_Type    │
│ ob_size = 3              │  (three digits)
│ ob_digit[0]  (4 bytes)   │
│ ob_digit[1]  (4 bytes)   │
│ ob_digit[2]  (4 bytes)   │
│ padding      (4 bytes)   │
└──────────────────────────┘
Total: 40 bytes
```

### tuple

```c
typedef struct {
    PyObject_VAR_HEAD          // 24 bytes (includes ob_size)
    PyObject *ob_item[1];      // Variable: ob_size × 8 bytes
} PyTupleObject;
```

```python
sys.getsizeof(())          # 40 bytes (empty tuple)
sys.getsizeof((1,))        # 48 bytes (+8 per element)
sys.getsizeof((1, 2, 3))   # 64 bytes
```

### list (PyListObject)

```c
typedef struct {
    PyObject_VAR_HEAD          // 24 bytes
    PyObject **ob_item;        // 8 bytes (pointer to external array)
    Py_ssize_t allocated;      // 8 bytes (capacity)
} PyListObject;               // Fixed struct: 40 bytes
// BUT the ob_item array is variable-size (allocated separately)
```

Lists are interesting: the struct itself is fixed-size (40 bytes), but `ob_item` points to a separately-allocated array of pointers that grows/shrinks.

```python
sys.getsizeof([])           # 56 bytes (empty list, struct only)
sys.getsizeof([1])          # 64 bytes (+8 per slot)
sys.getsizeof([1, 2, 3])    # 80 bytes (may have over-allocation)
```

### str (PyUnicodeObject / Compact String)

```c
// Highly complex — multiple representations depending on content:
// - ASCII: 1 byte per character
// - Latin1: 1 byte per character  
// - UCS-2: 2 bytes per character
// - UCS-4: 4 bytes per character
```

```python
sys.getsizeof("")           # 49 bytes (empty string, header overhead)
sys.getsizeof("hello")     # 54 bytes (ASCII: 49 + 5)
sys.getsizeof("héllo")     # 55 bytes (Latin1: 50 + 5 maybe)
sys.getsizeof("日本語")      # 76 bytes (UCS-2 or UCS-4)
```

### bytes

```c
typedef struct {
    PyObject_VAR_HEAD          // 24 bytes
    Py_hash_t ob_shash;        // 8 bytes (cached hash)
    char ob_sval[1];           // Variable: ob_size bytes + 1 null terminator
} PyBytesObject;
```

```python
sys.getsizeof(b"")          # 33 bytes
sys.getsizeof(b"hello")     # 38 bytes (33 + 5)
```

### dict

```c
typedef struct {
    PyObject_HEAD              // 16 bytes (NOT PyVarObject!)
    Py_ssize_t ma_used;        // 8 bytes
    uint64_t ma_version_tag;   // 8 bytes
    PyDictKeysObject *ma_keys; // 8 bytes (pointer)
    PyObject **ma_values;      // 8 bytes (pointer)
} PyDictObject;               // Fixed struct, but keys/values arrays are variable
```

Note: Dict uses PyObject_HEAD (not VAR_HEAD) because its variable parts are in separate allocations pointed to by `ma_keys` and `ma_values`.

### set / frozenset

```c
typedef struct {
    PyObject_HEAD              // 16 bytes
    Py_ssize_t fill;           // 8 bytes
    Py_ssize_t used;           // 8 bytes
    Py_ssize_t mask;           // 8 bytes
    setentry *table;           // 8 bytes (pointer to hash table)
    Py_hash_t hash;            // 8 bytes
    Py_ssize_t finger;         // 8 bytes
    setentry smalltable[8];    // inline small table
    PyObject *weakreflist;     // 8 bytes
} PySetObject;
```

---

## 9.4 Complete Classification Table

### Fixed-Size (tp_itemsize == 0)

| Type | C Struct | Instance Size (64-bit) | Notes |
|------|----------|----------------------|-------|
| `float` | PyFloatObject | 24 bytes | Always same size |
| `complex` | PyComplexObject | 32 bytes | Two doubles |
| `bool` | (PyLongObject singleton) | 28 bytes | True/False are singletons |
| `NoneType` | PyObject | 16 bytes | Smallest possible object |
| `ellipsis` | PyObject | 16 bytes | `...` singleton |
| `NotImplementedType` | PyObject | 16 bytes | Singleton |
| `function` | PyFunctionObject | ~112 bytes | Many pointer fields |
| `module` | PyModuleObject | ~56 bytes | Fixed struct |
| `slice` | PySliceObject | 40 bytes | start/stop/step pointers |
| `dict` | PyDictObject | ~64 bytes | Separate key/value arrays |
| `set` | PySetObject | ~200 bytes | Inline small table |
| `list` | PyListObject | ~40-56 bytes | Separate item array |

**Note**: dict, set, and list appear here because their STRUCT is fixed — but they reference externally-allocated variable-size data. This is a design choice: indirection for mutability.

### Variable-Size (tp_itemsize > 0)

| Type | C Struct | tp_itemsize | ob_size meaning |
|------|----------|-------------|-----------------|
| `int` | PyLongObject | 4 (sizeof digit) | Number of digits × sign |
| `tuple` | PyTupleObject | 8 (sizeof pointer) | Number of elements |
| `bytes` | PyBytesObject | 1 (sizeof char) | Number of bytes |
| `str` | PyUnicodeObject | 1, 2, or 4 | Number of code points |
| `bytearray` | PyByteArrayObject | 1 | Allocated capacity |
| `type` | PyTypeObject | varies | (used for method tables) |

---

## 9.5 The Mutable/Immutable Dimension

Orthogonal to fixed/variable:

```
                    Fixed-Size Struct    Variable-Size (inline data)
                    ─────────────────    ──────────────────────────
Immutable:          float, bool,         tuple, str, bytes, int,
                    None, complex        frozenset

Mutable:            list*, dict*,        bytearray
                    set*, function,
                    module

* = fixed struct with pointer to separately-allocated mutable data
```

Key insight: Mutable types with variable data tend to use **indirection** (a pointer to a separate allocation). This allows the data to be reallocated (grown/shrunk) without moving the object itself.

Immutable types with variable data can store it **inline** (right after the header) because it never changes after creation.

---

## 9.6 Why This Classification Matters

### Memory Estimation

```python
import sys

# Fixed-size: predictable memory usage
floats_mem = n_floats * 24  # Exact (excluding allocator overhead)

# Variable-size: unpredictable
int_mem = ???  # Depends on the VALUE of each integer!
str_mem = ???  # Depends on length AND character content!
```

### Cache Behavior

Inline variable data (tuple, str, bytes) is contiguous with the header:
```
tuple (1, 2, 3):
[header|ptr0|ptr1|ptr2]  ← All in one cache line (or two)
```

Indirect variable data (list, dict) requires chasing a pointer:
```
list [1, 2, 3]:
[header|ptr_to_array|...]  → [ptr0|ptr1|ptr2]  ← Extra cache miss
```

### Copying Behavior

```python
import copy

# Immutable, variable, inline → no copy needed (share the object):
t = (1, 2, 3)
copy.copy(t) is t  # True! Tuples are immutable, just share.

# Mutable, indirect → must copy the pointed-to data:
l = [1, 2, 3]
copy.copy(l) is l  # False — new list struct AND new item array
```

---

## 9.7 Verifying with sys.getsizeof()

```python
import sys

# Fixed-size types — size doesn't change with value:
assert sys.getsizeof(1.0) == sys.getsizeof(1e308)  # Both 24
assert sys.getsizeof(True) == sys.getsizeof(False)  # Both 28
assert sys.getsizeof(None) == 16

# Variable-size types — size grows with content:
sizes = [sys.getsizeof(i) for i in [0, 1, 2**30, 2**60, 2**90]]
print(sizes)  # [24, 28, 32, 36, 40] — grows with magnitude!

print(sys.getsizeof(""))         # 49+ (base overhead)
print(sys.getsizeof("a" * 100))  # 149+ (grows linearly)

print(sys.getsizeof(()))         # 40 (empty tuple)
print(sys.getsizeof((1,)*100))   # 840 (grows linearly)
```

---

## 9.8 Source References

| File | Type Definition |
|------|----------------|
| `Include/cpython/floatobject.h` | PyFloatObject |
| `Include/cpython/longintrepr.h` | PyLongObject (int) |
| `Include/cpython/tupleobject.h` | PyTupleObject |
| `Include/cpython/bytesobject.h` | PyBytesObject |
| `Include/cpython/listobject.h` | PyListObject |
| `Include/cpython/dictobject.h` | PyDictObject |
| `Include/cpython/setobject.h` | PySetObject |
| `Include/cpython/unicodeobject.h` | PyUnicodeObject (str) |
| `Include/cpython/funcobject.h` | PyFunctionObject |

---

## 9.9 Interview Questions — Part 9

**Q1**: What determines if a CPython type uses PyObject or PyVarObject as its header?
**A**: The type's `tp_itemsize`. If it's 0, instances are fixed-size (PyObject header). If > 0, instances are variable-size (PyVarObject header with ob_size).

**Q2**: Why is Python's `int` variable-size while C's `int` is fixed?
**A**: Python integers have arbitrary precision — they can be any size. CPython stores them as arrays of 30-bit "digits." A small int needs 1 digit (4 bytes), but a 1000-bit integer needs ~34 digits (136 bytes). The ob_size field tracks how many digits are used.

**Q3**: Explain why `list` uses a fixed-size struct with a pointer to an external array rather than inline storage.
**A**: Lists are mutable — they grow and shrink. If data were inline, growing would require moving the entire object to a new address, breaking all existing references (id() would change, `is` checks would fail). Indirection allows realloc of the data array while the list object stays at the same address.

**Q4**: Why can tuples store data inline but lists cannot?
**A**: Tuples are immutable — once created, their size never changes. The data is allocated inline (after the header) at creation time and stays fixed. Lists must support append/insert/delete, requiring the data to be separately allocatable/resizable.

**Q5**: What's the minimum size of a Python object?
**A**: 16 bytes (on 64-bit) — just the PyObject header with no additional data. `None` achieves this minimum (it has no payload).

**Q6**: How does `sys.getsizeof(42)` differ from `sys.getsizeof(2**1000)`?
**A**: `42` fits in one 30-bit digit → 28 bytes. `2**1000` needs ~34 digits → 28 + (33 × 4) = ~160 bytes. The int grows because it stores more digits for larger values.

**Q7**: Is `dict` a PyVarObject-based type?
**A**: No — PyDictObject uses PyObject_HEAD (not VAR_HEAD). Its variable-size data (keys table, values array) is stored in separately-allocated structures pointed to by `ma_keys` and `ma_values`. The dict struct itself is fixed-size.
