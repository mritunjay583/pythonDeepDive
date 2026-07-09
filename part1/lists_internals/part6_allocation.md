# Part 6 — Allocation (How Lists Get Memory)

## 6.1 The Memory Hierarchy

When CPython needs memory for a list or its pointer array, the request flows through multiple layers:

```
┌─────────────────────────────────────────┐
│          Python Code: a = [1,2,3]       │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│    Object Allocator (PyObject_Malloc)   │  ← Layer 3
│    Handles objects < 512 bytes          │
│    Uses Pools (4KB) within Arenas(256KB)│
└────────────────────┬────────────────────┘
                     │ (if > 512 bytes)
                     ▼
┌─────────────────────────────────────────┐
│    PyMem_Malloc / PyMem_Realloc         │  ← Layer 2
│    Raw memory allocator                 │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│    System malloc / realloc              │  ← Layer 1
│    (glibc, jemalloc, etc.)              │
└────────────────────┬────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────┐
│    OS Kernel (brk, mmap)                │  ← Layer 0
└─────────────────────────────────────────┘
```

---

## 6.2 What Gets Allocated for a List

Creating `a = [10, 20, 30]` requires TWO separate allocations:

### Allocation 1: The PyListObject struct

```
Size: 40 bytes (+ GC header) ≈ 64 bytes total
Allocator: PyObject_GC_New → pymalloc (< 512 bytes, fits in a pool)
Lifetime: from creation until refcnt hits 0

┌──────────────────────────────┐
│ GC Header (24 bytes)         │  ← For cycle detection
├──────────────────────────────┤
│ ob_refcnt  (8 bytes)         │
│ ob_type    (8 bytes)         │
│ ob_size    (8 bytes)         │
│ ob_item    (8 bytes)         │
│ allocated  (8 bytes)         │
└──────────────────────────────┘
Total: ~64 bytes → pymalloc 64-byte pool
```

### Allocation 2: The ob_item pointer array

```
Size: allocated * 8 bytes (varies)
Allocator: PyMem_Realloc → pymalloc if ≤ 512 bytes, else system malloc
Lifetime: resized (reallocated) as list grows/shrinks

For allocated=4: 4 × 8 = 32 bytes → pymalloc 32-byte pool
For allocated=64: 64 × 8 = 512 bytes → pymalloc 512-byte pool
For allocated=65: 65 × 8 = 520 bytes → system malloc (exceeds pymalloc)
```

---

## 6.3 PyMalloc and Lists

### Pools (4 KB blocks)

pymalloc manages memory in 4 KB pools, each dedicated to a single size class:

```
Size Classes: 8, 16, 24, 32, 40, 48, 56, 64, 72, ..., 512 bytes

Pool for 64-byte allocations:
┌─────────────────────────────────────────────────┐
│ Pool Header                                      │
├───────┬───────┬───────┬───────┬───────┬─────────┤
│ Obj 1 │ Obj 2 │ Obj 3 │ Obj 4 │ ...   │ Obj 63  │  ← 4096/64 = 63 objects
│ 64B   │ 64B   │ 64B   │ 64B   │       │ 64B     │
└───────┴───────┴───────┴───────┴───────┴─────────┘

A PyListObject (64 bytes with GC header) goes into this pool.
```

### Arenas (256 KB)

Multiple pools live in an arena:

```
Arena (256 KB):
┌────────────────────────────────────────────────────┐
│ Pool 1 (4KB, size class 32)                        │
│ Pool 2 (4KB, size class 64)  ← list objects here   │
│ Pool 3 (4KB, size class 32)  ← small ob_item arrays│
│ Pool 4 (4KB, size class 128)                       │
│ ...                                                │
│ Pool 64 (4KB, ...)                                 │
└────────────────────────────────────────────────────┘
```

---

## 6.4 How PyList_New Works

```c
// Objects/listobject.c
PyObject *
PyList_New(Py_ssize_t size)
{
    PyListObject *op;
    
    // Check free list first (reuse recently freed list structs)
    if (numfree) {
        numfree--;
        op = free_list[numfree];
        _Py_NewReference((PyObject *)op);  // reset refcnt to 1
    } else {
        // Allocate new PyListObject from pymalloc
        op = PyObject_GC_New(PyListObject, &PyList_Type);
        if (op == NULL)
            return NULL;
    }
    
    // Allocate the pointer array
    if (size <= 0) {
        op->ob_item = NULL;
    } else {
        op->ob_item = (PyObject **) PyMem_Calloc(size, sizeof(PyObject *));
        if (op->ob_item == NULL) {
            Py_DECREF(op);
            return PyErr_NoMemory();
        }
    }
    
    Py_SET_SIZE(op, size);
    op->allocated = size;
    _PyObject_GC_TRACK(op);  // Register with garbage collector
    return (PyObject *)op;
}
```

