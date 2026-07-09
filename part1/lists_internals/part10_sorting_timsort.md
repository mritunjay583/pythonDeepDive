# Part 10 — Sorting Internals (TimSort)

## 10.1 Overview

Python's `list.sort()` uses **TimSort**, an adaptive, stable, comparison-based sorting algorithm invented by Tim Peters in 2002 specifically for CPython. It has since been adopted by Java, Android, Swift, and Rust.

Key properties:
- **Stable**: equal elements maintain their original relative order
- **Adaptive**: exploits existing order in the data
- **Best case**: O(n) for nearly-sorted data
- **Worst case**: O(n log n)
- **Space**: O(n) auxiliary

---

## 10.2 The Core Idea

TimSort is a hybrid of **merge sort** and **insertion sort** that exploits "runs" — naturally occurring ordered subsequences in real-world data.

```
Input:  [3, 5, 7, 2, 1, 8, 9, 4, 6]

Step 1: Find natural runs:
        [3, 5, 7] [2→1→reversed to 1,2] [8, 9] [4, 6]
        Run 1↑     Run 2↑                Run 3↑  Run 4↑

Step 2: Extend short runs with binary insertion sort (to minimum run length)

Step 3: Merge runs intelligently using a merge stack
```

Real-world data almost always has existing order (logs are time-sorted, names are partially alphabetical, etc.). TimSort exploits this brilliantly.

---

## 10.3 Run Detection

A **run** is a maximal sequence that is either:
- **Ascending**: `a[i] <= a[i+1] <= a[i+2] <= ...`
- **Strictly descending**: `a[i] > a[i+1] > a[i+2] > ...` (reversed in place)

```python
# Example: finding runs in [5, 3, 1, 2, 4, 7, 9, 8, 6]
# 
# [5, 3, 1] → descending run → reverse to [1, 3, 5]
# [2, 4, 7, 9] → ascending run
# [8, 6] → descending run → reverse to [6, 8]
```

Why strictly descending (not `>=`)?
- To maintain **stability**. If we reversed a `>=` run, equal elements would swap positions.
- `[3a, 3b, 3c]` reversed is `[3c, 3b, 3a]` — stability violated!
- Strict `>` means no equal elements in descending runs, so reversal is safe.

---

## 10.4 Minimum Run Length (minrun)

Short runs are extended to a minimum length using **binary insertion sort**.

```c
// Compute minrun (between 32 and 64, from the input size)
static Py_ssize_t
merge_compute_minrun(Py_ssize_t n)
{
    Py_ssize_t r = 0;
    while (n >= 64) {
        r |= n & 1;
        n >>= 1;
    }
    return n + r;
}
```

The algorithm picks `minrun` so that `n/minrun` is a power of 2 (or close to it), which makes the final merge tree balanced.

For practical purposes: **minrun ≈ 32 to 64**.

Why this range?
- Below 32: too many tiny runs → too many merges
- Above 64: insertion sort becomes expensive
- 32-64: insertion sort is cache-friendly and fast for small arrays

---

## 10.5 Binary Insertion Sort (for small runs)

When a natural run is shorter than `minrun`, it's extended using binary insertion sort:

```
Natural run found: [3, 7, 9]  (length 3)
minrun = 32
Need to extend to 32 elements by inserting the next 29 elements in sorted order.

For each new element:
1. Binary search in the sorted portion to find insertion point → O(log k)
2. Shift elements right to make room → O(k)
3. Insert

Total for extending to minrun: O(minrun²) comparisons in worst case
But minrun is small (≤64), so this is effectively constant time.
```

Why binary insertion sort instead of plain insertion sort?
- Reduces comparisons from O(k) to O(log k) per insertion
- Comparisons in Python are expensive (may call `__lt__`, `__eq__`)
- The shifts (memmove of pointers) are cheap (just moving 8-byte values)

---

## 10.6 The Merge Stack

After identifying runs, TimSort uses a **stack-based merge strategy**:

