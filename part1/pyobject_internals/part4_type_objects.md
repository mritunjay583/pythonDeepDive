# Part 4 — PyTypeObject: Types Are Objects

## 4.1 The Key Insight

In CPython, `int`, `str`, `list`, `type` — these aren't just abstract concepts. They are **actual C struct instances** sitting in memory, with their own `ob_refcnt` and `ob_type` fields. Types are objects, and they have a type themselves.

```python
>>> type(42)
<class 'int'>
>>> type(int)
<class 'type'>
>>> type(type)
<class 'type'>    # type is its own type!
```

In C:
```c
// int(42) → PyLongObject instance
//   .ob_type → &PyLong_Type

// int → PyLong_Type (a global PyTypeObject struct)
//   .ob_type → &PyType_Type

// type → PyType_Type (a global PyTypeObject struct)
//   .ob_type → &PyType_Type  (points to itself!)
```

---

## 4.2 The PyTypeObject Struct

`PyTypeObject` is enormous — one of the largest structs in CPython. Here's a simplified view of its key fields:

```c
// Include/cpython/object.h (heavily simplified)
typedef struct _typeobject {
    PyObject_VAR_HEAD                    // ob_refcnt, ob_type, ob_size
    const char *tp_name;                 // "int", "str", "list"
    Py_ssize_t tp_basicsize;             // Size of instances
    Py_ssize_t tp_itemsize;              // Size per item (variable objects)

    /* Methods to implement standard operations */
    destructor tp_dealloc;               // __del__ / deallocation
    vectorcallfunc tp_vectorcall_offset; // fast call protocol
    getattrfunc tp_getattr;              // __getattr__ (legacy)
    setattrfunc tp_setattr;              // __setattr__ (legacy)
    PyAsyncMethods *tp_as_async;         // __await__, __aiter__, __anext__
    reprfunc tp_repr;                    // __repr__
    PyNumberMethods *tp_as_number;       // __add__, __mul__, etc.
    PySequenceMethods *tp_as_sequence;   // __getitem__, __len__ (sequence)
    PyMappingMethods *tp_as_mapping;     // __getitem__, __len__ (mapping)
    hashfunc tp_hash;                    // __hash__
    ternaryfunc tp_call;                 // __call__
    reprfunc tp_str;                     // __str__
    getattrofunc tp_getattro;            // __getattribute__
    setattrofunc tp_setattro;            // __setattr__
    PyBufferProcs *tp_as_buffer;         // Buffer protocol
    unsigned long tp_flags;              // Feature flags
    const char *tp_doc;                  // __doc__
    traverseproc tp_traverse;            // GC traversal
    inquiry tp_clear;                    // GC clearing
    richcmpfunc tp_richcompare;          // __eq__, __lt__, etc.
    Py_ssize_t tp_weaklistoffset;        // Weak reference support
    getiterfunc tp_iter;                 // __iter__
    iternextfunc tp_iternext;            // __next__
    PyMethodDef *tp_methods;             // Regular methods
    PyMemberDef *tp_members;             // Member descriptors
    PyGetSetDef *tp_getset;              // Properties
    PyTypeObject *tp_base;               // Base class
    PyObject *tp_dict;                   // __dict__ of the type
    descrgetfunc tp_descr_get;           // __get__ (descriptor)
    descrsetfunc tp_descr_set;           // __set__ (descriptor)
    Py_ssize_t tp_dictoffset;            // Offset of instance __dict__
    initproc tp_init;                    // __init__
    allocfunc tp_alloc;                  // Memory allocation for instances
    newfunc tp_new;                      // __new__
    freefunc tp_free;                    // Memory deallocation
    inquiry tp_is_gc;                    // Is this object GC-tracked?
    PyObject *tp_bases;                  // Base classes tuple
    PyObject *tp_mro;                    // Method Resolution Order
    // ... many more fields ...
} PyTypeObject;
```

On 64-bit systems, `PyTypeObject` is typically **400-600 bytes**.

---

## 4.3 The Type Hierarchy

