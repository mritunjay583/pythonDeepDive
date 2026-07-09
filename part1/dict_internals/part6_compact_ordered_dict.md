# Part 6 — Compact Ordered Dict (Python 3.6+)

## 6.1 Historical Evolution

### Python ≤ 3.5: Old-Style Hash Table

```
Single sparse array where each slot holds the FULL entry:

slot[0]: (hash, key_ptr, value_ptr)  or  EMPTY
slot[1]: (hash, key_ptr, value_ptr)  or  EMPTY
slot[2]: EMPTY
slot[3]: (hash, key_ptr, value_ptr)  or  EMPTY
...

Each slot: 24 bytes (hash=8, key_ptr=8, val_ptr=8)
Table size 8: 8 × 24 = 192 bytes (even with only 3 entries!)

Problems:
- ~2/3 of slots are EMPTY → 2/3 of memory wasted on empty 24-byte slots
- No insertion order (iteration order was arbitrary/random)
- Poor cache locality (entries scattered by hash positions)
```

### Python 3.6+ (CPython): Compact Layout

Raymond Hettinger's design (2016) splits into two arrays:

```
SPARSE INDEX TABLE (small per-slot cost):
┌──┬──┬──┬──┬──┬──┬──┬──┐
│-1│ 0│-1│ 1│-1│ 2│-1│-1│    ← 1 byte each! (for small tables)
└──┴──┴──┴──┴──┴──┴──┴──┘
8 bytes total (vs 192 bytes in old layout!)

DENSE ENTRIES ARRAY (packed, no gaps):
┌─────────────────────────────────┐
│[0]: hash_a, "a", value_a       │
│[1]: hash_b, "b", value_b       │    ← 24 bytes each, but NO empty slots!
│[2]: hash_c, "c", value_c       │
└─────────────────────────────────┘
72 bytes (3 entries × 24)

Total: 8 + 72 = 80 bytes (vs 192 bytes in old layout!)
Memory savings: ~58%!
```

---

## 6.2 Why the Compact Layout Saves Memory

### Old Layout (Python ≤ 3.5):

```
Table size must be ≥ 1.5× entries (load factor 2/3)
For 5 entries: table_size = 8
Memory = 8 slots × 24 bytes/slot = 192 bytes
  Active: 5 × 24 = 120 bytes (useful data)
  Wasted: 3 × 24 = 72 bytes (empty slots with full entry space)
```

### New Layout (Python 3.6+):

```
For 5 entries: table_size = 8
Index table: 8 × 1 byte = 8 bytes (sparse, but tiny per slot)
Entries: 5 × 24 bytes = 120 bytes (dense, no waste)
Total: 128 bytes
Savings: (192 - 128) / 192 = 33% smaller!

For larger dicts the savings are even better:
Old (1000 entries, table=2048): 2048 × 24 = 49,152 bytes
New (1000 entries, table=2048): 2048 × 2 + 1000 × 24 = 4,096 + 24,000 = 28,096 bytes
Savings: 43%!
```

---

## 6.3 Insertion Order — How It Works

The dense entries array naturally preserves insertion order:

```python
d = {}
d["first"] = 1     # entries[0] = ("first", 1)
d["second"] = 2    # entries[1] = ("second", 2)
d["third"] = 3     # entries[2] = ("third", 3)

# Iterating d.keys() walks entries[0], entries[1], entries[2]
# → "first", "second", "third"
# ALWAYS in insertion order!
```

### Why Old Dicts Didn't Have Order:

In the old layout, entries are stored at their HASH position:
```
"first" → hash→slot 5
"second" → hash→slot 1
"third" → hash→slot 6

Iteration walks slots 0,1,2,...7:
  slot 1: "second"
  slot 5: "first"
  slot 6: "third"
→ Iteration order: "second", "first", "third" (hash-determined, not insertion order!)
```

### Why New Dicts DO Have Order:

Entries array is append-only during insertion:
```
entries[0] = first thing inserted
entries[1] = second thing inserted
entries[2] = third thing inserted

Iteration walks entries[0], entries[1], entries[2]
→ Always insertion order!
```

---

## 6.4 The Language Guarantee (Python 3.7+)

- **Python 3.6**: Insertion order preserved as CPython implementation detail
- **Python 3.7+**: Insertion order is a **language specification guarantee**

```python
# Guaranteed behavior since Python 3.7:
d = {"a": 1, "b": 2, "c": 3}
list(d.keys()) == ["a", "b", "c"]  # Always True!
list(d.values()) == [1, 2, 3]      # Always True!

# Replacing a value doesn't change order:
d["b"] = 99
list(d.keys()) == ["a", "b", "c"]  # Still True!

# Deleting and re-inserting moves to end:
del d["a"]
d["a"] = 1
list(d.keys()) == ["b", "c", "a"]  # "a" moved to end!
```

---

## 6.5 Comparison: Old vs New Layout

