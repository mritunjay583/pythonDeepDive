# Part 15 — Performance: Overhead, Cache Locality, and Optimization

## 15.1 Memory Overhead Per Object

Every Python object carries a "tax" — metadata bytes that don't exist in lower-level languages:

```
Minimum overhead per object (64-bit):
┌──────────────────────────────────────────────────────┐
│ Component              Size      Cumulative            │
├──────────────────────────────────────────────────────┤
│ ob_refcnt              8 bytes   8 bytes               │
│ ob_type                8 bytes   16 bytes              │
│ ob_size (if variable)  8 bytes   24 bytes              │
│ GC header (if tracked) 16 bytes  32-40 bytes           │
└──────────────────────────────────────────────────────┘

Comparison with C:
  C int:          4 bytes
  Python int(42): 28 bytes (7× overhead!)
  
  C double:           8 bytes
  Python float(3.14): 24 bytes (3× overhead)
  
  C char[5]:          5 bytes
  Python "hello":     54 bytes (10× overhead!)
  
  C struct {int; int}: 8 bytes
  Python (1, 2):       56 bytes (7× overhead)
```

### Real-World Memory Comparison

```python
# Storing 1 million integers:

# Python list of ints:
#   List struct:     56 bytes
#   Pointer array:   8,000,000 bytes (1M × 8)
#   Int objects:     28,000,000 bytes (1M × 28) [if not cached]
#   Total:          ~36 MB

# C array of int:
#   int array[1000000]:  4,000,000 bytes
#   Total:              4 MB

# NumPy array (Python + C hybrid):
#   Array object:   ~112 bytes
#   Raw data:       8,000,000 bytes (1M × 8 for int64)
#   Total:          ~8 MB

# Factor: Python list is ~9× more memory than NumPy, ~9× more than C
```

---

## 15.2 Object Size Summary

| Object | Size (bytes) | Breakdown |
|--------|-------------|-----------|
| `None` | 16 | Header only |
| `True` | 28 | Header + 1 digit |
| `int(0)` | 24 | Header + ob_size (no digits) |
| `int(42)` | 28 | Header + 1 digit |
| `int(2^30)` | 32 | Header + 2 digits |
| `float(3.14)` | 24 | Header + double |
| `complex(1,2)` | 32 | Header + 2 doubles |
| `""` (empty str) | 49 | Header + string metadata |
| `"hello"` | 54 | 49 + 5 chars |
| `()` (empty tuple) | 40 | Header (reported by getsizeof) |
| `(1, 2, 3)` | 64 | Header + 3 pointers |
| `[]` (empty list) | 56 | Struct (with GC overhead in getsizeof) |
| `[1, 2, 3]` | 88 | Struct + pointer array (with overalloc) |
| `{}` (empty dict) | 64 | Struct only |
| `{"a": 1}` | 184 | Struct + keys table |
| `set()` | 216 | Struct + inline table |
| `object()` | 16 | Header only |
| `lambda: 0` | 136 | Function struct |

---

## 15.3 Cache Locality

### What Makes Good Cache Behavior

```
GOOD: Objects accessed together are near each other in memory
  → One cache line load brings multiple useful objects

BAD: Objects accessed together are scattered across memory  
  → Each access causes a cache miss (100+ cycle penalty)
```

### Python's Cache Challenges

Python objects are heap-allocated at arbitrary addresses. A list of objects:

```
list.ob_item → [ptr0, ptr1, ptr2, ptr3, ...]
                 │      │      │      │
                 ▼      ▼      ▼      ▼
             obj at  obj at  obj at  obj at
             0xA000  0xF800  0x3200  0xC400
             (scattered across heap!)
```

Iterating this list causes **pointer chasing** — each element access may be a cache miss:

```
for item in my_list:     # Access pattern:
    process(item)        # 1. Load pointer from array (likely cached)
                         # 2. Follow pointer to object (likely CACHE MISS!)
                         # 3. Access object data (may need another cache line)
```

### Tuple vs List Cache Behavior

```
Tuple (data inline):
┌────────────────────────────────────┐
│ header │ ptr0 │ ptr1 │ ptr2 │ ptr3 │  ← One or two cache lines
└────────────────────────────────────┘
The pointers themselves are contiguous (good for prefetching).
But the POINTED-TO objects are still scattered.

List (data via indirection):
┌─────────────────────────┐          ┌──────────────────────────────┐
│ header │ ob_item ptr ───┼────→     │ ptr0 │ ptr1 │ ptr2 │ ptr3   │
└─────────────────────────┘          └──────────────────────────────┘
Extra indirection (one more cache miss to reach the pointer array).
```

---

## 15.4 Allocation Cost

### PyMalloc Fast Path