```
                    ┌─────────────────┐
                    │  PyType_Type    │ ← "type" type object
                    │  (metaclass)    │
                    │  ob_type: self  │─────┐
                    └────────┬────────┘     │
                             │              │
                    ┌────────┴────────┐     │
         ┌─────────┤  Points to self  ├─────┘
         │         └─────────────────┘
         │
         ├──── PyLong_Type      (int)      .ob_type → PyType_Type
         ├──── PyFloat_Type     (float)    .ob_type → PyType_Type
         ├──── PyUnicode_Type   (str)      .ob_type → PyType_Type
         ├──── PyList_Type      (list)     .ob_type → PyType_Type
         ├──── PyDict_Type      (dict)     .ob_type → PyType_Type
         ├──── PyTuple_Type     (tuple)    .ob_type → PyType_Type
         └──── PyBaseObject_Type (object)  .ob_type → PyType_Type
```

Every built-in type object has `ob_type = &PyType_Type`. And `PyType_Type` itself has `ob_type = &PyType_Type` (self-referential).

---

## 4.4 Dynamic Dispatch via Function Pointers

This is CPython's version of virtual method dispatch. When Python code calls an operation, the interpreter:
1. Reads `ob_type` from the object header
2. Follows function pointers in the type object to find the implementation
3. Calls that function, passing the object itself

### Example: `repr(x)`

```c
// In Python/bltinmodule.c (builtin_repr):
PyObject *builtin_repr(PyObject *module, PyObject *obj) {
    return PyObject_Repr(obj);
}

// In Objects/object.c:
PyObject *PyObject_Repr(PyObject *v) {
    if (v->ob_type->tp_repr == NULL)
        return PyUnicode_FromFormat("<%s object at %p>",
                                    Py_TYPE(v)->tp_name, v);
    return v->ob_type->tp_repr(v);
    //     ^^^^^^^^^^^^^^^^^^^^^^^^^
    //     Dynamic dispatch! Jump through the type's function pointer.
}
```

### Example: `x + y` (numeric addition)

```c
// The interpreter sees BINARY_ADD bytecode, calls:
PyObject *PyNumber_Add(PyObject *v, PyObject *w) {
    // Try v's type first:
    PyNumberMethods *mv = Py_TYPE(v)->tp_as_number;
    if (mv && mv->nb_add) {
        PyObject *result = mv->nb_add(v, w);
        if (result != Py_NotImplemented)
            return result;
    }
    // Then try w's type...
    // ...
}
```

### Example: `len(x)`

```c
// Python calls PyObject_Size(obj):
Py_ssize_t PyObject_Size(PyObject *o) {
    PySequenceMethods *m = Py_TYPE(o)->tp_as_sequence;
    if (m && m->sq_length) {
        return m->sq_length(o);
    }
    PyMappingMethods *mm = Py_TYPE(o)->tp_as_mapping;
    if (mm && mm->mp_length) {
        return mm->mp_length(o);
    }
    // TypeError...
}
```

---

## 4.5 The Sub-Tables (tp_as_number, tp_as_sequence, tp_as_mapping)

Types don't cram all operation pointers directly into PyTypeObject. Instead, operations are grouped into sub-tables:

```c
// Number operations:
typedef struct {
    binaryfunc nb_add;           // __add__
    binaryfunc nb_subtract;      // __sub__
    binaryfunc nb_multiply;      // __mul__
    binaryfunc nb_remainder;     // __mod__
    binaryfunc nb_divmod;        // divmod()
    ternaryfunc nb_power;        // __pow__
    unaryfunc nb_negative;       // __neg__
    unaryfunc nb_positive;       // __pos__
    unaryfunc nb_absolute;       // abs()
    inquiry nb_bool;             // __bool__
    unaryfunc nb_invert;         // ~x
    binaryfunc nb_lshift;        // __lshift__
    binaryfunc nb_rshift;        // __rshift__
    binaryfunc nb_and;           // __and__
    binaryfunc nb_xor;           // __xor__
    binaryfunc nb_or;            // __or__
    unaryfunc nb_int;            // __int__
    unaryfunc nb_float;          // __float__
    binaryfunc nb_inplace_add;   // __iadd__
    binaryfunc nb_floor_divide;  // __floordiv__
    binaryfunc nb_true_divide;   // __truediv__
    binaryfunc nb_index;         // __index__
    // ... more
} PyNumberMethods;
```

