# Part 4 — PEP 393: The Flexible String Representation Design

## 4.1 The Problem PEP 393 Solved

Before Python 3.3, CPython had two incompatible string builds:

### Narrow Build (--enable-unicode=ucs2)
```
Internal storage: UCS-2 (2 bytes per character)
Range: U+0000 - U+FFFF only!
Problem: Characters above U+FFFF stored as surrogate pairs
  '😀' = U+1F600 → stored as TWO Py_UNICODE values (surrogate pair)
  len('😀') == 2  ← WRONG!
  '😀'[0] → '\ud83d' (high surrogate) ← BROKEN!

Used by: macOS, many Linux builds
```

### Wide Build (--enable-unicode=ucs4)
```
Internal storage: UCS-4 (4 bytes per character)
Range: U+0000 - U+10FFFF (full Unicode) ✓
Problem: MASSIVE memory waste for ASCII-heavy programs
  "hello" → 5 × 4 = 20 bytes (vs 5 bytes needed)
  A 1MB ASCII file → 4MB in memory

Used by: Some Linux builds
```

### The Incompatibility Disaster
```
C extension compiled for narrow build: expects sizeof(Py_UNICODE) == 2
C extension compiled for wide build:   expects sizeof(Py_UNICODE) == 4

Mix them → CRASH! Segfault! Data corruption!
Binary wheels had to ship both versions.
You couldn't pip install a narrow-build wheel on a wide-build Python.
```

---

## 4.2 PEP 393's Solution: Per-String Adaptive Width

Raymond Hettinger and Martin von Löwis proposed (2010, accepted 2011, implemented 3.3):

> Store each string using the NARROWEST fixed-width encoding that can represent ALL its characters.

```
Key Insight: Look at the MAXIMUM code point in the string.
  max < 128   → 1 byte per char (ASCII)
  max < 256   → 1 byte per char (Latin-1)
  max < 65536 → 2 bytes per char (UCS-2)
  max ≤ 10FFFF → 4 bytes per char (UCS-4)

Benefits:
  1. "hello" uses 1 byte/char (optimal, like narrow build)
  2. "日本" uses 2 bytes/char (like narrow build)
  3. "😀" uses 4 bytes/char (correct, like wide build)
  4. NO surrogate pairs (every char is ONE code point)
  5. O(1) indexing (fixed width per string)
  6. ONE binary (no narrow/wide distinction)
```

---

## 4.3 The Design Decision: Why Not Variable-Width Per Character?

Alternative: store each character in its minimum bytes (like UTF-8 internally).

Rejected because:
```
Indexing cost:
  Fixed-width: s[i] = *(data + i * width)  → O(1)
  Variable-width: s[i] = scan from start    → O(n)

Python HEAVILY uses indexing:
  - s[i] in for loops
  - Slicing: s[3:7]
  - Pattern matching regex internals
  - String methods (find, replace, split)

O(n) indexing would make ALL string operations O(n²) or worse.
The O(1) guarantee is non-negotiable.
```

---

## 4.4 The "Widening" Cost

One high code point forces the entire string to widen:

```python
import sys

s1 = "a" * 1000                    # 1BYTE: 49 + 1001 ≈ 1050 bytes
s2 = "a" * 999 + "é"              # 1BYTE: still Latin-1! ≈ 1073 bytes
s3 = "a" * 999 + "日"             # 2BYTE: 73 + 2×1000 + 2 ≈ 2075 bytes
s4 = "a" * 999 + "😀"            # 4BYTE: 73 + 4×1000 + 4 ≈ 4077 bytes

# The single emoji costs ~3000 extra bytes!
# 999 'a' characters now stored as 4 bytes each instead of 1.
```

### Why This Trade-off Is Acceptable:

1. **Strings with emoji/CJK are usually short** (messages, names, not megabyte files)
2. **ASCII strings (the vast majority) are maximally efficient**
3. **The alternative (variable-width) breaks O(1) indexing**
4. **Memory is cheap; incorrect semantics are expensive**

---

## 4.5 ASCII vs Latin-1: A Subtle Distinction

Both use 1 byte per character (1BYTE_KIND), but differ structurally:

```
ASCII (state.ascii = 1):
  Struct: PyASCIIObject (48 bytes, smaller)
  No utf8/utf8_length fields (ASCII IS UTF-8!)
  Data pointer: directly after struct (offset 48)

Latin-1 (state.ascii = 0, kind = 1):
  Struct: PyCompactUnicodeObject (64 bytes, larger)
  Has utf8/utf8_length fields (needs UTF-8 cache for non-ASCII bytes)
  Data pointer: directly after larger struct (offset 64)

Memory difference for same-length string:
  ASCII "hello": 48 + 6 = 54 bytes
  Latin-1 "café": 64 + 5 = 69 bytes (15 bytes more struct overhead!)

Why the distinction:
  For ASCII strings, the inline data IS the UTF-8 encoding.
  C API calls like PyUnicode_AsUTF8() can return the data pointer directly.
  No separate UTF-8 buffer allocation needed → saves memory AND time.
```

