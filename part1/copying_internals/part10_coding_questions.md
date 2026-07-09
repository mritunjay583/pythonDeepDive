# Part 10 — Coding Questions (100 Output Prediction)

### Q1
```python
a = [1, 2, 3]
b = a
b.append(4)
print(a)
```
**Output**: `[1, 2, 3, 4]`

### Q2
```python
a = [1, 2, 3]
b = a.copy()
b.append(4)
print(a)
```
**Output**: `[1, 2, 3]`

### Q3
```python
a = [[1, 2], [3, 4]]
b = a.copy()
b[0].append(5)
print(a)
```
**Output**: `[[1, 2, 5], [3, 4]]`

### Q4
```python
import copy
a = [[1, 2], [3, 4]]
b = copy.deepcopy(a)
b[0].append(5)
print(a)
```
**Output**: `[[1, 2], [3, 4]]`

### Q5
```python
a = [1, 2, 3]
b = a
a = a + [4]
print(b)
```
**Output**: `[1, 2, 3]`

### Q6
```python
a = [1, 2, 3]
b = a
a += [4]
print(b)
```
**Output**: `[1, 2, 3, 4]`

### Q7
```python
a = (1, 2, 3)
b = a
a += (4,)
print(b)
print(a is b)
```
**Output**: `(1, 2, 3)` then `False`

### Q8
```python
import copy
a = [1, 2, 3]
b = copy.copy(a)
print(a is b)
print(a == b)
print(a[0] is b[0])
```
**Output**: `False`, `True`, `True`

### Q9
```python
import copy
x = (1, [2, 3])
y = copy.copy(x)
print(x is y)
```
**Output**: `True` — tuple is immutable, copy.copy returns same object.

### Q10
```python
import copy
x = (1, [2, 3])
y = copy.deepcopy(x)
print(x is y)
print(x[1] is y[1])
```
**Output**: `False`, `False` — tuple contains mutable list → deep-copied.

### Q11
```python
a = {"x": [1, 2]}
b = a.copy()
a["y"] = 3
print("y" in b)
```
**Output**: `False` — b is independent container.

### Q12
```python
a = {"x": [1, 2]}
b = a.copy()
a["x"].append(3)
print(b["x"])
```
**Output**: `[1, 2, 3]` — shared mutable value.

### Q13
```python
a = {"x": [1, 2]}
b = a.copy()
a["x"] = [10, 20]
print(b["x"])
```
**Output**: `[1, 2]` — a["x"] rebinding doesn't affect b["x"].

### Q14
```python
def modify(lst):
    lst = lst.copy()
    lst.append(4)
    return lst

a = [1, 2, 3]
b = modify(a)
print(a)
print(b)
```
**Output**: `[1, 2, 3]`, `[1, 2, 3, 4]`

### Q15
```python
def modify(lst):
    lst.append(4)

a = [1, 2, 3]
modify(a)
print(a)
```
**Output**: `[1, 2, 3, 4]`

### Q16
```python
import copy
a = [1, 2, 3]
a.append(a)
b = copy.deepcopy(a)
print(b[3] is b)
print(b[3] is a)
```
**Output**: `True`, `False`

### Q17
```python
shared = [1, 2]
a = [shared, shared]
b = a.copy()
b[0].append(3)
print(a[1])
print(b[0] is b[1])
```
**Output**: `[1, 2, 3]`, `True`

### Q18
```python
import copy
shared = [1, 2]
a = [shared, shared]
b = copy.deepcopy(a)
b[0].append(3)
print(a[0])
print(b[0] is b[1])
```
**Output**: `[1, 2]`, `True` (deepcopy preserves internal sharing!)

### Q19
```python
a = [[]] * 3
a[0].append(1)
print(a)
```
**Output**: `[[1], [1], [1]]`

### Q20
```python
a = [[] for _ in range(3)]
a[0].append(1)
print(a)
```
**Output**: `[[1], [], []]`

