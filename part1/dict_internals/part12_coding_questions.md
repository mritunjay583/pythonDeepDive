# Part 12 — Coding Questions (100 Output Prediction)

### Q1
```python
d = {"a": 1, "b": 2}
d["c"] = 3
print(list(d.keys()))
```
**Output**: `['a', 'b', 'c']` — insertion order preserved.

### Q2
```python
d = {"a": 1, "b": 2, "c": 3}
del d["b"]
d["b"] = 4
print(list(d.keys()))
```
**Output**: `['a', 'c', 'b']` — deleted key re-inserted at end.

### Q3
```python
d = {}
d[1] = "one"
d[True] = "true"
print(d)
```
**Output**: `{1: 'true'}` — `True == 1` and `hash(True) == hash(1)`, so same key. Value overwritten.

### Q4
```python
d = {}
d[0] = "zero"
d[False] = "false"
print(d)
print(len(d))
```
**Output**: `{0: 'false'}` then `1` — `False == 0`, same key.

### Q5
```python
a = {"x": 1}
b = a
b["y"] = 2
print(a)
```
**Output**: `{'x': 1, 'y': 2}` — `b = a` is alias, not copy.

### Q6
```python
a = {"x": 1, "y": 2}
b = a.copy()
b["z"] = 3
print(a)
print(b)
```
**Output**: `{'x': 1, 'y': 2}` then `{'x': 1, 'y': 2, 'z': 3}` — shallow copy is independent.

### Q7
```python
a = {"x": [1, 2]}
b = a.copy()
b["x"].append(3)
print(a["x"])
```
**Output**: `[1, 2, 3]` — shallow copy shares mutable values.

### Q8
```python
d = dict.fromkeys(["a", "b", "c"], [])
d["a"].append(1)
print(d)
```
**Output**: `{'a': [1], 'b': [1], 'c': [1]}` — all keys share same list object!

### Q9
```python
d = {k: [] for k in ["a", "b", "c"]}
d["a"].append(1)
print(d)
```
**Output**: `{'a': [1], 'b': [], 'c': []}` — comprehension creates independent lists.

### Q10
```python
d = {"a": 1, "b": 2, "c": 3}
print(d.pop("b"))
print(d)
```
**Output**: `2` then `{'a': 1, 'c': 3}`.

### Q11
```python
d = {"a": 1, "b": 2}
print(d.get("c", "default"))
print(d)
```
**Output**: `default` then `{'a': 1, 'b': 2}` — get doesn't modify dict.

### Q12
```python
d = {"a": 1, "b": 2}
d.setdefault("c", 3)
d.setdefault("a", 99)
print(d)
```
**Output**: `{'a': 1, 'b': 2, 'c': 3}` — setdefault doesn't overwrite existing.

### Q13
```python
d1 = {"a": 1, "b": 2}
d2 = {"b": 3, "c": 4}
d3 = {**d1, **d2}
print(d3)
```
**Output**: `{'a': 1, 'b': 3, 'c': 4}` — d2's "b" wins (later overrides).

### Q14
```python
d = {"a": 1, "b": 2, "c": 3}
for k in list(d.keys()):
    if k == "b":
        del d[k]
print(d)
```
**Output**: `{'a': 1, 'c': 3}` — safe because iterating over list copy.

### Q15
```python
d = {"a": 1, "b": 2, "c": 3}
try:
    for k in d:
        del d[k]
except RuntimeError as e:
    print("Error!")
print(d)
```
**Output**: `Error!` then `{'b': 2, 'c': 3}` — deleting during iteration raises RuntimeError after first deletion.

### Q16
```python
d = {"a": 1}
keys = d.keys()
d["b"] = 2
print(list(keys))
```
**Output**: `['a', 'b']` — views are dynamic (reflect current state).

### Q17
```python
d = {"a": 1, "b": 2, "c": 3}
print(d.popitem())
print(d)
```
**Output**: `('c', 3)` then `{'a': 1, 'b': 2}` — popitem removes LAST item (LIFO, 3.7+).

### Q18
```python
print({} == {})
print({} is {})
```
**Output**: `True` then `False` — equal but different objects.

