# Part 12 — Production Topics

## 12.1 Large Lists: Memory Implications

### How Big Can a List Get?

Theoretical maximum: `sys.maxsize` elements (2^63 - 1 on 64-bit).
Practical maximum: limited by available RAM.

```python
import sys
print(sys.maxsize)  # 9223372036854775807 (64-bit)

# Memory for pointer array alone:
# 1 million items: 8 MB (just pointers)
# 10 million items: 80 MB
# 100 million items: 800 MB
# 1 billion items: 8 GB (just the pointer array!)
```

### Memory Breakdown for Large Lists

```python
# List of 1,000,000 integers (values 0-999999):
# 
# Pointer array:  1,000,000 × 8 = 8,000,000 bytes (~8 MB)
# PyListObject:   56 bytes
# Integer objects: 
#   - Cached [-5, 256]: 262 objects, already exist (free)
#   - New [257, 999999]: 999,743 × 28 bytes = ~28 MB
#
# Total: ~36 MB for 1 million integers
# Compare: C int array = 4 MB, NumPy int64 = 8 MB
```

---

## 12.2 Memory Fragmentation

### The Problem

Lists cause fragmentation through their lifecycle:

```
Time 0: Create list, allocate ob_item (32 bytes in pool)
Time 1: Grow list, realloc ob_item (32 → 64 bytes)
        Old 32-byte slot is freed → hole in 32-byte pool
Time 2: Grow again (64 → 128 bytes)
        Old 64-byte slot freed → hole in 64-byte pool
Time 3: Grow again (128 → 256 bytes)
        ...

Result: pools of small sizes have many free slots that can't be
        coalesced into larger blocks
```

### pymalloc's Mitigation

pymalloc uses size-class pools which partially mitigate this:
- Freed 32-byte slots can be reused by OTHER 32-byte allocations
- But can't be combined for larger allocations
- Arenas (256 KB) are only freed when completely empty

### When Fragmentation Matters

```python
# Pattern that causes fragmentation:
lists = []
for _ in range(100000):
    temp = list(range(100))  # Creates list, allocates array
    lists.append(temp[0])     # Keep one element
    # temp is freed, but its pool slots remain fragmented

# After this: many small holes in pymalloc pools
# Memory usage higher than expected
```

### Detection

```python
import tracemalloc
tracemalloc.start()

# ... your code ...

snapshot = tracemalloc.take_snapshot()
stats = snapshot.statistics('lineno')
for stat in stats[:10]:
    print(stat)
```

---

## 12.3 Cache Locality

### The L1/L2/L3 Cache Problem

Modern CPUs have caches:
```
Register:    ~1 ns access
L1 Cache:    ~1 ns  (32-64 KB)
L2 Cache:    ~4 ns  (256 KB - 1 MB)
L3 Cache:    ~10 ns (4-32 MB)
Main RAM:    ~100 ns
```

Python list iteration involves:
```
for x in my_list:    # What happens per iteration:
    process(x)

1. Load ob_item[i] from pointer array → likely L1/L2 cache hit (sequential)
2. Dereference pointer to get actual object → LIKELY CACHE MISS! (random heap)
3. Load object data → another potential cache miss
```

```
Pointer array (contiguous, cache-friendly):
┌─────┬─────┬─────┬─────┬─────┐
│ ptr │ ptr │ ptr │ ptr │ ptr │ → sequential access, prefetcher works
└──┬──┴──┬──┴──┬──┴──┬──┴──┬──┘

But dereferencing those pointers:
   │     │     │     │     │
   ▼     ▼     ▼     ▼     ▼
 0x1000 0x5000 0x2800 0x9100 0x3400  → random addresses, cache misses!
```

### NumPy Advantage

```python
import numpy as np

# NumPy: contiguous data, cache-friendly
arr = np.array([1, 2, 3, 4, 5], dtype=np.int64)
# Memory: [1][2][3][4][5] — all adjacent, prefetcher happy

# Python list: pointer indirection, cache-hostile
lst = [1, 2, 3, 4, 5]
# Memory: [ptr][ptr][ptr][ptr][ptr] → scattered int objects
```

