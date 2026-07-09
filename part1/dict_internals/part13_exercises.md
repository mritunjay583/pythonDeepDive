# Part 13 — Exercises

## Section A: Memory Diagrams (10 Exercises)

### Exercise A1
Draw the complete memory layout for:
```python
d = {"name": "Alice", "age": 30}
```
Show: PyDictObject, PyDictKeysObject, dk_indices, dk_entries, and the key/value objects.

---

### Exercise A2
Draw the memory showing key-sharing for:
```python
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

p1 = Person("Alice", 30)
p2 = Person("Bob", 25)
```
Show how p1.__dict__ and p2.__dict__ share a PyDictKeysObject.

---

### Exercise A3
Draw the state of dk_indices and dk_entries after:
```python
d = {}
d["a"] = 1    # Step 1
d["b"] = 2    # Step 2
d["c"] = 3    # Step 3
del d["b"]    # Step 4
d["d"] = 4    # Step 5
```
Show the DUMMY entry after deletion.

---

### Exercise A4
Draw the memory layout for a set:
```python
s = {10, 20, 30}
```
Show the PySetObject with its smalltable.

---

### Exercise A5
Draw the difference between:
```python
a = {"x": [1, 2]}
b = a.copy()        # shallow
```
Show shared references for the inner list.

---

### Exercise A6
Draw what happens during resize when:
```python
d = {}
for i in range(6):
    d[chr(97+i)] = i  # a=0, b=1, c=2, d=3, e=4, f=5
```
Show the state before resize (5 entries, table full) and after (6 entries, new larger table).

---

### Exercise A7
Draw the compact dict layout showing:
- Sparse index table with 1-byte entries
- Dense entries array

For: `d = {"x": 10, "y": 20, "z": 30}`

---

### Exercise A8
Draw the memory for:
```python
d = {1: "a", True: "b"}
```
Show that `1` and `True` occupy the same slot (same hash, equal).

---

### Exercise A9
Draw the split table layout for:
```python
class Config:
    def __init__(self, host, port):
        self.host = host
        self.port = port

c1 = Config("localhost", 8080)
c2 = Config("remote", 443)
```
Show shared keys, separate values arrays.

---

### Exercise A10
Draw the set operations visually:
```python
a = {1, 2, 3, 4}
b = {3, 4, 5, 6}
# Show: a & b, a | b, a - b, a ^ b
```

---

## Section B: Hash Calculations (10 Exercises)

### Exercise B1
Given `hash("a") = 5` and table_size = 8, calculate the initial index.

**Answer**: index = 5 & 7 = 5

---

### Exercise B2
Given hash("x") = 12 and table_size = 8, calculate the initial index.

**Answer**: index = 12 & 7 = 4

---

### Exercise B3
If two keys both hash to index 3 in a table of size 8, calculate the first probe position using CPython's formula.

