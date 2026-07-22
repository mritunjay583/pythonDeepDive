# CPython Generators Deep Dive — Complete Reference

An advanced systems-programming document covering every aspect of Python generators: from the initial PEP 255 motivation through PyGenObject internals, frame suspension mechanics, yield/send/throw/close protocols, coroutine evolution, async generators, and production streaming patterns.

## Table of Contents

| # | File | Topic |
|---|------|-------|
| 1 | [part1_why_generators_exist.md](part1_why_generators_exist.md) | Limitations of functions/iterators, PEP 255, historical context, language comparison |
| 2 | [part2_generator_fundamentals.md](part2_generator_fundamentals.md) | yield, generator function vs object, lazy execution, lifecycle, memory diagram |
| 3 | [part3_generator_creation.md](part3_generator_creation.md) | RETURN_GENERATOR opcode, _Py_MakeCoro, frame attachment, arg binding, refcounts |
| 4 | [part4_generator_execution.md](part4_generator_execution.md) | Complete step-by-step: first next(), resume, yield, exhaustion, operand stack trace |
| 5 | [part5_frame_suspension.md](part5_frame_suspension.md) | WHY generators can pause, heap vs stack, what's preserved, YIELD_VALUE C code |
| 6 | [part6_state_machine.md](part6_state_machine.md) | GEN_CREATED/RUNNING/SUSPENDED/CLOSED, transition diagram, gi_running guard |
| 9 | [part9_pygenobject.md](part9_pygenobject.md) | Complete C struct, every field, memory layout, PyGen_Type, GC interaction |
| 14 | [part14_coroutine_evolution.md](part14_coroutine_evolution.md) | PEP 255→342→380→479→492→525: complete evolution with code examples |
| 24 | [part24_historical_evolution.md](part24_historical_evolution.md) | 23-year timeline, problem each PEP solved, underlying mechanism |

### Cross-References (covered in iterators_and_generators module)

The following topics are covered deeply in `part1/iterators_and_generators/`:
- Part 7 (yield/yield from): see `iterators_and_generators/part7_generator_functions.md`
- Part 8 (send/throw/close): see `iterators_and_generators/part8_generator_internals.md`
- Part 10-11 (bytecode/source): see `iterators_and_generators/part14_cpython_source_tour.md`, `part15_bytecode.md`
- Part 12-13 (vs iterators, genexps): see `iterators_and_generators/part9_generator_expressions.md`, `part12_custom_iterators.md`
- Part 15 (async generators): see `iterators_and_generators/part13_async_iteration.md`
- Part 16-17 (production/perf): see `iterators_and_generators/part16_performance.md`, `part17_production_systems.md`
- Part 18 (mistakes): see `iterators_and_generators/part18_common_mistakes.md`
- Part 19-23 (interview/exercises): see `iterators_and_generators/part19-24`

## Prerequisites

- ✅ Python Object Model (PyObject, PyVarObject)
- ✅ Functions, Closures, Decorators
- ✅ Iterator Protocol (__iter__, __next__, StopIteration)
- ✅ Bytecode & ceval.c fundamentals
- ✅ Frame objects

## Key Source Files

```
Objects/genobject.c           → PyGenObject, PyCoroObject, PyAsyncGenObject
Include/cpython/genobject.h   → Generator struct definitions
Python/ceval.c                → YIELD_VALUE, SEND, RETURN_GENERATOR execution
Python/bytecodes.c            → Opcode definitions (3.12+)
Objects/frameobject.c         → Frame suspension/resumption support
Include/internal/pycore_frame.h → _PyInterpreterFrame
Lib/inspect.py               → getgeneratorstate(), getgeneratorlocals()
```

## Key PEPs

```
PEP 255  (2001) — Simple Generators (yield statement)
PEP 289  (2002) — Generator Expressions
PEP 342  (2005) — Coroutines via Enhanced Generators (send/throw/close)
PEP 380  (2009) — Syntax for Delegating to a Subgenerator (yield from)
PEP 479  (2014) — Change StopIteration handling inside generators
PEP 492  (2015) — Coroutines with async and await syntax
PEP 525  (2016) — Asynchronous Generators
PEP 530  (2016) — Asynchronous Comprehensions
```

