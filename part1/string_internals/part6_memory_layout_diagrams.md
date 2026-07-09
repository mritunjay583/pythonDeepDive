# Part 6 — Memory Layout Diagrams

## 6.1 Empty String `""`

```
Address    Field                    Value              Bytes
═══════════════════════════════════════════════════════════════
+0x00      ob_refcnt                IMMORTAL           8
+0x08      ob_type                  → PyUnicode_Type   8
+0x10      length                   0                  8
+0x18      hash                     0 (hash of "")    8
+0x20      state.interned           2 (IMMORTAL)       ─┐
           state.kind               1 (1BYTE)           │ 4
           state.compact            1                   │
           state.ascii              1                  ─┘
+0x24      (padding)                0                  4
+0x28      wstr                     NULL               8
───────────────────────────────────────────────────────────────
+0x30      data[0]                  '\0'               1
═══════════════════════════════════════════════════════════════
TOTAL: 49 bytes.  sys.getsizeof("") → 49

Notes:
  - Singleton — there is only ONE empty string in all of CPython
  - Immortal — never deallocated, refcount never changes
  - hash is pre-computed to 0
  - The null terminator is the ONLY data byte
```

---

## 6.2 Single ASCII Character `"A"`

```
Address    Field                    Value              Bytes
═══════════════════════════════════════════════════════════════
+0x00      ob_refcnt                IMMORTAL           8
+0x08      ob_type                  → PyUnicode_Type   8
+0x10      length                   1                  8
+0x18      hash                     (precomputed)      8
+0x20      state                    kind=1,ascii=1     4
+0x24      (padding)                                   4
+0x28      wstr                     NULL               8
───────────────────────────────────────────────────────────────
+0x30      data[0]                  0x41 ('A')         1
+0x31      data[1]                  0x00 ('\0')        1
═══════════════════════════════════════════════════════════════
TOTAL: 50 bytes.  sys.getsizeof("A") → 50

Notes:
  - ALL 128 single-ASCII-char strings are pre-allocated singletons
  - chr(0) through chr(127) are cached at interpreter startup
  - "A" is "A" → always True (same object)
  - Interned as IMMORTAL (never freed)
```

---

## 6.3 Short ASCII String `"hello"`

```
PyASCIIObject (state.ascii=1, state.compact=1)
═══════════════════════════════════════════════════════════════
+0x00  │ ob_refcnt     │ 1                              │ 8B
+0x08  │ ob_type       │ → PyUnicode_Type               │ 8B
+0x10  │ length        │ 5                              │ 8B
+0x18  │ hash          │ -1 (not yet computed)          │ 8B
+0x20  │ state         │ kind=1, compact=1, ascii=1,    │ 4B
       │               │ interned=1 (MORTAL)            │
+0x24  │ (pad)         │ 0                              │ 4B
+0x28  │ wstr          │ NULL                           │ 8B
═══════╪═══════════════╪════════════════════════════════╪═══
+0x30  │ data[0]       │ 0x68 ('h')                    │ 1B
+0x31  │ data[1]       │ 0x65 ('e')                    │ 1B
+0x32  │ data[2]       │ 0x6C ('l')                    │ 1B
+0x33  │ data[3]       │ 0x6C ('l')                    │ 1B
+0x34  │ data[4]       │ 0x6F ('o')                    │ 1B
+0x35  │ data[5]       │ 0x00 ('\0')                   │ 1B
═══════════════════════════════════════════════════════════════
TOTAL: 0x36 = 54 bytes.  sys.getsizeof("hello") → 54

Indexing: s[2] → *(data_start + 2 * 1) → *(0x30 + 2) → 0x32 → 'l'
```

---

## 6.4 Latin-1 String `"café"` (max char é = U+00E9 = 233)

```
PyCompactUnicodeObject (state.ascii=0, state.compact=1, state.kind=1)
═══════════════════════════════════════════════════════════════
+0x00  │ ob_refcnt     │ 1                              │ 8B
+0x08  │ ob_type       │ → PyUnicode_Type               │ 8B
+0x10  │ length        │ 4                              │ 8B
+0x18  │ hash          │ -1                             │ 8B
+0x20  │ state         │ kind=1, compact=1, ascii=0,    │ 4B
       │               │ interned=0                     │
+0x24  │ (pad)         │                                │ 4B
+0x28  │ wstr          │ NULL                           │ 8B
+0x30  │ utf8_length   │ 0 (not cached yet)             │ 8B
+0x38  │ utf8          │ NULL (not cached yet)          │ 8B
═══════╪═══════════════╪════════════════════════════════╪═══
+0x40  │ data[0]       │ 0x63 ('c')                    │ 1B
+0x41  │ data[1]       │ 0x61 ('a')                    │ 1B
+0x42  │ data[2]       │ 0x66 ('f')                    │ 1B
+0x43  │ data[3]       │ 0xE9 ('é')                    │ 1B ← Latin-1 byte!
+0x44  │ data[4]       │ 0x00 ('\0')                   │ 1B
═══════════════════════════════════════════════════════════════
TOTAL: 0x45 = 69 bytes (may be padded to 72-73)

Note: The é is stored as SINGLE BYTE 0xE9 (code point value directly).
      This is the Latin-1 trick: byte value == code point value for 0-255.
      The utf8 field is NULL — will be lazily filled if .encode('utf-8') is called.
      When filled: utf8 → separate allocation: [0x63, 0x61, 0x66, 0xC3, 0xA9, 0x00]
                   (UTF-8 of é is 2 bytes: 0xC3 0xA9)
```

