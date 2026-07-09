# Part 5 — PyUnicodeObject Structure: Every Field Explained

## 5.1 The Three-Level Struct Hierarchy

CPython uses three nested structs for strings, optimized for the common case:

```c
// Level 1: Pure ASCII strings (most common, smallest overhead)
typedef struct {
    PyObject_HEAD                        // ob_refcnt (8B) + ob_type (8B) = 16B
    Py_ssize_t length;                   // 8B: number of code points
    Py_hash_t hash;                      // 8B: cached hash (-1 = uncomputed)
    struct {
        unsigned int interned:2;         // 2 bits: interning state
        unsigned int kind:3;             // 3 bits: 0,1,2,4 (byte width)
        unsigned int compact:1;          // 1 bit: data inline?
        unsigned int ascii:1;            // 1 bit: all chars < 128?
        unsigned int ready:1;            // 1 bit: deprecated (always 1)
        unsigned int :24;                // 24 bits: padding/reserved
    } state;                             // 4B total (bit-packed)
    wchar_t *wstr;                       // 8B: deprecated (NULL in 3.12+)
} PyASCIIObject;
// Size: 16 + 8 + 8 + 4 + (4 padding) + 8 = 48 bytes

// Level 2: Non-ASCII compact strings (adds UTF-8 cache)
typedef struct {
    PyASCIIObject _base;                 // 48B: all of Level 1
    Py_ssize_t utf8_length;              // 8B: cached UTF-8 byte count
    char *utf8;                          // 8B: cached UTF-8 representation
} PyCompactUnicodeObject;
// Size: 48 + 8 + 8 = 64 bytes

// Level 3: Legacy non-compact (deprecated, external data pointer)
typedef struct {
    PyCompactUnicodeObject _base;        // 64B: all of Level 2
    union {
        void *any;
        Py_UCS1 *latin1;
        Py_UCS2 *ucs2;
        Py_UCS4 *ucs4;
    } data;                              // 8B: pointer to external buffer
} PyUnicodeObject;
// Size: 64 + 8 = 72 bytes (but data is EXTERNAL, separate allocation)
```

---

## 5.2 Field-by-Field Deep Dive

### Field: `ob_refcnt` (offset +0x00, 8 bytes)
```
Purpose: Reference count of the string object itself.
Behavior for strings:
  - Typically high for interned strings (shared across many names)
  - 1 for temporary/local strings
  - In 3.12+: special "immortal" value for singletons ("", single chars)
  
When decremented to 0: string is deallocated (unless interned immortal)
```

### Field: `ob_type` (offset +0x08, 8 bytes)
```
Purpose: Points to &PyUnicode_Type (the str type object)
Value:   Always the same for all str instances (0x... → PyUnicode_Type)
Used by: type(s) → reads this field → returns <class 'str'>
         isinstance(s, str) → checks this field
         Method dispatch: s.upper() → ob_type→tp_methods→"upper"
```

### Field: `length` (offset +0x10, 8 bytes)
```
Purpose: Number of code points in the string
Type:    Py_ssize_t (signed 64-bit)
Used by: len(s) → just reads this field → O(1)!
Range:   0 to PY_SSIZE_T_MAX

NOT the byte length! For "日本" (2BYTE_KIND):
  length = 2 (two code points)
  Actual bytes of char data = 2 × 2 = 4 bytes
```

### Field: `hash` (offset +0x18, 8 bytes)
```
Purpose: Cached hash value
Type:    Py_hash_t (signed 64-bit)
Initial: -1 (sentinel meaning "not yet computed")
Computed: On first hash(s) call, using SipHash-1-3
Cached:  Written back to this field, never recomputed

Why cache works: Strings are IMMUTABLE → hash never changes.
Performance:     First hash(s) → O(n). All subsequent → O(1).
Used by:         dict lookups, set operations, deduplication

Special: -1 is reserved as "uncomputed" sentinel.
         If SipHash computes -1, it's changed to -2.
         This means hash(s) == -1 is IMPOSSIBLE in Python.
         (Actually, the user-visible hash CAN be -1 in theory,
          but internally it's stored as -2 with -1 returned to Python.
          Implementation detail varies by version.)
```

### Field: `state` (offset +0x20, 4 bytes — bit-packed)

