# Part 2 — PyListObject

## 2.1 The Actual C Structure

The list object is defined in `Include/cpython/listobject.h`:

```c
typedef struct {
    PyObject_VAR_HEAD
    PyObject **ob_item;
    Py_ssize_t allocated;
} PyListObject;
```

Three fields beyond the standard variable-object header. Let's expand `PyObject_VAR_HEAD` fully:

```c
// Fully expanded PyListObject on 64-bit:
struct PyListObject {
    Py_ssize_t    ob_refcnt;      // 8 bytes — from PyObject
    PyTypeObject *ob_type;        // 8 bytes — from PyObject
    Py_ssize_t    ob_size;        // 8 bytes — from PyVarObject
    PyObject    **ob_item;        // 8 bytes — pointer to array of pointers
    Py_ssize_t    allocated;      // 8 bytes — total capacity
};
// Total: 40 bytes (+ GC header of 24 bytes = 64 bytes actual)
```

In practice, CPython also prepends a GC header (`PyGC_Head`) because lists are tracked by the garbage collector (they can form reference cycles):

```c
// Actual memory layout with GC header:
struct {
    PyGC_Head     gc_head;        // 24 bytes (prev, next, gc_refs)
    Py_ssize_t    ob_refcnt;      // 8 bytes
    PyTypeObject *ob_type;        // 8 bytes
    Py_ssize_t    ob_size;        // 8 bytes
    PyObject    **ob_item;        // 8 bytes
    Py_ssize_t    allocated;      // 8 bytes
};
// Total: 64 bytes for the list object itself
```

---

## 2.2 Field-by-Field Deep Dive

### Field 1: `ob_refcnt` (from PyObject)

```
Offset: +0x00 (after GC header)
Type:   Py_ssize_t (int64_t on 64-bit)
Size:   8 bytes
```

The reference count of the **list object itself** (not its contents).

```python
a = [1, 2, 3]    # list ob_refcnt = 1
b = a             # list ob_refcnt = 2  (two names → same object)
c = [a, a]        # list ob_refcnt = 4  (a, b, c[0], c[1])
del b             # list ob_refcnt = 3
```

When `ob_refcnt` reaches 0:
1. All elements have their refcounts decremented (Py_DECREF on each ob_item[i])
2. The `ob_item` array is freed
3. The PyListObject itself is freed (or returned to free-list)

### Field 2: `ob_type` (from PyObject)

```
Offset: +0x08
Type:   PyTypeObject *
Size:   8 bytes
Points: &PyList_Type (singleton type object for all lists)
```

Every list object's `ob_type` points to the **same** `PyList_Type` object. This is how Python knows an object is a list:

```c
// Type check in CPython:
#define PyList_Check(op)  PyType_FastSubclass(Py_TYPE(op), Py_TPFLAGS_LIST_SUBCLASS)

// Py_TYPE just reads ob_type:
#define Py_TYPE(ob)  (((PyObject*)(ob))->ob_type)
```

```python
type([1,2,3]) is type([4,5,6])  # True — same PyList_Type object
isinstance([], list)             # Uses ob_type for check
```

### Field 3: `ob_size` (from PyVarObject)

```
Offset: +0x10
Type:   Py_ssize_t
Size:   8 bytes
Range:  0 to PY_SSIZE_T_MAX (typically 2^63 - 1)
```

The **current number of items** in the list. This is the value `len()` returns.

```c
// len(list) in CPython:
static Py_ssize_t list_length(PyListObject *a) {
    return Py_SIZE(a);  // just reads ob_size
}

#define Py_SIZE(ob)  (((PyVarObject*)(ob))->ob_size)
```

```python
a = [10, 20, 30]
len(a)          # reads ob_size → 3
a.append(40)
len(a)          # reads ob_size → 4
```

**Invariant**: `0 <= ob_size <= allocated`

### Field 4: `ob_item`

