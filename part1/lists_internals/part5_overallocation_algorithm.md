# Part 5 — Overallocation Algorithm

## 5.1 The Central Question

When a list is full and needs to grow, **how much extra space** should be allocated?

This is a fundamental computer science tradeoff:
- Grow too little → frequent reallocations → slow
- Grow too much → wasted memory → bloated

---

## 5.2 The CPython Formula

From `Objects/listobject.c`, the `list_resize` function:

```c
static int
list_resize(PyListObject *self, Py_ssize_t newsize)
{
    PyObject **items;
    size_t new_allocated, num_allocated_bytes;
    Py_ssize_t allocated = self->allocated;

    /* Bypass realloc() when a previous overallocation is large enough
       to accommodate the newsize.  If the newsize falls lower than half
       the allocated size, then proceed with the realloc() to shrink the list.
    */
    if (allocated >= newsize && newsize >= (allocated >> 1)) {
        assert(self->ob_item != NULL || newsize == 0);
        Py_SET_SIZE(self, newsize);
        return 0;
    }

    /* This over-allocates proportional to the list size, making room
     * for additional growth.  The over-allocation is mild, but is
     * enough to give linear-time amortized behavior over a long
     * sequence of appends() in the presence of a poorly-performing
     * system realloc().
     * Add padding to make the allocated size multiple of 4.
     * The growth pattern is:  0, 4, 8, 16, 24, 32, 40, 52, 64, 76, ...
     * Note: new_allocated won't overflow because the largest possible value
     *       is PY_SSIZE_T_MAX * (9 / 8) + 6 which always fits in a size_t.
     */
    new_allocated = ((size_t)newsize + (newsize >> 3) + 6) & ~(size_t)3;
    /* Do not overallocate if the new size is closer to overflowing. */
    if (newsize - Py_SIZE(self) > (Py_ssize_t)(new_allocated - newsize))
        new_allocated = ((size_t)newsize + 3) & ~(size_t)3;
    // ... rest of function: actual realloc ...
}
```

### The Formula Broken Down:

```
new_allocated = (newsize + (newsize >> 3) + 6) & ~3

Which means:
new_allocated = (newsize + newsize/8 + 6) rounded up to multiple of 4
              = newsize * (1 + 1/8) + 6, rounded to multiple of 4
              = newsize * 1.125 + 6, aligned to 4
```

---

## 5.3 Understanding Each Component

### Component 1: `newsize`
The minimum number of slots needed (usually `ob_size + 1` for append).

### Component 2: `newsize >> 3` (= newsize / 8)
Proportional growth of **12.5%**. This ensures growth rate is proportional to current size:
- Small lists grow by small amounts (avoiding waste)
- Large lists grow by large amounts (avoiding too-frequent resizing)

### Component 3: `+ 6`
A **constant padding** that helps small lists:
- Without it, a list of size 1 would grow by `1/8 = 0` extra slots
- The `+6` ensures small lists get meaningful overallocation
- Also ensures the growth pattern starts reasonably: 0 → 4 → 8 → 16...

### Component 4: `& ~3` (round to multiple of 4)
**Alignment optimization**:
- Rounds up to next multiple of 4
- `~3` in binary is `...11111100`
- ANDing with this clears the bottom 2 bits
- Ensures the allocated size is always divisible by 4
- Helps with memory allocator alignment (many allocators work in 4/8/16 byte blocks)

---

## 5.4 Growth Pattern (The Exact Sequence)

Starting from empty and appending one at a time:

```
newsize  | newsize + newsize>>3 + 6 | & ~3 | new_allocated
---------|---------------------------|------|---------------
   1     |    1 + 0 + 6 = 7         |  4   |   4
   5     |    5 + 0 + 6 = 11        |  8   |   8
   9     |    9 + 1 + 6 = 16        | 16   |  16
  17     |   17 + 2 + 6 = 25        | 24   |  24
  25     |   25 + 3 + 6 = 34        | 32   |  32
  33     |   33 + 4 + 6 = 43        | 40   |  40
  41     |   41 + 5 + 6 = 52        | 52   |  52
  53     |   53 + 6 + 6 = 65        | 64   |  64
  65     |   65 + 8 + 6 = 79        | 76   |  76
  77     |   77 + 9 + 6 = 92        | 92   |  92
```

