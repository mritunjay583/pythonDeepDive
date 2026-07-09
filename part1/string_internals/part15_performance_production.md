# Part 15 — Performance and Production

## 15.1 Memory Usage Rules of Thumb

```
Per-string overhead:
  ASCII:   49 bytes fixed (even for "" !)
  Non-ASCII: 73 bytes fixed
  
Per-character cost:
  ASCII/Latin-1: 1 byte/char
  BMP (CJK, etc): 2 bytes/char
  Emoji/rare: 4 bytes/char (AND forces ALL chars to 4 bytes!)

Practical calculations:
  100-char ASCII identifier: 49 + 101 = 150 bytes
  100-char Chinese text: 73 + 202 = 275 bytes
  100 chars with 1 emoji: 73 + 404 = 477 bytes (!)
  1 million ASCII chars: 49 + 1,000,001 ≈ 1 MB
  1 million chars + 1 emoji: 73 + 4,000,004 ≈ 4 MB (4× more!)
```

---

## 15.2 Why join() Is Faster Than += (Quantified)

```python
import timeit

words = ["word"] * 10000

# Method 1: += loop
def concat_plus():
    s = ""
    for w in words:
        s += w
    return s

# Method 2: join
def concat_join():
    return "".join(words)

# Benchmarks (typical):
# concat_plus: ~2.5 ms (with refcnt=1 optimization!)
# concat_join: ~0.15 ms
# 
# join is 15-20× faster even WITH the optimization!
# Without optimization (e.g., if refcnt > 1): += is 100-1000× slower.
```

Why even with optimization join wins:
- join: 1 pass to count + 1 allocation + 1 pass to copy = 2n + alloc
- +=: each realloc may need to copy everything (amortized doubling: ~2n copies total)
- BUT: realloc has overhead (free list management, potential data movement)
- AND: join uses memcpy-optimized _PyUnicode_FastCopyCharacters

---

## 15.3 Large Text Processing Patterns

### Pattern 1: Streaming (Never Load Entire File)
```python
# BAD: loads entire file into memory as one giant string
content = open("huge.txt").read()  # 100MB string in memory!

# GOOD: process line by line (constant memory)
with open("huge.txt") as f:
    for line in f:        # ~100 bytes at a time
        process(line)
```

### Pattern 2: Use bytes for Binary/Non-Text Processing
```python
# BAD: decode to str then re-encode (wasteful for protocol parsing)
data = socket.recv(4096)        # bytes
text = data.decode('utf-8')     # str (double memory!)
# ... parse ...
response = result.encode('utf-8')  # back to bytes (triple!)

# GOOD: work in bytes for wire protocols
data = socket.recv(4096)        # bytes
# Parse bytes directly when protocol is binary/ASCII
header_end = data.find(b'\r\n\r\n')
```

### Pattern 3: Intern Repeated Strings from External Data
```python
import sys

# Processing 10M records with 100 unique category values:
# Without interning: 10M string objects × ~80 bytes = ~800 MB
# With interning: 100 unique objects + 10M pointers = ~80 MB

categories = {}
for record in huge_dataset:
    cat = record["category"]
    if cat not in categories:
        categories[cat] = sys.intern(cat)
    record["category"] = categories[cat]  # Share one object
```

### Pattern 4: Pre-compile Patterns
```python
import re

# BAD: re-compiles pattern every iteration
for line in lines:
    if re.search(r'\d{4}-\d{2}-\d{2}', line):
        process(line)

# GOOD: compile once, reuse
pattern = re.compile(r'\d{4}-\d{2}-\d{2}')
for line in lines:
    if pattern.search(line):
        process(line)
```

---

## 15.4 Cache Locality Considerations

```
Processing a list of 1000 short strings:

Each string is a separate heap object at a random address.
Iterating: pointer chase → cache miss → ~100ns latency per miss.
1000 strings × potential cache miss each = significant overhead.

For character-level processing within ONE string:
Characters are contiguous (inline after struct header).
CPU prefetcher handles sequential access well.
One cache line (64 bytes) holds 64 ASCII chars or 16 UCS-4 chars.

Conclusion:
  - Processing within a string: excellent locality
  - Processing across many strings: poor locality
  - For bulk text: one large string > many small strings
```

---

## 15.5 The Kind Widening Tax in Practice

```python
# Real-world impact: JSON processing with occasional emoji

# Pure ASCII JSON (most common): 
json_ascii = '{"name": "Alice", "status": "active"}'
# 1BYTE_KIND, ~86 bytes total

# Same JSON with one emoji:
json_emoji = '{"name": "Alice", "status": "active 😊"}'
# 4BYTE_KIND! ~232 bytes total (2.7× more!)

# At scale (1M such records):
# ASCII: ~86 MB
# With emoji: ~232 MB
# The emoji "costs" 146 MB extra across 1M records!

# Solution: keep emoji in separate strings if possible
status = "active"    # ASCII, efficient
emoji = "😊"         # UCS-4, isolated
# Don't mix them unless necessary
```

---

## 15.6 Profiling String Memory

```python
import sys, tracemalloc
from pympler import asizeof

# Single string measurement:
s = "hello world"
sys.getsizeof(s)        # 60 (header + data, not contents)

# Deep measurement of data structure:
data = [f"item_{i}" for i in range(100000)]
asizeof.asizeof(data)   # Deep recursive size (strings + list)

# Track allocations:
tracemalloc.start()
big_text = open("large.txt").read()
snapshot = tracemalloc.take_snapshot()
stats = snapshot.statistics('filename')
```

---

## 15.7 Production Anti-Patterns

| Anti-Pattern | Problem | Fix |
|---|---|---|
| `s += x` in loop | O(n²) allocation | `"".join(parts)` |
| `"text " + str(num)` | Creates intermediate | `f"text {num}"` |
| Loading entire file | Memory bloat | Stream line-by-line |
| Not interning repeated strings | Memory waste | `sys.intern()` |
| Mixing ASCII + emoji unnecessarily | 4× memory | Separate emoji strings |
| Regex without compile | Repeated compilation | `re.compile()` once |
| Multiple `.replace()` chains | Multiple string copies | Single `re.sub()` or `str.translate()` |
| String for binary data | Decode/encode overhead | Use `bytes` |

---

## 15.8 Interview Questions — Part 15

**Q1**: What's the memory cost of adding one emoji to a 10K-char ASCII string?
**A**: Forces 4BYTE_KIND. Memory goes from ~10,050 bytes (1B/char) to ~40,077 bytes (4B/char). ~4× increase, or ~30KB extra for one emoji.

**Q2**: For a list of 1M short strings, what dominates memory?
**A**: Per-string object overhead (49-73 bytes header each) dominates. 1M × 60 bytes average = ~60MB just for headers, regardless of content length.

**Q3**: When should you use `bytes` instead of `str`?
**A**: Binary protocols, raw file I/O, network data, image processing — anything where the data isn't text. Avoids the overhead of decode/encode and the internal PEP 393 representation.

**Q4**: How can you reduce memory for millions of repeated string values?
**A**: `sys.intern()` the repeated values. 1M references to 100 unique strings: 100 objects + 1M pointers = ~8MB, vs 1M separate objects = ~60MB.

**Q5**: Why is `"".join(generator)` not always optimal?
**A**: join() needs to iterate the sequence TWICE (once to count lengths, once to copy). A generator can only be iterated once. So join() materializes the generator into a list first, adding memory overhead. For generators, `io.StringIO` may be better.
