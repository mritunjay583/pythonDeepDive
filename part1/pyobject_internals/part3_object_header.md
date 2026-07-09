# Part 3 — Object Header: Metadata vs Data

## 3.1 The Two Regions of Every Object

Every CPython object in memory is divided into exactly two regions:

```
┌──────────────────────────────────────────────────────────┐
│                    HEADER (Metadata)                       │
│  Fixed size. Identical structure for all objects of the   │
│  same kind (PyObject or PyVarObject).                     │
│  ┌────────────────────────────────────────────────────┐  │
│  │ ob_refcnt   (Py_ssize_t, 8 bytes)                  │  │
│  │ ob_type     (PyTypeObject*, 8 bytes)               │  │
│  │ [ob_size]   (Py_ssize_t, 8 bytes — if variable)   │  │
│  └────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────┤
│                    PAYLOAD (Data)                          │
│  Variable structure. Depends entirely on the type.        │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Type-specific fields                               │  │
│  │ (ob_fval for float, ob_digit[] for int, etc.)      │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

The header is **for the runtime** — CPython uses it to manage the object. The payload is **for the programmer** — it holds the actual value.

---

## 3.2 Why Metadata Comes First

The header is placed at the **beginning** of the memory allocation for three critical reasons:

### Reason 1: Pointer Casting

When you have a pointer to any object, it IS a pointer to the header:

```c
PyLongObject *integer = ...;
PyObject *obj = (PyObject *)integer;  // Same address!

// obj points to the SAME memory as integer
// The first bytes at that address ARE the PyObject fields
```

If data came first, you'd need to know the data size to find the header — defeating the purpose of a uniform header.

### Reason 2: Zero-Offset Access to Refcount

```c
// ob_refcnt is at offset 0
// This means: &(obj->ob_refcnt) == obj
// 
// Incrementing refcount is just:
//   *(Py_ssize_t *)obj += 1;
//
// No offset addition needed in the machine instruction
```

On x86-64, accessing offset 0 vs offset N:
```asm
; Offset 0 (refcnt first):
inc QWORD PTR [rdi]          ; direct memory increment

; If refcnt were at offset 16:
inc QWORD PTR [rdi + 16]     ; extra displacement in encoding
```

The difference is small but ob_refcnt is modified billions of times during execution.

### Reason 3: Cache Line Alignment

The header fields are the most-accessed. By placing them first, they sit at the start of the cache line that the allocation returns, maximizing the chance of a cache hit when the pointer is first dereferenced.

---

## 3.3 Memory Alignment Fundamentals

CPython must respect CPU alignment requirements. On 64-bit systems:

```
Py_ssize_t (8 bytes):  must be at address divisible by 8
Pointer    (8 bytes):  must be at address divisible by 8
int        (4 bytes):  must be at address divisible by 4
double     (8 bytes):  must be at address divisible by 8
```

The PyObject header is naturally aligned because:
- ob_refcnt (8 bytes) at offset 0 — always aligned (allocators return aligned addresses)
- ob_type (8 bytes) at offset 8 — aligned (8 is divisible by 8)

```
Address    Offset    Field        Size    Aligned?
0x1000     +0        ob_refcnt    8       ✓ (0x1000 % 8 == 0)
0x1008     +8        ob_type      8       ✓ (0x1008 % 8 == 0)
0x1010     +16       [data...]    varies  ✓ (0x1010 % 8 == 0)
```

---

## 3.4 Padding Between Header and Data

After the header, type-specific fields may introduce padding:

### No Padding Needed (Common Case)

```c
typedef struct {
    PyObject ob_base;    // 16 bytes, ends at offset 16
    double ob_fval;      // 8 bytes, needs 8-byte alignment → offset 16 ✓
} PyFloatObject;
// Total: 24 bytes, no padding
```

### Padding Required

```c
typedef struct {
    PyObject ob_base;    // 16 bytes
    int some_flag;       // 4 bytes at offset 16
    double some_value;   // 8 bytes, needs 8-byte alignment → offset 24
    // 4 bytes of padding inserted between flag and value!
} SomeObject;
```

```
Memory layout with padding:
┌──────────────────────────────────────┐
│ ob_refcnt          (8 bytes) +0      │
│ ob_type            (8 bytes) +8      │
│ some_flag          (4 bytes) +16     │
│ ████ PADDING ████  (4 bytes) +20     │  ← wasted space
│ some_value         (8 bytes) +24     │
└──────────────────────────────────────┘
Total: 32 bytes (4 bytes wasted)
```

CPython type authors order fields carefully to minimize padding. Larger fields come first (after the header) to maintain alignment without gaps.

---

## 3.5 The Optional GC Header

Objects that participate in cyclic garbage collection get an ADDITIONAL header prepended BEFORE the PyObject header:

```c
// Include/internal/pycore_gc.h (simplified)
typedef struct {
    uintptr_t _gc_next;    // 8 bytes — linked list of tracked objects
    uintptr_t _gc_prev;    // 8 bytes — doubly-linked list
} PyGC_Head;
```

```
Complete memory layout for a GC-tracked object (e.g., a list):

         ┌─────────────────────────────────────┐
         │  GC Header (16 bytes)                │
         │  _gc_next: → next tracked object     │
         │  _gc_prev: → prev tracked object     │
    ───→ ├─────────────────────────────────────┤ ← This is the "official" address
         │  PyVarObject Header (24 bytes)       │    (what id() returns)
         │  ob_refcnt: N                        │
         │  ob_type: → PyList_Type              │
         │  ob_size: length                     │
         ├─────────────────────────────────────┤
         │  Payload                             │
         │  ob_item: → pointer array            │
         │  allocated: capacity                 │
         └─────────────────────────────────────┘
