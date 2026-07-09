# Part 16 — Exercises

## Section A: Draw Memory Layouts (10 Exercises)

### Exercise A1
Draw the complete memory layout (PyListObject, ob_item array, pointed-to objects) for:
```python
a = [100, 200, 300]
```
Include: ob_refcnt, ob_type, ob_size, ob_item pointer, allocated field, pointer array, and integer objects.

---

### Exercise A2
Draw the memory layout showing shared references for:
```python
x = [1, 2, 3]
a = [x, x]
```
Show both PyListObjects, both ob_item arrays, and how they share the inner list.

---

### Exercise A3
Draw the memory after each line executes:
```python
a = [10, 20, 30]
b = a
c = a.copy()
a.append(40)
```
Show which objects are shared and which are independent.

---

### Exercise A4
Draw the memory layout for:
```python
a = [[]] * 3
```
Then show what happens after: `a[0].append(1)`

---

### Exercise A5
Draw the complete layout for a self-referential list:
```python
a = [1, 2]
a.append(a)
```
Show the circular pointer.

---

### Exercise A6
Draw the layout for a list containing different types:
```python
a = [42, "hello", 3.14, None, True]
```
Show how each element is a different object type on the heap.

---

### Exercise A7
Draw the memory state after:
```python
a = [1, 2, 3, 4, 5]
b = a[1:4]
```
Show that b is independent with its own ob_item array but shares integer objects.

---

### Exercise A8
Draw the memory before and after:
```python
a = [10, 20, 30, 40]
a.insert(2, 99)
```
Show the pointer shift operation.

---

### Exercise A9
Draw the memory for nested lists:
```python
matrix = [[1, 2], [3, 4]]
row = matrix[0]
```
Show that `row` and `matrix[0]` point to the same inner list.

---

### Exercise A10
Draw the full memory layout showing the difference between:
```python
import copy
original = [[1, 2], [3, 4]]
shallow = original.copy()
deep = copy.deepcopy(original)
```

---

## Section B: Trace Pointer Changes (10 Exercises)

### Exercise B1
Trace what happens to pointers and reference counts for each line:
```python
a = [1, 2, 3]     # Step 1
b = a              # Step 2
c = a[0]           # Step 3
del a              # Step 4
b.append(4)        # Step 5
```

For each step, list: which objects exist, their refcounts, and what names point where.

---

### Exercise B2
Trace the pointer operations during:
```python
a = [10, 20, 30]
a[1] = 99
```
What happens to the pointer at ob_item[1]? What happens to the refcount of int(20) and int(99)?

---

### Exercise B3
Trace the operations during `a.pop(1)` for `a = [10, 20, 30, 40]`:
1. What value is saved?
2. What pointers shift?
3. What happens to ob_size?
4. What happens to the refcount of int(20)?

---

### Exercise B4
Trace what happens when you do:
```python
a = [1, 2, 3]
a = a + [4, 5]
```
How many list objects exist at each point? What happens to the old list?

---

### Exercise B5
Trace the reference count changes:
```python
a = [1, 2, 3]
b = a.copy()
del a
del b
```
At what point does the list's ob_item get freed? At what point do integers get their refcounts decremented?

---

### Exercise B6
Trace operations for:
```python
a = [1, 2, 3, 4, 5]
a[1:4] = [10]
```
List the steps: which pointers are decrefed, which are increfed, which elements shift.

---

### Exercise B7
Trace what happens during:
```python
a = [1, 2, 3]
b = [a, a, a]
a.append(4)
del b
```
What are the refcounts of list `a` at each step?

---

### Exercise B8
Trace the pointer array changes:
```python
a = []
a.append(1)   # What happens to ob_item, ob_size, allocated?
a.append(2)   # What changes?
a.append(3)   # What changes?
a.append(4)   # What changes?
a.append(5)   # What happens now? (reallocation!)
```

---

### Exercise B9
Trace the operations in:
```python
a = [1, 2, 3]
a.insert(0, 0)
```
Show: resize check, pointer shift direction, incref of new element.

---

### Exercise B10
Trace what happens with circular references and GC:
```python
a = []
b = []
a.append(b)
b.append(a)
del a
del b
# What happens during GC collection?
```

---

## Section C: Calculate Capacities After Appends (10 Exercises)

