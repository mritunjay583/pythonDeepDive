# Part 4 — Lookup Algorithm

## 4.1 The Core Lookup: Step by Step

When you write `d["hello"]`, CPython executes this algorithm:

```
1. Compute hash:      h = hash("hello")
2. Compute index:     i = h & mask          (mask = table_size - 1)
3. Read index table:  idx = dk_indices[i]
4. If idx == EMPTY:   → KeyError! Key not in dict.
5. If idx == DUMMY:   → Skip, go to probe step.
6. Read entry:        entry = dk_entries[idx]
7. Compare hash:      if entry.me_hash == h:
8. Compare key:          if entry.me_key == key or entry.me_key equals key:
9.                          → FOUND! Return entry.me_value
10. Probe:            i = next_probe(i, h)    → go to step 3
```

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        LOOKUP ALGORITHM                                   │
│                                                                           │
│  hash("hello") = 0x1A3F8B2C...                                          │
│  mask = 7 (table size 8)                                                │
│  initial index = hash & mask = 4                                         │
│                                                                           │
│  dk_indices:                                                             │
│  ┌──┬──┬──┬──┬──┬──┬──┬──┐                                             │
│  │-1│ 2│-1│ 0│ 1│-1│-1│-1│                                             │
│  └──┴──┴──┴──┴──┴──┴──┴──┘                                             │
│   [0] [1] [2] [3] [4] [5] [6] [7]                                      │
│                      ↑                                                   │
│                   index=4, dk_indices[4]=1                                │
│                                                                           │
│  dk_entries[1]:                                                          │
│    me_hash = 0x1A3F8B2C...  ← matches!                                  │
│    me_key  = "hello"        ← matches!                                   │
│    me_value = <the value>   ← FOUND!                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4.2 The Probe Sequence (Perturbation)

When a collision occurs (slot occupied by different key), CPython probes the next slot using:

```c
// The probing algorithm:
perturb = hash;         // Start with full hash value
i = hash & mask;        // Initial index

// On collision, compute next index:
perturb >>= 5;          // Shift perturb right by 5 bits
i = (5 * i + perturb + 1) & mask;   // Next probe index
```

This continues until an EMPTY slot is found (lookup miss) or the key is found (lookup hit).

### Why This Formula?

The probe sequence for a given hash visits ALL slots in the table before repeating:

```
Sequence: i₀, i₁, i₂, i₃, ...

i₀ = hash & mask                           (uses low bits)
i₁ = (5*i₀ + (hash>>5) + 1) & mask        (mixes in next 5 bits)
i₂ = (5*i₁ + (hash>>10) + 1) & mask       (mixes in next 5 bits)
...

As perturb → 0 (after enough shifts):
i_n = (5*i_{n-1} + 1) & mask               (becomes linear recurrence)
```

**Properties:**
1. **Uses all bits of hash**: The perturb shifts feed higher hash bits into the probe
2. **Visits all slots**: The formula `5*i + 1` with power-of-2 table size generates a full permutation
3. **No clustering**: Unlike linear probing, similar initial indices diverge quickly
4. **Better than quadratic**: Distributes probes more uniformly

### Example Probe Sequence

```
hash = 0x1A3F8B2C4D5E6F70
mask = 7 (table size 8)

perturb = 0x1A3F8B2C4D5E6F70
i₀ = 0x70 & 7 = 0

Collision at slot 0:
  perturb >>= 5 → 0x00D1FC4596...
  i₁ = (5*0 + 0x00D1FC... + 1) & 7 = ?   (some slot 0-7)

Collision again:
  perturb >>= 5 → 0x00068FE2...
  i₂ = (5*i₁ + 0x00068F... + 1) & 7 = ?  (different slot)

... continues until found or EMPTY ...
```

---

## 4.3 Why Two-Step Comparison (Hash Then Key)

```c
// Step 1: Compare hashes (FAST — integer comparison)
if (entry->me_hash == hash) {
    // Step 2: Compare keys (SLOW — may call __eq__)
    if (entry->me_key == key ||    // Identity check first (O(1))
        PyObject_RichCompareBool(entry->me_key, key, Py_EQ)) {
        // FOUND!
    }
}
```

Why this order?

1. **Hash comparison is O(1)**: Just compare two integers. If hashes differ, keys CANNOT be equal (by hash contract). Skip expensive key comparison.

2. **Identity check (`is`)**: If the key pointer is the exact same object, they're definitely equal. No need for `__eq__`. This is common for interned strings and small integers.

3. **Full equality (`==`)**: Only called when hashes match but pointers differ. For strings, this is O(n) character comparison.

