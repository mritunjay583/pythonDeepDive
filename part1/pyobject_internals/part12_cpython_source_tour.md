# Part 12 — CPython Source Tour: Include/object.h

## 12.1 File Overview

The heart of CPython's object system lives in a handful of header files:

```
Include/
├── object.h                  ← Public API: PyObject, Py_INCREF, Py_TYPE
├── refcount.h                ← Reference counting macros (3.12+)
├── cpython/
│   └── object.h              ← Internal: Full PyTypeObject struct
├── internal/
│   ├── pycore_object.h       ← Internal helpers: _Py_Dealloc, _Py_NewReference
│   └── pycore_gc.h           ← GC header struct, tracking macros
Objects/
├── object.c                  ← Object protocol: repr, hash, compare
├── typeobject.c              ← Type creation, MRO, slot inheritance
```

This tour walks through the key definitions line by line.

---

## 12.2 PyObject_HEAD Macro

```c
// Include/object.h

// The macro that every object struct starts with:
#define PyObject_HEAD       PyObject ob_base;

// Expands the struct to start with:
//   Py_ssize_t ob_refcnt;
//   PyTypeObject *ob_type;
```

Usage:
```c
typedef struct {
    PyObject_HEAD          // → PyObject ob_base;
    double ob_fval;
} PyFloatObject;

// Compiler sees:
typedef struct {
    PyObject ob_base;      // { Py_ssize_t ob_refcnt; PyTypeObject *ob_type; }
    double ob_fval;
} PyFloatObject;
```

---

## 12.3 PyObject_VAR_HEAD Macro

```c
// Include/object.h

#define PyObject_VAR_HEAD   PyVarObject ob_base;

// Expands to include ob_size:
//   Py_ssize_t ob_refcnt;
//   PyTypeObject *ob_type;
//   Py_ssize_t ob_size;
```

Usage:
```c
typedef struct {
    PyObject_VAR_HEAD      // → PyVarObject ob_base;
    PyObject *ob_item[1];  // Flexible array of pointers
} PyTupleObject;
```

---

## 12.4 Py_TYPE Macro

Reads the type pointer from any object:

```c
// Include/object.h (CPython 3.11+)
static inline PyTypeObject* Py_TYPE(PyObject *ob) {
    return ob->ob_type;
}

// Older versions (macro):
// #define Py_TYPE(ob) (((PyObject *)(ob))->ob_type)
```

The setter (introduced in 3.9):
```c
static inline void Py_SET_TYPE(PyObject *ob, PyTypeObject *type) {
    ob->ob_type = type;
}
```

**Why it became a function**: The old macro allowed `Py_TYPE(obj) = some_type` (assignment through macro). Making it a function prevents this misuse and enables future optimizations (like atomic operations for free-threading).

---

## 12.5 Py_SIZE Macro

Reads ob_size from variable-size objects:

```c
// Include/object.h
static inline Py_ssize_t Py_SIZE(PyObject *ob) {
    assert(ob->ob_type->tp_itemsize != 0 || Py_TYPE(ob) == &PyLong_Type);
    return _PyVarObject_CAST(ob)->ob_size;
}

#define _PyVarObject_CAST(op) ((PyVarObject *)(op))
```

The setter:
```c
static inline void Py_SET_SIZE(PyVarObject *ob, Py_ssize_t size) {
    ob->ob_size = size;
}
```

---

## 12.6 Py_INCREF — Reference Count Increment

```c
// Include/refcount.h (CPython 3.12+, simplified)

static inline Py_ALWAYS_INLINE void Py_INCREF(PyObject *op) {
#if SIZEOF_VOID_P > 4
    // 64-bit: check for immortal objects
    PY_UINT32_T cur_refcnt = op->ob_refcnt_split[PY_BIG_ENDIAN];
    if (cur_refcnt >= _Py_IMMORTAL_REFCNT_LOCAL) {
        return;  // Immortal — don't touch refcnt
    }
    op->ob_refcnt++;
#else
    // 32-bit: simpler path
    if (_Py_IsImmortal(op)) {
        return;
    }
    op->ob_refcnt++;
#endif
}
```

