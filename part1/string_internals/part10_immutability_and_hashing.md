# Part 10 — Immutability and Hashing

## 10.1 Why Strings Must Be Immutable

### Reason 1: Hash Caching Requires Immutability

```c
// The hash is computed ONCE and cached:
Py_hash_t unicode_hash(PyObject *self) {
    Py_hash_t h = _PyASCIIObject_CAST(self)->hash;
    if (h != -1) return h;  // Cached! O(1)!
    
    // Compute hash over character data: O(n)
    h = _Py_HashBytes(PyUnicode_DATA(self),
                      PyUnicode_GET_LENGTH(self) * PyUnicode_KIND(self));
    if (h == -1) h = -2;  // -1 reserved as "not computed" sentinel
    
    _PyASCIIObject_CAST(self)->hash = h;  // Store permanently
    return h;
}
```

If strings were mutable, the cached hash would become stale after modification. Every dict lookup would need to either:
- Recompute the hash (O(n) per lookup — defeats the purpose of hash tables)
- Invalidate the cache on every mutation (complex, error-prone)

Immutability guarantees: **compute once, use forever**.

### Reason 2: Safe Dict Keys

```python
# Hypothetical mutable string disaster:
key = MutableString("hello")
d = {key: "value"}       # Stored at hash("hello") → slot X
key.modify("world")      # Hash changes! hash("world") → slot Y
d[key]                   # Looks at slot Y → KeyError!
# The value is at slot X but we're looking at Y!
# Data is LOST in the dict!
```

Immutability makes strings safe dict keys by construction.

### Reason 3: Safe Sharing (Interning + Aliasing)

```python
a = "hello"
b = a        # Both point to same object (alias)
# If mutable: a[0] = 'H' would modify b too!
# Immutability means sharing is always safe — no defensive copies needed.

# Interning relies on this:
a = "hello"  # interned → shared singleton
b = "hello"  # same singleton
# If mutable, modifying a would corrupt b and ALL other "hello" references!
```

### Reason 4: Thread Safety Without Locks

```python
# Multiple threads can read the same string simultaneously:
shared_config = "production"  # Immutable — no race conditions possible
# No locks needed for concurrent reads!
# If mutable: would need mutex for every read/write.
```

### Reason 5: Enable Compiler Optimizations

```python
# The compiler can freely:
# - Share string constants between modules
# - Reuse string literals without copying
# - Intern identifier strings
# - Pre-compute hashes at compile time
# None of these are safe with mutable strings.
```

---

## 10.2 The Hash Algorithm: SipHash-1-3

CPython uses SipHash with parameters (c=1, d=3):
- c = compression rounds per message block
- d = finalization rounds

### Why SipHash (not FNV, djb2, MurmurHash)?

| Property | SipHash | FNV/djb2 | MurmurHash |
|----------|---------|----------|------------|
| Collision resistance | Cryptographic | Weak | Medium |
| HashDoS protection | ✓ (keyed) | ✗ | ✗ |
| Speed (short strings) | Fast | Fastest | Fast |
| Speed (long strings) | Fast | Fast | Fastest |
| Keyed (randomizable) | ✓ | ✗ | ✗ |

SipHash was chosen after the 2011 HashDoS attacks demonstrated that predictable hashes allow DoS attacks on web servers.

### The Random Key

```c
// At interpreter startup:
typedef struct {
    uint64_t k0;  // 64-bit random key part 1
    uint64_t k1;  // 64-bit random key part 2
} _Py_HashSecret_t;

// Generated from OS entropy:
_Py_HashSecret_t _Py_HashSecret;
// Read from /dev/urandom (Linux) or CryptGenRandom (Windows)
```

Same string → different hash in different processes:
```bash
$ python3 -c "print(hash('hello'))"
3258847587227523361

$ python3 -c "print(hash('hello'))"
-7839837882888834671  # DIFFERENT! New process, new random key.
```

### SipHash Algorithm (simplified):

```
Input: message bytes M, key (k0, k1)
State: four 64-bit words (v0, v1, v2, v3)

1. Initialize state from key:
   v0 = k0 ^ 0x736f6d6570736575
   v1 = k1 ^ 0x646f72616e646f6d
   v2 = k0 ^ 0x6c7967656e657261
   v3 = k1 ^ 0x7465646279746573

2. For each 8-byte block of message:
   v3 ^= block
   SipRound() × 1  (c=1 compression round)
   v0 ^= block

3. Finalization:
   v2 ^= 0xff
   SipRound() × 3  (d=3 finalization rounds)
   
4. Return v0 ^ v1 ^ v2 ^ v3

SipRound:
   v0 += v1; v1 = ROTL(v1, 13); v1 ^= v0; v0 = ROTL(v0, 32);
   v2 += v3; v3 = ROTL(v3, 16); v3 ^= v2;
   v0 += v3; v3 = ROTL(v3, 21); v3 ^= v0;
   v2 += v1; v1 = ROTL(v1, 17); v1 ^= v2; v2 = ROTL(v2, 32);
```

