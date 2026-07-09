# Part 14 — Object Allocation: Full Lifecycle

## 14.1 The Complete Journey

When you write `x = [1, 2, 3]`, here's the full path from Python source code to bits in memory and back:

```
Python Source Code
       │
       ▼
┌──────────────────┐
│ 1. COMPILER      │  Parse → AST → Compile → Bytecode
│    (compile.c)   │  Produces: BUILD_LIST instruction
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ 2. INTERPRETER   │  Execute bytecode
│    (ceval.c)     │  BUILD_LIST → calls PyList_New(3)
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ 3. TYPE'S ALLOC  │  PyList_New → PyObject_GC_New
│    (listobject.c)│  Calculates size, requests memory
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ 4. OBJECT ALLOC  │  PyObject_GC_New → _PyObject_GC_Alloc
│    (gcmodule.c)  │  Adds GC header size, calls allocator
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ 5. PyMalloc      │  Small object allocator
│    (obmalloc.c)  │  Routes to appropriate pool
└──────────────────┘
       │
       ▼
┌──────────────────────────────────────┐
│ 6. ARENA → POOL → BLOCK             │
│    Arena (256KB) contains Pools      │
│    Pool (4KB) contains Blocks        │
│    Block (fixed size) = your object  │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────┐
│ 7. HEADER INIT   │  Set ob_refcnt = 1, ob_type = &PyList_Type
│                   │  Set ob_size = 3, register with GC
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ 8. EXECUTION     │  Object lives, refcount goes up/down
│                   │  Eventually refcount hits 0...
└──────────────────┘
       │
       ▼
┌──────────────────┐
│ 9. DEALLOCATION  │  tp_dealloc → DECREF items → tp_free
│                   │  Return block to pool (or free to OS)
└──────────────────┘
```

---

## 14.2 Step 1: Compilation

```python
x = [1, 2, 3]
```

The compiler generates bytecode:
```
  LOAD_CONST     1 (1)
  LOAD_CONST     2 (2)
  LOAD_CONST     3 (3)
  BUILD_LIST     3
  STORE_FAST     0 (x)
```

At this stage, no list object exists yet — just instructions to create one.

---

## 14.3 Step 2: Interpreter Executes BUILD_LIST

```c
// Python/ceval.c (simplified)
case BUILD_LIST: {
    int oparg = GETARG();  // 3
    PyObject *list = PyList_New(oparg);
    // Pop 3 items from stack and store in list
    while (--oparg >= 0) {
        PyObject *item = POP();
        PyList_SET_ITEM(list, oparg, item);  // Steals reference
    }
    PUSH(list);  // Push list onto value stack
    break;
}
```

---

## 14.4 Step 3: PyList_New Allocates the List

```c
// Objects/listobject.c
PyObject *PyList_New(Py_ssize_t size) {
    PyListObject *op;
    
    // Check free list first (recycled list structs):
    if (numfree) {
        numfree--;
        op = free_list[numfree];
        _Py_NewReference((PyObject *)op);
    } else {
        // Allocate new list struct:
        op = PyObject_GC_New(PyListObject, &PyList_Type);
        if (op == NULL)
            return NULL;
    }
    
    // Allocate the item pointer array:
    if (size <= 0) {
        op->ob_item = NULL;
    } else {
        op->ob_item = (PyObject **)PyMem_Calloc(size, sizeof(PyObject *));
    }
    
    Py_SET_SIZE(op, size);
    op->allocated = size;
    
    // Register with GC (lists can participate in cycles):
    _PyObject_GC_TRACK(op);
    
    return (PyObject *)op;
}
```

---

## 14.5 Step 4: PyObject_GC_New

