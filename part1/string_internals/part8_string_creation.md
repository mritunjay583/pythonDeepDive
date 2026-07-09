# Part 8 — String Creation Internals

## 8.1 PyUnicode_New: The Core Allocation Function

```c
// Objects/unicodeobject.c (simplified)
PyObject *
PyUnicode_New(Py_ssize_t size, Py_UCS4 maxchar)
{
    PyObject *obj;
    PyCompactUnicodeObject *unicode;
    Py_ssize_t char_size;
    Py_ssize_t struct_size;
    
    // Step 1: Determine kind and character size from maxchar
    int kind;
    int is_ascii = 0;
    if (maxchar < 128) {
        kind = PyUnicode_1BYTE_KIND;
        char_size = 1;
        is_ascii = 1;
        struct_size = sizeof(PyASCIIObject);
    }
    else if (maxchar < 256) {
        kind = PyUnicode_1BYTE_KIND;
        char_size = 1;
        struct_size = sizeof(PyCompactUnicodeObject);
    }
    else if (maxchar < 65536) {
        kind = PyUnicode_2BYTE_KIND;
        char_size = 2;
        struct_size = sizeof(PyCompactUnicodeObject);
    }
    else {
        kind = PyUnicode_4BYTE_KIND;
        char_size = 4;
        struct_size = sizeof(PyCompactUnicodeObject);
    }
    
    // Step 2: Calculate total allocation (struct + inline data + null terminator)
    Py_ssize_t data_size = (size + 1) * char_size;  // +1 for null
    
    // Step 3: Single allocation via pymalloc or system malloc
    obj = (PyObject *)PyObject_Malloc(struct_size + data_size);
    if (obj == NULL)
        return PyErr_NoMemory();
    
    // Step 4: Initialize PyObject header
    _Py_NewReference(obj);           // ob_refcnt = 1
    PyObject_INIT(obj, &PyUnicode_Type);  // ob_type = &PyUnicode_Type
    
    // Step 5: Initialize string-specific fields
    unicode = (PyCompactUnicodeObject *)obj;
    _PyASCIIObject_CAST(obj)->length = size;
    _PyASCIIObject_CAST(obj)->hash = -1;     // Not yet computed
    _PyASCIIObject_CAST(obj)->state.interned = SSTATE_NOT_INTERNED;
    _PyASCIIObject_CAST(obj)->state.kind = kind;
    _PyASCIIObject_CAST(obj)->state.compact = 1;
    _PyASCIIObject_CAST(obj)->state.ready = 1;
    _PyASCIIObject_CAST(obj)->state.ascii = is_ascii;
    _PyASCIIObject_CAST(obj)->wstr = NULL;
    
    if (!is_ascii) {
        unicode->utf8 = NULL;
        unicode->utf8_length = 0;
    }
    
    // Step 6: Write null terminator at end
    // (character data itself will be filled by the caller)
    void *data = is_ascii ? (void*)(((PyASCIIObject*)obj) + 1)
                          : (void*)(unicode + 1);
    // Set null terminator:
    switch (kind) {
        case PyUnicode_1BYTE_KIND: ((Py_UCS1*)data)[size] = 0; break;
        case PyUnicode_2BYTE_KIND: ((Py_UCS2*)data)[size] = 0; break;
        case PyUnicode_4BYTE_KIND: ((Py_UCS4*)data)[size] = 0; break;
    }
    
    return obj;
}
```

**Key insight**: The function allocates but doesn't fill the character data. The caller is responsible for writing characters into the buffer. This allows construction in a single pass.

---

## 8.2 String Creation From Python Source Code

When the Python compiler encounters a string literal `"hello"`:

```
Source code:  x = "hello"

Compilation phase:
  1. Lexer tokenizes "hello" as STRING token
  2. Parser creates AST node (Constant with value str)
  3. Compiler creates a code object constant:
     - PyUnicode_DecodeUTF8("hello", 5, NULL)
     - String is interned if identifier-like
     - Stored in co_consts tuple of the code object
  
Runtime execution:
  LOAD_CONST instruction pushes the pre-built string object onto the stack.
  The string is NOT recreated at runtime — it's a reference to the compile-time constant.
```

### Constant Folding at Compile Time:

```python
# The compiler pre-computes constant expressions:
s = "hel" + "lo"     # Compiled as single constant "hello" (not runtime concat!)
s = "x" * 4          # Compiled as "xxxx" (not runtime repetition!)
s = f"{'hi'}"        # May be folded to "hi" 

# BUT: only if result ≤ 4096 characters (peephole optimizer limit)
s = "x" * 10000      # NOT folded — too long, would bloat .pyc file
```

---

## 8.3 String Creation From C API

### From UTF-8 bytes (most common C API path):
```c
PyObject *s = PyUnicode_DecodeUTF8("café", 5, "strict");
// 1. Decode UTF-8 bytes to determine code points
// 2. Find max code point (é = 0xE9 → kind=1)
// 3. Call PyUnicode_New(4, 0xE9) to allocate
// 4. Fill in the 4 characters
// 5. Return the new string
```