Pre-3.12 (classic, fast):
```c
#define Py_INCREF(op) (                         \
    _Py_INC_REFTOTAL                            \
    ((PyObject *)(op))->ob_refcnt++)
```

What happens at the machine level (x86-64):
```asm
; Py_INCREF(op):
; op is in register rdi
mov rax, [rdi]         ; load ob_refcnt
inc rax                ; increment
mov [rdi], rax         ; store back
; Or optimized to:
inc QWORD PTR [rdi]    ; atomic-ish on single-threaded (under GIL)
```

---

## 12.7 Py_DECREF — Reference Count Decrement

```c
// Include/refcount.h (CPython 3.12+, simplified)

static inline void Py_DECREF(PyObject *op) {
    if (_Py_IsImmortal(op)) {
        return;
    }
    if (--op->ob_refcnt == 0) {
        _Py_Dealloc(op);
    }
}
```

With debug assertions (debug build):
```c
static inline void Py_DECREF(PyObject *op) {
    if (_Py_IsImmortal(op)) {
        return;
    }
    _Py_DECREF_STAT_INC();
    if (--op->ob_refcnt != 0) {
        // Still alive
        assert(op->ob_refcnt > 0);  // Catch double-free!
    } else {
        _Py_Dealloc(op);
    }
}
```

---

## 12.8 Py_XINCREF and Py_XDECREF — NULL-Safe Variants

```c
// Include/refcount.h

// X variants handle NULL pointers safely:
static inline void Py_XINCREF(PyObject *op) {
    if (op != NULL) {
        Py_INCREF(op);
    }
}

static inline void Py_XDECREF(PyObject *op) {
    if (op != NULL) {
        Py_DECREF(op);
    }
}
```

When to use:
```c
// Use Py_INCREF when you KNOW the pointer is non-NULL:
Py_INCREF(Py_None);  // None is never NULL

// Use Py_XINCREF when the pointer MIGHT be NULL:
Py_XINCREF(self->optional_field);  // Could be NULL
```

---

## 12.9 PyObject_HEAD_INIT — Static Initialization

```c
// Include/object.h

#define PyObject_HEAD_INIT(type)    \
    { _Py_IMMORTAL_REFCNT, (type) },

// Used for statically-allocated objects:
PyObject _Py_NoneStruct = {
    PyObject_HEAD_INIT(&_PyNone_Type)
    // Expands to: { _Py_IMMORTAL_REFCNT, &_PyNone_Type }
};
```

---

## 12.10 PyVarObject_HEAD_INIT — For Type Objects

```c
// Include/object.h

#define PyVarObject_HEAD_INIT(type, size)    \
    { PyObject_HEAD_INIT(type) (size) },

// Every type object definition starts with:
PyTypeObject PyFloat_Type = {
    PyVarObject_HEAD_INIT(&PyType_Type, 0)
    // Expands to: { { _Py_IMMORTAL_REFCNT, &PyType_Type }, 0 }
    //             ob_refcnt                  ob_type        ob_size
    "float",        // tp_name
    sizeof(PyFloatObject),  // tp_basicsize
    0,              // tp_itemsize
    // ...
};
```

---

## 12.11 _Py_Dealloc — The Death Function

```c
// Objects/object.c (simplified)

void _Py_Dealloc(PyObject *op) {
    PyTypeObject *type = Py_TYPE(op);
    destructor dealloc = type->tp_dealloc;
    
    // Untrack from GC if tracked:
    if (PyType_IS_GC(type)) {
        PyObject_GC_UnTrack(op);
    }
    
    // Call the type's destructor:
    (*dealloc)(op);
    // tp_dealloc is responsible for:
    //   1. DECREF all referenced objects
    //   2. Free type-specific resources
    //   3. Call tp_free() to release memory
}
```