```
Hash mismatch:     ~1 cycle (integer compare) → SKIP
Hash match + is:   ~2 cycles (int compare + pointer compare) → FOUND
Hash match + ==:   O(key_length) → compare characters/values
```

In practice, >90% of probes terminate at step 1 (hash mismatch), making lookup very fast.

---

## 4.4 Open Addressing vs Chaining

CPython chose **open addressing** (probing) over **chaining** (linked lists):

```
CHAINING:
┌──────┐    ┌──────────┐    ┌──────────┐
│slot 0│───→│key1, val1│───→│key2, val2│───→ NULL
├──────┤    └──────────┘    └──────────┘
│slot 1│───→ NULL
├──────┤    ┌──────────┐
│slot 2│───→│key3, val3│───→ NULL
└──────┘    └──────────┘

Problems:
- Each node is a separate allocation (malloc overhead)
- Pointer chasing → cache misses
- Extra 8 bytes per entry (next pointer)

OPEN ADDRESSING (CPython):
┌──────────────────────────────────────────────────┐
│idx[0]│idx[1]│idx[2]│idx[3]│idx[4]│idx[5]│idx[6]│idx[7]│
└──────────────────────────────────────────────────┘
│entry[0]: hash, key, val │
│entry[1]: hash, key, val │
│entry[2]: hash, key, val │  ← contiguous memory!
└─────────────────────────┘

Advantages:
- All data in contiguous arrays → excellent cache locality
- No per-entry pointer overhead
- No separate allocations per entry
- Predictable memory access patterns
```

---

## 4.5 Deleted Entries: The Dummy Problem

When an entry is deleted, we can't just mark the index slot as EMPTY. Why?

```
Scenario:
1. Insert "A" at slot 3
2. Insert "B" → collision at slot 3 → probes to slot 5
3. Delete "A" (mark slot 3 as EMPTY)
4. Lookup "B" → hash("B") → slot 3 → EMPTY → "B not found"!
   BUT "B" IS AT SLOT 5! Lookup is BROKEN!
```

Solution: mark deleted slots as **DUMMY** (tombstone):
```
DUMMY means: "something was here, keep probing"
EMPTY means: "nothing was ever here, stop probing"

After deleting "A":
slot 3 = DUMMY (not EMPTY!)
Lookup "B" → slot 3 → DUMMY → keep probing → slot 5 → FOUND!
```

```c
// In dk_indices:
#define DKIX_EMPTY  (-1)    // Never used → terminate search
#define DKIX_DUMMY  (-2)    // Was used, now deleted → keep probing
```

### The Problem with Too Many Dummies

Dummies accumulate over time with many insert/delete cycles:
```
dk_indices: [DUMMY, DUMMY, 0, DUMMY, DUMMY, 1, DUMMY, 2]
```

Every lookup must probe past all these dummies. Performance degrades!

**Solution**: When too many dummies accumulate, CPython does a "resize" to the SAME size — this rebuilds the table, eliminating all dummies:
```
Resize-in-place:
Before: [DUMMY, DUMMY, 0, DUMMY, DUMMY, 1, DUMMY, 2]  (5 dummies!)
After:  [0, -1, 1, -1, 2, -1, -1, -1]                 (0 dummies!)
```

---

## 4.6 The Lookup Function in CPython Source

```c
// Simplified from Objects/dictobject.c
static Py_ssize_t
_Py_dict_lookup(PyDictObject *mp, PyObject *key, Py_hash_t hash, PyObject **value_addr)
{
    PyDictKeysObject *dk = mp->ma_keys;
    size_t mask = DK_MASK(dk);          // table_size - 1
    size_t perturb = hash;
    size_t i = hash & mask;             // Initial index
    
    for (;;) {
        Py_ssize_t ix = dk_get_index(dk, i);  // Read from dk_indices
        
        if (ix == DKIX_EMPTY) {
            // Slot never used → key not in dict
            *value_addr = NULL;
            return DKIX_EMPTY;
        }
        
        if (ix >= 0) {
            // Active entry — check if it matches
            PyDictKeyEntry *ep = DK_ENTRIES(dk) + ix;
            if (ep->me_hash == hash) {
                PyObject *startkey = ep->me_key;
                if (startkey == key) {
                    // Identity match!
                    *value_addr = ep->me_value;
                    return ix;
                }
                if (PyUnicode_CheckExact(startkey) && PyUnicode_CheckExact(key)) {
                    // Fast string comparison
                    if (_PyUnicode_EQ(startkey, key)) {
                        *value_addr = ep->me_value;
                        return ix;
                    }
                } else {
                    // General equality comparison
                    int cmp = PyObject_RichCompareBool(startkey, key, Py_EQ);
                    if (cmp > 0) {
                        *value_addr = ep->me_value;
                        return ix;
                    }
                }
            }
        }
        // ix == DKIX_DUMMY or hash/key didn't match → probe next
        perturb >>= PERTURB_SHIFT;  // PERTURB_SHIFT = 5
        i = (i * 5 + perturb + 1) & mask;
    }
}
```

