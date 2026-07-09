# Part 15B — Coding Questions (Output Prediction) — Questions 51-100

---

### Q51: Nested Deepcopy Independence
```python
import copy
a = [1, [2, [3, [4]]]]
b = copy.deepcopy(a)
a[1][1][1][0] = 99
print(b)
```
**Output**: `[1, [2, [3, [4]]]]`
**Why**: Deep copy creates fully independent nested structure.

---

### Q52: Self-Referential List
```python
a = [1, 2]
a.append(a)
print(a[2][2][0])
```
**Output**: `1`
**Why**: `a[2]` is `a` itself. `a[2][2]` is also `a`. `a[2][2][0]` is `a[0]` = 1.

---

### Q53: del vs remove
```python
a = [1, 2, 3, 4, 5]
del a[1]
a.remove(4)
print(a)
```
**Output**: `[1, 3, 5]`
**Why**: `del a[1]` removes index 1 (value 2). Then `remove(4)` finds and removes 4.

---

### Q54: Slice Assignment Grows List
```python
a = [1, 2, 3]
a[1:2] = [10, 20, 30, 40]
print(a)
print(len(a))
```
**Output**:
```
[1, 10, 20, 30, 40, 3]
6
```
**Why**: Replacing 1 element (index 1) with 4 elements. List grows by 3.

---

### Q55: Slice Assignment Shrinks List
```python
a = [1, 2, 3, 4, 5, 6]
a[1:5] = [99]
print(a)
```
**Output**: `[1, 99, 6]`
**Why**: Replacing 4 elements with 1. List shrinks by 3.

---

### Q56: Extended Slice Assignment
```python
a = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
a[::3] = ['a', 'b', 'c', 'd']
print(a)
```
**Output**: `['a', 1, 2, 'b', 4, 5, 'c', 7, 8, 'd']`
**Why**: `a[::3]` selects indices 0,3,6,9. Replaced with a,b,c,d respectively.

---

### Q57: Sort with key
```python
a = ['banana', 'Apple', 'cherry']
a.sort()
print(a)
a.sort(key=str.lower)
print(a)
```
**Output**:
```
['Apple', 'banana', 'cherry']
['Apple', 'banana', 'cherry']
```
**Why**: Default sort is case-sensitive ('A' < 'b'). key=str.lower makes it case-insensitive. Same result here by coincidence.

---

### Q58: Reverse Sort
```python
a = [3, 1, 4, 1, 5, 9]
b = sorted(a, reverse=True)
print(b)
print(a)
```
**Output**:
```
[9, 5, 4, 3, 1, 1]
[3, 1, 4, 1, 5, 9]
```
**Why**: sorted returns new descending list. Original unchanged.

---

### Q59: Shallow Copy with Tuple Elements
```python
a = [(1, 2), (3, 4)]
b = a.copy()
b[0] = (5, 6)
print(a)
```
**Output**: `[(1, 2), (3, 4)]`
**Why**: Replacing the pointer at `b[0]` doesn't affect `a[0]`. Tuples are immutable so the shared issue doesn't arise.

---

### Q60: Comprehension with Condition
```python
a = [x**2 for x in range(10) if x % 3 == 0]
print(a)
```
**Output**: `[0, 9, 36, 81]`
**Why**: x values where x%3==0: 0,3,6,9. Squared: 0,9,36,81.

---

### Q61: Unpacking
```python
a = [1, 2, 3, 4, 5]
first, *middle, last = a
print(first, middle, last)
```
**Output**: `1 [2, 3, 4] 5`
**Why**: Star unpacking collects the middle into a new list.

---

### Q62: Nested List Identity
```python
a = [1, 2]
b = [a, a]
b[0] is b[1]
a.append(3)
print(b)
```
**Output**: `[[1, 2, 3], [1, 2, 3]]`
**Why**: Both b[0] and b[1] point to same object `a`.

---

### Q63: list() from String
```python
a = list("hello")
print(a)
```
**Output**: `['h', 'e', 'l', 'l', 'o']`
**Why**: Iterates over characters of the string.

---

