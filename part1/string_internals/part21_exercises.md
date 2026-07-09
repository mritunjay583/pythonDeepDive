# Part 21 — Exercises: Memory Tracing & Implementation

## Section A: Memory Layout Exercises (10)

### Exercise 1
Calculate exact memory for `s = "Hello, World!"` (13 ASCII chars):
```
Struct: PyASCIIObject = 48 bytes
Data: 13 chars × 1 byte + 1 null = 14 bytes
Total: 48 + 14 = 62 bytes
Verify: sys.getsizeof("Hello, World!") ≈ 62
```

### Exercise 2
Calculate memory for `s = "Ñ"` (single Latin-1 char, U+00D1):
```
Struct: PyCompactUnicodeObject = 64 bytes (non-ASCII, needs utf8 cache fields)
Data: 1 × 1 + 1 null = 2 bytes
Total: 64 + 2 = 66 bytes
BUT: likely from single-char cache (128-255 range, cached lazily)
```

### Exercise 3
Calculate memory for `s = "こんにちは"` (5 CJK chars, max U+306F):
```
Kind: 2BYTE (max < 65536)
Struct: 64 bytes
Data: 5 × 2 + 2 null = 12 bytes
Total: 64 + 12 = 76 bytes
```

### Exercise 4
What kind and memory for `s = "Hello 🌍"` (6 ASCII + 1 emoji)?
```
Max char: 🌍 = U+1F30D > U+FFFF → 4BYTE_KIND
Struct: 64 bytes
Data: 7 × 4 + 4 null = 32 bytes
Total: 64 + 32 = 96 bytes

Compare: "Hello " alone = 48 + 7 = 55 bytes (ASCII)
The emoji adds 96 - 55 = 41 bytes of overhead!
```

### Exercise 5
After `hash(s)` is called on "café", draw the field changes:
```
BEFORE: hash = -1 (0xFFFFFFFFFFFFFFFF), utf8 = NULL, utf8_length = 0
AFTER hash(): hash = <computed SipHash value>
utf8 and utf8_length: UNCHANGED (hash doesn't trigger UTF-8 caching)
```

### Exercise 6
After `s.encode('utf-8')` on "café", draw the field changes:
```
BEFORE: utf8 = NULL, utf8_length = 0
AFTER encode(): 
  utf8 → heap allocation: [0x63, 0x61, 0x66, 0xC3, 0xA9, 0x00] (6 bytes)
  utf8_length = 5
```

### Exercise 7
How much memory do 100,000 interned 10-char ASCII strings use vs non-interned?
```
Non-interned (all unique): 100,000 × (48 + 11) = 100,000 × 59 ≈ 5.9 MB
Interned (all same value): 1 × 59 bytes + intern table entry ≈ 59 bytes
Interned (100 unique values, 1000 refs each): 100 × 59 + table overhead ≈ 6 KB
Plus: 100,000 pointers in whatever holds them = 800 KB

Savings from interning 100 unique values across 100K refs: ~5 MB
```

### Exercise 8
What is the internal representation of concatenating "abc" + "日本"?
```
"abc" is 1BYTE_KIND (ASCII)
"日本" is 2BYTE_KIND (UCS-2)
Result "abc日本": max(0x63, 0x672C) = 0x672C > 0xFF → 2BYTE_KIND

Result data: [0x0061][0x0062][0x0063][0x65E5][0x672C][0x0000]
             Each char stored as 2 bytes. 'a' = 0x0061 (widened!)
Total data: 6 × 2 = 12 bytes
```

### Exercise 9
What kind is `"Hello😀"[0:5]`?
```
Source: "Hello😀" is 4BYTE_KIND
Slice "Hello": max char = 'o' = U+006F < 128 → 1BYTE_KIND (ASCII!)
CPython scans the slice content to determine optimal kind.
Result uses PyASCIIObject (48 bytes) + 6 bytes data = 54 bytes.
```

### Exercise 10
Memory comparison: `["hello"] * 1000` vs `["hello" for _ in range(1000)]`:
```
["hello"] * 1000:
  1 list object + 1000 pointers (all same object!)
  1 string "hello" (interned, 54 bytes)
  Total: ~8056 (list) + 54 (one string) ≈ 8.1 KB

["hello" for _ in range(1000)]:
  Same! "hello" is a compile-time constant, interned.
  All 1000 entries point to the same interned string.
  Total: ~8.1 KB (identical!)
  
But: [f"item_{i}" for i in range(1000)]:
  1000 DIFFERENT strings, each ~58 bytes
  Total: 8056 (list) + 1000 × 58 ≈ 66 KB
```

---

## Section B: Encoding Exercises (5)

### Exercise 11
Manually encode "Hé" to UTF-8:
```
'H' = U+0048 → single byte: 0x48
'é' = U+00E9 = 1110 1001 (8 bits, needs 2-byte UTF-8)
  Split: 000_11 101001
  Encode: 110_00011 10_101001 = 0xC3 0xA9
Result: b'\x48\xc3\xa9' = b'H\xc3\xa9'
```

### Exercise 12
Manually encode "日" (U+65E5) to UTF-8:
```
U+65E5 = 0110 0101 1110 0101 (16 bits, needs 3-byte UTF-8)
Split: 0110 010111 100101
Encode: 1110_0110 10_010111 10_100101 = 0xE6 0x97 0xA5
Result: b'\xe6\x97\xa5'
Verify: "日".encode('utf-8') == b'\xe6\x97\xa5'
```

