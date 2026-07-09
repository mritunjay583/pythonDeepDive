# Part 8 — Hashability

## 8.1 The Rule

> An object is **hashable** if it has a hash value that never changes during its lifetime, and can be compared to other objects.

More precisely, an object is hashable if:
1. It implements `__hash__()` (returns an integer)
2. It implements `__eq__()` (for comparison)
3. The hash value NEVER changes while the object is alive
4. If `a == b`, then `hash(a) == hash(b)` (hash-equality contract)

---

## 8.2 Why Immutable Objects Are Hashable

Immutability guarantees that the hash value never changes:

```python
# String: immutable → hashable
s = "hello"
hash(s)  # Always the same for this object's lifetime
# Can't modify s → hash can't change → safe for dict keys

# Tuple (of hashables): immutable → hashable
t = (1, 2, 3)
hash(t)  # Stable forever

# Integer: immutable → hashable
n = 42
hash(n)  # Always 42
```

If the hash COULD change, dict lookup would break:
```python
# Hypothetical: if lists were hashable
d = {}
key = [1, 2, 3]
d[key] = "value"       # hash([1,2,3]) → slot 5
key.append(4)          # Mutation changes the hash!
d[key]                 # hash([1,2,3,4]) → slot 2 → KeyError!
# The value is still at slot 5 but we're looking at slot 2!
```

---

## 8.3 Why Lists Are NOT Hashable

```python
>>> hash([1, 2, 3])
TypeError: unhashable type: 'list'
```