For numerical operations, NumPy is 10-100× faster due to:
1. No pointer indirection
2. Contiguous memory (cache prefetcher works)
3. SIMD vectorization possible
4. No reference counting overhead per element

---

## 12.4 Performance Tuning

### 1. Pre-allocate When Size is Known

```python
# SLOW: repeated growth
result = []
for i in range(n):
    result.append(compute(i))
# ~15 reallocations for n=1000

# FASTER: pre-allocate
result = [None] * n
for i in range(n):
    result[i] = compute(i)
# 0 reallocations

# FASTEST: comprehension (less bytecode overhead)
result = [compute(i) for i in range(n)]
```

### 2. Use extend() Instead of Repeated append()

```python
# SLOW: n individual appends
for chunk in chunks:
    for item in chunk:
        result.append(item)

# FAST: bulk extend
for chunk in chunks:
    result.extend(chunk)

# FASTEST: chain + list
from itertools import chain
result = list(chain.from_iterable(chunks))
```

### 3. Avoid Unnecessary Copies

```python
# BAD: creates temporary lists
result = a + b + c + d  # Creates 3 temporary lists!

# GOOD: extend into one
result = []
result.extend(a)
result.extend(b)
result.extend(c)
result.extend(d)

# ALSO GOOD:
from itertools import chain
result = list(chain(a, b, c, d))
```

### 4. Use Generators for Pipeline Processing

```python
# BAD: materializes every intermediate step
data = load_data()                  # huge list
filtered = [x for x in data if valid(x)]    # another huge list
transformed = [process(x) for x in filtered] # yet another
final = [format(x) for x in transformed]     # and another

# GOOD: lazy pipeline, O(1) intermediate memory
data = load_data()
pipeline = (format(process(x)) for x in data if valid(x))
final = list(pipeline)  # or iterate directly
```

### 5. Choose the Right Container

```python
# Looking up items? Use a set
if item in my_list:      # O(n)
if item in my_set:       # O(1)

# FIFO queue? Use deque
my_list.pop(0)           # O(n)
my_deque.popleft()       # O(1)

# Sorted and need bisect?
import bisect
bisect.insort(sorted_list, item)  # O(n) insert but O(log n) search

# Counting? Use Counter
from collections import Counter
counts = Counter(my_list)  # O(n) once, then O(1) lookups
```

---

## 12.5 Avoiding Unnecessary Copies

### The Cost of Copying

```python
# Each creates a NEW list (O(n) allocation + O(n) pointer copies):
b = a[:]        # full slice copy
b = a.copy()    # explicit copy
b = list(a)     # constructor copy
b = a + []      # concatenation copy (don't do this!)
b = sorted(a)   # sort returns new list

# These do NOT copy (O(1)):
b = a           # assignment (alias)
a.sort()        # in-place sort
a.reverse()     # in-place reverse
a.clear()       # in-place clear
```

### Pattern: Return vs Modify

```python
# Function that builds a result: return new list (caller owns it)
def get_filtered(data):
    return [x for x in data if x > 0]

# Function that transforms in place: modify the argument
def normalize_inplace(data):
    max_val = max(data)
    for i in range(len(data)):
        data[i] /= max_val
    # No return (or return None)
```

---

## 12.6 Memory Profiling

### sys.getsizeof — Shallow Only

```python
import sys

a = [[1,2,3] for _ in range(1000)]
print(sys.getsizeof(a))  # ~8056 bytes (list + pointer array)
# Does NOT include the 1000 inner lists or their contents!
```

### pympler — Deep/Recursive Size

```python
from pympler import asizeof

a = [[1,2,3] for _ in range(1000)]
print(asizeof.asizeof(a))  # ~152,000 bytes (includes everything!)
```

### tracemalloc — Track Allocations

