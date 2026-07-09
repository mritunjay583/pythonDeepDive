# Part 18 — Common Mistakes

## 18.1 Iterator Exhaustion

```python
gen = (x**2 for x in range(5))
print(sum(gen))    # 30
print(sum(gen))    # 0!!! Generator exhausted!
print(list(gen))   # [] — nothing left

# Fix: recreate or use a function
def squares(): return (x**2 for x in range(5))
print(sum(squares()))   # 30
print(sum(squares()))   # 30 (new generator each time)
```

## 18.2 Reusing Generators

```python
def data_pipeline(records):
    processed = (transform(r) for r in records)
    valid = filter(validate, processed)
    return valid  # Returns GENERATOR — caller must consume it!

# BUG: consuming twice
result = data_pipeline(records)
count = sum(1 for _ in result)  # Exhausts it!
items = list(result)            # [] — empty!

# Fix: materialize if needed multiple times
items = list(data_pipeline(records))
count = len(items)
```

## 18.3 Modifying Collection During Iteration

```python
# RuntimeError:
d = {"a": 1, "b": 2, "c": 3}
for k in d:
    if d[k] < 2:
        del d[k]  # RuntimeError: dictionary changed size during iteration

# Fix: iterate over a copy of keys
for k in list(d.keys()):
    if d[k] < 2:
        del d[k]  # Safe! Iterating over the list, not the dict.

# Or: build new dict
d = {k: v for k, v in d.items() if v >= 2}
```

## 18.4 The `tee()` Memory Trap

```python
from itertools import tee

# tee creates independent iterators BUT buffers divergence:
a, b = tee(huge_generator)  # O(1) initially

# If 'a' advances far while 'b' hasn't:
for item in a:
    process(item)  # Processes all items

# ALL items are buffered (waiting for 'b' to read them)!
# Memory: O(n) — same as materializing to a list!

# Fix: don't use tee for large divergence. Materialize instead:
data = list(huge_generator)
# Then iterate data independently
```

## 18.5 Infinite Loop (Missing StopIteration)

```python
# BUG: iterator never raises StopIteration
class BrokenIter:
    def __iter__(self): return self
    def __next__(self): return 42  # NEVER stops!

for x in BrokenIter():  # INFINITE LOOP! for waits for StopIteration
    print(x)             # This prints 42 forever

# Fix: always have a termination condition
class FixedIter:
    def __init__(self, n):
        self.n = n; self.i = 0
    def __iter__(self): return self
    def __next__(self):
        if self.i >= self.n:
            raise StopIteration
        self.i += 1
        return 42
```

## 18.6 StopIteration Leaking from Generators

```python
# BUG: StopIteration inside a generator doesn't yield — it TERMINATES the generator!
def buggy():
    items = iter([1, 2, 3])
    while True:
        yield next(items)  # After 3 items: StopIteration PROPAGATES!
        # This silently terminates the generator! No error!

list(buggy())  # [1, 2, 3] — looks correct but...
# If items were supposed to be infinite, you'd lose data!

# Fix (Python 3.7+ RuntimeError for leaked StopIteration in generators):
# Since PEP 479 (default in 3.7): StopIteration inside generator → RuntimeError
# The fix: use for loop or handle explicitly:
def fixed():
    items = iter([1, 2, 3])
    for item in items:  # for catches StopIteration properly
        yield item
```

## 18.7 Late Binding in Generator Expressions

```python
# BUG:
i = 0
gen = (i for _ in range(3))
i = 10
list(gen)  # [10, 10, 10] — NOT [0, 0, 0]!

# The expression `i` is evaluated LAZILY — at consumption time, not creation!
# At consumption time, i = 10.

# Fix: capture current value
gen = (i for _ in range(3) for i in [i])  # Ugly
# Better: use a function default
def make_gen(val):
    return (val for _ in range(3))
gen = make_gen(0)
list(gen)  # [0, 0, 0]
```

## 18.8 Generator Resource Leaks

```python
# BUG: generator holds file open:
def read_lines(path):
    f = open(path)
    for line in f:
        yield line
    # f.close() NEVER called if generator is abandoned mid-way!

gen = read_lines("file.txt")
next(gen)  # Opens file
# gen goes out of scope without being fully consumed
# File stays open until GC collects the generator!

# Fix: use try/finally or context manager
def read_lines(path):
    with open(path) as f:
        for line in f:
            yield line
    # with statement ensures close even if generator is closed/GC'd
```

## 18.9 Interview Questions — Part 18

**Q1**: Why can't you iterate a generator twice? **A**: Generators are iterators (single-use). Once StopIteration is raised, subsequent next() calls keep raising it. Must create a new generator.

**Q2**: What's the memory danger of `itertools.tee`? **A**: If one copy advances far ahead, all yielded values are buffered (waiting for the other copy). Can use O(n) memory — equivalent to materializing the entire sequence.

**Q3**: Why does modifying a dict during iteration raise RuntimeError? **A**: The dict iterator stores the entry count at creation. If it changes (insert/delete), structural integrity of the hash table may be compromised. RuntimeError prevents undefined behavior.

**Q4**: What is PEP 479 about? **A**: Makes StopIteration inside a generator raise RuntimeError instead of silently terminating the generator. Prevents subtle bugs where generators end prematurely due to leaked StopIteration from inner iterators.