Typical allocation from a pool with free blocks:
```c
// ~5-10 nanoseconds:
block = pool->freeblock;                    // Load pointer
pool->freeblock = *(block **)block;         // Update free list
return block;                               // Done!
```

Compare with system malloc:
```c
// ~20-100 nanoseconds:
// Check thread cache → check central cache → check page heap → mmap
```

### Allocation Frequency

A typical Python program creates and destroys millions of objects per second:
```python
# This simple loop:
for i in range(1_000_000):
    s = f"item_{i}"     # 1M string allocations + int to string conversions
    items.append(s)     # 1M INCREF operations

# CPython does approximately:
#   1M PyUnicode_FromFormat calls → 1M allocations
#   1M+ Py_INCREF calls
#   1M+ temporary int creations (for format)
#   1M list_append calls (with occasional realloc)
```

---

## 15.5 Reference Counting Overhead

### Per-Operation Cost

Every pointer assignment involves refcount updates:
```c
// Conceptually, for "y = x":
Py_INCREF(x);        // Memory write: x->ob_refcnt++
Py_XDECREF(old_y);   // Memory write: old_y->ob_refcnt--
                      // Potential deallocation check

// 2 memory writes minimum per assignment
// In a tight loop, this adds ~2-4 nanoseconds per iteration
```

### Where Refcounting Time Goes

Profiling CPython shows significant time in refcount operations:
```
Typical breakdown of CPython interpreter time:
  ~10-15%  Bytecode dispatch (instruction fetch/decode)
  ~15-20%  Object allocation and deallocation
  ~10-15%  Py_INCREF/Py_DECREF operations
  ~5-10%   Type dispatch (reading ob_type, function pointers)
  ~40-60%  Actual computation (type-specific operations)
```

### Memory Bus Pressure

Each Py_INCREF/Py_DECREF:
1. Loads the cache line containing ob_refcnt (if not cached)
2. Modifies ob_refcnt (marks cache line dirty)
3. Eventually writes back to L2/L3/RAM

For frequently-referenced objects (None, True, small integers), this creates write pressure. Immortal objects (3.12+) eliminate this for the most common cases.

---

## 15.6 Small Object Optimization

### Integer Caching

```python
# Integers [-5, 256] are pre-allocated singletons:
a = 42
b = 42
a is b  # True — same object, no allocation needed!

# Saves: 28 bytes per reference to these common values
# Saves: allocation/deallocation time
```

### String Interning

```python
# Identifier-like strings are interned:
a = "hello"
b = "hello"
a is b  # True — interned, shared object

# Saves: string duplication memory
# Enables: O(1) string comparison for dict keys (pointer compare)
```

### Float Free List

```python
# When a float is freed, its memory goes to a free list:
x = 3.14  # Allocate (or take from free list)
del x      # Return to free list (not to pymalloc)
y = 2.71  # Take from free list — instant!
```

### Tuple Free List

```python
# Empty tuple is a singleton:
() is ()  # True!

# Small tuples (size 1-20) are recycled:
t = (1,)   # May come from free list
del t       # Returns to free list for reuse
```

---

## 15.7 Comparison: Python vs Other Approaches

### Tracing GC (Java, Go, C#)

```
Advantages over Python:
  - No per-object overhead for reference count (save 8 bytes/object)
  - No write barriers on every assignment
  - Objects can be moved (compacting GC → better cache locality)
  - No circular reference problem

Disadvantages:
  - Unpredictable pause times (GC sweeps)
  - Higher peak memory usage (dead objects linger until GC runs)
  - Object finalization is non-deterministic
```

### Manual Memory (C, C++, Rust)

```
Advantages over Python:
  - Zero per-object overhead (no headers unless you add them)
  - No GC pauses
  - Stack allocation for small objects (zero heap cost)
  - Data-oriented layout possible (struct of arrays)

Disadvantages:
  - Use-after-free bugs
  - Memory leaks
  - Manual lifetime tracking (or complex ownership types in Rust)
  - No runtime type introspection without RTTI
```

---

## 15.8 Performance Tips for Python Developers

### Minimize Object Creation

```python
# BAD: Creates a new tuple each iteration
for i in range(N):
    point = (x[i], y[i])
    process(point)

# BETTER: Use numpy or process inline
process_batch(x, y)
```

### Use __slots__ for Data Classes

```python
# WITHOUT __slots__: Each instance has a __dict__ (~100+ bytes overhead)
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
# sys.getsizeof(Point(1,2)) → ~48 bytes + dict ~184 bytes = ~232 total

# WITH __slots__: No __dict__, attributes stored inline
class Point:
    __slots__ = ('x', 'y')
    def __init__(self, x, y):
        self.x = x
        self.y = y
# sys.getsizeof(Point(1,2)) → ~48 bytes total (saves ~180 bytes per instance!)
```