```
Stack of pending runs: maintains invariants that control merge order.

Invariant (for runs A, B, C on stack):
1. |A| > |B| + |C|
2. |B| > |C|

Where |X| is the length of run X.

If violated → merge adjacent runs to restore invariant.
```

Example:
```
Stack:  [Run1: 40 elements] [Run2: 30 elements] [Run3: 35 elements]

Check: |Run1| > |Run2| + |Run3|?  40 > 30 + 35?  40 > 65?  NO!
→ Merge Run2 with the smaller neighbor

After merge: [Run1: 40] [Merged: 65]
Check: |Run1| > |Merged|?  40 > 65?  NO!
→ Merge them

Final: [Single sorted run: 105 elements]
```

This strategy ensures:
- The number of pending runs is O(log n)
- Merges happen between roughly equal-sized runs (balanced merge tree)
- Total merge work is O(n log n)

---

## 10.7 The Merge Operation

Merging two sorted runs:

```
Run A: [1, 3, 5, 7, 9]
Run B: [2, 4, 6, 8, 10]

Merge → [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
```

CPython allocates a **temporary buffer** for the shorter run:
```
If |A| ≤ |B|:
    Copy A to temp buffer
    Merge from temp + B into original array (left to right)

If |A| > |B|:
    Copy B to temp buffer
    Merge from A + temp into original array (right to left)
```

This ensures auxiliary space = min(|A|, |B|) rather than |A| + |B|.

---

## 10.8 Galloping Mode

When one run is "winning" consistently (its elements are always smaller/larger), TimSort switches to **galloping mode** (exponential search):

```
Normal merge: compare one element at a time
    A: [1, 2, 3, 4, 5, 100, 101, ...]
    B: [50, 60, 70, ...]
    
    Compare 1<50? yes, take from A
    Compare 2<50? yes, take from A  
    Compare 3<50? yes, take from A  ← A keeps winning
    Compare 4<50? yes, take from A  ← switch to galloping!

Galloping: exponential search in the winning run
    Check A[1], A[2], A[4], A[8], A[16]... to find where B[0] fits
    → Find that A[0..4] are all < B[0]
    → Copy A[0..4] in bulk (memcpy) instead of element-by-element
```

Galloping kicks in after `MIN_GALLOP` (initially 7) consecutive wins by one side.

Benefits:
- When data has large already-sorted segments, galloping copies them in bulk
- Goes from O(n) comparisons to O(log n) for a block
- Particularly effective for data that is "almost sorted" or has concatenated sorted sequences

---

## 10.9 Stability

TimSort is **stable**: elements that compare equal maintain their original order.

```python
data = [(1, 'b'), (2, 'a'), (1, 'a'), (2, 'b')]
data.sort(key=lambda x: x[0])
# Result: [(1, 'b'), (1, 'a'), (2, 'a'), (2, 'b')]
#          ↑ original order preserved for equal keys
```

Stability is guaranteed because:
1. The comparison uses `<` (strict), not `<=`
2. Descending runs use strict `>` before reversing
3. Merge is stable (equal elements from left run come first)
4. Insertion sort is stable

This is a **language guarantee** (documented behavior), not just an implementation detail.

---

## 10.10 Mutation Detection

During sort, the list must not be modified by comparisons:

```c
// Before sort:
saved_ob_size = Py_SIZE(self);
self->allocated = -1;  // Sentinel!
self->ob_item = NULL;  // Hide the array

// ... perform sort on a separate copy ...

// After sort:
self->ob_item = sorted_items;
self->allocated = saved_ob_size;
```

If any comparison function tries to modify the list:
```python
class Evil:
    def __lt__(self, other):
        the_list.append(42)  # Tries to mutate during sort!
        return True

# Raises: ValueError: list modified during sort
```

The `allocated = -1` trick causes `list_resize` to detect the modification attempt.

---

## 10.11 Complexity Analysis

### Best Case: O(n)
- Input: already sorted (one natural run of length n)
- TimSort detects the single run in O(n) scan
- No merges needed
- Total: O(n)

### Nearly Sorted: O(n)
- Input: sorted except for a few out-of-place elements
- TimSort finds large runs, small disruptions handled by insertion sort
- Very few merges needed
- Effectively linear

