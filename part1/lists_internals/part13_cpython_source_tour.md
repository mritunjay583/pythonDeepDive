# Part 13 — CPython Source Tour

## 13.1 Key Files

```
cpython/
├── Include/
│   ├── listobject.h              ← Public C API declarations
│   └── cpython/
│       └── listobject.h          ← PyListObject struct definition
├── Objects/
│   ├── listobject.c              ← ALL list implementation code (~3200 lines)
│   ├── listsort.txt              ← Tim Peters' description of TimSort
│   └── clinic/
│       └── listobject.c.h        ← Auto-generated argument clinic code
└── Lib/
    └── copy.py                   ← copy.copy / copy.deepcopy
```

---

## 13.2 PyList_New — Creating a List

```c
// Objects/listobject.c

PyObject *
PyList_New(Py_ssize_t size)
{
    PyListObject *op;

    if (size < 0) {
        PyErr_BadInternalCall();
        return NULL;
    }

    // Try the free list first
    struct _Py_list_state *state = get_list_state();
    if (state->numfree) {
        state->numfree--;
        op = state->free_list[state->numfree];
        _Py_NewReference((PyObject *)op);
    } else {
        op = PyObject_GC_New(PyListObject, &PyList_Type);
        if (op == NULL) return NULL;
    }

    // Allocate the pointer array
    if (size <= 0) {
        op->ob_item = NULL;
    } else {
        op->ob_item = (PyObject **)PyMem_Calloc(size, sizeof(PyObject *));
        if (op->ob_item == NULL) {
            Py_DECREF(op);
            return PyErr_NoMemory();
        }
    }

    Py_SET_SIZE(op, size);
    op->allocated = size;
    _PyObject_GC_TRACK(op);
    return (PyObject *)op;
}
```

**Key observations:**
- Free list is checked first (fast path for recycled lists)
- `PyObject_GC_New` allocates with GC tracking header
- `PyMem_Calloc` zero-initializes the pointer array (NULL pointers)
- New lists have `allocated == size` (no overallocation at creation)
- GC tracking is enabled immediately

---

## 13.3 list_resize — The Growth Engine

```c
static int
list_resize(PyListObject *self, Py_ssize_t newsize)
{
    PyObject **items;
    size_t new_allocated, num_allocated_bytes;
    Py_ssize_t allocated = self->allocated;

    /* Fast path: no reallocation needed */
    if (allocated >= newsize && newsize >= (allocated >> 1)) {
        assert(self->ob_item != NULL || newsize == 0);
        Py_SET_SIZE(self, newsize);
        return 0;
    }

    /* Calculate overallocation */
    new_allocated = ((size_t)newsize + (newsize >> 3) + 6) & ~(size_t)3;
    
    /* Overflow protection */
    if (newsize - Py_SIZE(self) > (Py_ssize_t)(new_allocated - newsize))
        new_allocated = ((size_t)newsize + 3) & ~(size_t)3;
    
    if (new_allocated == 0)
        num_allocated_bytes = 0;
    else {
        num_allocated_bytes = new_allocated * sizeof(PyObject *);
        if (num_allocated_bytes / sizeof(PyObject *) != new_allocated) {
            PyErr_NoMemory();
            return -1;
        }
    }

    if (num_allocated_bytes == 0)
        items = NULL;
    else {
        items = (PyObject **)PyMem_Realloc(self->ob_item, num_allocated_bytes);
        if (items == NULL) {
            PyErr_NoMemory();
            return -1;
        }
    }

    self->ob_item = items;
    Py_SET_SIZE(self, newsize);
    self->allocated = new_allocated;
    return 0;
}
```

**Key observations:**
- Fast path: if newsize fits within allocated and isn't less than half → just update ob_size
- Overallocation formula: `newsize + newsize/8 + 6`, rounded to multiple of 4
- Handles shrinking too (when newsize < allocated/2)
- Overflow protection for huge lists
- NULL ob_item for empty lists (allocated == 0)

---

## 13.4 PyList_Append — Adding an Element

```c
int
PyList_Append(PyObject *op, PyObject *newitem)
{
    if (PyList_Check(op) && (newitem != NULL))
        return app1((PyListObject *)op, newitem);
    PyErr_BadInternalCall();
    return -1;
}

static int
app1(PyListObject *self, PyObject *v)
{
    Py_ssize_t n = PyList_GET_SIZE(self);

    assert(v != NULL);
    assert((size_t)n + 1 < PY_SSIZE_T_MAX);
    
    if (list_resize(self, n+1) < 0)
        return -1;

    self->ob_item[n] = Py_NewRef(v);
    return 0;
}
```

**Key observations:**
- `app1` is the internal implementation, `PyList_Append` is the public API
- `list_resize(self, n+1)` handles growth (fast path if space available)
- `Py_NewRef(v)` increments reference count and stores pointer
- The element is stored at `ob_item[n]` (the old end, now included)
- No bounds checking needed — resize guarantees space

---

## 13.5 PyList_Insert — Inserting at Position