```c
// Include/objimpl.h + Modules/gcmodule.c

// PyObject_GC_New expands roughly to:
PyListObject *op = (PyListObject *)_PyObject_GC_New(&PyList_Type);

PyObject *_PyObject_GC_New(PyTypeObject *tp) {
    // Calculate size: GC header + object
    size_t basicsize = tp->tp_basicsize;  // sizeof(PyListObject)
    size_t size = sizeof(PyGC_Head) + basicsize;
    
    // Allocate:
    PyGC_Head *gc = (PyGC_Head *)PyObject_Malloc(size);
    
    // Initialize GC header:
    gc->_gc_next = 0;
    gc->_gc_prev = 0;
    
    // Get pointer to the actual object (past GC header):
    PyObject *op = FROM_GC(gc);  // (PyObject *)((gc) + 1)
    
    // Initialize object header:
    op->ob_refcnt = 1;
    op->ob_type = tp;
    
    return op;
}
```

---

## 14.6 Step 5: PyMalloc (Small Object Allocator)

```c
// Objects/obmalloc.c

void *PyObject_Malloc(size_t nbytes) {
    // Small object? Use pymalloc (fast path):
    if (nbytes <= SMALL_REQUEST_THRESHOLD) {  // 512 bytes
        return _PyObject_Alloc(nbytes);  // → pymalloc
    }
    // Large object? Fall through to system malloc:
    return malloc(nbytes);
}
```

PyMalloc is optimized for the typical Python workload — many small allocations:

```
Size classes (pymalloc):
  8, 16, 24, 32, 40, 48, 56, 64, 72, ... 512 bytes
  (increments of ALIGNMENT = 8 bytes)

Request size → rounded UP to next size class:
  Request 24 bytes → allocated from 24-byte pool
  Request 25 bytes → allocated from 32-byte pool
  Request 1 byte  → allocated from 8-byte pool
```

---

## 14.7 Step 6: Arena → Pool → Block

```
ARENA (256 KB — allocated from OS via mmap/VirtualAlloc):
┌─────────────────────────────────────────────────────────────────┐
│ Pool 0 (4KB)  │ Pool 1 (4KB)  │ Pool 2 (4KB)  │ ... │ Pool 63 │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
POOL (4 KB = 4096 bytes — serves ONE size class):
┌─────────────────────────────────────────────────────────────────┐
│ Pool Header │ Block │ Block │ Block │ Block │ ... │ Block       │
│ (48 bytes)  │ 32B   │ 32B   │ 32B   │ 32B   │     │ 32B        │
└─────────────────────────────────────────────────────────────────┘
                  │
                  ▼
BLOCK (fixed size — YOUR OBJECT goes here):
┌────────────────────────────────┐
│ [GC Header 16B] [Object 24B]  │ ← 40 bytes total for a list struct
└────────────────────────────────┘
```

Pool details:
```c
// Each pool serves one size class:
struct pool_header {
    union { block *_padding; uint count; } ref;  // 8B
    block *freeblock;           // 8B — next free block in this pool
    struct pool_header *nextpool;  // 8B — linked list of pools  
    struct pool_header *prevpool;  // 8B
    uint arenaindex;            // 4B — which arena
    uint szidx;                 // 4B — size class index
    uint nextoffset;            // 4B — offset of next virgin block
    uint maxnextoffset;         // 4B — maximum offset
};
```

Allocation from a pool:
```c
// Fast path: take from free list
block = pool->freeblock;
pool->freeblock = *(block **)block;  // Free list is in-block!
return block;

// If no free blocks: carve from virgin space
block = (char *)pool + pool->nextoffset;
pool->nextoffset += size_class;
return block;
```

---

## 14.8 Step 7: Header Initialization

After memory is allocated, the object header is filled:

```c
// The moment of "birth":
op->ob_refcnt = 1;               // Born with one reference
op->ob_type = &PyList_Type;      // Knows its type
Py_SET_SIZE(op, 3);              // 3 elements

// For GC-tracked objects:
_PyObject_GC_TRACK(op);
// Adds to the doubly-linked list of tracked objects:
// gc->_gc_next = generation->_gc_next;
// gc->_gc_prev = generation;
```

---

## 14.9 Step 8: Object Lives

During execution, the object is used and its refcount fluctuates:

```python
x = [1, 2, 3]    # refcnt = 1 (STORE_FAST)
y = x             # refcnt = 2 (COPY + INCREF)
z = [x, x]       # refcnt = 4 (two list slots INCREF)
del y             # refcnt = 3 (DECREF)
del z             # refcnt = 1 (z's dealloc DECREFs both slots)
x.append(4)       # refcnt unchanged (mutation, not reference)
```