### Average Case: O(n log n)
- Random data: runs are typically short (minrun length)
- ~n/minrun runs → ~log₂(n/minrun) merge passes
- Each pass touches all n elements
- Total: O(n log n)

### Worst Case: O(n log n)
- Guaranteed by the merge sort component
- Unlike quicksort, no O(n²) worst case
- The merge stack invariant ensures balanced merges

### Space: O(n)
- Temporary buffer for merges: up to n/2 elements
- Stack of pending runs: O(log n) entries
- Total auxiliary: O(n)

---

## 10.12 TimSort vs Other Algorithms

| Algorithm | Best | Average | Worst | Space | Stable | Adaptive |
|-----------|------|---------|-------|-------|--------|----------|
| TimSort | O(n) | O(n log n) | O(n log n) | O(n) | Yes | Yes |
| Quicksort | O(n log n) | O(n log n) | O(n²) | O(log n) | No* | No |
| Merge Sort | O(n log n) | O(n log n) | O(n log n) | O(n) | Yes | No |
| Heapsort | O(n log n) | O(n log n) | O(n log n) | O(1) | No | No |
| Insertion Sort | O(n) | O(n²) | O(n²) | O(1) | Yes | Yes |

TimSort combines the best properties: stable, adaptive, and never worse than O(n log n).

---

## 10.13 CPython Implementation Details

Source: `Objects/listobject.c` (sort section) and `Objects/listsort.txt` (Tim Peters' detailed description)

Key functions:
- `list_sort_impl()` — entry point
- `merge_compute_minrun()` — calculate minimum run length
- `count_run()` — find natural ascending/descending runs
- `binarysort()` — extend short runs via binary insertion sort
- `merge_lo()` / `merge_hi()` — merge two adjacent runs
- `gallop_left()` / `gallop_right()` — exponential search in galloping mode
- `merge_collapse()` — maintain stack invariant, trigger merges

---

## 10.14 The key= Parameter

```python
data.sort(key=str.lower)
```

CPython pre-computes all keys before sorting:

```c
// Simplified logic:
PyObject **keys = PyMem_Malloc(n * sizeof(PyObject*));
for (i = 0; i < n; i++)
    keys[i] = PyObject_CallOneArg(keyfunc, items[i]);

// Sort using keys for comparison, but move original items
// This is the "decorate-sort-undecorate" pattern (Schwartzian transform)
```

Benefits:
- Key function called exactly n times (not O(n log n) times)
- Stable sort preserves original order for equal keys
- More efficient than calling key during every comparison

---

## 10.15 Interview Questions — Part 10

**Q1**: What sorting algorithm does Python use?
**A**: TimSort — a hybrid merge sort + insertion sort designed by Tim Peters. It's adaptive (exploits existing order), stable, and O(n log n) worst case.

**Q2**: What is the best-case complexity of `list.sort()`?
**A**: O(n) for already-sorted or nearly-sorted data. TimSort detects natural runs and avoids unnecessary work.

**Q3**: Is Python's sort stable? What does that mean?
**A**: Yes, it's stable. Equal elements maintain their original relative order. This is guaranteed by the language specification.

**Q4**: What is a "run" in TimSort?
**A**: A maximal naturally ordered subsequence — either ascending (non-decreasing) or strictly descending (which gets reversed). TimSort builds on these existing ordered segments.

**Q5**: Why does sort() temporarily set allocated to -1?
**A**: To detect modifications during sorting. If any comparison function tries to mutate the list, the resize check sees allocated=-1 and raises ValueError.

**Q6**: What is galloping mode?
**A**: An optimization where, during merge, if one run consistently provides smaller elements, TimSort switches to exponential search to find the merge point in bulk. This turns O(n) comparisons into O(log n) for runs that are "interleaved at large scales."

**Q7**: How much extra memory does sort() use?
**A**: O(n) — specifically up to n/2 elements of temporary buffer for the merge operation. The merge always copies the shorter of the two runs being merged.