### Q19
```python
a = {1: "a", 2: "b"}
b = {2: "b", 1: "a"}
print(a == b)
```
**Output**: `True` — dict equality ignores order.

### Q20
```python
from collections import OrderedDict
a = OrderedDict([(1, "a"), (2, "b")])
b = OrderedDict([(2, "b"), (1, "a")])
print(a == b)
```
**Output**: `False` — OrderedDict equality IS order-sensitive.

### Q21
```python
d = {"a": 1, "b": 2}
d.update(b=3, c=4)
print(d)
```
**Output**: `{'a': 1, 'b': 3, 'c': 4}` — update with kwargs, "b" overwritten.

### Q22
```python
d = {"a": 1, "b": 2, "c": 3}
print({v: k for k, v in d.items()})
```
**Output**: `{1: 'a', 2: 'b', 3: 'c'}` — reversed key/value.

### Q23
```python
print(hash("hello") == hash("hello"))
```
**Output**: `True` — same string always same hash within one process.

### Q24
```python
d = {}
d[(1, 2)] = "tuple key"
print(d[(1, 2)])
```
**Output**: `tuple key` — tuples are hashable, valid keys.

### Q25
```python
try:
    d = {}
    d[[1, 2]] = "list key"
except TypeError as e:
    print(f"Error: {e}")
```
**Output**: `Error: unhashable type: 'list'`

### Q26
```python
s = {1, 2, 3}
print(2 in s)
print(4 in s)
```
**Output**: `True` then `False`.

### Q27
```python
a = {1, 2, 3}
b = {2, 3, 4}
print(a & b)
print(a | b)
print(a - b)
```
**Output**: `{2, 3}` then `{1, 2, 3, 4}` then `{1}`.

### Q28
```python
a = {1, 2, 3}
b = {1, 2}
print(b <= a)
print(b < a)
print(a <= a)
```
**Output**: `True` `True` `True` — subset checks.

### Q29
```python
s = {1, 2, 3}
s.add(2)
print(s)
print(len(s))
```
**Output**: `{1, 2, 3}` then `3` — adding existing element does nothing.

### Q30
```python
s = set()
s.add((1, 2))
s.add(frozenset({3, 4}))
print(len(s))
```
**Output**: `2` — tuples and frozensets are hashable.

### Q31
```python
d = {"a": 1, "b": 2}
k = d.keys()
print(k & {"a", "c"})
```
**Output**: `{'a'}` — dict_keys supports set operations.

### Q32
```python
from collections import defaultdict
d = defaultdict(list)
d["x"].append(1)
d["x"].append(2)
d["y"].append(3)
print(dict(d))
```
**Output**: `{'x': [1, 2], 'y': [3]}`.

### Q33
```python
from collections import Counter
c = Counter("abracadabra")
print(c.most_common(3))
```
**Output**: `[('a', 5), ('b', 2), ('r', 2)]`.

### Q34
```python
d = {"a": 1}
print(d.get("a") is not None)
print(d.get("b") is not None)
```
**Output**: `True` then `False`.

### Q35
```python
d = {"a": None}
print("a" in d)
print(d.get("a", "missing"))
```
**Output**: `True` then `None` — key exists, value is None.

### Q36
```python
d = {"a": 1, "b": 2, "c": 3}
filtered = {k: v for k, v in d.items() if v > 1}
print(filtered)
```
**Output**: `{'b': 2, 'c': 3}`.

### Q37
```python
a = {1, 2, 3}
b = a
b.add(4)
print(a)
```
**Output**: `{1, 2, 3, 4}` — alias, same set object.

### Q38
```python
a = {1, 2, 3}
b = a.copy()
b.add(4)
print(a)
```
**Output**: `{1, 2, 3}` — copy is independent.

### Q39
```python
print(type({}))
print(type(set()))
```
**Output**: `<class 'dict'>` then `<class 'set'>`.

### Q40
```python
d = {"a": 1, "b": 2}
x = d.pop("c", None)
print(x)
print(d)
```
**Output**: `None` then `{'a': 1, 'b': 2}` — pop with default doesn't raise.

### Q41-50 (Sets and Frozensets)