For example, list deallocation:
```c
// Objects/listobject.c
static void list_dealloc(PyListObject *op) {
    Py_ssize_t i;
    // DECREF every item:
    for (i = Py_SIZE(op); --i >= 0; ) {
        Py_XDECREF(op->ob_item[i]);
    }
    // Free the item array:
    PyMem_Free(op->ob_item);
    // Free the list object itself:
    Py_TYPE(op)->tp_free((PyObject *)op);
}
```

---

## 12.12 Py_NewRef and Py_XNewRef (Python 3.10+)

Modern helper that INCREFs and returns:

```c
// Include/refcount.h

static inline PyObject* Py_NewRef(PyObject *ob) {
    Py_INCREF(ob);
    return ob;
}

static inline PyObject* Py_XNewRef(PyObject *ob) {
    Py_XINCREF(ob);
    return ob;  // May return NULL
}
```

Simplifies common pattern:
```c
// Before Py_NewRef:
Py_INCREF(value);
self->field = value;

// After Py_NewRef (cleaner):
self->field = Py_NewRef(value);
```

---

## 12.13 Py_Is, Py_IsNone, Py_IsTrue, Py_IsFalse

```c
// Include/object.h (Python 3.10+)

static inline int Py_Is(PyObject *x, PyObject *y) {
    return (x == y);  // Pointer comparison
}

static inline int Py_IsNone(PyObject *x) {
    return Py_Is(x, Py_None);
}

static inline int Py_IsTrue(PyObject *x) {
    return Py_Is(x, Py_True);
}

static inline int Py_IsFalse(PyObject *x) {
    return Py_Is(x, Py_False);
}
```

---

## 12.14 PyObject_Init and _PyObject_INIT

```c
// Include/objimpl.h (simplified)

static inline PyObject* 
PyObject_Init(PyObject *op, PyTypeObject *typeobj) {
    assert(op != NULL);
    Py_SET_TYPE(op, typeobj);
    if (PyType_GetFlags(typeobj) & Py_TPFLAGS_HEAPTYPE) {
        Py_INCREF(typeobj);
    }
    _Py_NewReference(op);  // Sets ob_refcnt = 1
    return op;
}

// _Py_NewReference: Initialize refcount for a new object
static inline void _Py_NewReference(PyObject *op) {
    op->ob_refcnt = 1;
    #ifdef Py_TRACE_REFS
    _Py_AddToAllObjects(op);  // Debug: add to global list
    #endif
}
```

---

## 12.15 Key Constants

```c
// Include/object.h

// The None singleton:
#define Py_None (&_Py_NoneStruct)

// Boolean singletons:
#define Py_True  ((PyObject *)&_Py_TrueStruct)
#define Py_False ((PyObject *)&_Py_FalseStruct)

// Return macros for C functions:
#define Py_RETURN_NONE      return Py_NewRef(Py_None)
#define Py_RETURN_TRUE      return Py_NewRef(Py_True)
#define Py_RETURN_FALSE     return Py_NewRef(Py_False)
#define Py_RETURN_NOTIMPLEMENTED return Py_NewRef(Py_NotImplemented)
```

---

## 12.16 Object Protocol Functions (Objects/object.c)

```c
// Key functions in object.c:

PyObject *PyObject_Repr(PyObject *v);        // repr(v)
PyObject *PyObject_Str(PyObject *v);         // str(v)
PyObject *PyObject_ASCII(PyObject *v);       // ascii(v)
Py_hash_t PyObject_Hash(PyObject *v);        // hash(v)
int PyObject_IsTrue(PyObject *v);            // bool(v)
PyObject *PyObject_GetAttr(PyObject *v, PyObject *name);  // v.name
int PyObject_SetAttr(PyObject *v, PyObject *name, PyObject *value);
int PyObject_RichCompareBool(PyObject *v, PyObject *w, int op);
PyObject *PyObject_RichCompare(PyObject *v, PyObject *w, int op);
Py_ssize_t PyObject_Size(PyObject *o);       // len(o)
```