```c
// Sequence operations:
typedef struct {
    lenfunc sq_length;              // __len__
    binaryfunc sq_concat;           // __add__ (sequence)
    ssizeargfunc sq_repeat;         // __mul__ (sequence)
    ssizeargfunc sq_item;           // __getitem__ (by index)
    ssizeobjargproc sq_ass_item;    // __setitem__ (by index)
    objobjproc sq_contains;         // __contains__ (in)
    binaryfunc sq_inplace_concat;   // __iadd__ (sequence)
    ssizeargfunc sq_inplace_repeat; // __imul__ (sequence)
} PySequenceMethods;
```

```
PyTypeObject (e.g., PyList_Type):
┌─────────────────────────────┐
│ ob_refcnt                   │
│ ob_type → PyType_Type       │
│ tp_name: "list"             │
│ tp_basicsize: 40            │
│ tp_dealloc: list_dealloc    │
│ tp_repr: list_repr          │
│ tp_as_number: NULL          │  ← lists don't support + as addition
│ tp_as_sequence: ────────────┼──→ PySequenceMethods:
│ tp_as_mapping: ─────────────┼─┐    sq_length: list_length
│ tp_hash: NULL (unhashable)  │ │    sq_concat: list_concat
│ tp_iter: list_iter          │ │    sq_item: list_item
│ tp_methods: list_methods    │ │    sq_contains: list_contains
│ ...                         │ │
└─────────────────────────────┘ │
                                └→ PyMappingMethods:
                                     mp_length: list_length
                                     mp_subscript: list_subscript
```

---

## 4.6 How `int` Is Defined (PyLong_Type)

```c
// Objects/longobject.c
PyTypeObject PyLong_Type = {
    PyVarObject_HEAD_INIT(&PyType_Type, 0)
    "int",                          /* tp_name */
    offsetof(PyLongObject, long_value.ob_digit),  /* tp_basicsize */
    sizeof(digit),                  /* tp_itemsize */
    0,                              /* tp_dealloc (special handling) */
    0,                              /* tp_vectorcall_offset */
    0,                              /* tp_getattr */
    0,                              /* tp_setattr */
    0,                              /* tp_as_async */
    long_to_decimal_string,         /* tp_repr */
    &long_as_number,                /* tp_as_number → has nb_add, nb_mul, etc. */
    0,                              /* tp_as_sequence */
    0,                              /* tp_as_mapping */
    (hashfunc)long_hash,            /* tp_hash */
    0,                              /* tp_call (not callable) */
    0,                              /* tp_str */
    PyObject_GenericGetAttr,        /* tp_getattro */
    0,                              /* tp_setattro */
    0,                              /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_LONG_SUBCLASS,
    long_doc,                       /* tp_doc */
    0,                              /* tp_traverse */
    0,                              /* tp_clear */
    long_richcompare,               /* tp_richcompare */
    0,                              /* tp_weaklistoffset */
    0,                              /* tp_iter */
    0,                              /* tp_iternext */
    long_methods,                   /* tp_methods */
    0,                              /* tp_members */
    long_getset,                    /* tp_getset */
    0,                              /* tp_base */
    0,                              /* tp_dict */
    0,                              /* tp_descr_get */
    0,                              /* tp_descr_set */
    0,                              /* tp_dictoffset */
    0,                              /* tp_init */
    0,                              /* tp_alloc */
    long_new,                       /* tp_new */
    PyObject_Free,                  /* tp_free */
};
```

This is the **complete behavior definition** of the `int` type — sitting in a single C struct.

---

## 4.7 Slot Inheritance

When you define a class in Python:
```python
class MyInt(int):
    pass
```

CPython creates a NEW PyTypeObject for `MyInt`. For any slot not overridden, it **inherits** the parent's function pointer:

```c
// In typeobject.c, inherit_slots():
if (type->tp_repr == NULL)
    type->tp_repr = base->tp_repr;  // Copy parent's function pointer

if (type->tp_hash == NULL)
    type->tp_hash = base->tp_hash;
```

This means `MyInt` instances dispatch `repr()` through the same function pointer as `int` — no Python-level lookup needed for inherited C slots.

---

## 4.8 Static vs Heap Types

### Static Types (Built-in)

Built-in types like `int`, `str`, `list` are **statically allocated** — they're global C variables:

```c
// This is a compile-time constant. Lives in the data segment.
PyTypeObject PyLong_Type = { ... };
```

