# Part 16 — Macros and APIs for Object Management

## 16.1 Overview

CPython provides a layered set of macros and functions for creating, managing, and destroying objects. Understanding these is essential for C extension development and for reading CPython source code.

```
Layer 1 (Highest): PyObject_New / PyObject_GC_New
  → Allocate + initialize header

Layer 2: PyObject_Malloc / PyObject_Free
  → Raw memory allocation (pymalloc or system)

Layer 3: Py_INCREF / Py_DECREF / Py_NewRef / Py_SETREF
  → Reference count management

Layer 4 (Lowest): _Py_Dealloc / tp_dealloc / tp_free
  → Object destruction
```

---

## 16.2 Object Creation: PyObject_New

Allocates memory and initializes the PyObject header:

```c
// Include/objimpl.h
#define PyObject_New(type, typeobj) \
    ((type *)_PyObject_New(typeobj))

PyObject *_PyObject_New(PyTypeObject *tp) {
    // 1. Allocate tp_basicsize bytes:
    PyObject *op = (PyObject *)PyObject_Malloc(tp->tp_basicsize);
    if (op == NULL)
        return PyErr_NoMemory();
    
    // 2. Initialize header:
    _PyObject_Init(op, tp);
    //   → op->ob_refcnt = 1;
    //   → op->ob_type = tp;
    //   → Py_INCREF(tp) if heap type
    
    return op;
}
```

Usage:
```c
// Creating a new float:
PyFloatObject *op = PyObject_New(PyFloatObject, &PyFloat_Type);
op->ob_fval = 3.14;
return (PyObject *)op;
```

---

## 16.3 Variable-Size Object Creation: PyObject_NewVar

For PyVarObject-based types with inline variable data:

```c
// Include/objimpl.h
#define PyObject_NewVar(type, typeobj, n) \
    ((type *)_PyObject_NewVar(typeobj, n))

PyObject *_PyObject_NewVar(PyTypeObject *tp, Py_ssize_t nitems) {
    // Calculate total size:
    size_t size = _PyObject_VAR_SIZE(tp, nitems);
    //          = tp->tp_basicsize + nitems * tp->tp_itemsize
    
    // Allocate:
    PyObject *op = (PyObject *)PyObject_Malloc(size);
    if (op == NULL)
        return PyErr_NoMemory();
    
    // Initialize header:
    _PyObject_InitVar((PyVarObject *)op, tp, nitems);
    //   → op->ob_refcnt = 1;
    //   → op->ob_type = tp;
    //   → op->ob_size = nitems;
    
    return op;
}
```

Usage:
```c
// Creating a new tuple of 3 elements:
PyTupleObject *op = (PyTupleObject *)PyObject_NewVar(
    PyTupleObject, &PyTuple_Type, 3);
// op->ob_size = 3
// op->ob_item[0], [1], [2] ready for assignment
```

---

## 16.4 GC-Tracked Object Creation: PyObject_GC_New

For objects that may participate in reference cycles:

```c
// Include/objimpl.h
#define PyObject_GC_New(type, typeobj) \
    ((type *)_PyObject_GC_New(typeobj))

PyObject *_PyObject_GC_New(PyTypeObject *tp) {
    // 1. Allocate: GC_Head + basicsize
    size_t size = sizeof(PyGC_Head) + tp->tp_basicsize;
    PyGC_Head *gc = (PyGC_Head *)PyObject_Malloc(size);
    
    // 2. Initialize GC header:
    gc->_gc_next = 0;  // Not yet tracked
    gc->_gc_prev = 0;
    
    // 3. Get object pointer (past GC header):
    PyObject *op = FROM_GC(gc);
    
    // 4. Initialize PyObject header:
    _PyObject_Init(op, tp);
    
    return op;
}
```

And the variable-size version:
```c
#define PyObject_GC_NewVar(type, typeobj, n) \
    ((type *)_PyObject_GC_NewVar(typeobj, n))
```

After creation, you must explicitly track:
```c
PyObject *list = PyObject_GC_New(PyListObject, &PyList_Type);
// ... initialize fields ...
_PyObject_GC_TRACK(list);  // Add to GC tracking list
```

