# Part 3 — PyDictObject Structure

## 3.1 The Actual C Structures

### PyDictObject (the dict itself)

```c
// Include/cpython/dictobject.h
typedef struct {
    PyObject_HEAD
    Py_ssize_t ma_used;            // Number of active (non-deleted) entries
    uint64_t ma_version_tag;       // Version counter (PEP 509)
    PyDictKeysObject *ma_keys;     // Pointer to keys+indices structure
    PyDictValues *ma_values;       // NULL for combined, non-NULL for split table
} PyDictObject;
```

### PyDictKeysObject (the hash table + entries)

```c
typedef struct {
    Py_ssize_t dk_refcnt;          // Reference count for key sharing
    uint8_t dk_log2_size;          // log2 of hash table size (size = 2^dk_log2_size)
    uint8_t dk_log2_index_bytes;   // log2 of bytes per index entry
    uint8_t dk_kind;               // DICT_KEYS_GENERAL, DICT_KEYS_UNICODE, DICT_KEYS_SPLIT
    uint32_t dk_version;           // Version for keys
    Py_ssize_t dk_usable;          // Number of usable entries (before resize needed)
    Py_ssize_t dk_nentries;        // Number of entries used (next free index in entries)
    
    // Followed in memory by:
    // 1. dk_indices[]: the hash table (sparse array of indices)
    // 2. dk_entries[]: dense array of (hash, key, value) tuples
} PyDictKeysObject;
```

### PyDictKeyEntry (one entry in the dense array)

```c
typedef struct {
    Py_hash_t me_hash;     // Cached hash value (avoids recomputing)
    PyObject *me_key;      // Pointer to key object
    PyObject *me_value;    // Pointer to value object
} PyDictKeyEntry;
```

---

## 3.2 Field-by-Field Explanation

### PyDictObject Fields:

#### `ma_used`
- The count of **active** (live) key-value pairs
- This is what `len(d)` returns
- Does NOT include deleted (dummy) slots

#### `ma_version_tag`
- A unique version number incremented on every modification
- Used by PEP 509 optimizations (e.g., cached attribute lookups)
- Allows fast "has this dict changed?" checks without comparing contents
- Global counter: each dict modification gets a unique version

#### `ma_keys`
- Pointer to the `PyDictKeysObject` that contains both the hash table indices and the entry array
- Shared between multiple dicts for key-sharing optimization (split tables)

#### `ma_values`
- NULL for a **combined table** (normal dict)
- Points to a values array for **split table** (instance __dict__)
- Split tables share `ma_keys` between instances of the same class

---

## 3.3 Combined Table vs Split Table

### Combined Table (normal dict, most common)

```python
d = {"name": "Alice", "age": 30, "city": "NYC"}
```

```
PyDictObject:
  ma_used = 3
  ma_keys → PyDictKeysObject
  ma_values = NULL          ← combined: values stored in dk_entries

PyDictKeysObject:
  dk_indices: [sparse hash table with indices]
  dk_entries: [(hash, "name", "Alice"), (hash, "age", 30), (hash, "city", "NYC")]
```

Values are stored inline in `dk_entries` alongside keys and hashes.

### Split Table (instance __dict__, key-sharing)

```python
class Person:
    def __init__(self, name, age, city):
        self.name = name    # All Person instances have same keys!
        self.age = age
        self.city = city

p1 = Person("Alice", 30, "NYC")
p2 = Person("Bob", 25, "LA")
```

```
p1.__dict__:
  PyDictObject:
    ma_used = 3
    ma_keys → SHARED PyDictKeysObject  ←── shared!
    ma_values → ["Alice", 30, "NYC"]   ← separate values array

p2.__dict__:
  PyDictObject:
    ma_used = 3
    ma_keys → SHARED PyDictKeysObject  ←── same keys object!
    ma_values → ["Bob", 25, "LA"]      ← different values

SHARED PyDictKeysObject:
  dk_refcnt = 2  (shared by p1 and p2)
  dk_entries: [(hash, "name", NULL), (hash, "age", NULL), (hash, "city", NULL)]
              ← values are NULL here (stored in ma_values instead)
```