### Q64: Concatenation Creates New
```python
a = [1, 2]
b = [3, 4]
c = a + b
a.append(5)
print(c)
```
**Output**: `[1, 2, 3, 4]`
**Why**: `c` is a new list created at concat time. Later mutation of `a` doesn't affect it.

---

### Q65: enumerate and modify
```python
a = [10, 20, 30]
for i, v in enumerate(a):
    a[i] = v * 2
print(a)
```
**Output**: `[20, 40, 60]`
**Why**: Modifying existing indices (not adding/removing) during iteration is safe.

---

### Q66: Filter with remove in loop (bug)
```python
a = [1, 2, 3, 4, 5, 6]
for x in a:
    if x % 2 == 0:
        a.remove(x)
print(a)
```
**Output**: `[1, 3, 5]`? Actually: `[1, 3, 5]` works here by luck, but NOT reliable.
**Typical actual output**: `[1, 3, 5]` (happens to work for this specific data)
**Why**: Removing during iteration skips elements. This pattern is a BUG even when it appears to work.

---

### Q67: Assignment to Slice vs Index
```python
a = [1, 2, 3, 4, 5]
a[2:3] = [10, 20]
print(a)  # [1, 2, 10, 20, 4, 5]

b = [1, 2, 3, 4, 5]
b[2] = [10, 20]
print(b)  # [1, 2, [10, 20], 4, 5]
```
**Output**:
```
[1, 2, 10, 20, 4, 5]
[1, 2, [10, 20], 4, 5]
```
**Why**: Slice assignment unpacks the RHS. Index assignment stores the object itself.

---

### Q68: map vs comprehension
```python
a = [1, 2, 3]
b = list(map(str, a))
c = [str(x) for x in a]
print(b == c)
print(type(b[0]))
```
**Output**:
```
True
<class 'str'>
```

---

### Q69: Walrus in Comprehension
```python
a = [1, 2, 3, 4, 5, 6]
b = [y for x in a if (y := x**2) > 10]
print(b)
```
**Output**: `[16, 25, 36]`
**Why**: y is assigned x**2. Only included if y > 10. So 4^2=16, 5^2=25, 6^2=36.

---

### Q70: Copy of Slice
```python
a = [1, 2, 3, 4, 5]
b = a[1:4]
c = b
b.append(99)
print(a)
print(c)
```
**Output**:
```
[1, 2, 3, 4, 5]
[2, 3, 4, 99]
```
**Why**: b is a copy of a's slice (independent). c is alias of b. Appending to b shows in c, not a.

---

### Q71: Multiple Assignment
```python
a = [1, 2, 3]
a[0], a[1], a[2] = a[2], a[0], a[1]
print(a)
```
**Output**: `[3, 1, 2]`
**Why**: RHS evaluated first (tuple of values 3,1,2), then assigned. No intermediate corruption.

---

### Q72: Truthiness
```python
a = [[]]
b = [0]
c = [None]
print(bool(a), bool(b), bool(c))
```
**Output**: `True True True`
**Why**: Non-empty lists are truthy regardless of what they contain.

---

### Q73: sort() Stability Demo
```python
a = [(2,'b'), (1,'a'), (2,'a'), (1,'b')]
a.sort(key=lambda x: x[0])
print(a)
```
**Output**: `[(1, 'a'), (1, 'b'), (2, 'b'), (2, 'a')]`
**Why**: Stable sort preserves original relative order for equal keys. (1,'a') was before (1,'b'), and (2,'b') was before (2,'a').

---

### Q74: List * and Identity
```python
a = [1, 2]
b = a * 3
a.append(3)
print(b)
print(a)
```
**Output**:
```
[1, 2, 1, 2, 1, 2]
[1, 2, 3]
```
**Why**: `a * 3` creates NEW list with copies of pointers at that moment. Later mutation of `a` doesn't affect `b`.

---

### Q75: Pass by Reference
```python
def modify(lst):
    lst.append(4)
    lst = [10, 20, 30]
    lst.append(40)

a = [1, 2, 3]
modify(a)
print(a)
```
**Output**: `[1, 2, 3, 4]`
**Why**: `lst.append(4)` modifies the original. `lst = [...]` rebinds local name — doesn't affect `a`. The second append is on the local list.

---

