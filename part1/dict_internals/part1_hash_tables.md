# Part 1 — Hash Tables: Why They Exist

## 1.1 The Fundamental Problem

We need a data structure that supports:
- **Lookup by key**: given a key, find its associated value
- **Insert**: add a new key-value pair
- **Delete**: remove a key-value pair
- All in **O(1)** average time

No array or linked list can deliver this. Let's prove why.

---

## 1.2 Why Arrays Fail

### Attempt 1: Unsorted Array of Pairs

```
[(key0, val0), (key1, val1), (key2, val2), ...]

Lookup: scan every pair checking if key matches → O(n)
Insert: append to end → O(1)
Delete: find + shift → O(n)
```

Lookup is O(n) — unacceptable for a dictionary.

### Attempt 2: Sorted Array + Binary Search

```
[(key_a, val_a), (key_b, val_b), (key_c, val_c), ...]  (sorted by key)

Lookup: binary search → O(log n)
Insert: find position + shift elements → O(n)
Delete: find + shift → O(n)
```

Better lookup (O(log n)), but insertion is O(n) due to shifting. Still not O(1).

### Attempt 3: Direct Addressing (Index = Key)

```
If keys are integers 0..N-1:
array[key] = value

Lookup: array[key] → O(1) ✓
Insert: array[key] = value → O(1) ✓
Delete: array[key] = EMPTY → O(1) ✓
```

This works! But only if:
- Keys are non-negative integers
- Key range is small (we need an array of size max_key)
- Memory: O(max_key), even if only a few keys are used

For `d = {"hello": 1, "world": 2}`, this fails — keys are strings, not small integers.

---

## 1.3 Why Linked Lists Fail

```
head → (key0, val0) → (key1, val1) → (key2, val2) → NULL

Lookup: traverse from head comparing keys → O(n)
Insert at head: O(1) (but no duplicate check without O(n) search)
Delete: find node + relink → O(n)
```

Same O(n) lookup problem. Even skip lists only get O(log n).

---

## 1.4 Why Trees Almost Work

Balanced BST (red-black tree, AVL):
```
Lookup: O(log n)
Insert: O(log n)
Delete: O(log n)
```

This is what C++ `std::map` and Java `TreeMap` use. O(log n) is good but not O(1).

For Python's design goals (fast attribute lookup, fast keyword access), O(1) is essential.

---

## 1.5 The Hash Table Insight

**Key idea**: convert any key into an array index using a **hash function**.

```
hash("hello") → some large integer → mod table_size → index in array

Example:
hash("hello") = 2314058222102390712
table_size = 8
index = 2314058222102390712 % 8 = 0

Store ("hello", value) at array[0]
```

```
┌───────┐      hash()      ┌────────┐     % size    ┌─────────────┐
│"hello"│ ───────────────→  │ 231405 │ ────────────→ │ index = 0   │
└───────┘                   └────────┘               └─────────────┘
                                                           │
                                                           ▼
                                              ┌──┬──┬──┬──┬──┬──┬──┬──┐
                                              │HI│  │  │  │  │  │  │  │
                                              └──┴──┴──┴──┴──┴──┴──┴──┘
                                               [0] [1] [2] [3] [4] [5] [6] [7]
```

Now:
- **Lookup**: hash(key) → index → check array[index] → O(1)
- **Insert**: hash(key) → index → write array[index] → O(1)
- **Delete**: hash(key) → index → clear array[index] → O(1)

---

## 1.6 The Collision Problem

Two different keys can hash to the same index:

```
hash("hello") % 8 = 0
hash("world") % 8 = 0    ← COLLISION!
```

Both want slot 0. We need a **collision resolution** strategy.

### Strategy 1: Chaining (Separate Chaining)

Each slot holds a linked list of all entries that hash there:

```
[0] → ("hello", 1) → ("world", 2) → NULL
[1] → NULL
[2] → ("python", 3) → NULL
[3] → NULL
...
```

- Lookup: hash → index → traverse chain → O(1 + chain_length)
- If chains are short (good hash, low load): effective O(1)
- If chains are long (bad hash, high load): degrades to O(n)

Used by: Java HashMap, Go maps.

### Strategy 2: Open Addressing (Probing)

All entries stored in the array itself. On collision, **probe** for another empty slot:

```
Insert "hello" → index 0 → slot empty → store here
Insert "world" → index 0 → OCCUPIED → probe next slot → index 1 → store here

[0]: ("hello", 1)
[1]: ("world", 2)    ← placed here due to collision
[2]: empty
[3]: empty
...
```

Probe strategies:
- **Linear probing**: try index+1, index+2, index+3, ...
- **Quadratic probing**: try index+1, index+4, index+9, ...
- **Double hashing**: use a second hash function for step size
- **CPython's approach**: perturbation-based probing (explained in Part 4)

Used by: CPython dicts, Rust HashMap, Swiss Tables.

**CPython uses open addressing** because:
1. Better cache locality (all data in one array, no pointer chasing)
2. Less memory overhead (no linked list nodes)
3. Better performance for small tables (most Python dicts are small)

---

## 1.7 Load Factor

The **load factor** α = n/m where:
- n = number of stored entries
- m = number of slots (table size)

```
Load factor determines collision probability:

α = 0.0:  empty table, no collisions
α = 0.5:  half full, few collisions
α = 0.66: CPython's threshold → RESIZE!
α = 0.75: Java HashMap's threshold
α = 1.0:  completely full (impossible with open addressing)
```

CPython resizes when load factor reaches **2/3** (~66.7%):
- Below 2/3: most lookups find the key in 1-2 probes
- Above 2/3: collision chains grow rapidly
- At 2/3: good balance between memory usage and performance

