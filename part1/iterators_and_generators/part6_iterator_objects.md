# Part 6 — Iterator Objects (C Structures)

## 6.1 PyListIterObject

```c
typedef struct {
    PyObject_HEAD              // 16 bytes
    Py_ssize_t it_index;      // 8 bytes: current position
    PyListObject *it_seq;     // 8 bytes: reference to list (NULL when exhausted)
} _PyListIterObject;          // Total: 32 bytes

// Memory diagram after `it = iter([10, 20, 30]); next(it)`:
//
// 'it' → _PyListIterObject
//          it_index = 1  (already yielded index 0)
//          it_seq → [10, 20, 30] (list still alive, refcnt increased)
//
// After exhaustion: it_seq = NULL, Py_DECREF(list)
```

---

## 6.2 PyDictIterObject

```c
typedef struct {
    PyObject_HEAD              // 16 bytes
    PyDictObject *di_dict;    // 8 bytes: the dict
    Py_ssize_t di_used;       // 8 bytes: dict size at iter creation
    Py_ssize_t di_pos;        // 8 bytes: current position in dk_entries
    PyObject *di_result;      // 8 bytes: reusable tuple for items() (optimization!)
    Py_ssize_t len;           // 8 bytes: remaining items
} _PyDictIterObject;          // Total: 56 bytes
```

The `di_result` field is a **pre-allocated tuple** reused across iterations of `.items()`:
```python
for k, v in d.items():
    # Each iteration reuses the SAME tuple object (refcnt=1 check)
    # Avoids allocating a new tuple every iteration!
    pass
```

---

## 6.3 PyRangeIterObject

```c
typedef struct {
    PyObject_HEAD
    long index;     // Which item we're on (0, 1, 2, ...)
    long start;
    long stop;
    long step;
    long len;       // Total number of items
} _PyRangeIterObject;  // ~56 bytes total (fixed!)

// For range(0, 10**18): still only 56 bytes!
// Values computed on-the-fly: start + index * step
```

---

## 6.4 PySeqIterObject (Generic Sequence Iterator)

For objects with `__getitem__` but no `__iter__` (old protocol):
```c
typedef struct {
    PyObject_HEAD
    Py_ssize_t it_index;
    PyObject *it_seq;     // Any sequence-like object
} PySeqIterObject;

// __next__ calls: it_seq.__getitem__(it_index++)
// On IndexError: exhausted
```

---

## 6.5 Iterator Object Sizes

```
Iterator Type           Size (bytes)   State
───────────────────────────────────────────────
list_iterator           32             index + seq_ref
tuple_iterator          32             index + seq_ref
dict_keyiterator        56             pos + used + dict_ref
dict_itemiterator       56+tuple       same + reusable tuple
set_iterator            48             pos + used + table_ref
str_iterator            32             index + str_ref
range_iterator          56             index + start/stop/step/len
bytes_iterator          32             index + bytes_ref
file (self)             ~200+          OS file descriptor + buffers
generator               112+frame      full frame preservation!
```

**Key insight**: Most iterators are tiny (32-56 bytes). Generators are much larger because they preserve an entire execution frame.

---

## 6.6 Lifetime and Reference Ownership

```python
data = [1, 2, 3]
it = iter(data)
del data  # Is the list freed?
# NO! The iterator holds a reference (it_seq → list)
# The list stays alive until the iterator is freed or exhausted

next(it)  # 1 — still works!
next(it)  # 2
next(it)  # 3
next(it)  # StopIteration — iterator releases reference to list
# NOW the list can be freed (if no other refs)
```

---

## 6.7 Interview Questions — Part 6

**Q1**: How large is a list iterator in memory? **A**: ~32 bytes (PyObject_HEAD 16B + index 8B + seq pointer 8B). Tiny compared to copying the list.

**Q2**: What is the `di_result` optimization in dict iterators? **A**: For `.items()` iteration, a single tuple is pre-allocated and reused each iteration (if its refcnt is 1 — not held elsewhere). Avoids allocating a new tuple per key-value pair.

**Q3**: Does the iterator keep the source collection alive? **A**: Yes. The iterator holds a strong reference (Py_INCREF) to the collection. The collection isn't freed until the iterator releases it (on exhaustion or iterator deallocation).

**Q4**: Why are generator objects much larger than list iterators? **A**: Generators preserve an entire execution frame (instruction pointer, locals, stack). List iterators only need an index and a pointer to the list.
