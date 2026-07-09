# Part 7 — The Kind System

## 7.1 Kind Determination Algorithm

When CPython creates a string, it scans ALL characters to find the maximum code point:

```c
// Objects/unicodeobject.c — simplified
static int
find_maxchar_surrogates(const wchar_t *begin, const wchar_t *end,
                        Py_UCS4 *maxchar, Py_ssize_t *num_surrogates)
{
    const wchar_t *iter;
    Py_UCS4 ch, max = 0;
    for (iter = begin; iter < end; iter++) {
        ch = *iter;
        if (ch > max) max = ch;
    }
    *maxchar = max;
}

// Then determine kind:
// max < 128:    kind = 1, ascii = 1 (PyASCIIObject)
// max < 256:    kind = 1, ascii = 0 (PyCompactUnicodeObject)
// max < 65536:  kind = 2
// else:         kind = 4
```

This scan is O(n) — the cost of creating a string includes examining every character. This is unavoidable: you can't know the optimal representation without seeing all the data.

---

## 7.2 Kind Promotion During Operations

When two strings of different kinds are combined, the result takes the wider kind:

```python
# Concatenation promotes:
"hello"  + "日本"    # ASCII(kind=1) + UCS-2(kind=2) → result is kind=2
"hello"  + "😀"    # ASCII(kind=1) + UCS-4(kind=4) → result is kind=4
"café"   + "日本"    # Latin-1(kind=1) + UCS-2(kind=2) → result is kind=2

# The formula: result_kind = max(left.kind, right.kind)
# But more precisely: based on max code point of ENTIRE result
```

### How Promotion Works at C Level:

```c
// Concatenation (simplified from PyUnicode_Concat):
Py_UCS4 maxchar_left = PyUnicode_MAX_CHAR_VALUE(left);
Py_UCS4 maxchar_right = PyUnicode_MAX_CHAR_VALUE(right);
Py_UCS4 maxchar = Py_MAX(maxchar_left, maxchar_right);

// Allocate result with kind determined by maxchar:
PyObject *result = PyUnicode_New(len_left + len_right, maxchar);

// Copy characters — may need widening!
_PyUnicode_FastCopyCharacters(result, 0, left, 0, len_left);
_PyUnicode_FastCopyCharacters(result, len_left, right, 0, len_right);
```

### The `_PyUnicode_FastCopyCharacters` Function:

```c
// Handles kind conversion during copy:
void _PyUnicode_FastCopyCharacters(
    PyObject *to, Py_ssize_t to_start,
    PyObject *from, Py_ssize_t from_start,
    Py_ssize_t how_many)
{
    int from_kind = PyUnicode_KIND(from);
    int to_kind = PyUnicode_KIND(to);
    
    if (from_kind == to_kind) {
        // Same kind: memcpy (fastest path)
        memcpy(to_data + to_start * to_kind,
               from_data + from_start * from_kind,
               how_many * to_kind);
    }
    else if (from_kind < to_kind) {
        // Widening: expand each character
        // e.g., 1-byte 'h' (0x68) → 2-byte (0x0068) or 4-byte (0x00000068)
        _PyUnicode_CONVERT_BYTES(from_type, to_type, from_data, to_data, how_many);
    }
    else {
        // Narrowing: ONLY valid if all chars fit in narrower kind
        // This happens during slicing when a slice has lower maxchar
        _PyUnicode_CONVERT_BYTES(from_type, to_type, from_data, to_data, how_many);
    }
}
```

---

## 7.3 Kind Demotion During Slicing

A slice can be NARROWER than the source:

```python
s = "Hello😀World"  # kind=4 (because of 😀)
t = s[0:5]          # "Hello" → max char 'o' = U+006F < 128 → kind=1 (ASCII!)
u = s[6:11]         # "World" → same, kind=1

# The slice operation scans the slice content to find its own optimal kind!
# This means slicing a UCS-4 string may produce an ASCII string.
```

Implementation:
```c
// When creating a substring, CPython finds the max char in the slice:
Py_UCS4 maxchar = 0;
for (i = start; i < end; i++) {
    Py_UCS4 ch = PyUnicode_READ(kind, data, i);
    if (ch > maxchar) maxchar = ch;
}
// Then allocates result with the optimal kind for this maxchar
// Result may be narrower than source!
```

This is expensive (O(slice_length) scan), but ensures slices are memory-optimal.

---

## 7.4 The PyUnicode_MAX_CHAR_VALUE Macro

