# Part 2 — Everything Starts With PyObject

## 2.1 The Actual CPython Definition

From `Include/object.h` (simplified for clarity):

```c
typedef struct _object {
    Py_ssize_t ob_refcnt;
    PyTypeObject *ob_type;
} PyObject;
```

On 64-bit systems with the `Py_TRACE_REFS` debug build disabled (production), this is the complete definition. Two fields. 16 bytes. That's it.

With debug builds or GC tracking, additional fields may appear before or around this struct, but the core is always these two fields.

---

## 2.2 Field 1: ob_refcnt

```
Offset:  0x00 (first field)
Type:    Py_ssize_t (signed 64-bit integer on 64-bit systems)
Size:    8 bytes
Purpose: Number of references currently pointing to this object
```

### What It Tracks

Every pointer that "owns" a reference to this object contributes 1 to ob_refcnt:

```python
a = [1, 2, 3]    # ob_refcnt = 1 (name 'a' holds a reference)
b = a             # ob_refcnt = 2 (name 'b' also holds a reference)
c = [a, a]        # ob_refcnt = 4 (c[0] and c[1] also hold references)
del b             # ob_refcnt = 3
del c             # ob_refcnt = 1 (c's destructor decrefs both slots)
del a             # ob_refcnt = 0 → DEALLOCATION
```

### Why It's the FIRST Field

Performance: `ob_refcnt` is the most frequently accessed field (incremented/decremented on every assignment, function call, container operation). Placing it at offset 0 means:
- No offset calculation needed (pointer to object = pointer to refcnt)
- Slightly faster access on some architectures
- Simplifies the Py_INCREF/Py_DECREF macros

### Why Signed?

`Py_ssize_t` is signed, not unsigned. Reasons:
- Easier to detect bugs (negative refcount = corruption)
- Consistency with other CPython size types
- Debug assertions can check `ob_refcnt > 0`

### Special Values (Python 3.12+)

In Python 3.12+, certain "immortal" objects (like `None`, `True`, small integers) have a special refcount value that never changes:
```c
#define _Py_IMMORTAL_REFCNT  (UINT32_MAX >> 2)  // Very large value
// Py_INCREF/Py_DECREF check for this and skip the update
```

This prevents unnecessary cache line bouncing for frequently-shared immortal objects.

---

## 2.3 Field 2: ob_type

```
Offset:  0x08 (second field, after 8-byte refcnt)
Type:    PyTypeObject * (pointer)
Size:    8 bytes
Purpose: Points to the type object that defines this object's behavior
```

### What It Points To

`ob_type` points to a **type object** — itself a Python object (with its own ob_refcnt and ob_type!) — that contains:
- The type's name (e.g., "int", "str", "list")
- Function pointers for all operations (`__add__`, `__repr__`, `__hash__`, etc.)
- Memory layout information
- Method tables
- Base classes

```
Integer object 42:
┌─────────────────┐
│ ob_refcnt: N    │
│ ob_type: ───────┼──────→ PyLong_Type (the int type object)
│ ob_digit: [42]  │          ├── tp_name: "int"
└─────────────────┘          ├── tp_repr: long_repr function
                             ├── tp_hash: long_hash function
                             ├── tp_richcompare: long_richcompare
                             ├── nb_add: long_add function
                             └── ... (many more function pointers)
```

### Why a Pointer (Not Embedded)?

All objects of the same type share ONE type object:
```
int(42).ob_type  →  PyLong_Type  ←  int(99).ob_type
int(0).ob_type   →  PyLong_Type  ←  int(-5).ob_type
```

If type info were embedded in each object, every integer would carry hundreds of bytes of redundant type metadata. A pointer (8 bytes) to one shared type object is far more efficient.

### Type Objects Are Objects Too

`PyLong_Type` (the int type) is itself a Python object:
```
PyLong_Type:
  ob_refcnt: (very high — many ints reference it)
  ob_type: → PyType_Type (the 'type' type!)
  tp_name: "int"
  tp_basicsize: sizeof(PyLongObject)
  ... 

PyType_Type:
  ob_refcnt: (very high)
  ob_type: → PyType_Type (points to ITSELF!)
  tp_name: "type"
  ...
```

The chain terminates: `type` is its own type. `type(type) is type`.

---

## 2.4 How CPython Uses These Fields

### Using ob_type for Dispatch

```c
// Python: repr(x)  → internally becomes:
PyObject* result = x->ob_type->tp_repr(x);
//                  ↑           ↑        ↑
//                  |           |        pass object to its own repr function
//                  |           function pointer for __repr__
//                  read type from object header

// Python: x + y → internally becomes:
PyObject* result = x->ob_type->tp_as_number->nb_add(x, y);
```

### Using ob_refcnt for Lifetime

