# Part 17 — Historical Evolution of PyObject

## 17.1 Overview of Changes

The PyObject system has evolved significantly across Python versions, driven by performance needs, multi-core hardware trends, and the free-threading project.

```
Timeline:
┌────────────────────────────────────────────────────────────┐
│ Python 2.x    │ Classic layout, no GC initially, then GC   │
│ Python 3.0    │ Unicode redesign, type system changes      │
│ Python 3.4    │ PEP 442: Safe object finalization          │
│ Python 3.8    │ Vectorcall protocol, PyObject_Vectorcall   │
│ Python 3.9    │ Py_SET_TYPE, Py_SET_SIZE (setter functions)│
│ Python 3.10   │ Py_NewRef, Py_XNewRef                     │
│ Python 3.11   │ Specializing adaptive interpreter          │
│ Python 3.12   │ Immortal objects (PEP 683)                 │
│ Python 3.13   │ Free-threaded build (PEP 703, experimental)│
│ Python 3.14+  │ Per-interpreter GIL (ongoing)              │
└────────────────────────────────────────────────────────────┘
```

---

## 17.2 Python 2 → Python 3: The Big Shift

### int/long Unification

```c
// Python 2: Two integer types
typedef struct {
    PyObject_HEAD
    long ob_ival;       // Fixed-size C long
} PyIntObject;          // For small integers

typedef struct {
    PyObject_VAR_HEAD
    digit ob_digit[1];  // Arbitrary precision
} PyLongObject;         // For large integers

// Python 3: Only PyLongObject remains
// ALL integers are arbitrary precision (PyLongObject)
// The "small int" behavior is handled by caching, not a separate type
```

Impact on object size:
```
Python 2 int(42):  12 bytes (32-bit) or 16 bytes (64-bit) — fixed
Python 3 int(42):  28 bytes (64-bit) — variable precision
```

### String Representation

```c
// Python 2: 
typedef struct {
    PyObject_VAR_HEAD
    long ob_shash;
    int ob_sstate;       // Interned state
    char ob_sval[1];     // Byte string
} PyStringObject;        // bytes-like

// Python 3 (3.0-3.2):
// PyUnicodeObject with Py_UNICODE* buffer (UCS-2 or UCS-4)
// Wasteful: ASCII strings stored in 4 bytes/char on UCS-4 builds

// Python 3.3+ (PEP 393 "Flexible String Representation"):
// Multiple representations based on content:
//   - ASCII/Latin1: 1 byte per character
//   - UCS-2: 2 bytes per character  
//   - UCS-4: 4 bytes per character
// Compact form stores data inline after the struct
```

### ob_type and Classic Classes

```c
// Python 2: Both "old-style" and "new-style" classes existed
// Old-style: instances had ob_type == &PyInstance_Type (not the actual class!)
// New-style (class Foo(object)): proper type pointer

// Python 3: Only new-style classes
// Every instance's ob_type points to its actual class type object
// Simpler, more uniform, better performance
```

---

## 17.3 Python 3.4: PEP 442 — Safe Object Finalization

Before 3.4, objects in reference cycles with `__del__` methods couldn't be collected (put in `gc.garbage`). PEP 442 introduced a safe finalization protocol:

```c
// New tp_finalize slot (replaces old tp_del):
typedef void (*destructor)(PyObject *);

// The GC can now:
// 1. Call tp_finalize on objects in cycles (runs __del__)
// 2. THEN break the cycle and deallocate
// 3. Even if __del__ resurrects the object, it's handled safely
```

---

## 17.4 Python 3.8: Vectorcall Protocol (PEP 590)

A faster calling convention that avoids creating a tuple for arguments:

```c
// Old calling convention (always creates args tuple):
PyObject *tp_call(PyObject *callable, PyObject *args, PyObject *kwargs);

// New vectorcall (passes array of pointers — no tuple creation):
typedef PyObject *(*vectorcallfunc)(
    PyObject *callable,
    PyObject *const *args,    // Array of argument pointers
    size_t nargsf,            // Number of positional args + flags
    PyObject *kwnames         // Tuple of keyword argument names
);

// Added to PyTypeObject:
Py_ssize_t tp_vectorcall_offset;  // Offset in instance where vectorcallfunc is stored
```

Impact: Function calls 1.5-2× faster by avoiding tuple allocation for arguments.

---

## 17.5 Python 3.9: Setter Functions

Direct field access through macros was deprecated in favor of inline functions:

```c
// Python ≤ 3.8 (macro — allows misuse):
#define Py_TYPE(ob) (((PyObject *)(ob))->ob_type)
// Could be used as lvalue: Py_TYPE(obj) = new_type;  // BAD!

// Python 3.9+ (inline function — returns rvalue):
static inline PyTypeObject* Py_TYPE(PyObject *ob) {
    return ob->ob_type;
}
// Py_TYPE(obj) = new_type;  // COMPILE ERROR!

// New setter function:
static inline void Py_SET_TYPE(PyObject *ob, PyTypeObject *type) {
    ob->ob_type = type;
}
// Same for Py_SET_SIZE, Py_SET_REFCNT
```

