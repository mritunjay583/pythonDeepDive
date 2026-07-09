# Part 9 — Copying

## 9.1 The Copying Spectrum

Python offers multiple ways to "copy" a list, each with different semantics and memory behavior:

```
No Copy          Shallow Copy              Deep Copy
─────────────────────────────────────────────────────────────
b = a            b = a.copy()              b = copy.deepcopy(a)
b = a[:]             
                 b = list(a)
                 b = copy.copy(a)

│                │                         │
│ Same object    │ New list object          │ New everything
│ Same pointers  │ Same element pointers    │ New element objects
│ Same elements  │ Same elements            │ New elements (recursive)
```

---

## 9.2 Assignment (No Copy): `b = a`

```python
a = [1, 2, 3]
b = a
```

**This is NOT a copy.** It creates a new name binding to the same object.

```
BEFORE:
'a' ──→ PyListObject (refcnt=1)
         ob_item → [*1, *2, *3]

AFTER b = a:
'a' ──→ PyListObject (refcnt=2) ←── 'b'
         ob_item → [*1, *2, *3]
```

- `a is b` → True (same object)
- `id(a) == id(b)` → True
- `b.append(4)` modifies `a` too (same list!)
- `a[0] = 99` also visible through `b`
- Cost: **O(1)** — just increment refcnt

---

## 9.3 Shallow Copy: `b = a.copy()` / `b = a[:]` / `b = list(a)`

```python
a = [1, 2, 3]
b = a.copy()  # or a[:] or list(a) — all equivalent
```

Creates a **new list object** with **new pointer array** but **same element objects**.

```
'a' ──→ PyListObject_A (refcnt=1)
         ob_item_A → [ptr0, ptr1, ptr2]
                       │     │     │
                       ▼     ▼     ▼
                     int(1) int(2) int(3)    ← SHARED
                       ↑     ↑     ↑
                       │     │     │
'b' ──→ PyListObject_B (refcnt=1)
         ob_item_B → [ptr0, ptr1, ptr2]     ← NEW array, same pointers
```

Properties:
- `a is b` → **False** (different list objects)
- `a == b` → True (same contents)
- `a[0] is b[0]` → **True** (same element objects!)
- `b.append(4)` does NOT affect `a` (different lists)
- `a[0] = 99` does NOT affect `b` (replaced pointer in a, b still has old pointer)

But with mutable elements:
```python
a = [[1, 2], [3, 4]]
b = a.copy()
b[0].append(99)
print(a[0])  # [1, 2, 99] — BOTH point to same inner list!
```

### Memory Cost:
- New PyListObject: ~56 bytes
- New pointer array: n × 8 bytes
- Py_INCREF each element: n operations
- **Total: O(n) time, O(n) space**
- Elements themselves are NOT duplicated

---

## 9.4 The Three Equivalent Shallow Copies

```python
# These all produce identical results:
b = a.copy()        # list method (clearest intent)
b = a[:]            # slice of everything
b = list(a)         # constructor from iterable
b = [x for x in a] # comprehension (slightly slower)
```

Internally:
- `a.copy()` → calls `list_copy_impl` → calls `list_slice(self, 0, n)`
- `a[:]` → calls `list_subscript` with full slice → calls `list_slice(self, 0, n)`  
- `list(a)` → calls `list___init__` → detects list input → calls `list_slice`

They all converge to the same internal function. Performance is essentially identical.

---

## 9.5 copy.copy() — Also Shallow

```python
import copy
b = copy.copy(a)
```

For lists, `copy.copy()` is equivalent to `a.copy()`. It calls `a.__copy__()` which for lists returns a shallow copy.

No difference in behavior or performance from `a.copy()`.

---

## 9.6 copy.deepcopy() — Full Recursive Copy

```python
import copy

a = [[1, 2], [3, 4], {"key": "value"}]
b = copy.deepcopy(a)
```

Creates new objects **recursively** for all nested mutable objects.