```c
// Python: a = x → internally:
Py_INCREF(x);          // x->ob_refcnt += 1
// store pointer to x in local variable 'a'

// Python: del a → internally:
Py_DECREF(x);          // x->ob_refcnt -= 1; if (x->ob_refcnt == 0) dealloc(x)
// remove 'a' from namespace
```

---

## 2.5 Memory Diagram: A Complete Picture

For `x = 42`:

```
═══════════════════════════════════════════════════════════
STACK (local variable in the current frame)
═══════════════════════════════════════════════════════════
Variable 'x':  pointer → 0x00007F80_0090_4A20
═══════════════════════════════════════════════════════════


═══════════════════════════════════════════════════════════
HEAP: PyLongObject at 0x00007F80_0090_4A20
═══════════════════════════════════════════════════════════
Offset   Address              Field         Value
────────────────────────────────────────────────────────
+0x00    0x7F80_0090_4A20     ob_refcnt     137  (cached small int, many refs)
+0x08    0x7F80_0090_4A28     ob_type       0x0000_0000_0090_46A0 → PyLong_Type
+0x10    0x7F80_0090_4A30     ob_size       1    (one "digit")
+0x18    0x7F80_0090_4A38     ob_digit[0]   42   (the actual value)
═══════════════════════════════════════════════════════════
Total size: 28 bytes (with padding to 32)


═══════════════════════════════════════════════════════════
HEAP (or static data): PyLong_Type at 0x0090_46A0
═══════════════════════════════════════════════════════════
+0x00    ob_refcnt     (very high)
+0x08    ob_type       → PyType_Type (the metaclass)
+0x10    ob_size       0
+0x18    tp_name       → "int"
+0x20    tp_basicsize  28 (size of PyLongObject for single digit)
+0x28    tp_dealloc    → long_dealloc function
         ...           (hundreds of bytes of function pointers)
═══════════════════════════════════════════════════════════
```

---

## 2.6 The PyObject_HEAD Macro

CPython defines a macro for embedding the header:

```c
// Include/object.h
#define PyObject_HEAD          PyObject ob_base;

// Used in type definitions:
typedef struct {
    PyObject_HEAD              // expands to: PyObject ob_base;
    double ob_fval;            // float-specific data
} PyFloatObject;

// Equivalent to writing:
typedef struct {
    Py_ssize_t ob_refcnt;     // from PyObject
    PyTypeObject *ob_type;    // from PyObject  
    double ob_fval;            // float-specific data
} PyFloatObject;
```

The macro ensures every object type starts with the correct header without copy-pasting.

---

## 2.7 Proving the Layout with Python

```python
import sys
import ctypes

x = 42

# Address of object:
addr = id(x)
print(f"Object at: {addr:#x}")

# Read ob_refcnt (first 8 bytes):
refcnt = ctypes.c_ssize_t.from_address(addr).value
print(f"ob_refcnt: {refcnt}")

# Read ob_type (next 8 bytes):
type_addr = ctypes.c_void_p.from_address(addr + 8).value
print(f"ob_type at: {type_addr:#x}")
print(f"type(x) at: {id(type(x)):#x}")  # Should match!
assert type_addr == id(int)  # ob_type points to int type!
```

---

## 2.8 Why Every Object Begins With the Same Header

1. **Generic manipulation**: Any `PyObject*` pointer lets you read refcount and type
2. **Container uniformity**: Lists store `PyObject**` — can hold ANY object type
3. **Function signatures**: C functions take `PyObject*` parameters — accept anything
4. **Interpreter simplicity**: Bytecode interpreter manipulates `PyObject*` on the value stack

Without this uniformity, every operation would need type-specific code paths, making the interpreter enormously complex.

---

## 2.9 Interview Questions — Part 2

**Q1**: What is at offset 0 of every Python object in CPython?
**A**: `ob_refcnt` — the reference count (Py_ssize_t, 8 bytes on 64-bit).

**Q2**: What does `ob_type` point to?
**A**: A PyTypeObject — the type object that contains all operation function pointers and metadata for this object's type. All objects of the same type share one type object.

**Q3**: What does `type(type)` return and why?
**A**: `type` — the type metaclass points to itself. `PyType_Type.ob_type == &PyType_Type`. This terminates the infinite regress.

**Q4**: Why is ob_refcnt placed at offset 0?
**A**: Most frequently accessed field. Offset 0 means pointer-to-object equals pointer-to-refcnt — slightly faster access, simpler macros.

**Q5**: How does CPython achieve dynamic dispatch using ob_type?
**A**: Read `obj->ob_type`, then call the appropriate function pointer from the type object's tables (e.g., `obj->ob_type->tp_repr(obj)` for repr()).

**Q6**: What are "immortal" objects in Python 3.12+?
**A**: Objects like None, True, False, small integers that have a special refcount value. Py_INCREF/Py_DECREF skip updating their refcount, avoiding cache contention in multi-threaded scenarios.
