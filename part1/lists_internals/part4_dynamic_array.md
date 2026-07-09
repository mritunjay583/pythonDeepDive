# Part 4 — Dynamic Array

## 4.1 The Core Concept

A **dynamic array** is an array that automatically resizes itself when full. The key insight is:

> Allocate more space than currently needed, so that MOST insertions at the end are O(1). Only occasionally pay the O(n) cost of copying when the buffer is exhausted.

CPython's list is a textbook dynamic array with one twist: it stores pointers, not values.

---

## 4.2 Capacity vs Length

Two numbers govern a list's state:

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  ob_size (length)     = number of items currently stored│
│  allocated (capacity) = total slots available           │
│                                                         │
│  ┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐   │
│  │ obj │ obj │ obj │ obj │ obj │     │     │     │   │
│  └─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘   │
│  ├──────── ob_size = 5 ────────┤                       │
│  ├──────────────── allocated = 8 ─────────────────┤    │
│  │                              ├── free slots ───┤    │
│                                                         │
└─────────────────────────────────────────────────────────┘

len(my_list) → ob_size
Free space   → allocated - ob_size
```

---

## 4.3 Growth: What Happens on append()

### Case 1: Space Available (ob_size < allocated)

```python
# State: ob_size=3, allocated=8
a.append(x)
```

```
BEFORE:
┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│ p0  │ p1  │ p2  │     │     │     │     │     │
└─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
ob_size=3, allocated=8

AFTER:
┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│ p0  │ p1  │ p2  │ px  │     │     │     │     │
└─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
ob_size=4, allocated=8

Cost: O(1) — just write one pointer and increment ob_size
```

Steps:
1. `ob_item[ob_size] = x`  (store pointer)
2. `Py_INCREF(x)`  (increment reference count of x)
3. `ob_size += 1`

### Case 2: Full (ob_size == allocated)

```python
# State: ob_size=8, allocated=8
a.append(x)
```

```
BEFORE:
┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│ p0  │ p1  │ p2  │ p3  │ p4  │ p5  │ p6  │ p7  │  FULL!
└─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
ob_size=8, allocated=8

REALLOCATION TRIGGERED:
new_allocated = 8 + (8 >> 3) + 6 = 8 + 1 + 6 = 15
(actual formula — see Part 5 for details)

AFTER (new, larger array):
┌────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┐
│ p0 │ p1 │ p2 │ p3 │ p4 │ p5 │ p6 │ p7 │ px │    │    │    │    │    │    │
└────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┘
ob_size=9, allocated=15

Cost: O(n) — copy all existing pointers to new array
```

Steps:
1. Calculate `new_allocated` using overallocation formula
2. `ob_item = PyMem_Realloc(ob_item, new_allocated * sizeof(PyObject*))`
3. If realloc moved the block, all pointers are already copied
4. `ob_item[ob_size] = x`
5. `Py_INCREF(x)`
6. `ob_size += 1`
7. `allocated = new_allocated`

---

## 4.4 Why append() is Amortized O(1)

### The Amortization Argument

Consider n append operations starting from an empty list. Let's say the list doubles in capacity each time (simplified — CPython grows by ~12.5%, analyzed in Part 5).

Resizing happens at sizes: 1, 2, 4, 8, 16, ..., n/2, n

Copying costs at each resize: 1 + 2 + 4 + 8 + ... + n = 2n - 1

Total cost for n appends:
- n constant-time writes (one per append)
- Plus ~2n total copying work across all resizes
- Total: ~3n

Average per append: 3n/n = **O(1) amortized**

### Formal Proof (Potential Method)

Define potential function:
```
Φ(list) = 2 * ob_size - allocated
```

For a regular append (no resize):
- Actual cost: 1
- ΔΦ = 2(ob_size+1) - allocated - (2*ob_size - allocated) = 2
- Amortized cost = actual + ΔΦ = 1 + 2 = 3

For a resize append (when ob_size == allocated == n, grows to 2n):
- Actual cost: n + 1 (copy n elements + write 1)
- ΔΦ = 2(n+1) - 2n - (2n - n) = 2n + 2 - 2n - n = 2 - n
- Amortized cost = (n+1) + (2-n) = 3

Every append has amortized cost 3 = **O(1)**.

### Why NOT exact doubling in CPython?

CPython grows by approximately (n + n>>3 + 6), which is ~12.5% growth. This is MORE conservative than doubling:

- Doubling: wastes up to 50% memory
- 12.5% growth: wastes up to ~12.5% memory
- Tradeoff: more frequent resizes, but less wasted memory

Still amortized O(1), just with a larger constant.

---

## 4.5 Why insert(i, x) is O(n)

```python
a = [10, 20, 30, 40, 50]
a.insert(2, 99)  # Insert 99 at index 2
```

```
BEFORE insert(2, 99):
┌────┬────┬────┬────┬────┬────┐
│ 10 │ 20 │ 30 │ 40 │ 50 │    │
└────┴────┴────┴────┴────┴────┘
  [0]  [1]  [2]  [3]  [4]  free