Lists are mutable. If we allowed hashing:
1. Insert `[1,2,3]` as dict key → stored at slot determined by hash([1,2,3])
2. Mutate the list (it's mutable!) → hash changes
3. Lookup the "same" key → different hash → different slot → key lost!

**The design choice**: Python makes mutable containers unhashable to prevent silent data corruption.

---

## 8.4 Hashability Rules by Type

| Type | Hashable | Why |
|------|----------|-----|
| int | Yes | Immutable |
| float | Yes | Immutable |
| str | Yes | Immutable |
| bytes | Yes | Immutable |
| bool | Yes | Immutable (subclass of int) |
| None | Yes | Singleton, immutable |
| tuple | Yes* | *Only if ALL elements are hashable |
| frozenset | Yes | Immutable set |
| list | No | Mutable |
| dict | No | Mutable |
| set | No | Mutable |
| bytearray | No | Mutable |

```python
hash((1, 2, 3))           # OK — all elements hashable
hash((1, [2, 3]))         # TypeError! List inside tuple → unhashable
hash(frozenset({1, 2}))   # OK
hash({1, 2})              # TypeError! Set is mutable
```

---

## 8.5 `__hash__` and `__eq__` Protocol

### Default Behavior (no custom __eq__):

Every object has a default `__hash__` = `id(obj)`:
```python
class Foo:
    pass

a = Foo()
b = Foo()
hash(a) != hash(b)  # True (different objects → different hashes)
a == b               # False (default __eq__ uses identity)
```

### When You Define `__eq__`:

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

# Python automatically sets __hash__ = None!
p = Point(1, 2)
hash(p)  # TypeError: unhashable type: 'Point'

# WHY? Because if two Points can be __eq__, they MUST have same hash.
# But the default hash (based on id) doesn't satisfy this:
p1 = Point(1, 2)
p2 = Point(1, 2)
# p1 == p2 is True, but id(p1) != id(p2), so default hash would differ!
# This violates the contract → Python disables __hash__ as safety measure.
```

### Implementing Both Correctly:

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    
    def __eq__(self, other):
        if not isinstance(other, Point):
            return NotImplemented
        return self.x == other.x and self.y == other.y
    
    def __hash__(self):
        return hash((self.x, self.y))

# Now it works:
p1 = Point(1, 2)
p2 = Point(1, 2)
p1 == p2          # True
hash(p1) == hash(p2)  # True ← contract satisfied!

d = {p1: "origin"}
d[p2]  # "origin" — works because p1 == p2 and hash(p1) == hash(p2)
```

---

## 8.6 Common __hash__ Patterns

### Pattern 1: Delegate to Tuple

```python
def __hash__(self):
    return hash((self.x, self.y, self.z))
```
Best for objects with a few hashable fields. Leverages Python's optimized tuple hash.

### Pattern 2: XOR (use cautiously)

```python
def __hash__(self):
    return hash(self.x) ^ hash(self.y)
```
Problem: `hash((a, b)) == hash((b, a))` — commutative, loses order info.
`Point(1, 2)` and `Point(2, 1)` would collide!

### Pattern 3: For Data Classes

```python
from dataclasses import dataclass

@dataclass(frozen=True)  # frozen → immutable → hashable
class Point:
    x: float
    y: float
    # __hash__ and __eq__ auto-generated correctly!
```

### Pattern 4: Explicit Unhashable

```python
class MutableThing:
    def __eq__(self, other):
        ...
    
    __hash__ = None  # Explicitly unhashable
```

---

## 8.7 Mutable Objects That Define __hash__ (Dangerous!)

```python
class BadIdea:
    def __init__(self, value):
        self.value = value
    
    def __hash__(self):
        return hash(self.value)  # Based on mutable state!
    
    def __eq__(self, other):
        return self.value == other.value

# Disaster:
obj = BadIdea(42)
d = {obj: "found"}     # hash(obj) = 42 → stored at some slot
obj.value = 99          # MUTATED! hash is now 99!
d[obj]                  # KeyError! Looking at wrong slot!
d[BadIdea(42)]          # KeyError! Old slot, but obj.value changed!

# The original entry is unreachable — a "ghost" in the dict!
```

**Rule**: If your object defines `__hash__`, the fields used in `__hash__` and `__eq__` MUST be immutable.

---

## 8.8 Hash Value Caching

For immutable types, CPython caches the hash:

```c
// String object:
typedef struct {
    // ...
    Py_hash_t hash;  // -1 if not yet computed, cached value otherwise
} PyUnicodeObject;

// On first hash() call: compute and cache
// On subsequent calls: return cached value immediately
```

```python
s = "hello" * 1000  # Long string
# First hash(s): O(len(s)) — computes SipHash over 5000 chars
# Second hash(s): O(1) — returns cached value
```

For custom objects, you can cache manually:
```python
class CachedHash:
    def __init__(self, data):
        self._data = tuple(data)  # Immutable
        self._hash = None         # Cache
    
    def __hash__(self):
        if self._hash is None:
            self._hash = hash(self._data)
        return self._hash
```

---

## 8.9 frozenset and Frozen Dataclasses

### frozenset:

```python
fs = frozenset({1, 2, 3})
hash(fs)  # Valid! Computed from sorted element hashes

# frozenset hash algorithm:
# XOR of all element hashes with a mixing function
# Order-independent (same set of elements → same hash regardless of iteration order)
```

### Frozen Dataclass:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    host: str
    port: int
    debug: bool = False

# Auto-generates:
# __eq__ based on all fields
# __hash__ based on all fields (using tuple hash)
# Prevents attribute assignment (truly immutable)

c = Config("localhost", 8080)
d = {c: "production"}  # Works!
c.port = 9090          # FrozenInstanceError! Can't mutate
```

---

## 8.10 The `object.__hash__` Default

```python
class Foo:
    pass

# Default __hash__ for objects:
# CPython: based on id() (memory address), with some bit mixing
# Guaranteed unique per object (no collisions from default hash)
# But: different objects with same "value" get different hashes

a = Foo()
b = Foo()
hash(a) != hash(b)  # True (almost certainly)
```

The default is `id(obj) / 16` (shifted to mix bits better for the hash table), implementation-specific.

---

## 8.11 Interview Questions — Part 8

**Q1**: Why are Python lists unhashable?
**A**: Lists are mutable. If they could be hashed and used as dict keys, mutating the list would change its hash, making it impossible to find in the dict. This would cause silent data loss.

**Q2**: What happens if you define `__eq__` without `__hash__`?
**A**: Python sets `__hash__ = None`, making the class unhashable. This is a safety measure because the default hash (based on id) wouldn't satisfy the contract: equal objects must have equal hashes.

**Q3**: Can a tuple always be used as a dict key?
**A**: Only if ALL its elements are hashable. `hash((1, "a", (2, 3)))` works. `hash((1, [2, 3]))` raises TypeError because the list element is unhashable.

**Q4**: What is the hash-equality contract?
**A**: If `a == b`, then `hash(a) == hash(b)`. The converse is NOT required — different objects can have the same hash (collisions are allowed).

**Q5**: How do you make a custom class hashable?
**A**: Implement both `__hash__` and `__eq__`. Use only immutable fields in the computation. Or use `@dataclass(frozen=True)` which auto-generates both correctly.

**Q6**: Why does `hash(-1) == hash(-2) == -2` in CPython?
**A**: CPython uses -1 as an internal "not computed yet" sentinel. If any hash naturally equals -1, it's changed to -2 to avoid confusion. This creates a known collision between -1 and -2.

**Q7**: What's the difference between `set` and `frozenset` for hashability?
**A**: `set` is mutable → unhashable. `frozenset` is immutable → hashable. You can use a frozenset as a dict key or set element, but not a regular set.