#### `state.interned` (2 bits)
```
Values:
  SSTATE_NOT_INTERNED  = 0  → normal string
  SSTATE_INTERNED_MORTAL = 1  → in intern table, can be GC'd
  SSTATE_INTERNED_IMMORTAL = 2  → in intern table, never freed

Determines whether this string is in the global intern table.
Interned strings are shared — multiple equal strings → one object.
```

#### `state.kind` (3 bits)
```
Values:
  PyUnicode_WCHAR_KIND = 0  → legacy (deprecated, unused in 3.12+)
  PyUnicode_1BYTE_KIND = 1  → Py_UCS1 (uint8_t): Latin-1 / ASCII
  PyUnicode_2BYTE_KIND = 2  → Py_UCS2 (uint16_t): BMP
  PyUnicode_4BYTE_KIND = 4  → Py_UCS4 (uint32_t): full Unicode

Determines how many bytes each character occupies in the data buffer.
Chosen at creation: scan all chars, find max → select smallest kind that fits.

O(1) indexing formula: char_address = data_start + index × kind
```

#### `state.compact` (1 bit)
```
Values:
  1 → character data is INLINE (immediately after the struct)
  0 → character data is at a SEPARATE heap address (legacy)

Modern CPython: almost always 1 (compact).
Non-compact only for strings created via deprecated C API.

Why it matters:
  Compact: ONE allocation for struct + data → better cache locality
  Non-compact: TWO allocations (struct + data) → extra indirection
```

#### `state.ascii` (1 bit)
```
Values:
  1 → all characters < 128 (pure ASCII)
  0 → at least one character ≥ 128

When ascii=1:
  - Struct used is PyASCIIObject (smaller, no utf8 cache fields)
  - The string IS valid UTF-8 (ASCII = UTF-8 for chars < 128)
  - No separate UTF-8 cache needed
  - Most memory-efficient representation

When ascii=0:
  - Struct used is PyCompactUnicodeObject (has utf8 cache)
  - May need separate UTF-8 representation for I/O
```

#### `state.ready` (1 bit)
```
Historical: Indicated whether the string was "ready" (fully initialized).
In modern CPython (3.12+): always 1. Deprecated.
Was needed during the transition from Python 3.2→3.3 when legacy
representations could exist alongside new ones.
```

### Field: `wstr` (offset +0x28, 8 bytes)
```
Purpose: Pointer to wchar_t representation (DEPRECATED)
Status:  NULL in Python 3.12+. Being removed entirely.
History: Required by the old PyUnicode_AS_UNICODE() C API.
         Windows needed wchar_t* for Win32 API calls.
Memory:  When non-NULL, pointed to a SEPARATE heap allocation
         of wchar_t array — wasted memory for a rarely-needed format.
```

### Field: `utf8_length` (PyCompactUnicodeObject only, offset +0x30, 8 bytes)
```
Purpose: Byte length of the cached UTF-8 representation
Value:   0 if utf8 cache not yet computed
Used by: C API functions that need UTF-8 with known length
Relationship: len(s.encode('utf-8')) == utf8_length (when cached)
```

### Field: `utf8` (PyCompactUnicodeObject only, offset +0x38, 8 bytes)
```
Purpose: Pointer to cached UTF-8 byte string
Value:   NULL if not yet computed (lazy!)
Allocated: On first call to PyUnicode_AsUTF8() or similar

For ASCII strings: this field doesn't exist (PyASCIIObject has no utf8).
  Why? ASCII strings ARE their own UTF-8 — the inline data IS valid UTF-8.
  No separate cache needed!

For non-ASCII strings: utf8 may point to a SEPARATE allocation.
  Computed lazily when .encode('utf-8') or C API requests UTF-8.
  Once computed, kept alive for the lifetime of the string.
```

---

## 5.3 Which Struct Is Used When?

```
Decision tree at string creation:

Is every character < 128 (pure ASCII)?
  YES → PyASCIIObject (48 bytes) + inline data
        state.ascii = 1, state.compact = 1, state.kind = 1
  
  NO → Is every character < 256 (Latin-1)?
    YES → PyCompactUnicodeObject (64 bytes) + inline data
          state.ascii = 0, state.compact = 1, state.kind = 1

    NO → Is every character < 65536 (BMP)?
      YES → PyCompactUnicodeObject (64 bytes) + inline data
            state.ascii = 0, state.compact = 1, state.kind = 2

      NO → PyCompactUnicodeObject (64 bytes) + inline data
           state.ascii = 0, state.compact = 1, state.kind = 4
```

