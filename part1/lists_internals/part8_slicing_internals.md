# Part 8 — Slicing Internals

## 8.1 Fundamental Principle: Slices Are Copies

Unlike NumPy arrays, **Python list slices always create new lists**. There are no views.

```python
a = [1, 2, 3, 4, 5]
b = a[1:4]  # b is a NEW list: [2, 3, 4]

b[0] = 99
print(a)    # [1, 2, 3, 4, 5] — unchanged!
print(b)    # [99, 3, 4]
```

This is a **language guarantee**, not just an implementation detail.

---

## 8.2 How Slicing Works Internally

### Reading a Slice: `a[i:j]`

```c
static PyObject *
list_slice(PyListObject *a, Py_ssize_t ilow, Py_ssize_t ihigh)
{
    Py_ssize_t len = ihigh - ilow;
    PyListObject *np = (PyListObject *) list_new_prealloc(len);
    if (np == NULL)
        return NULL;
    
    PyObject **src = a->ob_item + ilow;
    PyObject **dest = np->ob_item;
    for (Py_ssize_t i = 0; i < len; i++) {
        PyObject *v = src[i];
        dest[i] = Py_NewRef(v);  // Copy pointer AND incref
    }
    Py_SET_SIZE(np, len);
    return (PyObject *)np;
}
```

Steps:
1. Calculate slice length: `k = j - i`
2. Allocate new PyListObject
3. Allocate new ob_item array (size = k, no overallocation)
4. Copy k pointers from source to destination
5. Py_INCREF each pointed-to object
6. Return new list

Memory diagram for `b = a[1:4]`:
```
a → PyListObject
    ob_item → [*1, *2, *3, *4, *5]
                    ↑         ↑
                    i=1       j=4 (exclusive)

b → PyListObject (NEW)
    ob_item → [*2, *3, *4]  (NEW array)
               ↓   ↓   ↓
               │   │   └──→ same int(4) object (refcnt++)
               │   └──────→ same int(3) object (refcnt++)
               └──────────→ same int(2) object (refcnt++)
```

Key points:
- New list object allocated
- New pointer array allocated (sized exactly to slice length — NO overallocation)
- Pointers are COPIED (shallow)
- Objects are SHARED (both lists reference same objects)
- Reference counts incremented on shared objects

---

## 8.3 Slice with Step: `a[i:j:k]`

```python
a = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
b = a[1:8:2]  # [1, 3, 5, 7]
```

```c
static PyObject *
list_subscript(PyListObject *self, PyObject *item)
{
    // For slice with step:
    Py_ssize_t start, stop, step, slicelength;
    PySlice_Unpack(item, &start, &stop, &step);
    slicelength = PySlice_AdjustIndices(Py_SIZE(self), &start, &stop, step);
    
    PyListObject *result = (PyListObject *)list_new_prealloc(slicelength);
    
    PyObject **src = self->ob_item;
    PyObject **dest = result->ob_item;
    for (Py_ssize_t cur = start, i = 0; i < slicelength; cur += step, i++) {
        dest[i] = Py_NewRef(src[cur]);
    }
    Py_SET_SIZE(result, slicelength);
    return (PyObject *)result;
}
```

The step just changes which indices are selected. The result is still a new list with copied pointers.

---

## 8.4 Slice Assignment: `a[i:j] = b`

This is more complex because it may need to resize the original list.

```python
a = [0, 1, 2, 3, 4, 5]
a[2:4] = [10, 20, 30]  # Replace 2 items with 3 items
# a = [0, 1, 10, 20, 30, 4, 5]
```

### Case 1: Same length replacement (j-i == len(b))