The official comment states the pattern: **0, 4, 8, 16, 24, 32, 40, 52, 64, 76, ...**

Let's verify with actual Python:
```python
import sys

a = []
prev_size = sys.getsizeof(a)
allocations = []

for i in range(100):
    a.append(i)
    curr_size = sys.getsizeof(a)
    if curr_size != prev_size:
        # Size changed → reallocation happened
        allocated = (curr_size - 56) // 8  # 56 = base, 8 = ptr size
        allocations.append(allocated)
        prev_size = curr_size

print(allocations)
# Output: [4, 8, 16, 24, 32, 40, 52, 64, 76, 92, ...]
```

---

## 5.5 Growth Ratio Analysis

```
Transition    | Growth Factor
0  →  4       | ∞ (from nothing)
4  →  8       | 2.00×
8  → 16       | 2.00×
16 → 24       | 1.50×
24 → 32       | 1.33×
32 → 40       | 1.25×
40 → 52       | 1.30×
52 → 64       | 1.23×
64 → 76       | 1.19×
76 → 92       | 1.21×
```

For large lists, the growth factor converges to approximately **1.125** (12.5% growth).

---

## 5.6 Why 12.5% and Not 2× (Doubling)?

### The Classic Approach: Doubling

Many textbooks and implementations use 2× growth:
- Java's `ArrayList`: 1.5×
- C++ `std::vector` (GCC): 2×
- C++ `std::vector` (MSVC): 1.5×
- Go slices: 2× (small), ~1.25× (large)

### Why CPython is More Conservative:

**Memory usage**: With 2× growth, up to 50% of allocated memory can be wasted. With 1.125× growth, waste is at most ~12.5%.

**Python's usage patterns**: Python programs create MANY lists. The interpreter itself uses lists extensively. Conservative growth saves significant aggregate memory.

**realloc() can be efficient**: On many systems, `realloc()` can extend in place if adjacent memory is free. Frequent smaller growths may succeed in place more often than infrequent large growths.

**The +6 constant helps small lists**: For lists under ~50 elements, the constant addend provides more-than-12.5% growth, giving small lists the aggressive growth they need.

### Tradeoff:

```
Strategy     | Memory Waste | Resize Frequency | Amortized append
-------------|--------------|------------------|------------------
2× growth    | up to 50%    | rare             | O(1), small const
1.5× growth  | up to 33%    | moderate         | O(1), medium const
1.125×+6     | up to ~12.5% | more frequent    | O(1), larger const
```

All three are O(1) amortized. CPython chose memory efficiency at the cost of slightly more resize operations.

---

## 5.7 The Shrink Condition

From the same `list_resize` function:

```c
if (allocated >= newsize && newsize >= (allocated >> 1)) {
    // No realloc needed — newsize fits in current allocation
    // and isn't less than half (so not too wasteful)
    Py_SET_SIZE(self, newsize);
    return 0;
}
```

This means:
- If the new size fits within current allocation AND is at least half the allocated size → no realloc
- If new size < allocated/2 → shrink (realloc to smaller)

Example:
```
allocated = 100, ob_size = 90
Pop 10 items → newsize = 80
80 >= 100/2 = 50? YES → no shrink

Pop 30 more → newsize = 50
50 >= 100/2 = 50? YES (barely) → no shrink

Pop 1 more → newsize = 49
49 >= 100/2 = 50? NO → SHRINK!
new_allocated = (49 + 49/8 + 6) & ~3 = (49 + 6 + 6) & ~3 = 61 & ~3 = 60
```

---

## 5.8 Historical Changes

### Python 2.x era:
```c
// Older formula (Python 2.3-ish):
new_allocated = (newsize >> 3) + (newsize < 9 ? 3 : 6) + newsize;
```

### Python 3.x (current):
```c
new_allocated = ((size_t)newsize + (newsize >> 3) + 6) & ~(size_t)3;
```

Key differences:
- The alignment to multiples of 4 was added later
- The small-list special case (`< 9 ? 3 : 6`) was simplified to just `+6`
- The overflow protection was refined

The pattern has been remarkably stable. The fundamental idea (proportional growth + constant + alignment) has been the same since Python 2.3 (2003).

---

## 5.9 Mathematical Proof: Still Amortized O(1)

For growth factor α = 1.125:

After n appends, total resizes = log_{1.125}(n) ≈ 8.5 × ln(n)

Total copying work across all resizes:
```
Σ (size at resize i) = n + n/α + n/α² + n/α³ + ...
                     = n × (1/(1 - 1/α))
                     = n × (1/(1 - 1/1.125))
                     = n × (1/(0.111...))
                     = n × 9
                     = 9n
```

Total work for n appends: n (direct writes) + 9n (copying) = 10n = **O(n)**
Per append: **O(1)** amortized (with constant factor ~10).

Compare with doubling (α = 2):
Total copying: n × (1/(1 - 1/2)) = 2n
Per append: constant factor ~3.

CPython's constant is about 3× larger than doubling. This is the price of memory efficiency.

---

## 5.10 Memory Diagrams — Growth Over Time

```
Starting: a = []
────────────────────────────────────────────────────────
After a.append(0):                          allocated = 4
┌───┬───┬───┬───┐
│ 0 │   │   │   │  ob_size=1, wasted=3 slots (75% waste)
└───┴───┴───┴───┘

After a.append(1), a.append(2), a.append(3): allocated = 4
┌───┬───┬───┬───┐
│ 0 │ 1 │ 2 │ 3 │  ob_size=4, wasted=0 (0% waste, FULL)
└───┴───┴───┴───┘

After a.append(4):                          allocated = 8
┌───┬───┬───┬───┬───┬───┬───┬───┐
│ 0 │ 1 │ 2 │ 3 │ 4 │   │   │   │  ob_size=5, wasted=3 (37% waste)
└───┴───┴───┴───┴───┴───┴───┴───┘

... filling up to 8 ...

After reaching 8, next append:              allocated = 16
┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐
│ 0 │ 1 │...│ 7 │ 8 │   │   │   │   │   │   │   │   │   │   │   │
└───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘
ob_size=9, allocated=16, wasted=7 (44% waste)
```

---

## 5.11 Practical Implications

### 1. Pre-allocation for known sizes

```python
# BAD: triggers multiple reallocations
result = []
for i in range(10000):
    result.append(compute(i))

# BETTER: single allocation, then fill
result = [None] * 10000
for i in range(10000):
    result[i] = compute(i)

# BEST: list comprehension (CPython optimizes this)
result = [compute(i) for i in range(10000)]
```

### 2. Memory after deletion

```python
a = list(range(1000000))  # allocated ≈ 1000000
del a[100:]               # ob_size = 100, but allocated might still be ~1000000!

# Force shrink:
a = a[:]  # Creates new list with tight allocation
# Or:
a = list(a)
```

### 3. Predicting allocations

```python
# After appending 100 items one-by-one from empty:
# Reallocations occur at: 0→4, 4→8, 8→16, 16→24, 24→32, 32→40, 40→52, 52→64, 64→76, 76→92, 92→112
# That's 11 reallocations for 100 appends
# Final allocated = 112 (for 100 items → 12% waste)
```

---

## 5.12 Interview Questions — Part 5

**Q1**: What is the growth factor of CPython lists?
**A**: Approximately 1.125 (12.5%) for large lists, with a +6 constant that makes small lists grow more aggressively. The exact formula is `(newsize + newsize/8 + 6)` rounded to multiple of 4.

**Q2**: Why doesn't CPython double the list size like C++ vector?
**A**: Memory efficiency. Python programs create many lists. 2× growth wastes up to 50% memory. 1.125× growth wastes ~12.5%. The tradeoff is slightly more frequent reallocations, but still O(1) amortized.

**Q3**: What is the growth sequence for CPython lists?
**A**: 0, 4, 8, 16, 24, 32, 40, 52, 64, 76, 92, ...

**Q4**: When does CPython shrink a list's allocation?
**A**: When `newsize < allocated / 2`. If you remove many elements and the remaining count drops below half the allocated capacity, the next resize-triggering operation will reallocate to a smaller array.

**Q5**: How many reallocations occur when appending 1000 items one by one?
**A**: Approximately `log_{1.125}(1000) ≈ 58` reallocations. Each reallocation copies all existing pointers.

**Q6**: What does the `& ~3` do in the allocation formula?
**A**: Rounds up to the nearest multiple of 4. This aligns the allocation count with memory allocator boundaries, reducing fragmentation and improving cache behavior.
