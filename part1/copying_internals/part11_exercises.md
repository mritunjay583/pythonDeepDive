# Part 11 — Exercises

## Section A: Memory Diagrams (10 Exercises)

### Exercise 1
Draw the object graph before and after `b = a.copy()` for:
```python
a = [1, [2, 3], "hello"]
```
Show which objects are shared and which are new.

### Exercise 2
Draw the object graph showing the difference between:
```python
a = [[0] * 3] * 3      # Bug version
b = [[0] * 3 for _ in range(3)]  # Correct version
```

### Exercise 3
Draw the complete graph after:
```python
shared = {"key": [1, 2]}
x = [shared, shared]
y = copy.deepcopy(x)
```
Show that y[0] is y[1] (sharing preserved in copy).

### Exercise 4
Draw the circular reference and how deepcopy handles it:
```python
a = [1, 2]
a.append(a)
b = copy.deepcopy(a)
```

### Exercise 5
Draw the memory state showing refcount changes:
```python
inner = [10, 20]
a = [inner, inner, inner]
b = a.copy()
# What is inner's refcount at each step?
```
**Answer**: After creation: 1. After `a = [inner]*3`: 4 (var + 3 slots). After `b = a.copy()`: 7 (var + 3 in a + 3 in b).

---

## Section B: Refcount Tracing (10 Exercises)

### Exercise 6
Trace refcount of the inner list through:
```python
inner = [1, 2, 3]         # inner.refcnt = 1
a = {"data": inner}       # inner.refcnt = 2
b = a.copy()              # inner.refcnt = 3 (shallow: b["data"] → same)
del a                     # inner.refcnt = 2
b["data"] = None          # inner.refcnt = 1
del inner                 # inner.refcnt = 0 → FREED
```

### Exercise 7
What's the refcount of `[1,2]` after:
```python
x = [1, 2]
y = copy.deepcopy(x)
```
**Answer**: x's list: refcnt=1 (just x). y's list: refcnt=1 (just y). They are DIFFERENT objects.

### Exercise 8
Trace through:
```python
a = [1, 2, 3]
b = a
c = b.copy()
d = copy.deepcopy(c)
del a, b
# What remains? What are refcounts?
```
**Answer**: Original list: refcnt was 2 (a,b), now 0 → freed. c: refcnt=1 (its own copy). d: refcnt=1 (deep copy). c and d both alive with refcnt=1.

### Exercise 9
```python
def foo():
    local = [1, 2, 3]
    return local.copy()

result = foo()
```
After foo returns: local's original list refcnt→0→freed. result holds the copy (refcnt=1). Integers 1,2,3 still alive (cached).

### Exercise 10
```python
cache = {}
def get_data():
    if "key" not in cache:
        cache["key"] = expensive_computation()
    return cache["key"]  # Returns reference, NOT copy!

data = get_data()
data.append("oops")  # Modifies the cached value!
```
**Question**: After this, what does `cache["key"]` contain?
**Answer**: Has "oops" appended — caller mutated the shared cached object.
**Fix**: `return cache["key"].copy()` or `return copy.deepcopy(cache["key"])`

---

## Section C: Predict the Output (15 Exercises)

### Exercise 11
```python
a = [1, 2, 3]
b = a
c = a.copy()
a.append(4)
print(len(b), len(c))
```
**Answer**: `4 3` — b is alias (sees append), c is copy (independent).

### Exercise 12
```python
d = {"a": [1], "b": [2]}
e = d.copy()
d["a"].append(10)
d["c"] = [3]
print(e)
```
**Answer**: `{'a': [1, 10], 'b': [2]}` — shared value mutated, new key not visible.

### Exercise 13
```python
import copy
a = [1, [2, [3, [4]]]]
b = copy.deepcopy(a)
a[1][1][1][0] = 99
print(b[1][1][1][0])
```
**Answer**: `4` — deep copy is fully independent.

### Exercise 14
```python
x = [1, 2, 3]
y = [x, x]
z = y.copy()
z[0].append(4)
print(x)
print(y[0] is y[1])
print(z[0] is z[1])
```
**Answer**: `[1, 2, 3, 4]`, `True`, `True` — shared ref preserved in shallow copy.