```
Offset: +0x18
Type:   PyObject ** (pointer to pointer)
Size:   8 bytes (it's a pointer, not the array itself)
Points: Heap-allocated array of PyObject* (or NULL if empty)
```

This is the **heart** of the list — a pointer to a contiguous block of `PyObject*` pointers.

```
ob_item → ┌──────────┬──────────┬──────────┬──────────┐
           │ PyObj*   │ PyObj*   │ PyObj*   │ (unused) │
           │ 8 bytes  │ 8 bytes  │ 8 bytes  │ 8 bytes  │
           └──────────┴──────────┴──────────┴──────────┘
            slot[0]    slot[1]    slot[2]    slot[3]

Total array size = allocated * sizeof(PyObject*) = allocated * 8 bytes
```

**Key behaviors:**
- `ob_item` is NULL when the list is empty (ob_size == 0, allocated == 0)
- `ob_item` is allocated via `PyMem_Realloc` (pymalloc for small, system malloc for large)
- When the list grows beyond capacity, `ob_item` is reallocated (may move)
- The PyListObject itself does NOT move — only `ob_item` changes value

**Accessing element i:**
```c
// list[i] internally:
#define PyList_GET_ITEM(op, i)  ((PyListObject *)(op))->ob_item[i]
// This is just: *(ob_item + i)
// Cost: one pointer dereference + pointer arithmetic = O(1)
```

### Field 5: `allocated`

```
Offset: +0x20
Type:   Py_ssize_t
Size:   8 bytes
```

The **total number of slots** in the `ob_item` array. Not all slots are in use.

```
Example: ob_size=3, allocated=4

ob_item → ┌───────┬───────┬───────┬───────┐
           │ used  │ used  │ used  │ FREE  │
           └───────┴───────┴───────┴───────┘
            [0]     [1]     [2]     [3]

len() = ob_size = 3 (user-visible)
capacity = allocated = 4 (internal)
free slots = allocated - ob_size = 1
```

**Invariants (from CPython source comments):**
```
0 <= ob_size <= allocated
len(list) == ob_size
ob_item == NULL implies ob_size == allocated == 0
```

**Special value**: During `list.sort()`, `allocated` is temporarily set to `-1` as a mutation guard. If any operation checks `allocated` and finds it's -1, it knows a sort is in progress and raises `ValueError`.

---

## 2.3 The Relationship Between ob_size and allocated

This dual-field design is the **key to amortized O(1) append**:

```
State after: a = []
    ob_size = 0, allocated = 0, ob_item = NULL

State after: a.append(1)
    ob_size = 1, allocated = 4, ob_item → [ptr, _, _, _]
    (allocated 4 slots even though only 1 needed)

State after: a.append(2)
    ob_size = 2, allocated = 4, ob_item → [ptr, ptr, _, _]
    (no reallocation needed!)

State after: a.append(3)
    ob_size = 3, allocated = 4, ob_item → [ptr, ptr, ptr, _]
    (still no reallocation!)

State after: a.append(4)
    ob_size = 4, allocated = 4, ob_item → [ptr, ptr, ptr, ptr]
    (fills last slot, no reallocation yet)

State after: a.append(5)
    ob_size = 5, allocated = 8, ob_item → [ptr, ptr, ptr, ptr, ptr, _, _, _]
    (REALLOCATION! grew from 4 to 8 slots)
```

Without `allocated`:
- Every append requires `realloc()` → O(n) copy each time
- n appends = O(1) + O(2) + O(3) + ... + O(n) = O(n²)

With `allocated`:
- Most appends are O(1) (just write to next slot)
- Occasional realloc is O(n)
- Amortized over n appends: O(1) per append (proven via potential method)

---

## 2.4 Complete Memory Layout on 64-bit CPython

For `a = [10, 20, 30]`:

```
═══════════════════════════════════════════════════════════════
HEAP: PyListObject (with GC header)
═══════════════════════════════════════════════════════════════
Address         Field            Value
────────────────────────────────────────────────────────────
0x7f001000      gc_prev          (GC linked list pointer)
0x7f001008      gc_next          (GC linked list pointer)  
0x7f001010      gc_refs          (GC reference info)
────────────────────────────────────────────────────────────
0x7f001018      ob_refcnt        1
0x7f001020      ob_type          → 0x904680 (PyList_Type)
0x7f001028      ob_size          3
0x7f001030      ob_item          → 0x7f002000
0x7f001038      allocated        4
════════════════════════════════════════════════════════════════

═══════════════════════════════════════════════════════════════
HEAP: ob_item array (separate allocation)
═══════════════════════════════════════════════════════════════
Address         Slot             Points To
────────────────────────────────────────────────────────────
0x7f002000      ob_item[0]       → 0x904a00 (PyLongObject for 10)
0x7f002008      ob_item[1]       → 0x904a20 (PyLongObject for 20)
0x7f002010      ob_item[2]       → 0x904a40 (PyLongObject for 30)
0x7f002018      ob_item[3]       (uninitialized / free slot)
════════════════════════════════════════════════════════════════

═══════════════════════════════════════════════════════════════
HEAP: Integer objects (small int cache for 10, 20, 30)
═══════════════════════════════════════════════════════════════
0x904a00        PyLongObject(10):  refcnt=N, type=&PyLong_Type, 
                                   ob_size=1, ob_digit=[10]
0x904a20        PyLongObject(20):  refcnt=N, type=&PyLong_Type,
                                   ob_size=1, ob_digit=[20]  
0x904a40        PyLongObject(30):  refcnt=N, type=&PyLong_Type,
                                   ob_size=1, ob_digit=[30]
════════════════════════════════════════════════════════════════
```

**Note**: Integers in range [-5, 256] are pre-allocated and cached by CPython. So `10`, `20`, `30` already exist — the list just points to the cached singletons. Their refcounts are high (referenced by the cache + any usage).

---

## 2.5 The Empty List

```python
a = []
```

```
PyListObject:
    ob_refcnt  = 1
    ob_type    = &PyList_Type
    ob_size    = 0        ← len() is 0
    ob_item    = NULL     ← no array allocated yet
    allocated  = 0        ← zero capacity
```

Memory cost of `[]`: just the PyListObject struct itself = ~56-64 bytes.

The first `append()` will allocate the `ob_item` array.

---

## 2.6 Why ob_item is a Separate Allocation

The pointer array is NOT embedded in the PyListObject struct. This is a deliberate design:

### Reason 1: Object Identity Stability

```python
a = [1, 2, 3]
ref = a              # ref points to same PyListObject
id_before = id(a)    # address of PyListObject
a.extend(range(100)) # triggers reallocation of ob_item
id_after = id(a)
assert id_before == id_after   # ALWAYS true
assert a is ref                # ALWAYS true
```

If the array were embedded, growing would require moving the entire object, breaking all references to it.

### Reason 2: Efficient Resizing

`realloc(ob_item, new_size)` only copies the pointer array. The PyListObject (40 bytes) stays in place. We never copy 40 bytes + N pointers — just the N pointers.

### Reason 3: Empty List Efficiency

Empty lists don't allocate any pointer array. If embedded, every list would need minimum space for the array even when empty.

### Reason 4: GC Tracking

The GC tracks objects by their address. If objects moved during resize, the GC's linked list would break.

---

## 2.7 The Free List Optimization

CPython maintains a **free list** of recently destroyed list objects to avoid frequent malloc/free:

```c
// Objects/listobject.c
#ifndef PyList_MAXFREELIST
#define PyList_MAXFREELIST 80
#endif

static PyListObject *free_list[PyList_MAXFREELIST];
static int numfree = 0;
```