### From Latin-1 bytes:
```c
PyObject *s = PyUnicode_DecodeLatin1("caf\xe9", 4, NULL);
// Fast path! Latin-1 byte value == code point value
// Just memcpy the bytes directly into a 1BYTE_KIND string
```

### From ASCII (fastest path):
```c
PyObject *s = PyUnicode_DecodeASCII("hello", 5, "strict");
// Even faster! Validates all bytes < 128, then memcpy
// Creates PyASCIIObject (smallest struct)
```

### From a single character:
```c
PyObject *s = PyUnicode_FromOrdinal(0x1F600);  // '😀'
// 1. Determine kind from the single code point
// 2. Check single-char cache for ASCII (U+0000 to U+007F)
// 3. Allocate and fill 1-character string
```

---

## 8.4 The Single-Character Cache

CPython pre-allocates ALL 128 ASCII single-character strings at startup:

```c
// At interpreter initialization:
static PyObject *unicode_latin1[256];  // Cache array

// Characters 0-127 are pre-created and IMMORTAL:
for (int i = 0; i < 128; i++) {
    unicode_latin1[i] = create_1char_ascii(i);
    // These are immortal — never freed
}

// Characters 128-255 are cached on first use (not pre-created):
// unicode_latin1[128..255] starts as NULL, filled lazily

// When chr(65) or s[i] (for ASCII) is called:
PyObject* get_latin1_char(unsigned char ch) {
    PyObject *unicode = unicode_latin1[ch];
    if (unicode) {
        Py_INCREF(unicode);  // (or no-op if immortal)
        return unicode;
    }
    // Create and cache (for 128-255 range):
    unicode = PyUnicode_New(1, ch);
    // ... fill character ...
    unicode_latin1[ch] = unicode;
    return unicode;
}
```

This means:
```python
"a" is "a"         # True (same cached object)
chr(97) is "a"     # True (same cached object)
"hello"[0] is "a"  # True (indexing returns cached single-char)
```

---

## 8.5 String Creation from format() and f-strings

f-strings compile to `FORMAT_VALUE` + `BUILD_STRING` bytecodes:

```python
name = "World"
s = f"Hello, {name}!"
```

Bytecode:
```
LOAD_CONST     "Hello, "
LOAD_FAST      name
FORMAT_VALUE   0           (calls str(name) if needed)
LOAD_CONST     "!"
BUILD_STRING   3           (join 3 parts into one string)
```

`BUILD_STRING` internally:
```c
// ceval.c (simplified):
case TARGET(BUILD_STRING): {
    int oparg = ...;  // number of parts
    
    // 1. Calculate total length and max char across all parts
    Py_ssize_t total_len = 0;
    Py_UCS4 maxchar = 0;
    for (int i = 0; i < oparg; i++) {
        PyObject *piece = PEEK(oparg - i);
        total_len += PyUnicode_GET_LENGTH(piece);
        Py_UCS4 piece_max = PyUnicode_MAX_CHAR_VALUE(piece);
        if (piece_max > maxchar) maxchar = piece_max;
    }
    
    // 2. Allocate result string with optimal kind
    PyObject *result = PyUnicode_New(total_len, maxchar);
    
    // 3. Copy all parts into result
    Py_ssize_t pos = 0;
    for (int i = 0; i < oparg; i++) {
        PyObject *piece = ...;
        _PyUnicode_FastCopyCharacters(result, pos, piece, 0, piece_len);
        pos += piece_len;
    }
    
    PUSH(result);
}
```

Single allocation, single pass copy. This is why f-strings are the fastest string formatting method.

---

## 8.6 Interview Questions — Part 8

**Q1**: What does PyUnicode_New allocate?
**A**: A single contiguous block: struct header + character data + null terminator. The struct size depends on ASCII (48B) vs non-ASCII (64B). Character data = (length+1) × kind bytes.

**Q2**: Is a string literal re-created every time the code executes?
**A**: No. String literals are constants stored in the code object's `co_consts` tuple at compile time. At runtime, `LOAD_CONST` just pushes a reference to the pre-existing object.

**Q3**: What is constant folding for strings?
**A**: The compiler pre-computes constant string expressions: `"hel" + "lo"` → `"hello"` at compile time. Limited to results ≤ 4096 chars to avoid bloating .pyc files.

**Q4**: How does the single-character cache work?
**A**: All 128 ASCII single-char strings are pre-allocated at startup as immortal singletons. Characters 128-255 (Latin-1) are cached on first use. Indexing ASCII strings returns cached objects.

**Q5**: Why is BUILD_STRING (f-string) faster than repeated concatenation?
**A**: BUILD_STRING pre-computes total length + max kind in one pass, allocates ONE result string, then copies all parts. No intermediate string objects are created. Repeated `+` creates a new string for each concatenation.