### Exercise C1
Starting from `a = []`, calculate `ob_size` and `allocated` after each append:
```python
a.append(1)   # ob_size=?, allocated=?
a.append(2)   # ob_size=?, allocated=?
a.append(3)   # ob_size=?, allocated=?
a.append(4)   # ob_size=?, allocated=?
a.append(5)   # ob_size=?, allocated=?
```

**Answer**:
```
append(1): ob_size=1, allocated=4    (grew from 0→4)
append(2): ob_size=2, allocated=4    (space available)
append(3): ob_size=3, allocated=4    (space available)
append(4): ob_size=4, allocated=4    (space available, now full)
append(5): ob_size=5, allocated=8    (grew from 4→8)
```

---

### Exercise C2
Calculate how many reallocations occur when appending 50 items one-by-one from empty.

**Answer**: Growth pattern is 0→4→8→16→24→32→40→52.
Reallocations at sizes: 1, 5, 9, 17, 25, 33, 41 = **7 reallocations**
Final: ob_size=50, allocated=52.

---

### Exercise C3
If `a = list(range(100))`, what is `allocated`?

**Answer**: `list(range(100))` uses `__length_hint__` → pre-allocates exactly 100.
`ob_size=100, allocated=100` (no overallocation for pre-sized creation).

---

### Exercise C4
After `a = list(range(100))` followed by 5 appends, what is `allocated`?

**Answer**: 
- Start: ob_size=100, allocated=100 (full)
- append(1): need 101. new_allocated = (101 + 101/8 + 6) & ~3 = (101 + 12 + 6) & ~3 = 119 & ~3 = 116
- ob_size=101, allocated=116
- Next 4 appends fit in allocated=116.
- Final: ob_size=105, allocated=116

---

### Exercise C5
Starting with `a = [None] * 1000`, what are ob_size and allocated?

**Answer**: `[None] * 1000` allocates exactly: ob_size=1000, allocated=1000.

---

### Exercise C6
After creating `a = [None] * 1000` and then calling `a.append(x)`:

**Answer**:
- Start: ob_size=1000, allocated=1000 (full)
- new_allocated = (1001 + 1001/8 + 6) & ~3 = (1001 + 125 + 6) & ~3 = 1132 & ~3 = 1132
- Final: ob_size=1001, allocated=1132

---

### Exercise C7
If you pop 900 items from a 1000-element list (using `pop()`), will shrinking occur?

**Answer**:
- Start: allocated=1000 (or ~1000)
- After 500 pops: ob_size=500, allocated=1000. 500 >= 1000/2? YES (500 >= 500). No shrink.
- After 501 pops: ob_size=499, allocated=1000. 499 >= 500? NO. → SHRINK triggered.
- Shrinking begins at ~501 pops.
- After 900 pops: ob_size=100, has been shrunk multiple times.

---

### Exercise C8
Calculate the memory (bytes) used by the ob_item array for a list with allocated=52.

