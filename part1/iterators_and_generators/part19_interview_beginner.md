# Part 19 — Interview Questions: Beginner (50)

**Q1**: What is an iterable? **A**: Any object with `__iter__()` that returns an iterator. Examples: list, dict, str, range.
**Q2**: What is an iterator? **A**: An object with `__iter__()` (returns self) AND `__next__()` (returns next value or raises StopIteration).
**Q3**: What does `iter(x)` do? **A**: Calls `x.__iter__()` and returns the resulting iterator.
**Q4**: What does `next(it)` do? **A**: Calls `it.__next__()` — returns next value or raises StopIteration.
**Q5**: What is StopIteration? **A**: Exception raised by `__next__()` to signal no more values. Caught by for loops to end iteration.
**Q6**: Is a list an iterator? **A**: No, it's an iterable. `iter(list)` returns a list_iterator.
**Q7**: Can you use a for loop on an iterator? **A**: Yes. `iter(iterator)` returns self, so for loops work.
**Q8**: What does `yield` do? **A**: Suspends the function, saves its state, returns a value. On next call to next(), resumes.
**Q9**: What does calling a generator function return? **A**: A generator object (iterator). The body doesn't execute yet.
**Q10**: Can you iterate a generator twice? **A**: No. Generators are one-shot iterators. Must create a new one.
**Q11**: What is a generator expression? **A**: `(expr for x in iter)` — creates a lazy generator without defining a function.
**Q12**: Difference between `[x for x in r]` and `(x for x in r)`? **A**: List comp creates a list (eager, O(n) memory). Genexp creates a generator (lazy, O(1) memory).
**Q13**: What does `range(n)` return? **A**: A range object (iterable, lazy). NOT a list. O(1) memory.
**Q14**: What does `map(func, iter)` return? **A**: A map iterator (lazy). Applies func to each item on demand.
**Q15**: What does `filter(pred, iter)` return? **A**: A filter iterator (lazy). Yields items where pred(item) is True.
**Q16**: What does `zip(a, b)` return? **A**: A zip iterator. Yields tuples pairing items from a and b.
**Q17**: What does `enumerate(iter)` return? **A**: An enumerate iterator. Yields (index, value) tuples.
**Q18**: What happens when you `list(gen)` twice? **A**: First time: materializes all values. Second time: empty list (generator exhausted).
**Q19**: How does a for loop end? **A**: When the iterator raises StopIteration. The for loop catches it silently.
**Q20**: What is `itertools`? **A**: Standard library module with C-implemented lazy iterator building blocks.
**Q21**: What is `itertools.chain()`? **A**: Lazily concatenates multiple iterables into one sequence.
**Q22**: What is `itertools.islice()`? **A**: Lazy slicing for any iterator (not just sequences).
**Q23**: How do you read a file line by line lazily? **A**: `for line in open(file)` — file iteration is already lazy.
**Q24**: What does `sum(x**2 for x in range(n))` use memory-wise? **A**: O(1) — genexp + range are both lazy. One value at a time.
**Q25**: Can dictionaries be iterated? **A**: Yes. `for k in dict` iterates over keys. `.values()` for values, `.items()` for pairs.
**Q26**: What does `reversed(list)` return? **A**: A list_reverseiterator (lazy, doesn't create a reversed list).
**Q27**: What is `next(it, default)`? **A**: Returns next value, or `default` if iterator is exhausted (no StopIteration raised).
**Q28**: Can you use `break` in a for loop? **A**: Yes. Exits loop immediately. Iterator is NOT fully consumed.
**Q29**: What is `iter(callable, sentinel)`? **A**: Creates iterator that calls callable() until result equals sentinel.
**Q30**: What does `yield from` do? **A**: Delegates to a sub-iterator, yielding all its values.
**Q31**: Can strings be iterated? **A**: Yes. Each iteration yields a single character (length-1 str).
**Q32**: Can sets be iterated? **A**: Yes. Iteration order is arbitrary (not insertion order like dicts).
**Q33**: What is an infinite iterator? **A**: One that never raises StopIteration. E.g., `itertools.count()`.
**Q34**: What happens if `__next__` never raises StopIteration? **A**: A for loop on it never terminates (infinite loop).
**Q35**: What is `any(gen)` efficient for? **A**: Short-circuits on first True value. Doesn't consume entire generator.
**Q36**: What is `all(gen)` efficient for? **A**: Short-circuits on first False value.
**Q37**: Can you send values into a generator? **A**: Yes, with `gen.send(value)`. The value becomes the result of the yield expression.
**Q38**: What does `gen.close()` do? **A**: Throws GeneratorExit inside the generator. finally blocks run.
**Q39**: What does `gen.throw(exc)` do? **A**: Throws an exception at the yield point inside the generator.
**Q40**: What is the `else` clause in a for loop? **A**: Runs if the loop completed without `break`.
**Q41**: Are generator expressions lazy? **A**: Yes. Values computed on demand, one at a time.
**Q42**: What is `functools.reduce`? **A**: Accumulates a sequence to a single value using a function. Eager (consumes all).
**Q43**: What does `sorted(iterable)` return? **A**: A new list (eager). Must consume the entire iterable first to sort.
**Q44**: What does `max(iterable)` do? **A**: Consumes entire iterable to find maximum. O(n) time, O(1) extra memory.
**Q45**: Can you nest generators? **A**: Yes. A generator can yield from another generator (yield from).
**Q46**: Is `range` an iterator? **A**: No! It's an iterable. `iter(range(n))` creates a range_iterator.
**Q47**: Why can `range` be iterated multiple times? **A**: Because `range.__iter__()` creates a NEW range_iterator each time. range itself is stateless.
**Q48**: What is `collections.abc.Iterator`? **A**: Abstract base class defining the iterator protocol. Useful for isinstance checks.
**Q49**: Can you pickle a generator? **A**: No. Generators contain frame state that can't be serialized.
**Q50**: What is `itertools.tee(iter, n)`? **A**: Creates n independent iterators from one source. But buffers values — memory warning!
