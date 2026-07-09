# CPython String Internals — Advanced Systems Programming Reference

A deep systems-level document explaining every implementation detail behind Python's string type, from the Unicode standard through PyUnicodeObject's memory layout to production-critical performance characteristics.

## Table of Contents

| # | File | Topic |
|---|------|-------|
| 1 | [part1_unicode_history.md](part1_unicode_history.md) | ASCII → codepages → Unicode, code points, encoding schemes |
| 2 | [part2_encoding_deep_dive.md](part2_encoding_deep_dive.md) | UTF-8/16/32 bit patterns, surrogates, BOM, byte order |
| 3 | [part3_graphemes_and_normalization.md](part3_graphemes_and_normalization.md) | Grapheme clusters, NFC/NFD/NFKC/NFKD, combining characters |
| 4 | [part4_pep393_design.md](part4_pep393_design.md) | Why PEP 393, narrow vs wide builds, the flexible representation |
| 5 | [part5_pyunicodeobject_struct.md](part5_pyunicodeobject_struct.md) | Every field of PyASCIIObject/PyCompactUnicodeObject/PyUnicodeObject |
| 6 | [part6_memory_layout_diagrams.md](part6_memory_layout_diagrams.md) | Byte-level ASCII diagrams for all string kinds |
| 7 | [part7_kind_system.md](part7_kind_system.md) | 1BYTE/2BYTE/4BYTE kinds, kind promotion, Latin-1 vs ASCII |
| 8 | [part8_string_creation.md](part8_string_creation.md) | PyUnicode_New, _PyUnicode_Ready, creation from C/Python |
| 9 | [part9_interning_deep_dive.md](part9_interning_deep_dive.md) | Intern table, compile-time interning, runtime interning, mortal vs immortal |
| 10 | [part10_immutability_and_hashing.md](part10_immutability_and_hashing.md) | Why immutable, hash caching, SipHash internals, dict optimization |
| 11 | [part11_string_operations.md](part11_string_operations.md) | C-level implementation of concat, join, split, replace, find |
| 12 | [part12_concatenation_internals.md](part12_concatenation_internals.md) | Why += is O(n²), the refcnt=1 optimization, BUILD_STRING |
| 13 | [part13_encoding_decoding.md](part13_encoding_decoding.md) | .encode()/.decode(), codec registry, error handlers |
| 14 | [part14_cpython_source_tour.md](part14_cpython_source_tour.md) | Objects/unicodeobject.c walkthrough, key functions, macros |
| 15 | [part15_performance_production.md](part15_performance_production.md) | Large text, memory profiling, cache locality, optimization |
| 16 | [part16_interview_beginner.md](part16_interview_beginner.md) | 50 beginner questions with detailed answers |
| 17 | [part17_interview_intermediate.md](part17_interview_intermediate.md) | 50 intermediate questions with detailed answers |
| 18 | [part18_interview_senior.md](part18_interview_senior.md) | 50 senior questions with detailed answers |
| 19 | [part19_coding_questions_a.md](part19_coding_questions_a.md) | Output prediction questions 1-50 |
| 20 | [part20_coding_questions_b.md](part20_coding_questions_b.md) | Output prediction questions 51-100 |
| 21 | [part21_exercises.md](part21_exercises.md) | Memory tracing, implementation exercises |

## Prerequisites

- ✅ Python Object Model (PyObject, PyVarObject)
- ✅ Reference Counting & Garbage Collection
- ✅ PyMalloc (Blocks, Pools, Arenas)
- ✅ Lists & Dicts internals

## Key Source Files

```
Include/cpython/unicodeobject.h   → struct definitions (PyASCIIObject, PyCompactUnicodeObject)
Include/unicodeobject.h           → public C API (~200 functions)
Objects/unicodeobject.c           → implementation (~16,000 lines)
Objects/unicodectype.c            → character classification
Python/codecs.c                   → codec registry
Lib/codecs.py                     → Python codec layer
Objects/clinic/unicodeobject.c.h  → argument clinic generated code
```

## Quick Reference

```
╔══════════════════════════════════════════════════════════════════════╗
║                     STRING REPRESENTATION (PEP 393)                  ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Kind          Bytes/Char   Range              C Type               ║
║  ─────────────────────────────────────────────────────────────────  ║
║  1BYTE_KIND    1            U+0000 - U+00FF    Py_UCS1 (uint8_t)   ║
║    └─ ASCII    1            U+0000 - U+007F    (state.ascii=1)     ║
║    └─ Latin-1  1            U+0080 - U+00FF    (state.ascii=0)     ║
║  2BYTE_KIND    2            U+0100 - U+FFFF    Py_UCS2 (uint16_t)  ║
║  4BYTE_KIND    4            U+10000 - U+10FFFF Py_UCS4 (uint32_t)  ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Struct Hierarchy:                                                   ║
║                                                                      ║
║  PyASCIIObject           (for pure ASCII, state.ascii=1)            ║
║    ├─ ob_refcnt                                                      ║
║    ├─ ob_type                                                        ║
║    ├─ length             (code point count)                          ║
║    ├─ hash               (-1 = not computed, cached after first)    ║
║    ├─ state              (kind, compact, ascii, interned, ready)    ║
║    ├─ wstr               (deprecated, NULL in 3.12+)                ║
║    └─ [inline data]      (chars follow struct immediately)          ║
║                                                                      ║
║  PyCompactUnicodeObject  (for non-ASCII compact, state.ascii=0)    ║
║    ├─ (all of PyASCIIObject)                                        ║
║    ├─ utf8_length        (cached UTF-8 byte length)                 ║
║    ├─ utf8               (cached UTF-8 bytes, NULL if not cached)   ║
║    └─ [inline data]      (chars follow struct immediately)          ║
║                                                                      ║
║  PyUnicodeObject         (legacy non-compact, deprecated)           ║
║    ├─ (all of PyCompactUnicodeObject)                               ║
║    └─ data               (pointer to EXTERNAL character buffer)     ║
║                                                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Memory Formulas (64-bit):                                           ║
║    ASCII:    49 + n + 1 bytes (n = length)                          ║
║    Latin-1:  73 + n + 1 bytes                                       ║
║    UCS-2:    73 + 2n + 2 bytes                                      ║
║    UCS-4:    73 + 4n + 4 bytes                                      ║
║                                                                      ║
║  Interning:                                                          ║
║    Auto-interned: identifiers, single ASCII chars, ""               ║
║    Manual: sys.intern(s)                                             ║
║    States: NOT_INTERNED(0), MORTAL(1), IMMORTAL(2)                  ║
║                                                                      ║
║  Hashing:                                                            ║
║    Algorithm: SipHash-1-3 (keyed, randomized per process)           ║
║    Cached: hash field = -1 initially, computed on first hash()      ║
║    Cost: O(n) first time, O(1) thereafter                           ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```