### Q76: Return List Mutation
```python
def get_list():
    return [1, 2, 3]

a = get_list()
b = get_list()
print(a is b)
a.append(4)
print(b)
```
**Output**:
```
False
[1, 2, 3]
```
**Why**: Each call creates a new list. They're independent.

---

### Q77: Comprehension with Side Effect
```python
counter = []
result = [counter.append(x) for x in range(5)]
print(result)
print(counter)
```
**Output**:
```
[None, None, None, None, None]
[0, 1, 2, 3, 4]
```
**Why**: `append()` returns None. The comprehension collects those Nones. Side effect fills counter.

---

### Q78: in with Sublist
```python
a = [[1, 2], [3, 4], [5, 6]]
print([1, 2] in a)
print([1, 3] in a)
print(1 in a)
```
**Output**:
```
True
False
False
```
**Why**: `in` checks for equal elements. [1,2]==[1,2]→True. 1 is not an element of `a` (elements are lists).

---

### Q79: List from dict
```python
d = {'a': 1, 'b': 2, 'c': 3}
print(list(d))
print(list(d.values()))
print(list(d.items()))
```
**Output**:
```
['a', 'b', 'c']
[1, 2, 3]
[('a', 1), ('b', 2), ('c', 3)]
```

---

### Q80: Negative Slice
```python
a = [0, 1, 2, 3, 4, 5]
print(a[-3:])
print(a[:-2])
print(a[-4:-1])
```
**Output**:
```
[3, 4, 5]
[0, 1, 2, 3]
[2, 3, 4]
```

---

### Q81: Slice Beyond Bounds
```python
a = [1, 2, 3]
print(a[1:100])
print(a[-100:2])
print(a[100:200])
```
**Output**:
```
[2, 3]
[1, 2]
[]
```
**Why**: Slice indices are clamped to valid range. No IndexError.

---

### Q82: Shallow Copy and Immutables
```python
a = [1, "hello", (1,2)]
b = a.copy()
a[0] = 99
a[1] = "world"
print(b)
```
**Output**: `[1, 'hello', (1, 2)]`
**Why**: Shallow copy copies pointers. But reassigning in `a` only changes `a`'s pointers. `b` still has original pointers to immutable objects.

---

### Q83: append vs extend Performance Semantics
```python
a = []
a.append('abc')
print(a)

b = []
b.extend('abc')
print(b)
```
**Output**:
```
['abc']
['a', 'b', 'c']
```
**Why**: append adds the whole object. extend iterates over the iterable (string → characters).

---

### Q84: Chained Indexing
```python
a = [[1,2,3], [4,5,6], [7,8,9]]
print(a[1][2])
a[0][1] = 99
print(a)
```
**Output**:
```
6
[[1, 99, 3], [4, 5, 6], [7, 8, 9]]
```

---

### Q85: range to list
```python
a = list(range(5, 0, -1))
print(a)
```
**Output**: `[5, 4, 3, 2, 1]`

---

