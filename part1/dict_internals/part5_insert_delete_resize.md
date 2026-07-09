# Part 5 — Insert, Delete, Resize

## 5.1 Insert Operation

### When you do `d["key"] = value`:

```
1. Compute hash(key)
2. Lookup key using probe algorithm (Part 4)
3. If found (existing key):
   - Replace old value with new value
   - Py_DECREF(old_value), Py_INCREF(new_value)
   - Increment ma_version_tag
4. If not found (new key):
   - Check if resize needed (dk_usable == 0?)
   - If resize needed: rebuild table with larger size
   - Find the EMPTY or DUMMY slot from the probe sequence
   - Store in dk_entries[dk_nentries]: (hash, key, value)
   - Set dk_indices[slot] = dk_nentries
   - dk_nentries += 1
   - dk_usable -= 1
   - ma_used += 1
   - Increment ma_version_tag
```

### Memory Diagram — Inserting "d" into {"a":1, "b":2, "c":3}:

```
BEFORE: d = {"a":1, "b":2, "c":3}
dk_indices: [-1, 0, -1, 1, -1, 2, -1, -1]   (table size 8)
dk_entries: [(h_a,"a",1), (h_b,"b",2), (h_c,"c",3), _, _]
dk_nentries = 3, dk_usable = 2, ma_used = 3

INSERT d["d"] = 4:
  hash("d") & 7 = 6  (example)
  dk_indices[6] is EMPTY → insert here!

AFTER:
dk_indices: [-1, 0, -1, 1, -1, 2, 3, -1]    ← slot 6 now = 3
dk_entries: [(h_a,"a",1), (h_b,"b",2), (h_c,"c",3), (h_d,"d",4), _]
dk_nentries = 4, dk_usable = 1, ma_used = 4
```

---

## 5.2 Delete Operation

### When you do `del d["key"]`:

```
1. Lookup key (full probe to find it)
2. If not found: raise KeyError
3. If found at dk_entries[ix]:
   - Set dk_indices[slot] = DKIX_DUMMY  (tombstone)
   - Set dk_entries[ix].me_key = NULL
   - Set dk_entries[ix].me_value = NULL
   - Py_DECREF(old_key), Py_DECREF(old_value)
   - ma_used -= 1
   - Increment ma_version_tag
   
   NOTE: dk_nentries does NOT decrease!
   The entry slot becomes a "hole" in the entries array.
```

### Memory Diagram — Deleting "b" from {"a":1, "b":2, "c":3, "d":4}:

```
BEFORE:
dk_indices: [-1, 0, -1, 1, -1, 2, 3, -1]
dk_entries: [(h_a,"a",1), (h_b,"b",2), (h_c,"c",3), (h_d,"d",4)]
ma_used = 4

DELETE d["b"]:
  Lookup "b" → found at dk_indices[3]=1, entry dk_entries[1]
  dk_indices[3] = DKIX_DUMMY
  dk_entries[1] = (hash_b, NULL, NULL)  ← hole!
  ma_used = 3

AFTER:
dk_indices: [-1, 0, -1, -2, -1, 2, 3, -1]   ← slot 3 is now DUMMY
dk_entries: [(h_a,"a",1), (HOLE), (h_c,"c",3), (h_d,"d",4)]
ma_used = 3, dk_nentries still = 4 (entry hole not reclaimed yet!)
```

---

## 5.3 Resize (Growth) Strategy

### When Does Resize Happen?

Resize triggers when `dk_usable` reaches 0 (load factor hits 2/3):

```
table_size = 8
max_entries = 8 * 2/3 = 5 (rounded down)
After 5 insertions → dk_usable = 0 → next insert triggers resize
```

### Growth Factor

CPython doubles (or quadruples for small dicts) the table size:

```c
// Simplified resize logic:
if (ma_used > 50000)
    new_size = old_size * 2;       // Large dicts: double
else
    new_size = old_size * 4;       // Small dicts: quadruple (aggressive)
    
// But actually, CPython picks the smallest power of 2 that holds:
//   new_size >= 4 * ma_used / 3    (ensures load factor ≤ 2/3 after resize)
```

Minimum table size is 8.

### Growth Sequence (typical):

```
Table size:  8 → 16 → 32 → 64 → 128 → 256 → 512 → 1024 → ...
Max entries: 5 → 10 → 21 → 42 →  85 → 170 → 341 →  682 → ...
```

### What Happens During Resize:

```
1. Allocate new PyDictKeysObject with larger table
2. For each ACTIVE entry in old dk_entries:
   a. Compute new index: hash & new_mask
   b. Probe in new table to find empty slot
   c. Copy entry to new dk_entries (in order!)
   d. Set new dk_indices[slot] = new_entry_index
3. Free old PyDictKeysObject
4. Update ma_keys to point to new one
```

```
BEFORE RESIZE (table_size=8, 5 entries, FULL):
dk_indices: [2, 0, -1, 1, -2, 3, 4, -1]
dk_entries: [e0, e1, e2, e3, e4]

AFTER RESIZE (table_size=16):
dk_indices: [-1, 0, -1, -1, 1, -1, -1, 2, -1, -1, 3, -1, -1, 4, -1, -1]
dk_entries: [e0, e1, e2, e3, e4]  ← same entries, reinserted at new positions
                                     all dummies eliminated!
dk_usable = 16 * 2/3 - 5 = 5 more slots available
```

Key observations:
- All DUMMY entries are eliminated during resize
- Entry ORDER is preserved (insertion order maintained!)
- Entries array is compacted (holes removed)
- All probe chains are recalculated from scratch

---

## 5.4 Shrink Strategy

