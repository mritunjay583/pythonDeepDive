# Part 7 — Special Cases

## 7.1 Immutable Objects

Immutable objects are NEVER actually copied — the original is returned:

```python
import copy

# These all return the SAME object:
n = 42
copy.copy(n) is n        # True
copy.deepcopy(n) is n    # True

s = "hello"
copy.copy(s) is s        # True
copy.deepcopy(s) is s    # True

t = (1, 2, 3)
copy.copy(t) is t        # True
copy.deepcopy(t) is t    # True (all elements immutable!)

# BUT: tuple with mutable contents:
t = ([1, 2], [3, 4])
copy.copy(t) is t        # True (shallow copy of immutable → same)
copy.deepcopy(t) is t    # FALSE! Must deep-copy the mutable inner lists
```

**Rule**: `copy.copy()` of an immutable type always returns the same object. `copy.deepcopy()` of an immutable type returns the same object UNLESS it contains mutable elements.

---

## 7.2 Singletons

```python
# None, True, False — always the same object:
copy.deepcopy(None) is None    # True
copy.deepcopy(True) is True    # True
copy.deepcopy(False) is False  # True

# Ellipsis:
copy.deepcopy(...) is ...      # True

# NotImplemented:
copy.deepcopy(NotImplemented) is NotImplemented  # True
```

---

## 7.3 Functions and Lambdas

Functions are NOT deep-copied — the same function object is returned:

```python
def my_func():
    return 42

f = copy.deepcopy(my_func)
f is my_func  # True! Functions are treated as atomic.
```

Why? Functions reference their globals dict, module, code object, and closure cells. Copying all of that would essentially clone the entire module/environment — impractical and usually wrong.

---

## 7.4 Classes and Types

Type objects are not copied:

```python
class MyClass:
    pass

cls_copy = copy.deepcopy(MyClass)
cls_copy is MyClass  # True! Type objects are atomic for copying.
```

But instances ARE deep-copied:
```python
obj = MyClass()
obj.x = [1, 2, 3]

obj_copy = copy.deepcopy(obj)
obj_copy is obj        # False (new instance)
obj_copy.x is obj.x   # False (deep-copied attribute)
```

---

## 7.5 Modules

Modules are not copied:
```python
import os
os_copy = copy.deepcopy(os)
os_copy is os  # True
```

---

## 7.6 Files and I/O Objects

File objects and I/O streams cannot be meaningfully copied:

```python
f = open("test.txt")
try:
    f_copy = copy.copy(f)
except TypeError:
    print("Can't copy file objects!")  # Raises TypeError
```

They hold OS-level resources (file descriptors) that can't be duplicated through Python's copy mechanism. Use `os.dup()` if you need to duplicate a file descriptor.

---

## 7.7 Objects with __slots__

```python
class Point:
    __slots__ = ('x', 'y')
    def __init__(self, x, y):
        self.x = x
        self.y = y

p = Point(1, 2)
q = copy.copy(p)
# Works! copy uses __reduce__ which handles __slots__
q.x, q.y  # (1, 2)
p is q     # False
```

The copy module handles `__slots__` through the `__reduce__` protocol, which knows how to serialize/reconstruct slotted objects.

---

## 7.8 Dataclasses

```python
from dataclasses import dataclass
import copy

@dataclass
class Config:
    name: str
    items: list

c1 = Config("test", [1, 2, 3])
c2 = copy.copy(c1)      # New Config, shared items list
c3 = copy.deepcopy(c1)  # New Config, independent items list

c2.items.append(4)
print(c1.items)  # [1, 2, 3, 4] — shallow copy shares!

c3.items.append(5)
print(c1.items)  # [1, 2, 3, 4] — deep copy is independent
```

Frozen dataclasses:
```python
@dataclass(frozen=True)
class Point:
    x: int
    y: int

p = Point(1, 2)
q = copy.copy(p)
q is p  # True! Frozen → immutable → no copy needed
```

---

## 7.9 Weak References

```python
import weakref, copy

class Obj: pass

original = Obj()
ref = weakref.ref(original)

ref_copy = copy.deepcopy(ref)
# The weak reference is copied but points to... the COPY of original?
# Actually: deepcopy of weakref creates a weakref to the deepcopy of the target
# (if the target is also being deep-copied in the same operation)
```

Weak references in deep copy are tricky — behavior depends on whether the referent is also being copied in the same deepcopy operation.

---

## 7.10 Generators and Coroutines

```python
def gen():
    yield 1
    yield 2

g = gen()
next(g)  # 1

# Cannot copy generators:
try:
    copy.copy(g)
except TypeError:
    print("Can't copy generator!")
```

Generators contain execution state (stack frame, instruction pointer) that cannot be meaningfully duplicated.

---

## 7.11 Summary Table

| Object Type | copy.copy() | copy.deepcopy() |
|-------------|-------------|-----------------|
| int, float, str, bytes, bool | Returns same object | Returns same object |
| None, True, False, Ellipsis | Returns same object | Returns same object |
| tuple (immutable contents) | Returns same object | Returns same object |
| tuple (mutable contents) | Returns same object | New tuple, deep-copies elements |
| list | New list, shared elements | New list, deep-copies elements |
| dict | New dict, shared keys/values | New dict, deep-copies all |
| set | New set, shared elements | New set, deep-copies elements |
| frozenset | Returns same object | Returns same (or deep-copies if has mutables)* |
| Custom class instance | New instance, shallow __dict__ | New instance, deep __dict__ |
| Function/lambda | Returns same object | Returns same object |
| Class/type | Returns same object | Returns same object |
| Module | Returns same object | Returns same object |
| File/IO | TypeError | TypeError |
| Generator | TypeError | TypeError |

*frozenset elements are always immutable (hashable requirement), so typically returned as-is.

---

## 7.12 Interview Questions — Part 7

**Q1**: Does `copy.deepcopy(42)` create a new integer?
**A**: No. Returns the same int object. Immutable atomics are never actually copied.

**Q2**: Can you deepcopy a function?
**A**: deepcopy returns the same function object (not a copy). Functions are treated as atomic — copying their entire closure/globals environment would be impractical.

**Q3**: What happens when you deepcopy a tuple containing a list?
**A**: A NEW tuple is created with deep-copied elements. The inner list is independently copied. This is because the mutable list inside needs to be independent.

**Q4**: Can you copy a generator?
**A**: No. Raises TypeError. Generators have internal execution state (stack frame) that cannot be meaningfully duplicated.

**Q5**: How do frozen dataclasses interact with copy?
**A**: `copy.copy()` of a frozen dataclass returns the same object (it's immutable). `copy.deepcopy()` also returns the same object if all fields are immutable.
