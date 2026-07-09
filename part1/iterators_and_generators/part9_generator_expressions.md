# Part 9 — Generator Expressions

## 9.1 Syntax and Semantics

```python
# Generator expression (lazy — O(1) memory):
gen = (x**2 for x in range(1000000))

# List comprehension (eager — O(n) memory):
lst = [x**2 for x in range(1000000)]

# They look similar but behave VERY differently:
type(gen)  # <class 'generator'>
type(lst)  # <class 'list'>
```

---

## 9.2 Lazy vs Eager Evaluation

```python
# List comprehension: computes ALL values NOW, stores in memory
squares_list = [x**2 for x in range(10_000_000)]
# Memory: ~80 MB (10M integers × 8 bytes pointer + int objects)
# Time: computes all 10M squares immediately

# Generator expression: computes NOTHING yet
squares_gen = (x**2 for x in range(10_000_000))
# Memory: ~200 bytes (just the generator object!)
# Time: instant (no computation yet)

# Values computed on-demand:
next(squares_gen)  # 0 (computes just this one)
next(squares_gen)  # 1 (computes just this one)

# Perfect for: sum, any, all, min, max (don't need all values at once)
total = sum(x**2 for x in range(10_000_000))
# Only ONE value in memory at a time! O(1) space!
```

---

## 9.3 Compilation: Genexp Creates a Nested Function

```python
gen = (x**2 for x in items)
```

Compiles to (conceptually):
```python
def _genexpr_hidden(iter_arg):
    for x in iter_arg:
        yield x**2

gen = _genexpr_hidden(iter(items))
```

The genexp creates an **anonymous generator function** + immediately calls it with the iterator. This is why genexps have their own scope (Python 3+).

---

## 9.4 Memory Comparison

```python
import sys

items = range(1000)

lst = [x**2 for x in items]
gen = (x**2 for x in items)

sys.getsizeof(lst)  # ~8856 bytes (1000 pointers + list overhead)
sys.getsizeof(gen)  # ~112 bytes (just the generator object!)

# After consuming:
total_list = sum(lst)    # List persists in memory (8KB) until del
total_gen = sum(gen)     # Generator consumed → just 112 bytes throughout
```

---

## 9.5 When to Use Each

| Use Case | Comprehension | Generator Expression |
|----------|--------------|---------------------|
| Need random access later | ✅ | ❌ (one-shot) |
| Need to iterate multiple times | ✅ | ❌ (exhaustible) |
| Feeding into sum/min/max/any/all | ❌ (wasteful) | ✅ (O(1) memory) |
| Very large datasets | ❌ (memory) | ✅ |
| Need length before processing | ✅ | ❌ |
| Pipeline of transformations | ❌ | ✅ (lazy chain) |
| Short sequences (<100 items) | ✅ (faster) | ~same |

---

## 9.6 Composing Lazy Pipelines

```python
# Each step is O(1) memory — values flow through one at a time:
data = range(10_000_000)
step1 = (x * 2 for x in data)            # Double
step2 = (x for x in step1 if x % 3 == 0) # Filter
step3 = (x + 1 for x in step2)           # Transform
result = sum(step3)                        # Consume

# Total memory: O(1)! Three generator objects (~336 bytes)
# No intermediate lists of millions of items!
```

---

## 9.7 Gotcha: Single-Use

```python
gen = (x for x in range(5))
print(list(gen))  # [0, 1, 2, 3, 4]
print(list(gen))  # [] — EXHAUSTED! Cannot reuse!

# Fix: re-create the generator
def make_gen():
    return (x for x in range(5))

print(list(make_gen()))  # [0, 1, 2, 3, 4]
print(list(make_gen()))  # [0, 1, 2, 3, 4] — new generator each time
```

---

## 9.8 Interview Questions — Part 9

**Q1**: What's the memory difference between `[x for x in range(1M)]` and `(x for x in range(1M))`? **A**: List: ~8 MB (materialized). Generator: ~112 bytes (lazy, values computed on demand). 

**Q2**: Can you iterate a generator expression twice? **A**: No. It's a one-shot iterator. Once exhausted, it yields nothing on second iteration.

**Q3**: When should you prefer list comprehension over genexp? **A**: When you need random access (lst[i]), multiple iterations, or need to know the length upfront. For short sequences, list comp is slightly faster (no generator overhead per element).

**Q4**: How does `sum(x**2 for x in range(n))` achieve O(1) memory? **A**: The genexp produces one value at a time. sum() consumes each immediately (adds to running total). Only one x**2 value exists in memory at any moment.

**Q5**: Why do generator expressions have their own scope? **A**: They compile to a hidden generator function. The iteration variable is local to that function. This prevents variable leakage (unlike Python 2 list comprehensions which leaked).
