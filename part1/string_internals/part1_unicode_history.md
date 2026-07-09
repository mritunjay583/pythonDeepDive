# Part 1 — Unicode: History and Fundamentals

## 1.1 The Problem That Unicode Solves

In the beginning, computers dealt only with English text. Then the world needed computers.

### The ASCII Era (1963)

ASCII assigned 7-bit codes (0-127) to 128 characters:
```
0x00-0x1F: Control characters (tab, newline, null)
0x20-0x7E: Printable characters (A-Z, a-z, 0-9, punctuation)
0x7F:      DEL

Memory: 1 byte per character (high bit unused)
Total characters representable: 128
Sufficient for: English. Nothing else.
```

### The Codepage Chaos (1980s)

The high bit (128-255) was used differently by every vendor/region:
```
ISO 8859-1 (Latin-1): Western European (é, ñ, ü)
ISO 8859-5:           Cyrillic (Б, Г, Д)
ISO 8859-6:           Arabic (ب, ت, ث)
Shift_JIS:            Japanese (multi-byte: 1 or 2 bytes per char)
GB2312:               Chinese (double-byte)
Big5:                 Traditional Chinese
Windows-1252:         Microsoft's Latin-1 superset
KOI8-R:              Russian

Problem: byte 0xC0 means 'À' in Latin-1, 'Р' in Windows-1251, '타' in EUC-KR
No way to represent multiple scripts in one document!
```

This era was called "encoding hell" — the same bytes meant different things depending on the encoding, and there was no standard way to indicate which encoding a file used.

### The Unicode Solution (1988-1991)

The Unicode Consortium set out to assign a unique number (**code point**) to every character in every script ever:
```
Design Goals:
1. Universal: cover ALL characters from ALL scripts
2. Unique: each character gets exactly one code point
3. Uniform: code points are abstract numbers (encoding is separate)

Result: a single mapping from characters → numbers
  'A' → U+0041 (65)
  'é' → U+00E9 (233)
  '日' → U+65E5 (26085)
  '😀' → U+1F600 (128512)
  'ℝ' → U+211D (8477)
```

---

## 1.2 Code Points: The Abstract Layer

A **code point** is a number in the range U+0000 to U+10FFFF. It represents one "character" in the abstract Unicode character set.

```
Total space:   1,114,112 possible code points
Assigned:      ~149,000 characters (as of Unicode 15.1)
Reserved:      Private Use Areas, unassigned blocks
Forbidden:     Surrogate range U+D800-U+DFFF (used only in UTF-16)
Actually usable: 1,112,064 (total minus surrogates)
```

### The Planes

Unicode divides the code point space into 17 planes of 65,536 code points each:

```
Plane  Range               Name                            Usage
─────────────────────────────────────────────────────────────────────────
0      U+0000 - U+FFFF    Basic Multilingual Plane (BMP)  Latin, CJK, Arabic, etc.
1      U+10000 - U+1FFFF  Supplementary Multilingual       Emoji, historic scripts
2      U+20000 - U+2FFFF  Supplementary Ideographic        CJK Extension B
3      U+30000 - U+3FFFF  Tertiary Ideographic             CJK Extension G-I
4-13   U+40000 - U+DFFFF  (unassigned)
14     U+E0000 - U+EFFFF  Supplementary Special-purpose    Tags
15-16  U+F0000 - U+10FFFF Private Use Areas
```

**Key insight for CPython**: BMP (Plane 0) contains >99% of commonly used characters. Characters in Planes 1-16 are comparatively rare (emoji, historic scripts, rare CJK). This is why the 2BYTE_KIND optimization works — most strings never need 4-byte characters.

---

## 1.3 Code Points vs Code Units vs Bytes

These are three distinct concepts that are often confused:

```
LEVEL        DEFINITION                      EXAMPLE for '😀' (U+1F600)
─────────────────────────────────────────────────────────────────────────
Code Point   Abstract Unicode number         U+1F600 (ONE code point)

Code Unit    Fixed-size unit in an encoding  UTF-8:  4 code units (bytes)
                                             UTF-16: 2 code units (surrogates)
                                             UTF-32: 1 code unit

Bytes        Physical storage                UTF-8:  F0 9F 98 80
                                             UTF-16: D83D DE00 (+ BOM)
                                             UTF-32: 0001F600 (+ BOM)
```

Python's `str` operates at the **code point** level:
```python
s = "😀"
len(s)     # 1  ← one CODE POINT
s[0]       # '😀'  ← one code point accessed

# NOT byte-level:
s.encode('utf-8')   # b'\xf0\x9f\x98\x80'  (4 bytes)
s.encode('utf-16')  # b'\xff\xfe=\xd8\x00\xde'  (BOM + 4 bytes = 2 code units)
```

---

## 1.4 Encodings: Mapping Code Points to Bytes

An encoding is a **reversible function** from code points → byte sequences:

### UTF-32 (Fixed Width, 4 bytes/character)

```
Algorithm: store code point value directly as 32-bit integer
U+0041 ('A')   → 00 00 00 41
U+00E9 ('é')   → 00 00 00 E9
U+65E5 ('日')  → 00 00 65 E5
U+1F600 ('😀') → 00 01 F6 00

Properties:
  + O(1) random access (char i at byte offset 4*i)
  + Simple implementation
  - Extremely wasteful (4 bytes even for ASCII!)
  - English text uses 4× the memory of ASCII
```

### UTF-16 (Variable Width, 2 or 4 bytes/character)