```c
int
PyList_Insert(PyObject *op, Py_ssize_t where, PyObject *newitem)
{
    if (!PyList_Check(op)) {
        PyErr_BadInternalCall();
        return -1;
    }
    return ins1((PyListObject *)op, where, newitem);
}

static int
ins1(PyListObject *self, Py_ssize_t where, PyObject *v)
{
    Py_ssize_t i, n = Py_SIZE(self);
    PyObject **items;

    if (v == NULL) {
        PyErr_BadInternalCall();
        return -1;
    }

    assert((size_t)n + 1 < PY_SSIZE_T_MAX);
    if (list_resize(self, n+1) < 0)
        return -1;

    // Clamp 'where' to valid range
    if (where < 0) {
        where += n;
        if (where < 0)
            where = 0;
    }
    if (where > n)
        where = n;

    // Shift elements right
    items = self->ob_item;
    for (i = n; --i >= where; )
        items[i+1] = items[i];

    items[where] = Py_NewRef(v);
    return 0;
}
```

**Key observations:**
- Negative indices are converted to positive (+ clamping)
- Elements are shifted right one-by-one from the end
- The loop goes from right to left to avoid overwriting
- O(n - where) shifts required
- `list_resize` is called first to ensure space

---

## 13.6 PyList_GetItem — Accessing an Element

```c
PyObject *
PyList_GetItem(PyObject *op, Py_ssize_t i)
{
    if (!PyList_Check(op)) {
        PyErr_BadInternalCall();
        return NULL;
    }
    if (!valid_index(i, Py_SIZE(op))) {
        _Py_DECLARE_STR(list_err, "list index out of range");
        PyErr_SetObject(PyExc_IndexError, &_Py_STR(list_err));
        return NULL;
    }
    return ((PyListObject *)op)->ob_item[i];
}

// The fast macro version (no error checking):
#define PyList_GET_ITEM(op, i) (((PyListObject *)(op))->ob_item[i])
```

**Key observations:**
- Bounds check (returns NULL and sets IndexError if invalid)
- Direct array access: `ob_item[i]` — pure O(1)
- The macro `PyList_GET_ITEM` skips checks (used internally when index is known valid)
- Returns a **borrowed reference** (no incref — caller must not decref)

---

## 13.7 PyList_Sort — Sorting

```c
static PyObject *
list_sort_impl(PyListObject *self, PyObject *keyfunc, int reverse)
{
    MergeState ms;
    Py_ssize_t nremaining;
    Py_ssize_t minrun;
    sortslice lo;
    Py_ssize_t saved_ob_size, saved_allocated;
    PyObject **saved_ob_item;
    PyObject **final_ob_item;
    PyObject *result = NULL;

    // Save the list state and hide it from mutations
    saved_ob_size = Py_SIZE(self);
    saved_allocated = self->allocated;
    saved_ob_item = self->ob_item;
    
    // Make the list appear empty (mutation detection)
    Py_SET_SIZE(self, 0);
    self->ob_item = NULL;
    self->allocated = -1;  // Sentinel for mutation detection!

    // Pre-compute keys if keyfunc provided
    if (keyfunc != NULL) {
        // ... allocate and compute keys array ...
    }

    // Initialize merge state
    merge_init(&ms, saved_ob_size, ...);

    // Compute minimum run length
    minrun = merge_compute_minrun(saved_ob_size);

    // Main TimSort loop
    nremaining = saved_ob_size;
    PyObject **keys_ptr = ...;
    
    do {
        Py_ssize_t n;
        // Find next natural run
        n = count_run(&ms, ...);
        
        // If descending, reverse it
        if (n < 0) {
            n = -n;
            reverse_sortslice(...);
        }
        
        // Extend short runs with binary insertion sort
        if (n < minrun) {
            Py_ssize_t force = nremaining < minrun ? nremaining : minrun;
            binarysort(&ms, ...);
            n = force;
        }
        
        // Push run onto merge stack
        ms.pending[ms.n].base = ...;
        ms.pending[ms.n].len = n;
        ms.n++;
        
        // Merge to maintain stack invariant
        merge_collapse(&ms);
        
        // Advance
        lo.keys += n;
        lo.values += n;
        nremaining -= n;
    } while (nremaining);

    // Final merge to combine all remaining runs
    merge_force_collapse(&ms);

    // Restore list state
    self->ob_item = final_ob_item;
    Py_SET_SIZE(self, saved_ob_size);
    self->allocated = saved_allocated;

    result = Py_None;
    // ... cleanup ...
    return result;
}
```

**Key observations:**
- List is "hidden" during sort (ob_item=NULL, allocated=-1)
- Keys are pre-computed for efficiency
- Natural runs are found, short runs extended with insertion sort
- Merge stack maintains balance invariant
- After sort, list state is restored

---

## 13.8 list_dealloc — Destroying a List

