# Part 2 — Iterable vs Iterator

## 2.1 The Two Distinct Concepts

This is the most important distinction in Python's iteration system:

```
ITERABLE:  "I can produce an iterator"
           → has __iter__() method that returns an iterator
           → Examples: list, dict, str, set, range, file

ITERATOR:  "I can produce the next value"
           → has __next__() method that returns next value or raises StopIteration
           → has __iter__() that returns self (iterators ARE iterables too)
           → Examples: list_iterator, dict_keyiterator, generator, file object
```

```python
data = [10, 20, 30]  # ITERABLE (has __iter__)
it = iter(data)       # ITERATOR (has __iter__ AND __next__)

type(data)  # <class 'list'>
type(it)    # <class 'list_iterator'>

# Iterable can produce MANY iterators:
it1 = iter(data)  # Independent iterator 1
it2 = iter(data)  # Independent iterator 2

# Iterator produces values:
next(it1)  # 10
next(it1)  # 20
next(it2)  # 10 (independent!)

# Iterator IS an iterable (returns self):
iter(it1) is it1  # True!
```

---

## 2.2 Why They're Separate

### Iterables are reusable:
```python
data = [1, 2, 3]
for x in data:  # Works
    pass
for x in data:  # Works AGAIN! (new iterator each time)
    pass
```

### Iterators are one-shot:
```python
it = iter([1, 2, 3])
for x in it:    # Works (consumes all values)
    pass
for x in it:    # EMPTY! Iterator is exhausted!
    pass

# Generators are iterators (one-shot):
gen = (x**2 for x in range(3))
list(gen)  # [0, 1, 4]
list(gen)  # [] — exhausted!
```

---

## 2.3 The Protocol in Detail

### `__iter__()` — "Give me an iterator"

```python
# For containers (iterables that are NOT iterators):
class MyList:
    def __iter__(self):
        return MyListIterator(self)  # Returns NEW iterator each time!

# For iterators:
class MyListIterator:
    def __iter__(self):
        return self  # Returns SELF (iterator is its own iterable)
```

### `__next__()` — "Give me the next value"

```python
class MyListIterator:
    def __init__(self, data):
        self._data = data
        self._index = 0
    
    def __iter__(self):
        return self
    
    def __next__(self):
        if self._index >= len(self._data):
            raise StopIteration  # Signal: no more values
        value = self._data[self._index]
        self._index += 1
        return value
```

### `StopIteration` — The Termination Signal

```python
it = iter([10, 20])
next(it)  # 10
next(it)  # 20
next(it)  # raises StopIteration (NOT IndexError!)

# StopIteration is caught by for loops:
for x in iter([10, 20]):
    print(x)  # 10, 20 — loop ends cleanly on StopIteration

# You can provide a default to avoid StopIteration:
next(it, "default")  # "default" (instead of raising)
```

---

## 2.4 Memory Diagram

```python
data = [10, 20, 30]
it = iter(data)
next(it)  # 10
```

```
'data' ──→ PyListObject
            │ ob_item → [ptr→10, ptr→20, ptr→30]
            │ ob_size = 3

'it'   ──→ PyListIterObject
            │ it_seq → (same PyListObject as data) ────→ data's list
            │ it_index = 1  (already returned index 0)
            │
            │ After next(it):
            │   reads it_seq->ob_item[it_index] → 20
            │   it_index becomes 2

Relationship:
  list (iterable) ←── referenced by ──── list_iterator (iterator)
  The iterator holds a REFERENCE to the list (keeps it alive).
  The iterator has its own STATE (index).
  The list is UNMODIFIED by iteration.
```

---

## 2.5 The iter() Built-in

```python
# Form 1: iter(iterable) → calls iterable.__iter__()
iter([1,2,3])     # → list_iterator
iter("hello")     # → str_iterator
iter({1,2,3})     # → set_iterator
iter(range(10))   # → range_iterator

# Form 2: iter(callable, sentinel) → calls callable() until sentinel returned
# Creates a special "callable_iterator"
import random
# Roll dice until we get 6:
for roll in iter(lambda: random.randint(1,6), 6):
    print(roll)  # Prints rolls until 6 is rolled (6 is NOT printed)
```

