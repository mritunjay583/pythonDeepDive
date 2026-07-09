# Part 2 — Hash Functions

## 2.1 What is a Hash Function?

A hash function maps an arbitrary input to a fixed-size integer:

```
hash: Universe of Keys → {0, 1, 2, ..., 2^64 - 1}

hash("hello")   → 2314058222102390712
hash(42)        → 42
hash((1, 2, 3)) → 529344067295497451
hash(3.14)      → 322818021289917443
```

Properties of a good hash function:
1. **Deterministic**: same input always produces same output
2. **Uniform distribution**: outputs spread evenly across the range
3. **Avalanche effect**: small input changes cause large output changes
4. **Fast to compute**: O(1) for fixed-size inputs, O(n) for strings

---

## 2.2 Python's `hash()` Built-in

```python
>>> hash("hello")
-1556830207       # (varies per process due to randomization!)

>>> hash(42)
42                # Small integers hash to themselves

>>> hash(42.0)
42                # Float equal to int → same hash (required!)

>>> hash((1, 2, 3))
529344067295497451

>>> hash([1, 2, 3])
TypeError: unhashable type: 'list'
```

### The hash/equality contract:

```python
# RULE: if a == b, then hash(a) == hash(b)
# This MUST hold, or dict lookup breaks

hash(42) == hash(42.0)     # True (because 42 == 42.0)
hash(1) == hash(True)      # True (because 1 == True)
```

---

## 2.3 Hash Functions for Different Types

### Integers

```python
# For small integers (fits in one C long):
hash(n) = n    (identity function!)

# Why? It's fast and provides perfect distribution for sequential keys.
# Special case: hash(-1) = -2 (because -1 is reserved as error indicator in C)

hash(0)  → 0
hash(1)  → 1
hash(42) → 42
hash(-1) → -2   # Special case!
hash(-2) → -2   # Collision with -1's hash (rare, harmless)
```

For large integers (multi-digit PyLongObject):
```
hash(n) = n mod MERSENNE_PRIME
where MERSENNE_PRIME = 2^61 - 1 (on 64-bit)
```

### Strings

Strings use **SipHash** (since Python 3.4):
```python
hash("hello")  # Result varies per process (randomized!)
hash("")       # 0 (special case)
```

### Tuples

```python
# Tuples hash by combining hashes of all elements
# Uses xxHash-based algorithm (Python 3.8+)
hash((a, b, c)) = combine(hash(a), hash(b), hash(c))
```

### Floats

```python
# Floats use their binary representation
# But: hash(float_x) == hash(int_x) when float_x == int_x
hash(3.0) == hash(3)  # True! Required by hash contract
```

### None

```python
hash(None)  # Some fixed value (implementation defined, randomized)
```

---

## 2.4 SipHash: Python's String Hashing Algorithm

Since Python 3.4, strings are hashed using **SipHash-1-3** (a keyed hash function).

### Why SipHash?

Before Python 3.3, strings used a simple FNV-like hash:
```c
// OLD (vulnerable) hash for strings:
static long string_hash(PyObject *self) {
    unsigned char *p = (unsigned char *)str;
    long x = *p << 7;
    while (--len >= 0)
        x = (1000003 * x) ^ *p++;
    x ^= original_length;
    return x;
}
```

This was **predictable** — an attacker could craft strings that all hash to the same value, creating O(n²) denial-of-service attacks on web servers.

### The Attack (2011-2012)

```
Scenario: Web server receives POST data as key-value pairs → stored in dict

Attack: Send thousands of keys that all hash to same slot:
  key1 → index 5
  key2 → index 5 (collision, probe to 6)
  key3 → index 5 (collision, probe to 7)
  ...
  key_n → index 5 (collision, probe to n+4)

Inserting n keys takes: 1 + 2 + 3 + ... + n = O(n²)
With 100,000 keys: billions of operations → server hangs!
```

This affected Python, Ruby, PHP, Java, and many other languages.

### SipHash Solution