```c
static void
list_dealloc(PyListObject *op)
{
    Py_ssize_t i;
    
    // Untrack from GC
    PyObject_GC_UnTrack(op);
    
    // Prevent recursive deallocation
    Py_TRASHCAN_BEGIN(op, list_dealloc)
    
    // Decref all elements
    if (op->ob_item != NULL) {
        i = Py_SIZE(op);
        while (--i >= 0) {
            Py_XDECREF(op->ob_item[i]);
        }
        PyMem_Free(op->ob_item);
    }
    
    // Try to cache on free list
    struct _Py_list_state *state = get_list_state();
    if (state->numfree < PyList_MAXFREELIST && PyList_CheckExact(op)) {
        state->free_list[state->numfree++] = op;
    } else {
        Py_TYPE(op)->tp_free((PyObject *)op);
    }
    
    Py_TRASHCAN_END
}
```

**Key observations:**
- GC untracking happens first
- `Py_TRASHCAN_*` prevents stack overflow from deeply nested structures
- All elements are decrefed (may trigger cascading deallocations)
- `ob_item` array is freed
- PyListObject struct is cached on free list (up to 80)
- If free list full, struct is freed back to allocator

---

## 13.9 list_ass_slice — Slice Assignment Engine

This is one of the most complex list operations. It handles `a[i:j] = b`:

```c
static int
list_ass_slice(PyListObject *a, Py_ssize_t ilow, Py_ssize_t ihigh, PyObject *v)
{
    PyObject **recycle, **item;
    Py_ssize_t n, norig, d;

    // Handle 'del a[i:j]' (v is NULL)
    // Handle a[i:j] = iterable

    norig = ihigh - ilow;  // Number of items being replaced
    n = /* length of v */;
    d = n - norig;          // Size difference

    if (d < 0) {
        // Shrinking: shift elements left
        memmove(&item[ihigh+d], &item[ihigh],
                (Py_SIZE(a) - ihigh) * sizeof(PyObject *));
        if (list_resize(a, Py_SIZE(a) + d) < 0) { ... }
    } else if (d > 0) {
        // Growing: resize then shift elements right
        if (list_resize(a, Py_SIZE(a) + d) < 0) { ... }
        memmove(&item[ihigh+d], &item[ihigh],
                (Py_SIZE(a) - d - ihigh) * sizeof(PyObject *));
    }

    // Copy new items into the gap
    for (k = 0; k < n; k++, ilow++) {
        PyObject *w = vitem[k];
        item[ilow] = Py_NewRef(w);
    }

    // Decref old items (the ones that were replaced)
    for (k = norig - 1; k >= 0; --k)
        Py_XDECREF(recycle[k]);

    return 0;
}
```

**Key observations:**
- Handles growing, shrinking, and same-size replacements
- Uses `memmove` for shifting (handles overlapping memory correctly)
- Old items are saved, new items inserted, then old items decrefed
- Decref happens AFTER insertion (in case new items reference old ones)

---

## 13.10 Important Macros

```c
// Get list size (fast, no function call):
#define PyList_GET_SIZE(op)    Py_SIZE(op)

// Get item at index (fast, no bounds check):
#define PyList_GET_ITEM(op, i) (((PyListObject *)(op))->ob_item[i])

// Set item at index (fast, no bounds check, no decref of old):
#define PyList_SET_ITEM(op, i, v) (((PyListObject *)(op))->ob_item[i] = (v))

// Type check:
#define PyList_Check(op) PyType_FastSubclass(Py_TYPE(op), Py_TPFLAGS_LIST_SUBCLASS)
#define PyList_CheckExact(op) Py_IS_TYPE(op, &PyList_Type)
```

`PyList_SET_ITEM` is dangerous — it doesn't decref the old value. Used only when initializing a fresh list where slots are NULL.

---

## 13.11 The Free List Implementation

```c
// Per-interpreter state (Python 3.12+)
struct _Py_list_state {
    PyListObject *free_list[PyList_MAXFREELIST];
    int numfree;
};

// Older versions used module-level static variables:
// static PyListObject *free_list[80];
// static int numfree = 0;
```

The free list was moved to per-interpreter state in Python 3.12 for sub-interpreter support.

---

## 13.12 Summary of Key Functions

| Function | Purpose | Complexity |
|----------|---------|------------|
| `PyList_New(n)` | Create list with n NULL slots | O(n) |
| `list_resize(self, n)` | Grow/shrink ob_item array | O(n) worst, O(1) fast path |
| `app1(self, v)` | Internal append | O(1) amortized |
| `ins1(self, where, v)` | Internal insert | O(n) |
| `list_sort_impl(...)` | TimSort | O(n log n) |
| `list_dealloc(op)` | Destroy list + free memory | O(n) |
| `list_ass_slice(...)` | Slice assignment | O(n) |
| `list_slice(a, i, j)` | Create slice copy | O(j-i) |
| `list_contains(a, v)` | Membership test | O(n) |
| `list_concat(a, b)` | Concatenation (new list) | O(n+m) |
| `list_repeat(a, n)` | Multiplication (new list) | O(n×k) |
| `list_reverse_impl(self)` | In-place reverse | O(n) |
| `list_clear(self)` | Remove all items | O(n) |