```

The pointer that Python code sees (`id()`) points to the PyObject header, NOT the GC header. The GC header is hidden "behind" the object — at a negative offset.

```c
// Getting GC header from object pointer:
#define AS_GC(o) ((PyGC_Head *)(o) - 1)

// Getting object from GC header:
#define FROM_GC(g) ((PyObject *)((g) + 1))
```

---

## 3.6 Object Lifetime and the Header

The header orchestrates the entire object lifetime:

### Birth

```c
// 1. Memory allocated (malloc or pymalloc)
PyObject *obj = (PyObject *)PyObject_Malloc(size);

// 2. Header initialized
obj->ob_refcnt = 1;           // Born with one reference
obj->ob_type = &SomeType;    // Knows its type from birth

// 3. Type-specific initialization
// ... fill in payload fields ...
```

### Life

```c
// Reference count goes up and down as the object is used:
Py_INCREF(obj);   // Someone new points to it
Py_DECREF(obj);   // Someone stopped pointing to it

// Type pointer is read for every operation:
obj->ob_type->tp_repr(obj);    // __repr__
obj->ob_type->tp_hash(obj);    // __hash__
```

### Death

```c
// When ob_refcnt reaches 0:
void _Py_Dealloc(PyObject *op) {
    destructor dealloc = Py_TYPE(op)->tp_dealloc;
    // Read the type's destructor function pointer from the header...
    (*dealloc)(op);  // ...and call it
    // tp_dealloc frees type-specific resources, then the memory
}
```

The header is the LAST thing freed — it's needed until the very end to find the deallocator.

---

## 3.7 Debug Build: Extra Header Fields

In debug builds (`Py_TRACE_REFS`), the header grows:

```c
// Debug-only fields prepended:
typedef struct _object {
    struct _object *_ob_next;    // 8 bytes — all-objects linked list
    struct _object *_ob_prev;    // 8 bytes — doubly-linked
    Py_ssize_t ob_refcnt;        // 8 bytes — normal refcnt
    PyTypeObject *ob_type;       // 8 bytes — normal type
} PyObject;
```

```
Debug build object layout:
┌───────────────────────────────────┐
│ _ob_next  (8 bytes)  +0          │  ← debug only
│ _ob_prev  (8 bytes)  +8          │  ← debug only
│ ob_refcnt (8 bytes)  +16         │  ← normal header starts here
│ ob_type   (8 bytes)  +24         │
├───────────────────────────────────┤
│ Payload...                        │
└───────────────────────────────────┘
Total header: 32 bytes (vs 16 in release)
```

This lets developers iterate over ALL live objects to find leaks — but doubles header cost.

---

## 3.8 Header Size Summary

| Build / Object Kind | Header Size (64-bit) |
|---------------------|---------------------|
| Release, fixed-size (PyObject) | 16 bytes |
| Release, variable-size (PyVarObject) | 24 bytes |
| Release, GC-tracked fixed | 16 + 16 = 32 bytes |
| Release, GC-tracked variable | 24 + 16 = 40 bytes |
| Debug, fixed-size | 32 bytes |
| Debug, variable-size | 40 bytes |
| Debug, GC-tracked variable | 56 bytes |

---

## 3.9 Source References

| File | What's Defined |
|------|---------------|
| `Include/object.h` | PyObject struct, PyObject_HEAD macro |
| `Include/cpython/object.h` | Internal layout details |
| `Include/internal/pycore_gc.h` | PyGC_Head struct |
| `Include/internal/pycore_object.h` | _Py_Dealloc, header initialization |
| `Objects/object.c` | Object protocol, deallocation |

---

## 3.10 Interview Questions — Part 3

**Q1**: Why does the metadata header come BEFORE the data payload in CPython objects?
**A**: So that a pointer to any object is also a pointer to its header. This enables pointer casting (any `SomeType*` can be cast to `PyObject*`) and zero-offset access to ob_refcnt.

**Q2**: What is the GC header and where is it in memory relative to the object?
**A**: PyGC_Head sits BEFORE the PyObject header (at a negative offset). It contains next/prev pointers for the doubly-linked list of GC-tracked objects. The "official" object address (id()) points past the GC header.

**Q3**: How do you go from a PyObject pointer to its GC header?
**A**: `((PyGC_Head *)obj) - 1` — subtract the size of one PyGC_Head from the object pointer. The macro `AS_GC(o)` does this.

**Q4**: What causes padding in CPython object structs?
**A**: CPU alignment requirements. If a field requires N-byte alignment but the preceding field ends at a non-N-aligned offset, the compiler inserts padding bytes.

**Q5**: Why is ob_refcnt the first field (offset 0) rather than ob_type?
**A**: ob_refcnt is modified far more often (every reference creation/destruction). At offset 0, no displacement is needed in the machine instruction, saving a tiny amount of time per operation — significant given billions of refcount operations per second.

**Q6**: What happens to the header during object deallocation?
**A**: The header must remain valid until the end because `tp_dealloc` is read FROM the header (`Py_TYPE(op)->tp_dealloc`) to find the correct destructor. Only after the destructor runs is the header memory freed.

**Q7**: How much larger is the debug build header compared to release?
**A**: Debug adds `_ob_next` and `_ob_prev` pointers (16 bytes total) for an all-objects linked list, making the base header 32 bytes vs 16 bytes in release.