```
'a' ──→ PyListObject_A
         ob_item → [ptr0_a, ptr1_a, ptr2_a]
                     │       │       │
                     ▼       ▼       ▼
                   [1,2]_A  [3,4]_A  {"key":"value"}_A
                   (original objects)


'b' ──→ PyListObject_B  (NEW)
         ob_item → [ptr0_b, ptr1_b, ptr2_b]  (NEW array)
                     │       │       │
                     ▼       ▼       ▼
                   [1,2]_B  [3,4]_B  {"key":"value"}_B
                   (COMPLETELY NEW objects, independent)
```

After deepcopy:
- `a is b` → False
- `a[0] is b[0]` → **False** (different inner list objects!)
- `b[0].append(99)` does NOT affect `a[0]`
- All objects are independent

### How deepcopy Works:

```python
# Simplified logic:
def deepcopy(obj, memo=None):
    if memo is None:
        memo = {}  # Track already-copied objects (handles cycles)
    
    obj_id = id(obj)
    if obj_id in memo:
        return memo[obj_id]  # Already copied — return same copy
    
    if isinstance(obj, list):
        new_list = []
        memo[obj_id] = new_list  # Register BEFORE recursing (cycle protection)
        for item in obj:
            new_list.append(deepcopy(item, memo))
        return new_list
    
    elif isinstance(obj, dict):
        # Similar recursive copy...
        pass
    
    else:
        # Immutable objects (int, str, tuple of immutables) — share them
        return obj
```

Key features:
- Uses a `memo` dict to handle **circular references**
- Immutable objects (int, str, None) are shared, not copied
- Mutable objects (list, dict, sets) are recursively duplicated
- **Very expensive**: O(total_objects) time and space

---

## 9.7 Deepcopy and Circular References

```python
import copy

a = [1, 2, 3]
a.append(a)  # Circular reference!

b = copy.deepcopy(a)
print(b[3] is b)  # True — the copy has its OWN cycle!
print(b[3] is a)  # False — not linked to original
```

```
Original:                         Deep Copy:
a → [1, 2, 3, ──→ a]             b → [1, 2, 3, ──→ b]
     └────────────┘                    └────────────┘
     (self-reference)                  (self-reference to COPY)
```

The `memo` dict ensures that when deepcopy encounters `a` inside itself, it returns the already-created copy `b` rather than creating infinite copies.

---

## 9.8 Performance Comparison

```python
import copy, timeit

a = list(range(10000))

# Timing results (relative):
# Assignment:     ~20 ns      (just refcnt increment)
# .copy():        ~50 μs      (copy 10000 pointers + incref each)
# copy.copy():    ~55 μs      (same as .copy() with import overhead)
# copy.deepcopy(): ~200 μs    (recursive traversal, memo dict, etc.)
```

| Method | Time | Space | New List? | New Elements? | Handles Cycles? |
|--------|------|-------|-----------|---------------|-----------------|
| `b = a` | O(1) | O(1) | No | No | N/A |
| `a.copy()` | O(n) | O(n) | Yes | No | N/A |
| `a[:]` | O(n) | O(n) | Yes | No | N/A |
| `list(a)` | O(n) | O(n) | Yes | No | N/A |
| `copy.copy(a)` | O(n) | O(n) | Yes | No | N/A |
| `copy.deepcopy(a)` | O(N)* | O(N)* | Yes | Yes | Yes |

*N = total number of objects in the entire nested structure

---

## 9.9 Aliasing Traps

### Trap 1: Function Default Arguments

```python
def append_to(item, target=[]):  # DANGER: default is shared!
    target.append(item)
    return target

print(append_to(1))  # [1]
print(append_to(2))  # [1, 2] — same list!
```

The default `[]` is created ONCE when the function is defined. Every call that uses the default shares the same list object.

Fix: `def append_to(item, target=None): target = target if target is not None else []`

### Trap 2: Class Attributes

```python
class Team:
    members = []  # Shared among ALL instances!

t1 = Team()
t2 = Team()
t1.members.append("Alice")
print(t2.members)  # ["Alice"] — same list!
```