---

## 14.10 Step 9: Deallocation

When the last reference is removed:

```python
del x  # refcnt: 1 → 0 → DEALLOC triggered
```

```c
// Triggered by Py_DECREF reaching 0:
void _Py_Dealloc(PyObject *op) {
    destructor dealloc = Py_TYPE(op)->tp_dealloc;
    (*dealloc)(op);  // → list_dealloc
}

// Objects/listobject.c
static void list_dealloc(PyListObject *op) {
    Py_ssize_t i;
    
    // 1. Untrack from GC:
    PyObject_GC_UnTrack(op);
    
    // 2. DECREF every item (cascading deallocation):
    Py_TRASHCAN_BEGIN(op, list_dealloc)
    if (op->ob_item != NULL) {
        i = Py_SIZE(op);
        while (--i >= 0) {
            Py_XDECREF(op->ob_item[i]);
        }
        PyMem_Free(op->ob_item);  // Free the pointer array
    }
    
    // 3. Add to free list (for reuse) or free:
    if (numfree < PyList_MAXFREELIST) {
        free_list[numfree++] = op;  // Recycle!
    } else {
        Py_TYPE(op)->tp_free((PyObject *)op);  // → PyObject_GC_Del
    }
    Py_TRASHCAN_END
}
```

### Memory Return Path

```c
// PyObject_GC_Del:
void PyObject_GC_Del(void *op) {
    PyGC_Head *gc = AS_GC(op);  // Get GC header
    // Unlink from GC list:
    gc_list_remove(gc);
    // Free memory:
    PyObject_Free(gc);  // → pymalloc or system free
}

// PyObject_Free (pymalloc):
void PyObject_Free(void *ptr) {
    // Return block to its pool's free list:
    pool = POOL_FROM_PTR(ptr);
    *(block **)ptr = pool->freeblock;
    pool->freeblock = (block *)ptr;
    
    // If pool is now completely empty → return pool to arena
    // If arena is completely empty → return arena to OS (munmap)
}
```

---

## 14.11 Free Lists: Recycling Objects

CPython keeps "free lists" for frequently-created types — pre-allocated slots that avoid going back to the allocator:

```c
// Lists:
#define PyList_MAXFREELIST 80
static PyListObject *free_list[PyList_MAXFREELIST];

// Tuples (by size):
static PyTupleObject *free_list[PyTuple_MAXSAVESIZE];

// Floats:
#define PyFloat_MAXFREELIST 100
static PyFloatObject *free_list_head;

// Dicts:
#define PyDict_MAXFREELIST 80
```

When an object is deallocated, instead of fully freeing, it's saved for reuse:
```c
// Dealloc:
if (numfree < MAX) {
    free_list[numfree++] = op;  // Save for later
} else {
    actually_free(op);  // Free list full — return to allocator
}

// New allocation:
if (numfree > 0) {
    op = free_list[--numfree];  // Instant reuse!
    _Py_NewReference(op);       // Reset refcount to 1
} else {
    op = allocate_new();        // Go through pymalloc
}
```

---

## 14.12 Complete Allocation Timeline

```
Time →

t0: x = [1, 2, 3]
    ┌───────────────────────────────────────────────────────────────┐
    │ 1. Bytecode: BUILD_LIST 3                                      │
    │ 2. PyList_New(3) called                                        │
    │ 3. Check free list → empty → PyObject_GC_New                   │
    │ 4. Calculate: GC_Head(16) + PyListObject(40) = 56 bytes        │
    │ 5. PyObject_Malloc(56) → pymalloc → pool for 56-byte class     │
    │ 6. Pool has free block → return immediately (fast!)             │
    │ 7. Init: refcnt=1, type=list, size=3, track with GC            │
    │ 8. Allocate item array: PyMem_Calloc(3, 8) = 24 bytes          │
    │ 9. Store pointers to int(1), int(2), int(3) in array            │
    │ 10. STORE_FAST: frame[x] = list_ptr                            │
    └───────────────────────────────────────────────────────────────┘
    Total time: ~50-200 nanoseconds (mostly in pymalloc fast path)

t1: del x
    ┌───────────────────────────────────────────────────────────────┐
    │ 1. DELETE_FAST: old = frame[x]; frame[x] = NULL                │
    │ 2. Py_DECREF(old): refcnt 1→0 → _Py_Dealloc                   │
    │ 3. list_dealloc: DECREF int(1), int(2), int(3)                 │
    │    (integers are cached — refcnt decremented but not freed)    │
    │ 4. PyMem_Free(item_array): 24 bytes back to allocator          │
    │ 5. Add list struct to free_list (saves 56 bytes for reuse)     │
    └───────────────────────────────────────────────────────────────┘
    Total time: ~30-100 nanoseconds
```