**Answer**: 52 × 8 bytes = 416 bytes. (Still within pymalloc's 512-byte limit.)

---

### Exercise C9
At what list size does ob_item exceed pymalloc's 512-byte limit?

**Answer**: 512 / 8 = 64. When allocated > 64, the array exceeds 512 bytes and switches to system malloc. This happens at the 65th element (the growth from 64 capacity to 76 triggers system malloc: 76×8=608 bytes).

---

### Exercise C10
Calculate total bytes of memory for `a = list(range(1000))`:
- PyListObject struct (with GC header)
- ob_item array
- Integer objects (which are cached vs not?)

**Answer**:
- PyListObject: ~56 bytes
- ob_item: 1000 × 8 = 8000 bytes
- Integers 0-256: already cached (257 objects, 0 additional bytes)
- Integers 257-999: 743 new PyLongObject × 28 bytes = 20,804 bytes
- **Total: ~28,860 bytes ≈ 28 KB**

---

## Section D: Predict Allocations (10 Exercises)

### Exercise D1
How many total bytes are allocated when you execute `a = [1, 2, 3]`?

**Answer**:
- PyListObject (from free list or pymalloc): ~56 bytes
- ob_item array (allocated=3, no overalloc for literal): 3×8 = 24 bytes
- int(1), int(2), int(3): cached (0 new bytes)
- **Total new allocation: ~80 bytes**

---

### Exercise D2
How many malloc calls occur for `a = [x**2 for x in range(10)]`?

**Answer**:
- 1 call for PyListObject struct (or from free list: 0)
- Multiple calls for ob_item as it grows: starts empty, grows through 4→8→16
  (3 realloc calls for the growth)
- 10 calls for new PyLongObject (for 0,1,4,9,16,25,36,49,64,81)
  Actually: 0,1,4,9,16,25,36,49,64,81 — 0,1,4,9,16,25 are cached. 
  New objects needed for: 36,49,64,81 = 4 new int objects
- **Approximate total: 1 (struct) + 3 (reallocs) + 4 (ints) = ~8 allocation operations**

---

### Exercise D3
What's the peak memory usage during `a = sorted([random list of 1000 items])`?

**Answer**:
- Original list: 56 + 1000×8 = 8,056 bytes
- sorted() creates new list: another 8,056 bytes
- TimSort auxiliary space: up to 500×8 = 4,000 bytes
- **Peak: ~20 KB** (both lists exist + sort temporary)

---

### Exercise D4
How many total allocations for `a = [[]] * 1000`?

**Answer**:
- 1 PyListObject for outer list
- 1 ob_item array (1000 slots = 8000 bytes)
- 1 PyListObject for the single inner `[]`
- 0 ob_item for inner (it's empty, ob_item=NULL)
- **Total: 3 allocations** (all 1000 slots point to same empty list!)

---

### Exercise D5
How many allocations for `a = [[] for _ in range(1000)]`?

**Answer**:
- 1 PyListObject for outer list
- Multiple ob_item reallocs for outer (grows dynamically): ~15 reallocs
- 1000 PyListObject for inner lists (from free list if available)
- 0 ob_item for each inner (empty, ob_item=NULL)
- **Total: ~1016 allocations** (much more than `[[]] * 1000`!)

---

### Exercise D6
Memory freed when you execute `del a` where `a = list(range(100))`:

**Answer**:
- Decrefs 100 integer objects (0-99 are cached, refcounts drop but objects persist)
- Frees ob_item array: 800 bytes returned
- PyListObject struct: goes to free list (not freed, cached)
- **Net freed: ~800 bytes** (the pointer array only)

---

### Exercise D7
What happens memory-wise during `a.extend(a)` for `a = [1,2,3]`?

**Answer**:
- CPython first gets the items to extend with (handles self-extension)
- list_resize: new size = 6, new_allocated = (6 + 0 + 6) & ~3 = 12 & ~3 = 12
- Realloc ob_item from current allocation to 12×8 = 96 bytes
- Copy 3 new pointers, incref each
- **New allocation: 96 bytes (or realloc of existing)**

---

### Exercise D8
How much memory does `sys.getsizeof([1,2,3])` report and why?

**Answer**:
- Reports: 88 bytes (typical CPython 3.10+)
- Breakdown: 56 (base PyListObject+GC) + 4×8 (allocated=4, overallocation!) = 56 + 32 = 88
- Wait — for a literal `[1,2,3]`, allocated=3, so 56 + 3×8 = 80. 
  Actually depends on version. Check: `sys.getsizeof([1,2,3])` → typically 80 or 88.

---

### Exercise D9
Memory difference between `tuple(range(100))` and `list(range(100))`?

**Answer**:
- Tuple: ~56 (header) + 100×8 (inline pointers) = 856 bytes. No overallocation.
- List: ~56 (header) + 100×8 (ob_item) = 856 bytes. allocated=ob_size=100.
- Nearly same! But tuple elements are inline (no separate array allocation).
  Tuple: ONE allocation of 856 bytes.
  List: TWO allocations (56 struct + 800 array).

---

### Exercise D10
How much memory is wasted (overallocation) after appending items 1 through 100 one by one?

**Answer**:
- Final ob_size=100
- Growth sequence includes: ...76→92→112
- At ob_size=100, allocated=112 (last growth from 92→112 at append 93)
- Wasted slots: 112 - 100 = 12 slots × 8 bytes = 96 bytes wasted
- Percentage: 12/112 ≈ 10.7% waste

---

## Section E: Explain Complexity (10 Exercises)

### Exercise E1
Explain why this code is O(n²) and how to fix it:
```python
def remove_all(lst, value):
    while value in lst:
        lst.remove(value)
```

**Answer**: `value in lst` is O(n). `lst.remove(value)` is O(n). While loop runs O(k) times where k = count of value. If k ∝ n, total is O(n²).

**Fix**: Build new list in O(n): `lst[:] = [x for x in lst if x != value]`

---

### Exercise E2
Explain the complexity of:
```python
for i in range(n):
    lst.insert(0, i)
```

**Answer**: Each `insert(0, i)` shifts all existing elements right → O(current_length). Total: 0+1+2+...+(n-1) = n(n-1)/2 = **O(n²)**.

**Fix**: `lst = list(range(n-1, -1, -1))` or append + reverse.

---

### Exercise E3
What's the complexity of:
```python
result = []
for chunk in data:  # k chunks, each of size m
    result = result + chunk
```

**Answer**: Each `result + chunk` creates a new list and copies all of result. Sizes grow: m, 2m, 3m, ..., km. Total copies: m(1+2+3+...+k) = O(k²m). **Quadratic!**

**Fix**: Use `result.extend(chunk)` → O(km) total.

---

### Exercise E4
Analyze the complexity of:
```python
def deduplicate(lst):
    seen = []
    result = []
    for item in lst:
        if item not in seen:
            seen.append(item)
            result.append(item)
    return result
```

**Answer**: `item not in seen` is O(len(seen)). In worst case (all unique), seen grows to n. Total comparisons: 1+2+3+...+n = **O(n²)**.

**Fix**: Use a set for seen: O(n) total.

---

### Exercise E5
What is the complexity of `sorted(lst, key=lambda x: x.count('a'))` where lst has n strings each of length m?

**Answer**: 
- Key computation: n calls to `.count('a')`, each O(m) → O(nm)
- Sort: O(n log n) comparisons of integers (pre-computed keys)
- **Total: O(nm + n log n)**

---

### Exercise E6
Explain why `collections.deque` is better than `list` for a FIFO queue:
```python
# Using list:
queue.append(x)   # O(1) amortized
queue.pop(0)      # O(n)!

# Using deque:
queue.append(x)   # O(1) amortized
queue.popleft()   # O(1)!
```

**Answer**: list.pop(0) must shift all n-1 elements left. deque uses a doubly-linked list of blocks — removing from the left just adjusts a pointer within the current block. No shifting.

---

### Exercise E7
What's the total time complexity of building a sorted list by insertion?
```python
import bisect
result = []
for item in data:  # n items
    bisect.insort(result, item)
```

**Answer**: `bisect.insort` = O(log n) search + O(n) insert (shifting). Per item: O(n). Total: O(n²). Same as insertion sort.

Despite O(log n) search, the insert is the bottleneck.

---

### Exercise E8
Analyze:
```python
a = list(range(n))
b = a[:n//2]
c = a[n//2:]
d = b + c
```

**Answer**:
- `a = list(range(n))`: O(n)
- `b = a[:n//2]`: O(n/2) copy
- `c = a[n//2:]`: O(n/2) copy
- `d = b + c`: O(n) copy
- **Total: O(n)**, but creates 4 list objects and allocates 4 arrays.
- **Peak memory**: ~4n pointers simultaneously alive.

---

### Exercise E9
Why is this O(n) and not O(1)?
```python
a = [1, 2, 3, ..., 1000000]
a.clear()
```

**Answer**: `clear()` must Py_DECREF each of the n elements to maintain correct reference counts. Each decref is O(1), but doing n of them is O(n). The actual memory free (ob_item) is O(1).

---

### Exercise E10
Analyze the complexity difference:
```python
# Version A:
for x in list_a:
    if x in list_b:  # O(m) per check
        process(x)
# Total: O(n * m)

# Version B:
set_b = set(list_b)  # O(m)
for x in list_a:
    if x in set_b:   # O(1) per check
        process(x)
# Total: O(n + m)
```

**Answer**: Version A does n linear scans of list_b → O(nm). Version B builds set once O(m) then does n O(1) lookups → O(n+m). For n=m=10000: A=100,000,000 ops, B=20,000 ops. **5000× faster**.
