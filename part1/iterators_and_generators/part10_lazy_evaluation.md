# Part 10 — Lazy Evaluation

## 10.1 The Principle

**Lazy evaluation** = compute values only when needed, not before. In Python, this is achieved through iterators and generators.

```python
# EAGER: compute everything upfront
data = [expensive(x) for x in range(1000000)]  # All 1M computations NOW
result = data[0]  # Used only the first one — wasted 999,999 computations!

# LAZY: compute on demand
data = (expensive(x) for x in range(1000000))  # No computation yet
result = next(data)  # Computes ONLY the first one — no waste!
```

---

## 10.2 Lazy Built-ins

These return iterators (lazy), NOT lists:

```python
map(func, iterable)        # Applies func to each item lazily
filter(pred, iterable)     # Filters items lazily
zip(iter1, iter2)          # Pairs items lazily
enumerate(iterable)        # Adds index lazily
reversed(sequence)         # Reverses lazily (for sequences with __reversed__)
range(n)                   # Generates integers lazily (O(1) memory!)

# All are O(1) memory regardless of input size!
# Values computed only when consumed.
```

### Pipeline Example:
```python
# Process 100M records with O(1) memory:
records = read_csv_lazily("huge.csv")              # Generator (yields rows)
filtered = filter(lambda r: r["age"] > 18, records) # Lazy filter
names = map(lambda r: r["name"].upper(), filtered)   # Lazy transform
first_100 = itertools.islice(names, 100)             # Lazy slice

result = list(first_100)  # Only NOW does computation happen
# Only 100 items ever in memory (plus the one being processed)!
```

---

## 10.3 Infinite Sequences

Lazy evaluation enables infinite sequences:

```python
def naturals():
    """Infinite sequence: 0, 1, 2, 3, ..."""
    n = 0
    while True:
        yield n
        n += 1

def fibonacci():
    """Infinite Fibonacci sequence."""
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

# Take only what you need:
import itertools
first_20_fibs = list(itertools.islice(fibonacci(), 20))
# [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, ...]

# Find first Fibonacci > 1000:
fib = fibonacci()
result = next(f for f in fib if f > 1000)  # 1597 (computed lazily!)
```

---

## 10.4 Streaming Data Processing

```python
def read_log_lines(path):
    """Stream lines from a multi-GB log file."""
    with open(path) as f:
        for line in f:           # File iteration is already lazy!
            yield line.strip()

def parse_json_lines(lines):
    """Parse each line as JSON."""
    import json
    for line in lines:
        yield json.loads(line)

def filter_errors(records):
    """Keep only error records."""
    for record in records:
        if record.get("level") == "ERROR":
            yield record

# Pipeline: GB of data, O(1) memory!
lines = read_log_lines("/var/log/app.log")  # Lazy
records = parse_json_lines(lines)            # Lazy
errors = filter_errors(records)              # Lazy

for error in errors:
    alert(error)  # Process one at a time, never loads entire file
```

---

## 10.5 itertools — The Lazy Toolkit

```python
import itertools as it

# Infinite:
it.count(10, 2)        # 10, 12, 14, 16, ... (infinite!)
it.cycle([1,2,3])      # 1, 2, 3, 1, 2, 3, ... (infinite!)
it.repeat(42)          # 42, 42, 42, ... (infinite!)
it.repeat(42, 5)       # 42, 42, 42, 42, 42 (finite)

# Combining:
it.chain([1,2], [3,4])     # 1, 2, 3, 4 (concatenate iterables)
it.chain.from_iterable([[1,2],[3,4]])  # Same, from iterable of iterables
it.zip_longest([1,2], [3,4,5], fillvalue=0)  # (1,3),(2,4),(0,5)

# Filtering:
it.compress([1,2,3,4], [1,0,1,0])  # 1, 3 (select by mask)
it.filterfalse(pred, data)          # Opposite of filter
it.dropwhile(pred, data)            # Drop leading items where pred=True
it.takewhile(pred, data)            # Take leading items where pred=True
it.islice(data, 5, 20, 2)          # Slice lazily: items[5:20:2]

# Grouping:
it.groupby(sorted_data, key=func)   # Group consecutive equal keys

# Combinatorial:
it.product([1,2], [3,4])           # (1,3),(1,4),(2,3),(2,4)
it.permutations([1,2,3], 2)        # All 2-permutations
it.combinations([1,2,3], 2)        # All 2-combinations

# Accumulating:
it.accumulate([1,2,3,4], operator.add)  # 1, 3, 6, 10 (running sum)
```

ALL of these are lazy — they return iterators, not lists.

---

## 10.6 Memory Comparison: Eager vs Lazy

```python
# Processing 10 million items:

# EAGER (bad for large data):
data = list(range(10_000_000))                    # 80 MB
doubled = [x * 2 for x in data]                   # 80 MB more
filtered = [x for x in doubled if x % 3 == 0]    # ~27 MB more
total = sum(filtered)                              # Peak: ~187 MB

# LAZY (constant memory):
data = range(10_000_000)                           # 48 bytes
doubled = (x * 2 for x in data)                   # 112 bytes
filtered = (x for x in doubled if x % 3 == 0)    # 112 bytes
total = sum(filtered)                              # Peak: ~384 bytes!

# Same result. 500,000× less memory.
```

---

## 10.7 When Lazy Evaluation Hurts

```python
# 1. Multiple iterations needed:
gen = (expensive(x) for x in data)
total = sum(gen)       # Exhausts generator
average = total / ???  # Can't iterate again for count!
# Fix: materialize or use two passes with itertools.tee (but tee buffers!)

# 2. Random access needed:
gen = (x**2 for x in range(1000))
gen[500]  # TypeError! Generators don't support indexing.
# Fix: materialize to list if random access needed

# 3. Debugging is harder:
gen = (complex_transform(x) for x in data)
# Can't inspect "what's in it" without consuming it!
# print(list(gen)) exhausts it — can't use it after

# 4. Timing is different:
gen = (slow_io(x) for x in urls)
# Errors happen during CONSUMPTION, not creation!
# Hard to trace which item caused the error.
```

---

## 10.8 Interview Questions — Part 10

**Q1**: What is lazy evaluation in Python? **A**: Computing values only when consumed (via iterators/generators), not when defined. Enables O(1) memory processing of arbitrarily large datasets.

**Q2**: Which built-in functions return lazy iterators? **A**: map(), filter(), zip(), enumerate(), reversed(), range(). All return iterators, not lists (unlike Python 2 where map/filter returned lists).

**Q3**: How do you process a 100GB file with constant memory? **A**: Use lazy pipeline: `for line in open(file)` (file iteration is lazy) → generator transforms → consume one at a time. Never load entire file.

**Q4**: What's the downside of lazy evaluation? **A**: Can't iterate twice (single-use), no random access, harder to debug (errors at consumption time), and can't know length without exhausting.

**Q5**: How does `sum(x**2 for x in range(10**9))` avoid using 8GB of memory? **A**: The genexp produces one value at a time. sum() consumes immediately. Only one integer exists at a time in the pipeline. range() is also O(1). Total memory: ~400 bytes.
