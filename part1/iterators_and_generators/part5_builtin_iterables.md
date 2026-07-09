# Part 5 — Built-in Iterables

## 5.1 How Each Built-in Type Creates Its Iterator

| Type | `iter(obj)` returns | Iterator state | Exhaustible? |
|------|-------------------|----------------|-------------|
| list | `list_iterator` | index into ob_item | Yes |
| tuple | `tuple_iterator` | index into ob_item | Yes |
| dict | `dict_keyiterator` | position in entries | Yes |
| set | `set_iterator` | position in table | Yes |
| str | `str_iterator` | index (code point) | Yes |
| bytes | `bytes_iterator` | index | Yes |
| range | `range_iterator` | current value + step | Yes |
| file | self (file IS iterator) | file position (OS) | Yes |
| deque | `_deque_iterator` | index + state counter | Yes |

---

## 5.2 List Iteration

```c
// Objects/listobject.c
typedef struct {
    PyObject_HEAD
    Py_ssize_t it_index;     // Current position (starts at 0)
    PyListObject *it_seq;    // Reference to the list
} _PyListIterObject;

// __next__ implementation:
static PyObject *listiter_next(_PyListIterObject *it) {
    PyListObject *seq = it->it_seq;
    if (seq == NULL) return NULL;  // Already exhausted
    
    if (it->it_index < Py_SIZE(seq)) {
        PyObject *item = PyList_GET_ITEM(seq, it->it_index);
        ++it->it_index;
        Py_INCREF(item);
        return item;
    }
    // Exhausted:
    it->it_seq = NULL;
    Py_DECREF(seq);
    return NULL;
}
```

Key: iterator holds a reference to the list (keeps it alive). On exhaustion, releases the reference.

---

## 5.3 Dict Iteration

```python
d = {"a": 1, "b": 2, "c": 3}
for key in d:          # Iterates over KEYS (default)
    print(key)

for val in d.values(): # Values iterator
for k, v in d.items(): # Items iterator (yields tuples)
```

```c
// Objects/dictobject.c
typedef struct {
    PyObject_HEAD
    PyDictObject *di_dict;     // The dict
    Py_ssize_t di_used;        // dict.ma_used at creation (mutation detection!)
    Py_ssize_t di_pos;         // Current position in entries array
    Py_ssize_t len;            // Remaining items
} _PyDictIterObject;
```

**Mutation detection**: If `di_used != dict.ma_used` (dict was modified), raises RuntimeError:
```python
d = {"a": 1, "b": 2}
for k in d:
    d["c"] = 3  # RuntimeError: dictionary changed size during iteration
```

---

## 5.4 Range Iteration

```python
r = range(0, 1000000, 2)  # O(1) memory! No list of 500K items.
for i in r:
    process(i)
```

```c
typedef struct {
    PyObject_HEAD
    long index;    // Current value to yield
    long start;
    long stop;
    long step;
    long len;      // Total number of items (precomputed)
} _PyRangeIterObject;

// __next__: just computes next value arithmetically
static PyObject *rangeiter_next(_PyRangeIterObject *r) {
    if (r->index < r->len) {
        long val = r->start + r->index * r->step;
        r->index++;
        return PyLong_FromLong(val);  // Create int object on-the-fly
    }
    return NULL;  // Exhausted
}
```

**Key insight**: Range iterator creates integer objects on-demand. No array stored. O(1) memory for any range size.

---

## 5.5 String Iteration

```c
typedef struct {
    PyObject_HEAD
    Py_ssize_t it_index;
    PyObject *it_seq;    // The string
} _PyUnicodeIterObject;

// __next__: returns single-character string at current index
static PyObject *unicodeiter_next(_PyUnicodeIterObject *it) {
    if (it->it_index < PyUnicode_GET_LENGTH(it->it_seq)) {
        Py_UCS4 ch = PyUnicode_READ(kind, data, it->it_index);
        it->it_index++;
        return unicode_char(ch);  // Single-char string (possibly cached)
    }
    return NULL;
}
```

Each iteration yields a **new string object** of length 1 (or cached single-char if ASCII).

---

## 5.6 File Iteration

```python
# Files ARE their own iterators:
f = open("data.txt")
iter(f) is f  # True!

for line in f:
    process(line)  # Each line is a string (including \n)
```

Files use the readline protocol for iteration. Each `__next__` call reads one line from the OS buffer. This is memory-efficient for huge files (one line in memory at a time).

---

## 5.7 Interview Questions — Part 5

**Q1**: How much memory does iterating `range(10**9)` use? **A**: O(1) — the range_iterator stores only (current, stop, step). No billion-element list. Values are computed arithmetically.

**Q2**: Why does modifying a dict during iteration raise RuntimeError? **A**: The dict iterator stores `di_used` (entry count at creation). Each __next__ checks if `dict.ma_used` changed. If so: RuntimeError prevents undefined behavior from structural changes.

**Q3**: Is a file object an iterable or an iterator? **A**: Both! `iter(file) is file` — files are their own iterators. This means they're single-use (can't iterate twice without seeking).

**Q4**: What object does `for char in "hello"` iterate over? **A**: A `str_iterator` that yields single-character strings. Each character is a new str object (or cached if ASCII).
