# Part 15A — Coding Questions (Output Prediction) — Questions 1-50

## Instructions
For each question, predict the output WITHOUT running the code. Then verify.

---

### Q1: Basic Aliasing
```python
a = [1, 2, 3]
b = a
b.append(4)
print(a)
```
**Output**: `[1, 2, 3, 4]`
**Why**: `b = a` creates an alias. Both names reference the same list object.

---

### Q2: Copy Independence
```python
a = [1, 2, 3]
b = a.copy()
b.append(4)
print(a)
print(b)
```
**Output**:
```
[1, 2, 3]
[1, 2, 3, 4]
```
**Why**: `.copy()` creates a new list. Mutations to `b` don't affect `a`.

---

### Q3: Nested Aliasing
```python
a = [[1, 2], [3, 4]]
b = a.copy()
b[0].append(5)
print(a)
```
**Output**: `[[1, 2, 5], [3, 4]]`
**Why**: Shallow copy copies pointers. `b[0]` and `a[0]` point to same inner list.

---

### Q4: Multiplication Trap
```python
a = [[0]] * 3
a[0][0] = 1
print(a)
```
**Output**: `[[1], [1], [1]]`
**Why**: `*3` replicates the pointer. All three slots reference the same `[0]` list.

---

### Q5: Comprehension vs Multiplication
```python
a = [[0] for _ in range(3)]
a[0][0] = 1
print(a)
```
**Output**: `[[1], [0], [0]]`
**Why**: Comprehension creates three independent lists.

---

### Q6: += vs + for Aliases
```python
a = [1, 2, 3]
b = a
a += [4, 5]
print(b)
```
**Output**: `[1, 2, 3, 4, 5]`
**Why**: `+=` calls `extend` in-place. `b` is alias to same object, so sees the change.

---

### Q7: + Rebinding
```python
a = [1, 2, 3]
b = a
a = a + [4, 5]
print(b)
print(a is b)
```
**Output**:
```
[1, 2, 3]
False
```
**Why**: `a + [4,5]` creates new list, rebinds `a`. `b` still points to old list.

---

### Q8: Slice Assignment
```python
a = [1, 2, 3, 4, 5]
a[1:3] = [10, 20, 30]
print(a)
```
**Output**: `[1, 10, 20, 30, 4, 5]`
**Why**: Replaces 2 items (indices 1,2) with 3 items. List grows by 1.

---

### Q9: Delete Slice
```python
a = [1, 2, 3, 4, 5]
del a[1:4]
print(a)
```
**Output**: `[1, 5]`
**Why**: Removes elements at indices 1, 2, 3.

---

### Q10: Identity After Append
```python
a = [1, 2, 3]
id_before = id(a)
a.append(4)
a.append(5)
a.extend([6, 7, 8, 9, 10])
print(id(a) == id_before)
```
**Output**: `True`
**Why**: The list object never moves. Only the internal ob_item array may move.

---

### Q11: sort() Return Value
```python
a = [3, 1, 2]
b = a.sort()
print(b)
print(a)
```
**Output**:
```
None
[1, 2, 3]
```
**Why**: `sort()` sorts in-place and returns None. The sorted result is in `a`.

---

### Q12: sorted() Creates New List
```python
a = [3, 1, 2]
b = sorted(a)
print(a)
print(b)
print(a is b)
```
**Output**:
```
[3, 1, 2]
[1, 2, 3]
False
```
**Why**: `sorted()` returns a new list. Original unchanged.

---

### Q13: reverse() Return Value
```python
a = [1, 2, 3]
b = a.reverse()
print(b)
print(a)
```
**Output**:
```
None
[3, 2, 1]
```
**Why**: `reverse()` modifies in-place, returns None.

---

### Q14: Chained Assignment
```python
a = b = [1, 2, 3]
a.append(4)
print(b)
```
**Output**: `[1, 2, 3, 4]`
**Why**: `a = b = [1,2,3]` both reference same object.

---

### Q15: extend vs append
```python
a = [1, 2, 3]
a.extend([4, 5])
print(a)

b = [1, 2, 3]
b.append([4, 5])
print(b)
```
**Output**:
```
[1, 2, 3, 4, 5]
[1, 2, 3, [4, 5]]
```
**Why**: `extend` adds each element. `append` adds the list itself as one element.

---

### Q16: Slice Step
```python
a = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
print(a[::3])
print(a[1::2])
print(a[::-1])
```
**Output**:
```
[0, 3, 6, 9]
[1, 3, 5, 7, 9]
[9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
```

---