Each of these reads `ob_type` and dispatches to the appropriate `tp_*` slot.

---

## 12.17 File-by-File Summary

```
Include/object.h (PUBLIC):
├── PyObject struct
├── PyVarObject struct
├── PyObject_HEAD, PyObject_VAR_HEAD macros
├── Py_TYPE(), Py_SIZE(), Py_IS_TYPE()
├── PyObject_HEAD_INIT, PyVarObject_HEAD_INIT
├── Py_None, Py_True, Py_False constants
└── Py_Is(), Py_IsNone(), Py_IsTrue(), Py_IsFalse()

Include/refcount.h (PUBLIC):
├── Py_INCREF(), Py_DECREF()
├── Py_XINCREF(), Py_XDECREF()
├── Py_NewRef(), Py_XNewRef()
├── Py_SETREF()
└── _Py_IMMORTAL_REFCNT

Include/cpython/object.h (INTERNAL — unstable API):
├── Full PyTypeObject definition
├── PyNumberMethods, PySequenceMethods, PyMappingMethods
├── tp_* slot function typedefs
└── Type flag constants (Py_TPFLAGS_*)

Include/internal/pycore_object.h (INTERNAL):
├── _Py_Dealloc()
├── _Py_NewReference()
├── _Py_IsImmortal()
└── Debug-only tracking functions

Objects/object.c (IMPLEMENTATION):
├── PyObject_Repr(), PyObject_Str()
├── PyObject_Hash(), PyObject_Compare()
├── PyObject_GetAttr(), PyObject_SetAttr()
├── PyObject_RichCompare()
├── _Py_Dealloc()
└── Object protocol dispatching
```

---

## 12.18 Interview Questions — Part 12

**Q1**: What's the difference between `Py_INCREF` and `Py_XINCREF`?
**A**: `Py_INCREF` requires a non-NULL pointer (undefined behavior if NULL). `Py_XINCREF` checks for NULL first and does nothing if the pointer is NULL. Use X-variants when the pointer might be NULL.

**Q2**: Why did `Py_TYPE()` change from a macro to an inline function?
**A**: The macro `#define Py_TYPE(op) (((PyObject*)(op))->ob_type)` allowed misuse like `Py_TYPE(obj) = new_type` (assignment). The inline function returns a value (not an lvalue), preventing accidental assignment. It also enables adding safety checks or atomic operations.

**Q3**: Trace the code path of `repr(x)` from Python to C.
**A**: `repr(x)` → `builtin_repr()` in bltinmodule.c → `PyObject_Repr(x)` in object.c → `x->ob_type->tp_repr(x)` which calls the type's repr function (e.g., `long_to_decimal_string` for int, `list_repr` for list).

**Q4**: What does `_Py_Dealloc` do and when is it called?
**A**: Called when ob_refcnt reaches 0. It reads `tp_dealloc` from the object's type, optionally untracks from GC, then calls the destructor. The destructor DECREFs referenced objects (cascading) and frees the memory.

**Q5**: What is `Py_NewRef` and why was it added?
**A**: `Py_NewRef(op)` does `Py_INCREF(op); return op;` in one call. It simplifies the common pattern of incrementing a reference and storing/returning the pointer. Added in Python 3.10 for cleaner C code.

**Q6**: How are None, True, and False defined at the C level?
**A**: They're statically-allocated struct instances: `_Py_NoneStruct`, `_Py_TrueStruct`, `_Py_FalseStruct`. Macros like `Py_None` expand to `&_Py_NoneStruct`. They have immortal refcounts and are never deallocated.

**Q7**: Where would you look in the CPython source to understand how `+` works for a custom type?
**A**: The type's `tp_as_number->nb_add` slot. The call chain: BINARY_ADD bytecode → `PyNumber_Add()` in abstract.c → reads `Py_TYPE(v)->tp_as_number->nb_add` → calls the function pointer.
