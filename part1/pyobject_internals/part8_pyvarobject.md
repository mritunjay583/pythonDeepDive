# Part 8 — PyVarObject: The Variable-Size Object Header

## 8.1 The Struct Definition

```c
// Include/object.h
typedef struct {
    PyObject ob_base;       // Embeds: ob_refcnt + ob_type (16 bytes)
    Py_ssize_t ob_size;     // Number of items (8 bytes)
} PyVarObject;
```

Expanded (what the compiler actually sees):
```c
typedef struct {
    Py_ssize_t ob_refcnt;       // 8 bytes at offset 0
    PyTypeObject *ob_type;      // 8 bytes at offset 8
    Py_ssize_t ob_size;         // 8 bytes at offset 16
} PyVarObject;                  // Total: 24 bytes
```

---

## 8.2 Memory Layout

```
PyVarObject in memory (64-bit system):

Address       Offset    Field         Type              Size
─────────────────────────────────────────────────────────────
base+0x00     +0        ob_refcnt     Py_ssize_t        8 bytes
base+0x08     +8        ob_type       PyTypeObject*     8 bytes
base+0x10     +16       ob_size       Py_ssize_t        8 bytes
─────────────────────────────────────────────────────────────
                                      TOTAL HEADER:     24 bytes
```

After this 24-byte header comes the type-specific variable-length data:

```
Complete variable-size object:
┌────────────────────────────────────────────────────────┐
│ PyVarObject Header (24 bytes)                           │
│ ┌──────────────────────────────────────────────────┐   │
│ │ ob_refcnt   [8 bytes]                            │   │
│ │ ob_type     [8 bytes] → type object              │   │
│ │ ob_size     [8 bytes] = N (item count)           │   │
│ └──────────────────────────────────────────────────┘   │
├────────────────────────────────────────────────────────┤
│ Variable-length data (N × tp_itemsize bytes)            │
│ ┌──────────────────────────────────────────────────┐   │
│ │ item[0]                                          │   │
│ │ item[1]                                          │   │
│ │ ...                                              │   │
│ │ item[N-1]                                        │   │
│ └──────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────┘
```

---

## 8.3 The ob_size Field in Detail

### Type: Py_ssize_t

```c
// Py_ssize_t is signed:
// - 64-bit on 64-bit platforms: range [-2^63, 2^63 - 1]
// - 32-bit on 32-bit platforms: range [-2^31, 2^31 - 1]
```

### Why Signed?

Two reasons:

1. **CPython's `int` type uses the sign to encode the integer's sign**:
```c
// int(42):  ob_size =  1  (one digit, positive number)
// int(-42): ob_size = -1  (one digit, negative number)
// int(0):   ob_size =  0  (zero digits)
// int(2^60): ob_size = 2  (two 30-bit digits, positive)
```

