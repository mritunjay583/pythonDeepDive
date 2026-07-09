# Part 5 — copy Module Internals

## 5.1 Source Location

The entire `copy` module is in `Lib/copy.py` — it's pure Python, about 300 lines. No C code needed because it builds on top of existing object protocols.

---

## 5.2 copy.copy() Dispatch

```python
# Lib/copy.py (actual logic, simplified):
def copy(x):
    cls = type(x)
    
    # 1. Try __copy__ protocol
    copier = getattr(cls, "__copy__", None)
    if copier:
        return copier(x)
    
    # 2. Check the dispatch table for known types
    reductor = getattr(x, "__reduce_ex__", None)
    rv = reductor(4)
    # 4 = pickle protocol 4 (highest)
    
    # 3. Reconstruct from reduction
    return _reconstruct(x, None, *rv)
```

The dispatch table handles built-in types specially:
```python
# Built-in types that are their own shallow copy (immutables):
_copy_dispatch = {}
# Immutables: copy returns the same object
for t in (type(None), int, float, bool, complex, str, bytes,
          frozenset, type, range, slice, type(Ellipsis), type(NotImplemented)):
    _copy_dispatch[t] = _copy_immutable

def _copy_immutable(x):
    return x  # Just return the same object — it's immutable!
```

---

## 5.3 copy.deepcopy() Dispatch

```python
def deepcopy(x, memo=None, _nil=[]):
    if memo is None:
        memo = {}
    
    d = id(x)
    y = memo.get(d, _nil)
    if y is not _nil:
        return y  # Already copied!
    
    cls = type(x)
    
    # 1. Try reduction-based copying
    if issubclass(cls, type):
        y = _deepcopy_atomic(x, memo)  # Types are not copied
    else:
        copier = getattr(x, "__deepcopy__", None)
        if copier is not None:
            y = copier(memo)
        else:
            reductor = getattr(x, "__reduce_ex__", None)
            rv = reductor(4)
            y = _reconstruct(x, memo, *rv)
    
    # Register in memo (if not already)
    if id(x) not in memo:
        memo[d] = y
    
    return y
```

---

## 5.4 The __reduce__ Protocol

For types that don't have special `__copy__`/`__deepcopy__` methods, the copy module uses the **pickle protocol** (`__reduce_ex__`/`__reduce__`) to decompose and reconstruct objects.

```python
# What __reduce_ex__ returns:
# (callable, args)                    → callable(*args) creates the copy
# (callable, args, state)             → callable(*args); obj.__setstate__(state)
# (callable, args, state, list_items) → + extend with list_items
# (callable, args, state, list_items, dict_items) → + update with dict_items

# Example for a list:
[1, 2, 3].__reduce_ex__(4)
# Returns something like: (list, (), None, iter([1, 2, 3]))
# Reconstruction: list() → [] → extend with [1, 2, 3]
```

This means any picklable object is automatically copyable!

---

## 5.5 Custom Copy Support

### Implementing `__copy__`:
```python
class MyClass:
    def __init__(self, data, metadata):
        self.data = data
        self.metadata = metadata
        self._cache = {}  # Don't want to copy cache!
    
    def __copy__(self):
        # Create new instance without copying cache
        new = MyClass.__new__(MyClass)
        new.data = self.data          # Shared reference (shallow)
        new.metadata = self.metadata  # Shared reference
        new._cache = {}               # Fresh empty cache
        return new
```

### Implementing `__deepcopy__`:
```python
class MyClass:
    def __deepcopy__(self, memo):
        new = MyClass.__new__(MyClass)
        memo[id(self)] = new  # Register BEFORE recursing!
        new.data = copy.deepcopy(self.data, memo)
        new.metadata = copy.deepcopy(self.metadata, memo)
        new._cache = {}  # Fresh cache, not deep-copied
        return new
```

### Using `__copy_replace__` (Python 3.13+):
```python
# PEP 708: for dataclass-like copy with field replacement
import copy
new_obj = copy.replace(obj, field1=new_value1)
```

---

## 5.6 How Built-in Types Handle Copying

### list:
```python
# copy.copy(list) → list.copy() → list_slice (C-level memcpy of pointers)
# copy.deepcopy(list) → new list + deepcopy each element
```

### dict:
```python
# copy.copy(dict) → dict.copy() → new dict with same key/value refs
# copy.deepcopy(dict) → new dict + deepcopy each key + deepcopy each value
```

### tuple:
```python
# copy.copy(tuple) → returns SAME tuple (immutable!)
# copy.deepcopy(tuple):
#   If all elements are immutable → return same tuple
#   If any element is mutable → new tuple(deepcopy(elem) for elem in t)
```

### set:
```python
# copy.copy(set) → set.copy() → new set with same element refs
# copy.deepcopy(set) → new set + deepcopy each element
```

### Custom objects (with __dict__):
```python
# copy.copy(obj):
#   new = cls.__new__(cls)
#   new.__dict__.update(obj.__dict__)  # Shallow copy of attributes
#   return new

# copy.deepcopy(obj):
#   new = cls.__new__(cls)
#   memo[id(obj)] = new
#   new.__dict__ = deepcopy(obj.__dict__, memo)  # Deep copy all attributes
#   return new
```

---

## 5.7 The _reconstruct Function

```python
# Simplified version of _reconstruct from Lib/copy.py:
def _reconstruct(x, memo, func, args, state=None, listiter=None, dictiter=None):
    # Create base object:
    y = func(*args)
    
    # Register in memo:
    if memo is not None:
        memo[id(x)] = y
    
    # Restore state:
    if state is not None:
        if hasattr(y, '__setstate__'):
            y.__setstate__(state)
        else:
            # Default: update __dict__
            y.__dict__.update(state)
    
    # Restore list items:
    if listiter is not None:
        for item in listiter:
            y.append(item)  # or deepcopy(item) for deep copy
    
    # Restore dict items:
    if dictiter is not None:
        for key, value in dictiter:
            y[key] = value
    
    return y
```

---

## 5.8 Interview Questions — Part 5

**Q1**: Where is the copy module implemented?
**A**: `Lib/copy.py` — pure Python, ~300 lines. Uses the pickle protocol (__reduce__) for generic object copying.

**Q2**: How does copy.copy() decide how to copy an object?
**A**: 1) Check for `__copy__` method. 2) For known immutable types, return the same object. 3) Fall back to `__reduce_ex__` + reconstruction.

**Q3**: Why can any picklable object be copied?
**A**: The copy module uses the same `__reduce__` protocol as pickle to decompose objects into constructor + args + state, then reconstructs them. If you can pickle it, you can copy it.

**Q4**: What's the difference between `__copy__` and `__deepcopy__`?
**A**: `__copy__` implements shallow copy (called by `copy.copy()`). `__deepcopy__(memo)` implements deep copy (called by `copy.deepcopy()`). The memo parameter enables cycle detection.

**Q5**: Does `copy.copy()` actually copy immutable objects?
**A**: No. For int, str, float, bool, None, frozenset — it returns the exact same object. Immutables don't need copying.