### iter() at C level:
```c
// Python/bltinmodule.c
PyObject *builtin_iter(PyObject *self, PyObject *args) {
    if (nargs == 1) {
        return PyObject_GetIter(v);  // Calls v.__iter__()
    }
    // Two-arg form: iter(callable, sentinel)
    return PyCallIter_New(callable, sentinel);
}

// PyObject_GetIter:
PyObject *PyObject_GetIter(PyObject *o) {
    PyTypeObject *t = Py_TYPE(o);
    if (t->tp_iter) {
        PyObject *res = (*t->tp_iter)(o);  // Call type's tp_iter slot
        // Verify result has __next__:
        if (!PyIter_Check(res)) { TypeError... }
        return res;
    }
    // Fallback: old sequence protocol (__getitem__)
    return PySeqIter_New(o);
}
```

---

## 2.6 Checking Iterable vs Iterator

```python
from collections.abc import Iterable, Iterator

# Iterable: has __iter__
isinstance([1,2,3], Iterable)    # True
isinstance("hello", Iterable)    # True
isinstance(42, Iterable)         # False

# Iterator: has __iter__ AND __next__
isinstance(iter([1,2,3]), Iterator)  # True
isinstance([1,2,3], Iterator)        # False! List is iterable, not iterator.

# Key check at C level:
# tp_iter slot != NULL → iterable
# tp_iternext slot != NULL → iterator
```

---

## 2.7 Common Confusion Points

### "Is a generator an iterable or an iterator?"
```python
def gen():
    yield 1; yield 2

g = gen()  # Generator OBJECT — it's an ITERATOR (and therefore also an iterable)
type(g)    # <class 'generator'>

# Generator object:
#   Has __next__: yes → iterator ✓
#   Has __iter__ (returns self): yes → iterable ✓
#   Reusable? NO — once exhausted, done.
#   Can you call gen() again? YES — creates a NEW generator object.

# So:
# gen (the function) — neither iterable nor iterator (it's a generator FUNCTION)
# gen() (the result) — an iterator (single-use, has __next__)
```

### "Is a file an iterable or an iterator?"
```python
f = open("file.txt")
# It's BOTH! f has __iter__ (returns self) AND __next__ (returns next line)
# This means: files are ITERATORS (one-shot)
# You CAN'T iterate a file twice (without seeking to beginning)

iter(f) is f  # True — file IS its own iterator
```

---

## 2.8 The Iterator Contract

```
For an object to be a VALID ITERATOR it must satisfy:
1. __iter__() returns self
2. __next__() returns a value OR raises StopIteration
3. Once StopIteration is raised, ALL subsequent __next__() calls must also raise StopIteration
   (iterators must be "sticky" once exhausted — no resurrection!)
4. The iterator should hold a reference to its data source (keeps it alive)
```

Rule 3 is important:
```python
it = iter([1, 2])
next(it)  # 1
next(it)  # 2
next(it)  # StopIteration
next(it)  # StopIteration (AGAIN — must stay exhausted!)
next(it)  # StopIteration (forever after)
```

---

## 2.9 Interview Questions — Part 2

**Q1**: What's the difference between an iterable and an iterator?
**A**: An iterable has `__iter__()` that returns an iterator. An iterator has `__iter__()` (returns self) + `__next__()` (returns next value or raises StopIteration). Iterables are reusable (produce fresh iterators). Iterators are one-shot (track position internally).

**Q2**: Is a list an iterator?
**A**: No. A list is an ITERABLE. `iter(list)` returns a `list_iterator` which IS an iterator. The list itself doesn't have `__next__()`.

**Q3**: Why does an iterator's `__iter__()` return self?
**A**: So iterators can be used anywhere an iterable is expected (in for loops, passed to functions expecting iterables). `for x in iterator` works because for calls `iter(iterator)` which returns the iterator itself.

**Q4**: What happens if you iterate twice over an iterator vs an iterable?
**A**: Iterable: second iteration works (creates new iterator). Iterator: second iteration yields nothing (already exhausted, StopIteration immediately).

**Q5**: What does `iter(callable, sentinel)` do?
**A**: Creates a special iterator that calls `callable()` repeatedly. Each call's result is yielded. When the result equals `sentinel`, StopIteration is raised (sentinel itself is NOT yielded).
