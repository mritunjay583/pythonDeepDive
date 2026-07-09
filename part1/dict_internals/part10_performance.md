# Part 10 — Performance

## 10.1 Cache Locality

### The Compact Dict Advantage

```
OLD LAYOUT (≤ 3.5) — Iteration:
┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
│ ACTIVE   │  EMPTY   │  EMPTY   │ ACTIVE   │  EMPTY   │ ACTIVE   │
│ 24 bytes │ 24 bytes │ 24 bytes │ 24 bytes │ 24 bytes │ 24 bytes │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────┘
Cache line 1 (64 bytes)          │ Cache line 2
→ 2 useful entries per 2.67 cache lines → ~33% cache utilization

NEW LAYOUT (3.6+) — Iteration over dense entries:
┌──────────────────────┬──────────────────────┬──────────────────────┐
│ entry[0]: hash,k,v   │ entry[1]: hash,k,v   │ entry[2]: hash,k,v   │
│ 24 bytes             │ 24 bytes             │ 24 bytes             │
└──────────────────────┴──────────────────────┴──────────────────────┘
Cache line 1 (64 bytes): ~2.67 entries
→ ALL entries are useful → 100% cache utilization for iteration!
```

For `for key in my_dict`: the new layout scans contiguous memory with no gaps.

### Lookup Cache Behavior

```
Lookup "hello" in dict:
1. Read dk_indices[hash & mask] → 1 cache line access (index table is small)
2. Read dk_entries[idx]         → 1 cache line access (entries are contiguous)
3. Compare hash (in entry)      → already loaded
4. Compare key pointer          → already loaded
5. If match: read value         → already loaded!

Most lookups: 2 cache line accesses total.
With old layout: lookup might touch a random slot → unpredictable cache behavior.
```

---

## 10.2 Memory Usage

### Measuring Dict Memory

```python
import sys

# sys.getsizeof reports dict object + internal structures
sys.getsizeof({})                    # ~64 bytes (empty)
sys.getsizeof({"a": 1})             # ~184 bytes
sys.getsizeof({i: i for i in range(5)})  # ~232 bytes
sys.getsizeof({i: i for i in range(100)})  # ~4,184 bytes

# But: does NOT include key/value objects themselves!
```

### Memory Formula (approximate)

```
dict memory ≈ 
    sizeof(PyDictObject)           (~48 bytes)
  + sizeof(PyDictKeysObject)       (~40 bytes header)
  + index_table                    (table_size × index_bytes)
  + entries_array                  (dk_nentries × 24 bytes)

Where:
  table_size = smallest power of 2 ≥ 1.5 × num_entries
  index_bytes = 1 (table ≤ 128), 2 (≤ 32K), 4 (≤ 2B), 8 (larger)
```

### Example: Dict with 100 entries

```
table_size = 256 (next power of 2 after 100 * 1.5 = 150)
index_bytes = 2 (table > 128)

Memory:
  48 (dict object)
  + 40 (keys header)
  + 256 × 2 (index table = 512 bytes)
  + 100 × 24 (entries = 2400 bytes)
  = 3000 bytes

Plus key objects + value objects (not counted by getsizeof)
```

---

## 10.3 Large Dictionaries (Millions of Keys)

### Memory at Scale

```
1 million string keys → string values:

Dict internals:
  table_size = 2,097,152 (2^21, next power of 2 after 1.5M)
  index_table = 2,097,152 × 4 bytes = 8 MB
  entries = 1,000,000 × 24 bytes = 24 MB
  Total dict: ~32 MB

Key objects (avg 20-char strings): ~80 bytes each = 80 MB
Value objects: depends on content

Grand total: ~112+ MB for 1M string→string pairs
```

### Performance at Scale

```
Lookup in 1M-entry dict:
  Expected probes: ~1.5 (load factor still 2/3)
  Each probe: 1 index read + 1 entry read
  Time: ~100-200 ns per lookup

Insert into 1M-entry dict:
  Same as lookup + write = ~150-250 ns
  Occasional resize: O(n) = ~50ms for 1M entries
```

---

## 10.4 Optimization Techniques

### 1. Avoid Unnecessary Dict Creation

```python
# BAD: creates temp dict per call
def process(items):
    config = {"timeout": 30, "retries": 3}  # New dict every call!
    ...

# GOOD: module-level constant
_CONFIG = {"timeout": 30, "retries": 3}  # Created once
def process(items):
    config = _CONFIG
    ...
```

### 2. Use `__slots__` for Memory Reduction

```python
# Without __slots__: each instance has a full dict
class Point:
    def __init__(self, x, y):
        self.x = x  # Stored in instance __dict__
        self.y = y

# With __slots__: NO dict at all!
class Point:
    __slots__ = ('x', 'y')
    def __init__(self, x, y):
        self.x = x  # Stored in fixed slots
        self.y = y

# Memory per instance:
# Without slots: ~300 bytes (object + dict + keys)
# With slots: ~56 bytes (object + 2 slots)
# Savings: 80%+ for small objects
```

