# CPython PyObject & PyVarObject Internals — Complete Reference

A production-quality deep dive into the fundamental building blocks of every Python object in CPython — PyObject and PyVarObject. This covers the exact memory layout, design philosophy, and implementation of the object header system.

## Table of Contents

| # | File | Topic |
|---|------|-------|
| 1 | [part1_why_pyobject_exists.md](part1_why_pyobject_exists.md) | Why every object needs a common layout, design philosophy |
| 2 | [part2_pyobject.md](part2_pyobject.md) | The actual struct, ob_refcnt, ob_type, memory diagrams |
| 3 | [part3_object_header.md](part3_object_header.md) | Header, metadata, data separation, alignment, padding |
| 4 | [part4_type_objects.md](part4_type_objects.md) | PyTypeObject, dynamic dispatch, types-are-objects |
| 5 | [part5_reference_count.md](part5_reference_count.md) | ob_refcnt lifecycle, C-level updates, source code |
| 6 | [part6_object_identity.md](part6_object_identity.md) | id(), memory addresses, identity semantics |
| 7 | [part7_why_pyvarobject_exists.md](part7_why_pyvarobject_exists.md) | Limitations of PyObject, variable-size problem |
| 8 | [part8_pyvarobject.md](part8_pyvarobject.md) | The struct, ob_size, len() is O(1) |
| 9 | [part9_fixed_vs_variable.md](part9_fixed_vs_variable.md) | Classification of all Python object types |
| 10 | [part10_memory_layout_examples.md](part10_memory_layout_examples.md) | ASCII diagrams for int, str, list, dict, function, etc. |
| 11 | [part11_object_relationships.md](part11_object_relationships.md) | Reference graphs, aliasing, cycles, ownership |
| 12 | [part12_cpython_source_tour.md](part12_cpython_source_tour.md) | Include/object.h, macros, Py_INCREF/DECREF |
| 13 | [part13_memory_alignment.md](part13_memory_alignment.md) | CPU alignment, padding, cache lines, 32 vs 64 bit |
| 14 | [part14_object_allocation.md](part14_object_allocation.md) | Complete lifecycle from Python code to deallocation |
| 15 | [part15_performance.md](part15_performance.md) | Overhead, cache locality, small object optimization |
| 16 | [part16_macros_and_apis.md](part16_macros_and_apis.md) | PyObject_New, Py_INCREF, Py_DECREF, etc. |
| 17 | [part17_historical_evolution.md](part17_historical_evolution.md) | Changes across Python versions, 3.11/3.12 improvements |
| 18a | [part18_a_interview_beginner.md](part18_a_interview_beginner.md) | 50 beginner interview questions |
| 18b | [part18_b_interview_intermediate.md](part18_b_interview_intermediate.md) | 50 intermediate interview questions |
| 18c | [part18_c_interview_senior.md](part18_c_interview_senior.md) | 50 senior interview questions |
| 19a | [part19_a_exercises.md](part19_a_exercises.md) | Exercises 1-40: refcounts & object headers |
| 19b | [part19_b_exercises.md](part19_b_exercises.md) | Exercises 41-75: identity, graphs, PyVarObject |
| 20 | [part20_sources.md](part20_sources.md) | References: source code, PEPs, books |

## Prerequisites

- ✅ Python Object Model (variables, names, references)
- ✅ Identity, Mutability
- ✅ Reference Counting & Garbage Collection
- ✅ Python Process Memory (Heap, Stack)
- ✅ PyMalloc (Arena → Pool → Block)

## Key Source Files

```
Include/object.h          → PyObject, PyVarObject struct definitions
Include/cpython/object.h  → Internal details
Objects/object.c          → Object protocol implementation
Objects/typeobject.c      → Type object (PyTypeObject) implementation
Include/refcount.h        → Py_INCREF, Py_DECREF macros
```

## Quick Reference

```
PyObject (every Python object starts with this):
┌──────────────────────────────────┐
│ ob_refcnt   (Py_ssize_t, 8B)    │  ← reference count
│ ob_type     (PyTypeObject*, 8B)  │  ← pointer to type object
└──────────────────────────────────┘
Total: 16 bytes header on 64-bit

PyVarObject (variable-size objects add):
┌──────────────────────────────────┐
│ ob_refcnt   (Py_ssize_t, 8B)    │
│ ob_type     (PyTypeObject*, 8B)  │
│ ob_size     (Py_ssize_t, 8B)    │  ← number of items
└──────────────────────────────────┘
Total: 24 bytes header on 64-bit

Every Python object in memory:
[GC Header (optional)] [PyObject/PyVarObject Header] [Type-specific data]
```