### Prefer Tuples Over Lists for Immutable Data

```python
# Tuple: inline storage, smaller header, can be cached
coords = (3.14, 2.71)   # 56 bytes

# List: extra indirection, over-allocation, GC tracking
coords = [3.14, 2.71]   # 72+ bytes
```

### Use Array/NumPy for Numeric Data

```python
import array
import numpy as np

# Python list of 1000 floats: ~32 KB (pointers + objects)
pylist = [0.0] * 1000

# array.array: ~8 KB (raw doubles, one object header)
arr = array.array('d', [0.0] * 1000)

# NumPy: ~8 KB (raw doubles, one object header)
nparr = np.zeros(1000)
```

---

## 15.9 Measuring Object Overhead

```python
import sys
import tracemalloc

# Track memory allocations:
tracemalloc.start()

# Create objects and measure:
data = [float(i) for i in range(100_000)]
snapshot = tracemalloc.take_snapshot()
stats = snapshot.statistics('lineno')
print(stats[0])  # Shows memory used

# Manual size calculation:
total = sys.getsizeof(data)  # List struct + pointer array
total += sum(sys.getsizeof(x) for x in data)  # All float objects
print(f"Total: {total:,} bytes")
# ~3.2 MB for 100K floats (vs 800 KB in C)
```

---

## 15.10 Source References

| File | Relevance |
|------|-----------|
| `Objects/obmalloc.c` | PyMalloc performance, size classes, free lists |
| `Objects/longobject.c` | Small integer cache |
| `Objects/floatobject.c` | Float free list |
| `Objects/tupleobject.c` | Tuple free list, empty tuple singleton |
| `Objects/unicodeobject.c` | String interning |
| `Include/refcount.h` | Py_INCREF/DECREF implementation (hot path) |
| `Python/ceval.c` | Interpreter main loop (refcount operations) |

---

## 15.11 Interview Questions — Part 15

**Q1**: How much memory overhead does a Python int(42) have compared to a C int?
**A**: Python int(42) = 28 bytes (16B header + 8B ob_size + 4B digit). C int = 4 bytes. That's 7× overhead. The extra bytes pay for: reference counting (8B), type identification (8B), variable-precision support (8B ob_size), and the digit array.

**Q2**: Why is iterating a Python list slower than iterating a C array from a cache perspective?
**A**: A C array stores values contiguously — one cache line load brings multiple elements. A Python list stores pointers to scattered heap objects. Each element access follows a pointer to a random address, likely causing a cache miss (~100 cycles). This "pointer chasing" is the main bottleneck.

**Q3**: What percentage of CPython execution time is spent on reference counting?
**A**: Approximately 10-15% of total interpreter time goes to Py_INCREF/Py_DECREF operations. This is the price of deterministic lifetime management — every variable assignment, function call, and container operation requires refcount updates.

**Q4**: Explain the free list optimization and which types use it.
**A**: When objects are deallocated, instead of returning memory to the allocator, they're saved in a per-type "free list." Next allocation of that type takes from the free list (O(1), no allocator overhead). Types using this: float (100 max), list (80), dict (80), tuple (by size), set, frame objects.

**Q5**: Why does `__slots__` save memory, and by how much?
**A**: Without `__slots__`, each instance has a `__dict__` (a full PyDictObject + keys structure, ~100-200 bytes). With `__slots__`, attributes are stored as fixed pointer slots in the instance struct (8 bytes each). For a 2-attribute class, savings are ~150-180 bytes per instance.

**Q6**: Compare Python's refcounting with Java's tracing GC in terms of memory overhead.
**A**: Python: 8 bytes per object for refcount, immediate deallocation, deterministic. Java: no per-object refcount overhead, but ~8-16 bytes for object header (mark word + class pointer), non-deterministic GC pauses, and higher peak memory (dead objects live until GC sweep). Python pays per-object, Java pays in pause times and peak memory.

**Q7**: What is the pymalloc "fast path" and how fast is it?
**A**: The fast path is: read `pool->freeblock`, update the free list pointer, return the block. It's ~5-10 nanoseconds — just two pointer operations. This works when the target size-class pool has free blocks available. The "slow path" (allocating new pools/arenas) is much more expensive.

**Q8**: How do immortal objects (Python 3.12+) improve performance?
**A**: Immortal objects (None, True, False, small integers) skip Py_INCREF/Py_DECREF entirely. This eliminates: (1) memory writes for their refcounts, (2) cache line dirty marking, (3) cache line bouncing between CPU cores in multi-threaded code. The check adds a branch but avoids the write — net positive for these super-hot objects.
