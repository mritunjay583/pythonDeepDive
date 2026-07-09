# Part 7 — Sets

## 7.1 Sets as "Dicts Without Values"

A Python `set` is implemented as a hash table that stores only keys (no values). It reuses the same concepts as `dict` but with a simpler structure.

```c
// Objects/setobject.c
typedef struct {
    PyObject_HEAD
    Py_ssize_t fill;            // Active + dummy entries
    Py_ssize_t used;            // Active entries only (len())
    Py_ssize_t mask;            // table_size - 1
    setentry *table;            // The hash table array
    Py_hash_t hash;             // Cached hash for frozenset (-1 if not computed)
    Py_ssize_t finger;          // Search finger for pop()
    setentry smalltable[PySet_MINSIZE];  // Inline small table (8 entries)
    PyObject *weakreflist;      // Weak reference support
} PySetObject;

typedef struct {
    PyObject *key;      // Pointer to the element
    Py_hash_t hash;     // Cached hash value
} setentry;
```

Key differences from dict:
- No values — just keys and hashes
- Uses the **old-style** sparse layout (not compact like dict 3.6+)
- Has an inline `smalltable` for optimization
- `frozenset` can cache its own hash value

---

## 7.2 Memory Layout

```python
s = {10, 20, 30}
```

```
PySetObject:
┌──────────────────────────────┐
│ ob_refcnt: 1                 │
│ ob_type: → PySet_Type        │
│ fill: 3                      │  (active + dummies)
│ used: 3                      │  (active only = len())
│ mask: 7                      │  (table_size - 1 = 8 - 1)
│ table: → smalltable          │  (points to inline table)
│ hash: -1                     │  (not computed for mutable set)
│ finger: 0                    │
│ smalltable:                  │  (inline, 8 entries)
│   [0]: (key→10, hash=10)    │
│   [1]: EMPTY                 │
│   [2]: (key→20, hash=20)    │ 
│   [3]: EMPTY                 │
│   [4]: (key→30, hash=30)    │
│   [5]: EMPTY                 │
│   [6]: EMPTY                 │
│   [7]: EMPTY                 │
└──────────────────────────────┘
```

For sets with ≤ 8 entries, the table is stored inline in the struct (no separate allocation). For larger sets, `table` points to a heap-allocated array.

---

## 7.3 Lookup, Insert, Delete

### Lookup (`x in s`):

```
1. h = hash(x)
2. i = h & mask
3. Check table[i]:
   - EMPTY → not in set (return False)
   - key matches (hash + equality) → in set (return True)
   - different key or DUMMY → probe next slot
4. Probe: same perturb algorithm as dict
```

### Insert (`s.add(x)`):

```
1. h = hash(x)
2. Probe for x:
   - If found: already exists, do nothing
   - If not found: insert at empty/dummy slot
3. Check load factor → resize if needed
```

### Delete (`s.remove(x)` / `s.discard(x)`):

```
1. Probe for x
2. If found: mark slot as DUMMY, used -= 1
3. If not found: 
   - remove() raises KeyError
   - discard() silently returns
```

---

## 7.4 Set Operations and Their Complexity

### Union: `a | b` or `a.union(b)`

```python
a = {1, 2, 3}
b = {3, 4, 5}
c = a | b  # {1, 2, 3, 4, 5}
```

Algorithm:
```
1. Create new set from the larger of a, b (copy all entries)
2. Insert each element from the smaller set
   - If already present: skip
   - If new: insert

Time: O(len(a) + len(b))
Space: O(len(a) + len(b))
```

### Intersection: `a & b` or `a.intersection(b)`

```python
a = {1, 2, 3, 4, 5}
b = {3, 4, 5, 6, 7}
c = a & b  # {3, 4, 5}
```

Algorithm:
```
1. Iterate over the SMALLER set
2. For each element: check if it's in the larger set (O(1) lookup)
3. If yes: add to result

Time: O(min(len(a), len(b)))
Space: O(min(len(a), len(b)))
```

### Difference: `a - b` or `a.difference(b)`

```python
a = {1, 2, 3, 4, 5}
b = {3, 4, 5, 6, 7}
c = a - b  # {1, 2}
```

Algorithm:
```
1. Iterate over a
2. For each element: check if NOT in b (O(1) lookup)
3. If not in b: add to result

Time: O(len(a))   (check each element of a against b)
Space: O(len(a))
```

### Symmetric Difference: `a ^ b` or `a.symmetric_difference(b)`

```python
c = a ^ b  # {1, 2, 6, 7} — elements in either but not both
```

Algorithm:
```
1. Take (a - b) ∪ (b - a)
Time: O(len(a) + len(b))
Space: O(len(a) + len(b))
```