---

## 6.5 UCS-2 String `"日本語"` (max char 語 = U+8A9E)

```
PyCompactUnicodeObject (state.kind=2)
═══════════════════════════════════════════════════════════════
+0x00  │ ob_refcnt     │ 1                              │ 8B
+0x08  │ ob_type       │ → PyUnicode_Type               │ 8B
+0x10  │ length        │ 3                              │ 8B
+0x18  │ hash          │ -1                             │ 8B
+0x20  │ state         │ kind=2, compact=1, ascii=0     │ 4B
+0x24  │ (pad)         │                                │ 4B
+0x28  │ wstr          │ NULL                           │ 8B
+0x30  │ utf8_length   │ 0                              │ 8B
+0x38  │ utf8          │ NULL                           │ 8B
═══════╪═══════════════╪════════════════════════════════╪═══
+0x40  │ data[0]       │ 0x65E5  (日)                   │ 2B
+0x42  │ data[1]       │ 0x672C  (本)                   │ 2B
+0x44  │ data[2]       │ 0x8A9E  (語)                   │ 2B
+0x46  │ data[3]       │ 0x0000  ('\0' null, 2 bytes)  │ 2B
═══════════════════════════════════════════════════════════════
TOTAL: 0x48 = 72 bytes

Indexing: s[1] → *(data_start + 1 * 2) → *(0x40 + 2) → 0x42 → 0x672C → '本'

Note: Each character is a uint16_t (Py_UCS2).
      O(1) indexing: multiply index by 2, add to data base.
      No surrogate pairs — each 2-byte value IS the code point directly.
```

---

## 6.6 UCS-4 String `"Hello😀!"` (max char 😀 = U+1F600)

```
PyCompactUnicodeObject (state.kind=4)
═══════════════════════════════════════════════════════════════
+0x00  │ ob_refcnt     │ 1                              │ 8B
+0x08  │ ob_type       │ → PyUnicode_Type               │ 8B
+0x10  │ length        │ 7                              │ 8B
+0x18  │ hash          │ -1                             │ 8B
+0x20  │ state         │ kind=4, compact=1, ascii=0     │ 4B
+0x24  │ (pad)         │                                │ 4B
+0x28  │ wstr          │ NULL                           │ 8B
+0x30  │ utf8_length   │ 0                              │ 8B
+0x38  │ utf8          │ NULL                           │ 8B
═══════╪═══════════════╪════════════════════════════════╪═══
+0x40  │ data[0]       │ 0x00000048  ('H')              │ 4B
+0x44  │ data[1]       │ 0x00000065  ('e')              │ 4B
+0x48  │ data[2]       │ 0x0000006C  ('l')              │ 4B
+0x4C  │ data[3]       │ 0x0000006C  ('l')              │ 4B
+0x50  │ data[4]       │ 0x0000006F  ('o')              │ 4B
+0x54  │ data[5]       │ 0x0001F600  ('😀')             │ 4B ← forces 4BYTE!
+0x58  │ data[6]       │ 0x00000021  ('!')              │ 4B
+0x5C  │ data[7]       │ 0x00000000  ('\0')             │ 4B
═══════════════════════════════════════════════════════════════
TOTAL: 0x60 = 96 bytes

Observe: 'H' (U+0048) occupies 4 bytes as 0x00000048!
         6 out of 7 characters are ASCII but ALL stored as 4 bytes
         because ONE emoji forces the entire string to 4BYTE_KIND.

         Without emoji: "Hello!" → ASCII → 48 + 7 = 55 bytes
         With emoji:    "Hello😀!" → UCS-4 → 64 + 32 = 96 bytes
         Cost of one emoji: 96 - 55 = 41 extra bytes (74% increase!)
```

---

## 6.7 Multilingual String `"Hé日😀"` (mixed scripts)