---

## 4.7 Why Lookup is O(1) Average

With load factor α = 2/3:

**Expected number of probes:**
- Successful lookup: `1/(1-α) * ln(1/(1-α))` ≈ 1.65 probes
- Unsuccessful lookup: `1/(1-α)` = 3 probes

In practice, most lookups in CPython resolve in **1 or 2 probes**:
- First probe: check initial slot (often correct)
- If collision: ~1 more probe on average

**Proof sketch (successful lookup):**

The probability that a probe finds an occupied slot = α = 2/3.
Expected probes = 1 + α + α² + α³ + ... = 1/(1-α) = 3 for unsuccessful.
For successful (item known to exist), the expected probe count is the average over all insertion orders, giving the harmonic formula.

**Why O(1) and not O(n)?**
- Hash function distributes keys uniformly → collisions are rare
- Load factor kept below 2/3 → short probe chains
- Probe sequence covers the whole table → always terminates
- As long as the hash function is good, expected probes stay constant regardless of n

---

## 4.8 Worst Case: O(n)

If ALL keys hash to the same slot (degenerate hash function), every lookup probes through ALL entries:

```python
# Hypothetical worst case:
class BadHash:
    def __hash__(self): return 0  # Everything hashes to 0!

# All entries probe from slot 0:
d = {BadHash(): i for i in range(1000)}
# Lookup probes through all 1000 entries: O(n)!
```

This is prevented by:
1. SipHash producing uniformly distributed hashes
2. Hash randomization preventing attacker-crafted collisions
3. Load factor cap at 2/3

---

## 4.9 The Complete Probe Sequence Visualization

```python
d = {}
# Table size = 8, mask = 7

# Insert "apple" (hash=5):  slot 5 → EMPTY → store at entries[0], indices[5]=0
# Insert "banana" (hash=3): slot 3 → EMPTY → store at entries[1], indices[3]=1
# Insert "cherry" (hash=5): slot 5 → OCCUPIED → probe:
#   perturb = hash >> 5, i = (5*5 + perturb + 1) & 7 = ...
#   → finds empty slot → store at entries[2], indices[new_slot]=2

dk_indices: [-1, -1, -1, 1, -1, 0, 2, -1]   (example positions)
dk_entries: [("apple",v1), ("banana",v2), ("cherry",v3)]

Lookup "cherry":
  hash("cherry") & 7 = 5
  indices[5] = 0 → entries[0] = ("apple", ...) → hash match? Maybe. Key match? No.
  Probe: next index → indices[6] = 2 → entries[2] = ("cherry", ...) → FOUND!
```

---

## 4.10 Interview Questions — Part 4

**Q1**: Describe CPython's probe sequence formula.
**A**: `i = (5*i + perturb + 1) & mask` where perturb starts as the full hash value and shifts right by 5 each probe. This uses all hash bits and generates a full permutation of the table.

**Q2**: Why does CPython compare hashes before comparing keys?
**A**: Hash comparison is O(1) (integer compare). If hashes differ, keys can't be equal — avoids expensive `__eq__` calls. Filters out ~99% of false matches cheaply.

**Q3**: What is a dummy/tombstone entry?
**A**: A slot marker meaning "was occupied, now deleted — keep probing." Without it, deleting an entry could break probe chains for other entries that were inserted after it.

**Q4**: Why is open addressing better than chaining for CPython?
**A**: Better cache locality (contiguous arrays vs pointer chasing), lower memory overhead (no list nodes), and better performance for small tables (most Python dicts).

**Q5**: What's the expected number of probes for a successful lookup?
**A**: ~1.65 with load factor 2/3. Most lookups resolve in 1-2 probes.

**Q6**: When does dict lookup become O(n)?
**A**: When all keys hash to the same value (degenerate hash). SipHash and hash randomization make this practically impossible for attackers.

**Q7**: Why does the probe use `5*i + 1` instead of `i + 1` (linear probing)?
**A**: Linear probing causes "primary clustering" — consecutive filled slots create long chains. The `5*i + perturb + 1` formula distributes probes widely, avoiding clusters.