### Q41
```python
s = frozenset({1, 2, 3})
d = {s: "frozen"}
print(d[frozenset({3, 2, 1})])
```
**Output**: `frozen` — frozenset equality is order-independent.

### Q42
```python
a = {1, 2, 3}
a.discard(5)
print(a)
```
**Output**: `{1, 2, 3}` — discard silently ignores missing elements.

### Q43
```python
a = {1, 2, 3}
try:
    a.remove(5)
except KeyError:
    print("not found")
```
**Output**: `not found`.

### Q44
```python
a = {1, 2, 3, 4, 5}
b = {4, 5, 6, 7, 8}
print(a ^ b)
```
**Output**: `{1, 2, 3, 6, 7, 8}` — symmetric difference.

### Q45
```python
a = {1, 2, 3}
a.update([3, 4, 5])
print(a)
```
**Output**: `{1, 2, 3, 4, 5}`.

### Q46
```python
print({1, 2, 3} == {3, 2, 1})
```
**Output**: `True` — set equality is order-independent.

### Q47
```python
d = dict(zip("abc", range(3)))
print(d)
```
**Output**: `{'a': 0, 'b': 1, 'c': 2}`.

### Q48
```python
d = {"a": 1, "b": 2}
print("a" in d)
print(1 in d)
print("a" in d.values())
```
**Output**: `True` `False` `False` — `in` checks keys by default. 1 is not a key. "a" is not a value.

### Q49
```python
class Obj:
    def __init__(self, val):
        self.val = val
    def __hash__(self):
        return hash(self.val)
    def __eq__(self, other):
        return self.val == other.val

d = {Obj(1): "a", Obj(1): "b"}
print(len(d))
print(d[Obj(1)])
```
**Output**: `1` then `b` — both Obj(1) have same hash and are equal, second overwrites first.

### Q50
```python
d = {"a": 1, "b": 2}
items = list(d.items())
d.clear()
print(items)
print(d)
```
**Output**: `[('a', 1), ('b', 2)]` then `{}` — list was created before clear.

### Q51-100 (Advanced patterns)

### Q51
```python
nested = {"a": {"x": 1}}
shallow = nested.copy()
shallow["a"]["x"] = 99
print(nested["a"]["x"])
```
**Output**: `99` — shallow copy shares inner dict.

### Q52
```python
import copy
nested = {"a": {"x": 1}}
deep = copy.deepcopy(nested)
deep["a"]["x"] = 99
print(nested["a"]["x"])
```
**Output**: `1` — deepcopy is fully independent.

### Q53
```python
d = {"a": 1, "b": 2, "c": 3}
result = {k: v**2 for k, v in d.items()}
print(result)
```
**Output**: `{'a': 1, 'b': 4, 'c': 9}`.

### Q54
```python
keys = ["a", "b", "a", "c", "b"]
d = {}
for k in keys:
    d[k] = d.get(k, 0) + 1
print(d)
```
**Output**: `{'a': 2, 'b': 2, 'c': 1}` — manual counting.

### Q55
```python
d1 = {"a": 1}
d2 = {"b": 2}
d1 |= d2
print(d1)
print(d2)
```
**Output**: `{'a': 1, 'b': 2}` then `{'b': 2}` — `|=` modifies d1 in-place.

### Q56
```python
d = {"a": 1, "b": 2, "c": 3}
print(list(reversed(d)))
```
**Output**: `['c', 'b', 'a']` — reversed iteration (3.8+).

### Q57
```python
class MyDict(dict):
    def __missing__(self, key):
        return f"{key} not found"

d = MyDict(a=1, b=2)
print(d["c"])
print("c" in d)
```
**Output**: `c not found` then `False` — `__missing__` provides fallback but doesn't insert.

### Q58
```python
d = {"a": 1, "b": 2, "c": 3}
keys_view = d.keys()
d["d"] = 4
print(len(keys_view))
```
**Output**: `4` — view reflects current state.

### Q59
```python
s1 = {1, 2, 3}
s2 = s1
s1 = s1 | {4, 5}
print(s2)
```
**Output**: `{1, 2, 3}` — `|` creates NEW set, rebinds s1. s2 still references old set.