Why: Enables adding atomic operations, assertions, and future changes without breaking ABI.

---

## 17.6 Python 3.10: Py_NewRef / Py_XNewRef

```c
// New convenience functions:
static inline PyObject* Py_NewRef(PyObject *ob) {
    Py_INCREF(ob);
    return ob;
}

// Eliminates the 2-line INCREF-then-assign pattern:
// Before: Py_INCREF(value); return value;
// After:  return Py_NewRef(value);
```

---

## 17.7 Python 3.11: Specializing Adaptive Interpreter

The interpreter now specializes bytecodes based on observed types:

```c
// LOAD_ATTR becomes LOAD_ATTR_INSTANCE_VALUE when the type is stable
// This caches the attribute offset in the object

// Impact on PyObject: Type objects gained version tags
struct _typeobject {
    // ...
    unsigned int tp_version_tag;  // Changes when type is modified
    // Used to validate cached specializations
};
```

Also introduced in 3.11: **zero-cost exception handling** changed frame layout, and the interpreter eliminated per-instruction refcount overhead for some operations through "quickened" bytecodes.

---

## 17.8 Python 3.12: Immortal Objects (PEP 683)

The most significant change to ob_refcnt since Python's creation:

```c
// Before 3.12: Every Py_INCREF/Py_DECREF modifies ob_refcnt
// Problem: None, True, False are referenced millions of times
//   → constant cache line writes
//   → prevents safe sharing across sub-interpreters

// Solution: Immortal refcount — a special value that's never modified
#define _Py_IMMORTAL_REFCNT  /* very large value */

static inline int _Py_IsImmortal(PyObject *op) {
    // Check if refcount is in the "immortal" range
    return op->ob_refcnt >= _Py_IMMORTAL_REFCNT;
}

// Py_INCREF now checks:
static inline void Py_INCREF(PyObject *op) {
    if (_Py_IsImmortal(op)) return;  // ← NEW: skip for immortals
    op->ob_refcnt++;
}
```

Objects made immortal:
- `None`, `True`, `False`
- Small integers (-5 to 256)
- Interned strings (common identifiers)
- Type objects (int, str, list, etc.)
- Other frequently-shared singletons

Benefits:
1. No cache line bouncing for hot objects
2. Safe to share across sub-interpreters without synchronization
3. Enables per-interpreter GIL
4. Slight overhead (one comparison per INCREF/DECREF) but net positive

---

## 17.9 Python 3.12: Refcount Split (Implementation Detail)

```c
// On 64-bit, the refcount is conceptually split:
union {
    Py_ssize_t ob_refcnt;           // Full 64-bit refcount
    struct {
        uint32_t ob_refcnt_split[2]; // [0]=local, [1]=shared (or immortal flag)
    };
};

// The upper 32 bits encode immortality:
// If upper bits indicate immortal → skip modification
// This avoids a separate flag field
```

---

## 17.10 Python 3.13: Free-Threaded Build (PEP 703)

The experimental free-threaded (no-GIL) build fundamentally changes refcounting:

```c
// Traditional (with GIL): Simple increment
op->ob_refcnt++;  // Safe because GIL prevents concurrent access

// Free-threaded (no GIL): Atomic operations needed
_Py_atomic_add_ssize(&op->ob_refcnt, 1);  // Thread-safe

// Additional changes in 3.13 free-threaded build:
// - Biased reference counting (each thread has a local refcount)
// - Deferred reference counting for some objects
// - Object-level locks for certain operations
// - Immortal objects even more critical (avoid contention)
```

### Biased Reference Counting

```c
// Each object has a "local" refcount per owning thread
// and a "shared" refcount for cross-thread references:
struct _object {
    // Simplified conceptual model:
    _Py_atomic_ssize_t ob_refcnt;      // Shared refcount (atomic)
    uint32_t ob_ref_local;              // Local refcount (thread-specific, fast)
    uint32_t ob_tid;                    // Owning thread ID
    PyTypeObject *ob_type;
};

// Local INCREF (fast, no atomic):
if (current_thread_id == op->ob_tid) {
    op->ob_ref_local++;  // No atomic needed!
} else {
    _Py_atomic_add(&op->ob_refcnt, 1);  // Cross-thread: atomic
}
```

---

## 17.11 Python 3.13: Per-Interpreter GIL (PEP 684)

Each sub-interpreter can have its own GIL:

```c
// Implication for objects:
// - Immortal objects (None, True, type objects) can be shared across interpreters
//   without coordination (refcount never changes)
// - Mutable objects CANNOT be shared — each interpreter has its own heap
// - Type objects: shared (immortal) vs per-interpreter (heap types)
```

---