SipHash is a **keyed** hash function:
```
SipHash(key, message) → 64-bit hash

- "key" is a random 128-bit secret generated at process start
- Different process → different key → different hash values
- Attacker can't predict hash values without knowing the key
- Crafting collisions becomes computationally infeasible
```

Properties:
- Cryptographically strong against collision attacks
- Fast for short strings (optimized for hash table use)
- 1-3 variant (1 compression round, 3 finalization rounds) balances speed/security

---

## 2.5 Hash Randomization

Since Python 3.3, hash values are **randomized per process**:

```bash
$ python3 -c "print(hash('hello'))"
-1556830207

$ python3 -c "print(hash('hello'))"
735823487          # DIFFERENT! New process, new random seed

$ PYTHONHASHSEED=0 python3 -c "print(hash('hello'))"
-8115687834685505957   # Fixed seed → reproducible (for testing)
```

### How It Works

At interpreter startup:
```c
// Python/bootstrap_hash.c
// Generate random seed from OS entropy source
_Py_HashSecret_t _Py_HashSecret;

void _Py_HashRandomization_Init(void) {
    // Read 24 bytes from /dev/urandom (Linux) or CryptGenRandom (Windows)
    // Store as the SipHash key
}
```

### What's Randomized vs Not:

| Type | Randomized? | Notes |
|------|-------------|-------|
| str | Yes | SipHash with random key |
| bytes | Yes | SipHash with random key |
| int | No | `hash(n) = n` (deterministic) |
| float | No | Based on binary representation |
| tuple | Yes* | Combines element hashes (str elements → randomized) |
| frozenset | Yes* | Based on element hashes |

### Implications for Developers:

```python
# DON'T rely on hash values being consistent across runs:
hash("hello")  # Different every time you restart Python!

# DON'T persist hash values (e.g., in files or databases)
# DON'T use hash() for cryptographic purposes (use hashlib)

# DO use PYTHONHASHSEED=fixed_value for reproducible testing
```

---

## 2.6 The Collision Attack in Detail

### Constructing Collisions (pre-SipHash)

With the old FNV hash, the hash was a simple polynomial:
```
hash(s) = s[0]*M^(n-1) + s[1]*M^(n-2) + ... + s[n-1]  (mod 2^64)
where M = 1000003
```

An attacker could solve for strings that produce the same hash:
```python
# Two strings with same hash under old algorithm:
# "Aa" and "BB" had the same hash
# Then "AaAa", "AaBB", "BBAa", "BBBB" all had the same hash
# Exponential number of collisions constructable!
```

### Why This Matters in Production

```python
# Django/Flask web server processing form data:
form_data = dict(request.POST)  # Keys from user input!

# If attacker sends 100,000 crafted keys that all collide:
# Dict insertion becomes O(n²) = 10,000,000,000 operations
# Server CPU pegged at 100% for minutes
# One HTTP request = denial of service!
```

SipHash makes this attack computationally infeasible (would require breaking SipHash).

---

## 2.7 Hash Table Index Calculation

The hash value is a large integer. We need a table index:

```
index = hash(key) % table_size

But: modulo is slow! CPython uses a power-of-2 table size:
table_size = 2^n

index = hash(key) & (table_size - 1)    ← bitwise AND (fast!)

Example:
hash("hello") = 0x...1A3F  (some 64-bit value)
table_size = 8 = 2^3
mask = 7 = 0b111

index = hash & mask = 0x1A3F & 0b111 = last 3 bits
```

Why power-of-2 sizes:
- Bitwise AND is much faster than modulo division
- CPython always keeps table size as a power of 2
- Trade-off: must ensure hash function distributes well across low bits

---

## 2.8 Hash Quality Metrics

### Good Distribution

```
Keys: ["key0", "key1", "key2", ..., "key99"]
Table size: 128

Good hash → spread across slots 0-127 roughly uniformly
Bad hash  → cluster in a few slots → long probe chains
```

### Avalanche Effect

```
hash("hello") = 0x7F3A891C22E4D5B1
hash("hellp") = 0xC4D8E12F98A37B64   ← completely different!

One character change → ~50% of bits flip
This prevents clustering of similar keys
```