## Quick Reference

```
╔══════════════════════════════════════════════════════════════════════════╗
║                    GENERATOR MODEL                                        ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  GENERATOR FUNCTION (has 'yield' in body):                               ║
║    def gen_func(args):                                                   ║
║        ...                                                               ║
║        yield value    ← makes this a generator function                  ║
║        ...                                                               ║
║                                                                          ║
║  CALLING gen_func() DOES NOT EXECUTE BODY:                               ║
║    gen_obj = gen_func(args)   ← creates PyGenObject, attaches frame     ║
║    type(gen_obj)              → <class 'generator'>                      ║
║    gen_obj.gi_frame           → suspended frame (not yet started)        ║
║                                                                          ║
║  EXECUTION HAPPENS ON next()/send():                                     ║
║    next(gen_obj)              → resumes frame, runs to next yield        ║
║    gen_obj.send(value)        → resumes frame, yield expr = value        ║
║    gen_obj.throw(exc)         → raises exc at yield point                ║
║    gen_obj.close()            → throws GeneratorExit, runs finally       ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  STATE MACHINE:                                                          ║
║    GEN_CREATED    → never started (next() not called yet)                ║
║         │ next()/send(None)                                              ║
║         ▼                                                                ║
║    GEN_RUNNING    → currently executing (between resume and yield)        ║
║         │ yield / return / exception                                     ║
║         ▼                                                                ║
║    GEN_SUSPENDED  → paused at yield point                                ║
║         │ next()/send()/throw()/close()                                  ║
║         ▼                                                                ║
║    GEN_RUNNING    → executing again...                                   ║
║         │ ...                                                            ║
║         ▼                                                                ║
║    GEN_CLOSED     → completed (cannot resume)                            ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  PyGenObject (Objects/genobject.c):                                      ║
║    ├── ob_refcnt, ob_type           (PyObject header)                   ║
║    ├── gi_frame          → _PyInterpreterFrame (suspended state)        ║
║    ├── gi_code           → PyCodeObject (bytecode)                      ║
║    ├── gi_name           → function name (str)                          ║
║    ├── gi_qualname       → qualified name (str)                         ║
║    ├── gi_weakreflist    → weak references                              ║
║    ├── gi_exc_state      → saved exception state                        ║
║    ├── gi_closed         → True if generator is finished                ║
║    └── gi_running_async  → True if in async context                     ║
║    Size: ~112 bytes + frame                                              ║
║                                                                          ║
║  FRAME PRESERVATION (between yields):                                    ║
║    ├── prev_instr        → instruction pointer (where to resume)        ║
║    ├── localsplus[0..n]  → local variables (preserved!)                 ║
║    ├── operand stack     → stack state (preserved!)                     ║
║    └── f_code            → code object reference                        ║
║                                                                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  BYTECODE:                                                               ║
║    RETURN_GENERATOR   → create gen object from frame (don't execute)    ║
║    YIELD_VALUE        → suspend frame, return value to caller           ║
║    RESUME             → entry/re-entry point                            ║
║    SEND               → resume with a value (for yield from)            ║
║    END_SEND           → cleanup after send completes                    ║
║                                                                          ║
║  PERFORMANCE:                                                            ║
║    Generator object:     ~112 bytes + frame                              ║
║    Per yield/resume:     ~100-200 ns (frame save/restore)               ║
║    vs list_iterator:     ~30 ns/element (just index++)                  ║
║    Memory advantage:     O(1) vs O(n) for lazy sequences                ║
║                                                                          ║
║  COROUTINE EVOLUTION:                                                    ║
║    PEP 255 (2001): yield → simple generators (produce values)           ║
║    PEP 342 (2005): send/throw/close → bidirectional communication      ║
║    PEP 380 (2009): yield from → delegation, return values               ║
║    PEP 492 (2015): async def/await → native coroutines (separate type) ║
║    PEP 525 (2016): async yield → async generators                       ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
```
