# Part 7 — Time Complexity

## 7.1 Philosophy: Derive, Don't Memorize

For every operation, we will:
1. Describe what the operation does internally
2. Identify the dominant work
3. Derive the complexity from first principles

---

## 7.2 append(x) — Amortized O(1)

**What happens internally:**
```c
static int
app1(PyListObject *self, PyObject *v)
{
    Py_ssize_t n = Py_SIZE(self);
    if (list_resize(self, n+1) < 0)  // May trigger realloc
        return -1;
    self->ob_item[n] = Py_NewRef(v); // Store pointer, incref
    return 0;
}
```

**Derivation:**
- Without resize: write 1 pointer + incref = O(1)
- With resize: copy n pointers + allocate = O(n)
- Resize frequency: every ~n/8 appends (12.5% growth)
- Amortized: total work for n appends = n (writes) + geometric series of copies ≈ 9n
- Per append: 9n/n = **O(1) amortized**

---

## 7.3 extend(iterable) — O(k) where k = len(iterable)

**What happens internally:**
```c
static PyObject *
list_extend(PyListObject *self, PyObject *iterable)
{
    Py_ssize_t n = Py_SIZE(self);
    Py_ssize_t m = PySequence_Fast_GET_SIZE(iterable);
    
    // Single resize for all new items:
    if (list_resize(self, n + m) < 0)
        return NULL;
    
    // Copy all m pointers:
    PyObject **src = PySequence_Fast_ITEMS(iterable);
    PyObject **dest = self->ob_item + n;
    for (Py_ssize_t i = 0; i < m; i++) {
        dest[i] = Py_NewRef(src[i]);
    }
    return Py_None;
}
```

**Derivation:**
- One resize call: O(n + m) worst case (if realloc moves)
- Copy m pointers: O(m)
- But typically n + m ~ n (when extending by small amount): O(n) worst case
- If no resize needed: O(m) — just copy m pointers
- **Average/Typical: O(k) where k = number of items added**
- **Worst case: O(n + k)** (if reallocation is triggered)

---

## 7.4 insert(i, x) — O(n)

**What happens internally:**
```c
static int
ins1(PyListObject *self, Py_ssize_t where, PyObject *v)
{
    Py_ssize_t n = Py_SIZE(self);
    
    if (list_resize(self, n+1) < 0)
        return -1;
    
    // Clamp where to valid range
    if (where > n) where = n;
    if (where < 0) { where += n; if (where < 0) where = 0; }
    
    // Shift elements right:
    PyObject **items = self->ob_item;
    for (Py_ssize_t i = n; --i >= where; )
        items[i+1] = items[i];
    
    items[where] = Py_NewRef(v);
    return 0;
}
```

**Derivation:**
- Must shift (n - i) elements right to make room
- Best case (insert at end, i=n): shift 0 elements → O(1)
- Worst case (insert at start, i=0): shift n elements → O(n)
- Average case (random i): shift n/2 elements → O(n)
- **O(n)** (worst and average)

---

## 7.5 remove(x) — O(n)

**What happens internally:**
```c
static PyObject *
list_remove(PyListObject *self, PyObject *value)
{
    Py_ssize_t i;
    // Phase 1: Linear search
    for (i = 0; i < Py_SIZE(self); i++) {
        int cmp = PyObject_RichCompareBool(self->ob_item[i], value, Py_EQ);
        if (cmp > 0) {
            // Phase 2: Shift elements left
            if (list_ass_slice(self, i, i+1, NULL) == 0)
                Py_RETURN_NONE;
            return NULL;
        }
        if (cmp < 0) return NULL;  // comparison raised exception
    }
    PyErr_SetString(PyExc_ValueError, "list.remove(x): x not in list");
    return NULL;
}
```