### Subset/Superset: `a <= b`, `a >= b`

```
1. If len(a) > len(b): a can't be subset → False
2. For each element in a: check if in b
   If any element not found: False
   
Time: O(len(a))
```

---

## 7.5 Complexity Summary

| Operation | Average | Worst | Notes |
|-----------|---------|-------|-------|
| `x in s` | O(1) | O(n) | Hash lookup |
| `s.add(x)` | O(1) | O(n) | Amortized O(1), O(n) on resize |
| `s.remove(x)` | O(1) | O(n) | Hash lookup + tombstone |
| `s.discard(x)` | O(1) | O(n) | Like remove but no error |
| `s.pop()` | O(1) | O(n) | Uses finger for fast scanning |
| `len(s)` | O(1) | O(1) | Read `used` field |
| `a \| b` | O(n+m) | O(n+m) | Copy + insert all |
| `a & b` | O(min(n,m)) | O(n*m) | Iterate smaller, lookup in larger |
| `a - b` | O(n) | O(n*m) | Iterate a, lookup in b |
| `a ^ b` | O(n+m) | O(n+m) | Union minus intersection |
| `a <= b` | O(n) | O(n*m) | Check all of a in b |
| `a == b` | O(n) | O(n*m) | Check size + subset both ways |

*Worst cases occur with hash collisions (degenerate hash function)*

---

## 7.6 set vs frozenset

| Feature | set | frozenset |
|---------|-----|-----------|
| Mutable | Yes | No |
| Hashable | No | Yes |
| Can be dict key | No | Yes |
| Can be set element | No | Yes |
| Has `.add()`, `.remove()` | Yes | No |
| Has `\|`, `&`, `-` | Yes | Yes (returns frozenset) |
| Cached hash | No (always -1) | Yes (computed once) |

```python
# frozenset as dict key:
d = {frozenset({1,2}): "pair"}  # Valid!
d = {{1,2}: "pair"}             # TypeError: unhashable type: 'set'
```

---

## 7.7 The `smalltable` Optimization

```c
#define PySet_MINSIZE 8

typedef struct {
    // ...
    setentry *table;          // Points to smalltable for small sets
    setentry smalltable[8];   // Inline storage!
} PySetObject;
```

For sets with ≤ 5 elements (load factor 2/3 of 8):
- The table array is INSIDE the struct (no separate heap allocation)
- No malloc for the table until the set grows beyond 5 elements
- Small sets (very common) are very memory-efficient

---

## 7.8 Set vs Dict for Membership Testing

```python
# Both give O(1) membership testing:
my_set = {1, 2, 3, 4, 5}
my_dict = {1: None, 2: None, 3: None, 4: None, 5: None}

3 in my_set   # O(1)
3 in my_dict  # O(1)
```

But sets are more memory-efficient for pure membership:
```python
import sys
sys.getsizeof({1,2,3,4,5})            # ~216 bytes
sys.getsizeof({1:None,2:None,...})     # ~232 bytes
```

Sets don't store values (saving 8 bytes per entry for the value pointer).

---

## 7.9 Why Sets Don't Use the Compact Layout

Dicts switched to compact layout in 3.6 because:
1. They need insertion order (language requirement since 3.7)
2. They iterate frequently (for x in d)

Sets don't need order guarantee, and the old-style sparse table is simpler. The compact layout's two-level indirection adds complexity without as much benefit for sets.

However, sets DO use good probe sequences and the same load factor (2/3).

---

## 7.10 Interview Questions — Part 7

**Q1**: How is a set implemented internally?
**A**: As a hash table storing only keys (no values). Uses open addressing with perturbation probing, same as dict.

**Q2**: What's the time complexity of `x in my_set`?
**A**: O(1) average. Hash-based lookup, same as dict.

**Q3**: What's the complexity of `set_a & set_b`?
**A**: O(min(len(a), len(b))). Iterates over the smaller set and checks membership in the larger one.

**Q4**: Why can't a set be a dictionary key?
**A**: Sets are mutable (can add/remove elements). Mutable objects can't have a stable hash, so they're unhashable. Use `frozenset` instead.

**Q5**: What is the `smalltable` optimization?
**A**: Sets with ≤ 5 elements store their hash table inline in the struct (no separate heap allocation). Since most sets are small, this saves a malloc call.

**Q6**: Why don't sets use the compact dict layout?
**A**: Sets don't need insertion order (no language requirement) and the simpler sparse layout works well. The compact layout's two-level indirection adds complexity without proportional benefit for sets.

**Q7**: What's the difference between `s.remove(x)` and `s.discard(x)`?
**A**: Both delete x. `remove` raises KeyError if x is not in the set. `discard` silently does nothing if x is absent.