### Q60
```python
s1 = {1, 2, 3}
s2 = s1
s1 |= {4, 5}
print(s2)
```
**Output**: `{1, 2, 3, 4, 5}` — `|=` modifies in-place (for sets). s2 is alias.

### Q61
```python
d = {}
d[float('nan')] = 1
d[float('nan')] = 2
print(len(d))
```
**Output**: `2` — NaN != NaN and different objects, so different keys!

### Q62
```python
d = {}
nan = float('nan')
d[nan] = 1
d[nan] = 2
print(len(d))
print(d[nan])
```
**Output**: `1` then `2` — SAME nan object, identity check passes → same key, value overwritten.

### Q63
```python
print(hash(1) == hash(1.0))
print({1: "int", 1.0: "float"})
```
**Output**: `True` then `{1: 'float'}` — 1==1.0, same key, float value wins.

### Q64
```python
d = {"a": 1, "b": 2}
e = {"b": 2, "a": 1}
print(d == e)
print(list(d) == list(e))
```
**Output**: `True` then `False` — equality ignores order, but list() preserves it.

### Q65
```python
d = {}
d["first"] = 1
d["second"] = 2
d["first"] = 10
print(list(d.keys()))
```
**Output**: `['first', 'second']` — updating existing key doesn't change position.

### Q66
```python
s = {3, 1, 4, 1, 5, 9}
print(len(s))
```
**Output**: `5` — duplicates removed: {1, 3, 4, 5, 9}.

### Q67
```python
d = {i: i**2 for i in range(5)}
print(d)
```
**Output**: `{0: 0, 1: 1, 2: 4, 3: 9, 4: 16}`.

### Q68
```python
a = {"x": 1}
b = {"x": 1}
print(a == b)
print(a is b)
```
**Output**: `True` then `False`.

### Q69
```python
d = {"a": 1, "b": 2}
x, y = d
print(x, y)
```
**Output**: `a b` — unpacking dict gives keys.

### Q70
```python
d = {"a": 1, "b": 2, "c": 3}
print(max(d))
print(min(d))
```
**Output**: `c` then `a` — max/min on keys (lexicographic for strings).

### Q71
```python
d = {"a": 3, "b": 1, "c": 2}
print(max(d, key=d.get))
```
**Output**: `a` — key with maximum value.

### Q72
```python
d = {"a": 1, "b": 2, "c": 3}
print(sum(d.values()))
```
**Output**: `6`.

### Q73
```python
words = ["apple", "banana", "apple", "cherry", "banana", "apple"]
freq = {}
for w in words:
    freq[w] = freq.get(w, 0) + 1
print(freq)
```
**Output**: `{'apple': 3, 'banana': 2, 'cherry': 1}`.

### Q74
```python
d = {"a": 1, "b": 2, "c": 3}
inverted = dict(zip(d.values(), d.keys()))
print(inverted)
```
**Output**: `{1: 'a', 2: 'b', 3: 'c'}`.

### Q75
```python
from collections import ChainMap
base = {"a": 1, "b": 2}
overlay = {"b": 3, "c": 4}
combined = ChainMap(overlay, base)
print(combined["a"])
print(combined["b"])
```
**Output**: `1` then `3` — overlay wins for "b".

### Q76-100: More Advanced

### Q76
```python
d = {0: "a", 1: "b", 2: "c"}
print(d.get(True))
```
**Output**: `b` — `True == 1`, so looks up key 1.

### Q77
```python
s = {frozenset({1,2}), frozenset({2,1})}
print(len(s))
```
**Output**: `1` — `frozenset({1,2}) == frozenset({2,1})` and same hash.

### Q78
```python
d = {}
keys = d.keys()
d[1] = "one"
for k in keys:
    print(k)
```
**Output**: `1` — view sees additions.

### Q79
```python
d = {"a": 1, "b": 2}
print(d | {"c": 3})
print(d)
```
**Output**: `{'a': 1, 'b': 2, 'c': 3}` then `{'a': 1, 'b': 2}` — `|` creates new dict.

### Q80
```python
a = {1: "one"}
b = {1: "ONE", 2: "TWO"}
print(a | b)
print(b | a)
```
**Output**: `{1: 'ONE', 2: 'TWO'}` then `{1: 'one', 2: 'TWO'}` — right operand wins.

