# Part 11 — String Operations: C-Level Implementation

## 11.1 Concatenation: `PyUnicode_Concat`

```c
PyObject *PyUnicode_Concat(PyObject *left, PyObject *right)
{
    // Fast exits:
    if (PyUnicode_GET_LENGTH(left) == 0) { Py_INCREF(right); return right; }
    if (PyUnicode_GET_LENGTH(right) == 0) { Py_INCREF(left); return left; }
    
    Py_ssize_t left_len = PyUnicode_GET_LENGTH(left);
    Py_ssize_t right_len = PyUnicode_GET_LENGTH(right);
    Py_ssize_t new_len = left_len + right_len;
    
    // Determine result kind:
    Py_UCS4 maxchar = Py_MAX(PyUnicode_MAX_CHAR_VALUE(left),
                             PyUnicode_MAX_CHAR_VALUE(right));
    
    // Allocate result:
    PyObject *result = PyUnicode_New(new_len, maxchar);
    
    // Copy left then right (with potential kind widening):
    _PyUnicode_FastCopyCharacters(result, 0, left, 0, left_len);
    _PyUnicode_FastCopyCharacters(result, left_len, right, 0, right_len);
    
    return result;
}
```

**Complexity**: O(n + m) where n = len(left), m = len(right).
Always creates a new string (immutability).

---

## 11.2 `str.join()` Implementation

```c
static PyObject *
unicode_join(PyObject *separator, PyObject *seq)
{
    // Phase 1: Count total length and determine kind
    Py_ssize_t nseq = PySequence_Fast_GET_SIZE(seq);
    Py_ssize_t sz = 0;
    Py_UCS4 maxchar = 0;
    
    for (Py_ssize_t i = 0; i < nseq; i++) {
        PyObject *item = PySequence_Fast_GET_ITEM(seq, i);
        sz += PyUnicode_GET_LENGTH(item);
        Py_UCS4 item_max = PyUnicode_MAX_CHAR_VALUE(item);
        if (item_max > maxchar) maxchar = item_max;
    }
    // Add separators: (nseq - 1) * sep_length
    sz += (nseq - 1) * PyUnicode_GET_LENGTH(separator);
    Py_UCS4 sep_max = PyUnicode_MAX_CHAR_VALUE(separator);
    if (sep_max > maxchar) maxchar = sep_max;
    
    // Phase 2: Single allocation for result
    PyObject *result = PyUnicode_New(sz, maxchar);
    
    // Phase 3: Copy all items + separators
    Py_ssize_t pos = 0;
    for (Py_ssize_t i = 0; i < nseq; i++) {
        if (i > 0) {
            // Copy separator:
            _PyUnicode_FastCopyCharacters(result, pos, separator, 0, sep_len);
            pos += sep_len;
        }
        // Copy item:
        PyObject *item = PySequence_Fast_GET_ITEM(seq, i);
        _PyUnicode_FastCopyCharacters(result, pos, item, 0, item_len);
        pos += item_len;
    }
    
    return result;
}
```

**Complexity**: O(total_output_length). Two passes: one to count, one to copy.
Key advantage: SINGLE allocation regardless of number of items.

---

## 11.3 `str.split()` Implementation

```c
// Splitting by whitespace (default):
static PyObject *
unicode_split_whitespace(PyObject *self, Py_ssize_t maxsplit)
{
    PyObject *list = PyList_New(0);
    Py_ssize_t i = 0, j, len = PyUnicode_GET_LENGTH(self);
    int kind = PyUnicode_KIND(self);
    void *data = PyUnicode_DATA(self);
    
    while (i < len) {
        // Skip whitespace:
        while (i < len && Py_UNICODE_ISSPACE(PyUnicode_READ(kind, data, i)))
            i++;
        if (i >= len) break;
        
        // Find end of word:
        j = i;
        while (j < len && !Py_UNICODE_ISSPACE(PyUnicode_READ(kind, data, j)))
            j++;
        
        // Extract substring [i:j]:
        PyObject *sub = PyUnicode_Substring(self, i, j);
        PyList_Append(list, sub);
        Py_DECREF(sub);
        
        i = j;
        if (--maxsplit == 0) break;
    }
    return list;
}
```

