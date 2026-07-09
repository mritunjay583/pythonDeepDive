# Part 7 — Why PyVarObject Exists

## 7.1 The Limitation of Fixed-Size PyObject

Recall PyObject:
```c
typedef struct _object {
    Py_ssize_t ob_refcnt;
    PyTypeObject *ob_type;
} PyObject;
```

This 16-byte header tells the runtime:
- How many references point here (lifetime management)
- What type this is (dispatch)

But it does NOT tell:
- **How big is the object's data?**
- **How many elements does it contain?**

For fixed-size types (float, bool, None), this isn't a problem — the type itself encodes the size. A `float` is always `sizeof(PyFloatObject)`.

But for **variable-size** types (list, str, tuple, bytes, int), the object's size varies from instance to instance:

```python
"hi"       →  2 characters
"hello"    →  5 characters
"x" * 1000 → 1000 characters

[1, 2]     → 2 elements
[1]*10000  → 10000 elements
```

---

## 7.2 The Problem: How Does the Runtime Know the Size?

Consider what CPython needs to know for basic operations:

### `len()` Must Be Fast

```python
len(my_list)   # This MUST be O(1) — not O(n)!
```

If there's no stored size, `len()` would need to scan memory counting elements until hitting a sentinel — like C strings with '\0'. This would be:
- O(n) instead of O(1)
- Fragile (what if the data contains the sentinel value?)
- Incompatible with Python's semantics (arbitrary objects in containers)

### Memory Management Needs the Size

When freeing a variable-size object, the allocator needs to know how many bytes to free:
```c
// To dealloc a string, we need to know its length
// To dealloc a tuple, we need to know how many slots to DECREF
// To dealloc an int, we need to know how many digits it has
```

### Iteration Needs Bounds

```c
// Iterating over a tuple:
for (i = 0; i < ???; i++) {
    item = PyTuple_GET_ITEM(tuple, i);
    // How do we know when to stop?
}
```

---

## 7.3 Alternative Designs Considered

### Option A: Store Size in the Type Object

```c
// BAD: Type knows size
// But ALL lists would have the same size!
PyList_Type.tp_basicsize = ???  // Different for each list instance!
```

This doesn't work because the type is shared by ALL instances. A type can define `tp_basicsize` (the fixed part) and `tp_itemsize` (per-element cost), but the ACTUAL item count must live in the instance.

### Option B: Store Size in the Data Section

```c
typedef struct {
    PyObject ob_base;
    Py_ssize_t my_length;    // Each type defines its own size field
    // ... data ...
} SomeVarObject;
```

Problem: Every variable-size type would need its own length field at a different offset. The runtime couldn't generically ask "how many items?" without knowing the specific type layout.

### Option C: Add Size to the Common Header (Chosen!)

```c
typedef struct {
    PyObject ob_base;
    Py_ssize_t ob_size;      // ← Standard place for item count
} PyVarObject;
```

Benefits:
- Generic access: Any code can read `Py_SIZE(obj)` for any variable-size object
- Consistent offset: `ob_size` is always at offset 16 (after the 16-byte PyObject header)
- `len()` is always O(1): just read this field
- Memory management knows the data size without type-specific knowledge

---

## 7.4 The Design Decision

```
Fixed-size objects (float, bool, None):
┌──────────────────────────┐
│ ob_refcnt  (8 bytes)     │  ← PyObject header: 16 bytes
│ ob_type    (8 bytes)     │
├──────────────────────────┤
│ [fixed data]             │  ← Size known from type
└──────────────────────────┘


Variable-size objects (list, str, tuple, int, bytes):
┌──────────────────────────┐
│ ob_refcnt  (8 bytes)     │  ← PyVarObject header: 24 bytes
│ ob_type    (8 bytes)     │
│ ob_size    (8 bytes)     │  ← Number of items (variable!)
├──────────────────────────┤
│ [variable data]          │  ← Size = ob_size × tp_itemsize
└──────────────────────────┘
```

The extra 8 bytes per variable-size object is a small price for:
- O(1) `len()`
- Generic size access
- Simplified memory management
- Cleaner iteration bounds

---

## 7.5 What ob_size Actually Represents

`ob_size` does NOT always mean "number of Python objects inside." Its meaning varies:

| Type | ob_size means |
|------|--------------|
| `list` | NOT stored in ob_size (list uses its own `ob_size` in PyListObject... actually it uses `Py_SIZE`) |
| `tuple` | Number of elements |
| `str` (compact) | Length in characters |
| `bytes` | Number of bytes |
| `int` | Number of "digits" (30-bit chunks). **Negative** if the int is negative! |
| `code` | Number of bytecode instructions |

The sign trick for integers:
```python
# int(42)   → ob_size = 1  (one digit, positive)
# int(-42)  → ob_size = -1 (one digit, NEGATIVE)
# int(0)    → ob_size = 0  (zero digits)
# int(2**60)→ ob_size = 2  (two digits needed)
```