```python
import tracemalloc

tracemalloc.start()

# Your code here
big_list = [i**2 for i in range(100000)]

current, peak = tracemalloc.get_traced_memory()
print(f"Current: {current / 1024:.1f} KB")
print(f"Peak:    {peak / 1024:.1f} KB")

tracemalloc.stop()
```

### memory_profiler — Line-by-Line

```python
# pip install memory-profiler
from memory_profiler import profile

@profile
def build_data():
    a = list(range(1000000))    # shows memory per line
    b = a[:]                     # shows the copy cost
    del a                        # shows memory freed
    return b
```

---

## 12.7 Common Production Anti-Patterns

### Anti-Pattern 1: Infinite Growth

```python
# Memory leak: list grows forever
event_log = []

def handle_event(event):
    event_log.append(event)  # Never cleaned up!
    process(event)

# Fix: bounded buffer
from collections import deque
event_log = deque(maxlen=10000)  # Auto-discards oldest
```

### Anti-Pattern 2: Accidental Quadratic

```python
# O(n²): repeated membership test on list
def find_unique(data):
    result = []
    for item in data:
        if item not in result:  # O(n) lookup each time!
            result.append(item)
    return result
# Total: O(n²)

# Fix: O(n) with set
def find_unique(data):
    seen = set()
    result = []
    for item in data:
        if item not in seen:  # O(1) lookup
            seen.add(item)
            result.append(item)
    return result
```

### Anti-Pattern 3: Building Strings with List

```python
# Common but often unnecessary:
parts = []
for item in data:
    parts.append(str(item))
result = ', '.join(parts)

# Better (when data is small): generator directly
result = ', '.join(str(item) for item in data)
```

### Anti-Pattern 4: Large Temporary Lists

```python
# BAD: materializes huge intermediate list
total = sum([x**2 for x in range(10000000)])  # 80MB+ temporary list!

# GOOD: generator, O(1) memory
total = sum(x**2 for x in range(10000000))
```

---

## 12.8 Lists in Multiprocessing

### The GIL and Lists

The GIL protects against race conditions on CPython objects, but doesn't prevent logical races:

```python
import threading

shared_list = [0] * 10

def worker(index):
    for _ in range(1000):
        shared_list[index] += 1  # "safe" due to GIL... mostly
        # But +=1 is not atomic! (load + increment + store)

# For shared mutable state, use proper synchronization:
import queue
q = queue.Queue()  # Thread-safe
```

### Sharing Lists Between Processes

```python
from multiprocessing import Process, Manager

# Manager provides shared lists (proxy objects, slow):
manager = Manager()
shared = manager.list([1, 2, 3])

# For large data, prefer:
# - multiprocessing.Array (shared memory, typed)
# - multiprocessing.shared_memory (Python 3.8+)
# - Files / databases
```

---

## 12.9 Interview Questions — Part 12

**Q1**: How much memory does a list of 1 million integers use?
**A**: ~36 MB. Pointer array (8 MB) + integer objects for values > 256 (~28 MB) + list overhead (56 bytes). Compare to NumPy int64 array: ~8 MB.

**Q2**: Why is iterating a Python list slower than iterating a NumPy array?
**A**: Python lists require pointer indirection for each element (random memory access, cache misses). NumPy stores values contiguously, enabling sequential access, cache prefetching, and SIMD vectorization.

**Q3**: How can you detect memory issues with lists?
**A**: Use `tracemalloc` for allocation tracking, `pympler.asizeof` for deep size measurement, `memory_profiler` for line-by-line memory usage, and `sys.getsizeof` for shallow size.

**Q4**: What causes "accidental quadratic" with lists?
**A**: Using `item in my_list` inside a loop. The `in` operator is O(n) for lists, so n lookups in a list of size n = O(n²). Fix: convert to a set for O(1) lookups.

**Q5**: When should you NOT use a list?
**A**: When you need O(1) membership testing (use set), O(1) popleft (use deque), key-value mapping (use dict), numerical computation (use numpy), or fixed data that won't change (use tuple).
