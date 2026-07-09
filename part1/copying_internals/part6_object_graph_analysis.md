# Part 6 — Object Graph Analysis

## 6.1 What Is an Object Graph?

Every Python program creates a **graph of objects** connected by references:

```python
data = {
    "users": [
        {"name": "Alice", "scores": [90, 85]},
        {"name": "Bob", "scores": [75, 92]},
    ],
    "metadata": {"version": 1}
}
```

```
'data' → dict_root
           ├─ "users" → list_users
           │              ├─ [0] → dict_alice
           │              │         ├─ "name" → "Alice"
           │              │         └─ "scores" → [90, 85]
           │              └─ [1] → dict_bob
           │                        ├─ "name" → "Bob"
           │                        └─ "scores" → [75, 92]
           └─ "metadata" → dict_meta
                            └─ "version" → 1
```

Object count: 1 root dict + 1 list + 2 user dicts + 1 meta dict + 2 score lists + strings + ints = ~15+ objects.

---

## 6.2 Shared References in Graphs

Objects can be shared (multiple paths lead to the same object):

```python
shared_list = [1, 2, 3]
a = {"x": shared_list, "y": shared_list}

# Object graph:
# a → dict
#       ├─ "x" → shared_list ←─ "y"
#       └─ "y" ─────────────────┘
# shared_list has refcnt = 3 (a["x"], a["y"], variable shared_list)
```

### How shallow copy handles sharing:
```python
b = a.copy()
# b["x"] is b["y"]  → True! Sharing preserved (same pointers copied)
# b["x"] is a["x"]  → True! Still the SAME shared_list object
```

### How deep copy handles sharing:
```python
b = copy.deepcopy(a)
# b["x"] is b["y"]  → True! Sharing preserved within the copy!
# b["x"] is a["x"]  → False! It's a new copy of shared_list
```

Deep copy preserves the **topology** (sharing structure) within the copy, while making the copy independent from the original.

---

## 6.3 Cycles in Object Graphs

```python
# Self-reference:
a = []
a.append(a)  # a[0] is a

# Mutual reference:
x = {"partner": None}
y = {"partner": x}
x["partner"] = y
# x → y → x → y → ... (infinite cycle)

# Multi-node cycle:
nodes = [{"next": None} for _ in range(3)]
nodes[0]["next"] = nodes[1]
nodes[1]["next"] = nodes[2]
nodes[2]["next"] = nodes[0]  # Cycle!
```

Deep copy handles all of these correctly via the memo dict.

---

## 6.4 Visualizing Copy Depth

```python
original = [[1, [2, 3]], {"a": [4, 5]}]
```

### Assignment (depth 0):
```
original ──→ [ref, ref] ←── alias
              │     │
              ▼     ▼
         [1,[2,3]] {"a":[4,5]}
```
Everything shared. One object graph.

### Shallow copy (depth 1):
```
original ──→ [ref, ref]        (original container)
              │     │
              ▼     ▼
         [1,[2,3]] {"a":[4,5]}  ← SHARED!
              ↑     ↑
              │     │
copy ────→ [ref, ref]          (NEW container, same elements)
```
New top-level container. Everything inside is shared.

### Deep copy (depth ∞):
```
original ──→ [ref, ref]
              │     │
              ▼     ▼
         [1,[2,3]] {"a":[4,5]}

copy ────→ [ref', ref']
              │      │
              ▼      ▼
         [1,[2,3]'] {"a":[4,5]'}  ← ALL NEW (except immutables)
```
Every mutable object has its own independent copy.

---

## 6.5 Refcount Effects of Copying

```python
import sys

inner = [1, 2, 3]
a = [inner, inner, inner]

print(sys.getrefcount(inner))  # 5 (inner, a[0], a[1], a[2], getrefcount arg)

b = a.copy()  # Shallow
print(sys.getrefcount(inner))  # 8 (+ b[0], b[1], b[2])

c = copy.deepcopy(a)
print(sys.getrefcount(inner))  # 8 (unchanged! deepcopy made a new list)
# c's elements point to a NEW list [1,2,3], not inner
```

---

## 6.6 The Diamond Problem

```python
shared = [1, 2, 3]
parent_a = {"data": shared}
parent_b = {"data": shared}
root = {"a": parent_a, "b": parent_b}
```

```
root → dict
        ├─ "a" → parent_a → dict
        │                     └─ "data" → shared [1,2,3]
        └─ "b" → parent_b → dict          ↑
                              └─ "data" ───┘
```

Deep copy must handle this diamond correctly:
```python
root_copy = copy.deepcopy(root)
# root_copy["a"]["data"] is root_copy["b"]["data"]  → True!
# The sharing within the graph is preserved!
# But: root_copy["a"]["data"] is root["a"]["data"]  → False!
# Independent from original.
```

---

## 6.7 Interview Questions — Part 6

**Q1**: Does deepcopy preserve shared references within the copy?
**A**: Yes! If two parts of the original graph reference the same object, two parts of the copy reference the same (new) copy of that object. The sharing topology is preserved.

**Q2**: What is the "diamond problem" in copying?
**A**: When multiple paths in an object graph lead to the same shared object. Deep copy must ensure the copy has the same structure (one shared copy, not multiple independent copies of the shared object).

**Q3**: How does deepcopy handle self-referential lists?
**A**: Registers the new list in memo before recursing. When the self-reference is encountered during element copying, it's found in memo → the new list gets a reference to itself.

**Q4**: What happens to refcounts during shallow copy?
**A**: All shared elements get +1 refcount (the copy holds a new reference). The container refcount is unaffected (it's a new object with its own refcount of 1).

**Q5**: Can you visualize the difference between shallow and deep copy for `[[1,2],[3,4]]`?
**A**: Shallow: new outer list, same two inner lists (refcnt of each inner list goes up by 1). Deep: new outer list AND two new inner lists (ints are shared since immutable).