2. **Error detection**: A negative ob_size (for types that don't use sign encoding) indicates corruption.

### What ob_size Means for Each Type

| Type | ob_size represents | Example |
|------|-------------------|---------|
| `tuple` | Number of elements | `(1,2,3)` → ob_size = 3 |
| `bytes` | Number of bytes | `b"hello"` → ob_size = 5 |
| `int` | Number of digits × sign | `42` → 1, `-42` → -1, `0` → 0 |
| `str` (compact) | Number of code points | `"abc"` → ob_size = 3 |
| `list` | Number of elements | `[1,2]` → ob_size = 2 |
| `code` | (varies by version) | Implementation-specific |

---

## 8.4 How len() Is O(1)

When Python code calls `len(obj)`, here's the complete path:

```python
len(my_tuple)  # → instant O(1) answer
```

```c
// Python/bltinmodule.c
static PyObject *
builtin_len(PyObject *module, PyObject *obj) {
    Py_ssize_t res = PyObject_Size(obj);
    return PyLong_FromSsize_t(res);
}

// Objects/abstract.c
Py_ssize_t PyObject_Size(PyObject *o) {
    PySequenceMethods *m = Py_TYPE(o)->tp_as_sequence;
    if (m && m->sq_length) {
        return m->sq_length(o);      // Call type's length function
    }
    // ... try mapping protocol ...
}

// For tuple — Objects/tupleobject.c:
static Py_ssize_t
tuple_length(PyObject *self) {
    return Py_SIZE(self);   // Just read ob_size! O(1)!
}
```

The complete call chain:
```
len(x)
  → builtin_len()
    → PyObject_Size()
      → Py_TYPE(x)->tp_as_sequence->sq_length(x)
        → tuple_length(x)  [or list_length, etc.]
          → Py_SIZE(x)
            → ((PyVarObject*)(x))->ob_size
              → Read 8 bytes at offset 16. Done.
```

Total work: a few function calls + one memory read. **O(1)**.

Compare with C strings:
```c
// C's strlen() is O(n) — must scan for '\0':
size_t strlen(const char *s) {
    size_t len = 0;
    while (*s++) len++;  // O(n) scan!
    return len;
}
```

---

## 8.5 The PyObject_VAR_HEAD Macro

```c
// Include/object.h
#define PyObject_VAR_HEAD  PyVarObject ob_base;
```

Used in type definitions:
```c
// Objects/tupleobject.c
typedef struct {
    PyObject_VAR_HEAD              // → PyVarObject ob_base; (24 bytes)
    PyObject *ob_item[1];          // Variable-length array of pointers
} PyTupleObject;

// Expanded:
typedef struct {
    Py_ssize_t ob_refcnt;          // +0: from PyObject
    PyTypeObject *ob_type;         // +8: from PyObject
    Py_ssize_t ob_size;            // +16: from PyVarObject
    PyObject *ob_item[1];          // +24: tuple's own data (flexible array)
} PyTupleObject;
```

The `[1]` is a C89 "struct hack" (modern C uses `[]` flexible array member). The actual allocation provides space for `ob_size` pointers.

---

## 8.6 The Py_SIZE Macro

```c
// Include/object.h
static inline Py_ssize_t Py_SIZE(PyObject *ob) {
    return _PyVarObject_CAST(ob)->ob_size;
}

#define _PyVarObject_CAST(op) ((PyVarObject *)(op))
```

This macro:
1. Casts any `PyObject*` to `PyVarObject*`
2. Reads the `ob_size` field at offset 16
3. Returns it as `Py_ssize_t`

**Note**: Only valid for actual PyVarObject-based types. Calling `Py_SIZE` on a float would read garbage (the float's data misinterpreted as a size).

---

## 8.7 The PyVarObject_HEAD_INIT Macro

Used when statically defining type objects:

```c
#define PyVarObject_HEAD_INIT(type, size) \
    { PyObject_HEAD_INIT(type) (size) },

// PyObject_HEAD_INIT expands to set ob_refcnt and ob_type:
#define PyObject_HEAD_INIT(type) \
    { _Py_IMMORTAL_REFCNT, (type) },
```

Usage in type definitions:
```c
PyTypeObject PyTuple_Type = {
    PyVarObject_HEAD_INIT(&PyType_Type, 0)
    //                    ^^^^^^^^^^^^  ^
    //                    ob_type       ob_size (type objects have size 0)
    "tuple",                             // tp_name
    sizeof(PyTupleObject),               // tp_basicsize
    sizeof(PyObject *),                  // tp_itemsize
    // ...
};
```

---

## 8.8 Allocation of Variable-Size Objects

When CPython creates a variable-size object, it calculates the total allocation:

```c
// Objects/tupleobject.c (simplified)
PyObject *PyTuple_New(Py_ssize_t size) {
    PyTupleObject *op;
    // Total bytes = base struct + (N items × pointer size)
    Py_ssize_t nbytes = size * sizeof(PyObject *);
    op = PyObject_GC_NewVar(PyTupleObject, &PyTuple_Type, size);
    // PyObject_GC_NewVar:
    //   1. Allocates tp_basicsize + size * tp_itemsize bytes
    //   2. Sets ob_refcnt = 1
    //   3. Sets ob_type = &PyTuple_Type
    //   4. Sets ob_size = size
    //   5. Registers with GC
    return (PyObject *)op;
}
```

```
Allocation for tuple (1, 2, 3):

tp_basicsize = sizeof(PyTupleObject) = 24 + 8 = 32 bytes (header + one pointer)
tp_itemsize = sizeof(PyObject *) = 8 bytes
ob_size = 3

Total allocated = tp_basicsize + (3 - 1) * tp_itemsize
                = 32 + 16 = 48 bytes
  (The -1 because tp_basicsize already includes space for ob_item[1])

Actually in modern CPython: 
Total = sizeof(PyTupleObject) + (size - 1) * sizeof(PyObject*)
      = 32 + 2*8 = 48 bytes for a 3-element tuple

Memory:
┌──────────────────────────────┐
│ ob_refcnt = 1         (+0)   │  8 bytes
│ ob_type = &PyTuple_Type (+8) │  8 bytes
│ ob_size = 3           (+16)  │  8 bytes
│ ob_item[0] → int(1)  (+24)  │  8 bytes (pointer)
│ ob_item[1] → int(2)  (+32)  │  8 bytes (pointer)
│ ob_item[2] → int(3)  (+40)  │  8 bytes (pointer)
└──────────────────────────────┘
Total: 48 bytes
```

---

## 8.9 Modifying ob_size

For mutable containers, `ob_size` changes as items are added/removed:

```python
x = [1, 2, 3]     # ob_size = 3
x.append(4)        # ob_size = 4
x.pop()            # ob_size = 3
x.clear()          # ob_size = 0
```

The macro for setting ob_size:
```c
// Include/object.h (CPython 3.12+)
static inline void Py_SET_SIZE(PyVarObject *ob, Py_ssize_t size) {
    ob->ob_size = size;
}

// Usage in list operations:
static int
list_append(PyListObject *self, PyObject *v) {
    // ... ensure capacity ...
    self->ob_item[Py_SIZE(self)] = v;
    Py_SET_SIZE(self, Py_SIZE(self) + 1);
    return 0;
}
```

For immutable types (tuple, str, bytes), `ob_size` is set once at creation and never modified.

---

## 8.10 PyVarObject vs PyObject: Complete Comparison

```
PyObject (fixed-size types):
┌─────────────┬──────────────────────────────────────────┐
│  ob_refcnt  │  Reference count                         │ 8 bytes
│  ob_type    │  Type pointer                            │ 8 bytes
├─────────────┼──────────────────────────────────────────┤
│  [data]     │  Fixed, known from tp_basicsize          │ varies
└─────────────┴──────────────────────────────────────────┘
Header: 16 bytes
Total instance size: tp_basicsize (constant for all instances)


PyVarObject (variable-size types):
┌─────────────┬──────────────────────────────────────────┐
│  ob_refcnt  │  Reference count                         │ 8 bytes
│  ob_type    │  Type pointer                            │ 8 bytes
│  ob_size    │  Number of items                         │ 8 bytes
├─────────────┼──────────────────────────────────────────┤
│  [data]     │  Variable: ob_size × tp_itemsize         │ varies
└─────────────┴──────────────────────────────────────────┘
Header: 24 bytes
Total instance size: tp_basicsize + ob_size × tp_itemsize (varies per instance)
```

---

## 8.11 Source References

| File | Contents |
|------|----------|
| `Include/object.h` | PyVarObject struct, Py_SIZE, Py_SET_SIZE, PyObject_VAR_HEAD |
| `Objects/tupleobject.c` | PyTupleObject (uses PyVarObject), tuple_length |
| `Objects/bytesobject.c` | PyBytesObject (uses PyVarObject) |
| `Objects/longobject.c` | PyLongObject (ob_size encodes sign) |
| `Objects/object.c` | PyObject_Size (calls sq_length which reads ob_size) |
| `Include/cpython/tupleobject.h` | PyTupleObject struct definition |

---

## 8.12 Interview Questions — Part 8

**Q1**: What is the PyVarObject struct and how does it extend PyObject?
**A**: PyVarObject adds a single field — `ob_size` (Py_ssize_t, 8 bytes) — after the PyObject header. It embeds PyObject as its first field, so a PyVarObject* can be safely cast to PyObject*. Total header: 24 bytes vs PyObject's 16.

**Q2**: Explain exactly how `len()` achieves O(1) time complexity.
**A**: `len(x)` calls `PyObject_Size(x)`, which dispatches to the type's `sq_length` slot. For built-in containers, this function simply returns `Py_SIZE(x)`, which reads `ob_size` at offset 16 — a single memory load. No iteration or counting needed.

**Q3**: What does `Py_SIZE(x)` expand to?
**A**: `((PyVarObject *)(x))->ob_size` — cast the object pointer to PyVarObject* and read the ob_size field at offset 16. It's a compile-time offset calculation, resulting in one memory read instruction.

**Q4**: Why is ob_size signed (Py_ssize_t) rather than unsigned?
**A**: Primarily for int objects, where the sign of ob_size encodes whether the integer is positive or negative. Also useful for error detection — an unexpected negative size indicates memory corruption.

**Q5**: How is PyObject_VAR_HEAD used in type definitions?
**A**: It expands to `PyVarObject ob_base;` and is placed as the first field in variable-size object structs (like PyTupleObject, PyBytesObject). This ensures the 24-byte header is properly embedded.

**Q6**: What determines whether a type uses PyObject or PyVarObject?
**A**: The type's `tp_itemsize` field. If `tp_itemsize > 0`, instances use PyVarObject (variable-size). If `tp_itemsize == 0`, instances use PyObject (fixed-size).

**Q7**: How is a tuple of 3 elements allocated in memory?
**A**: CPython allocates `sizeof(PyTupleObject) + (3-1) * sizeof(PyObject*)` bytes, sets `ob_size = 3`, initializes the header, and fills `ob_item[0..2]` with pointers to the elements. Total ~48 bytes for the tuple struct (plus the elements themselves).

**Q8**: Can ob_size be modified after object creation?
**A**: For mutable containers (list), yes — `Py_SET_SIZE` updates it as items are added/removed. For immutable types (tuple, str, bytes, frozenset), it's set once at creation and never changed.
