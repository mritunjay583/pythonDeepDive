# Part 2 — Encoding Deep Dive

## 2.1 UTF-8: Complete Bit-Level Specification

UTF-8 uses a prefix-free variable-length encoding. The first byte determines the total length:

```
First Byte Pattern   Total Bytes   Code Point Bits   Code Point Range
─────────────────────────────────────────────────────────────────────
0xxxxxxx             1             7                 U+0000 - U+007F
110xxxxx 10xxxxxx    2             11                U+0080 - U+07FF
1110xxxx 10xxxxxx²   3             16                U+0800 - U+FFFF
11110xxx 10xxxxxx³   4             21                U+10000 - U+10FFFF

Key Properties:
  - Leading 0: single byte (ASCII)
  - Leading 110: 2-byte start
  - Leading 1110: 3-byte start
  - Leading 11110: 4-byte start
  - Leading 10: continuation byte (NEVER starts a character)
```

### Worked Examples

```
'A' (U+0041 = 0100 0001):
  Fits in 7 bits → 1 byte
  Encoding: 0_1000001 = 0x41
  Bytes: [41]

'é' (U+00E9 = 000 1110 1001):
  Needs 8 bits → 2 bytes
  Split into 5+6: 00011 101001
  Encoding: 110_00011 10_101001 = 0xC3 0xA9
  Bytes: [C3 A9]

'€' (U+20AC = 0010 0000 1010 1100):
  Needs 16 bits → 3 bytes
  Split into 4+6+6: 0010 000010 101100
  Encoding: 1110_0010 10_000010 10_101100 = 0xE2 0x82 0xAC
  Bytes: [E2 82 AC]

'😀' (U+1F600 = 0 0001 1111 0110 0000 0000):
  Needs 17 bits → 4 bytes
  Split into 3+6+6+6: 000 011111 011000 000000
  Encoding: 11110_000 10_011111 10_011000 10_000000 = 0xF0 0x9F 0x98 0x80
  Bytes: [F0 9F 98 80]
```

### Self-Synchronization Property

Given any byte in a UTF-8 stream, you can determine if it's:
- A single-byte character (starts with 0)
- A multi-byte start (starts with 11)
- A continuation (starts with 10)

This means: if you jump into the middle of a UTF-8 stream, you can scan forward/backward to the nearest character boundary. No other variable-length encoding has this property as simply.

### Over-long Encoding (Security!)

UTF-8 mandates the **shortest** encoding:
```
'A' (U+0041):
  VALID:   [41]           (1 byte)
  INVALID: [C1 81]       (2-byte over-long — REJECTED)
  INVALID: [E0 81 81]    (3-byte over-long — REJECTED)
  INVALID: [F0 80 81 81] (4-byte over-long — REJECTED)
```

Over-long encodings were historically used for security exploits (e.g., encoding "/" as overlong to bypass path validation). Python's codecs correctly reject these.

---

## 2.2 UTF-16: Surrogate Pairs in Detail

### BMP Characters (U+0000 to U+FFFF, excluding surrogates):
```
Store the code point value directly as a 16-bit integer.
'A' (U+0041) → 0x0041 (2 bytes)
'日' (U+65E5) → 0x65E5 (2 bytes)
```

### Surrogate Pair Algorithm (U+10000 to U+10FFFF):
```
Input: code point P (where P ≥ 0x10000)

Step 1: P' = P - 0x10000 (result fits in 20 bits: 0x00000 to 0xFFFFF)
Step 2: high = 0xD800 + (P' >> 10)    (top 10 bits + 0xD800)
Step 3: low  = 0xDC00 + (P' & 0x3FF)  (bottom 10 bits + 0xDC00)

Result: [high surrogate][low surrogate] (4 bytes total)
```

### Detailed Example: U+1F4A9 (💩)
```
Step 1: 0x1F4A9 - 0x10000 = 0x0F4A9
Step 2: 0x0F4A9 >> 10 = 0x003D → 0xD800 + 0x003D = 0xD83D
Step 3: 0x0F4A9 & 0x3FF = 0x00A9 → 0xDC00 + 0x00A9 = 0xDCA9
Result: [D83D][DCA9]

Verification: 
  ((0xD83D - 0xD800) << 10) + (0xDCA9 - 0xDC00) + 0x10000
  = (0x3D << 10) + 0xA9 + 0x10000
  = 0xF400 + 0xA9 + 0x10000
  = 0x1F4A9 ✓
```

### Byte Order Mark (BOM)