- Never deallocated (immortal)
- Never garbage collected
- One instance per interpreter (in traditional CPython)

### Heap Types (User-Defined)

User-defined classes are **heap allocated**:

```python
class Foo:
    pass
```

```c
// CPython calls type_new() → allocates PyTypeObject on the heap:
PyTypeObject *foo_type = PyObject_GC_New(PyTypeObject, &PyType_Type);
foo_type->tp_name = "Foo";
// ... fill in slots ...
```

- CAN be deallocated when no instances or references remain
- Tracked by GC (can participate in cycles)
- Has `Py_TPFLAGS_HEAPTYPE` flag set

---

## 4.9 The tp_flags Field

`tp_flags` is a bitmask that tells CPython what features this type supports:

```c
#define Py_TPFLAGS_HEAPTYPE             (1UL << 9)   // Heap-allocated type
#define Py_TPFLAGS_BASETYPE             (1UL << 10)  // Can be subclassed
#define Py_TPFLAGS_READY                (1UL << 12)  // Fully initialized
#define Py_TPFLAGS_HAVE_GC              (1UL << 14)  // Has GC support
#define Py_TPFLAGS_HAVE_VECTORCALL      (1UL << 11)  // Supports vectorcall
#define Py_TPFLAGS_LONG_SUBCLASS        (1UL << 24)  // int subclass
#define Py_TPFLAGS_LIST_SUBCLASS        (1UL << 25)  // list subclass
#define Py_TPFLAGS_TUPLE_SUBCLASS       (1UL << 26)  // tuple subclass
#define Py_TPFLAGS_BYTES_SUBCLASS       (1UL << 27)  // bytes subclass
#define Py_TPFLAGS_UNICODE_SUBCLASS     (1UL << 28)  // str subclass
#define Py_TPFLAGS_DICT_SUBCLASS        (1UL << 29)  // dict subclass
#define Py_TPFLAGS_TYPE_SUBCLASS        (1UL << 31)  // type subclass
```

The `*_SUBCLASS` flags allow fast `isinstance()` checks without walking the MRO:
```c
// Fast check: is this a string?
#define PyUnicode_Check(op) PyType_FastSubclass(Py_TYPE(op), Py_TPFLAGS_UNICODE_SUBCLASS)
// Just a bitwise AND — O(1)!
```

---

## 4.10 How type() and isinstance() Work Internally

### `type(x)` — Just Read ob_type

```c
// Python: type(x)
// C: Py_TYPE(x) macro
#define Py_TYPE(ob) (((PyObject *)(ob))->ob_type)
// Returns the pointer stored in the header — instant O(1)
```

### `isinstance(x, SomeType)` — Walk the MRO

```c
int PyObject_IsInstance(PyObject *inst, PyObject *cls) {
    // Fast path: exact type match
    if (Py_TYPE(inst) == (PyTypeObject *)cls)
        return 1;
    
    // Fast path: check subclass flags
    if (PyType_FastSubclass(Py_TYPE(inst), relevant_flag))
        return 1;
    
    // Slow path: walk MRO (method resolution order)
    PyObject *mro = Py_TYPE(inst)->tp_mro;
    for (int i = 0; i < PyTuple_GET_SIZE(mro); i++) {
        if (PyTuple_GET_ITEM(mro, i) == cls)
            return 1;
    }
    return 0;
}
```

---

## 4.11 Memory Layout of a Type Object

