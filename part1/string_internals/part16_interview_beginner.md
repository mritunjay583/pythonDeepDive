# Part 16 — Interview Questions: Beginner (50)

**Q1**: Are Python strings mutable or immutable? **A**: Immutable. Characters cannot be changed after creation. Every "modification" creates a new string.

**Q2**: What does `len("hello")` return? **A**: 5 — the number of Unicode code points. NOT bytes.

**Q3**: What is `len("café")` and why? **A**: 4. Each character (including é = U+00E9) is one code point. len() counts code points.

**Q4**: What does `sys.getsizeof("hello")` return approximately? **A**: ~54 bytes (49-byte PyASCIIObject header + 5 chars + null terminator).

**Q5**: Why does `sys.getsizeof("a")` return ~50 bytes for a single character? **A**: Every string object carries a fixed header (ob_refcnt, ob_type, length, hash, state, wstr) of ~48 bytes, plus the character data.

**Q6**: Is `"hello" is "hello"` True? **A**: In CPython, typically yes (interned as an identifier-like constant). But this is an implementation detail — always use `==` for string comparison.

**Q7**: What does `.encode('utf-8')` do? **A**: Converts a str (code points) to bytes (UTF-8 byte sequence). Returns a bytes object.

**Q8**: What is the difference between str and bytes? **A**: str = sequence of Unicode code points (text). bytes = sequence of raw bytes (binary data). Convert between them with encode/decode.

**Q9**: Why is `"".join(list)` preferred over `+=` in a loop? **A**: join() allocates once and copies once (O(n)). += creates a new string each iteration (O(n²) without optimization).

**Q10**: What does `hash("hello")` return? **A**: An integer hash value. Same within one process run, different between runs (hash randomization).

**Q11**: Why does hash change between runs? **A**: Hash randomization (SipHash with random key) prevents HashDoS attacks.

**Q12**: What is string interning? **A**: Ensuring one canonical object per unique string value. `sys.intern()` does this explicitly; CPython auto-interns identifiers.

**Q13**: What does `ord('A')` return? **A**: 65 — the Unicode code point of 'A'.

**Q14**: What does `chr(65)` return? **A**: 'A' — the character with Unicode code point 65.

**Q15**: Can strings contain null bytes? **A**: Yes. `"\x00"` is a valid Python string of length 1.

**Q16**: What is a raw string `r"..."`? **A**: Backslashes aren't treated as escape characters. `r"\n"` is literal backslash + n, not newline.

**Q17**: What does `"hello"[1:3]` return? **A**: "el" — a new string (slice/copy, not a view).

**Q18**: Is `"hello"[0]` a character or a string? **A**: A string of length 1. Python has no separate char type.

**Q19**: What does `.split()` return? **A**: A list of strings, split by whitespace (default) or the specified separator.

**Q20**: What does `.strip()` do? **A**: Returns a new string with leading/trailing whitespace removed.

**Q21**: What is an f-string? **A**: Formatted string literal: `f"{expr}"`. Fastest formatting method. Compiled to direct bytecode.

**Q22**: What's the difference between `find()` and `index()`? **A**: find() returns -1 on failure; index() raises ValueError.

**Q23**: Is `"hello" + " " + "world"` efficient? **A**: For a small fixed number of parts: fine. For loops: no — use join(). F-string is best: `f"hello world"`.

**Q24**: What does `.upper()` return? **A**: A new string with all characters converted to uppercase.

**Q25**: Does `.upper()` modify the original? **A**: No. Strings are immutable. It returns a new string.

**Q26**: What is `"abc" * 3`? **A**: "abcabcabc" — string repetition. Creates a new string.

**Q27**: Can strings be dictionary keys? **A**: Yes. They're immutable and hashable. Most common dict key type.

**Q28**: What does `in` do for strings? **A**: Substring search: `"lo" in "hello"` → True. O(n) operation.

**Q29**: What is `str()` used for? **A**: Converts any object to its string representation by calling `__str__` (or `__repr__`).

**Q30**: What does `repr("hello\n")` show? **A**: `"'hello\\n'"` — the string with escape sequences visible.

**Q31**: Can you iterate over a string? **A**: Yes. `for c in "hello"` yields 'h', 'e', 'l', 'l', 'o'.

**Q32**: What type does iteration yield? **A**: str (length-1 strings). Not bytes, not ints.

**Q33**: What is `"hello".replace("l", "L")`? **A**: "heLLo" — replaces ALL occurrences.

**Q34**: What does `.startswith("hel")` check? **A**: Whether the string begins with "hel". O(3) — only checks prefix length.

**Q35**: Is `""` falsy? **A**: Yes. `bool("") == False`. Non-empty strings are truthy.

**Q36**: What encoding does Python 3 source code use? **A**: UTF-8 by default (PEP 3120). Can be changed with `# -*- coding: xxx -*-`.

**Q37**: What is `b"hello"`? **A**: A bytes literal — sequence of raw bytes (not Unicode code points).

**Q38**: Can you mix str and bytes with `+`? **A**: No. `"hello" + b"world"` raises TypeError. Must encode/decode explicitly.

**Q39**: What does `.count("l")` return for "hello"? **A**: 2 — counts non-overlapping occurrences.

**Q40**: What is `.join()` called on? **A**: The separator: `", ".join(["a", "b"])` → "a, b". Separator is "self".

**Q41**: What does `"hello".center(11, '*')` return? **A**: "***hello***" — padded to width 11 with *.

**Q42**: What is the maximum string length? **A**: Limited by sys.maxsize and available memory. Billions of characters in theory.

**Q43**: Does Python 3 support unicode identifiers? **A**: Yes. `café = 42` and `变量 = "value"` are valid variable names.

**Q44**: What normalization does Python use for identifiers? **A**: NFKC (PEP 3131). `café` (precomposed) and `café` (decomposed) are the same identifier.

**Q45**: What does `"hello".encode()` use by default? **A**: UTF-8. The default encoding for encode/decode.

**Q46**: What is `string.ascii_letters`? **A**: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ" from the string module.

**Q47**: How do you check if a string is all digits? **A**: `s.isdigit()` — but beware: includes Unicode digits like ² (superscript 2)!

**Q48**: How do you reverse a string? **A**: `s[::-1]`. No built-in reverse() for strings (they're immutable).

**Q49**: What does `"hello\nworld".splitlines()` return? **A**: `['hello', 'world']` — splits on various line endings.

**Q50**: What is `textwrap.dedent()` for? **A**: Removes common leading whitespace from multiline strings. Useful for docstrings.