---

## 14.13 Source References

| File | Role |
|------|------|
| `Python/compile.c` | Compiler: source → bytecode |
| `Python/ceval.c` | Interpreter: bytecode execution, BUILD_LIST |
| `Objects/listobject.c` | PyList_New, list_dealloc, free list |
| `Objects/obmalloc.c` | PyMalloc: arena/pool/block allocator |
| `Modules/gcmodule.c` | GC header allocation, tracking |
| `Include/objimpl.h` | PyObject_New, PyObject_GC_New macros |
| `Include/pymem.h` | PyMem_Malloc, PyMem_Free, PyMem_Calloc |
| `Objects/object.c` | _Py_Dealloc |

---

## 14.14 Interview Questions — Part 14

**Q1**: Trace the complete allocation path for `x = 3.14`.
**A**: LOAD_CONST loads the pre-compiled float constant (or creates via PyFloat_FromDouble). Check float free list → if available, reuse. Otherwise: PyObject_Malloc(24) → pymalloc finds 24-byte pool → returns block. Init: refcnt=1, type=&PyFloat_Type, ob_fval=3.14. STORE_FAST stores in frame locals.

**Q2**: What is the purpose of the free list optimization?
**A**: Avoid the overhead of allocation/deallocation for frequently-created objects. When a float/list/dict/tuple is freed, its memory is saved in a type-specific free list. Next allocation of the same type takes from the free list (O(1)) instead of going through pymalloc.

**Q3**: Explain the Arena → Pool → Block hierarchy.
**A**: Arena (256KB) is allocated from OS via mmap. It's divided into Pools (4KB each). Each Pool serves one size class and is divided into Blocks of that size. Blocks are the units given to individual object allocations. Free blocks within a pool form a linked list.

**Q4**: Why does CPython use its own allocator (pymalloc) instead of just malloc?
**A**: Python creates and destroys millions of small objects (16-512 bytes). System malloc has per-allocation overhead (headers, fragmentation, system calls). Pymalloc uses size-class pools with minimal overhead, no headers per block, and returns memory to the OS efficiently. It's ~2-3× faster for Python's workload.

**Q5**: What happens to memory when a list with 1000 elements is deleted?
**A**: 1. list_dealloc is called. 2. Each of the 1000 item pointers is DECREF'd (may cascade). 3. The item pointer array (8000 bytes) is freed via PyMem_Free → returned to pymalloc or system. 4. The list struct itself goes to the free list or is freed. 5. If any DECREF'd items reach refcnt=0, THEIR deallocation cascades.

**Q6**: How does `_PyObject_GC_TRACK` work?
**A**: It inserts the object's GC header into a doubly-linked list of all GC-tracked objects in the current generation. The GC periodically traverses this list during collection cycles to find reference cycles.

**Q7**: What's the "trashcan" mechanism in list_dealloc?
**A**: A protection against C stack overflow. Deeply nested structures (list-of-lists-of-lists...) cause cascading deallocations that each add a C stack frame. The trashcan limits recursion depth — excess objects are queued for later iterative deletion.

**Q8**: What size class would a PyFloatObject (24 bytes) be allocated from?
**A**: The 24-byte size class (pymalloc rounds to multiples of 8). A pool for 24-byte blocks can hold `(4096 - 48) / 24 ≈ 168` blocks.
