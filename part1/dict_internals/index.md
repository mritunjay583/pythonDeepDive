# CPython Dictionary & Set Internals — Complete Reference

A production-quality deep dive into CPython's dictionary and set implementation, from hash table fundamentals to the compact ordered dict introduced in Python 3.6+.

## Table of Contents

| # | File | Topic |
|---|------|-------|
| 1 | [part1_hash_tables.md](part1_hash_tables.md) | Why arrays/linked lists fail, hash tables, load factor, buckets, collisions |
| 2 | [part2_hash_functions.md](part2_hash_functions.md) | hash(), SipHash, security, hash randomization, collision attacks |
| 3 | [part3_pydictobject.md](part3_pydictobject.md) | The C struct, every field, combined/split tables, key-sharing |
| 4 | [part4_lookup_algorithm.md](part4_lookup_algorithm.md) | Probe sequence, open addressing, perturb, dummy markers, O(1) proof |
| 5 | [part5_insert_delete_resize.md](part5_insert_delete_resize.md) | Insertion, deletion, growth/shrink strategy, memory diagrams |
| 6 | [part6_compact_ordered_dict.md](part6_compact_ordered_dict.md) | Python 3.6+ compact layout, insertion ordering, historical evolution |
| 7 | [part7_sets.md](part7_sets.md) | How sets reuse dict concepts, membership, union, intersection, difference |
| 8 | [part8_hashability.md](part8_hashability.md) | Why immutables are hashable, __hash__, __eq__, custom objects, frozen |
| 9 | [part9_cpython_source_tour.md](part9_cpython_source_tour.md) | Objects/dictobject.c, key functions, source walkthrough |
| 10 | [part10_performance.md](part10_performance.md) | Cache locality, large dicts, millions of keys, production tuning |
| 11 | [part11_interview_questions.md](part11_interview_questions.md) | 50 beginner, 50 intermediate, 50 senior with answers |
| 12 | [part12_coding_questions.md](part12_coding_questions.md) | 100 output prediction questions |
| 13 | [part13_exercises.md](part13_exercises.md) | Memory diagrams, hash calculations, probe tracing exercises |

## Prerequisites

- ✅ Python Object Model (PyObject, PyVarObject)
- ✅ Reference Counting & Garbage Collection
- ✅ PyMalloc (Blocks, Pools, Arenas)
- ✅ Lists Internals (dynamic arrays, overallocation)

## Key Source Files in CPython

```
Include/cpython/dictobject.h   → PyDictObject struct
Include/dictobject.h           → Public C API
Objects/dictobject.c           → All dict implementation (~5000+ lines)
Objects/setobject.c            → Set implementation
Objects/dictnotes.txt          → Design notes by Tim Peters & Raymond Hettinger
Python/pyhash.c                → Hash function implementations
```

## Quick Reference

```
Modern CPython Dict (3.6+):
┌────────────────────────────────────────────┐
│ PyDictObject                               │
│   ma_used     = number of active entries   │
│   ma_version  = version tag (PEP 509)     │
│   ma_keys     → PyDictKeysObject          │
│   ma_values   → values array (split only) │
└────────────────────────────────────────────┘

PyDictKeysObject:
┌────────────────────────────────────────────┐
│   dk_refcnt   = sharing count             │
│   dk_log2_size = log2(hash table size)    │
│   dk_nentries = next index in entries     │
│   dk_indices  = [compact hash table]      │  ← sparse
│   dk_entries  = [key, value, hash] array  │  ← dense
└────────────────────────────────────────────┘

Load factor: 2/3 (resize when 66% full)
Probe: open addressing with perturbation
Hash: SipHash-1-3 (keyed, randomized per process)
```