| Aspect | Old (≤3.5) | New (3.6+) |
|--------|-----------|------------|
| Memory per empty slot | 24 bytes | 1-8 bytes |
| Iteration | Hash order (random) | Insertion order |
| Cache locality for iteration | Poor (sparse) | Excellent (dense) |
| Lookup | O(1) avg | O(1) avg |
| Insert | O(1) amortized | O(1) amortized |
| Resize | Rehash all entries | Rebuild indices + compact entries |
| `OrderedDict` needed? | Yes (for ordered behavior) | No (built-in) |

---

## 6.6 Impact on `collections.OrderedDict`

Since Python 3.7, regular `dict` maintains order. So why does `OrderedDict` still exist?

`OrderedDict` has additional features:
```python
from collections import OrderedDict

# 1. move_to_end():
od = OrderedDict(a=1, b=2, c=3)
od.move_to_end('a')  # Move 'a' to end
# dict has no equivalent

# 2. Equality considers order:
OrderedDict(a=1, b=2) == OrderedDict(b=2, a=1)  # False!
dict(a=1, b=2) == dict(b=2, a=1)                 # True!

# 3. popitem(last=False):
od.popitem(last=False)  # Pop from BEGINNING (FIFO)
# dict.popitem() only pops from end (LIFO)
```

For most use cases, regular `dict` is sufficient and faster than `OrderedDict`.

---

## 6.7 How Resize Preserves Order

During resize, entries are copied in order:

```
BEFORE RESIZE:
entries: [(h_a,"a",1), (HOLE), (h_c,"c",3), (h_d,"d",4)]
         entry 0      entry 1   entry 2      entry 3
(entry 1 was deleted — it's a hole)

AFTER RESIZE:
entries: [(h_a,"a",1), (h_c,"c",3), (h_d,"d",4)]
         entry 0      entry 1      entry 2
(holes eliminated, remaining entries maintain relative order!)

New indices recomputed for new table size.
```

The relative order of surviving entries is preserved. Deleted entries are simply skipped during the rebuild.

---

## 6.8 The Compact Dict in Numbers

For a dict with n entries and table_size = m (where m ≈ 1.5n, power of 2):

```
Old layout memory:  m × 24 bytes
New layout memory:  m × index_size + n × 24 bytes

Where index_size:
  m ≤ 128:    1 byte
  m ≤ 32768:  2 bytes
  m ≤ 2^31:   4 bytes
  else:        8 bytes

Example (100 entries, m=256):
  Old:  256 × 24 = 6,144 bytes
  New:  256 × 1 + 100 × 24 = 256 + 2,400 = 2,656 bytes
  Savings: 57%!

Example (1M entries, m=2,097,152):
  Old:  2,097,152 × 24 = 50,331,648 bytes (~50 MB)
  New:  2,097,152 × 4 + 1,000,000 × 24 = 8,388,608 + 24,000,000 = 32,388,608 bytes (~32 MB)
  Savings: 36%
```

---

## 6.9 Cache Locality Improvement

```
Old layout iteration (sparse):
  Visit slot 0 → EMPTY (cache line loaded for nothing)
  Visit slot 1 → entry (useful)
  Visit slot 2 → EMPTY (wasted)
  Visit slot 3 → EMPTY (wasted)
  Visit slot 4 → entry (useful)
  ...
  ~33% of cache loads are useful

New layout iteration (dense):
  Visit entries[0] → entry (useful!)
  Visit entries[1] → entry (useful!)
  Visit entries[2] → entry (useful!)
  ...
  100% of cache loads are useful!
```

Iterating over dict keys/values is significantly faster with the dense layout because every cache line contains useful data.

---

## 6.10 Interview Questions — Part 6

**Q1**: What changed in Python 3.6 regarding dict implementation?
**A**: CPython introduced the compact dict layout: a small sparse index table + dense entries array. This saves ~30-50% memory and preserves insertion order as a side effect.

**Q2**: When did dict ordering become a language guarantee?
**A**: Python 3.7. In 3.6, it was a CPython implementation detail. In 3.7, it became part of the language spec that all implementations must follow.

**Q3**: How does the compact layout save memory?
**A**: Empty slots in the sparse index table cost only 1-4 bytes each (vs 24 bytes in old layout). The dense entries array has no empty slots at all.

**Q4**: Is `collections.OrderedDict` obsolete?
**A**: Not entirely. It provides `move_to_end()`, order-sensitive equality, and `popitem(last=False)`. But for basic "ordered dict" behavior, regular dict suffices since 3.7.

**Q5**: What happens to insertion order when you delete a key and re-insert it?
**A**: The re-inserted key goes to the end. `del d["x"]; d["x"] = val` moves "x" to the last position.

**Q6**: Does updating an existing key change its position?
**A**: No. `d["existing_key"] = new_value` only updates the value; the key's position in iteration order is unchanged.
