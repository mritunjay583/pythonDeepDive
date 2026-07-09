# Part 3 — The Iterator Protocol

## 3.1 The Complete Protocol Specification

The iterator protocol is defined by two dunder methods and one exception:

```python
class Iterator:
    def __iter__(self):
        """Return the iterator object itself.
        Required so iterators can be used in for loops."""
        return self
    
    def __next__(self):
        """Return the next item. Raise StopIteration when exhausted.
        This is the heart of the protocol."""
        if self._has_more():
            return self._get_next()
        raise StopIteration
```

At the C level, this maps to two slots in `PyTypeObject`:
```c
typedef struct _typeobject {
    // ...
    getiterfunc tp_iter;       // __iter__: returns iterator
    iternextfunc tp_iternext;  // __next__: returns next value (NULL + StopIteration on end)
    // ...
} PyTypeObject;

// Signatures:
typedef PyObject *(*getiterfunc)(PyObject *);           // Takes self, returns iterator
typedef PyObject *(*iternextfunc)(PyObject *);          // Takes self, returns next or NULL
```

**Important C convention**: `tp_iternext` returns `NULL` to signal exhaustion. The `StopIteration` exception is set internally but the NULL return is what ceval.c checks (faster than exception checking).

---

## 3.2 How `iter()` and `next()` Call the Protocol

```c
// Built-in iter():
PyObject *PyObject_GetIter(PyObject *o) {
    PyTypeObject *t = Py_TYPE(o);
    
    // Check tp_iter slot:
    if (t->tp_iter == NULL) {
        // Fallback: old __getitem__ protocol
        if (t->tp_as_sequence && t->tp_as_sequence->sq_item)
            return PySeqIter_New(o);
        TypeError("object is not iterable");
    }
    
    PyObject *res = (*t->tp_iter)(o);  // Call __iter__
    
    // Verify result is actually an iterator:
    if (!PyIter_Check(res)) {
        TypeError("iter() returned non-iterator");
    }
    return res;
}

// Built-in next():
PyObject *builtin_next(PyObject *self, PyObject *args) {
    PyObject *it = args[0];
    PyObject *res = (*Py_TYPE(it)->tp_iternext)(it);  // Call __next__
    
    if (res == NULL) {
        if (nargs == 2) {
            // next(it, default) — return default instead of raising
            PyErr_Clear();
            return args[1];
        }
        // next(it) — let StopIteration propagate
        if (!PyErr_Occurred())
            PyErr_SetNone(PyExc_StopIteration);
        return NULL;
    }
    return res;
}
```

---

## 3.3 The for Loop Protocol Implementation

```python
for x in iterable:
    body(x)
else:
    else_clause()
```

Is equivalent to:
```python
_iterator = iter(iterable)      # 1. Get iterator (calls __iter__)
_exhausted = False
while True:
    try:
        x = next(_iterator)     # 2. Get next value (calls __next__)
    except StopIteration:
        _exhausted = True
        break                   # 3. StopIteration → exit loop
    body(x)                     # 4. Process value
if _exhausted:
    else_clause()               # 5. else runs if loop completed normally
```

At the bytecode level (see Part 4 for detailed walkthrough):
```
GET_ITER                 # Call iter(iterable), push iterator
FOR_ITER <exit>          # Call next(iterator), push value or jump to <exit>
STORE_FAST x             # Store value in x
... body ...
JUMP_BACKWARD <FOR_ITER> # Loop back to FOR_ITER
<exit>:
END_FOR                  # Clean up iterator from stack
... else clause ...
```

---

## 3.4 StopIteration: The Termination Mechanism

StopIteration is a special exception:
- It's the ONLY way an iterator signals exhaustion
- It's caught by `for` loops (and comprehensions, `map`, `filter`, etc.)
- It MUST be raised by `__next__()` — returning a special sentinel value is NOT the protocol

```python
# How the for loop catches StopIteration (ceval.c FOR_ITER logic):
# 
# result = tp_iternext(iterator)
# if (result == NULL) {
#     if (PyErr_ExceptionMatches(PyExc_StopIteration)) {
#         PyErr_Clear()           ← swallow the exception
#         JUMP to exit_label      ← end the loop
#     } else {
#         goto error              ← propagate other exceptions!
#     }
# }
# PUSH(result)                    ← push value for STORE_FAST
```

**Critical**: Only StopIteration ends the loop cleanly. Any OTHER exception (ValueError, TypeError, etc.) propagates up as a real error.

---

## 3.5 Protocol Verification

```python
# How to check if something follows the protocol:
from collections.abc import Iterator, Iterable

# Structural check (duck typing):
hasattr(obj, '__iter__')              # Iterable?
hasattr(obj, '__iter__') and hasattr(obj, '__next__')  # Iterator?

# ABC check (isinstance):
isinstance(obj, Iterable)    # Has __iter__
isinstance(obj, Iterator)    # Has __iter__ AND __next__

# C-level check:
# PyIter_Check(obj) — checks tp_iternext != NULL
```

---

## 3.6 The Old Sequence Protocol (Fallback)

For backward compatibility, if an object has `__getitem__` but no `__iter__`, it's still iterable:

```python
class OldStyle:
    def __getitem__(self, index):
        if index >= 3:
            raise IndexError
        return index * 10

for x in OldStyle():
    print(x)  # 0, 10, 20

# CPython creates a PySeqIter (sequence iterator) that calls __getitem__(0), (1), (2), ...
# until IndexError is raised.
```

This fallback exists for pre-PEP 234 code. New code should always implement `__iter__`.

---

## 3.7 Protocol Relationships Diagram

```
                    ┌──────────────┐
                    │   Iterable   │ has __iter__()
                    └──────┬───────┘
                           │ __iter__() returns
                           ▼
                    ┌──────────────┐
                    │   Iterator   │ has __iter__() AND __next__()
                    └──────┬───────┘
                           │ __next__() returns
                           ▼
              ┌────────────┴────────────┐
              │                         │
       value (normal)          StopIteration (exhausted)
              │                         │
              ▼                         ▼
     for loop body              for loop exit


Types that are ITERABLES (not iterators):
  list, tuple, dict, set, str, range, frozenset

Types that are ITERATORS (and therefore also iterables):
  list_iterator, generator, file, map, filter, zip, enumerate
  dict_keyiterator, range_iterator, str_iterator
```

---

## 3.8 Interview Questions — Part 3

**Q1**: What are the three components of the iterator protocol?
**A**: `__iter__()` (return iterator), `__next__()` (return next value), and `StopIteration` (signal exhaustion). At C level: `tp_iter`, `tp_iternext`, and NULL return.

**Q2**: Why does `tp_iternext` return NULL instead of using exception-only signaling?
**A**: Performance. Checking a NULL pointer is one CPU instruction. Checking for a set exception is much more expensive. The for loop's hot path just checks `if (result == NULL)`.

**Q3**: What happens if `__next__` raises ValueError instead of StopIteration?
**A**: The for loop does NOT catch it — it propagates as a real exception. Only StopIteration terminates the loop cleanly.

**Q4**: Does the old `__getitem__` protocol still work?
**A**: Yes, as a fallback. If an object has `__getitem__` but no `__iter__`, CPython creates a PySeqIter that calls `__getitem__(0)`, `__getitem__(1)`, etc. until IndexError.

**Q5**: Why must iterators return `self` from `__iter__()`?
**A**: So they can be used anywhere an iterable is expected. `for x in my_iterator` calls `iter(my_iterator)` → must return the iterator itself for the loop to work.