---

## 10.3 Hash Caching in Practice

```python
import sys

s = "a" * 1000000  # 1M character string

# First hash: O(n) — must process all 1M characters
%timeit hash(s)  # ~500 μs (first call, computes SipHash)

# After first call, hash is cached in the object:
%timeit hash(s)  # ~50 ns (returns cached value from struct field!)

# 10,000× speedup for repeated hash operations!
```

### Impact on Dict Performance:

```python
d = {}
key = "a" * 1000  # Long string key

# First insertion: hash computed → O(n)
d[key] = "value"

# All subsequent lookups: hash cached → O(1) for the hash part
for _ in range(1000000):
    _ = d[key]  # Each lookup uses cached hash — only compares chars if hash matches
```

---

## 10.4 The hash == -1 Sentinel Issue

```python
# -1 is used internally as "hash not computed yet"
# If SipHash naturally produces -1, CPython changes it to -2:

hash_value = siphash(data)
if (hash_value == -1):
    hash_value = -2  // Avoid collision with sentinel

# This means hash(s) == -1 is almost impossible from Python
# (would require a contrived __hash__ override)

# Fun fact: since hash(int) = int for small ints:
hash(-1)  # Returns -2 in CPython! (because -1 is the sentinel)
hash(-2)  # Also returns -2! (identity: hash(n) = n for small ints, but -1→-2)
# This creates a known (harmless) collision.
```

---

## 10.5 Immutability and the Buffer Protocol

Strings do NOT export a writable buffer:
```python
s = "hello"
memoryview(s)  # TypeError: cannot make memory view for str

# Why?
# 1. The internal representation (1/2/4 byte) is an implementation detail
# 2. Exposing raw bytes would leak the internal kind
# 3. A writable view would violate immutability
# 4. Different Python versions might use different internal layouts

# For buffer access, use bytes:
b = b"hello"
mv = memoryview(b)  # Works (read-only view of bytes)
```

---

## 10.6 Immutability Enables Copy Elimination

Because strings can't change, many operations can avoid copying:

```python
s = "hello world"

# Full slice — returns SAME object (no copy needed!):
t = s[:]
t is s  # True! CPython returns the same immutable object.

# Identity is preserved through operations that "don't change" the string:
s = "HELLO"
t = s.upper()  # s is already uppercase...
t is s  # Might be True! CPython can detect no-op and return original.

# Concatenation with empty string:
s = "hello"
t = s + ""
t is s  # Might be True! CPython may optimize.

# Multiplication by 1:
t = s * 1
t is s  # Might be True!
```

These optimizations are ONLY safe because the returned object can never be mutated.

---

## 10.7 Interview Questions — Part 10

**Q1**: Why does CPython cache the hash inside the string object?
**A**: Because strings are immutable — the hash never changes. Computing once (O(n)) and caching gives all subsequent hash() calls O(1). Critical for dict performance since strings are the most common dict key type.

**Q2**: What hash algorithm does CPython use for strings?
**A**: SipHash-1-3 with a random 128-bit key generated at process startup. Chosen for collision resistance against HashDoS attacks while maintaining good performance for short strings.

**Q3**: Why is hash("hello") different every time you restart Python?
**A**: Hash randomization. The SipHash key is randomly generated at interpreter startup from OS entropy. Without knowing the key, attackers can't craft strings with colliding hashes.

**Q4**: What is the hash value -1 used for internally?
**A**: Sentinel meaning "hash not yet computed." If SipHash naturally produces -1, CPython stores -2 instead. This is why `hash(-1) == -2` in CPython.

**Q5**: Why can't strings export a writable memoryview?
**A**: Three reasons: (1) would violate immutability, (2) would expose the internal kind (1/2/4 byte) which is an implementation detail, (3) the internal layout may change between Python versions.

**Q6**: How does immutability enable CPython to return the same object from `s[:]`?
**A**: Since `s` can never be modified, returning the same object from `s[:]` is semantically indistinguishable from returning a copy. The "copy" and original behave identically forever — so why waste memory on a real copy?
