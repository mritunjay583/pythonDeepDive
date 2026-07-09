# Part 20 — Coding Questions: Output Prediction (51-100)

### Q51
```python
print("résumé".encode('ascii', errors='xmlcharrefreplace'))
```
**Output**: `b'r&#233;sum&#233;'`

### Q52
```python
print(b'\xc3\xa9'.decode('utf-8'))
print(b'\xe9'.decode('latin-1'))
```
**Output**: `é`, `é` — same character, different encodings.

### Q53
```python
print("hello".encode('utf-16'))
```
**Output**: `b'\xff\xfeh\x00e\x00l\x00l\x00o\x00'` (BOM + LE 2-byte chars)

### Q54
```python
s = "abc"
t = s.replace("x", "y")
print(s is t)
```
**Output**: `True` (likely) — nothing to replace, CPython may return same object.

### Q55
```python
import sys
a = "x" * 4096
b = "x" * 4097
print(sys.getsizeof(a) - sys.getsizeof(b))
```
**Output**: `-1` — each additional char adds exactly 1 byte for ASCII.

### Q56
```python
print("hello\tworld".expandtabs(4))
```
**Output**: `hello   world` (tab expands to reach next 4-col boundary: 3 spaces)

### Q57
```python
s = "one,two,,four"
print(s.split(','))
print(s.split(',', maxsplit=2))
```
**Output**: `['one', 'two', '', 'four']`, `['one', 'two', ',four']`

### Q58
```python
print("hello".partition("ll"))
print("hello".partition("xx"))
```
**Output**: `('he', 'll', 'o')`, `('hello', '', '')`

### Q59
```python
s = "hello"
print(s.center(3))
print(s.center(10, '-'))
```
**Output**: `hello` (already wider), `--hello---`

### Q60
```python
print("42".zfill(6))
print("-42".zfill(6))
print("hello".zfill(8))
```
**Output**: `000042`, `-00042`, `000hello`

### Q61
```python
s = "Hello World Hello Python"
print(s.count("Hello"))
print(s.replace("Hello", "Hi", 1))
```
**Output**: `2`, `Hi World Hello Python`

### Q62
```python
print("abc".translate(str.maketrans("abc", "xyz")))
```
**Output**: `xyz`

### Q63
```python
s = "hello"
print(s.ljust(10, '.'))
print(s.rjust(10, '.'))
```
**Output**: `hello.....`, `.....hello`

### Q64
```python
print("abc".isidentifier())
print("123".isidentifier())
print("_x".isidentifier())
print("class".isidentifier())
```
**Output**: `True`, `False`, `True`, `True` (keywords are valid identifiers)

### Q65
```python
import keyword
print(keyword.iskeyword("class"))
print("class".isidentifier() and not keyword.iskeyword("class"))
```
**Output**: `True`, `False`

### Q66
```python
s = "\u0041\u0042\u0043"
print(s)
print(len(s))
```
**Output**: `ABC`, `3` — Unicode escapes.

### Q67
```python
s = "\U0001F600"
print(s)
print(len(s))
```
**Output**: `😀`, `1` — 32-bit Unicode escape.

### Q68
```python
print("hello" + " " + "world")
print("hello" " " "world")
```
**Output**: Both `hello world` — second is implicit string literal concatenation (compile-time).

### Q69
```python
s = """line 1
line 2
line 3"""
print(s.splitlines())
print(len(s.splitlines()))
```
**Output**: `['line 1', 'line 2', 'line 3']`, `3`

### Q70
```python
s = "Hello, World!"
print(s[::2])
print(s[::-2])
```
**Output**: `Hlo ol!`, `!lo olH`

### Q71
```python
a = "hello"
b = "HELLO"
print(a == b)
print(a.lower() == b.lower())
print(a.casefold() == b.casefold())
```
**Output**: `False`, `True`, `True`

### Q72
```python
print("straße".casefold())
print("straße".lower())
```
**Output**: `strasse`, `straße` — casefold converts ß→ss, lower doesn't.

### Q73
```python
s = "the quick brown fox"
print(s.title())
```
**Output**: `The Quick Brown Fox`

### Q74
```python
print(f"{3.14159:.2f}")
print(f"{42:08d}")
print(f"{255:08b}")
```
**Output**: `3.14`, `00000042`, `11111111`

### Q75
```python
name = "World"
print(f"{name!r}")
print(f"{name!s}")
print(f"{name!a}")
```
**Output**: `'World'`, `World`, `'World'` — !r=repr, !s=str, !a=ascii

