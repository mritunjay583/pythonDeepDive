# CPython Iterators, Generators & Lazy Evaluation — Complete Reference

An advanced systems-programming document covering the complete iteration subsystem in CPython: from the iterator protocol through generator internals, lazy evaluation, itertools, async iteration, and production streaming patterns.

## Table of Contents

| # | File | Topic |
|---|------|-------|
| 1 | [part1_why_iteration_exists.md](part1_why_iteration_exists.md) | Evolution from array indexing to generalized iteration |
| 2 | [part2_iterable_vs_iterator.md](part2_iterable_vs_iterator.md) | __iter__, __next__, StopIteration, the two protocols |
| 3 | [part3_iterator_protocol.md](part3_iterator_protocol.md) | Complete protocol spec, iter()/next(), protocol enforcement |
| 4 | [part4_for_loop_internals.md](part4_for_loop_internals.md) | for desugaring → bytecode → ceval.c GET_ITER/FOR_ITER |
| 5 | [part5_builtin_iterables.md](part5_builtin_iterables.md) | How list, dict, set, str, range, file create iterators |
| 6 | [part6_iterator_objects.md](part6_iterator_objects.md) | C structs: PyListIterObject, PyDictIterObject, PyRangeIterObject |
| 7 | [part7_generator_functions.md](part7_generator_functions.md) | yield, generator creation, suspension, resumption, state machine |
| 8 | [part8_generator_internals.md](part8_generator_internals.md) | PyGenObject, frame preservation, instruction pointer, send/throw |
| 9 | [part9_generator_expressions.md](part9_generator_expressions.md) | Genexps vs comprehensions, memory, lazy evaluation |
| 10 | [part10_lazy_evaluation.md](part10_lazy_evaluation.md) | Infinite sequences, pipelines, map/filter/zip/enumerate |
| 11 | [part11_itertools.md](part11_itertools.md) | count, cycle, chain, islice, tee, groupby, product, accumulate |
| 12 | [part12_custom_iterators.md](part12_custom_iterators.md) | Building iterator classes, common mistakes, production patterns |
| 13 | [part13_async_iteration.md](part13_async_iteration.md) | __aiter__, __anext__, async for, async generators, streaming |
| 14 | [part14_cpython_source_tour.md](part14_cpython_source_tour.md) | iterobject.c, genobject.c, ceval.c iteration paths |
| 15 | [part15_bytecode.md](part15_bytecode.md) | GET_ITER, FOR_ITER, YIELD_VALUE, SEND, RETURN_GENERATOR |
| 16 | [part16_performance.md](part16_performance.md) | Iterator allocation, generator overhead, lazy vs eager, caching |
| 17 | [part17_production_systems.md](part17_production_systems.md) | FastAPI streaming, Django ORM, pandas, Kafka, LLM tokens |
| 18 | [part18_common_mistakes.md](part18_common_mistakes.md) | Exhaustion, reuse, infinite loops, tee costs, mutation during iter |
| 19 | [part19_interview_beginner.md](part19_interview_beginner.md) | 50 beginner questions |
| 20 | [part20_interview_intermediate.md](part20_interview_intermediate.md) | 50 intermediate questions |
| 21 | [part21_interview_senior.md](part21_interview_senior.md) | 50 senior questions |
| 22 | [part22_coding_problems_a.md](part22_coding_problems_a.md) | Coding problems 1-50 |
| 23 | [part23_coding_problems_b.md](part23_coding_problems_b.md) | Coding problems 51-100 |
| 24 | [part24_exercises.md](part24_exercises.md) | Memory tracing, state tracing, implementation exercises |

## Prerequisites

- ✅ Python Object Model (PyObject, PyVarObject)
- ✅ Reference Counting & GC
- ✅ Lists, Dicts, Strings internals
- ✅ Functions, Closures, Decorators
- ✅ Bytecode & ceval.c fundamentals