Dicts can also shrink when many entries are deleted:

```python
d = {i: i for i in range(1000)}  # Large table
for i in range(900):
    del d[i]                       # Delete most entries
# Table is now mostly empty/dummies → shrink on next resize trigger
```

CPython shrinks (or rebuilds at same size) when:
- Too many dummy entries accumulate
- The ratio of active entries to table size is too low
- A resize is triggered but the effective data fits in a smaller table

The shrink condition:
```c
// If the number of active entries * 4 < table_size:
//   resize to a smaller power of 2
if (mp->ma_used * 4 < dk_size(mp->ma_keys))
    new_size = next_power_of_2(mp->ma_used * 2);  // Shrink!
```

---

## 5.5 The Resize Rebuilds Everything

```
BEFORE (many deletions, table is messy):
Table size: 64
dk_indices: lots of DUMMY entries scattered around
dk_entries: [(h,k,v), HOLE, (h,k,v), HOLE, HOLE, (h,k,v), ...]
ma_used = 10 (only 10 active entries in 64-slot table!)

Resize decision: 10 * 4 < 64? → 40 < 64? YES → shrink!
new_size = next_power_of_2(10 * 2) = 32

AFTER REBUILD:
Table size: 32
dk_indices: [freshly computed, no dummies]
dk_entries: [e0, e1, e2, ..., e9]  ← compact, no holes
dk_usable = 32 * 2/3 - 10 = 11
```

---

## 5.6 Insertion Order Preservation

Since Python 3.7 (implementation detail in 3.6), dicts maintain insertion order. This works because:

```
dk_entries is a DENSE array — entries are stored in insertion order:
  entries[0] = first key-value inserted
  entries[1] = second key-value inserted
  entries[2] = third key-value inserted
  ...

dk_indices maps hash slots → entry indices:
  indices[hash(key1) & mask] = 0
  indices[hash(key2) & mask] = 1
  indices[hash(key3) & mask] = 2

Iterating over d.keys() = iterating entries[0], entries[1], entries[2], ...
  = insertion order!
```

---

## 5.7 Amortized O(1) Insert

Same argument as list.append():
- Most inserts: just write to next entries slot + update index → O(1)
- Occasional resize: rebuild entire table → O(n)
- With doubling growth: total work for n inserts = O(n)
- Per insert: **amortized O(1)**

---

## 5.8 Memory Diagrams — Full Lifecycle

```
═══ Step 1: d = {} ═══
PyDictObject: ma_used=0, ma_keys→(empty shared singleton)

═══ Step 2: d["a"] = 1 ═══
Allocates real PyDictKeysObject (table_size=8):
dk_indices: [-1,-1,-1,-1,-1,-1,-1,-1]  → after insert:
dk_indices: [-1, 0,-1,-1,-1,-1,-1,-1]   (assuming hash("a")&7=1)
dk_entries: [(h_a, "a", 1)]
ma_used=1, dk_nentries=1, dk_usable=4

═══ Step 3: d["b"]=2, d["c"]=3, d["d"]=4, d["e"]=5 ═══
dk_indices: [4, 0, 1, 2, 3, -1, -1, -1]  (5 entries, dk_usable=0)
dk_entries: [(h_a,"a",1),(h_b,"b",2),(h_c,"c",3),(h_d,"d",4),(h_e,"e",5)]
ma_used=5 → TABLE FULL (usable=0)

═══ Step 4: d["f"] = 6 → TRIGGERS RESIZE ═══
New table_size = 16 (or 32 for small dict aggressive growth)
All entries reinserted into new, larger table
dk_indices: [16 slots, freshly computed]
dk_entries: [e0,e1,e2,e3,e4,e5]  (6 entries in insertion order)
dk_usable = 16*2/3 - 6 = 4

═══ Step 5: del d["c"], del d["d"] ═══
dk_indices: [..., DUMMY, ..., DUMMY, ...]
dk_entries: [..., HOLE, ..., HOLE, ...]
ma_used = 4 (but dk_nentries still = 6, holes in entries)

═══ Step 6: Next resize → holes compacted ═══
Entries reordered to: [a, b, e, f] (preserving insertion order of LIVING entries)
```

---

## 5.9 The `dict.pop()` Optimization

```python
val = d.pop("key")  # Delete and return value
```

This is slightly more efficient than `val = d["key"]; del d["key"]` because it does ONE lookup instead of two.

---

## 5.10 Interview Questions — Part 5

**Q1**: What triggers a dict resize?
**A**: When dk_usable reaches 0 (load factor hits 2/3). The next insertion triggers a rebuild to a larger table.

**Q2**: What is the growth factor for dicts?
**A**: For small dicts (< 50k entries), 4×. For large dicts, 2×. Always a power of 2.

**Q3**: What happens to dummy entries during resize?
**A**: They're eliminated. Resize rebuilds the table from scratch using only active entries. All probe chains are clean afterward.

**Q4**: Does CPython ever shrink a dict?
**A**: Yes. If active entries drop below 1/4 of table size, the next modification may trigger a shrink to a smaller power-of-2 table.

**Q5**: Why does resize preserve insertion order?
**A**: Entries are stored in a dense array in insertion order. During resize, entries are reinserted in the same order into the new index table, maintaining the sequence.

**Q6**: Is `d["key"] = value` O(1)?
**A**: Amortized O(1). Occasional O(n) resizes are amortized over all insertions.

**Q7**: What happens when you delete a key? Does the entries array compact?
**A**: No. Deletion creates a "hole" in the entries array (key=NULL, value=NULL). The hole is only eliminated during the next resize/rebuild.
