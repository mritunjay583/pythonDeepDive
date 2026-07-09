# Part 4 — Deep Copy

## 4.1 Definition

A **deep copy** recursively duplicates the entire object graph — every mutable object reachable from the root is independently cloned.

```python
import copy

a = [[1, 2], {"key": [3, 4]}, (5, [6, 7])]
b = copy.deepcopy(a)

# Everything is independent:
a is b           # False (different list)
a[0] is b[0]    # False (different inner list!)
a[1] is b[1]    # False (different dict!)
a[1]["key"] is b[1]["key"]  # False (different inner list!)

# But immutables ARE shared (optimization):
a[0][0] is b[0][0]  # True — int(1) is shared (immutable)
```

---

## 4.2 The Memo Dictionary

Deep copy uses a **memo dict** to handle two critical problems:
1. **Shared references**: If two parts of the graph point to the same object, the copy should maintain that sharing
2. **Circular references**: Prevent infinite recursion

```python
# Shared reference:
shared = [1, 2, 3]
a = [shared, shared]  # Both elements point to same list

b = copy.deepcopy(a)
b[0] is b[1]  # True! The sharing is PRESERVED in the copy
b[0] is a[0]  # False — it's a copy, not the original
```

The memo maps `id(original_obj) → copy_of_obj`:
```python
# Internally:
memo = {}
# When copying 'shared' the first time:
memo[id(shared)] = new_copy_of_shared
# When encountering 'shared' again:
# Already in memo! Return memo[id(shared)] instead of copying again
```

---

## 4.3 Handling Circular References

```python
a = [1, 2]
a.append(a)  # Circular: a[2] is a itself!

b = copy.deepcopy(a)
# b[2] is b (NOT a!) — the cycle is reproduced in the copy
print(b[2] is b)   # True
print(b[2] is a)   # False — independent cycle
```

Without the memo, deepcopy of a circular structure would recurse infinitely:
```
Copy a → copy a[0] (int, done) → copy a[1] (int, done) → copy a[2] (it's a!) → copy a → copy a[0] → ...INFINITE!
```

With memo:
```
Copy a → register in memo: memo[id(a)] = new_list_b
  → copy a[0] (int 1, return shared) ✓
  → copy a[1] (int 2, return shared) ✓
  → copy a[2] → it's a → id(a) IN memo! → return memo[id(a)] = b ✓
Done! b[2] = b (the copy references itself, cycle preserved)
```

---

## 4.4 The Algorithm

```python
# Simplified deepcopy logic (Lib/copy.py):
def deepcopy(x, memo=None):
    if memo is None:
        memo = {}
    
    # 1. Check if already copied (handles cycles + shared refs)
    d = id(x)
    if d in memo:
        return memo[d]
    
    # 2. Determine how to copy based on type
    cls = type(x)
    
    # 3. Atomic/immutable types — return as-is (no copy needed)
    if cls in (int, float, str, bytes, bool, type(None), type(...)):
        return x
    
    # 4. Try __deepcopy__ method
    copier = getattr(x, "__deepcopy__", None)
    if copier is not None:
        y = copier(memo)
    
    # 5. Known container types — copy structure, recurse on elements
    elif cls is list:
        y = []
        memo[d] = y  # Register BEFORE recursing (cycle protection!)
        for item in x:
            y.append(deepcopy(item, memo))
    
    elif cls is dict:
        y = {}
        memo[d] = y
        for key, value in x.items():
            y[deepcopy(key, memo)] = deepcopy(value, memo)
    
    elif cls is tuple:
        # Special: tuple is immutable, but may contain mutables
        elements = [deepcopy(item, memo) for item in x]
        # If no element changed, return original tuple (optimization)
        if all(elements[i] is x[i] for i in range(len(x))):
            y = x  # All elements are immutable — share the tuple
        else:
            y = tuple(elements)
        memo[d] = y
    
    # 6. General case — use __reduce__/__reduce_ex__
    else:
        reductor = getattr(x, "__reduce_ex__", None)
        rv = reductor(4)
        y = _reconstruct(x, memo, *rv)
    
    return y
```

Critical detail: `memo[d] = y` is set **BEFORE** recursing into children. This is how cycles are handled — when we encounter the object again during child recursion, it's already in memo.