### Q81
```python
d = {"hello": 1, "world": 2}
print(sorted(d))
```
**Output**: `['hello', 'world']` — sorted keys.

### Q82
```python
d1 = {"a": [1, 2]}
d2 = d1.copy()
d1["a"] = [3, 4]
print(d2["a"])
```
**Output**: `[1, 2]` — reassigning d1["a"] doesn't affect d2 (shallow copy copied the pointer, then d1 replaced its pointer).

### Q83
```python
d = {"a": {"nested": True}}
keys = list(d.keys())
d.clear()
print(keys)
```
**Output**: `['a']` — list was created before clear.

### Q84
```python
s = set("hello")
print(sorted(s))
```
**Output**: `['e', 'h', 'l', 'o']` — set removes duplicate 'l'.

### Q85
```python
a = {1, 2, 3}
b = {1, 2, 3}
print(a == b)
print(a is b)
```
**Output**: `True` then `False`.

### Q86
```python
d = dict(enumerate("abc"))
print(d)
```
**Output**: `{0: 'a', 1: 'b', 2: 'c'}`.

### Q87
```python
s = {i % 3 for i in range(10)}
print(s)
```
**Output**: `{0, 1, 2}`.

### Q88
```python
d = {"a": 1, "b": 2}
d2 = dict(d, c=3, b=99)
print(d2)
```
**Output**: `{'a': 1, 'b': 99, 'c': 3}` — kwargs override.

### Q89
```python
s = set()
s.add(s)
```
**Output**: `TypeError: unhashable type: 'set'` — can't add mutable set to itself.

### Q90
```python
d = {"a": 1}
print(d.setdefault("b"))
print(d)
```
**Output**: `None` then `{'a': 1, 'b': None}` — default value defaults to None.

### Q91
```python
s1 = {1, 2, 3}
s2 = {2, 3, 4}
s1.intersection_update(s2)
print(s1)
```
**Output**: `{2, 3}` — in-place intersection.

### Q92
```python
d = {chr(i): i for i in range(97, 100)}
print(d)
```
**Output**: `{'a': 97, 'b': 98, 'c': 99}`.

### Q93
```python
print(bool({}))
print(bool(set()))
print(bool({0: False}))
```
**Output**: `False` `False` `True` — non-empty containers are truthy.

### Q94
```python
d = {"a": 1, "b": 2, "c": 3}
print(list(d)[-1])
```
**Output**: `c` — last key (insertion order).

### Q95
```python
class Point:
    def __init__(self, x, y): self.x, self.y = x, y
    def __hash__(self): return hash((self.x, self.y))
    def __eq__(self, other): return (self.x, self.y) == (other.x, other.y)

d = {Point(1,2): "A"}
print(d[Point(1,2)])
```
**Output**: `A` — equal objects with same hash find the entry.

### Q96
```python
d = {}
for i in range(5):
    d[i] = i * 10
    
del d[1]
del d[3]
print(list(d.keys()))
```
**Output**: `[0, 2, 4]` — remaining keys in insertion order.

### Q97
```python
a = {"x": 1}
b = a
a = {"y": 2}
print(b)
```
**Output**: `{'x': 1}` — rebinding `a` doesn't affect `b`.

### Q98
```python
d = {"a": 1, "b": 2}
try:
    print(d["c"])
except KeyError as e:
    print(repr(e))
```
**Output**: `KeyError('c')`.

### Q99
```python
s = {1, 2, 3}
t = s
s = s - {2}
print(t)
```
**Output**: `{1, 2, 3}` — `-` creates new set, rebinds `s`. `t` still references old.

### Q100
```python
import copy
original = {"a": {1, 2}, "b": [3, 4]}
shallow = original.copy()
deep = copy.deepcopy(original)

original["a"].add(3)
original["b"].append(5)

print(shallow["a"])
print(shallow["b"])
print(deep["a"])
print(deep["b"])
```
**Output**:
```
{1, 2, 3}
[3, 4, 5]
{1, 2}
[3, 4]
```
Shallow copy shares mutable values. Deep copy is fully independent.
