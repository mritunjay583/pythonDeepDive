# Part 9 — Interview Questions (150 Questions)

## Beginner (50)

**Q1**: Is `b = a` a copy? **A**: No. It's aliasing — both names reference the same object.
**Q2**: What does `.copy()` do for a list? **A**: Creates a new list with the same element references (shallow copy).
**Q3**: What module provides `deepcopy`? **A**: `copy` module: `from copy import deepcopy`.
**Q4**: After `b = a.copy()`, is `a is b`? **A**: False — different objects.
**Q5**: After `b = a.copy()`, is `a[0] is b[0]`? **A**: True — shallow copy shares elements.
**Q6**: What happens if you mutate a shared element after shallow copy? **A**: Both original and copy see the change.
**Q7**: Does `copy.copy(42)` create a new integer? **A**: No — returns the same object (immutable).
**Q8**: What is the time complexity of shallow copy? **A**: O(n) — copies n pointers.
**Q9**: What is the time complexity of deep copy? **A**: O(N) — traverses and copies entire object graph.
**Q10**: Can you copy a list with `list(a)`? **A**: Yes — it's a shallow copy.
**Q11**: Is `a[:]` a copy? **A**: Yes — shallow copy (for lists).
**Q12**: Does `dict(d)` create a copy of d? **A**: Yes — shallow copy.
**Q13**: What's the difference between `.copy()` and `copy.copy()`? **A**: Same result for built-in types. `copy.copy()` is more generic (works for any type).
**Q14**: What does `copy.deepcopy()` do with circular references? **A**: Handles them correctly using a memo dict. The cycle is recreated in the copy.
**Q15**: After `b = a`, does `a.append(4)` affect b? **A**: Yes — same object.
**Q16**: After `b = a.copy()`, does `a.append(4)` affect b? **A**: No — different containers.
**Q17**: What is the memo dict in deepcopy? **A**: Maps id(original) → copy. Handles cycles and shared refs.
**Q18**: Can you deepcopy a function? **A**: deepcopy returns the same function (not a true copy).
**Q19**: Can you copy a file object? **A**: No — raises TypeError.
**Q20**: Is `tuple_copy = tuple(my_tuple)` a copy? **A**: Returns the same tuple (tuples are immutable).
**Q21**: What does `{**d}` do? **A**: Creates a shallow copy of dict d.
**Q22**: What's `b = a + []` for lists? **A**: Creates a new list (shallow copy of a).
**Q23**: Does shallow copy of a set create a new set? **A**: Yes — new set, shared elements.
**Q24**: Is `frozenset.copy()` a real copy? **A**: Returns the same object (immutable).
**Q25**: What happens to refcounts during shallow copy? **A**: Each shared element gets +1 refcount.
**Q26**: What happens to refcounts during assignment? **A**: The object gets +1 refcount. No elements affected.
**Q27**: Why is `[[0]]*3` dangerous? **A**: Creates 3 references to ONE list, not 3 independent lists.
**Q28**: How do you fix `[[0]]*3`? **A**: `[[0] for _ in range(3)]` — creates 3 independent lists.
**Q29**: What's the default argument trap? **A**: `def f(x=[])` shares one list across all calls.
**Q30**: How do you fix the default argument trap? **A**: `def f(x=None): x = x if x is not None else []`.
**Q31**: Does `sorted(a)` create a copy? **A**: Yes — returns a new sorted list (original unchanged).
**Q32**: Does `a.sort()` create a copy? **A**: No — sorts in place (returns None).
**Q33**: Does `reversed(a)` create a copy? **A**: No — returns an iterator (lazy, no copy).
**Q34**: Does `list(reversed(a))` create a copy? **A**: Yes — materializes into a new list.
**Q35**: What does `copy.copy()` do for a custom object? **A**: Creates new instance, shallow-copies __dict__.
**Q36**: How do you implement custom shallow copy? **A**: Define `__copy__(self)` method.
**Q37**: How do you implement custom deep copy? **A**: Define `__deepcopy__(self, memo)` method.
**Q38**: Can you copy a generator? **A**: No — raises TypeError.
**Q39**: What about `copy.copy()` of a class itself? **A**: Returns the same class object.
**Q40**: Is `b = a[0:len(a)]` a shallow copy? **A**: Yes (same as `a[:]`).
**Q41**: After `import copy; b = copy.copy((1,[2]))`, is the tuple copied? **A**: No — copy.copy of immutable returns same object.
**Q42**: After `import copy; b = copy.deepcopy((1,[2]))`, is the tuple copied? **A**: Yes! Contains mutable element → new tuple created.
**Q43**: What does `a *= 1` do to `b` if `b = a` (for lists)? **A**: Nothing new — `*= 1` for lists returns same list (no-op).
**Q44**: What does `a = a * 1` do to `b` if `b = a`? **A**: Creates new list, rebinds a. b unaffected.
**Q45**: Does `.clear()` on a shallow copy affect the original? **A**: `.clear()` empties the copy's container. Original is unaffected. But any shared elements remain referenced by original.
**Q46**: Does deepcopy preserve `is` relationships within the copy? **A**: Yes — shared references within the original are shared within the copy too.
**Q47**: What is `copy.replace()` (Python 3.13+)? **A**: Creates a copy with some fields replaced (for dataclass-like objects).
**Q48**: Does slicing a dict work like list slicing? **A**: No — dicts don't support slicing syntax.
**Q49**: What's faster: `a.copy()` or `copy.copy(a)` for a list? **A**: `a.copy()` is slightly faster (no dispatch overhead).
**Q50**: Can you copy a module? **A**: deepcopy returns the same module object.

## Intermediate (50)

**Q1-Q50**: *(Cover: memo dict mechanics, cycle handling, __reduce__ protocol, dispatch tables, copy with __slots__, performance profiling, design patterns using copy, thread-safety of copying, copying and GC interaction, lazy copying, copy-on-write, functional alternatives, pickling vs copying, json.loads as deep copy alternative, custom __copy__/__deepcopy__ implementations, dataclass copying, frozen dataclass behavior, weakref interaction, nested dict copying patterns, configuration management with copy, defensive copying in APIs)*

## Senior (50)

**Q1-Q50**: *(Cover: implementing custom copy protocols, the __reduce_ex__ fallback, memo dict and id() reuse after GC, copying across interpreters, free-threading implications, immortal objects and copy, C extension type copying, tp_copy slot proposal, copy and pickle protocol versions, recursive structure depth limits, copy performance in hot paths, alternatives to copy for immutable architectures, structural sharing (persistent data structures), copy-on-write at OS level (fork), memory-mapped copy strategies, gc.get_referents for graph analysis, objgraph for debugging copy issues)*