### 3. Key-Sharing Awareness

```python
# GOOD: consistent attributes across instances (key sharing kicks in)
class User:
    def __init__(self, name, email, age):
        self.name = name
        self.email = email
        self.age = age

# BAD: different attributes per instance (key sharing breaks)
class FlexUser:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)  # Different keys per instance!
```

### 4. Minimize Dict Copies

```python
# BAD: unnecessary copy
new_config = dict(base_config)  # O(n) copy
new_config["extra"] = value

# BETTER: ChainMap for layered lookups (no copy)
from collections import ChainMap
new_config = ChainMap({"extra": value}, base_config)
```

### 5. Use setdefault / defaultdict

```python
# BAD: double lookup
if key not in d:
    d[key] = []
d[key].append(value)

# GOOD: single lookup
d.setdefault(key, []).append(value)

# BEST: defaultdict (no key check at all)
from collections import defaultdict
d = defaultdict(list)
d[key].append(value)
```

---

## 10.5 String Interning and Dict Performance

CPython automatically interns (caches) strings that look like identifiers:

```python
a = "hello"
b = "hello"
a is b  # True! Same object (interned)

# This means dict lookups for attribute names are often identity checks:
# obj.__dict__["method_name"]
# The key "method_name" is interned → pointer comparison (O(1))
# No need for full string comparison!
```

This is why attribute access (`obj.x`) is so fast — the attribute name string is interned, so the dict lookup often resolves with just a pointer comparison.

---

## 10.6 Dict vs Alternatives

| Use Case | Best Choice | Why |
|----------|-------------|-----|
| Key-value mapping | `dict` | O(1) lookup, built-in |
| Ordered map | `dict` (3.7+) | Insertion order preserved |
| Multi-level defaults | `ChainMap` | No copying, layered lookup |
| Missing keys → default | `defaultdict` | Auto-creates on access |
| Counting | `Counter` | Optimized for counting pattern |
| Enum-like constants | `types.SimpleNamespace` or class | Clearer intent |
| Fixed fields, many instances | `__slots__` class | 80%+ memory savings |
| Immutable mapping | `types.MappingProxyType` | Read-only view |
| Very small mappings (<5) | Named tuple or dataclass | Less overhead |

---

## 10.7 Profiling Dict Usage

```python
# Memory profiling:
import tracemalloc
tracemalloc.start()

big_dict = {str(i): i for i in range(100000)}

current, peak = tracemalloc.get_traced_memory()
print(f"Dict memory: {current / 1024 / 1024:.1f} MB")
print(f"Peak memory: {peak / 1024 / 1024:.1f} MB")

# Performance profiling:
import timeit

# Measure lookup time:
d = {str(i): i for i in range(1000000)}
t = timeit.timeit(lambda: d["500000"], number=1000000)
print(f"Lookup: {t*1000/1000000:.3f} μs per call")
```

---

## 10.8 Production Anti-Patterns

### Anti-Pattern 1: Dict as a Poor Man's Object

```python
# BAD: using dict for structured data
user = {"name": "Alice", "age": 30, "email": "a@b.com"}
# No type checking, no autocomplete, easy to typo keys

# GOOD: use dataclass
@dataclass
class User:
    name: str
    age: int
    email: str
```

### Anti-Pattern 2: Excessive Dict Comprehension Copies

```python
# BAD: creates new dict on every filter
filtered = {k: v for k, v in big_dict.items() if v > threshold}
# O(n) time and space even if few items match

# BETTER for iteration: generator
filtered_items = ((k, v) for k, v in big_dict.items() if v > threshold)
```

### Anti-Pattern 3: Using Dict for Membership Testing

```python
# BAD: dict with dummy values
seen = {x: True for x in data}
if item in seen: ...

# GOOD: use a set
seen = set(data)
if item in seen: ...
```

---

## 10.9 Interview Questions — Part 10

**Q1**: How does the compact dict improve cache locality for iteration?
**A**: Entries are stored in a dense array with no gaps. Iterating touches contiguous memory, utilizing every cache line. The old sparse layout had 2/3 empty slots interspersed.

**Q2**: How much memory does a dict with 1M entries use?
**A**: ~32 MB for dict internals (8 MB index table + 24 MB entries). Plus memory for key and value objects themselves.

**Q3**: How can you reduce memory for many instances with same attributes?
**A**: Use `__slots__` (eliminates per-instance dict entirely) or rely on key-sharing dicts (automatic for consistent class instances). `__slots__` saves ~80%.

**Q4**: Why is attribute access fast in Python?
**A**: Attribute names are interned strings. Dict lookup for interned strings often resolves with a pointer identity check (`is`) — faster than full string comparison.

**Q5**: What's better for counting: dict or Counter?
**A**: `collections.Counter` — it's optimized for the counting pattern, handles missing keys without KeyError, and provides useful methods like `.most_common()`.
