# Part 6 — Object Identity: id() and Memory Addresses

## 6.1 What id() Returns in CPython

The Python language specification says:
> `id(obj)` returns an integer that is **unique and constant** for this object during its lifetime. Two objects with non-overlapping lifetimes may have the same id().

**CPython implementation detail**: `id()` returns the **memory address** of the object (as an integer).

```c
// Python/bltinmodule.c
static PyObject *
builtin_id(PyModuleDef *self, PyObject *v) {
    return PyLong_FromVoidPtr(v);
    //     ^^^^^^^^^^^^^^^^^^^^^^^^^
    //     Casts the PyObject* pointer to an integer
}
```

This is the simplest possible identity implementation — the object's position in memory IS its identity.

---

## 6.2 Why Memory Address Works as Identity

For `id()` to satisfy the language spec, it must be:
1. **Unique**: No two live objects have the same address ✓ (non-overlapping memory)
2. **Constant**: An object's address doesn't change during its lifetime ✓ (CPython never moves objects)

```
Two objects alive at the same time:

Heap:
┌──────────────────┐ ← 0x7F001000: Object A (id = 0x7F001000)
│  list [1, 2, 3]  │
└──────────────────┘
        ...
┌──────────────────┐ ← 0x7F001080: Object B (id = 0x7F001080)
│  list [4, 5, 6]  │
└──────────────────┘

Different addresses → different identities → a is not b
```

---

## 6.3 Identity vs Equality

```python
a = [1, 2, 3]
b = [1, 2, 3]
c = a

# Identity (is): same object in memory?
a is b    # False — different objects at different addresses
a is c    # True  — same object (c is just another name)

# Equality (==): same value?
a == b    # True  — same contents
a == c    # True  — same contents (trivially, same object)
```

At the C level:
```c
// 'is' operator → pointer comparison:
a is b  →  (PyObject *)a_ptr == (PyObject *)b_ptr  // Compare addresses

// '==' operator → rich comparison dispatch:
a == b  →  PyObject_RichCompareBool(a, b, Py_EQ)
        →  a->ob_type->tp_richcompare(a, b, Py_EQ)
        // Calls list_richcompare which compares element by element
```

---

## 6.4 When id() Values Get Reused

Since `id()` is just a memory address, once an object is deallocated, its address can be reused:

```python
>>> id(object())
140234567890112
>>> id(object())
140234567890112    # Same! The first object was freed, address reused.
```

Why?
```
Timeline:
1. object() created at 0x7F8A_0001_0000 → id = 0x7F8A00010000
2. No reference → immediately freed
3. object() created → same memory block allocated → same id
```

This is why you should **never** store `id()` values for later comparison — the object might be dead and the id reused by a new, unrelated object.

---

## 6.5 The `is` Operator Internals

```python
x is y
```

Compiles to:
```
LOAD_FAST    x
LOAD_FAST    y
IS_OP        0    # (0 means 'is', 1 means 'is not')
```

In the interpreter (`Python/ceval.c`):
```c
case IS_OP: {
    PyObject *right = POP();
    PyObject *left = TOP();
    int res = Py_Is(left, right);  // Just a pointer comparison!
    // ...
}

// Include/object.h
static inline int Py_Is(PyObject *x, PyObject *y) {
    return (x == y);  // Pointer equality — that's ALL 'is' does
}
```

The `is` operator is the **fastest comparison in Python** — it's a single pointer comparison instruction on the CPU.

---

## 6.6 Singleton Identity: None, True, False

```python
x = None
y = None
x is y    # ALWAYS True — there's only one None object

a = True
b = True
a is b    # ALWAYS True — there's only one True object
```

```
All variables pointing to None share the same pointer:

x ──→ ┌──────────────────┐ ← 0x00005600_ABCD_1234
y ──→ │  _Py_NoneStruct  │    (the ONE None object)
       │  ob_refcnt: huge  │
       │  ob_type: NoneType│
       └──────────────────┘
       
id(x) == id(y) == id(None) — always the same address
```

---

## 6.7 Small Integer Caching and Identity

CPython pre-allocates integers from -5 to 256 (inclusive):

```python
a = 256
b = 256
a is b    # True — same cached object

a = 257
b = 257
a is b    # False (usually) — different objects created
```

```
Small integer cache (statically allocated array):
┌───────────────────────────────────────────────────────────┐
│ Index 0: PyLongObject(-5)  → always at address 0xA000     │
│ Index 1: PyLongObject(-4)  → always at address 0xA020     │
│ ...                                                        │
│ Index 5: PyLongObject(0)   → always at address 0xA0A0     │
│ ...                                                        │
│ Index 261: PyLongObject(256) → always at address 0xB0C0   │
└───────────────────────────────────────────────────────────┘

x = 42 → x points to cache[47] (index = value + 5)
y = 42 → y points to cache[47] (same object!)
x is y → True (same pointer)
```

**Important**: This is an implementation detail. NEVER rely on `is` for integer comparison. Always use `==`.

---

## 6.8 String Interning and Identity

CPython automatically interns certain strings:
- Identifiers (variable names, function names)
- String literals that look like identifiers
- Strings used in source code

```python
a = "hello"
b = "hello"
a is b    # True (interned — same object)

a = "hello world"
b = "hello world"
a is b    # Might be True (compiler constant folding) or False

a = "".join(["h", "e", "l", "l", "o"])
b = "hello"
a is b    # False (runtime-created string not interned)
```

---

