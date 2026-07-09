# CPython List Internals — Complete Reference

A production-quality deep dive into CPython's list implementation, covering everything from first principles to advanced internals.

## Table of Contents

| # | File | Topic |
|---|------|-------|
| 1 | [part1_why_lists_exist.md](part1_why_lists_exist.md) | Arrays vs Linked Lists, why Python chose dynamic arrays, design goals |
| 2 | [part2_pylistobject.md](part2_pylistobject.md) | The C struct, every field explained, memory layout |
| 3 | [part3_memory_layout.md](part3_memory_layout.md) | How `[10,20,30]` is stored, pointer indirection, nested lists |
| 4 | [part4_dynamic_array.md](part4_dynamic_array.md) | Capacity vs length, growth, why append is O(1), why insert is O(n) |
| 5 | [part5_overallocation_algorithm.md](part5_overallocation_algorithm.md) | The exact resizing formula, growth sequence, mathematical analysis |
| 6 | [part6_allocation.md](part6_allocation.md) | PyMalloc, pools, arenas, how lists get memory, free list |
| 7 | [part7_time_complexity.md](part7_time_complexity.md) | Derived complexity for every list operation with proofs |
| 8 | [part8_slicing_internals.md](part8_slicing_internals.md) | Copy vs view, slice assignment, performance |
| 9 | [part9_copying.md](part9_copying.md) | Assignment, .copy(), deepcopy, aliasing, memory diagrams |
| 10 | [part10_sorting_timsort.md](part10_sorting_timsort.md) | TimSort: runs, galloping, merging, stability, complexity |
| 11 | [part11_list_comprehensions.md](part11_list_comprehensions.md) | Bytecode, LIST_APPEND, performance vs loops |
| 12 | [part12_production_topics.md](part12_production_topics.md) | Large lists, fragmentation, cache locality, profiling |
| 13 | [part13_cpython_source_tour.md](part13_cpython_source_tour.md) | Key C functions: PyList_New, list_resize, PyList_Append, etc. |
| 14 | [part14_interview_questions.md](part14_interview_questions.md) | 150 questions: 50 beginner, 50 intermediate, 50 senior |
| 15a | [part15a_coding_questions.md](part15a_coding_questions.md) | Output prediction questions 1-50 |
| 15b | [part15b_coding_questions.md](part15b_coding_questions.md) | Output prediction questions 51-100 |
| 16 | [part16_exercises.md](part16_exercises.md) | Memory diagrams, pointer tracing, capacity calculations |

## Prerequisites

This material assumes you already understand:
- ✅ Python Object Model
- ✅ PyObject & PyVarObject
- ✅ Reference Counting
- ✅ Garbage Collection
- ✅ PyMalloc (Blocks, Pools, Arenas)
- ✅ Identity vs Mutability

## Key Source Files in CPython

```
Include/cpython/listobject.h  → PyListObject struct
Include/listobject.h          → Public C API
Objects/listobject.c          → All implementation (~3200 lines)
Objects/listsort.txt          → Tim Peters' TimSort description
```

## Quick Reference

```
PyListObject (64-bit):
┌──────────────────────────────┐
│ ob_refcnt   (8 bytes)        │
│ ob_type     (8 bytes) → PyList_Type
│ ob_size     (8 bytes) = len()│
│ ob_item     (8 bytes) → pointer array
│ allocated   (8 bytes) = capacity
└──────────────────────────────┘
Total struct: 40 bytes (+GC header = ~56-64 bytes)

Growth pattern: 0, 4, 8, 16, 24, 32, 40, 52, 64, 76, 92, ...
Formula: (newsize + newsize/8 + 6) & ~3
```