**Derivation:**
- Phase 1 (search): scan up to n elements → O(n)
- Phase 2 (shift): move (n - i) elements left → O(n)
- Total: O(n) + O(n) = **O(n)**
- Best case (first element): O(1) search + O(n) shift = O(n)
- Worst case (last element): O(n) search + O(1) shift = O(n)
- Either way: **O(n)**

---

## 7.6 index(x) — O(n)

**What happens internally:**
```c
static PyObject *
list_index_impl(PyListObject *self, PyObject *value,
                Py_ssize_t start, Py_ssize_t stop)
{
    for (Py_ssize_t i = start; i < stop; i++) {
        int cmp = PyObject_RichCompareBool(self->ob_item[i], value, Py_EQ);
        if (cmp > 0) return PyLong_FromSsize_t(i);
        if (cmp < 0) return NULL;
    }
    PyErr_Format(PyExc_ValueError, "%R is not in list", value);
    return NULL;
}
```

**Derivation:**
- Linear scan through elements
- Best case: found at index 0 → O(1)
- Worst case: found at last index or not found → O(n)
- Average case: n/2 comparisons → **O(n)**

---

## 7.7 count(x) — O(n)

**What happens internally:**
```c
static PyObject *
list_count(PyListObject *self, PyObject *value)
{
    Py_ssize_t count = 0;
    for (Py_ssize_t i = 0; i < Py_SIZE(self); i++) {
        int cmp = PyObject_RichCompareBool(self->ob_item[i], value, Py_EQ);
        if (cmp > 0) count++;
        if (cmp < 0) return NULL;
    }
    return PyLong_FromSsize_t(count);
}
```

