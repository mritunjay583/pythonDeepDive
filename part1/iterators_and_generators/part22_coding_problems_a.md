# Part 22 — Coding Problems (1-50)

### Q1: Basic Iterator
```python
it = iter([10, 20, 30])
print(next(it))
print(next(it))
```
**Output**: `10`, `20`

### Q2: Exhaustion
```python
gen = (x for x in range(3))
print(list(gen))
print(list(gen))
```
**Output**: `[0, 1, 2]`, `[]`

### Q3: Generator Function
```python
def gen():
    yield 1; yield 2; yield 3
g = gen()
print(next(g), next(g))
```
**Output**: `1 2`

### Q4: Generator State
```python
def gen():
    print("A"); yield 1
    print("B"); yield 2
g = gen()
print("start")
x = next(g)
print(x)
```
**Output**: `start`, `A`, `1` (A prints when generator resumes to first yield)

### Q5: for loop on generator
```python
def gen():
    for i in range(3):
        yield i * 10
print(list(gen()))
```
**Output**: `[0, 10, 20]`

### Q6: Generator expression memory
```python
import sys
a = [x**2 for x in range(1000)]
b = (x**2 for x in range(1000))
print(sys.getsizeof(a) > 1000)
print(sys.getsizeof(b) < 200)
```
**Output**: `True`, `True`

### Q7: Yield from
```python
def sub(): yield 1; yield 2
def main():
    yield 0
    yield from sub()
    yield 3
print(list(main()))
```
**Output**: `[0, 1, 2, 3]`

### Q8: send()
```python
def acc():
    total = 0
    while True:
        val = yield total
        total += val
a = acc(); next(a)
print(a.send(10))
print(a.send(20))
```
**Output**: `10`, `30`

### Q9: StopIteration value
```python
def gen():
    yield 1
    return "done"
g = gen(); next(g)
try: next(g)
except StopIteration as e: print(e.value)
```
**Output**: `done`

### Q10: range reuse
```python
r = range(3)
print(list(r))
print(list(r))
```
**Output**: `[0, 1, 2]`, `[0, 1, 2]` — range is iterable (reusable), not iterator!

### Q11: map is lazy
```python
m = map(lambda x: x**2, [1,2,3])
print(type(m))
print(next(m))
```
**Output**: `<class 'map'>`, `1`

### Q12: filter lazy
```python
f = filter(lambda x: x>2, [1,2,3,4,5])
print(list(f))
print(list(f))
```
**Output**: `[3, 4, 5]`, `[]` — filter is an iterator (one-shot)

### Q13: zip stops at shortest
```python
print(list(zip([1,2,3], [4,5])))
```
**Output**: `[(1, 4), (2, 5)]`

### Q14: enumerate
```python
print(list(enumerate("abc", start=1)))
```
**Output**: `[(1, 'a'), (2, 'b'), (3, 'c')]`

### Q15: Infinite generator
```python
def naturals():
    n = 0
    while True:
        yield n; n += 1
from itertools import islice
print(list(islice(naturals(), 5)))
```
**Output**: `[0, 1, 2, 3, 4]`

### Q16: itertools.chain
```python
from itertools import chain
print(list(chain([1,2], [3,4], [5])))
```
**Output**: `[1, 2, 3, 4, 5]`

### Q17: itertools.count
```python
from itertools import count, islice
print(list(islice(count(10, 3), 4)))
```
**Output**: `[10, 13, 16, 19]`

### Q18: itertools.accumulate
```python
from itertools import accumulate
print(list(accumulate([1,2,3,4,5])))
```
**Output**: `[1, 3, 6, 10, 15]`

### Q19: Generator close
```python
def gen():
    try:
        yield 1; yield 2
    finally:
        print("cleanup")
g = gen(); next(g); g.close()
```
**Output**: `cleanup`

### Q20: Dict iteration order
```python
d = {"a":1, "b":2, "c":3}
print(list(d))
```
**Output**: `['a', 'b', 'c']` (insertion order, Python 3.7+)

### Q21-50: (More patterns)

### Q21
```python
it = iter("hello")
print(next(it), next(it))
```
**Output**: `h e`

### Q22
```python
def gen():
    yield from range(3)
    yield from "ab"
print(list(gen()))
```
**Output**: `[0, 1, 2, 'a', 'b']`

### Q23
```python
from itertools import takewhile
print(list(takewhile(lambda x: x<4, [1,2,3,5,2,1])))
```
**Output**: `[1, 2, 3]` — stops at first failure (5)

### Q24
```python
from itertools import dropwhile
print(list(dropwhile(lambda x: x<4, [1,2,3,5,2,1])))
```
**Output**: `[5, 2, 1]` — drops leading matches, keeps rest

### Q25
```python
g = (x for x in range(5))
print(2 in g)
print(3 in g)
print(list(g))
```
**Output**: `True`, `True`, `[4]` — `in` consumes up to the found item!

### Q30
```python
def fibonacci():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a+b
from itertools import islice
print(list(islice(fibonacci(), 8)))
```
**Output**: `[0, 1, 1, 2, 3, 5, 8, 13]`

### Q40
```python
# Late binding trap:
funcs = [lambda: i for i in range(3)]
print([f() for f in funcs])
```
**Output**: `[2, 2, 2]` — all closures share the same `i` (final value)

### Q45
```python
from itertools import groupby
data = "AAABBBCCA"
print([(k, list(g)) for k, g in groupby(data)])
```
**Output**: `[('A',['A','A','A']),('B',['B','B','B']),('C',['C','C']),('A',['A'])]`

### Q50
```python
def gen():
    x = yield 1
    y = yield x + 10
    yield x + y
g = gen()
print(next(g))
print(g.send(5))
print(g.send(20))
```
**Output**: `1`, `15` (x=5, yield 5+10), `25` (y=20, yield 5+20)