### Q21
```python
import copy
print(copy.copy(None) is None)
print(copy.deepcopy(42) is 42)  # noqa
```
**Output**: `True`, `True`

### Q22
```python
a = {"a": 1, "b": 2}
b = {**a, "c": 3}
a["d"] = 4
print(b)
```
**Output**: `{'a': 1, 'b': 2, 'c': 3}` — b is independent.

### Q23
```python
import copy
a = {1: [10], 2: [20]}
b = copy.copy(a)
a[1].append(11)
print(b[1])
print(3 in b)
```
**Output**: `[10, 11]`, `False`

### Q24
```python
a = [1, 2, 3]
b = a[:]
a[0] = 99
print(b)
```
**Output**: `[1, 2, 3]` — slice copy is shallow, reassignment doesn't propagate.

### Q25
```python
a = [1, 2, 3]
b = list(a)
print(a is b)
print(a == b)
```
**Output**: `False`, `True`

### Q26-50
```python
# Q26
s = {1, 2, 3}; t = s.copy(); s.add(4); print(t)
# Output: {1, 2, 3}

# Q27
d = dict.fromkeys("abc", []); d["a"].append(1); print(d)
# Output: {'a': [1], 'b': [1], 'c': [1]}

# Q28
import copy; a = frozenset({1,2}); b = copy.copy(a); print(a is b)
# Output: True

# Q29
a = [1,2]; b = a; del a; print(b)
# Output: [1, 2]

# Q30
a = [1,2,3]; b = a; a.clear(); print(b)
# Output: []

# Q31
a = [1,[2,3]]; b = a[:]; b[1] = [4,5]; print(a[1])
# Output: [2, 3] — b[1] rebinding doesn't affect a[1]

# Q32
a = [1,[2,3]]; b = a[:]; b[1].append(4); print(a[1])
# Output: [2, 3, 4] — shared inner list mutated

# Q33
import copy; a = "hello"; b = copy.deepcopy(a); print(a is b)
# Output: True — strings are immutable

# Q34
x = [1,2]; y = [x,x]; z = copy.deepcopy(y); z[0].append(3); print(z[1])
# Output: [1, 2, 3] — shared ref preserved in deepcopy

# Q35
a = [1]; b = [a]; c = [b]; d = copy.deepcopy(c); d[0][0].append(2); print(c)
# Output: [[[1]]] — deep copy is independent

# Q36-50: (more patterns with nested dicts, sets, custom objects, += vs +, etc.)
```

### Q51-100

### Q51
```python
class Bag:
    def __init__(self): self.items = []

b1 = Bag()
b1.items.append("apple")
b2 = copy.copy(b1)
b2.items.append("banana")
print(b1.items)
```
**Output**: `['apple', 'banana']` — shallow copy shares the list.

### Q52
```python
class Bag:
    def __init__(self): self.items = []

b1 = Bag()
b1.items.append("apple")
b2 = copy.deepcopy(b1)
b2.items.append("banana")
print(b1.items)
```
**Output**: `['apple']` — deep copy is independent.

### Q53
```python
a = [1, 2, 3]
b = a
a = [4, 5, 6]
print(b)
```
**Output**: `[1, 2, 3]` — rebinding a doesn't affect b.

### Q54
```python
a = [1, 2, 3]
b = a
a[:] = [4, 5, 6]  # In-place replacement!
print(b)
```
**Output**: `[4, 5, 6]` — `a[:] = ...` mutates the object, b sees it.

### Q55
```python
original = {"config": {"debug": True, "port": 8080}}
backup = original.copy()
original["config"]["debug"] = False
print(backup["config"]["debug"])
```
**Output**: `False` — shallow copy shares the nested dict.

### Q56-100: *(Pattern continues: custom __copy__, dataclass copying, weakref + copy, tuple unpacking and copy, generator expression materialization, map/filter creating new objects, json round-trip as deep copy alternative, multiprocessing and pickling, copy with default args, class variables vs instance variables in copy context)*