### Exercise 13
Decode b'\xf0\x9f\x98\x80' from UTF-8:
```
First byte: 0xF0 = 11110_000 → 4-byte sequence
Remaining: 0x9F=10_011111, 0x98=10_011000, 0x80=10_000000
Code point bits: 000 011111 011000 000000 = 0x1F600
chr(0x1F600) = '😀'
```

### Exercise 14
What goes wrong with: `b'\xc3\xa9'.decode('latin-1')`?
```
Latin-1 decodes each byte directly as its code point value:
  0xC3 → U+00C3 = 'Ã'
  0xA9 → U+00A9 = '©'
Result: "Ã©" (MOJIBAKE — incorrect! The bytes were UTF-8 for 'é')
Correct: b'\xc3\xa9'.decode('utf-8') → "é"
```

### Exercise 15
How many bytes does "Hello 🌍!" produce in each encoding?
```
UTF-8:  H(1)+e(1)+l(1)+l(1)+o(1)+SP(1)+🌍(4)+!(1) = 11 bytes
UTF-16: H(2)+e(2)+l(2)+l(2)+o(2)+SP(2)+🌍(4)+!(2) = 18 bytes (+2 BOM = 20)
UTF-32: 8 × 4 = 32 bytes (+4 BOM = 36)
CPython internal (4BYTE): 8 × 4 = 32 bytes (no BOM, data only)
```

---

## Section C: Interning Exercises (5)

### Exercise 16
Predict which are the same object:
```python
a = "hello";  b = "hello"         → a is b: True (auto-interned)
c = "hel" + "lo"                  → c is a: True (constant folding)
d = "hel"; d = d + "lo"           → d is a: False (runtime concat)
e = sys.intern(d)                 → e is a: True (intern returns canonical)
f = "hello!"; g = "hello!"        → f is g: depends (punctuation, not identifier)
```

### Exercise 17
What happens to memory when you intern 10 copies of "data":
```python
strings = ["data", "data", "data", "data", "data",
           "data", "data", "data", "data", "data"]
```
**Answer**: "data" is a compile-time constant, already interned. All 10 list entries point to the SAME object. Memory: 1 string (54B) + 1 list (56+80B) = ~190 bytes total.

### Exercise 18
Why does this waste memory?
```python
for i in range(1000000):
    key = sys.intern(f"key_{i}")
```
**Answer**: 1M UNIQUE strings interned → 1M entries in intern table, never freed (mortal but kept alive by table reference). ~60 MB wasted. Only intern strings with HIGH repetition.

### Exercise 19
After `del s`, is an interned string freed?
```python
s = sys.intern("unique_value")
del s
# Is "unique_value" still in the intern table?
```
**Answer**: Yes! The intern table holds a reference. Only if the table is the ONLY reference (refcnt=1 from table) might it eventually be cleaned up. In practice: persists until shutdown.

### Exercise 20
How does interning affect this dict lookup performance?
```python
d = {"name": "Alice", "age": 30}
key = "name"
d[key]  # How many steps?
```
**Answer**: "name" is interned (identifier). Dict key "name" is also interned. Lookup: hash("name") → cached O(1) → find slot → `stored_key == lookup_key` → True (pointer comparison, same interned object!) → O(1) total. No character comparison needed.

---

## Section D: Implementation Exercises (5)

### Exercise 21
Implement a simplified version of str.join():
```python
def my_join(sep, items):
    if not items:
        return ""
    # Phase 1: calculate total length
    total = sum(len(s) for s in items) + len(sep) * (len(items) - 1)
    # Phase 2: build result (using list for simplicity)
    result = []
    for i, item in enumerate(items):
        if i > 0:
            result.append(sep)
        result.append(item)
    return "".join(result)  # Single final allocation
```

### Exercise 22
Why is this O(n²)? How to fix?
```python
def build_csv(rows):
    result = ""
    for row in rows:
        result += ",".join(str(x) for x in row) + "\n"
    return result

# Fix:
def build_csv(rows):
    lines = [",".join(str(x) for x in row) for row in rows]
    return "\n".join(lines) + "\n"
```

### Exercise 23
Predict the kind after each operation:
```python
a = "hello"         # 1BYTE (ASCII)
b = a + "café"      # 1BYTE (max é=0xE9 ≤ 0xFF, still Latin-1!)
c = b + "日"        # 2BYTE (日=U+65E5 > 0xFF)
d = c + "😀"       # 4BYTE (😀=U+1F600 > 0xFFFF)
e = d[0:5]          # 1BYTE (ASCII chars only in that slice!)
```

### Exercise 24
Trace the hash caching:
```python
s = "test"
d = {s: 1}        # hash(s) computed HERE (O(n=4))
d[s]              # hash(s) returned from cache (O(1))
d["test"]         # "test" is same interned object → same cached hash
another = "te"+"st"  # runtime concat → different object
d[another]        # hash(another) computed (O(4)), then char comparison with s
```

### Exercise 25
Explain why this creates a memory problem:
```python
big = "x" * 10_000_000   # 10M ASCII chars, ~10 MB
small = big + "😀"        # Forces 4BYTE_KIND: 10,000,001 × 4 = ~40 MB!
del big                    # Frees 10 MB
# But 'small' still uses 40 MB — the emoji "cost" 30 MB!
```
**Solution**: If you need the emoji alongside ASCII text, keep them as separate strings and only combine when absolutely necessary (e.g., for display).
