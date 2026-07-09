# Part 8 — Performance

## 8.1 Cost Comparison

```python
import copy, timeit

data = [list(range(100)) for _ in range(1000)]  # 1000 lists of 100 ints

# Assignment: O(1)
timeit.timeit(lambda: data, number=1000000)  # ~0.05 μs each

# Shallow copy: O(n) top-level elements
timeit.timeit(lambda: data.copy(), number=10000)  # ~200 μs each

# Deep copy: O(N) entire graph
timeit.timeit(lambda: copy.deepcopy(data), number=100)  # ~50 ms each
```

| Method | Time | Memory | Independence |
|--------|------|--------|-------------|
| `b = a` | O(1), ~20 ns | 0 extra bytes | None (alias) |
| `a.copy()` | O(n), ~200 μs | n×8 bytes (ptrs) | Container only |
| `copy.deepcopy(a)` | O(N), ~50 ms | Entire graph duplicated | Full |

For the example above: deepcopy is **250,000× slower** than assignment.

---

## 8.2 When NOT to Copy

### Pattern 1: Read-only access
```python
# BAD: copying "just in case"
def analyze(data):
    safe_data = copy.deepcopy(data)  # 50ms wasted!
    return sum(safe_data) / len(safe_data)

# GOOD: don't copy if you're not mutating
def analyze(data):
    return sum(data) / len(data)  # No mutation → no copy needed
```

### Pattern 2: Immutable data
```python
# BAD: copying immutable data
config = ("host", 8080, True)
safe_config = copy.deepcopy(config)  # Pointless! Tuples of immutables are already safe.

# GOOD: just reference it
safe_config = config  # Immutable — can't be modified anyway
```

### Pattern 3: Short-lived locals
```python
# BAD: defensive copy of data you're about to discard
def process(items):
    local_items = items.copy()  # Why copy if function ends soon?
    return [x * 2 for x in local_items]

# GOOD: just read the original
def process(items):
    return [x * 2 for x in items]
```

---

## 8.3 Alternatives to Copying

### Alternative 1: Use immutable types
```python
# Instead of: copying a list to prevent mutation
data = [1, 2, 3]
safe = data.copy()

# Use a tuple (immutable — can't be accidentally mutated):
data = (1, 2, 3)
# No copy needed — tuples can't be modified
```

### Alternative 2: Frozen dataclasses
```python
@dataclass(frozen=True)
class Config:
    host: str
    port: int
    
# Can't be mutated → never needs copying
config = Config("localhost", 8080)
```

### Alternative 3: Copy-on-write semantics
```python
# Instead of pre-emptive deep copy:
class LazyConfig:
    def __init__(self, data):
        self._data = data
        self._modified = False
    
    def modify(self, key, value):
        if not self._modified:
            self._data = copy.deepcopy(self._data)  # Copy only when needed
            self._modified = True
        self._data[key] = value
```

### Alternative 4: sorted/map/filter (create new without explicit copy)
```python
# These naturally create new objects:
new_list = sorted(original)        # New sorted list
new_list = [x*2 for x in original] # New transformed list
new_dict = {k: v+1 for k, v in d.items()}  # New dict
```

---

## 8.4 Memory Impact

```python
import sys
from pympler import asizeof

# Original: nested structure
data = {"users": [{"name": f"user_{i}", "scores": list(range(10))} 
                  for i in range(10000)]}

print(asizeof.asizeof(data))  # ~6.5 MB

# After deep copy:
data_copy = copy.deepcopy(data)
# Memory doubles: original still exists + full copy = ~13 MB

# After shallow copy:
data_shallow = data.copy()  # Only new top-level dict (~200 bytes extra)
# Total: ~6.5 MB + 200 bytes (inner objects shared)
```

---

## 8.5 Profiling Copy Operations

```python
import tracemalloc, copy

tracemalloc.start()

data = [list(range(1000)) for _ in range(1000)]

snapshot1 = tracemalloc.take_snapshot()
data_copy = copy.deepcopy(data)
snapshot2 = tracemalloc.take_snapshot()

stats = snapshot2.compare_to(snapshot1, 'lineno')
for stat in stats[:5]:
    print(stat)  # Shows memory allocated by deepcopy
```

---

## 8.6 Best Practices

1. **Default to NO copy** — only copy when you have evidence of unwanted mutation
2. **Prefer shallow copy** when elements are immutable
3. **Use deepcopy sparingly** — it's expensive and often unnecessary
4. **Design with immutability** — immutable objects never need copying
5. **Document mutation** — if a function mutates arguments, document it clearly
6. **Use type hints** — `def process(data: Sequence[int])` suggests read-only
7. **Profile before optimizing** — measure if copying is actually a bottleneck

---

## 8.7 Interview Questions — Part 8

**Q1**: How much slower is deepcopy compared to assignment?
**A**: Typically 100,000-1,000,000× slower. Assignment is O(1) pointer copy (~20ns). Deepcopy traverses the entire object graph with Python-level recursion.

**Q2**: When should you avoid copying altogether?
**A**: When you're only reading data (no mutation), when data is immutable, when the function's purpose is to transform (naturally creates new objects), or when the copy's lifetime is shorter than the operation.

**Q3**: What's the memory impact of deepcopy?
**A**: Approximately doubles memory usage — the entire object graph is duplicated (except shared immutables). For large data structures, this can be significant.

**Q4**: What are alternatives to copying for mutation protection?
**A**: Use immutable types (tuple, frozenset, frozen dataclass), copy-on-write patterns, or functional transformations that naturally produce new objects.

**Q5**: How do you profile the cost of a copy operation?
**A**: Use `tracemalloc` for memory, `timeit` for speed, `pympler.asizeof` for deep size measurement. Compare the cost against your actual workload requirements.
