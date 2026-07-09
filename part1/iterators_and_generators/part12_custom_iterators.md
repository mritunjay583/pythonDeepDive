# Part 12 — Custom Iterators

## 12.1 Building an Iterator Class

```python
class CountDown:
    """Iterator that counts down from n to 1."""
    
    def __init__(self, n):
        self.n = n
    
    def __iter__(self):
        return self  # Iterator IS its own iterable
    
    def __next__(self):
        if self.n <= 0:
            raise StopIteration
        value = self.n
        self.n -= 1
        return value

for x in CountDown(5):
    print(x)  # 5, 4, 3, 2, 1
```

---

## 12.2 Separating Iterable from Iterator

```python
class NumberRange:
    """Iterable: can create multiple independent iterators."""
    
    def __init__(self, start, end):
        self.start = start
        self.end = end
    
    def __iter__(self):
        return NumberRangeIterator(self.start, self.end)

class NumberRangeIterator:
    """Iterator: tracks position, single-use."""
    
    def __init__(self, current, end):
        self.current = current
        self.end = end
    
    def __iter__(self):
        return self
    
    def __next__(self):
        if self.current >= self.end:
            raise StopIteration
        value = self.current
        self.current += 1
        return value

# Multiple independent iterations:
r = NumberRange(1, 4)
for x in r:
    for y in r:        # Creates NEW iterator each time!
        print(x, y)    # All 9 combinations (1,1)(1,2)...(3,3) ✓
```

---

## 12.3 Generator-Based (Simpler)

```python
class NumberRange:
    def __init__(self, start, end):
        self.start = start
        self.end = end
    
    def __iter__(self):
        """Use a generator for the iteration logic!"""
        current = self.start
        while current < self.end:
            yield current
            current += 1

# Same behavior, much less boilerplate!
# __iter__ returns a generator (which IS an iterator automatically)
```

---

## 12.4 Common Mistakes

### Mistake 1: Forgetting `__iter__` returns self for iterators
```python
class BadIter:
    def __next__(self):
        return 42
    # Missing __iter__! → TypeError: 'BadIter' object is not iterable

# Fix: add __iter__ returning self
```

### Mistake 2: Not raising StopIteration
```python
class InfiniteByAccident:
    def __iter__(self): return self
    def __next__(self):
        return "oops"  # Never raises StopIteration!
        # for loop on this will NEVER terminate!
```

### Mistake 3: Reusing an exhausted iterator
```python
it = CountDown(3)
list(it)  # [3, 2, 1]
list(it)  # [] — exhausted! Must create new one.
```

### Mistake 4: Not handling the container reference properly
```python
class BadListIter:
    def __init__(self, lst):
        self.lst = lst  # Holds reference — keeps list alive!
        self.idx = 0
    
    def __next__(self):
        if self.idx >= len(self.lst):
            # SHOULD release reference on exhaustion:
            self.lst = None  # Allow list to be GC'd
            raise StopIteration
        val = self.lst[self.idx]
        self.idx += 1
        return val
```

---

## 12.5 Real-World Custom Iterator: Chunked Reader

```python
class ChunkedReader:
    """Read a file in fixed-size chunks (for binary processing)."""
    
    def __init__(self, filepath, chunk_size=4096):
        self.filepath = filepath
        self.chunk_size = chunk_size
    
    def __iter__(self):
        with open(self.filepath, 'rb') as f:
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    return  # Generator-style: return = StopIteration
                yield chunk

# Usage:
for chunk in ChunkedReader("huge_file.bin", 1024*1024):
    process(chunk)  # 1MB at a time, O(1) memory
```

---

## 12.6 Interview Questions — Part 12

**Q1**: What methods must a class implement to be an iterator? **A**: `__iter__()` (return self) and `__next__()` (return value or raise StopIteration).

**Q2**: Why separate iterable from iterator? **A**: So the iterable can create multiple independent iterators. Nested for loops on the same iterable require independent iteration state.

**Q3**: Can you use a generator inside `__iter__`? **A**: Yes! `__iter__` can be a generator function (contains yield). It returns a generator object which IS an iterator automatically. Much cleaner than writing a separate iterator class.

**Q4**: What should a custom iterator do on exhaustion? **A**: Raise StopIteration, release any held references (allow GC), and remain exhausted on subsequent __next__ calls.
