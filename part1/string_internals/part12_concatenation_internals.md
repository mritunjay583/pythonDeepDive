# Part 12 — Concatenation Internals

## 12.1 The O(n²) Problem

```python
# The classic anti-pattern:
result = ""
for word in words:    # n words of average length m
    result += word    # Each += creates a NEW string!

# Cost analysis:
# Iteration 1: copy 0 + m chars → total work: m
# Iteration 2: copy m + m chars → total work: 2m
# Iteration 3: copy 2m + m chars → total work: 3m
# ...
# Iteration n: copy (n-1)m + m chars → total work: nm
# TOTAL: m(1 + 2 + 3 + ... + n) = m × n(n+1)/2 = O(n²m)
```

For 10,000 words averaging 10 chars: ~500 million character copies!

---

## 12.2 CPython's Refcount==1 Optimization (The "String += Hack")

CPython detects when a string has refcount=1 (only one reference exists) and tries to extend it in-place using `realloc`:

```c
// ceval.c — BINARY_ADD / INPLACE_ADD for strings (simplified):
static PyObject *
unicode_concatenate(PyObject *v, PyObject *w, ...)
{
    // Check if we can modify v in-place:
    if (Py_REFCNT(v) == 1 &&          // Only one reference
        !PyUnicode_CHECK_INTERNED(v) && // Not interned (can't modify shared)
        PyUnicode_CheckExact(v))         // Exact str type (not subclass)
    {
        // Try to resize v in-place via realloc:
        Py_ssize_t new_len = len_v + len_w;
        if (unicode_resize(&v, new_len) == 0) {
            // Realloc succeeded! Copy w's data to the end:
            _PyUnicode_FastCopyCharacters(v, len_v, w, 0, len_w);
            return v;  // Same pointer (or moved by realloc), no new object!
        }
    }
    // Fallback: normal concatenation (allocate new string)
    return PyUnicode_Concat(v, w);
}
```

### When This Optimization Works:

```python
# WORKS (refcount == 1):
result = ""
for word in words:
    result += word      # result has refcount 1 → realloc in-place!
# Amortized O(n) if realloc extends in place!

# DOESN'T WORK (refcount > 1):
result = ""
saved = result          # refcount == 2!
for word in words:
    result += word      # refcount > 1 → can't realloc → new object each time
# Back to O(n²)!

# DOESN'T WORK (interned):
result = "hello"        # "hello" is interned! Can't modify!
result += " world"      # Must create new object
```

### Why It's Not Reliable:

```python
# Many things increase refcount without you knowing:
result = ""
log.debug(f"Building: {result}")  # Oops! result was passed to format → refcnt > 1
for word in words:
    result += word       # Optimization LOST for this iteration!

# The optimization is a HEURISTIC, not a guarantee.
# NEVER rely on it for performance-critical code.
# ALWAYS use "".join() for building strings.
```

---

## 12.3 `"".join()` — The Correct Approach

```python
words = ["hello", "world", "foo", "bar"]
result = " ".join(words)
```

### Why join() is Always O(n):

```
Phase 1: iterate sequence, sum lengths → O(k) where k = number of items
Phase 2: ONE allocation of exact final size → O(1)
Phase 3: copy all items + separators sequentially → O(total_chars)

Total: O(total_output_length) — ONE allocation, ONE copy pass.
No intermediate strings. No reallocation. No wasted copies.
```

### Comparison:

```
10,000 words × 10 chars each:

"+= loop" (without optimization):
  Allocations: 10,000 intermediate strings
  Total chars copied: ~50 million (quadratic sum)
  Time: ~50 ms

"+= loop" (WITH refcnt=1 optimization):
  Allocations: ~20 reallocs (amortized growth)
  Total chars copied: ~200,000 (amortized linear)
  Time: ~5 ms
  BUT: fragile! Can degrade to O(n²) unexpectedly.

"".join():
  Allocations: 1 (exact size)
  Total chars copied: 100,000 (exactly once each)
  Time: ~1 ms
  ALWAYS reliable.
```