**Complexity**: O(n) scan + O(n) total substring copies = O(n).
Each substring is a new string (immutability — can't share internal buffer).

---

## 11.4 `str.replace()` Implementation

```c
// Simplified: replace all occurrences of old with new
static PyObject *
replace(PyObject *self, PyObject *old, PyObject *new, Py_ssize_t maxcount)
{
    // Phase 1: Count occurrences of 'old' in 'self'
    Py_ssize_t count = count_occurrences(self, old, maxcount);
    if (count == 0) { Py_INCREF(self); return self; }  // Nothing to replace!
    
    // Phase 2: Calculate result length
    Py_ssize_t result_len = PyUnicode_GET_LENGTH(self)
                          + count * (PyUnicode_GET_LENGTH(new) - PyUnicode_GET_LENGTH(old));
    Py_UCS4 maxchar = calculate_maxchar(self, old, new);
    
    // Phase 3: Allocate result
    PyObject *result = PyUnicode_New(result_len, maxchar);
    
    // Phase 4: Build result (copy non-matching parts + new)
    Py_ssize_t pos = 0, start = 0;
    while (count > 0) {
        Py_ssize_t found = find_substring(self, old, start);
        // Copy text before match:
        copy_characters(result, pos, self, start, found - start);
        pos += found - start;
        // Copy replacement:
        copy_characters(result, pos, new, 0, PyUnicode_GET_LENGTH(new));
        pos += PyUnicode_GET_LENGTH(new);
        start = found + PyUnicode_GET_LENGTH(old);
        count--;
    }
    // Copy remaining tail:
    copy_characters(result, pos, self, start, len_self - start);
    
    return result;
}
```

**Complexity**: O(n) for counting + O(n) for building result = O(n).
**Key optimization**: If nothing matches, returns the SAME object (incref, no copy).

---

## 11.5 `str.find()` / `str.index()` — Substring Search

CPython uses a combination of algorithms:

```c
// For short patterns (len ≤ 5): simple brute-force
// For longer patterns: FAST search (simplified Boyer-Moore-Horspool variant)

static Py_ssize_t
FASTSEARCH(const void *s, Py_ssize_t n,
           const void *p, Py_ssize_t m,
           Py_ssize_t maxcount, int mode)
{
    // Build skip table (last occurrence of each char):
    unsigned long mask = 0;
    Py_ssize_t skip = m - 1;
    Py_ssize_t mlast = m - 1;
    
    // Bloom filter for quick rejection:
    for (Py_ssize_t i = 0; i < mlast; i++) {
        STRINGLIB_BLOOM_ADD(mask, STRINGLIB_CHAR(p, i));
        if (STRINGLIB_CHAR(p, i) == STRINGLIB_CHAR(p, mlast))
            skip = mlast - i - 1;
    }
    STRINGLIB_BLOOM_ADD(mask, STRINGLIB_CHAR(p, mlast));
    
    // Search:
    for (Py_ssize_t i = 0; i <= n - m; ) {
        // Check last char first (Boyer-Moore heuristic):
        if (STRINGLIB_CHAR(s, i + mlast) == STRINGLIB_CHAR(p, mlast)) {
            // Last char matches → compare rest
            if (memcmp_like(s+i, p, mlast) == 0)
                return i;  // FOUND!
            // Mismatch: skip based on bloom filter
            if (!STRINGLIB_BLOOM(mask, STRINGLIB_CHAR(s, i + m)))
                i += m;  // Character at i+m not in pattern → big skip!
            else
                i += skip;
        } else {
            // Last char doesn't match: skip based on bloom
            if (!STRINGLIB_BLOOM(mask, STRINGLIB_CHAR(s, i + m)))
                i += m;
            else
                i++;
        }
    }
    return -1;  // NOT FOUND
}
```

**Average case**: O(n/m) — the bloom filter skips most positions.
**Worst case**: O(n*m) — pathological patterns (rare in practice).

---

## 11.6 `str.startswith()` / `str.endswith()`

```c
static int
tailmatch(PyObject *self, PyObject *substring,
          Py_ssize_t start, Py_ssize_t end, int direction)
{
    // direction: -1 = startswith, +1 = endswith
    
    Py_ssize_t slen = PyUnicode_GET_LENGTH(substring);
    if (direction < 0) {
        // startswith: compare self[start:start+slen] with substring
        offset = start;
    } else {
        // endswith: compare self[end-slen:end] with substring
        offset = end - slen;
    }
    
    // Direct comparison of slen characters:
    return PyUnicode_Compare_at(self, offset, substring, 0, slen) == 0;
}
```

**Complexity**: O(k) where k = len(prefix/suffix). Does NOT scan entire string.

---

## 11.7 `str.strip()` / `str.lstrip()` / `str.rstrip()`

```c
static PyObject *
do_strip(PyObject *self, int striptype, PyObject *chars)
{
    Py_ssize_t i, j, len = PyUnicode_GET_LENGTH(self);
    int kind = PyUnicode_KIND(self);
    void *data = PyUnicode_DATA(self);
    
    i = 0;
    if (striptype != RIGHTSTRIP) {
        // Scan from left: find first non-strip character
        while (i < len) {
            Py_UCS4 ch = PyUnicode_READ(kind, data, i);
            if (!char_in_strip_set(ch, chars)) break;
            i++;
        }
    }
    
    j = len;
    if (striptype != LEFTSTRIP) {
        // Scan from right: find last non-strip character
        while (j > i) {
            Py_UCS4 ch = PyUnicode_READ(kind, data, j - 1);
            if (!char_in_strip_set(ch, chars)) break;
            j--;
        }
    }
    
    // Return substring self[i:j]:
    return PyUnicode_Substring(self, i, j);
}
```

**Complexity**: O(n) worst case (entire string is whitespace). O(k) typical (k = stripped chars).

---

## 11.8 `str.encode()` — Encoding to Bytes

```c
PyObject *
PyUnicode_AsEncodedString(PyObject *unicode,
                          const char *encoding,
                          const char *errors)
{
    // Look up codec in the codec registry:
    PyObject *codec = _PyCodec_Lookup(encoding);
    
    // For common encodings, use fast C paths:
    if (strcmp(encoding, "utf-8") == 0) {
        return _PyUnicode_AsUTF8String(unicode, errors);
    }
    if (strcmp(encoding, "ascii") == 0) {
        return _PyUnicode_AsASCIIString(unicode, errors);
    }
    if (strcmp(encoding, "latin-1") == 0) {
        return _PyUnicode_AsLatin1String(unicode, errors);
    }
    
    // General path: call codec encoder
    return codec_encode(codec, unicode, errors);
}
```

For UTF-8 encoding of an ASCII string: **O(1)!** (the ASCII data IS valid UTF-8 — just wrap in a bytes object pointing to the same data, or memcpy).

---

## 11.9 Complexity Summary

| Operation | Average | Worst | Notes |
|-----------|---------|-------|-------|
| `s[i]` | O(1) | O(1) | Pointer arithmetic |
| `len(s)` | O(1) | O(1) | Read length field |
| `s + t` | O(n+m) | O(n+m) | New string, copy both |
| `"".join(list)` | O(total) | O(total) | Single alloc + copy |
| `s.find(sub)` | O(n/m) | O(nm) | FAST search bloom filter |
| `s.replace(old,new)` | O(n) | O(n) | Count + rebuild |
| `s.split()` | O(n) | O(n) | Scan + extract substrings |
| `s.strip()` | O(k) | O(n) | Scan from edges |
| `s.startswith(p)` | O(k) | O(k) | k = len(p), direct compare |
| `s.upper()/lower()` | O(n) | O(n) | New string, transform each char |
| `s.encode('utf-8')` | O(n) | O(n) | (O(1) if ASCII — it IS UTF-8!) |
| `hash(s)` | O(1) | O(n) | O(n) first time, O(1) cached |
| `s == t` | O(1) best | O(n) | Identity→len→hash→chars |
| `s in t` | O(n/m) | O(nm) | Substring search |

---

## 11.10 Interview Questions — Part 11

**Q1**: Why is `"".join(words)` faster than `result += word` in a loop?
**A**: join() counts total length first (O(n pass)), allocates ONE string, copies everything in ONE pass. Loop concatenation creates n intermediate strings, each copying all previous content — O(n²) total allocations and copies.

**Q2**: What algorithm does CPython use for `str.find()`?
**A**: A FAST search variant combining Boyer-Moore-Horspool skip heuristic with a Bloom filter for quick character rejection. Average O(n/m), but O(nm) worst case.

**Q3**: What's the complexity of `str.encode('utf-8')` for an ASCII string?
**A**: Effectively O(1) — the ASCII data IS valid UTF-8. CPython may just create a bytes object wrapping the same data (or a quick memcpy). No character-by-character conversion needed.

**Q4**: Why does `str.replace()` return the same object if nothing matches?
**A**: Because strings are immutable, returning the original (with incref) is safe. Avoids allocating a new identical copy — saves time and memory.

**Q5**: How does `str.split()` handle the kind system?
**A**: It reads characters using PyUnicode_READ(kind, data, i) in a loop. Each extracted substring gets its own optimal kind (may be narrower than the source if the substring has lower max char).
