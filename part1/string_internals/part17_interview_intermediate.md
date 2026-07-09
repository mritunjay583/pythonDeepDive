# Part 17 — Interview Questions: Intermediate (50)

**Q1**: What are the three internal string kinds in CPython? **A**: 1BYTE_KIND (uint8, Latin-1/ASCII), 2BYTE_KIND (uint16, BMP), 4BYTE_KIND (uint32, full Unicode). Chosen per-string by maximum code point.

**Q2**: What is PEP 393? **A**: Flexible String Representation (Python 3.3). Eliminated narrow/wide builds. Each string uses the narrowest fixed-width encoding for its max code point.

**Q3**: Why doesn't CPython use UTF-8 internally? **A**: Variable-width → O(n) indexing. Python guarantees O(1) `s[i]`, requiring fixed-width per string.

**Q4**: What is the memory difference between PyASCIIObject and PyCompactUnicodeObject? **A**: PyASCIIObject = 48 bytes (no utf8 cache). PyCompactUnicodeObject = 64 bytes (adds utf8 + utf8_length fields). ASCII strings don't need UTF-8 cache because ASCII IS UTF-8.

**Q5**: How does hash caching work for strings? **A**: `hash` field = -1 initially. On first hash() call, SipHash-1-3 computed over character data, result stored permanently. Subsequent calls return cached value in O(1).

**Q6**: What is SipHash and why is it used? **A**: A keyed (randomized) hash function resistant to collision attacks. 128-bit key generated at process start from OS entropy. Prevents HashDoS.

**Q7**: How does the single-character cache work? **A**: All 128 ASCII single-char strings are pre-allocated at startup as immortal singletons. Characters 128-255 are cached lazily. `chr(65)` and `"A"` and `s[i]` all return the same cached object.

**Q8**: What happens when you concatenate ASCII + emoji strings? **A**: Result is 4BYTE_KIND. ALL characters (including ASCII) stored as 4 bytes each. The emoji forces widening of the entire result.

**Q9**: Can slicing produce a narrower kind? **A**: Yes. CPython scans the slice to determine its own max code point. `"Hello😀"[0:5]` → "Hello" with kind=1 (ASCII), not kind=4.

**Q10**: What is the UTF-8 cache in PyCompactUnicodeObject? **A**: `utf8` pointer + `utf8_length` field. Lazily populated on first .encode('utf-8') or C API UTF-8 request. Persists for string's lifetime.

**Q11**: How does CPython's str.find() work internally? **A**: FASTSEARCH algorithm: Boyer-Moore-Horspool variant with bloom filter for character rejection. Average O(n/m), worst O(nm).

**Q12**: What is the STRINGLIB template pattern? **A**: C preprocessor trick: include the same algorithm file with STRINGLIB_CHAR defined as Py_UCS1/2/4. Generates 3 width-specialized versions. Eliminates per-char kind branching.

**Q13**: What is the refcnt==1 optimization for +=? **A**: If a string has refcount 1, CPython tries realloc to extend in place. Avoids creating a new object. Unreliable — fails if refcount > 1, interned, or realloc can't extend.

**Q14**: Why does `sys.getsizeof("😀")` return more than `sys.getsizeof("a")`? **A**: "a" uses PyASCIIObject (48B header) + 2B data = 50B. "😀" uses PyCompactUnicodeObject (64B header) + 8B data (4B char + 4B null) = 72B.

**Q15**: What does `state.interned` encode? **A**: 2-bit field: 0=not interned, 1=mortal (can be freed), 2=immortal (permanent). Controls whether string is in the intern table.

**Q16**: Why are single-char ASCII strings immortal? **A**: They're used so frequently (indexing any ASCII string returns them) that tracking refcounts would be wasteful. Immortal = never freed, no refcount modification needed.

**Q17**: How does str.join() achieve O(total_length)? **A**: Phase 1: iterate to count total length + determine max kind. Phase 2: single allocation. Phase 3: copy all items + separators. One allocation, two passes.

**Q18**: What is `unicodedata.normalize()` for? **A**: Converts strings to canonical form. NFC (compose), NFD (decompose), NFKC, NFKD. Required for correct comparison of strings with combining characters.

**Q19**: Why is `"café" == "cafe\u0301"` False? **A**: Different code point sequences. Precomposed é (U+00E9) ≠ decomposed e+combining acute (U+0065+U+0301). Normalize both before comparing.

**Q20**: What does `state.ascii` control? **A**: If 1: string uses PyASCIIObject (smaller struct), data starts at offset 48, no UTF-8 cache needed. If 0: uses PyCompactUnicodeObject (larger), data at offset 64, has UTF-8 cache fields.

**Q21**: How does memcmp optimization work for string comparison? **A**: When both strings have the same kind, raw byte comparison (memcmp) gives correct code-point ordering. Uses SIMD on modern CPUs (16-64 bytes compared per cycle).

**Q22**: What is the `wstr` field and why is it deprecated? **A**: Legacy wchar_t* representation for the old C API (PyUnicode_AS_UNICODE). Being removed. NULL in 3.12+.

**Q23**: How does BUILD_STRING work for f-strings? **A**: Sum lengths + determine max kind across all parts. Single allocation. Sequential copy. Same efficiency as join() but without creating a list.

**Q24**: What is the `surrogateescape` error handler? **A**: Maps undecoded bytes to surrogate code points (U+DC80-U+DCFF). Allows lossless round-trip for filenames with invalid encodings.

**Q25**: How does the intern table interact with GC? **A**: Mortal interned strings can be removed from the table if only the table itself references them. The table is a regular dict. Cleanup happens during interpreter shutdown.

**Q26**: What is constant folding for strings? **A**: Compiler pre-computes constant expressions at compile time: `"hel" + "lo"` → `"hello"`. Limited to results ≤ 4096 chars.

**Q27**: How does `str.encode('ascii')` handle non-ASCII characters? **A**: Depends on error handler: 'strict' (default) raises UnicodeEncodeError. 'ignore' skips them. 'replace' uses '?'. 'xmlcharrefreplace' uses &#NNN;.

**Q28**: Why doesn't str support the buffer protocol? **A**: Internal representation (kind) is an implementation detail. Exposing raw bytes would leak it. Also: writable buffer would violate immutability.

**Q29**: How does CPython optimize `s == t` for interned strings? **A**: If both are interned (same value → same object), `ep_key == key` (pointer comparison) succeeds immediately. O(1) without character comparison.

**Q30**: What is the null terminator used for in string data? **A**: C API compatibility. Many C functions expect null-terminated strings. The null width matches the kind (1/2/4 bytes).

**Q31-50**: *(Cover: grapheme clusters and len(), Unicode categories, case folding edge cases, str.translate() with dict mapping, str.format_map(), template strings, codec registry, custom codecs, string subclassing, __format__ protocol, PEP 3131 identifiers, PEP 461 % for bytes, locale-aware operations, memory pools and string allocation, the free-list for short strings if any, PyUnicode_FromFormat for C sprintf-like, string iteration protocol, reversed() on strings, string comparison and locale.)*