---

## 16.5 Reference Counting: Py_INCREF / Py_DECREF

### Py_INCREF — Increment Reference Count

```c
// Include/refcount.h
static inline Py_ALWAYS_INLINE void Py_INCREF(PyObject *op) {
    #ifdef Py_REF_DEBUG
    _Py_INC_REFTOTAL();
    #endif
    
    // Immortal check (3.12+):
    if (_Py_IsImmortal(op)) {
        return;
    }
    op->ob_refcnt++;
}
```

**Contract**: `op` MUST NOT be NULL. Use `Py_XINCREF` if it might be NULL.

### Py_DECREF — Decrement Reference Count

```c
static inline void Py_DECREF(PyObject *op) {
    #ifdef Py_REF_DEBUG
    _Py_DEC_REFTOTAL();
    #endif
    
    if (_Py_IsImmortal(op)) {
        return;
    }
    if (--op->ob_refcnt == 0) {
        _Py_Dealloc(op);
    }
}
```

**Contract**: `op` MUST NOT be NULL. `ob_refcnt` MUST be > 0.

---

## 16.6 NULL-Safe Variants: Py_XINCREF / Py_XDECREF

```c
// Include/refcount.h

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

When to use which:
```c
// Use Py_INCREF when pointer is guaranteed non-NULL:
Py_INCREF(Py_None);         // None is always valid
Py_INCREF(self->required);  // Field that's always set

// Use Py_XINCREF when pointer might be NULL:
Py_XINCREF(self->optional);  // Field that might not be set
Py_XINCREF(kwargs);          // kwargs might be NULL
```

---

## 16.7 Py_NewRef / Py_XNewRef (Python 3.10+)

INCREF and return in one operation:

```c
// Include/refcount.h

static inline PyObject* Py_NewRef(PyObject *ob) {
    Py_INCREF(ob);
    return ob;
}

static inline PyObject* Py_XNewRef(PyObject *ob) {
    Py_XINCREF(ob);
    return ob;  // May be NULL
}
```

Simplifies common patterns:
```c
// BEFORE (verbose, error-prone):
PyObject *result;
result = self->value;
Py_INCREF(result);
return result;

// AFTER (one line):
return Py_NewRef(self->value);

// Assigning with INCREF:
// BEFORE:
Py_INCREF(value);
self->field = value;

// AFTER:
self->field = Py_NewRef(value);
```

---

## 16.8 Py_SETREF (Python 3.6+)

Safely replace a pointer field — DECREFs old, stores new:

```c
// Include/refcount.h

#define Py_SETREF(op, op2)              \
    do {                                 \
        PyObject *_py_tmp = _PyObject_CAST(op); \
        (op) = (op2);                    \
        Py_DECREF(_py_tmp);             \
    } while (0)

// NULL-safe version:
#define Py_XSETREF(op, op2)             \
    do {                                 \
        PyObject *_py_tmp = _PyObject_CAST(op); \
        (op) = (op2);                    \
        Py_XDECREF(_py_tmp);           \
    } while (0)
```

Why this exists — the naive approach is DANGEROUS:
```c
// WRONG (use-after-free if old == new):
Py_DECREF(self->field);     // If field points to same object as value,
self->field = value;         // this DECREF might free it!
Py_INCREF(value);           // Accessing freed memory!

// WRONG (doesn't handle self-referencing):
Py_XDECREF(self->field);
self->field = value;
Py_XINCREF(value);

// CORRECT (store first, then DECREF old):
Py_SETREF(self->field, Py_NewRef(value));
// Or equivalently:
PyObject *old = self->field;
self->field = Py_NewRef(value);
Py_DECREF(old);
```

---

## 16.9 Py_CLEAR (Python 3.0+)

Sets a field to NULL and DECREFs the old value — safe for cleanup:

```c
// Include/refcount.h

#define Py_CLEAR(op)                    \
    do {                                 \
        PyObject *_py_tmp = _PyObject_CAST(op); \
        if (_py_tmp != NULL) {          \
            (op) = NULL;                 \
            Py_DECREF(_py_tmp);         \
        }                                \
    } while (0)