Step 1: Shift elements [2..4] right by one:
┌────┬────┬────┬────┬────┬────┐
│ 10 │ 20 │    │ 30 │ 40 │ 50 │   ← shifted 30,40,50 right
└────┴────┴────┴────┴────┴────┘
  [0]  [1]  [2]  [3]  [4]  [5]

Step 2: Write new element at position 2:
┌────┬────┬────┬────┬────┬────┐
│ 10 │ 20 │ 99 │ 30 │ 40 │ 50 │
└────┴────┴────┴────┴────┴────┘
  [0]  [1]  [2]  [3]  [4]  [5]

ob_size: 5 → 6
```

The shift operation is `memmove` of `(ob_size - i) * sizeof(PyObject*)` bytes.

- Insert at beginning `insert(0, x)`: shift ALL n elements → O(n)
- Insert at end `insert(len, x)`: shift 0 elements → O(1) (same as append)
- Insert at middle `insert(n/2, x)`: shift n/2 elements → O(n)
- **Worst/Average case: O(n)**

CPython source (`Objects/listobject.c`):
```c
static int
ins1(PyListObject *self, Py_ssize_t where, PyObject *v)
{
    Py_ssize_t i, n = Py_SIZE(self);
    // ... resize if needed ...
    
    // Shift items right:
    items = self->ob_item;
    for (i = n; --i >= where; )
        items[i+1] = items[i];    // memmove equivalent
    
    items[where] = Py_NewRef(v);
    Py_SET_SIZE(self, n + 1);
    return 0;
}
```

---

## 4.6 Why remove(x) is O(n)

```python
a = [10, 20, 30, 40, 50]
a.remove(30)  # Remove first occurrence of 30
```

Two O(n) operations:
1. **Search**: Linear scan to find 30 → O(n)
2. **Shift**: Move elements left to fill gap → O(n)

```
Step 1: Find 30 at index 2 (linear scan)
┌────┬────┬────┬────┬────┐
│ 10 │ 20 │ 30 │ 40 │ 50 │
└────┴────┴──▲─┴────┴────┘
             │ found!

Step 2: Shift elements [3..4] left by one:
┌────┬────┬────┬────┬────┐
│ 10 │ 20 │ 40 │ 50 │ ?? │  ← shifted 40,50 left
└────┴────┴────┴────┴────┘

Step 3: Decrement size, Py_DECREF(30):
┌────┬────┬────┬────┐
│ 10 │ 20 │ 40 │ 50 │
└────┴────┴────┴────┘
ob_size: 5 → 4
```

Total: O(n) search + O(n) shift = **O(n)**

---

## 4.7 Why pop() from End is O(1)

```python
a = [10, 20, 30, 40, 50]
x = a.pop()  # Remove and return last element
```

```
BEFORE:
┌────┬────┬────┬────┬────┬────┐
│ 10 │ 20 │ 30 │ 40 │ 50 │    │
└────┴────┴────┴────┴────┴────┘
ob_size=5

AFTER:
┌────┬────┬────┬────┬────┬────┐
│ 10 │ 20 │ 30 │ 40 │    │    │  ← slot[4] now unused
└────┴────┴────┴────┴────┴────┘
ob_size=4, x = ptr_to_50
```

Steps:
1. Save `ob_item[ob_size - 1]` as return value
2. `ob_size -= 1`
3. (Maybe shrink if way too much wasted space — but typically no realloc)
4. Return saved value (WITHOUT decref — ownership transfers to caller)

No shifting needed. **O(1)**.

CPython implementation:
```c
static PyObject *
list_pop_impl(PyListObject *self, Py_ssize_t index)
{
    // For pop() with no argument, index = ob_size - 1
    PyObject *v;
    Py_ssize_t size = Py_SIZE(self);
    
    v = self->ob_item[index];
    // ... handle shrinking ...
    Py_SET_SIZE(self, size - 1);
    // Note: v is returned with its reference "stolen" from the list
    return v;
}
```

---

## 4.8 Why pop(0) is O(n)

```python
a = [10, 20, 30, 40, 50]
x = a.pop(0)  # Remove and return FIRST element
```

```
BEFORE:
┌────┬────┬────┬────┬────┐
│ 10 │ 20 │ 30 │ 40 │ 50 │
└────┴────┴────┴────┴────┘
  [0]  [1]  [2]  [3]  [4]

Step 1: Save ob_item[0] (= ptr to 10) as return value

Step 2: Shift ALL remaining elements left:
┌────┬────┬────┬────┬────┐
│ 20 │ 30 │ 40 │ 50 │ ?? │
└────┴────┴────┴────┴────┘