---

## 4.6 Creation Algorithm (Pseudocode)

```c
PyObject* create_string(const char* input_chars, Py_ssize_t length) {
    // Step 1: Scan for maximum code point
    Py_UCS4 maxchar = 0;
    for (int i = 0; i < length; i++) {
        if (input_chars[i] > maxchar)
            maxchar = input_chars[i];
    }
    
    // Step 2: Determine kind
    int kind, char_size;
    int is_ascii = 0;
    if (maxchar < 128) {
        kind = PyUnicode_1BYTE_KIND; char_size = 1; is_ascii = 1;
    } else if (maxchar < 256) {
        kind = PyUnicode_1BYTE_KIND; char_size = 1;
    } else if (maxchar < 65536) {
        kind = PyUnicode_2BYTE_KIND; char_size = 2;
    } else {
        kind = PyUnicode_4BYTE_KIND; char_size = 4;
    }
    
    // Step 3: Calculate allocation size
    Py_ssize_t struct_size = is_ascii ? sizeof(PyASCIIObject) 
                                      : sizeof(PyCompactUnicodeObject);
    Py_ssize_t data_size = (length + 1) * char_size;  // +1 for null
    
    // Step 4: Allocate (single allocation for struct + data!)
    PyObject *str = PyObject_Malloc(struct_size + data_size);
    
    // Step 5: Initialize header
    str->ob_refcnt = 1;
    str->ob_type = &PyUnicode_Type;
    ((PyASCIIObject*)str)->length = length;
    ((PyASCIIObject*)str)->hash = -1;  // Not yet computed
    ((PyASCIIObject*)str)->state.kind = kind;
    ((PyASCIIObject*)str)->state.compact = 1;
    ((PyASCIIObject*)str)->state.ascii = is_ascii;
    ((PyASCIIObject*)str)->state.interned = SSTATE_NOT_INTERNED;
    
    // Step 6: Copy character data (potentially widening)
    void *data = (char*)str + struct_size;
    for (int i = 0; i < length; i++) {
        // Write each char at the appropriate width
        if (kind == 1) ((Py_UCS1*)data)[i] = input_chars[i];
        else if (kind == 2) ((Py_UCS2*)data)[i] = input_chars[i];
        else ((Py_UCS4*)data)[i] = input_chars[i];
    }
    // Write null terminator
    memset((char*)data + length * char_size, 0, char_size);
    
    // Step 7: Try to intern (if identifier-like)
    maybe_intern(str);
    
    return str;
}
```

---

## 4.7 Impact on CPython Codebase

PEP 393 required rewriting most of `Objects/unicodeobject.c`:
- Every string operation must handle 3 kinds (1B, 2B, 4B)
- Concatenation may need to "promote" one operand's kind
- Comparison between different kinds requires careful handling
- The code uses macros (`PyUnicode_READ`, `PyUnicode_WRITE`) to abstract kind

```c
// The PyUnicode_READ macro (simplified):
#define PyUnicode_READ(kind, data, index) \
    ((kind) == PyUnicode_1BYTE_KIND ? ((Py_UCS1*)(data))[(index)] : \
     (kind) == PyUnicode_2BYTE_KIND ? ((Py_UCS2*)(data))[(index)] : \
     ((Py_UCS4*)(data))[(index)])

// Used everywhere: comparisons, search, slicing, etc.
// The compiler may optimize the switch away for known kinds.
```

---

## 4.8 Interview Questions — Part 4

**Q1**: What specific problem did PEP 393 solve?
**A**: Eliminated the narrow/wide build incompatibility. Before 3.3, CPython had to choose at compile time between UCS-2 (broken for code points > U+FFFF) or UCS-4 (wasteful for ASCII). PEP 393 gives per-string adaptive width.

**Q2**: Why does adding one emoji to a 10,000-char ASCII string quadruple memory?
**A**: PEP 393 uses a single fixed width for all characters in a string. The emoji (> U+FFFF) forces 4BYTE_KIND. All 10,001 characters are stored as 4 bytes each. The alternative (variable-width) would break O(1) indexing.

**Q3**: What is the struct difference between an ASCII and Latin-1 string?
**A**: ASCII uses PyASCIIObject (48 bytes, no utf8 cache — ASCII IS UTF-8). Latin-1 uses PyCompactUnicodeObject (64 bytes, has utf8/utf8_length fields for separate UTF-8 cache). Both use 1 byte per character for data.

**Q4**: Could CPython use a hybrid approach (UTF-8 + index table)?
**A**: Theoretically yes (like Swift's String). But it adds complexity, memory for the index table, and cache pressure. CPython's approach is simpler, faster for the common case, and the "widening" cost is rarely triggered in practice.

**Q5**: How does PEP 393 handle the kind determination for string concatenation?
**A**: The result kind = max(kind of left, kind of right). If concatenating ASCII + UCS-2, the result is UCS-2. All characters from the narrower string are "widened" during copy.