```
BEFORE: a = [0, 1, 2, 3, 4, 5], a[2:4] = [10, 20]
        [*0, *1, *2, *3, *4, *5]
                  └──┬──┘
                  replace these 2 with 2 new

AFTER:  a = [0, 1, 10, 20, 4, 5]
        [*0, *1, *10, *20, *4, *5]

Steps:
1. Py_DECREF(old a[2]) → decref int(2)
2. Py_DECREF(old a[3]) → decref int(3)
3. a.ob_item[2] = Py_NewRef(int(10))
4. a.ob_item[3] = Py_NewRef(int(20))

Cost: O(k) where k = slice length. No shifting!
```

### Case 2: Shorter replacement (len(b) < j-i)

```
BEFORE: a = [0, 1, 2, 3, 4, 5], a[1:5] = [99]
        [*0, *1, *2, *3, *4, *5]
              └─────┬─────┘
              replace 4 items with 1

AFTER:  a = [0, 99, 5]
        [*0, *99, *5]

Steps:
1. Decref items a[1], a[2], a[3], a[4]
2. Store new item at a[1]
3. Shift a[5] left by 3 positions → a[2] = old a[5]
4. Reduce ob_size by 3 (6 - 4 + 1 = 3)
5. May shrink allocation if too wasteful

Cost: O(n) due to shifting
```

### Case 3: Longer replacement (len(b) > j-i)

```
BEFORE: a = [0, 1, 2, 3, 4, 5], a[2:3] = [10, 20, 30]
        [*0, *1, *2, *3, *4, *5]
                  └┘
                  replace 1 item with 3

Step 1: Need to make room — shift elements right:
        [*0, *1, __, __, __, *3, *4, *5]
                  ↑  ↑  ↑
                  room for 3 new items

Step 2: Insert new items:
        [*0, *1, *10, *20, *30, *3, *4, *5]

AFTER:  a = [0, 1, 10, 20, 30, 3, 4, 5]

Steps:
1. Resize list (may realloc): list_resize(self, new_total_size)
2. Shift elements [j..n-1] right by (len(b) - (j-i)) positions
3. Decref old items in slice range
4. Store new pointers, incref new items

Cost: O(n + k) — shift + copy new items
```

---

## 8.5 Slice Deletion: `del a[i:j]`

Equivalent to `a[i:j] = []` — replace slice with nothing.

```python
a = [0, 1, 2, 3, 4, 5]
del a[2:4]  # a = [0, 1, 4, 5]
```

```
BEFORE: [*0, *1, *2, *3, *4, *5]   ob_size=6
                  └──┬──┘
                  delete these

Step 1: Decref a[2], a[3]
Step 2: Shift a[4], a[5] left by 2:
        [*0, *1, *4, *5]            ob_size=4

Cost: O(n) — shifting dominates
```

---

## 8.6 No Views — Why?

### Why doesn't Python support list views (like NumPy)?

**Problem 1: Mutation safety**
```python
a = [1, 2, 3, 4, 5]
view = a[1:4]   # hypothetical view
a.append(6)     # This might realloc ob_item!
# view now points to freed memory → use-after-free bug!
```

With dynamic arrays that can reallocate, views would become dangling pointers. NumPy avoids this because ndarray doesn't reallocate (fixed size after creation).

**Problem 2: Reference counting complexity**
Views would need to keep the source list alive (preventing deallocation), creating complex lifetime dependencies.

**Problem 3: Insertion/deletion semantics**
What does `del view[0]` mean? Delete from the original list? This makes semantics confusing.

**The language choice**: Python chose simplicity and safety over performance. Slices are always independent copies.

### memoryview — The Exception

For bytes-like objects (buffer protocol), Python DOES support views:
```python
data = bytearray(b"hello world")
view = memoryview(data)[0:5]
view[0] = ord('H')
print(data)  # bytearray(b'Hello world') — modified original!
```

This works because bytearray doesn't reallocate on mutation of existing elements.

---

## 8.7 Negative Indices

```python
a = [10, 20, 30, 40, 50]
print(a[-2:])   # [40, 50]
print(a[:-1])   # [10, 20, 30, 40]
print(a[-3:-1]) # [30, 40]
```