When a list is destroyed:
- If the free list has space (numfree < 80), the PyListObject struct is saved
- The `ob_item` array is freed, but the struct itself is kept
- Next time `[]` or `list()` is called, a struct is popped from the free list

This means creating/destroying short-lived lists is cheap:
```python
for i in range(1000000):
    temp = [i, i+1, i+2]  # reuses PyListObject structs from free list
    process(temp)
    # temp destroyed → struct goes back to free list
```

---

## 2.8 sys.getsizeof() Explained

```python
import sys

sys.getsizeof([])           # 56 bytes
sys.getsizeof([1])          # 64 bytes  (56 + 1*8)
sys.getsizeof([1,2])        # 72 bytes  (56 + 2*8)
sys.getsizeof([1,2,3])      # 88 bytes  (56 + 4*8) ← overallocated!
sys.getsizeof([1,2,3,4])    # 88 bytes  (56 + 4*8)
```

**What sys.getsizeof reports**: PyListObject struct + ob_item array
**What it does NOT report**: The memory used by the contained objects

The 56-byte base:
- 40 bytes PyListObject fields
- 16 bytes GC overhead and alignment padding

The per-slot cost: 8 bytes (one pointer)

**WARNING**: `sys.getsizeof([1,2,3])` reports 88 bytes. But the TRUE memory cost is:
```
88 (list + pointer array)
+ 28 * 3 (three PyLongObject integers, if not cached)
= 172 bytes
```

For deep memory measurement, use `pympler.asizeof` or `objgraph`.

---

## 2.9 CPython Source References

| File | Content |
|------|---------|
| `Include/cpython/listobject.h` | PyListObject struct definition |
| `Include/listobject.h` | Public C API (`PyList_New`, `PyList_Size`, etc.) |
| `Objects/listobject.c` | All implementation code |
| `Include/object.h` | PyObject_VAR_HEAD macro |

The struct definition with official comments:
```c
// Include/cpython/listobject.h
typedef struct {
    PyObject_VAR_HEAD
    /* Vector of pointers to list elements.  list[0] is ob_item[0], etc. */
    PyObject **ob_item;

    /* ob_item contains space for 'allocated' elements.  The number
     * currently in use is ob_size.
     * Invariants:
     *     0 <= ob_size <= allocated
     *     len(list) == ob_size
     *     ob_item == NULL implies ob_size == allocated == 0
     * list.sort() temporarily sets allocated to -1 to detect mutations.
     *
     * Note: list.sort() does not change ob_size during sort.
     */
    Py_ssize_t allocated;
} PyListObject;
```

---

## 2.10 Interview Questions — Part 2

**Q1**: What is the total size of a PyListObject struct on 64-bit?
**A**: 40 bytes for the fields (5 × 8 bytes). With GC header, ~64 bytes. `sys.getsizeof([])` reports ~56 bytes (includes GC overhead, varies by version).

**Q2**: Does `sys.getsizeof(my_list)` include the memory of contained objects?
**A**: No. It reports only the list object + its pointer array. To get total recursive size, use `pympler.asizeof()`.

**Q3**: What happens to `ob_item` when you call `a.append(x)` and the list is full?
**A**: `ob_item` is reallocated (via `PyMem_Realloc`) to a larger block. The pointer value stored in `ob_item` changes, but the PyListObject's address doesn't.

**Q4**: What is the CPython free list for lists?
**A**: A cache of up to 80 recently-destroyed PyListObject structs. Creating a new list checks this cache first, avoiding `malloc`. Only the struct is cached — the ob_item array is always freed.

**Q5**: What value does `allocated` take during `list.sort()`?
**A**: -1. This is a sentinel that causes any concurrent modification attempt to detect the sort-in-progress and raise `ValueError: list modified during sort`.

**Q6**: Can `ob_size` ever exceed `allocated`?
**A**: Never. The invariant `0 <= ob_size <= allocated` is maintained by all operations. Violating it would mean writing past the end of the allocated array — a buffer overflow.