```c
// Returns the maximum possible character value for a string's kind:
#define PyUnicode_MAX_CHAR_VALUE(op)                                    \
    (assert(PyUnicode_IS_READY(op)),                                    \
     (PyUnicode_IS_ASCII(op) ?                                          \
      (0x7f) :                                                          \
      (PyUnicode_KIND(op) == PyUnicode_1BYTE_KIND ?                    \
       (0xff) :                                                         \
       (PyUnicode_KIND(op) == PyUnicode_2BYTE_KIND ?                   \
        (0xffff) :                                                      \
        (0x10ffff)))))
```

This doesn't tell you the actual max char in the string — it tells you the maximum POSSIBLE for its kind. The actual max may be lower (e.g., a UCS-2 string might only contain chars up to U+3000).

---

## 7.5 Kind Affects All String Operations

Every operation that reads characters must account for kind:

```c
// Reading character at index i:
Py_UCS4 ch = PyUnicode_READ(PyUnicode_KIND(str), PyUnicode_DATA(str), i);

// This expands to:
// kind==1: ((uint8_t*)data)[i]
// kind==2: ((uint16_t*)data)[i]  
// kind==4: ((uint32_t*)data)[i]

// Finding a character:
for (i = 0; i < length; i++) {
    Py_UCS4 ch = PyUnicode_READ(kind, data, i);
    if (ch == target) return i;
}

// Comparison between strings of different kinds:
// Must read each char with appropriate kind accessor
```

### Compiler Optimization:

In many hot paths, the kind is checked ONCE and then a specialized loop runs:
```c
// Pattern used in CPython:
switch (kind) {
    case PyUnicode_1BYTE_KIND: {
        Py_UCS1 *data = PyUnicode_1BYTE_DATA(str);
        for (i = 0; i < len; i++) { /* use data[i] directly */ }
        break;
    }
    case PyUnicode_2BYTE_KIND: {
        Py_UCS2 *data = PyUnicode_2BYTE_DATA(str);
        for (i = 0; i < len; i++) { /* use data[i] directly */ }
        break;
    }
    case PyUnicode_4BYTE_KIND: {
        Py_UCS4 *data = PyUnicode_4BYTE_DATA(str);
        for (i = 0; i < len; i++) { /* use data[i] directly */ }
        break;
    }
}
```

This eliminates the per-character branch inside the loop — critical for performance.

---

## 7.6 Same-Kind Comparison Optimization

When both strings have the same kind, comparison becomes `memcmp`:

```c
static int
unicode_compare(PyObject *str1, PyObject *str2)
{
    int kind1 = PyUnicode_KIND(str1);
    int kind2 = PyUnicode_KIND(str2);
    
    if (kind1 == kind2) {
        // FAST PATH: direct memory comparison
        Py_ssize_t len = Py_MIN(len1, len2);
        int cmp = memcmp(data1, data2, len * kind1);
        if (cmp) return (cmp < 0) ? -1 : 1;
        // Equal prefix — shorter string is less
        if (len1 < len2) return -1;
        if (len1 > len2) return 1;
        return 0;
    }
    
    // SLOW PATH: different kinds, char-by-char comparison
    // Read each char with its appropriate kind, compare as UCS4
    ...
}
```

`memcmp` uses SIMD instructions on modern CPUs — comparing 16/32/64 bytes at a time. This makes same-kind comparison blazingly fast.

---

## 7.7 Interview Questions — Part 7

**Q1**: What triggers kind promotion during concatenation?
**A**: The result kind is determined by the maximum code point across BOTH strings. If one is ASCII and the other has an emoji, the result is 4BYTE_KIND for all characters.

**Q2**: Can slicing produce a narrower kind than the source?
**A**: Yes! CPython scans the slice to find its max code point and allocates the optimal kind. Slicing "Hello😀"[0:5] gives "Hello" as ASCII (1BYTE_KIND), not UCS-4.

**Q3**: Why does CPython use memcmp for same-kind strings?
**A**: When both strings use the same bytes-per-character, their raw byte representations can be compared directly with memcmp. The CPU can use SIMD to compare 16+ bytes at once — extremely fast.

**Q4**: What is the performance cost of the per-character kind check?
**A**: In hot paths, CPython uses switch-on-kind with separate loops for each kind. The branch is taken ONCE (outside the loop), not per character. Inside each loop, the data is accessed with the correct typed pointer — no per-character branching.

**Q5**: How does _PyUnicode_FastCopyCharacters handle widening?
**A**: If source kind < dest kind (e.g., copying 1BYTE into a 4BYTE result), each character is read at the source width and written at the destination width. For narrowing (only valid when all chars fit), the reverse happens.