Steps:
1. Try to get a PyListObject from the **free list** (up to 80 cached)
2. If free list is empty, allocate from **pymalloc** (PyObject_GC_New)
3. Allocate the pointer array using **PyMem_Calloc** (zero-initialized)
4. Set `ob_size = size`, `allocated = size`
5. Register with the **garbage collector** for cycle detection

---

## 6.5 How list_resize Works (Memory Perspective)

```c
static int
list_resize(PyListObject *self, Py_ssize_t newsize)
{
    PyObject **items;
    size_t new_allocated, num_allocated_bytes;
    Py_ssize_t allocated = self->allocated;

    // Fast path: fits within current allocation
    if (allocated >= newsize && newsize >= (allocated >> 1)) {
        Py_SET_SIZE(self, newsize);
        return 0;
    }

    // Calculate new allocation size (overallocation formula)
    new_allocated = ((size_t)newsize + (newsize >> 3) + 6) & ~(size_t)3;
    
    // Overflow protection
    if (newsize - Py_SIZE(self) > (Py_ssize_t)(new_allocated - newsize))
        new_allocated = ((size_t)newsize + 3) & ~(size_t)3;

    if (new_allocated == 0)
        num_allocated_bytes = 0;
    else
        num_allocated_bytes = new_allocated * sizeof(PyObject *);
    
    // THE KEY CALL: realloc the pointer array
    items = (PyObject **)PyMem_Realloc(self->ob_item, num_allocated_bytes);
    if (items == NULL) {
        PyErr_NoMemory();
        return -1;
    }
    
    self->ob_item = items;          // Update pointer (may have moved!)
    Py_SET_SIZE(self, newsize);
    self->allocated = new_allocated;
    return 0;
}
```

---

## 6.6 PyMem_Realloc Behavior

`PyMem_Realloc` is the critical operation for list growth. It has three possible outcomes:

### Case 1: Extend in Place (Best Case)

If there's free space immediately after the current block:

```
BEFORE:
┌──────────────────────┬─── FREE SPACE ───┐
│ ob_item[0..3]        │                   │
│ (32 bytes used)      │ (enough for grow) │
└──────────────────────┴───────────────────┘

AFTER realloc(ptr, 64):
┌─────────────────────────────────────────┐
│ ob_item[0..7]                            │
│ (64 bytes, extended in place)            │
└─────────────────────────────────────────┘

Cost: O(1) — just update bookkeeping
No copying! Pointer doesn't change!
```

### Case 2: Allocate + Copy + Free (Common Case)

If no space after current block:

```
BEFORE:
┌──────────────────┬──── USED BY OTHER ────┐
│ ob_item (old)    │ object (can't extend)  │
│ (32 bytes)       │                        │
└──────────────────┴────────────────────────┘

STEP 1: Allocate new block elsewhere:
                                     ┌─────────────────────────────────────┐
                                     │ new block (64 bytes)                 │
                                     └─────────────────────────────────────┘

STEP 2: Copy old data to new:
                                     ┌─────────────────────────────────────┐
                                     │ copied ob_item[0..3] │ new space    │
                                     └─────────────────────────────────────┘

STEP 3: Free old block:
┌── NOW FREE ──────┐
│ (returned to      │
│  allocator)       │
└───────────────────┘

Cost: O(n) — must copy all existing pointers
ob_item pointer value changes!
```

### Case 3: Failure (Out of Memory)

```
realloc returns NULL → PyErr_NoMemory() → MemoryError exception
The original block is PRESERVED (not freed) when realloc fails!
```

---

## 6.7 pymalloc vs System malloc Boundary

The boundary matters for lists:

```
ob_item array size = allocated × 8 bytes

pymalloc handles:   ≤ 512 bytes → allocated ≤ 64 slots
system malloc:      > 512 bytes → allocated > 64 slots

Transition point: when list grows past 64 elements,
                  the ob_item array switches from pymalloc to system malloc
```