## Key Source Files

```
Objects/iterobject.c        → Generic iterator (PySeqIterObject)
Objects/genobject.c         → Generator/coroutine/async generator objects
Objects/listobject.c        → PyListIterObject (list iterator)
Objects/dictobject.c        → Dict iterators (keys/values/items)
Objects/rangeobject.c       → Range iterator
Objects/tupleobject.c       → Tuple iterator
Objects/setobject.c         → Set iterator
Objects/unicodeobject.c     → String iterator
Objects/fileobject.c        → File line iterator
Python/ceval.c              → GET_ITER, FOR_ITER, YIELD_VALUE execution
Modules/itertoolsmodule.c   → itertools C implementations
Include/cpython/genobject.h → PyGenObject struct
```

## Key PEPs

```
PEP 234  — Iterators (Python 2.1)
PEP 255  — Simple Generators (Python 2.2)
PEP 289  — Generator Expressions (Python 2.4)
PEP 342  — Coroutines via Enhanced Generators (Python 2.5)
PEP 380  — Syntax for Delegating to a Subgenerator: yield from (Python 3.3)
PEP 492  — Coroutines with async and await syntax (Python 3.5)
PEP 525  — Asynchronous Generators (Python 3.6)
PEP 530  — Asynchronous Comprehensions (Python 3.6)
```

## Quick Reference

```
╔══════════════════════════════════════════════════════════════════════════╗
║                    ITERATION MODEL                                       ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  ITERABLE: object with __iter__() → returns an iterator                  ║
║    Examples: list, dict, set, str, range, file, generator                ║
║                                                                          ║
║  ITERATOR: object with __iter__() + __next__()                           ║
║    __iter__() returns self (iterators are their own iterables)            ║
║    __next__() returns next value or raises StopIteration                 ║
║                                                                          ║
║  for x in iterable:       # SUGAR FOR:                                   ║
║      process(x)           _iter = iter(iterable)  # calls __iter__       ║
║                           while True:                                    ║
║                               try:                                       ║
║                                   x = next(_iter)  # calls __next__      ║
║                               except StopIteration:                      ║
║                                   break                                  ║
║                               process(x)                                 ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  GENERATOR FUNCTION:                                                     ║
║    def gen():                                                            ║
║        yield 1      # Suspends frame, returns 1                          ║
║        yield 2      # On resume, continues here                          ║
║        yield 3      # Frame preserved between yields                     ║
║                     # StopIteration raised when function returns          ║
║                                                                          ║
║  GENERATOR OBJECT (PyGenObject):                                         ║
║    ├── gi_frame      → suspended frame (instruction pointer + locals)    ║
║    ├── gi_code       → code object                                       ║
║    ├── gi_running    → True while executing                              ║
║    └── gi_yieldfrom  → delegated sub-iterator (yield from)               ║
║                                                                          ║
║  LAZY PIPELINE:                                                          ║
║    # No intermediate lists created!                                      ║
║    result = sum(x**2 for x in range(1000000) if x % 2 == 0)            ║
║    # Each value: range→filter→transform→sum, one at a time              ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  BYTECODE:                                                               ║
║    GET_ITER      → calls iter(TOS), pushes iterator                      ║
║    FOR_ITER      → calls next(TOS_iter), pushes value or jumps           ║
║    YIELD_VALUE   → suspends generator, returns value to caller           ║
║    SEND          → resumes generator with a value (gen.send(v))          ║
║    RETURN_GENERATOR → creates generator object from frame                ║
║                                                                          ║
║  PERFORMANCE:                                                            ║
║    Iterator object: ~48-64 bytes (header + state)                        ║
║    Generator object: ~112 bytes + frame                                  ║
║    list(range(1M)): ~8 MB (materialized)                                 ║
║    range(1M): ~48 bytes (lazy, O(1) memory!)                             ║
║    sum(gen): O(1) memory regardless of sequence length                   ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
```