---

## 12.4 BUILD_STRING Bytecode (f-strings)

f-strings compile to a sequence of `FORMAT_VALUE` + `BUILD_STRING`:

```python
name, age = "Alice", 30
s = f"Name: {name}, Age: {age}"
```

Bytecode:
```
LOAD_CONST     "Name: "
LOAD_FAST      name
FORMAT_VALUE   0
LOAD_CONST     ", Age: "
LOAD_FAST      age
FORMAT_VALUE   0
BUILD_STRING   4
```

`BUILD_STRING` works like `"".join()` but without creating a list:
```c
// ceval.c (BUILD_STRING):
// 1. Sum lengths of all n pieces on stack
// 2. Find max char across all pieces
// 3. ONE allocation for final string
// 4. Copy all pieces sequentially
// Result: O(total_length), single allocation
```

This is why f-strings are the fastest string construction method.

---

## 12.5 io.StringIO for Complex Building

```python
import io

buf = io.StringIO()
for record in large_dataset:
    buf.write(f"{record.name},{record.value}\n")
result = buf.getvalue()
```

StringIO uses an internal buffer that grows with doubling strategy:
- Write operations: amortized O(1) (like list.append)
- Final getvalue(): O(n) — creates one string from buffer

Good for: complex conditional building where join() isn't practical.

---

## 12.6 Concatenation Kind Promotion Cost

When concatenating strings of different kinds, the narrower string must be "widened":

```python
ascii_part = "Hello "                # 1BYTE, 6 chars × 1 byte = 6 bytes data
emoji_part = "😀"                    # 4BYTE, 1 char × 4 bytes = 4 bytes data
result = ascii_part + emoji_part     # 4BYTE, 7 chars × 4 bytes = 28 bytes data!

# The 6 ASCII characters are each expanded from 1 byte to 4 bytes:
# 'H' goes from [0x48] to [0x00000048]
# This widening is the hidden cost of mixed-kind concatenation.
```

---

## 12.7 Best Practices Summary

```python
# WORST: repeated concatenation
s = ""
for x in items:
    s += str(x) + ","

# BAD: repeated concatenation (even if refcnt optimization helps sometimes)
s = ""
for x in items:
    s = s + str(x) + ","

# GOOD: join with generator
s = ",".join(str(x) for x in items)

# GOOD: f-string for fixed number of parts
s = f"{a},{b},{c}"

# GOOD: StringIO for complex conditional building
buf = io.StringIO()
for x in items:
    if condition(x):
        buf.write(format_special(x))
    else:
        buf.write(str(x))
    buf.write(",")
s = buf.getvalue()

# GOOD: list + join (explicit accumulation)
parts = []
for x in items:
    parts.append(str(x))
s = ",".join(parts)
```

---

## 12.8 Interview Questions — Part 12

**Q1**: Why is `result += word` in a loop O(n²)?
**A**: Each concatenation creates a new string and copies ALL previous content. Total copies: 1+2+3+...+n = O(n²). The string grows but must be copied entirely each time because strings are immutable.

**Q2**: What is CPython's refcount==1 optimization for string concatenation?
**A**: When a string has refcount 1 (only one reference), CPython tries `realloc` to extend it in place instead of creating a new object. If realloc succeeds without moving, the cost is just copying the appended part. Makes += closer to O(n) amortized.

**Q3**: When does the refcount==1 optimization fail?
**A**: When refcount > 1 (another variable references the string), when the string is interned, when it's a str subclass, or when realloc can't extend in place and must move the entire block.

**Q4**: How does BUILD_STRING (f-strings) work?
**A**: Calculates total length of all parts on the stack, determines max kind, allocates ONE result string of exact size, copies all parts in order. Like join() but without creating an intermediate list.

**Q5**: When should you use io.StringIO over join()?
**A**: When the building logic is complex (conditionals, loops with different formatting, incremental writes). StringIO provides a file-like write interface with amortized O(1) appends, then O(n) final getvalue().