### Exercise 15
```python
a = {"x": 1}
b = a
a = {"y": 2}
print(b)
```
**Answer**: `{'x': 1}` — rebinding a doesn't affect b.

### Exercise 16
```python
a = {"x": 1}
b = a
a.update({"y": 2})
print(b)
```
**Answer**: `{'x': 1, 'y': 2}` — mutation through alias.

### Exercise 17
```python
a = [1, 2, 3]
b = a[1:3]
b[0] = 99
print(a)
```
**Answer**: `[1, 2, 3]` — slice creates new list, mutation doesn't propagate.

### Exercise 18
```python
import copy
t = (1, 2, [3, 4])
u = copy.deepcopy(t)
u[2].append(5)
print(t)
```
**Answer**: `(1, 2, [3, 4])` — deep copy independent.

### Exercise 19
```python
a = [1, 2, 3]
b = a
a = a + [4, 5]  # Creates NEW list
print(b)
print(a is b)
```
**Answer**: `[1, 2, 3]`, `False`

### Exercise 20
```python
a = [1, 2, 3]
b = a
a.extend([4, 5])  # Mutates IN PLACE
print(b)
print(a is b)
```
**Answer**: `[1, 2, 3, 4, 5]`, `True`

### Exercise 21
```python
class Foo:
    data = []  # Class variable!

f1 = Foo()
f2 = Foo()
f1.data.append(1)
print(f2.data)
```
**Answer**: `[1]` — class variable shared by all instances.

### Exercise 22
```python
import copy
a = [None] * 5
b = copy.deepcopy(a)
print(a[0] is b[0])
```
**Answer**: `True` — None is a singleton, deepcopy shares it.

### Exercise 23
```python
a = [1, 2, 3]
b = [a]
c = copy.deepcopy(b)
a.append(4)
print(c[0])
```
**Answer**: `[1, 2, 3]` — c[0] is a deep copy of a (independent).

### Exercise 24
```python
original = [1, 2, 3]
copies = [original.copy() for _ in range(3)]
copies[0].append(4)
print(original)
print(copies[1])
```
**Answer**: `[1, 2, 3]`, `[1, 2, 3]` — each copy is independent.

### Exercise 25
```python
a = {"nested": {"deep": [1, 2, 3]}}
b = a.copy()
c = copy.deepcopy(a)
a["nested"]["deep"].append(4)
print(b["nested"]["deep"])
print(c["nested"]["deep"])
```
**Answer**: `[1, 2, 3, 4]`, `[1, 2, 3]` — shallow shares nested, deep doesn't.

---

## Section D: Design Decisions (5 Exercises)

### Exercise 26
You have a function that receives a config dict and might need to modify it temporarily. What's the best approach?
**Answer**: Shallow copy if config has only immutable values. Deep copy if nested mutable structures. Best: design config as immutable (frozen dataclass/namedtuple).

### Exercise 27
You're implementing a cache that returns stored results. How do you prevent callers from mutating cached values?
**Answer**: Return `copy.deepcopy(cached_value)` or use immutable return types (tuple/frozenset). For performance: document that returned values shouldn't be modified, or use `types.MappingProxyType` for dicts.

### Exercise 28
You have a 10MB nested data structure and need 100 "variants" that differ in one field each. What's the most memory-efficient approach?
**Answer**: Don't make 100 deep copies (1GB!). Store base + diffs: `variants = [{"base": data, "override": diff_i}]`. Or use structural sharing (persistent data structures). Or copy.copy() + override the one field if top-level change suffices.

### Exercise 29
A thread wants to read a shared data structure while another might be writing. Copying approach?
**Answer**: Lock + shallow/deep copy before processing. Or: use immutable structures (no copy needed for reads). Or: copy-on-write with versioning. Copy cost = O(n) but done once, then thread processes independently.

### Exercise 30
Your API returns internal state. How do you choose between returning the object directly vs a copy?
**Answer**: If API contract promises "no mutation": return directly (document it). If users might modify: return a copy. For public APIs: prefer returning copies (defensive) or immutable views. Balance between safety and performance.
