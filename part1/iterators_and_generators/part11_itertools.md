# Part 11 — itertools Deep Dive

## 11.1 Why itertools Exists

itertools provides **memory-efficient**, **C-implemented** iterator building blocks. Each function:
- Returns a lazy iterator (O(1) memory)
- Is implemented in C (Modules/itertoolsmodule.c) — much faster than Python equivalents
- Composes with other itertools and generators

## 11.2 Infinite Iterators

### `itertools.count(start=0, step=1)`
```python
# Infinite counter: 0, 1, 2, 3, ...
# Like range() but infinite and supports float step
from itertools import count
for i in count(10, 0.5):  # 10.0, 10.5, 11.0, 11.5, ...
    if i > 12: break

# C struct: just stores (current, step) — 2 numbers, O(1)!
```

### `itertools.cycle(iterable)`
```python
# Repeats iterable forever: [1,2,3,1,2,3,1,2,3,...]
# WARNING: saves a copy of the iterable internally! O(n) memory!
from itertools import cycle
colors = cycle(["red", "green", "blue"])
[next(colors) for _ in range(7)]  # red,green,blue,red,green,blue,red
```

### `itertools.repeat(object, times=None)`
```python
# Yields object repeatedly (infinite if times=None)
from itertools import repeat
list(repeat(42, 5))  # [42, 42, 42, 42, 42]
# Used with map: list(map(pow, range(10), repeat(2))) → [0,1,4,9,16,...]
```

## 11.3 Terminating Iterators

### `itertools.chain(*iterables)` / `chain.from_iterable()`
```python
# Concatenate multiple iterables lazily:
from itertools import chain
list(chain([1,2], [3,4], [5,6]))  # [1,2,3,4,5,6]

# For iterable-of-iterables:
data = [[1,2], [3,4], [5,6]]
list(chain.from_iterable(data))  # [1,2,3,4,5,6]
# Flattens one level, lazily!
```

### `itertools.islice(iterable, stop)` / `islice(it, start, stop, step)`
```python
# Lazy slicing (works on any iterator, not just sequences!):
from itertools import islice
gen = (x**2 for x in count())  # Infinite!
list(islice(gen, 5))           # [0, 1, 4, 9, 16] — takes first 5
list(islice(gen, 3))           # [25, 36, 49] — continues from where left off!
```

### `itertools.tee(iterable, n=2)`
```python
# Create n independent iterators from one source:
from itertools import tee
a, b = tee(range(5))
list(a)  # [0,1,2,3,4]
list(b)  # [0,1,2,3,4] — independent!

# WARNING: tee BUFFERS values that one copy has consumed but others haven't!
# If one copy advances far ahead: O(n) memory! Can be a trap for large data.
```

### `itertools.groupby(iterable, key=None)`
```python
# Groups consecutive elements with same key:
from itertools import groupby
data = [("a",1),("a",2),("b",3),("b",4),("a",5)]
for key, group in groupby(data, lambda x: x[0]):
    print(key, list(group))
# a [(a,1),(a,2)]
# b [(b,3),(b,4)]
# a [(a,5)]       ← separate group! Only groups CONSECUTIVE matches!
```

### `itertools.accumulate(iterable, func=operator.add, initial=None)`
```python
# Running accumulation (like reduce but yields intermediate results):
from itertools import accumulate
import operator
list(accumulate([1,2,3,4,5]))  # [1,3,6,10,15] — running sum
list(accumulate([1,2,3,4,5], operator.mul))  # [1,2,6,24,120] — running product
```

## 11.4 Combinatorial Iterators

```python
from itertools import product, permutations, combinations, combinations_with_replacement

list(product([1,2], [3,4]))          # [(1,3),(1,4),(2,3),(2,4)]
list(permutations([1,2,3], 2))       # All 2-length arrangements
list(combinations([1,2,3,4], 2))     # All 2-element subsets
list(combinations_with_replacement([1,2,3], 2))  # With repetition
```

## 11.5 Filtering Iterators

```python
from itertools import compress, filterfalse, dropwhile, takewhile

list(compress("ABCDEF", [1,0,1,0,1,1]))  # A,C,E,F (select by mask)
list(filterfalse(lambda x: x%2, range(10)))  # [0,2,4,6,8] (keep where pred=False)
list(dropwhile(lambda x: x<5, [1,3,6,2,8]))  # [6,2,8] (drop leading matches)
list(takewhile(lambda x: x<5, [1,3,6,2,8]))  # [1,3] (take leading matches)
```

## 11.6 Implementation: All in C

Every itertools function is implemented in C (`Modules/itertoolsmodule.c`). Example structure for `islice`:
```c
typedef struct {
    PyObject_HEAD
    PyObject *it;           // Source iterator
    Py_ssize_t next;        // Next index to yield
    Py_ssize_t stop;        // Stop index
    Py_ssize_t step;        // Step size
    Py_ssize_t cnt;         // Current count
} isliceobject;
```

~30-50 bytes per itertools object. All lazy. All C-speed.

## 11.7 Interview Questions — Part 11

**Q1**: Why is `itertools.chain` better than concatenating lists? **A**: O(1) memory (no intermediate list). Lazily yields from each iterable in sequence.

**Q2**: What's the memory trap with `itertools.tee`? **A**: tee buffers consumed-but-not-yet-read values. If one copy advances far ahead of others, all skipped values are buffered in memory. Can grow to O(n).

**Q3**: Why must input to `groupby` be sorted by key? **A**: groupby only groups CONSECUTIVE elements with the same key. If equal keys aren't adjacent, they form separate groups. Sort first for complete grouping.

**Q4**: Are itertools functions implemented in Python or C? **A**: C (Modules/itertoolsmodule.c). This makes them significantly faster than equivalent Python generators.