## 17.12 Future Directions (3.14+)

### Ongoing Work

1. **More objects becoming immortal**: Extension to cover more common constants
2. **Deferred refcounting**: Some objects don't need immediate refcount updates
3. **Tagged pointers** (proposed): Small integers stored in the pointer itself
4. **Memory layout optimization**: Better cache behavior for common access patterns
5. **Compact object headers**: Reducing the 16-byte minimum

### Potential Future Changes

```c
// Tagged pointers (hypothetical):
// Instead of: x = PyLong_FromLong(42);  // 28-byte heap allocation
// Maybe:      x = (PyObject *)((42 << 1) | 1);  // Integer in the pointer!
// Saves: allocation entirely for small integers

// Compact headers (hypothetical):
// Instead of 8-byte refcnt + 8-byte type:
// Maybe: 4-byte refcnt + 4-byte type_index → 8 bytes total
// (Type index into a type table instead of full pointer)
```

---

## 17.13 Version Compatibility Summary

| Feature | Added | Removed/Changed |
|---------|-------|----------------|
| PyObject basic layout | 1.x | Still present |
| Cyclic GC | 2.0 | Enhanced in 3.x |
| New-style classes only | 3.0 | Classic classes removed |
| PEP 393 strings | 3.3 | Old unicode buffer removed |
| PEP 442 finalization | 3.4 | Safe __del__ in cycles |
| `Py_SETREF` | 3.6 | — |
| Vectorcall | 3.8 | — |
| `Py_SET_TYPE/SIZE` | 3.9 | Macro lvalue usage deprecated |
| `Py_NewRef` | 3.10 | — |
| Specialized interpreter | 3.11 | Ongoing improvements |
| Immortal objects | 3.12 | — |
| Free-threaded build | 3.13 | Experimental |
| Per-interpreter GIL | 3.12+ | Ongoing |

---

## 17.14 Source References

| Feature | PEP | Key Files |
|---------|-----|-----------|
| Flexible strings | PEP 393 | `Objects/unicodeobject.c` |
| Safe finalization | PEP 442 | `Modules/gcmodule.c` |
| Vectorcall | PEP 590 | `Include/cpython/abstract.h` |
| Immortal objects | PEP 683 | `Include/refcount.h`, `Include/internal/pycore_global_objects.h` |
| Free-threading | PEP 703 | `Include/internal/pycore_object.h` |
| Per-interp GIL | PEP 684 | `Python/pystate.c` |

---

## 17.15 Interview Questions — Part 17

**Q1**: What changed about integers between Python 2 and Python 3?
**A**: Python 2 had two types: `int` (fixed C long, ~4-8 bytes) and `long` (arbitrary precision). Python 3 unified them — all integers are arbitrary precision (PyLongObject). This simplified the type system but increased memory usage for small integers (28 bytes vs 8-16 bytes).

**Q2**: What is PEP 683 (Immortal Objects) and what problem does it solve?
**A**: PEP 683 (Python 3.12) makes certain objects "immortal" — their refcount is never modified. This solves: (1) cache line bouncing for frequently-shared objects (None, True), (2) enables safe sharing across sub-interpreters, (3) prepares for free-threading by eliminating contention on hot refcounts.

**Q3**: Why did Py_TYPE change from a macro to an inline function in Python 3.9?
**A**: The macro allowed `Py_TYPE(obj) = new_type` (lvalue assignment), which bypassed any future safety checks. The inline function returns an rvalue, forcing use of `Py_SET_TYPE()` for assignment. This enables adding atomic operations for free-threading without breaking code.

**Q4**: How does the free-threaded build (PEP 703) change reference counting?
**A**: Without the GIL, concurrent INCREF/DECREF from multiple threads requires atomic operations. The free-threaded build uses biased reference counting: thread-local fast path (no atomics if you own the object) and shared atomic path for cross-thread references. Immortal objects bypass all this.

**Q5**: What is the vectorcall protocol and why was it introduced?
**A**: Vectorcall (PEP 590, Python 3.8) passes function arguments as a C array of `PyObject*` pointers instead of packing them into a tuple. This avoids allocating a tuple for every function call, giving ~1.5-2× speedup for function calls.

**Q6**: How did PEP 393 change string memory usage?
**A**: Before 3.3, strings were stored as fixed-width arrays (2 or 4 bytes per character depending on build). PEP 393 introduced flexible representation: ASCII/Latin1 uses 1 byte/char, BMP uses 2 bytes/char, full Unicode uses 4 bytes/char. Each string picks the narrowest sufficient width. This typically saves 2-4× memory for ASCII-heavy code.

**Q7**: What are the implications of per-interpreter GIL for object sharing?
**A**: With per-interpreter GIL, each interpreter has its own heap of mutable objects (not shared). Only immortal objects (None, types, etc.) can be safely shared across interpreters because their refcounts are never modified. Heap types and user objects must be interpreter-local.