Given: i=3, perturb=hash (let's say hash=11 for the second key)
```
perturb >>= 5 → 11 >> 5 = 0
new_i = (5*3 + 0 + 1) & 7 = 16 & 7 = 0
```

**Answer**: Next probe is at index 0.

---

### Exercise B4
Calculate the table size needed for a dict with 100 entries.

**Answer**: Need table_size × 2/3 ≥ 100. table_size ≥ 150. Next power of 2: 256.

---

### Exercise B5
Calculate dk_usable for a fresh dict with table_size = 16.

**Answer**: USABLE_FRACTION(16) = 16 × 2 / 3 = 10. Can hold 10 entries before resize.

---

### Exercise B6
How many bytes does the dk_indices array use for a dict with table_size = 64?

**Answer**: 64 entries, table ≤ 128, so 1 byte each. Total: 64 bytes.

---

### Exercise B7
How many bytes does the dk_indices array use for a dict with table_size = 256?

**Answer**: 256 entries, table > 128 but ≤ 32768, so 2 bytes each. Total: 512 bytes.

---

### Exercise B8
Calculate total memory for dk_indices + dk_entries for dict with 50 entries (table_size = 128):

**Answer**:
- dk_indices: 128 × 1 byte = 128 bytes
- dk_entries: 50 × 24 bytes = 1200 bytes
- Total: 1328 bytes

---

### Exercise B9
Compare old-style (pre-3.6) vs compact layout memory for 50 entries, table_size=128:

**Answer**:
- Old: 128 × 24 = 3072 bytes
- New: 128 × 1 + 50 × 24 = 128 + 1200 = 1328 bytes
- Savings: (3072 - 1328) / 3072 = 56.8%

---

### Exercise B10
Calculate: after inserting keys with hashes 0, 8, 16 into table_size=8, where does each land?

**Answer**:
- hash=0: index = 0 & 7 = 0 → slot 0
- hash=8: index = 8 & 7 = 0 → collision! Probe: (5×0 + 8>>5 + 1) & 7 = (0+0+1)&7 = 1
- hash=16: index = 16 & 7 = 0 → collision! Probe: (5×0 + 16>>5 + 1) & 7 = (0+0+1)&7 = 1 → collision! Probe again: perturb>>5=0, (5×1 + 0 + 1) & 7 = 6
- Final positions: 0, 1, 6

---

## Section C: Probe Tracing (10 Exercises)

### Exercise C1
Trace the probe sequence for looking up a key with hash=20 in table_size=8 where indices are:
```
dk_indices = [-1, 0, -1, 1, 2, -1, -1, -1]
```

**Answer**:
- initial i = 20 & 7 = 4
- dk_indices[4] = 2 → check entries[2]
- If entry matches: FOUND at entries[2]
- If not: perturb=20>>5=0, next i = (5×4+0+1)&7 = 21&7 = 5
- dk_indices[5] = -1 → EMPTY → NOT FOUND

---

### Exercise C2
Trace insertion of key "x" (hash=13) into table_size=8, current state:
```
dk_indices = [-1, 0, -1, 1, -1, 2, -1, -1]
dk_nentries = 3
```

**Answer**:
- i = 13 & 7 = 5
- dk_indices[5] = 2 → check entries[2]. Key doesn't match.
- Probe: perturb=13>>5=0, i = (5×5+0+1)&7 = 26&7 = 2
- dk_indices[2] = -1 → EMPTY → insert here!
- dk_indices[2] = 3, dk_entries[3] = (13, "x", value)
- dk_nentries = 4

---

### Exercise C3
Trace deletion of key at dk_entries[1] (which hashes to index 3):
```
BEFORE: dk_indices = [-1, 0, -1, 1, 2, -1, -1, -1]
```

**Answer**:
- dk_indices[3] = -2 (DUMMY)
- dk_entries[1].me_key = NULL
- dk_entries[1].me_value = NULL
- ma_used -= 1
- AFTER: dk_indices = [-1, 0, -1, -2, 2, -1, -1, -1]

---

### Exercise C4
After the deletion in C3, trace lookup for a key with hash=3 that was originally at entries[2] (stored after the deleted entry):

**Answer**:
- i = 3 & 7 = 3
- dk_indices[3] = -2 (DUMMY) → keep probing!
- perturb = 3>>5 = 0, i = (5×3+0+1)&7 = 16&7 = 0
- dk_indices[0] = -1 → EMPTY → NOT FOUND

Wait — but entries[2] might hash to index 4 (dk_indices[4]=2). The probe would need to reach index 4. Let me recalculate: if the key hashes to 4 (not 3), lookup starts at index 4, finds entries[2] directly. The DUMMY at index 3 only affects lookups that start at or probe through index 3.

---

### Exercise C5
Calculate the probe sequence for hash=7 in table_size=8 (show first 5 positions):

**Answer**:
```
i₀ = 7 & 7 = 7
perturb = 7

perturb >>= 5 → 0
i₁ = (5×7 + 0 + 1) & 7 = 36 & 7 = 4

perturb >>= 5 → 0
i₂ = (5×4 + 0 + 1) & 7 = 21 & 7 = 5

i₃ = (5×5 + 0 + 1) & 7 = 26 & 7 = 2

i₄ = (5×2 + 0 + 1) & 7 = 11 & 7 = 3

Sequence: 7, 4, 5, 2, 3, ...
```

---

### Exercise C6-C10: Practice computing probe sequences for various hash values and table sizes. Use the formula:
```
perturb >>= 5
i = (5*i + perturb + 1) & mask
```
Try: hash=100 table=16, hash=0 table=8, hash=255 table=32, hash=42 table=8, hash=1000 table=64.

---

## Section D: Complexity Analysis (5 Exercises)

### Exercise D1
Explain why this is O(n²):
```python
items = get_large_list()
unique = []
for item in items:
    if item not in unique:  # O(n) membership test!
        unique.append(item)
```
**Fix**: Use a set for O(1) membership: `seen = set(); unique = [x for x in items if x not in seen and not seen.add(x)]`

---

### Exercise D2
What's the complexity of:
```python
common = [x for x in list_a if x in dict_b]
```
**Answer**: O(n) where n = len(list_a). Each `x in dict_b` is O(1).

Compare with:
```python
common = [x for x in list_a if x in list_b]  # O(n × m)!
```

---

### Exercise D3
Analyze:
```python
d = {}
for i in range(n):
    d[i] = i ** 2
```
**Answer**: n insertions × O(1) amortized each = O(n) total. Resize happens ~log₂(n) times, each O(current_size). Total resize cost: 8+16+32+...+n ≈ 2n = O(n).

---

### Exercise D4
What's the complexity of `dict(zip(keys, values))` for n pairs?
**Answer**: O(n) — iterates n pairs, each insertion O(1) amortized.

---

### Exercise D5
Analyze set intersection: `big_set & small_set` vs `small_set & big_set`.
**Answer**: Both are O(min(n,m)). CPython iterates the smaller set and checks membership in the larger. The `&` operator automatically picks the optimal direction.