Negative indices are converted to positive before slicing:
```c
// Conversion in PySlice_Unpack / adjust:
if (i < 0) i += length;  // -2 + 5 = 3
if (j < 0) j += length;  // -1 + 5 = 4
```

After conversion, the normal slicing logic applies. No special memory handling.

---

## 8.8 Performance Characteristics

### Slice Read Performance

| Operation | Time | Space | Notes |
|-----------|------|-------|-------|
| `a[i:j]` | O(j-i) | O(j-i) | Copy k pointers + incref each |
| `a[::2]` | O(n/2) | O(n/2) | Every other element |
| `a[:]` | O(n) | O(n) | Full shallow copy |
| `a[::-1]` | O(n) | O(n) | Reverse copy |

### Slice Write Performance

| Operation | Time | Space | Notes |
|-----------|------|-------|-------|
| `a[i:j] = b` (same len) | O(k) | O(1) | Just swap pointers |
| `a[i:j] = b` (shorter) | O(n) | O(1) | Shift left |
| `a[i:j] = b` (longer) | O(n+k) | O(n+k)† | May realloc + shift right |
| `del a[i:j]` | O(n) | O(1) | Shift left |

---

## 8.9 Nested List Slicing — The Shallow Copy Trap

```python
a = [[1, 2], [3, 4], [5, 6]]
b = a[:]  # Shallow copy of outer list

b[0].append(99)
print(a[0])  # [1, 2, 99] — MODIFIED! Inner lists are shared!
```

Memory diagram:
```
a → ob_item → [ptr0, ptr1, ptr2]
                 │     │     │
                 │     │     └──→ [5, 6]  ← shared!
                 │     └────────→ [3, 4]  ← shared!
                 └──────────────→ [1, 2]  ← shared!
                 ↑     ↑     ↑
b → ob_item → [ptr0, ptr1, ptr2]  (DIFFERENT array, SAME targets)
```

The slice copies POINTERS to the inner lists, not the inner lists themselves. Both `a[0]` and `b[0]` point to the same `[1, 2]` list object.

To get independent nested lists: `b = copy.deepcopy(a)`

---

## 8.10 Slice Object Internals

When you write `a[1:5:2]`, Python creates a `slice` object:

```python
s = slice(1, 5, 2)
# s.start = 1, s.stop = 5, s.step = 2

# These are equivalent:
a[1:5:2]
a[slice(1, 5, 2)]
a.__getitem__(slice(1, 5, 2))
```

The slice object itself is small (just three integers). The list's `__getitem__` method unpacks it and performs the copy.

---

## 8.11 Interview Questions — Part 8

**Q1**: Does `b = a[1:3]` create a view or a copy?
**A**: Always a copy. Python list slices create new independent lists. The pointers are copied (shallow copy), but a new list object and pointer array are allocated.

**Q2**: After `b = a[:]`, is `a[0] is b[0]` True or False?
**A**: True. The slice copies pointers — both `a[0]` and `b[0]` point to the same underlying object. It's a shallow copy.

**Q3**: Why can't Python lists support views like NumPy?
**A**: Because lists can be resized (append/insert may reallocate ob_item), which would invalidate any views pointing into the old array. NumPy arrays have fixed size, making views safe.

**Q4**: What's the time complexity of `a[i:j] = b` when len(b) == j-i?
**A**: O(k) where k = j-i. No shifting needed — just replace k pointers in place (decref old, incref new).

**Q5**: Does `a[::-1]` modify a in place?
**A**: No. It creates a NEW reversed list. Use `a.reverse()` for in-place reversal. `a[::-1]` costs O(n) time AND O(n) space; `a.reverse()` costs O(n) time and O(1) space.

**Q6**: After slicing, does the new list have overallocation?
**A**: No. Slices are allocated with exactly the needed size (allocated == ob_size). Overallocation only happens during append/growth operations.