Step 3: ob_size -= 1
┌────┬────┬────┬────┐
│ 20 │ 30 │ 40 │ 50 │
└────┴────┴────┴────┘
ob_size=4, x = ptr_to_10
```

Must shift n-1 elements left. **O(n)**.

This is why `collections.deque` exists — it provides O(1) `popleft()`:
```python
from collections import deque
d = deque([10, 20, 30, 40, 50])
x = d.popleft()  # O(1)!
```

---

## 4.9 Shrink Behavior

CPython doesn't just grow — it also **shrinks** the allocated array when it becomes too wasteful.

The shrink condition (from `list_resize` in `Objects/listobject.c`):
```c
// Shrink if the new size is less than half the allocated space
if (allocated >= newsize && newsize >= (allocated >> 1)) {
    // No realloc needed — just adjust ob_size
    Py_SET_SIZE(self, newsize);
    return 0;
}
```

Translation:
- If `newsize >= allocated/2`: don't shrink (not worth it)
- If `newsize < allocated/2`: realloc to a smaller array

Example:
```python
a = list(range(1000))   # allocated ≈ 1000
for _ in range(900):
    a.pop()             # Eventually triggers shrink

# After removing many items, CPython will resize the internal
# array smaller to avoid wasting memory
```

The shrink behavior is conservative — CPython won't constantly reallocate if you're near the threshold. The hysteresis prevents oscillation (repeatedly growing and shrinking at a boundary).

---

## 4.10 The del Operation

```python
a = [10, 20, 30, 40, 50]
del a[2]  # Delete element at index 2
```

```
BEFORE:
┌────┬────┬────┬────┬────┐
│ 10 │ 20 │ 30 │ 40 │ 50 │
└────┴────┴────┴────┴────┘

Step 1: Py_DECREF(a[2])  — may trigger object destruction
Step 2: Shift [3..4] left by one:
┌────┬────┬────┬────┐
│ 10 │ 20 │ 40 │ 50 │
└────┴────┴────┴────┘
ob_size: 5 → 4
```

Equivalent to `remove()` but without the search phase — you specify the index directly.
- `del a[i]` is O(n) because of shifting (O(n-i) specifically)
- `del a[-1]` is O(1) — no shifting needed (same as pop())

---

## 4.11 extend() vs Repeated append()

```python
# Method 1: extend
a.extend([1, 2, 3, 4, 5])

# Method 2: loop append
for x in [1, 2, 3, 4, 5]:
    a.append(x)
```

`extend()` is faster because:
1. It calculates the final size once: `new_size = ob_size + len(iterable)`
2. Resizes once (at most): one `list_resize` call
3. Copies all pointers in bulk

Repeated `append()`:
1. May trigger multiple resizes
2. Each append has function call overhead
3. Each append checks bounds independently

Both are O(k) where k is the number of items added, but `extend` has smaller constants.

---

## 4.12 Complexity Summary Table

| Operation | Average Case | Worst Case | Why |
|-----------|-------------|------------|-----|
| `a[i]` | O(1) | O(1) | Pointer arithmetic |
| `a[i] = x` | O(1) | O(1) | Pointer write |
| `a.append(x)` | O(1) amortized | O(n) | Occasional realloc |
| `a.insert(i, x)` | O(n) | O(n) | Shift elements right |
| `a.pop()` | O(1) | O(1) | No shifting |
| `a.pop(i)` | O(n) | O(n) | Shift elements left |
| `a.pop(0)` | O(n) | O(n) | Shift all elements |
| `a.remove(x)` | O(n) | O(n) | Search + shift |
| `del a[i]` | O(n) | O(n) | Shift elements left |
| `len(a)` | O(1) | O(1) | Read ob_size |
| `x in a` | O(n) | O(n) | Linear scan |
| `a.extend(b)` | O(k) | O(n+k) | Possible resize + copy k items |

---

## 4.13 Interview Questions — Part 4

**Q1**: Why is `list.append()` O(1) amortized but `list.insert(0, x)` is O(n)?
**A**: `append` writes to the next free slot — no shifting. `insert(0, x)` must shift ALL existing elements right by one position, which is O(n) memmove.

**Q2**: When does `append()` become O(n)?
**A**: When `ob_size == allocated` (the buffer is full). The entire pointer array must be reallocated and copied. This happens infrequently enough that the amortized cost is O(1).

**Q3**: Why is `pop()` O(1) but `pop(0)` O(n)?
**A**: `pop()` removes the last element — no shifting needed, just decrement `ob_size`. `pop(0)` removes the first element, requiring all remaining n-1 elements to shift left.

**Q4**: What data structure gives O(1) for both append and popleft?
**A**: `collections.deque` — implemented as a doubly-linked list of fixed-size blocks (64 items per block). O(1) at both ends.

**Q5**: Does CPython ever shrink the allocated array?
**A**: Yes. When the list size drops below half the allocated capacity, CPython reallocates to a smaller array. This prevents permanently wasting memory after mass deletions.

**Q6**: How can you avoid reallocation overhead when you know the final size?
**A**: Pre-allocate: `a = [None] * n` then assign to indices. Or use a list comprehension which pre-sizes the result. There's no direct `list.reserve(n)` in Python.

**Q7**: Is `a += [x]` the same as `a.append(x)`?
**A**: No. `a += [x]` calls `list.extend([x])` which creates a temporary list `[x]` first. `a.append(x)` is a direct single-element insertion. `append` is more efficient for single items.