### Why 2/3 Specifically?

Analysis of expected probe length for open addressing:

```
Expected probes for successful lookup:   -ln(1-α) / α
Expected probes for unsuccessful lookup: 1 / (1-α)

At α = 2/3:
  Successful:   -ln(1/3) / (2/3) = 1.099 / 0.667 ≈ 1.65 probes
  Unsuccessful: 1 / (1/3) = 3.0 probes

At α = 3/4:
  Successful:   ≈ 1.85 probes
  Unsuccessful: 4.0 probes

At α = 9/10:
  Successful:   ≈ 2.56 probes
  Unsuccessful: 10.0 probes
```

2/3 gives excellent performance (< 2 probes average for hits) while using 66% of allocated memory.

---

## 1.8 Buckets and Slots

In CPython's hash table:

```
A "slot" or "bucket" is one position in the hash table array.
Each slot can be in one of three states:

1. EMPTY   — never been used (search terminates here)
2. ACTIVE  — contains a live key-value pair
3. DELETED — previously active, now removed (dummy/tombstone)

┌────────┬────────┬────────┬────────┬────────┬────────┬────────┬────────┐
│ACTIVE  │ EMPTY  │DELETED │ACTIVE  │ EMPTY  │ACTIVE  │ EMPTY  │ EMPTY  │
│"hello" │        │(dummy) │"world" │        │"foo"   │        │        │
│  → 1   │        │        │  → 2   │        │  → 3   │        │        │
└────────┴────────┴────────┴────────┴────────┴────────┴────────┴────────┘
  [0]      [1]      [2]      [3]      [4]      [5]      [6]      [7]
```

Why we need DELETED (not just EMPTY):
- If we delete "hello" at slot 0 and set it to EMPTY
- Then lookup "world" starts at slot 0, finds EMPTY, concludes "world" doesn't exist
- But "world" is at slot 3! We must NOT stop searching at a formerly-occupied slot
- DELETED means "keep probing, something was here before"

---

## 1.9 The Hash Table Contract

For a correct hash table:
1. `hash(key)` must be **deterministic**: same key always gives same hash
2. If `a == b`, then `hash(a) == hash(b)` (equal objects have equal hashes)
3. If `hash(a) != hash(b)`, then `a != b` (contrapositive of #2)
4. NOT required: if `hash(a) == hash(b)`, then `a == b` (collisions are allowed!)

Rule 2 is critical. If violated, you can insert a key but never find it again:
```python
# Hypothetical broken hash:
hash(key_at_insert) = 5 → stored at slot 5
hash(key_at_lookup) = 7 → looks at slot 7 → not found!
```

---

## 1.10 Why Hash Tables are O(1) Average

**Expected behavior with good hash and α < 2/3:**

- Hash computation: O(1) for fixed-size keys (O(k) for strings of length k)
- Index calculation: O(1)
- Average probes before finding/inserting: ≈ 1.5 (with α = 2/3)
- Each probe: O(1) (array access)

Total: O(1) amortized average.

**Worst case**: O(n) — if all keys hash to same slot (degenerate hash). 
This is why hash function quality matters enormously.

---

## 1.11 Memory Layout Intuition

```
Traditional hash table (like Java):
┌──────────────────────────────────────────────────┐
│ slot[0]: (hash, key_ptr, val_ptr) or EMPTY       │
│ slot[1]: (hash, key_ptr, val_ptr) or EMPTY       │
│ slot[2]: (hash, key_ptr, val_ptr) or EMPTY       │
│ ...                                              │
│ slot[m-1]: (hash, key_ptr, val_ptr) or EMPTY     │
└──────────────────────────────────────────────────┘
Sparse! Many EMPTY slots wasting space.

Modern CPython (3.6+):
┌─────────────────────────────┐
│ Index table (sparse, small) │  ← just indices (1-8 bytes each)
│ [3, -, 0, -, 1, -, 2, -]   │
└─────────────────────────────┘
          │
          ▼
┌─────────────────────────────┐
│ Entries array (dense)       │  ← packed, no holes
│ [0]: (hash, key, val)       │
│ [1]: (hash, key, val)       │
│ [2]: (hash, key, val)       │
│ [3]: (hash, key, val)       │
└─────────────────────────────┘
```

The modern layout (Part 6) saves ~30% memory and preserves insertion order.

---

## 1.12 Interview Questions — Part 1

**Q1**: Why can't you use a sorted array for O(1) lookup?
**A**: Binary search gives O(log n), not O(1). And insertion requires O(n) shifting.

**Q2**: What is a hash collision?
**A**: When two different keys produce the same hash table index: `hash(a) % size == hash(b) % size`.

**Q3**: What are the two main collision resolution strategies?
**A**: Chaining (linked lists at each bucket) and open addressing (probing for next free slot). CPython uses open addressing.

**Q4**: What is the load factor and why does CPython use 2/3?
**A**: Load factor = entries/slots. At 2/3, average lookup takes ~1.5 probes — good balance of speed vs memory. Higher causes too many collisions; lower wastes memory.

**Q5**: Why does CPython use open addressing instead of chaining?
**A**: Better cache locality (contiguous memory), less memory overhead (no linked list nodes), and most Python dicts are small where probing is very fast.

**Q6**: What is a tombstone/dummy entry?
**A**: A slot marked as "deleted but not empty". Necessary so that probe chains past this slot still work correctly. Without it, deleting an entry could break lookups for other entries that probed past it.

**Q7**: What is the worst-case time complexity of a hash table lookup?
**A**: O(n) — when all keys hash to the same slot, creating a long probe chain. This is why hash quality and collision resistance matter.