```
PyLong_Type (the "int" type) in memory:
┌──────────────────────────────────────────────────────────────────┐
│ HEADER (PyVarObject, 24 bytes)                                    │
│   ob_refcnt:  (very large — every int instance references this)  │
│   ob_type:    → PyType_Type (type's type is 'type')              │
│   ob_size:    0                                                   │
├──────────────────────────────────────────────────────────────────┤
│ TYPE-SPECIFIC FIELDS (~400+ bytes)                                │
│   tp_name:         → "int"                                        │
│   tp_basicsize:    depends on digit count                         │
│   tp_itemsize:     sizeof(digit)                                  │
│   tp_dealloc:      → long_dealloc                                 │
│   tp_repr:         → long_to_decimal_string                       │
│   tp_as_number:    → long_as_number (PyNumberMethods struct)      │
│   tp_as_sequence:  NULL                                           │
│   tp_as_mapping:   NULL                                           │
│   tp_hash:         → long_hash                                    │
│   tp_call:         NULL (ints aren't callable)                    │
│   tp_richcompare:  → long_richcompare                             │
│   tp_iter:         NULL                                           │
│   tp_methods:      → long_methods table                           │
│   tp_new:          → long_new                                     │
│   tp_free:         → PyObject_Free                                │
│   tp_base:         → PyBaseObject_Type (object)                   │
│   tp_mro:          → (int, object) tuple                          │
│   ...              (many more fields)                             │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4.12 The Metaclass Bootstrap Problem

There's a chicken-and-egg problem:
- Every object needs `ob_type` pointing to its type
- Type objects are objects, so they need `ob_type` too
- `type` must exist before any type can be created
- But `type` is itself a type object...

CPython solves this with manual initialization during interpreter startup:

```c
// In Objects/typeobject.c, _PyTypes_Init():
// 1. Partially create PyType_Type and PyBaseObject_Type
// 2. Manually set their ob_type fields:
PyType_Type.ob_type = &PyType_Type;         // type is its own type
PyBaseObject_Type.ob_type = &PyType_Type;   // object's type is type
// 3. Call PyType_Ready() to fill in inherited slots
```

---

## 4.13 Source References

| File | Contents |
|------|----------|
| `Include/object.h` | PyTypeObject forward declaration |
| `Include/cpython/object.h` | Full PyTypeObject struct definition |
| `Objects/typeobject.c` | Type creation, slot inheritance, type_new() |
| `Objects/longobject.c` | PyLong_Type definition |
| `Objects/listobject.c` | PyList_Type definition |
| `Objects/floatobject.c` | PyFloat_Type definition |
| `Objects/unicodeobject.c` | PyUnicode_Type definition |

---

## 4.14 Interview Questions — Part 4

**Q1**: What is PyTypeObject and why is it so large?
**A**: PyTypeObject is the C struct that represents a Python type. It contains function pointers for every possible operation (repr, hash, add, call, iter, etc.), sub-tables for number/sequence/mapping protocols, and metadata. It's typically 400-600 bytes because it must cover ALL possible behaviors.

**Q2**: How does CPython implement dynamic dispatch (polymorphism)?
**A**: Through function pointers in type objects. The interpreter reads `obj->ob_type` to get the type, then follows the relevant `tp_*` function pointer (e.g., `tp_repr`, `tp_hash`) to call the correct implementation. This is analogous to a C++ vtable but more explicit.

**Q3**: What's the difference between static types and heap types?
**A**: Static types (built-in like int, str) are global C variables allocated at compile time — immortal and never GC'd. Heap types (user classes) are allocated via `type_new()` on the heap, can be deallocated, and are GC-tracked. Heap types have `Py_TPFLAGS_HEAPTYPE`.

**Q4**: How does `type(type) is type` work at the C level?
**A**: `PyType_Type.ob_type = &PyType_Type` — the type metaclass's `ob_type` pointer points to itself. This self-referential pointer terminates what would otherwise be an infinite type chain.

**Q5**: How does isinstance() achieve O(1) for built-in types?
**A**: Through `tp_flags` bitmask checks. Each built-in type has a unique `*_SUBCLASS` flag. `isinstance(x, str)` just does a bitwise AND on `Py_TYPE(x)->tp_flags` — no MRO traversal needed.

**Q6**: What is slot inheritance and how does it work?
**A**: When a subclass doesn't override a C-level slot, CPython copies the parent's function pointer into the subclass's type object during `PyType_Ready()`. This means inherited methods dispatch directly through the C function pointer, not through Python attribute lookup.

**Q7**: Why does CPython separate operations into sub-tables (tp_as_number, etc.)?
**A**: To save memory. Most types only support a subset of protocols. Types that don't support numbers set `tp_as_number = NULL`, avoiding allocation of the entire PyNumberMethods struct. It also provides logical grouping.

**Q8**: How is a user-defined class (`class Foo: pass`) represented in C?
**A**: As a heap-allocated PyTypeObject with `Py_TPFLAGS_HEAPTYPE`. CPython calls `type_new()` which allocates the struct, fills in slots based on methods defined in the class body, and links it into the type hierarchy.