UTF-16 has endianness ambiguity:
```
'A' = U+0041:
  Big-endian (UTF-16BE):    00 41
  Little-endian (UTF-16LE): 41 00

BOM (Byte Order Mark) = U+FEFF at the start:
  Big-endian:    FE FF (then data in big-endian)
  Little-endian: FF FE (then data in little-endian)

Python behavior:
  "A".encode('utf-16')    → b'\xff\xfe\x41\x00'  (LE + BOM on most systems)
  "A".encode('utf-16-be') → b'\x00\x41'           (BE, no BOM)
  "A".encode('utf-16-le') → b'\x41\x00'           (LE, no BOM)
```

---

## 2.3 UTF-32: The Simplest Encoding

```
Every code point stored as a 32-bit (4 byte) integer:

'A' (U+0041) → 00 00 00 41 (BE) or 41 00 00 00 (LE)
'日' (U+65E5) → 00 00 65 E5 (BE) or E5 65 00 00 (LE)
'😀' (U+1F600) → 00 01 F6 00 (BE) or 00 F6 01 00 (LE)

Properties:
  + Trivially O(1) indexing: byte_offset = index * 4
  + Simple: no encoding logic needed
  + No surrogates, no multi-byte issues
  - Extremely wasteful: ASCII text is 4× larger
  - Almost never used for storage or transmission
  - Used internally by some systems (CPython's 4BYTE_KIND is essentially UCS-4)
```

---

## 2.4 Encoding Comparison Table

For the string "Hello, 世界! 😀" (12 code points):

```
Encoding    Bytes    Breakdown
─────────────────────────────────────────────────────────────
ASCII       N/A      Can't represent non-ASCII characters!
Latin-1     N/A      Can't represent CJK or emoji!
UTF-8       19       H(1)+e(1)+l(1)+l(1)+o(1)+,(1)+SP(1)+世(3)+界(3)+!(1)+SP(1)+😀(4)
UTF-16LE    26       H(2)+e(2)+l(2)+l(2)+o(2)+,(2)+SP(2)+世(2)+界(2)+!(2)+SP(2)+😀(4)
UTF-32      48       12 × 4 bytes
CPython     48       12 × 4 (UCS-4, because max char is 😀 > U+FFFF)
```

For "Hello, World!" (13 ASCII chars):
```
Encoding    Bytes
─────────────────
UTF-8       13     (1 byte each)
UTF-16      26     (2 bytes each)
UTF-32      52     (4 bytes each)
CPython     13     (1BYTE_KIND! Optimal!)
```

CPython wins here — for the overwhelmingly common case of ASCII strings, it uses the minimal 1 byte per character.

---

## 2.5 Python's Relationship with Encodings

```python
# str is ALWAYS Unicode code points (internal representation is hidden)
s = "Hello"  # str — code points, not bytes

# bytes is raw byte sequence (no encoding assumption)
b = b"Hello"  # bytes — just bytes 72, 101, 108, 108, 111

# Converting between them:
s.encode('utf-8')     # str → bytes (code points → UTF-8 bytes)
b.decode('utf-8')     # bytes → str (UTF-8 bytes → code points)

# The internal representation (1/2/4 byte) is NOT an encoding!
# It's an implementation detail for efficient code point storage.
# You NEVER see it from Python code.
```

---

## 2.6 Interview Questions — Part 2

**Q1**: How many bytes does UTF-8 use for 'é' (U+00E9)?
**A**: 2 bytes (0xC3 0xA9). U+00E9 falls in range U+0080-U+07FF → 110xxxxx 10xxxxxx pattern.

**Q2**: What is a UTF-16 surrogate pair? When is it needed?
**A**: Two 16-bit code units (high surrogate 0xD800-0xDBFF + low surrogate 0xDC00-0xDFFF) that together represent one code point above U+FFFF. Needed for emoji, rare CJK, historic scripts.

**Q3**: Why is UTF-8 self-synchronizing?
**A**: Continuation bytes always start with `10`, start bytes never do. From any position, you can scan to find the nearest character boundary by looking for a byte that doesn't start with `10`.

**Q4**: What is an over-long encoding and why is it dangerous?
**A**: Encoding a character with more bytes than necessary (e.g., '/' as 2-byte `C0 AF` instead of 1-byte `2F`). Security risk: an attacker could bypass string-matching filters that only check the canonical form.

**Q5**: Why does `"A".encode('utf-16')` produce `b'\xff\xfe\x41\x00'` (4 bytes, not 2)?
**A**: The `utf-16` codec prepends a BOM (Byte Order Mark: FF FE for little-endian) to indicate endianness. Use `utf-16-le` or `utf-16-be` to suppress the BOM.

**Q6**: In CPython's internal storage, what does a string like "Hello😀" use?
**A**: 4BYTE_KIND (UCS-4) for ALL characters — because the maximum code point (😀 = U+1F600) exceeds U+FFFF. Even 'H' is stored as 4 bytes internally: `00 00 00 48`.