```
Algorithm:
  BMP (U+0000 to U+FFFF): store directly as 16-bit integer (2 bytes)
  Above BMP: encode as surrogate pair (4 bytes total)

Surrogate Pair Encoding:
  1. Subtract 0x10000 from code point → 20-bit value
  2. High 10 bits → add to 0xD800 → high surrogate (0xD800-0xDBFF)
  3. Low 10 bits  → add to 0xDC00 → low surrogate  (0xDC00-0xDFFF)

Example: U+1F600 ('😀')
  1. 0x1F600 - 0x10000 = 0x0F600
  2. 0x0F600 = 0000111110 0110000000 (20 bits)
  3. High: 0xD800 + 0x003E = 0xD83D
  4. Low:  0xDC00 + 0x0200 = 0xDE00
  5. Encoded: D8 3D DE 00 (big-endian) or 3D D8 00 DE (little-endian)

Properties:
  + BMP characters: 2 bytes (common case efficient)
  + Used by Windows, Java, JavaScript, Qt internally
  - NOT fixed-width (surrogate pairs break O(1) indexing!)
  - Surrogates are confusing edge cases
```

### UTF-8 (Variable Width, 1-4 bytes/character)

```
Algorithm (bit-pattern based):
  U+0000-U+007F:    0xxxxxxx                        (1 byte, ASCII compatible!)
  U+0080-U+07FF:    110xxxxx 10xxxxxx               (2 bytes)
  U+0800-U+FFFF:    1110xxxx 10xxxxxx 10xxxxxx      (3 bytes)
  U+10000-U+10FFFF: 11110xxx 10xxxxxx 10xxxxxx 10xxxxxx (4 bytes)

Example: U+00E9 ('é' = 0xE9 = 11101001 binary)
  Range: U+0080-U+07FF → 2 bytes
  Split: 000_11 101001 → 110_00011 10_101001 = 0xC3 0xA9

Example: U+65E5 ('日' = 0x65E5 = 0110 0101 1110 0101)
  Range: U+0800-U+FFFF → 3 bytes
  Split: 0110 010111 100101 → 1110_0110 10_010111 10_100101 = 0xE6 0x97 0xA5

Properties:
  + ASCII compatible (ASCII files are valid UTF-8!)
  + Self-synchronizing (can find char boundaries from any position)
  + No endianness issues
  + Most compact for ASCII-heavy text
  + Standard for web, files, network protocols
  - Variable width → O(n) indexing
  - CJK text larger than UTF-16 (3 bytes vs 2)
```

---

## 1.5 Why CPython Doesn't Use Any Standard Encoding Internally

None of the standard encodings satisfies CPython's requirements:

| Requirement | UTF-8 | UTF-16 | UTF-32 |
|-------------|--------|--------|--------|
| O(1) indexing `s[i]` | ❌ Variable width | ❌ Surrogates | ✅ Fixed 4B |
| Memory efficient for ASCII | ✅ 1 byte/char | ❌ 2 bytes/char | ❌ 4 bytes/char |
| Memory efficient for BMP | ❌ 3 bytes/CJK | ✅ 2 bytes/char | ❌ 4 bytes/char |
| Covers all Unicode | ✅ | ✅ | ✅ |
| Simple implementation | ✅ | Medium | ✅ |

CPython's solution (PEP 393): **internal representation that adapts per-string** — 1, 2, or 4 bytes per character based on the maximum code point in that specific string. This gives O(1) indexing AND memory efficiency.

---

## 1.6 The Critical Distinction: Characters vs Code Points vs Graphemes

What a human perceives as a "character" may be:

```python
# One code point = one perceived character:
"A"        # U+0041, len=1 ✓

# Two code points = one perceived character:
"é"        # Could be U+0065 U+0301 (e + combining acute), len=2!
           # Or: U+00E9 (precomposed é), len=1

# Multiple code points = one perceived character:
"🇺🇸"      # U+1F1FA U+1F1F8 (regional indicators), len=2
"👨‍👩‍👧‍👦"    # U+1F468 U+200D U+1F469 U+200D U+1F467 U+200D U+1F466, len=7!
"ñ̃"       # U+006E U+0303 U+0303 (n + two combining tildes), len=3

# Why this matters for CPython:
# len() counts CODE POINTS, not graphemes
# s[i] returns ONE code point, not one grapheme
# This is by design — grapheme segmentation is locale-dependent
```

---

## 1.7 Interview Questions — Part 1

**Q1**: What is the difference between a code point and a code unit?
**A**: A code point is an abstract number assigned to a character (U+0000 to U+10FFFF). A code unit is a fixed-size chunk in a specific encoding: 8 bits for UTF-8, 16 bits for UTF-16, 32 bits for UTF-32. One code point may require multiple code units.

**Q2**: Why can't CPython use UTF-8 for internal string storage?
**A**: UTF-8 is variable-width (1-4 bytes per character). `s[i]` would require scanning from the beginning to count i characters → O(n). Python guarantees O(1) indexing.

**Q3**: What is a surrogate pair?
**A**: In UTF-16, code points above U+FFFF are encoded as two 16-bit code units: a high surrogate (0xD800-0xDBFF) followed by a low surrogate (0xDC00-0xDFFF). Together they represent one code point.

**Q4**: Why does `len("👨‍👩‍👧‍👦")` return 7?
**A**: This emoji is composed of 7 code points (4 person emojis + 3 Zero Width Joiners). Python's len() counts code points, not grapheme clusters (visual characters).

**Q5**: What is the total Unicode code point space?
**A**: 1,114,112 code points (U+0000 to U+10FFFF). 17 planes × 65,536 per plane. Minus surrogates (2,048), leaving 1,112,064 usable.

**Q6**: Why is Latin-1 special for CPython?
**A**: Latin-1 (ISO 8859-1) has a 1:1 identity mapping to Unicode code points U+0000-U+00FF (byte value = code point value). This makes conversion trivial and enables CPython's 1BYTE_KIND to store any code point ≤ 255 directly.