Fix: Initialize in `__init__`: `self.members = []`

### Trap 3: Multiplication with Mutables

```python
matrix = [[0] * 3] * 3  # 3 references to SAME row!
matrix[0][0] = 1
print(matrix)  # [[1, 0, 0], [1, 0, 0], [1, 0, 0]]

# Fix:
matrix = [[0] * 3 for _ in range(3)]  # 3 DIFFERENT rows
```

---

## 9.10 When to Use Each Method

| Scenario | Method | Why |
|----------|--------|-----|
| Just need another name | `b = a` | No copy needed |
| Independent list, immutable elements | `a.copy()` | Shallow is sufficient |
| Independent list, mutable elements | `copy.deepcopy(a)` | Need recursive independence |
| Passing to function that might mutate | `func(a.copy())` | Protect original |
| List of strings/numbers | `a.copy()` | Strings/numbers are immutable |
| List of lists/dicts | `copy.deepcopy(a)` | Inner containers are mutable |
| Performance-critical, read-only use | `b = a` | Zero cost |

---

## 9.11 Memory Diagrams — Complete Comparison

### Original:
```python
original = [[1, 2], "hello", 42]
```

```
'original' → PyListObject
              ob_item → [ptr0, ptr1, ptr2]
                          │      │      │
                          ▼      ▼      ▼
                       [1,2]  "hello"  42
                       (list) (str)  (int)
```

### After `shallow = original.copy()`:
```
'original' → PyListObject_1
              ob_item_1 → [ptr0, ptr1, ptr2]
                            │      │      │
                            ▼      ▼      ▼
                         [1,2]  "hello"  42    ← SHARED objects
                            ↑      ↑      ↑
                            │      │      │
'shallow'  → PyListObject_2  (different object!)
              ob_item_2 → [ptr0, ptr1, ptr2]  (different array!)
```

### After `deep = copy.deepcopy(original)`:
```
'original' → PyListObject_1
              ob_item_1 → [ptr0, ptr1, ptr2]
                            │      │      │
                            ▼      ▼      ▼
                         [1,2]_A "hello"  42
                         (list)  (str)   (int)
                                   ↑       ↑
                                   │       │ (immutables shared!)
'deep'     → PyListObject_3       │       │
              ob_item_3 → [ptr0, ptr1, ptr2]
                            │
                            ▼
                         [1,2]_B    ← DIFFERENT list object!
                         (independent copy)
```

Note: `deepcopy` shares **immutable** objects (str, int, tuple) since they can't be mutated anyway. Only **mutable** objects (list, dict, set) get new copies.

---

## 9.12 Interview Questions — Part 9

**Q1**: After `b = a`, does modifying `b` affect `a`?
**A**: Yes! `b = a` is not a copy — both names reference the same list object. Any mutation through either name is visible through both.

**Q2**: After `b = a.copy()`, does `b[0].append(99)` affect `a` (if a[0] is a list)?
**A**: Yes! Shallow copy only copies the top-level pointers. `a[0]` and `b[0]` still point to the same inner list object.

**Q3**: What's the time complexity of `copy.deepcopy(a)` for a list of n elements?
**A**: O(N) where N is the total number of mutable objects reachable from `a` (including nested structures). For a flat list of immutable items, it's effectively O(n) with higher constant than shallow copy.

**Q4**: Why does deepcopy use a memo dictionary?
**A**: To handle circular references and shared objects. If object A references object B which references A, the memo prevents infinite recursion by returning the already-created copy when the same object is encountered again.

**Q5**: Is `a[:] == a.copy()` always True?
**A**: `a[:] == a.copy()` is True (same contents). `a[:] is a.copy()` is False (different objects). They produce equivalent but distinct lists.

**Q6**: Which copy methods share immutable objects?
**A**: ALL of them. Even deepcopy shares immutable objects (int, str, tuple of immutables, frozenset). There's no point duplicating objects that can never change.