```

Why set to NULL first:
```c
// If Py_DECREF triggers deallocation that somehow accesses self->field,
// it would see NULL (safe) rather than a dangling pointer (crash).

// Usage in tp_clear (GC cycle breaking):
static int mytype_clear(MyObject *self) {
    Py_CLEAR(self->callback);  // Safe: sets to NULL, then DECREFs
    Py_CLEAR(self->data);
    return 0;
}
```

---

## 16.10 Memory Allocation APIs

### Layer 1: Object-oriented (preferred for Python objects)

```c
// For non-GC objects:
PyObject *PyObject_Malloc(size_t n);    // Allocate raw bytes
void PyObject_Free(void *p);            // Free
void *PyObject_Realloc(void *p, size_t n);  // Resize

// For GC-tracked objects:
void *PyObject_GC_Malloc(size_t n);     // Allocate with GC header space
void PyObject_GC_Del(void *p);          // Free GC-tracked object
```

### Layer 2: Raw memory (for non-object data)

```c
// For auxiliary data (arrays, buffers, not Python objects):
void *PyMem_Malloc(size_t n);           // Like malloc()
void *PyMem_Calloc(size_t n, size_t s); // Like calloc()
void *PyMem_Realloc(void *p, size_t n); // Like realloc()
void PyMem_Free(void *p);              // Like free()

// Usage: the item array of a list
list->ob_item = PyMem_Calloc(size, sizeof(PyObject *));
```

### Layer 3: Raw system (avoid — use only for special cases)

```c
// Direct system calls (bypasses Python's memory tracking):
void *PyMem_RawMalloc(size_t n);
void *PyMem_RawRealloc(void *p, size_t n);
void PyMem_RawFree(void *p);
// Only needed when the GIL is NOT held
```

---

## 16.11 GC Tracking and Untracking

```c
// Start tracking (after initialization):
void _PyObject_GC_TRACK(PyObject *op);
// Adds to the GC's linked list of tracked objects

// Stop tracking (before deallocation):
void _PyObject_GC_UNTRACK(PyObject *op);
// Removes from GC's linked list

// Check if tracked:
int PyObject_GC_IsTracked(PyObject *op);

// The public API versions:
void PyObject_GC_Track(void *op);
void PyObject_GC_UnTrack(void *op);
```

Pattern in type implementations:
```c
static MyObject *MyObject_new(PyTypeObject *type) {
    MyObject *self = PyObject_GC_New(MyObject, type);
    // ... initialize fields to safe values (NULL) ...
    self->data = NULL;
    self->callback = NULL;
    
    // Only track AFTER all fields are initialized:
    _PyObject_GC_TRACK(self);
    return self;
}

static void MyObject_dealloc(MyObject *self) {
    // Untrack FIRST (GC might run during DECREF):
    PyObject_GC_UnTrack(self);
    
    // Then clean up:
    Py_CLEAR(self->data);
    Py_CLEAR(self->callback);
    
    // Free:
    Py_TYPE(self)->tp_free((PyObject *)self);
}
```

---

## 16.12 Object Initialization Helpers

```c
// Initialize a pre-allocated PyObject:
PyObject *PyObject_Init(PyObject *op, PyTypeObject *type);
// Sets: op->ob_refcnt = 1, op->ob_type = type