Implications:
- Lists with ≤ 64 elements: ob_item lives in a pymalloc pool (fast alloc/free)
- Lists with > 64 elements: ob_item uses system malloc (may use mmap for very large)
- The PyListObject struct itself ALWAYS uses pymalloc (it's only 64 bytes)

---

## 6.8 The Free List

```c
#ifndef PyList_MAXFREELIST
#define PyList_MAXFREELIST 80
#endif

static PyListObject *free_list[PyList_MAXFREELIST];
static int numfree = 0;
```

When a list is deallocated:
```c
static void
list_dealloc(PyListObject *op)
{
    // First: decref all contained items
    Py_ssize_t i = Py_SIZE(op);
    while (--i >= 0)
        Py_XDECREF(op->ob_item[i]);
    
    // Free the pointer array
    PyMem_Free(op->ob_item);
    
    // Try to cache the struct on the free list
    if (numfree < PyList_MAXFREELIST) {
        free_list[numfree++] = op;  // Save for reuse
    } else {
        Py_TYPE(op)->tp_free((PyObject *)op);  // Actually free struct
    }
}
```

Flow:
```
List destroyed:
1. Py_DECREF each element (may cascade destructions)
2. PyMem_Free(ob_item)  ← free the pointer array
3. If free_list not full: cache the PyListObject struct
4. Else: free the struct back to pymalloc
```

---

## 6.9 Memory Map: Complete Allocation Flow

```
a = []           → Alloc PyListObject (from free_list or pymalloc)
                   ob_item = NULL, allocated = 0

a.append(1)      → list_resize(1):
                   new_allocated = (1 + 0 + 6) & ~3 = 4
                   PyMem_Realloc(NULL, 32)  ← allocates 32 bytes from pymalloc
                   ob_item now points to 32-byte block in pool

a.append(2)      → ob_size < allocated, just store pointer
a.append(3)      → ob_size < allocated, just store pointer
a.append(4)      → ob_size < allocated, just store pointer (now FULL)

a.append(5)      → list_resize(5):
                   new_allocated = (5 + 0 + 6) & ~3 = 8
                   PyMem_Realloc(ob_item, 64)
                   → Try extend in place (32→64 in same pool? unlikely)
                   → Likely: alloc new 64-byte block, copy 32 bytes, free old
                   ob_item now points to 64-byte block

... grow to 65 items ...

a.append(65th)   → list_resize(65):
                   new_allocated = (65 + 8 + 6) & ~3 = 76
                   PyMem_Realloc(ob_item, 608)
                   → 608 > 512! Falls through to system malloc!
                   ob_item now managed by system allocator
```

---

## 6.10 Interaction with Garbage Collector

Lists are GC-tracked because they can form reference cycles:

```python
a = []
a.append(a)  # a references itself → cycle!
```

The GC header (prepended to PyListObject):
```c
typedef struct {
    uintptr_t _gc_next;    // 8 bytes - linked list of tracked objects
    uintptr_t _gc_prev;    // 8 bytes - linked list
} PyGC_Head;
```

When a list is created: `_PyObject_GC_TRACK(op)` adds it to the GC's tracking list.
When destroyed: `_PyObject_GC_UNTRACK(op)` removes it.

The GC periodically traverses all tracked objects to find unreachable cycles. Lists are the most common cycle-forming objects in Python.

---

## 6.11 Memory Fragmentation

Over time, lists cause fragmentation because:

1. **Different lifetimes**: Short-lived temp lists and long-lived data lists share pools
2. **Resize pattern**: Growing a list frees the old ob_item block, creating holes
3. **Size class mismatch**: A list that grows from 4→8→16→24 slots uses blocks from pools of sizes 32→64→128→192 bytes

```
Pool for 64-byte blocks (after many list operations):
┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│USED │FREE │USED │FREE │USED │FREE │FREE │USED │
└─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
         ↑         ↑               ↑     ↑
    freed when lists grew past this size class
```

pymalloc mitigates this (same-size pools), but doesn't eliminate it entirely.

---

## 6.12 Interview Questions — Part 6

**Q1**: Where does a PyListObject struct get its memory?
**A**: First from the free list (up to 80 cached structs). If empty, from pymalloc's 64-byte pool. The struct itself is always small enough for pymalloc.

**Q2**: Where does the ob_item array get its memory?
**A**: Via `PyMem_Realloc`. For arrays ≤ 512 bytes (≤ 64 pointers), pymalloc handles it. For larger arrays, system malloc/realloc.

**Q3**: What happens to the old memory when a list grows?
**A**: `realloc` either extends the block in place (ideal) or allocates a new block, copies data, and frees the old block. The old block returns to the appropriate pool or system allocator.

**Q4**: Why does CPython maintain a free list for PyListObjects?
**A**: Creating/destroying lists is extremely common (temporary lists, comprehensions, function returns). The free list avoids malloc/free overhead for the struct by recycling. Up to 80 list structs are cached.

**Q5**: At what list size does ob_item transition from pymalloc to system malloc?
**A**: When `allocated * 8 > 512`, i.e., when the list has more than 64 elements. At that point, the pointer array is too large for pymalloc's size classes.

**Q6**: Can realloc fail? What happens?
**A**: Yes. If the system is out of memory, realloc returns NULL. CPython catches this and raises `MemoryError`. The original array is preserved (realloc guarantees this on failure).