### Q17: Nested List Copy Behavior
```python
import copy
a = [[1, 2], [3, 4]]
b = copy.copy(a)
c = copy.deepcopy(a)
a[0].append(5)
print(b[0])
print(c[0])
```
**Output**:
```
[1, 2, 5]
[1, 2]
```
**Why**: Shallow copy shares inner lists. Deep copy creates independent ones.

---

### Q18: List in Default Argument
```python
def foo(x, lst=[]):
    lst.append(x)
    return lst

print(foo(1))
print(foo(2))
print(foo(3))
```
**Output**:
```
[1]
[1, 2]
[1, 2, 3]
```
**Why**: Default `[]` is created once at function definition. All calls share it.

---

### Q19: is vs ==
```python
a = [1, 2, 3]
b = [1, 2, 3]
print(a == b)
print(a is b)
```
**Output**:
```
True
False
```
**Why**: `==` compares contents. `is` compares identity (they're different objects).

---

### Q20: Empty List is
```python
a = []
b = []
print(a is b)
print(a == b)
```
**Output**:
```
False
True
```
**Why**: Each `[]` creates a new object. No interning for lists.

---

### Q21: Slice Creates New Object
```python
a = [1, 2, 3]
b = a[:]
print(a == b)
print(a is b)
```
**Output**:
```
True
False
```

---

### Q22: Index Assignment
```python
a = [1, 2, 3]
b = a
a[0] = 99
print(b)
```
**Output**: `[99, 2, 3]`
**Why**: `b` is alias. Index assignment mutates the shared object.

---

### Q23: Append vs Concatenation Identity
```python
a = [1, 2]
original_id = id(a)
a = a + [3]
print(id(a) == original_id)
```
**Output**: `False`
**Why**: `a + [3]` creates NEW list. Rebinds `a` to new object.

---

### Q24: Append Preserves Identity
```python
a = [1, 2]
original_id = id(a)
a.append(3)
print(id(a) == original_id)
```
**Output**: `True`
**Why**: append modifies in-place. Object doesn't move.

---

### Q25: Nested Mutation Through Alias
```python
inner = [1, 2]
outer = [inner, inner]
outer[0].append(3)
print(outer)
print(inner)
```
**Output**:
```
[[1, 2, 3], [1, 2, 3]]
[1, 2, 3]
```
**Why**: Both outer[0] and outer[1] point to same `inner` object.

---

### Q26: List Comparison
```python
print([1, 2, 3] < [1, 2, 4])
print([1, 2, 3] < [1, 2, 3, 0])
print([1, 2, 3] == [1, 2, 3])
```
**Output**:
```
True
True
True
```
**Why**: Lexicographic comparison. Shorter prefix is "less than" longer.

---

### Q27: pop() Behavior
```python
a = [10, 20, 30, 40]
x = a.pop()
y = a.pop(0)
print(x, y, a)
```
**Output**: `40 10 [20, 30]`
**Why**: `pop()` removes last (40). `pop(0)` removes first (10).

---

### Q28: insert Beyond Bounds
```python
a = [1, 2, 3]
a.insert(100, 4)
a.insert(-100, 0)
print(a)
```
**Output**: `[0, 1, 2, 3, 4]`
**Why**: insert clamps index. 100 → end, -100 → beginning.

---

### Q29: remove Only First
```python
a = [1, 2, 3, 2, 1]
a.remove(2)
print(a)
```
**Output**: `[1, 3, 2, 1]`
**Why**: `remove` deletes only the FIRST occurrence.

---

### Q30: clear vs del
```python
a = [1, 2, 3]
b = a
a.clear()
print(b)
print(a is b)
```
**Output**:
```
[]
True
```
**Why**: `clear()` empties the same object. `b` still aliases it.

---

### Q31: del Rebinds
```python
a = [1, 2, 3]
b = a
del a
print(b)
# print(a)  # NameError
```
**Output**: `[1, 2, 3]`
**Why**: `del a` removes the name binding. The object lives on via `b`.

---

### Q32: List of References to Same Int
```python
a = [1] * 5
print(a[0] is a[1])
```
**Output**: `True`
**Why**: All slots point to the same cached int(1) object.

---

### Q33: Comprehension Scope
```python
x = 10
a = [x for x in range(5)]
print(x)
```
**Output**: `10`
**Why**: In Python 3, comprehension variable `x` doesn't leak to enclosing scope.

---

### Q34: Enumerate Modification
```python
a = [1, 2, 3, 4, 5]
for i, v in enumerate(a):
    if v % 2 == 0:
        del a[i]
print(a)
```
**Output**: `[1, 3, 5]` (but behavior is unpredictable — modifying during iteration!)
**Actual typical output**: `[1, 3, 5]` in this specific case, but DON'T rely on it.
**Why**: Deleting shifts indices. May skip elements. This is a bug pattern.

---

### Q35: Extend With Self
```python
a = [1, 2, 3]
a.extend(a)
print(a)
```
**Output**: `[1, 2, 3, 1, 2, 3]`
**Why**: CPython handles self-extension correctly by copying items before modifying.

---

### Q36: Sort Stability
```python
data = [(1, 'b'), (2, 'a'), (1, 'a'), (2, 'b')]
data.sort(key=lambda x: x[0])
print(data)
```
**Output**: `[(1, 'b'), (1, 'a'), (2, 'a'), (2, 'b')]`
**Why**: Stable sort preserves original order for equal keys.

---

### Q37: Boolean List
```python
a = [[], (), 0, '', None, 1, 'a', [0]]
b = [x for x in a if x]
print(b)
```
**Output**: `[1, 'a', [0]]`
**Why**: Empty containers, 0, '', None are falsy. [0] is truthy (non-empty).

---

### Q38: Slice Assignment with Empty
```python
a = [1, 2, 3, 4, 5]
a[2:2] = [10, 20]
print(a)
```
**Output**: `[1, 2, 10, 20, 3, 4, 5]`
**Why**: `a[2:2]` is empty slice at position 2. Inserting without removing.

---

### Q39: Multiple Return
```python
def f():
    return [1, 2], [3, 4]

a, b = f()
a.append(5)
print(b)
```
**Output**: `[3, 4]`
**Why**: Two independent lists returned. Modifying `a` doesn't affect `b`.

---

### Q40: Nested comprehension
```python
matrix = [[1,2,3],[4,5,6],[7,8,9]]
flat = [x for row in matrix for x in row]
print(flat)
```
**Output**: `[1, 2, 3, 4, 5, 6, 7, 8, 9]`

---

### Q41: in-place vs new
```python
a = [3, 1, 2]
b = a
a.sort()
print(b)
print(a is b)
```
**Output**:
```
[1, 2, 3]
True
```
**Why**: sort() is in-place. b is alias, sees the sorted result.

---

### Q42: Slice of Slice
```python
a = [0, 1, 2, 3, 4, 5]
b = a[1:5]
c = b[1:3]
print(c)
a[2] = 99
print(c)
```
**Output**:
```
[2, 3]
[2, 3]
```
**Why**: Each slice is a copy. Modifying `a` doesn't affect `b` or `c`.

---

### Q43: list() Constructor
```python
a = [1, 2, 3]
b = list(a)
print(a is b)
print(a[0] is b[0])
```
**Output**:
```
False
True
```
**Why**: `list(a)` creates new list (shallow copy). Elements are shared.

---

### Q44: Multiplication with Mutable Default
```python
class Item:
    def __init__(self):
        self.value = 0

items = [Item()] * 3
items[0].value = 42
print(items[1].value)
```
**Output**: `42`
**Why**: All three slots reference the same Item instance.

---

### Q45: Extend Changes Length During Iteration?
```python
a = [1, 2, 3]
for x in a:
    if x == 2:
        a.extend([4, 5])
print(a)
```
**Output**: `[1, 2, 3, 4, 5]`
**Note**: The iterator sees size change and continues iterating (includes new elements). Behavior is implementation-defined and dangerous.

---

### Q46: index() with start
```python
a = [1, 2, 3, 2, 1]
print(a.index(2))
print(a.index(2, 2))
```
**Output**:
```
1
3
```
**Why**: First call finds 2 at index 1. Second starts searching from index 2, finds at 3.

---

### Q47: count()
```python
a = [1, [1], 1, '1', True]
print(a.count(1))
print(a.count(True))
```
**Output**:
```
3
3
```
**Why**: `True == 1` in Python. So `1`, `1`, and `True` all match both `1` and `True`.

---

### Q48: None Sorting
```python
a = [3, None, 1]
try:
    a.sort()
    print(a)
except TypeError as e:
    print(f"Error: {e}")
```
**Output**: `Error: '<' not supported between instances of 'NoneType' and 'int'`
**Why**: Python 3 doesn't allow comparison between incompatible types.

---

### Q49: zip and unzip
```python
a = [1, 2, 3]
b = ['a', 'b', 'c']
zipped = list(zip(a, b))
print(zipped)
a2, b2 = zip(*zipped)
print(list(a2))
```
**Output**:
```
[(1, 'a'), (2, 'b'), (3, 'c')]
[1, 2, 3]
```

---

### Q50: *= Operator
```python
a = [1, 2]
b = a
a *= 3
print(a)
print(b)
print(a is b)
```
**Output**:
```
[1, 2, 1, 2, 1, 2]
[1, 2, 1, 2, 1, 2]
True
```
**Why**: `*=` modifies in-place (calls `__imul__`). `b` is alias, sees change.