---

## 7.6 Why Not Give Every Object ob_size?

If `ob_size` is so useful, why not put it in ALL objects?

Answer: **memory efficiency**. Fixed-size objects would waste 8 bytes on a field that's always the same:

```
float → always 1 "item" (the double value)
bool  → always 0 or 1 (but size is always fixed at 28 bytes)  
None  → always 0 items
```

For these types, the size is implicit in `tp_basicsize` — no per-instance field needed. Given that there are millions of floats and small integers in a typical program, saving 8 bytes each adds up.

---

## 7.7 The Struct Embedding Relationship

```c
typedef struct _object {
    Py_ssize_t ob_refcnt;
    PyTypeObject *ob_type;
} PyObject;

typedef struct {
    PyObject ob_base;          // ← Embeds PyObject
    Py_ssize_t ob_size;
} PyVarObject;
```

Memory layout equivalence:
```
PyVarObject in memory:
Offset 0:   ob_refcnt   (from embedded PyObject)
Offset 8:   ob_type     (from embedded PyObject)
Offset 16:  ob_size     (PyVarObject's own field)
```

Because `ob_base` is the first field:
```c
PyVarObject *var_obj = ...;
PyObject *obj = (PyObject *)var_obj;   // SAFE! Same starting address
obj->ob_refcnt;  // Works — offset 0
obj->ob_type;    // Works — offset 8
```

This is "inheritance" via struct embedding — PyVarObject IS-A PyObject.

---

## 7.8 How the Runtime Distinguishes Fixed vs Variable

How does code know whether an object is PyObject-based or PyVarObject-based?

**Answer**: It's encoded in the TYPE, not the instance.

```c
// In the type object:
PyTypeObject PyFloat_Type = {
    .tp_basicsize = sizeof(PyFloatObject),
    .tp_itemsize = 0,           // ← ZERO means fixed-size (PyObject-based)
};

PyTypeObject PyTuple_Type = {
    .tp_basicsize = sizeof(PyTupleObject) - sizeof(PyObject *),
    .tp_itemsize = sizeof(PyObject *),  // ← NON-ZERO means variable (PyVarObject-based)
};
```

Rule:
- `tp_itemsize == 0` → Fixed-size type, uses PyObject header
- `tp_itemsize > 0` → Variable-size type, uses PyVarObject header

The total allocation size for a variable object:
```c
size_t alloc_size = tp_basicsize + (ob_size * tp_itemsize);
```

---

## 7.9 Source References

| File | Contents |
|------|----------|
| `Include/object.h` | PyVarObject definition, Py_SIZE macro |
| `Include/cpython/object.h` | PyTypeObject with tp_itemsize |
| `Objects/typeobject.c` | Size calculation during allocation |
| `Objects/tupleobject.c` | Example of variable-size object |
| `Objects/longobject.c` | Example where ob_size is signed (for negative ints) |

---

## 7.10 Interview Questions — Part 7

**Q1**: Why can't PyObject (with just ob_refcnt and ob_type) support variable-size objects?
**A**: PyObject has no field for the element count. Without it, operations like `len()` would be O(n), memory management wouldn't know how many bytes to free, and iteration wouldn't know where to stop.

**Q2**: Why not store the size in the type object?
**A**: The type is shared by ALL instances. `[1,2]` and `[1,2,3,4,5]` are both lists (same type), but have different sizes. Per-instance size must be stored in the instance.

**Q3**: Why not give EVERY object an ob_size field?
**A**: Memory efficiency. Fixed-size objects (float, bool, None) always have the same size — storing it per-instance wastes 8 bytes each. With millions of such objects, this adds up to significant memory.

**Q4**: What's the relationship between tp_itemsize and ob_size?
**A**: `tp_itemsize` (in the type) is the size in bytes of ONE item. `ob_size` (in the instance) is the number of items. Total data size = `ob_size × tp_itemsize`. If `tp_itemsize == 0`, it's a fixed-size type.

**Q5**: Why does Python's `int` type use a SIGNED ob_size?
**A**: The sign of `ob_size` encodes whether the integer is positive or negative. `ob_size = 2` means two digits, positive. `ob_size = -2` means two digits, negative. `ob_size = 0` means the integer is zero.

**Q6**: How can you cast a PyVarObject* to PyObject* safely?
**A**: Because PyVarObject's first field is `PyObject ob_base` — the first bytes of a PyVarObject ARE a PyObject. The C standard guarantees that a pointer to a struct can be cast to a pointer to its first member.

**Q7**: What's the total allocation size for a variable-size object?
**A**: `tp_basicsize + (ob_size × tp_itemsize)`. The basicsize covers the fixed header and any fixed fields, while the variable part is the item count times per-item size.
