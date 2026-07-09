# CPython Copying Internals — Complete Reference

A production-quality deep dive into Python's copying semantics — from assignment (no copy) to shallow copy to deep copy — covering the `copy` module internals, reference sharing, object graphs, and production implications.

## Table of Contents

| # | File | Topic |
|---|------|-------|
| 1 | [part1_why_copying_matters.md](part1_why_copying_matters.md) | Reference semantics, aliasing, why copying is non-trivial |
| 2 | [part2_assignment_is_not_copy.md](part2_assignment_is_not_copy.md) | Name binding, shared references, `b = a` semantics |
| 3 | [part3_shallow_copy.md](part3_shallow_copy.md) | .copy(), [:], list(), dict(), copy.copy() — what's shared |
| 4 | [part4_deep_copy.md](part4_deep_copy.md) | copy.deepcopy(), memo dict, recursion, cycle handling |
| 5 | [part5_copy_module_internals.md](part5_copy_module_internals.md) | CPython source: dispatch tables, __copy__, __deepcopy__ |
| 6 | [part6_object_graph_analysis.md](part6_object_graph_analysis.md) | Reference graphs, shared objects, nested containers |
| 7 | [part7_special_cases.md](part7_special_cases.md) | Immutables, singletons, classes, functions, files, modules |
| 8 | [part8_performance.md](part8_performance.md) | Cost analysis, when to copy, alternatives, memory impact |
| 9 | [part9_interview_questions.md](part9_interview_questions.md) | 50 beginner, 50 intermediate, 50 senior |
| 10 | [part10_coding_questions.md](part10_coding_questions.md) | 100 output prediction questions |
| 11 | [part11_exercises.md](part11_exercises.md) | Memory diagrams, graph tracing, refcount exercises |

## Prerequisites

- ✅ Python Object Model (PyObject, references, identity)
- ✅ Mutability vs Immutability
- ✅ Reference Counting
- ✅ Lists, Dicts, Sets internals (how containers store references)

## Key Source Files

```
Lib/copy.py              → copy.copy() and copy.deepcopy() implementation
Objects/listobject.c     → list.copy(), list slice copy
Objects/dictobject.c     → dict.copy()
Objects/setobject.c      → set.copy()
```

## Quick Reference

```
THE COPYING SPECTRUM:
═══════════════════════════════════════════════════════════════

Assignment (b = a):
  - NO new object created
  - b and a reference the SAME object
  - Mutations through either name affect both
  - Cost: O(1)

Shallow Copy (b = a.copy(), copy.copy(a)):
  - NEW container object created
  - Elements are SHARED (same references)
  - Mutating the container (add/remove) is independent
  - Mutating shared ELEMENTS affects both!
  - Cost: O(n) where n = number of top-level elements

Deep Copy (b = copy.deepcopy(a)):
  - NEW everything (recursively)
  - All mutable objects duplicated
  - Completely independent copy
  - Handles cycles via memo dict
  - Cost: O(N) where N = total objects in graph

═══════════════════════════════════════════════════════════════

DECISION GUIDE:
  Need another name for same object?     → assignment
  Need independent container, shared items? → shallow copy
  Need fully independent clone?           → deep copy
  Need read-only access?                  → don't copy at all
```