---

## 4.5 What Gets Shared (Not Copied)

Deep copy does NOT copy immutable atomic types:
```python
import copy

a = [42, "hello", 3.14, True, None, (1, 2, 3)]
b = copy.deepcopy(a)

a[0] is b[0]   # True — int 42 is shared
a[1] is b[1]   # True — string "hello" is shared
a[2] is b[2]   # True — float is shared
a[3] is b[3]   # True — True singleton
a[4] is b[4]   # True — None singleton
a[5] is b[5]   # True — tuple of immutables is shared!
```

This is safe because immutable objects can't be modified — sharing them is always correct.

### But: Tuple with mutable contents IS deep-copied:
```python
t = ([1, 2], [3, 4])  # Tuple containing mutable lists!
u = copy.deepcopy(t)

t is u         # False — different tuple!
t[0] is u[0]  # False — inner lists are copied!
```

---

## 4.6 Custom Deep Copy: `__deepcopy__`

```python
class Connection:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self._socket = connect(host, port)  # Resource — can't copy!
    
    def __deepcopy__(self, memo):
        # Create new connection instead of copying the socket
        new = Connection(
            copy.deepcopy(self.host, memo),
            copy.deepcopy(self.port, memo)
        )
        memo[id(self)] = new
        return new
```

Use `__deepcopy__` when:
- Object holds non-copyable resources (files, sockets, locks)
- You need custom copying logic
- You want to skip certain fields

---

## 4.7 Performance Characteristics

```python
import copy, timeit

# Simple flat list:
a = list(range(10000))
timeit.timeit(lambda: copy.deepcopy(a))  # ~10 ms (vs ~50 μs for shallow!)

# Nested structure:
a = [[i, i+1] for i in range(10000)]
timeit.timeit(lambda: copy.deepcopy(a))  # ~50 ms

# Deep nesting:
a = {"level1": {"level2": {"level3": list(range(1000))}}}
timeit.timeit(lambda: copy.deepcopy(a))  # ~1 ms (small graph)
```

Deep copy is 100-1000× slower than shallow copy because:
1. Must traverse the entire object graph
2. Must create new objects for every mutable node
3. Must maintain the memo dictionary
4. Many Python function calls (not just C-level pointer copies)

---

## 4.8 Memory Diagram: Deep Copy of Nested Structure

```python
original = {"a": [1, 2], "b": [3, 4]}
clone = copy.deepcopy(original)
```

```
'original' → dict_A
               ├─ "a" → list_X [1, 2]
               └─ "b" → list_Y [3, 4]

'clone'    → dict_B  (NEW dict)
               ├─ "a" → list_X' [1, 2]  (NEW list, shares ints)
               └─ "b" → list_Y' [3, 4]  (NEW list, shares ints)

Shared: "a", "b" (interned strings), 1, 2, 3, 4 (cached ints)
NOT shared: dict_A/dict_B, list_X/list_X', list_Y/list_Y'
```

---

## 4.9 Interview Questions — Part 4

**Q1**: What is the memo dictionary in deepcopy?
**A**: Maps `id(original_object)` → `copy_of_object`. Handles shared references (preserves sharing in the copy) and circular references (prevents infinite recursion).

**Q2**: How does deepcopy handle circular references?
**A**: It registers the copy in memo BEFORE recursing into children. When the circular reference is encountered during recursion, it's found in memo and the existing copy is returned instead of recursing again.

**Q3**: Does deepcopy copy integers and strings?
**A**: No. Immutable atomic types are shared between original and copy. They can't be mutated, so sharing is always safe and saves time/memory.

**Q4**: What about tuples?
**A**: If a tuple contains only immutable elements, it's shared. If it contains mutable elements (list, dict), the tuple is deep-copied (a new tuple with deep-copied elements is created).

**Q5**: How do you customize deep copy behavior?
**A**: Define `__deepcopy__(self, memo)` on your class. Useful for objects with non-copyable resources (files, sockets, database connections).

**Q6**: Why is deepcopy so much slower than shallow copy?
**A**: Shallow copy just copies n pointers (C-level memcpy + increfs). Deepcopy must traverse the entire graph, create new objects for each mutable node, and maintain a memo dict — all through Python-level function calls.