**Memory savings**: 1000 instances share ONE keys object instead of 1000 copies.

---

## 3.4 Why Key-Sharing Saves Memory

Without key-sharing (Python < 3.3):
```
1000 Person instances × full dict each:
  = 1000 × (dict header + hash table + entries with keys + values)
  = 1000 × ~300 bytes = ~300 KB
```

With key-sharing (Python 3.3+):
```
1 shared keys object: ~200 bytes
+ 1000 instances × (dict header + values array only):
  = 200 + 1000 × ~80 bytes = ~80 KB
```

**~75% memory reduction** for instances with consistent attributes!

### When Key-Sharing Breaks:

```python
p1 = Person("Alice", 30, "NYC")
p1.extra = "something"  # Adds new key not in shared layout!
# p1's dict "unshares" — converts from split to combined table
```

If any instance adds/removes keys that differ from the class pattern, that instance's dict falls back to a normal combined table.

---

## 3.5 Complete Memory Layout (Combined Table)

```python
d = {"a": 1, "b": 2, "c": 3}
```

```
══════════════════════════════════════════════════════════════
PyDictObject (on heap, ~48 bytes with GC header)
══════════════════════════════════════════════════════════════
Field           Size    Value
──────────────────────────────────────────────────────────────
ob_refcnt       8       1
ob_type         8       → PyDict_Type
ma_used         8       3
ma_version_tag  8       some_unique_version
ma_keys         8       → 0x7F001000 (PyDictKeysObject)
ma_values       8       NULL (combined table)
══════════════════════════════════════════════════════════════


══════════════════════════════════════════════════════════════
PyDictKeysObject at 0x7F001000
══════════════════════════════════════════════════════════════
Field               Size    Value
──────────────────────────────────────────────────────────────
dk_refcnt           8       1
dk_log2_size        1       3 (table size = 2^3 = 8)
dk_log2_index_bytes 1       0 (1 byte per index for small tables)
dk_kind             1       DICT_KEYS_UNICODE
dk_version          4       ...
dk_usable           8       2 (can still add 2 more before resize)
dk_nentries         8       3 (3 entries stored)
──────────────────────────────────────────────────────────────

Followed immediately in memory by:

dk_indices (hash table, 8 slots × 1 byte each = 8 bytes):
┌────┬────┬────┬────┬────┬────┬────┬────┐
│ -1 │  0 │ -1 │  1 │ -1 │  2 │ -1 │ -1 │
└────┴────┴────┴────┴────┴────┴────┴────┘
 [0]   [1]  [2]  [3]  [4]  [5]  [6]  [7]

 -1 = EMPTY (no entry at this hash slot)
  0,1,2 = index into dk_entries array

dk_entries (dense array, 3 used entries):
┌───────────────────────────────────────────────────────┐
│ [0]: hash=hash("a"), key→"a", value→int(1)           │
│ [1]: hash=hash("b"), key→"b", value→int(2)           │
│ [2]: hash=hash("c"), key→"c", value→int(3)           │
│ [3]: (unused)                                         │
│ [4]: (unused — dk_usable says 2 more slots available) │
└───────────────────────────────────────────────────────┘
══════════════════════════════════════════════════════════════
```

---

## 3.6 Index Table Sizing

The dk_indices array uses the smallest integer type that can represent all index values:

| Table size (2^n) | Max entries | Index type | Bytes per index |
|------------------|-------------|------------|-----------------|
| ≤ 128 | ≤ 85 | int8_t | 1 |
| ≤ 32768 | ≤ 21845 | int16_t | 2 |
| ≤ 2^31 | ≤ ~1.4B | int32_t | 4 |
| > 2^31 | > 1.4B | int64_t | 8 |

Special index values:
```c
#define DKIX_EMPTY    (-1)   // Slot never used
#define DKIX_DUMMY    (-2)   // Slot was deleted (tombstone)
```

For a dict with 8 hash table slots and ≤ 128 possible entries, each index is just 1 byte!

