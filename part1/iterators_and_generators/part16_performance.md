# Part 16 — Performance

## 16.1 Cost Per Element

| Iterator Type | ns/element | Memory | Notes |
|---|---|---|---|
| list iteration | ~30 ns | 32B iterator + list | Fastest: just index++ |
| tuple iteration | ~28 ns | 32B iterator + tuple | Slightly faster (no resize check) |
| range iteration | ~40 ns | 56B iterator only | Computes value arithmetically |
| dict key iteration | ~35 ns | 56B iterator + dict | Sequential entries scan |
| generator (simple) | ~100-200 ns | 112B + frame | Frame save/restore overhead |
| itertools.chain | ~40 ns | ~48B + sub-iters | C implementation, minimal overhead |
| map(func, iter) | ~150 ns | 48B + func + iter | Function call overhead per element |
| genexp | ~120-200 ns | 112B + frame | Same as generator |

## 16.2 Memory: Lazy vs Eager

```python
# Processing 10M items:
import sys

# Eager (list):
eager = [x**2 for x in range(10_000_000)]
sys.getsizeof(eager)   # ~80 MB

# Lazy (generator):
lazy = (x**2 for x in range(10_000_000))
sys.getsizeof(lazy)    # ~112 bytes (!!!)

# Same result from sum():
sum(eager) == sum(lazy)  # True
# But lazy used 700,000× less memory!
```

## 16.3 When Eager Wins

```python
# Multiple iterations:
data = [compute(x) for x in source]  # Compute once, iterate many times
for _ in range(100):
    process(data)  # Reuses computed list — O(1) per re-iteration

# vs generator: must recompute each time
for _ in range(100):
    gen = (compute(x) for x in source)
    process(gen)  # Recomputes all values every time — 100× slower total!

# Random access:
data = list(gen_expr)
data[5000]    # O(1) — direct index
# Can't do this with a generator!

# Short sequences:
# For <100 items, list comprehension is faster (no generator overhead)
# The ~100ns per-element generator overhead dominates for small N
```

## 16.4 Pipeline Optimization

```python
# BAD: multiple materialized intermediates
step1 = [transform1(x) for x in data]    # 80 MB
step2 = [transform2(x) for x in step1]   # 80 MB
step3 = [transform3(x) for x in step2]   # 80 MB
result = aggregate(step3)                  # Peak: 240 MB

# GOOD: lazy pipeline
result = aggregate(
    transform3(transform2(transform1(x)))
    for x in data
)  # Peak: O(1)! One item flows through all transforms at a time.
```

## 16.5 Cache Locality

```
List iteration: excellent cache locality
  - ob_item array is contiguous → prefetcher works
  - Iterator walks sequentially → cache hits

Generator iteration: poor cache locality
  - Frame on heap (random location)
  - Each yield: jump to generator frame (likely cache miss)
  - Return: jump back to caller frame (likely cache miss)
  - For CPU-bound tight loops: generators lose badly

Rule: For < 10K items where you'll process multiple times, materialize to list.
      For > 100K items or single-pass or I/O-bound: use generators.
```

## 16.6 Interview Questions — Part 16

**Q1**: How much slower is a generator per element vs list iteration? **A**: ~3-7× slower (100-200ns vs 30ns). The overhead is frame save/restore on each yield.

**Q2**: When should you materialize a generator to a list? **A**: When you need multiple iterations, random access, or the dataset is small (<10K items) and you process it in tight CPU-bound loops.

**Q3**: What's the memory advantage of generators for large data? **A**: O(1) vs O(n). A generator over 10M items uses ~112 bytes. A list uses ~80 MB. Generators enable processing datasets larger than RAM.

**Q4**: Why do itertools functions outperform equivalent generators? **A**: itertools is C code — no Python frame overhead, no bytecode dispatch, direct C loops. 2-5× faster than equivalent Python generators.
