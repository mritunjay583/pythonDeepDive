# Part 18 — Interview Questions: Senior (50)

**Q1**: Explain the complete memory layout of "café" including byte offsets. **A**: PyCompactUnicodeObject(64B): refcnt(8)+type(8)+length=4(8)+hash=-1(8)+state{kind=1,ascii=0}(4)+pad(4)+wstr=NULL(8)+utf8_len=0(8)+utf8=NULL(8). Then inline data(5B): 0x63,0x61,0x66,0xE9,0x00. Total: 69 bytes.

**Q2**: How does _PyUnicode_FastCopyCharacters handle widening from 1BYTE to 4BYTE? **A**: Reads each Py_UCS1 byte, writes it as a Py_UCS4 (zero-extending: 0x48 → 0x00000048). Loop processes elements one at a time with correct source/dest pointers. Some implementations use SIMD widening instructions.

**Q3**: Explain the SipHash-1-3 algorithm at a high level for string hashing. **A**: Initialize 4×64-bit state from 128-bit key. Process message in 8-byte blocks: XOR block into state, run 1 SipRound (ARX: add-rotate-XOR on state variables). After all blocks: XOR length, run 3 finalization SipRounds. Return XOR of all 4 state words.

**Q4**: How does CPython's FASTSEARCH bloom filter work? **A**: A bitmask of 64 bits. Each character in the pattern sets bits (ch & 0x3F positions). During search, if a character at position i+m is NOT in the bloom filter, the entire pattern can skip past it. Eliminates many unnecessary comparisons.

**Q5**: Why does CPython scan the slice to determine kind during substring creation? **A**: A slice of a UCS-4 string may contain only ASCII characters. Scanning finds the actual max code point, allowing the substring to use 1BYTE_KIND. This costs O(k) scan time but saves memory (1 byte/char vs 4).

**Q6**: Explain how the intern table interacts with the dict used for `__dict__` in class instances. **A**: Attribute names are interned at class creation. Instance __dict__ uses interned keys. Dict lookup does pointer comparison first (O(1)). Because both lookup key and stored key are the same interned object, the fast path succeeds without character comparison.

**Q7**: What is the relationship between PyUnicode_AsUTF8() and the utf8 cache? **A**: PyUnicode_AsUTF8() returns a `const char*` to the UTF-8 form. For ASCII strings: returns the inline data directly (ASCII IS UTF-8). For non-ASCII: computes UTF-8 if not cached, stores in `utf8` field, returns cached pointer. The cached memory lives as long as the string.

**Q8**: How does CPython handle the case where `str.upper()` changes string length? **A**: Some characters expand: "ß".upper() → "SS" (1 char → 2 chars). upper() must first compute the result length (scanning + accounting for expansions), then allocate, then convert. Two passes over the input.

**Q9**: Explain the immortal string optimization in Python 3.12+. **A**: Strings like "", single ASCII chars, type names, builtin names have a special refcount value. Py_INCREF/Py_DECREF detect this and skip modification. Eliminates cache line bouncing when many threads access the same interned string.

**Q10**: How does the 3-way STRINGLIB template avoid code duplication while maintaining performance? **A**: The same .h file is #included 3 times with STRINGLIB_CHAR typedef'd to Py_UCS1, Py_UCS2, Py_UCS4. The compiler generates 3 specialized functions. At runtime, a switch selects the right one. No per-character branching in the hot loop.

**Q11**: What is the unicode_compare fast path for same-kind strings? **A**: If kind1 == kind2: memcmp(data1, data2, min_len * kind). memcmp uses SIMD (SSE/AVX). Comparing 16-64 bytes per cycle. Only if equal prefix: compare lengths. Orders of magnitude faster than char-by-char.

**Q12**: Explain how `s += t` can be O(1) amortized with the refcount optimization. **A**: If refcnt==1: try realloc. With typical allocators: overallocated blocks can often extend in place (free space after the block). If not: realloc moves + doubles the buffer. Amortized over n appends: total copies ~ 2n. But fragile — any second reference breaks it.

**Q13**: How does the compact representation save memory compared to the old 3.2 layout? **A**: Old: either UCS-2 everywhere (2 bytes even for ASCII) or UCS-4 everywhere (4 bytes). New: ASCII gets 1 byte/char. A million ASCII strings save 1-3 MB EACH vs the old wide builds.

**Q14**: What happens to the hash field during `pickle.dumps(s)` and `pickle.loads()`? **A**: pickle doesn't serialize the hash. After loads(), the new string has hash=-1 (uncomputed). First dict lookup/hash() call recomputes it. This is correct because hash is per-process (randomized).

**Q15**: How would removing the GIL (PEP 703) affect string operations? **A**: String immutability means reads are always safe without locks. But: refcount updates on string objects need atomic ops (or deferred counting). The hash cache write (first hash() call) needs atomic compare-and-swap. Interning table access needs synchronization.

**Q16-50**: *(Advanced topics: string creation from bytecode compiler, co_consts handling, code object string constants, relation between LOAD_CONST and interning, tp_hash slot for str, how str subclasses affect interning, PyUnicode_FromKindAndData internals, legacy wstr elimination timeline, _PyUnicode_Ready removal in 3.12, string GC behavior (not tracked), weak reference support for strings (none), comparison with Java's compact strings (Java 9), comparison with Rust's str/String, how io.TextIOWrapper uses encodings, incremental codecs, the codecs.StreamReader/Writer protocol, BOM handling in utf-8-sig, null byte handling in C API, PyUnicode_FromFormat for formatted C strings, string memory in sub-interpreters, per-interpreter intern tables.)*