Note: PyUnicodeObject (Level 3, non-compact) is only used by legacy C API code. In modern CPython, you'll almost never encounter it.

---

## 5.4 Complete Memory Calculations

### Pure ASCII: "hello" (5 chars)
```
Struct: PyASCIIObject = 48 bytes (with padding)
Data:   5 × 1 (kind=1) + 1 (null terminator) = 6 bytes
Total:  48 + 6 = 54 bytes
Verify: sys.getsizeof("hello") ≈ 54
```

### Latin-1: "café" (4 chars, max=é=U+00E9)
```
Struct: PyCompactUnicodeObject = 64 bytes
Data:   4 × 1 + 1 = 5 bytes
Total:  64 + 5 = 69 bytes (padded to ~72 or 73)
Verify: sys.getsizeof("café") ≈ 73
```

### UCS-2: "日本語" (3 chars, max=語=U+8A9E)
```
Struct: PyCompactUnicodeObject = 64 bytes
Data:   3 × 2 + 2 = 8 bytes (2-byte null terminator)
Total:  64 + 8 = 72 bytes
Verify: sys.getsizeof("日本語") ≈ 76
```

### UCS-4: "😀" (1 char, U+1F600 > U+FFFF)
```
Struct: PyCompactUnicodeObject = 64 bytes
Data:   1 × 4 + 4 = 8 bytes (4-byte null terminator)
Total:  64 + 8 = 72 bytes
Verify: sys.getsizeof("😀") ≈ 76
```

---

## 5.5 The Inline Data Layout

For compact strings, character data is stored **immediately after** the struct in memory:

```
Compact ASCII "Hi":
┌────────────────────────────────────────┐
│ PyASCIIObject (48 bytes)               │
│   ob_refcnt, ob_type, length=2,       │
│   hash=-1, state{kind=1,ascii=1,...}, │
│   wstr=NULL                           │
├────────────────────────────────────────┤
│ Inline data (3 bytes):                 │
│   'H' 'i' '\0'                        │
└────────────────────────────────────────┘
Address: one malloc gives struct + data together
Cache:   all in same allocation → excellent locality

Access: PyUnicode_1BYTE_DATA(op) returns pointer to offset 48
        (directly after struct)
```

For non-ASCII compact:
```
Compact UCS-2 "日本":
┌────────────────────────────────────────┐
│ PyCompactUnicodeObject (64 bytes)      │
│   (includes PyASCIIObject base)       │
│   utf8_length=0, utf8=NULL            │
├────────────────────────────────────────┤
│ Inline data (6 bytes):                 │
│   0x65E5 0x672C 0x0000               │
│   (日)   (本)   (null)               │
└────────────────────────────────────────┘
```

---

## 5.6 Interview Questions — Part 5

**Q1**: What three struct levels exist for Python strings and when is each used?
**A**: PyASCIIObject for pure ASCII (all chars < 128, smallest). PyCompactUnicodeObject for non-ASCII compact (chars ≥ 128, adds utf8 cache). PyUnicodeObject for legacy non-compact (deprecated, external data pointer).

**Q2**: What does the `hash` field contain before anyone calls hash(s)?
**A**: -1, a sentinel meaning "not yet computed." On first hash() call, SipHash is computed over the character data and the result is stored permanently.

**Q3**: Why does PyASCIIObject not have `utf8` and `utf8_length` fields?
**A**: Because ASCII IS valid UTF-8. The inline data buffer already serves as the UTF-8 representation. No separate cache is needed — saving 16 bytes per ASCII string.

**Q4**: What is `state.kind` and what values can it take?
**A**: A 3-bit field indicating bytes per character: 1 (1BYTE_KIND, Latin-1/ASCII), 2 (2BYTE_KIND, UCS-2/BMP), or 4 (4BYTE_KIND, UCS-4/full Unicode). Determines the indexing formula: `data + i * kind`.

**Q5**: Why is `state.compact` almost always 1 in modern CPython?
**A**: Compact means data is inline (one allocation for struct + data). Non-compact (separate data allocation) is only used by deprecated C API code paths. Modern string creation always produces compact strings.

**Q6**: How does CPython achieve O(1) indexing using these structs?
**A**: For compact strings: `data_ptr = (char*)str + struct_size`, then `char_at_i = data_ptr + i * kind`. Since `kind` is fixed per string (1, 2, or 4), this is pure pointer arithmetic — constant time.