**Derivation:**
- MUST scan ALL elements (can't stop early — need total count)
- Always exactly n comparisons
- **Θ(n)** (always, not just worst case)

---

## 7.8 reverse() — O(n)

**What happens internally:**
```c
static PyObject *
list_reverse_impl(PyListObject *self)
{
    if (Py_SIZE(self) > 1)
        reverse_slice(self->ob_item, self->ob_item + Py_SIZE(self));
    Py_RETURN_NONE;
}

static void
reverse_slice(PyObject **lo, PyObject **hi)
{
    --hi;
    while (lo < hi) {
        PyObject *t = *lo;
        *lo = *hi;
        *hi = t;
        ++lo;
        --hi;
    }
}
```

**Derivation:**
- Swap n/2 pairs of pointers
- Each swap: O(1) (just exchange two 8-byte values)
- Total: n/2 swaps = **O(n)**
- Note: NO object copying — just pointer swaps. Very cache-friendly since it walks the contiguous ob_item array.

---

## 7.9 sort() — O(n log n)

**What happens internally:**
- TimSort algorithm (covered in detail in Part 10)
- Comparison-based sort

**Derivation:**
- Best case (already sorted): O(n) — TimSort detects runs
- Average case: O(n log n)
- Worst case: O(n log n)
- **O(n log n)** typical
- Space: O(n) auxiliary (for merge operations)

---

## 7.10 copy() / list[:] — O(n)

**What happens internally:**
```c
static PyObject *
list_copy_impl(PyListObject *self)
{
    return list_slice(self, 0, Py_SIZE(self));
}
```

**Derivation:**
- Allocate new PyListObject: O(1)
- Allocate new ob_item array of n slots: O(1)
- Copy n pointers: O(n)
- Py_INCREF each element: O(n)
- Total: **O(n)**
- Note: This is a SHALLOW copy — only pointers are copied, not the objects themselves.

---

## 7.11 clear() — O(n)

**What happens internally:**
```c
static int
_list_clear(PyListObject *a)
{
    PyObject **items = a->ob_item;
    Py_ssize_t i = Py_SIZE(a);
    
    Py_SET_SIZE(a, 0);
    a->ob_item = NULL;
    a->allocated = 0;
    
    // Decref all items (may trigger cascading destructions)
    while (--i >= 0)
        Py_XDECREF(items[i]);
    
    // Free the pointer array
    PyMem_Free(items);
    return 0;
}
```

**Derivation:**
- Must Py_DECREF each of the n elements: O(n)
- Free the pointer array: O(1)
- **O(n)** due to reference count updates
- Note: Even though we're "just clearing", we must touch every element to maintain refcounts correctly.

---

## 7.12 Slicing `a[i:j]` — O(j - i) = O(k)

**What happens:**
- Create new list of size (j - i)
- Copy (j - i) pointers from source
- Incref each copied pointer

**Derivation:**
- k = j - i elements to copy
- Each copy: O(1) pointer copy + O(1) incref
- Total: **O(k)** where k is slice length
- `a[:]` (full slice): O(n)

---

## 7.13 Slice Assignment `a[i:j] = b` — O(n + k)

**What happens:**
- If len(b) != j-i: shift elements to make/remove space → O(n)
- Copy k new pointers into position: O(k)
- Decref old elements, incref new elements: O(j-i) + O(k)

**Derivation:**
- Worst case: **O(n + k)** where k = len(b)
- If same length (j-i == len(b)): just replace pointers → O(k)

---

## 7.14 Membership `x in a` — O(n)

**What happens:**
```c
static int
list_contains(PyListObject *a, PyObject *el)
{
    for (Py_ssize_t i = 0; i < Py_SIZE(a); i++) {
        int cmp = PyObject_RichCompareBool(a->ob_item[i], el, Py_EQ);
        if (cmp > 0) return 1;   // Found!
        if (cmp < 0) return -1;  // Error
    }
    return 0;  // Not found
}
```

**Derivation:**
- Linear scan, stops on first match
- Best case: O(1) (first element matches)
- Worst case: O(n) (not found, scan entire list)
- Average: **O(n)**

---

## 7.15 Concatenation `a + b` — O(n + m)

**What happens:**
```c
static PyObject *
list_concat(PyListObject *a, PyObject *bb)
{
    PyListObject *np;
    Py_ssize_t size = Py_SIZE(a) + Py_SIZE(b);
    
    np = (PyListObject *) list_new_prealloc(size);
    // Copy pointers from a:
    PyObject **src = a->ob_item;
    PyObject **dest = np->ob_item;
    for (Py_ssize_t i = 0; i < Py_SIZE(a); i++)
        dest[i] = Py_NewRef(src[i]);
    // Copy pointers from b:
    src = b->ob_item;
    dest = np->ob_item + Py_SIZE(a);
    for (Py_ssize_t i = 0; i < Py_SIZE(b); i++)
        dest[i] = Py_NewRef(src[i]);
    
    return (PyObject *)np;
}
```

**Derivation:**
- Create new list: O(1)
- Copy n pointers from a: O(n)
- Copy m pointers from b: O(m)
- **O(n + m)**
- CREATES NEW LIST (doesn't modify a or b)

---

## 7.16 Multiplication `a * k` — O(n × k)

**What happens:**
- Creates new list of size n*k
- Copies n pointers k times

**Derivation:**
- Total pointers to copy: n × k
- **O(n × k)**

---

## 7.17 Complete Complexity Table

| Operation | Best | Average | Worst | Space | Notes |
|-----------|------|---------|-------|-------|-------|
| `a[i]` | O(1) | O(1) | O(1) | O(1) | Index bounds check + pointer arith |
| `a[i] = x` | O(1) | O(1) | O(1) | O(1) | Decref old + store + incref new |
| `a.append(x)` | O(1) | O(1)* | O(n) | O(n)† | *amortized, †resize allocation |
| `a.extend(b)` | O(k) | O(k) | O(n+k) | O(n+k)† | k=len(b), †if resize |
| `a.insert(i,x)` | O(1)‡ | O(n) | O(n) | O(n)† | ‡insert at end only |
| `a.remove(x)` | O(n) | O(n) | O(n) | O(1) | Search + shift |
| `a.pop()` | O(1) | O(1) | O(1) | O(1) | No shift needed |
| `a.pop(i)` | O(1)‡ | O(n) | O(n) | O(1) | ‡pop from end only |
| `a.index(x)` | O(1) | O(n) | O(n) | O(1) | Linear search |
| `a.count(x)` | O(n) | O(n) | O(n) | O(1) | Must scan all |
| `a.reverse()` | O(n) | O(n) | O(n) | O(1) | In-place pointer swap |
| `a.sort()` | O(n) | O(n log n) | O(n log n) | O(n) | TimSort |
| `a.copy()` | O(n) | O(n) | O(n) | O(n) | Shallow copy |
| `a.clear()` | O(n) | O(n) | O(n) | O(1)§ | §frees memory |
| `a[i:j]` | O(k) | O(k) | O(k) | O(k) | k = j-i |
| `x in a` | O(1) | O(n) | O(n) | O(1) | Linear scan |
| `a + b` | O(n+m) | O(n+m) | O(n+m) | O(n+m) | New list |
| `a * k` | O(nk) | O(nk) | O(nk) | O(nk) | New list |
| `len(a)` | O(1) | O(1) | O(1) | O(1) | Just read ob_size |
| `del a[i]` | O(1)‡ | O(n) | O(n) | O(1) | ‡del last only |
| `min(a)/max(a)` | O(n) | O(n) | O(n) | O(1) | Full scan |

---

## 7.18 Common Complexity Traps

### Trap 1: Loop with insert(0, x)

```python
# O(n²) — each insert shifts everything!
result = []
for x in data:          # n iterations
    result.insert(0, x) # O(n) each
# Total: O(n²)

# Fix: append then reverse → O(n)
result = []
for x in data:
    result.append(x)    # O(1) amortized
result.reverse()        # O(n)
# Total: O(n)
```

### Trap 2: Loop with `x in list`

```python
# O(n²) — membership test is O(n) per check!
for x in list_a:        # n iterations
    if x in list_b:     # O(m) each
        process(x)
# Total: O(n × m)

# Fix: convert to set → O(n + m)
set_b = set(list_b)     # O(m)
for x in list_a:        # n iterations
    if x in set_b:      # O(1) each
        process(x)
# Total: O(n + m)
```

### Trap 3: Repeated concatenation

```python
# O(n²) — each + creates a new list and copies!
result = []
for chunk in chunks:       # k chunks of size m
    result = result + chunk # O(len(result)) each time!
# Total: O(m + 2m + 3m + ... + km) = O(k²m)

# Fix: use extend → O(km)
result = []
for chunk in chunks:
    result.extend(chunk)   # O(m) each (amortized)
# Total: O(km)
```

---

## 7.19 Interview Questions — Part 7

**Q1**: Why is `list.remove(x)` O(n) even when x is at the beginning?
**A**: Even if found at index 0, all remaining n-1 elements must shift left. Search is O(1) but shift is O(n). Total still O(n).

**Q2**: What's the difference between `a.append(x)` and `a.insert(len(a), x)`?
**A**: Functionally identical. But `insert` has slightly more overhead (bounds checking, loop setup). Both are O(1) when inserting at the end.

**Q3**: Why is `a.clear()` O(n) and not O(1)?
**A**: Must Py_DECREF every element to maintain reference counts. Even though no shifting happens, touching n reference counts is O(n).

**Q4**: Is `a.reverse()` faster than `a[::-1]`?
**A**: Yes. `reverse()` swaps pointers in-place (O(n), no allocation). `a[::-1]` creates a NEW list, copies n pointers, and increfs n objects (O(n) + O(n) memory).

**Q5**: Why is `for x in data: result += [x]` slower than `for x in data: result.append(x)`?
**A**: `result += [x]` creates a temporary list `[x]` each iteration (allocation + deallocation overhead). `append` adds directly. Both are O(1) amortized, but append has much smaller constant.
