# Part 19 — Coding Questions: Output Prediction (1-50)

### Q1
```python
print(len("hello"))
print(len("café"))
print(len("😀"))
```
**Output**: `5`, `4`, `1` — len counts code points.

### Q2
```python
import sys
print(sys.getsizeof("") < sys.getsizeof("a") < sys.getsizeof("ab"))
```
**Output**: `True` — each character adds bytes (49 < 50 < 51 for ASCII).

### Q3
```python
a = "hello"
b = "hello"
print(a is b)
```
**Output**: `True` — identifier-like string, auto-interned.

### Q4
```python
a = "hello world"
b = "hello world"
print(a is b)
```
**Output**: Likely `True` in a script (same compilation unit). Implementation detail.

### Q5
```python
a = "hello"
b = "hell" + "o"
print(a is b)
```
**Output**: `True` — constant folding at compile time produces same interned object.

### Q6
```python
a = "hello"
c = "hell"
b = c + "o"
print(a is b)
```
**Output**: `False` — runtime concatenation, not interned.

### Q7
```python
import sys
print(sys.getsizeof("a"))
print(sys.getsizeof("é"))
print(sys.getsizeof("日"))
print(sys.getsizeof("😀"))
```
**Output**: `50`, `74`, `76`, `76` (approximately — ASCII vs Latin-1 vs UCS-2 vs UCS-4 struct sizes differ).

### Q8
```python
import sys
s = "a" * 100
t = "日" * 100
print(sys.getsizeof(s))
print(sys.getsizeof(t))
```
**Output**: ~`150`, ~`274` (ASCII: 49+101; UCS-2: 73+202).

### Q9
```python
s = "hello"
print(s[:] is s)
```
**Output**: `True` — full slice of immutable returns same object.

### Q10
```python
s = "Hello"
t = s.lower()
u = "hello"
print(t is u)
```
**Output**: Depends on implementation. Likely `False` (lower() creates new non-interned string unless special optimization).

### Q11
```python
print("hello"[0] is "hello"[0])
```
**Output**: `True` — both return the cached single-char 'h' singleton.

### Q12
```python
print(chr(97) is "a")
```
**Output**: `True` — chr(97) returns the cached single-char 'a'.

### Q13
```python
s = "café"
print(s[3])
print(ord(s[3]))
```
**Output**: `é`, `233` — s[3] is the character é (U+00E9 = 233).

### Q14
```python
print(len("👨‍👩‍👧‍👦"))
```
**Output**: `7` — 4 person emoji + 3 Zero Width Joiners = 7 code points.

### Q15
```python
print("🇺🇸"[0])
print(len("🇺🇸"))
```
**Output**: `🇺` (regional indicator U), `2` — flag is 2 code points.

### Q16
```python
s = "hello"
try:
    s[0] = 'H'
except TypeError:
    print("immutable!")
```
**Output**: `immutable!`

### Q17
```python
a = "test"
b = a
a += "!"
print(b)
print(a is b)
```
**Output**: `test`, `False` — += creates new string, rebinds a. b unchanged.

### Q18
```python
print(hash("hello") == hash("hello"))
```
**Output**: `True` — same value within same process.

### Q19
```python
print("café".encode('utf-8'))
print(len("café".encode('utf-8')))
```
**Output**: `b'caf\xc3\xa9'`, `5` — é encodes to 2 UTF-8 bytes.

### Q20
```python
print("café".encode('latin-1'))
print(len("café".encode('latin-1')))
```
**Output**: `b'caf\xe9'`, `4` — é = 0xE9 in Latin-1 (1 byte).

### Q21
```python
try:
    "café".encode('ascii')
except UnicodeEncodeError:
    print("can't encode!")
```
**Output**: `can't encode!` — é is not ASCII.

### Q22
```python
print("café".encode('ascii', errors='ignore'))
```
**Output**: `b'caf'` — é skipped.

### Q23
```python
print("café".encode('ascii', errors='replace'))
```
**Output**: `b'caf?'` — é replaced with ?.

### Q24
```python
s = "hello world"
print(s.split())
print(s.split('o'))
```
**Output**: `['hello', 'world']`, `['hell', ' w', 'rld']`

### Q25
```python
print("  hello  ".strip())
print("xxhelloxx".strip('x'))
```
**Output**: `hello`, `hello`

