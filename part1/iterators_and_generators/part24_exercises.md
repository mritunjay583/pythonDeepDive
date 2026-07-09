# Part 24 — Exercises

## Section A: Iterator State Tracing (5 Exercises)

### Exercise 1: Trace list_iterator state
```python
data = [10, 20, 30, 40]
it = iter(data)
next(it)  # ?
next(it)  # ?
```
**Answer:**
```
After iter(data): _PyListIterObject{it_index=0, it_seq→[10,20,30,40]}
After next(it):   it_index=1, returns 10
After next(it):   it_index=2, returns 20
State: [seq ref alive, 2 items remaining]
```

### Exercise 2: Trace generator state
```python
def gen():
    x = 1
    yield x
    x += 1
    yield x

g = gen()
next(g)
# What is the state of g's frame now?
```
**Answer:** `gi_frame.prev_instr` points to first YIELD_VALUE. `localsplus[0]` (x) = 1. Operand stack empty. State = GEN_SUSPENDED.

### Exercise 3: Trace exhaustion
```python
gen = (x for x in [1,2])
list(gen)
next(gen, "default")
```
**Answer:** After `list(gen)`: generator exhausted (gi_frame=NULL, gi_closed=True). `next(gen, "default")` → tp_iternext returns NULL → default returned → `"default"`.

### Exercise 4: Trace dict iterator mutation detection
```python
d = {"a": 1, "b": 2}
it = iter(d)
next(it)  # "a"
d["c"] = 3  # Mutation!
next(it)  # ???
```
**Answer:** dict_iterator stores `di_used=2` at creation. After `d["c"]=3`: dict.ma_used=3. On next call: `3 != 2` → RuntimeError!

### Exercise 5: Trace yield from delegation
```python
def sub():
    yield "sub1"
    return "sub_result"
def main():
    result = yield from sub()
    yield f"got: {result}"

g = main()
print(next(g))   # ?
print(next(g))   # ?
```
**Answer:** First next: enters main → yield from sub() → enters sub → yields "sub1". Second next: resumes sub → sub returns "sub_result" → StopIteration(value="sub_result") → yield from catches it → result = "sub_result" → yields "got: sub_result".

---

## Section B: Memory Analysis (5 Exercises)

### Exercise 6
Compare memory usage:
```python
a = [x**2 for x in range(1_000_000)]  # How much?
b = (x**2 for x in range(1_000_000))  # How much?
```
**Answer:** `a` ≈ 8 MB (1M pointers + int objects). `b` ≈ 112 bytes (generator object). Ratio: ~70,000×.

### Exercise 7
What's the peak memory during:
```python
total = sum(x**2 for x in range(10_000_000))
```
**Answer:** O(1)! At any moment: one int from range (28B) + one squared result (28B) + running sum (28B) + generator object (112B) + range_iterator (56B). Total: ~250 bytes regardless of n!

### Exercise 8
What's wrong with this code for large data?
```python
from itertools import tee
data = (expensive(x) for x in huge_source)
a, b = tee(data)
result_a = sum(a)  # Consumes all of a
result_b = max(b)  # Consumes all of b
```
**Answer:** `tee` buffers all items consumed by `a` until `b` reads them. Since we consume ALL of `a` first, then ALL of `b`, tee buffers the ENTIRE dataset! Same as materializing to a list. Fix: `data = list(data)`.

### Exercise 9
How many objects are created during:
```python
for i in range(5):
    for c in "ab":
        pass
```
**Answer:**
- 1 range object (persists)
- 1 range_iterator (persists through outer loop)
- 5 int objects (0-4, from cache)
- 5 str_iterators (one per outer iteration, for "ab")
- 10 single-char strings ('a','b' × 5, from cache)
- Total NEW allocations: ~5 str_iterators + 1 range_iterator = ~6 objects (ints and chars are cached)

### Exercise 10
Calculate generator object size for:
```python
def complex_gen(a, b, c):
    x = a + b
    y = [1, 2, 3]
    while True:
        yield x + y[0] + c
```
**Answer:**
- PyGenObject: ~112 bytes
- Frame: header (~56B) + localsplus (5 locals: a,b,c,x,y × 8B = 40B) + stack (co_stacksize ~3 × 8B = 24B)
- Total: ~112 + 56 + 40 + 24 ≈ 232 bytes (plus the list [1,2,3] = ~88 bytes)

---

## Section C: Implementation Exercises (5 Exercises)

### Exercise 11: Implement `my_enumerate`
```python
def my_enumerate(iterable, start=0):
    """Recreate enumerate() as a generator."""
    n = start
    for item in iterable:
        yield n, item
        n += 1

# Test:
assert list(my_enumerate("abc")) == [(0,'a'),(1,'b'),(2,'c')]
```

### Exercise 12: Implement `my_zip`
```python
def my_zip(*iterables):
    """Recreate zip() as a generator."""
    iterators = [iter(it) for it in iterables]
    while True:
        result = []
        for it in iterators:
            try:
                result.append(next(it))
            except StopIteration:
                return  # Shortest exhausted
        yield tuple(result)
```

### Exercise 13: Implement `my_chain`
```python
def my_chain(*iterables):
    """Recreate itertools.chain."""
    for iterable in iterables:
        yield from iterable
```

### Exercise 14: Implement `my_islice`
```python
def my_islice(iterable, *args):
    """Recreate itertools.islice (simplified: islice(it, stop))."""
    s = slice(*args)
    start = s.start or 0
    stop = s.stop
    step = s.step or 1
    
    it = iter(iterable)
    # Skip items before start:
    for i in range(start):
        try: next(it)
        except StopIteration: return
    
    # Yield items:
    count = 0
    for i, item in enumerate(it):
        if start + count >= stop:
            return
        if i % step == 0:
            yield item
            count += 1
```

### Exercise 15: Implement a coroutine-style pipeline
```python
def running_average():
    """Coroutine: accepts values, yields running average."""
    total = 0
    count = 0
    while True:
        value = yield total / count if count else 0
        total += value
        count += 1

# Usage:
avg = running_average()
next(avg)  # Prime
print(avg.send(10))  # 10.0
print(avg.send(20))  # 15.0
print(avg.send(30))  # 20.0
```