// Initialize a pre-allocated PyVarObject:
PyVarObject *PyObject_InitVar(PyVarObject *op, PyTypeObject *type, Py_ssize_t size);
// Sets: refcnt = 1, type = type, ob_size = size
```

---

## 16.13 Quick Reference Table

| Macro/Function | Purpose | NULL-safe? | When to Use |
|---------------|---------|------------|-------------|
| `Py_INCREF(op)` | Add reference | No | Know pointer is valid |
| `Py_DECREF(op)` | Remove reference | No | Know pointer is valid |
| `Py_XINCREF(op)` | Add reference | Yes | Pointer might be NULL |
| `Py_XDECREF(op)` | Remove reference | Yes | Pointer might be NULL |
| `Py_NewRef(op)` | INCREF + return | No | Return with ownership |
| `Py_XNewRef(op)` | XINCREF + return | Yes | Return nullable |
| `Py_SETREF(lhs, rhs)` | Replace pointer | No | Assign new value to field |
| `Py_XSETREF(lhs, rhs)` | Replace pointer | Yes (old) | Assign, old might be NULL |
| `Py_CLEAR(op)` | NULL + DECREF | Yes | Cleanup in dealloc/clear |
| `PyObject_New` | Alloc + init | N/A | Create non-GC object |
| `PyObject_GC_New` | Alloc + init + GC | N/A | Create GC-tracked object |
| `PyObject_NewVar` | Variable alloc | N/A | Create var-size non-GC |
| `PyObject_GC_NewVar` | Variable + GC | N/A | Create var-size GC |

---

## 16.14 Source References

| File | Contents |
|------|----------|
| `Include/refcount.h` | All refcount macros: INCREF, DECREF, SETREF, CLEAR, NewRef |
| `Include/objimpl.h` | PyObject_New, PyObject_NewVar, GC variants |
| `Include/pymem.h` | PyMem_Malloc, PyMem_Free (raw memory) |
| `Objects/obmalloc.c` | PyObject_Malloc/Free implementation |
| `Modules/gcmodule.c` | GC_New, GC_Track, GC_Del |
| `Include/internal/pycore_gc.h` | Internal GC macros |
| `Include/internal/pycore_object.h` | _PyObject_Init, _Py_NewReference |

---

## 16.15 Interview Questions — Part 16

**Q1**: What's the difference between `PyObject_New` and `PyObject_GC_New`?
**A**: `PyObject_New` allocates `tp_basicsize` bytes and initializes the header (refcnt=1, type). `PyObject_GC_New` allocates extra space for the GC header (16 bytes), initializes both headers, and prepares for GC tracking. Use GC_New for types that can be part of reference cycles (contain pointers to other Python objects).

**Q2**: Why does `Py_SETREF` exist? Why not just DECREF then assign?
**A**: DECREF-then-assign is unsafe when the old and new values might be the same object, or when DECREF triggers deallocation that accesses the field. `Py_SETREF` stores the new value first (making the field valid), then DECREFs the old value. This prevents dangling pointer access.

**Q3**: What does `Py_CLEAR(self->field)` do and why set to NULL before DECREF?
**A**: It saves the pointer, sets the field to NULL, then DECREFs the saved pointer. Setting to NULL first protects against re-entrant access — if the DECREF triggers code that reads `self->field`, it sees NULL (handled) rather than a freed pointer (crash).

**Q4**: When should you use `PyMem_Malloc` vs `PyObject_Malloc`?
**A**: `PyObject_Malloc` is for Python object memory (tracked by pymalloc). `PyMem_Malloc` is for auxiliary data that isn't a Python object (arrays, buffers, strings). Both use pymalloc for small allocations, but they use different memory pools for tracking purposes.

**Q5**: Why must you call `_PyObject_GC_TRACK` only AFTER initializing all fields?
**A**: The GC might run at any time after tracking begins. If the GC calls `tp_traverse` on a partially-initialized object, it would follow uninitialized pointers (garbage values) leading to crashes. Initialize all pointer fields to NULL/valid values first.

**Q6**: Explain the "stolen reference" convention and why PyList_SetItem uses it.
**A**: A "stolen reference" means the callee takes ownership — the caller must NOT DECREF after passing. `PyList_SetItem` steals because it directly stores the pointer in the list slot. If it INCREF'd instead, the caller would need a DECREF for balance — but many callers create objects specifically for the list (refcnt already 1), making steal-semantics avoid an INCREF+DECREF pair.

**Q7**: What's the difference between `PyObject_Free` and `PyObject_GC_Del`?
**A**: `PyObject_Free` frees the memory at the given pointer. `PyObject_GC_Del` first adjusts the pointer back to include the GC header (pointer - sizeof(PyGC_Head)), removes from the GC tracking list, then calls `PyObject_Free` on the GC header address.