### CPython's Approach for `hash(int)`:

Since `hash(n) = n`, sequential integers 0,1,2,3... map to consecutive slots:
```
hash(0) % 8 = 0
hash(1) % 8 = 1
hash(2) % 8 = 2
...
hash(7) % 8 = 7
```

This is actually **perfect** for sequential integer keys (zero collisions). The perturbation-based probing handles the cases where this pattern breaks down.

---

## 2.9 Custom Hash Functions

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y
    
    def __hash__(self):
        return hash((self.x, self.y))  # Delegate to tuple hash
```

Rules for implementing `__hash__`:
1. If `__eq__` is defined, `__hash__` MUST be defined (or set to None)
2. `a == b` must imply `hash(a) == hash(b)`
3. Hash should be fast to compute
4. Hash should distribute well

```python
# BAD: constant hash (everything collides!)
def __hash__(self): return 0

# BAD: only uses one field (poor distribution)
def __hash__(self): return hash(self.x)

# GOOD: combines all relevant fields
def __hash__(self): return hash((self.x, self.y))

# GOOD: XOR with bit mixing
def __hash__(self): return hash(self.x) ^ (hash(self.y) << 16)
```

---

## 2.10 Special Hash Values in CPython

```c
// In CPython, these hash values have special meaning:
#define HASH_UNSET    -1    // Object hasn't been hashed yet (cached hash)
// Note: if hash(x) naturally equals -1, CPython changes it to -2

// That's why:
// hash(-1) → -2  (the only integer whose hash differs from its value)
```

```python
>>> hash(-1)
-2
>>> hash(-2)
-2
# Both -1 and -2 have hash value -2!
# This is a known (harmless) collision caused by the -1 sentinel.
```

---

## 2.11 Performance of Hash Computation

| Type | Hash Time | Notes |
|------|-----------|-------|
| Small int | O(1) | Identity: hash(n) = n |
| Large int | O(digits) | Modular reduction |
| str | O(len) first time, O(1) cached | SipHash computed once, cached in object |
| bytes | O(len) | SipHash, not cached |
| tuple | O(elements) | Combines element hashes |
| float | O(1) | Based on binary representation |
| None | O(1) | Pre-computed constant |
| frozenset | O(elements) | XOR of sorted element hashes |

**String hash caching**: Once computed, a string's hash is stored in the object:
```c
typedef struct {
    // ... PyUnicodeObject fields ...
    Py_hash_t hash;     // -1 if not computed yet, cached value otherwise
} PyUnicodeObject;
```

This means the first `hash("hello")` costs O(5) but subsequent calls cost O(1).

---

## 2.12 Interview Questions — Part 2

**Q1**: Why does Python randomize hash values?
**A**: To prevent algorithmic complexity attacks (HashDoS). Without randomization, attackers can craft inputs that all hash to the same slot, making dict operations O(n²) and enabling denial-of-service.

**Q2**: What hash function does CPython use for strings?
**A**: SipHash-1-3 with a random 128-bit key generated at process startup.

**Q3**: Why is `hash(-1) == -2` in CPython?
**A**: CPython uses -1 as an internal error indicator in the C API. If a hash naturally computes to -1, it's changed to -2 to avoid confusion with the error signal.

**Q4**: Why must `hash(42) == hash(42.0)`?
**A**: Because `42 == 42.0` is True. The hash contract requires equal objects to have equal hashes, or dict lookup would break (insert with int key, can't find with float key).

**Q5**: Can you use `hash()` for security (like password hashing)?
**A**: Absolutely not. `hash()` is not cryptographic — it's designed for speed, not irreversibility. Use `hashlib.sha256` or `bcrypt` for security.

**Q6**: Why does CPython use power-of-2 table sizes?
**A**: So that index computation (`hash & (size-1)`) uses a fast bitwise AND instead of slow modulo division.

**Q7**: Is the hash of a string computed every time you call `hash(s)`?
**A**: No. The first call computes and caches it inside the string object. Subsequent calls return the cached value in O(1).