**Memory savings**: Old-style dict stored full `(hash, key*, value*)` = 24 bytes per slot. New style stores 1-byte index per slot → 8× savings on the sparse part!

---

## 3.7 dk_usable: Tracking Capacity

`dk_usable` tracks how many more entries can be added before a resize is needed:

```
Initial state (table size 8):
  max_entries = table_size * 2/3 = 8 * 2/3 = 5
  dk_nentries = 0
  dk_usable = 5

After inserting 3 items:
  dk_nentries = 3
  dk_usable = 2   (can add 2 more)

After inserting 2 more:
  dk_nentries = 5
  dk_usable = 0   (FULL — next insert triggers resize!)
```

---

## 3.8 The dk_kind Field

```c
#define DICT_KEYS_GENERAL   0  // Keys can be any type
#define DICT_KEYS_UNICODE   1  // All keys are strings (optimized path)
#define DICT_KEYS_SPLIT     2  // Split table (instance __dict__)
```

When all keys are strings (very common — attribute access, kwargs), CPython uses an optimized code path that skips type checking.

---

## 3.9 ASCII Memory Diagram — The Big Picture

```
    Variable 'd'                    
         │                          
         ▼                          
┌──────────────────┐                
│  PyDictObject    │                
│                  │                
│  ma_used: 3     │                
│  ma_keys: ──────┼───────────────────┐
│  ma_values: NULL│                   │
└──────────────────┘                   │
                                       ▼
                        ┌──────────────────────────────────────────┐
                        │  PyDictKeysObject                         │
                        │                                          │
                        │  dk_log2_size: 3 (size=8)                │
                        │  dk_nentries: 3                          │
                        │  dk_usable: 2                            │
                        │                                          │
                        │  dk_indices (8 × 1 byte):                │
                        │  ┌──┬──┬──┬──┬──┬──┬──┬──┐              │
                        │  │-1│ 0│-1│ 1│-1│ 2│-1│-1│  (sparse)    │
                        │  └──┴──┴──┴──┴──┴──┴──┴──┘              │
                        │                                          │
                        │  dk_entries (dense):                     │
                        │  ┌────────────────────────────────┐      │
                        │  │[0] hash_a, key→"a", val→1     │      │
                        │  │[1] hash_b, key→"b", val→2     │      │
                        │  │[2] hash_c, key→"c", val→3     │      │
                        │  │[3] (empty)                     │      │
                        │  │[4] (empty)                     │      │
                        │  └────────────────────────────────┘      │
                        └──────────────────────────────────────────┘
```

---

## 3.10 Size of Empty Dict

```python
import sys
sys.getsizeof({})  # 64 bytes (Python 3.11+)
```

An empty dict still has:
- PyDictObject struct: ~48 bytes
- Points to a shared "empty keys" singleton (no separate allocation)
- First insertion triggers allocation of a real PyDictKeysObject

---

## 3.11 Interview Questions — Part 3

**Q1**: What are the two types of dict table layouts in CPython?
**A**: Combined table (normal dict — keys and values in same entries array) and split table (instance __dict__ — keys shared, values in separate array).

**Q2**: How does key-sharing work for class instances?
**A**: All instances of a class share one PyDictKeysObject (containing the attribute names). Each instance only stores its own values array. This saves ~75% memory for classes with consistent attributes.

**Q3**: What is `ma_version_tag`?
**A**: A unique version counter incremented on every dict modification. Used for optimization (e.g., cached LOAD_ATTR can detect if a dict changed without comparing contents).

**Q4**: How big is each index entry in the hash table?
**A**: 1, 2, 4, or 8 bytes depending on table size. For small dicts (≤128 slots), just 1 byte per slot.

**Q5**: What does `dk_usable` track?
**A**: How many more entries can be added before resize is triggered. Starts at `table_size * 2/3`, decremented on each insert.

**Q6**: Why does CPython cache the hash value in each entry?
**A**: To avoid recomputing hash during probing and resize. Comparing hashes first (integer comparison) is much faster than comparing keys (which may call `__eq__`).