```
Characters and their code points:
  'H'  = U+0048   (7 bits,  fits in 1 byte)
  'é'  = U+00E9   (8 bits,  fits in 1 byte)  
  '日' = U+65E5   (16 bits, fits in 2 bytes)
  '😀' = U+1F600  (17 bits, needs 4 bytes)  ← MAXIMUM

Kind determination: max(0x48, 0xE9, 0x65E5, 0x1F600) = 0x1F600 > 0xFFFF → 4BYTE_KIND

PyCompactUnicodeObject (kind=4):
+0x40  │ 0x00000048 │ 0x000000E9 │ 0x000065E5 │ 0x0001F600 │ 0x00000000 │
       │    'H'     │    'é'     │    '日'    │    '😀'    │   '\0'     │
       │   4 bytes  │   4 bytes  │   4 bytes  │   4 bytes  │  4 bytes   │

Total data: 5 × 4 = 20 bytes
Total object: 64 + 20 = 84 bytes

Comparison if stored optimally per-character (hypothetical):
  H=1B + é=1B + 日=2B + 😀=4B = 8 bytes
  CPython uses: 4+4+4+4 = 16 bytes (2× overhead)
  
  Trade-off: 2× memory for O(1) indexing guarantee.
```

---

## 6.8 After hash() Is Called

```
BEFORE hash("hello"):
+0x18  │ hash  │ -1  (UNCOMPUTED)

AFTER hash("hello"):
+0x18  │ hash  │ 4420697037752 (or whatever SipHash produces)

The field is written ONCE and never changes.
Subsequent hash() calls: just read this field → O(1).

For the intern table check and dict lookup, this cached hash
means "hello" as a dict key costs O(n) only the FIRST time.
```

---

## 6.9 After .encode('utf-8') Is Called (Latin-1 String)

```
BEFORE "café".encode('utf-8'):
+0x30  │ utf8_length │ 0    │
+0x38  │ utf8        │ NULL │

AFTER "café".encode('utf-8'):  (é → 0xC3 0xA9 in UTF-8)
+0x30  │ utf8_length │ 5    │  (c=1 + a=1 + f=1 + é=2 = 5 bytes)
+0x38  │ utf8        │ → 0x7F002000 (separate heap allocation) │

At 0x7F002000:
  [0x63][0x61][0x66][0xC3][0xA9][0x00]   (5 chars + null = 6 bytes)

This cache persists for the lifetime of the string object.
Next .encode('utf-8') or C API UTF-8 request: returns cached pointer.
```

---

## 6.10 Memory Comparison Table

```
String            Kind      Header   Data     Total    vs UTF-8 bytes
─────────────────────────────────────────────────────────────────────
""                ASCII     48       1        49       0
"a"               ASCII     48       2        50       1
"hello"           ASCII     48       6        54       5
"hello world!!!"  ASCII     48       15       63       14
"café"            Latin-1   64       5        69       5
"naïve"           Latin-1   64       6        70       7
"日本語"           UCS-2     64       8        72       9
"αβγδε"           UCS-2     64       12       76       10
"Hello😀"         UCS-4     64       32       96       10
"😀😀😀"          UCS-4     64       16       80       12
"a"*1000          ASCII     48       1001     1049     1000
"日"*1000         UCS-2     64       2002     2066     3000
"😀"*1000        UCS-4     64       4004     4068     4000
```

Key insight: CPython is MORE efficient than UTF-8 for pure ASCII (49 vs struct+bytes overhead) and for CJK text (2 bytes/char vs 3 bytes/char). It's LESS efficient than UTF-8 when emoji forces 4BYTE on mostly-ASCII text.

---

## 6.11 Interview Questions — Part 6

**Q1**: Draw the memory layout difference between "hi" and "hi😀".
**A**: "hi" = PyASCIIObject(48) + [0x68, 0x69, 0x00] = 51 bytes. "hi😀" = PyCompactUnicodeObject(64) + [0x00000068, 0x00000069, 0x0001F600, 0x00000000] = 80 bytes. The emoji forces all chars to 4 bytes.

**Q2**: Where exactly in memory is the character data for a compact ASCII string?
**A**: At offset 48 (immediately after the PyASCIIObject struct). For non-ASCII compact: at offset 64 (after PyCompactUnicodeObject). Single contiguous allocation.

**Q3**: What happens to the utf8 field when you call .encode('utf-8') on a Latin-1 string?
**A**: A separate heap allocation is made for the UTF-8 bytes. The `utf8` pointer is set to this allocation and `utf8_length` records the byte count. This cache persists for the string's lifetime.

**Q4**: Why is the null terminator wider for UCS-2 and UCS-4 strings?
**A**: The null must match the character width. UCS-2 null = 0x0000 (2 bytes). UCS-4 null = 0x00000000 (4 bytes). Required for C API functions that expect null-terminated wide strings.