### Q86: sum of lists
```python
lists = [[1,2], [3,4], [5,6]]
result = sum(lists, [])
print(result)
```
**Output**: `[1, 2, 3, 4, 5, 6]`
**Why**: sum with start=[] does `[] + [1,2] + [3,4] + [5,6]`. Creates intermediates (O(n^2) — don't do this for large lists).

---

### Q87: Slice Assignment with Iterable
```python
a = [1, 2, 3]
a[1:2] = range(10, 14)
print(a)
```
**Output**: `[1, 10, 11, 12, 13, 3]`
**Why**: Slice assignment accepts any iterable on RHS.

---

### Q88: Equality with Different Types
```python
print([1, 2, 3] == (1, 2, 3))
print([1, 2, 3] == [1, 2, 3])
```
**Output**:
```
False
True
```
**Why**: List == Tuple is always False (different types).

---

### Q89: Mixed sort key
```python
a = ['b', 'A', 'c', 'B', 'a', 'C']
a.sort(key=lambda x: (x.lower(), x.isupper()))
print(a)
```
**Output**: `['a', 'A', 'b', 'B', 'c', 'C']`
**Why**: Sorts by lowercase letter first, then by case (lowercase before upper since False < True).

---

### Q90: Deletion in Reverse (safe pattern)
```python
a = [1, 2, 3, 4, 5, 6]
for i in range(len(a)-1, -1, -1):
    if a[i] % 2 == 0:
        del a[i]
print(a)
```
**Output**: `[1, 3, 5]`
**Why**: Deleting in reverse order is safe — shifted elements are already processed.

---

### Q91: List as Stack
```python
stack = []
stack.append('a')
stack.append('b')
stack.append('c')
print(stack.pop())
print(stack.pop())
print(stack)
```
**Output**:
```
c
b
['a']
```

---

### Q92: Circular Reference Print
```python
a = [1, 2]
a.append(a)
print(a)
```
**Output**: `[1, 2, [...]]`
**Why**: Python's repr detects cycles and shows `[...]` instead of infinite recursion.

---

### Q93: Comprehension Order
```python
result = [(x, y) for x in range(3) for y in range(3) if x != y]
print(result)
```
**Output**: `[(0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1)]`

---

### Q94: all() and any() with lists
```python
a = [1, 2, 0, 3]
print(all(a))
print(any(a))
b = [0, '', None]
print(all(b))
print(any(b))
```
**Output**:
```
False
True
False
False
```

---

### Q95: list.copy() vs assignment in function
```python
def process(data):
    local = data
    local.append(99)
    return local

original = [1, 2, 3]
result = process(original)
print(original)
print(result is original)
```
**Output**:
```
[1, 2, 3, 99]
True
```
**Why**: No copy made. `local` is alias. Modification affects original.

---

### Q96: Multiple del
```python
a = [0, 1, 2, 3, 4, 5]
del a[5]
del a[3]
del a[1]
print(a)
```
**Output**: `[0, 2, 4]`
**Why**: After del a[5]: [0,1,2,3,4]. After del a[3]: [0,1,2,4]. After del a[1]: [0,2,4].

---

### Q97: Nested Multiplication
```python
a = [[0] * 3 for _ in range(2)]
a[0][0] = 1
print(a)

b = [[0] * 3] * 2
b[0][0] = 1
print(b)
```
**Output**:
```
[[1, 0, 0], [0, 0, 0]]
[[1, 0, 0], [1, 0, 0]]
```
**Why**: Inner `[0]*3` creates independent lists per row in comprehension. Outer `*2` copies the reference.

---

### Q98: sort vs sorted types
```python
a = (3, 1, 2)
# a.sort()  # AttributeError: tuple has no sort
b = sorted(a)
print(b)
print(type(b))
```
**Output**:
```
[1, 2, 3]
<class 'list'>
```
**Why**: `sorted()` always returns a list, regardless of input type.

---

### Q99: Interning and List Identity
```python
a = [256, 257]
b = [256, 257]
print(a[0] is b[0])
print(a[1] is b[1])
```
**Output**:
```
True
False
```
**Why**: 256 is in the small int cache (shared). 257 is not cached (separate objects).
**Note**: In practice, CPython may intern 257 within the same code block (compile-time constant folding). Result may vary by context.

---

### Q100: The Grand Finale — Everything Combined
```python
import copy

original = [[1, 2], [3, 4]]
alias = original
shallow = original.copy()
deep = copy.deepcopy(original)

original[0].append(5)
original.append([6, 7])

print(f"original: {original}")
print(f"alias:    {alias}")
print(f"shallow:  {shallow}")
print(f"deep:     {deep}")
print(f"alias is original: {alias is original}")
print(f"shallow[0] is original[0]: {shallow[0] is original[0]}")
print(f"deep[0] is original[0]: {deep[0] is original[0]}")
```
**Output**:
```
original: [[1, 2, 5], [3, 4], [6, 7]]
alias:    [[1, 2, 5], [3, 4], [6, 7]]
shallow:  [[1, 2, 5], [3, 4]]
deep:     [[1, 2], [3, 4]]
alias is original: True
shallow[0] is original[0]: True
deep[0] is original[0]: False
```
**Why**:
- `alias`: same object, sees ALL changes
- `shallow`: different list, but shares inner lists. Sees `[1,2,5]` (inner mutated) but NOT `[6,7]` (outer append)
- `deep`: fully independent. Sees nothing.