### Q76
```python
data = [1, 2, 3]
print(f"{data}")
print(f"{data!r}")
```
**Output**: `[1, 2, 3]`, `[1, 2, 3]` (same for lists — str and repr are same)

### Q77
```python
s = "abc"
print(list(s))
print(tuple(s))
```
**Output**: `['a', 'b', 'c']`, `('a', 'b', 'c')`

### Q78
```python
print("ab" < "abc")
print("abc" < "abd")
print("ABC" < "abc")
```
**Output**: `True`, `True`, `True` — lexicographic; shorter prefix < longer; 'A'(65) < 'a'(97).

### Q79
```python
s = "  hello  world  "
print(s.split())
print(s.split(' '))
```
**Output**: `['hello', 'world']`, `['', '', 'hello', '', 'world', '', '']`
(split() with no arg collapses whitespace; split(' ') splits on every single space)

### Q80
```python
print(''.join(reversed("hello")))
print("hello"[::-1])
```
**Output**: Both `olleh`.

### Q81
```python
print("hello".encode('utf-32'))
```
**Output**: `b'\xff\xfe\x00\x00h\x00\x00\x00e\x00\x00\x00l\x00\x00\x00l\x00\x00\x00o\x00\x00\x00'` (BOM + 4 bytes/char LE)

### Q82
```python
s = "one two three"
print(s.rsplit(maxsplit=1))
```
**Output**: `['one two', 'three']` — splits from the RIGHT.

### Q83
```python
print("hello\x00world".split('\x00'))
```
**Output**: `['hello', 'world']` — null byte is a valid separator.

### Q84
```python
print(str(None))
print(str(True))
print(str(42))
```
**Output**: `None`, `True`, `42` — str() calls __str__ on each.

### Q85
```python
s = "hello"
print(s * -1)
print(s * 0)
```
**Output**: (empty string), (empty string) — negative/zero repetition gives "".

### Q86
```python
s = "hello world"
print(s.index("world"))
print(s.rindex("l"))
```
**Output**: `6`, `9` — rindex searches from the right.

### Q87
```python
print("Hello".isupper())
print("HELLO".isupper())
print("Hello".istitle())
```
**Output**: `False`, `True`, `True`

### Q88
```python
s = f"{'test':{'>'}{10}}"
print(s)
```
**Output**: `      test` — nested format spec (Python 3.12+): right-align in width 10.

### Q89
```python
import sys
s1 = "hello"
s2 = "hello"
print(sys.getrefcount(s1))
```
**Output**: A large number (interned string referenced from multiple places + the function arg).

### Q90
```python
print("abc".encode('utf-8').decode('utf-8') == "abc")
print("abc".encode('utf-8').decode('latin-1') == "abc")
```
**Output**: `True`, `True` — ASCII bytes are valid in both encodings.

### Q91
```python
print("café".encode('utf-8').decode('latin-1'))
```
**Output**: `cafÃ©` — WRONG! UTF-8 bytes 0xC3 0xA9 decoded as Latin-1 → Ã (0xC3) + © (0xA9). Mojibake!

### Q92
```python
s = "hello"
print(id(s) == id("hello"))
```
**Output**: `True` — both reference the same interned object.

### Q93
```python
print("".join(["a", "b", "c"]))
print(",".join([]))
print(",".join(["only"]))
```
**Output**: `abc`, (empty string), `only`

### Q94
```python
s = "aAbBcC"
print(s.swapcase())
print(s.swapcase().swapcase() == s)
```
**Output**: `AaBbCc`, `True`

### Q95
```python
print("\t\n\r ".isspace())
print("".isspace())
print(" a ".isspace())
```
**Output**: `True`, `False` (empty!), `False`

### Q96
```python
print("hello".removeprefix("he"))
print("hello".removeprefix("he").removeprefix("l"))
```
**Output**: `llo`, `lo` (Python 3.9+)

### Q97
```python
x = 42
print(f"{x = }")
```
**Output**: `x = 42` (Python 3.8+ self-documenting expression)

### Q98
```python
import sys
print(sys.getsizeof("a" * 1000))
print(sys.getsizeof("😀" * 1000))
```
**Output**: ~`1050` (49+1001), ~`4077` (73+4004) — 4× difference due to kind!

### Q99
```python
s = "Hello"
print(s.lower() is s.lower())
```
**Output**: `False` — each call creates a new string object.

### Q100
```python
s = "hello"
t = s.upper()
u = t.lower()
print(u == s)
print(u is s)
```
**Output**: `True`, `False` — equal content, different objects.