## 6.9 Lifetime Implications for Identity

Because `id()` = memory address, and addresses get reused:

```python
# DANGEROUS pattern:
saved_id = id(some_object)
del some_object
# ... later ...
new_object = SomeClass()
id(new_object) == saved_id  # Could be True! But they're different objects!
```

The language guarantee: id is unique **during the object's lifetime**. After deallocation, all bets are off.

### Safe Identity Checking

```python
# ✓ Safe — compare the objects directly:
x is y

# ✗ Dangerous — storing ids for later comparison:
saved = id(obj)
# ... obj might be deleted ...
# id(new_obj) == saved doesn't mean new_obj is the original!
```

### `weakref` for Non-Owning References

If you need to reference an object without keeping it alive, use `weakref`:
```python
import weakref

obj = SomeClass()
ref = weakref.ref(obj)
# ref() returns obj if alive, None if dead
# Does NOT prevent deallocation (doesn't affect refcount)
```

---

## 6.10 id() in Other Python Implementations

| Implementation | id() returns |
|---------------|-------------|
| CPython | Memory address (integer) |
| PyPy | Arbitrary unique integer (NOT address — GC moves objects) |
| Jython | `System.identityHashCode()` |
| MicroPython | Memory address |
| GraalPy | Arbitrary unique integer |

**Language guarantee**: `id()` returns an integer unique during the object's lifetime. The memory-address behavior is CPython-specific and MUST NOT be relied upon in portable code.

---

## 6.11 Object Identity and Mutability

Identity matters more for mutable objects:

```python
# Mutable — identity determines what gets modified:
a = [1, 2, 3]
b = a           # Same identity — b IS a
b.append(4)     # Modifies the SHARED object
print(a)        # [1, 2, 3, 4] — a sees the change!

# Immutable — identity is less critical:
x = "hello"
y = x           # Same identity, but since strings are immutable,
y = y + "!"     # This creates a NEW string — x unchanged
print(x)        # "hello" — x unaffected
```

---

## 6.12 Memory Diagram: Identity in Practice

```python
a = [1, 2, 3]
b = a
c = [1, 2, 3]
```

```
Variable Table                    Heap
┌──────┬──────────────┐
│  a   │ 0x7F00_1000 ─┼────→ ┌─────────────────────┐ 0x7F00_1000
├──────┼──────────────┤       │ list object          │
│  b   │ 0x7F00_1000 ─┼────→ │ refcnt: 2            │ (a and b)
├──────┼──────────────┤       │ ob_type: list        │
│  c   │ 0x7F00_1080 ─┼──┐   │ items: [1, 2, 3]    │
└──────┴──────────────┘  │   └─────────────────────┘
                          │
                          └→ ┌─────────────────────┐ 0x7F00_1080
                             │ list object          │
                             │ refcnt: 1            │ (only c)
                             │ ob_type: list        │
                             │ items: [1, 2, 3]    │
                             └─────────────────────┘

a is b → True  (same address: 0x7F00_1000)
a is c → False (different addresses)
a == c → True  (same contents)
id(a) == id(b) → True  (0x7F00_1000 == 0x7F00_1000)
id(a) == id(c) → False (0x7F00_1000 != 0x7F00_1080)
```

---

## 6.13 Source References

| File | Relevant Code |
|------|--------------|
| `Python/bltinmodule.c` | `builtin_id()` — implementation of `id()` |
| `Python/ceval.c` | `IS_OP` bytecode handler |
| `Include/object.h` | `Py_Is()` inline function |
| `Objects/longobject.c` | Small integer cache (`_PyLong_SMALL_INTS`) |
| `Objects/unicodeobject.c` | String interning (`PyUnicode_InternInPlace`) |
| `Lib/weakref.py` | Weak reference module |

---

## 6.14 Interview Questions — Part 6

**Q1**: What does `id()` return in CPython and why?
**A**: The memory address of the object cast to an integer. This works because CPython never moves objects (no compacting GC), so the address is unique and constant during the object's lifetime.

**Q2**: Why is `a is b` faster than `a == b`?
**A**: `is` is a single pointer comparison (one CPU instruction). `==` requires dynamic dispatch through `ob_type->tp_richcompare`, potentially calling Python code and comparing contents element-by-element.

**Q3**: Can two different objects ever have the same `id()`?
**A**: Not simultaneously (addresses don't overlap). But sequentially yes — after an object is freed, its address can be reused by a new allocation. This is why storing `id()` values for later comparison is dangerous.

**Q4**: Why does `a = 256; b = 256; a is b` return True but `a = 257; b = 257; a is b` might return False?
**A**: CPython caches integers -5 to 256 as pre-allocated singletons. Both names point to the same cached object. For 257, new PyLongObject instances are created (though the compiler may optimize this in some contexts).

**Q5**: How does `id()` differ between CPython and PyPy?
**A**: CPython returns memory address (objects never move). PyPy uses a moving GC, so it returns an arbitrary unique integer that's stable for the object's lifetime but has no relation to the current memory location.

**Q6**: Why should you never write `id(x) == id(y)` instead of `x is y`?
**A**: Beyond being slower, if x or y is a temporary object that could be freed between the two `id()` calls, you could get a false positive. `x is y` is both faster and semantically correct.

**Q7**: What is string interning and how does it affect identity?
**A**: CPython maintains a table of "interned" strings (those that look like identifiers). Multiple references to the same string literal share one object. This saves memory and enables `is` comparison for fast string matching (used internally for attribute lookup).