### Q26
```python
words = ["hello", "world", "python"]
print(" ".join(words))
print("".join(words))
```
**Output**: `hello world python`, `helloworldpython`

### Q27
```python
s = "hello"
print(s.find("ll"))
print(s.find("xx"))
print(s.index("ll"))
```
**Output**: `2`, `-1`, `2`

### Q28
```python
s = "hello"
try:
    s.index("xx")
except ValueError:
    print("not found!")
```
**Output**: `not found!`

### Q29
```python
s = "Hello World"
print(s.replace("o", "0"))
print(s.replace("l", "L", 1))
```
**Output**: `Hell0 W0rld`, `HeLlo World`

### Q30
```python
print("hello".startswith("hel"))
print("hello".endswith("llo"))
print("hello".startswith(("hi", "he")))
```
**Output**: `True`, `True`, `True` — tuple of prefixes allowed.

### Q31
```python
name = "Alice"
age = 30
print(f"{name} is {age}")
print("{} is {}".format(name, age))
print("%s is %d" % (name, age))
```
**Output**: All three produce `Alice is 30`.

### Q32
```python
print(f"{'hello':>10}")
print(f"{'hello':<10}")
print(f"{'hello':^10}")
```
**Output**: `     hello`, `hello     `, `  hello   `

### Q33
```python
print("abc" > "ABC")
print("abc" == "ABC")
```
**Output**: `True`, `False` — 'a'(97) > 'A'(65) in Unicode ordering.

### Q34
```python
s = "banana"
print(s.count("an"))
```
**Output**: `2` — non-overlapping: found at index 1 and index 3.

### Q35
```python
print("123".isdigit())
print("12.3".isdigit())
print("²".isdigit())
```
**Output**: `True`, `False`, `True` — ² (superscript 2) IS a Unicode digit!

### Q36
```python
print("hello".isascii())
print("café".isascii())
```
**Output**: `True`, `False`

### Q37
```python
s = "python"
print(s[::-1])
```
**Output**: `nohtyp`

### Q38
```python
print("hello"[1:100])
print("hello"[-100:3])
```
**Output**: `ello`, `hel` — slicing clamps to bounds, no IndexError.

### Q39
```python
import sys
s = sys.intern("hello world")
t = sys.intern("hello world")
print(s is t)
```
**Output**: `True` — both return the same interned object.

### Q40
```python
print("ß".upper())
print(len("ß"), len("ß".upper()))
```
**Output**: `SS`, `1 2` — German sharp s expands to 2 chars on upper()!

### Q41
```python
s1 = "\u00e9"       # precomposed é
s2 = "e\u0301"      # e + combining acute
print(s1 == s2)
print(len(s1), len(s2))
```
**Output**: `False`, `1 2` — different code point sequences!

### Q42
```python
import unicodedata
s1 = "\u00e9"
s2 = "e\u0301"
print(unicodedata.normalize('NFC', s1) == unicodedata.normalize('NFC', s2))
```
**Output**: `True` — NFC normalizes both to precomposed form.

### Q43
```python
print(ascii("café"))
```
**Output**: `'caf\\xe9'` — non-ASCII escaped.

### Q44
```python
print("hello" * 0)
print(type("hello" * 0))
```
**Output**: (empty string), `<class 'str'>`

### Q45
```python
s = "hello"
print(s.removeprefix("hel"))
print(s.removesuffix("llo"))
print(s.removeprefix("xyz"))
```
**Output**: `lo`, `he`, `hello` (3.9+; no match → returns original)

### Q46
```python
print(ord("€"))
print(hex(ord("€")))
```
**Output**: `8364`, `0x20ac`

### Q47
```python
print("\N{SNOWMAN}")
print(len("\N{SNOWMAN}"))
```
**Output**: `☃`, `1`

### Q48
```python
s = "Hello\x00World"
print(len(s))
print(s)
```
**Output**: `11`, `Hello` (followed by NUL then `World` — display may truncate at NUL depending on terminal).

### Q49
```python
print("abc" in "xabcx")
print("abc" in ["a", "b", "c"])
```
**Output**: `True` (substring), `False` (list membership — "abc" not an element)

### Q50
```python
s = "Hello, World!"
print(s.swapcase())
print(s.title())
print(s.capitalize())
```
**Output**: `hELLO, wORLD!`, `Hello, World!`, `Hello, world!`
