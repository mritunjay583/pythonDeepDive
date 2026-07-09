# Python Object Model & Memory Management: A Deep Systems-Level Guide

> Written from the perspective of a CPython core developer.  
> Goal: After mastering this document, you can confidently answer any Python interview question on variables, objects, references, mutability, identity, memory management, and CPython internals.

---

## Table of Contents

1. [Part 1 — Python Object Model](#part-1--python-object-model)
2. [Part 2 — Mutable vs Immutable Objects](#part-2--mutable-vs-immutable-objects)
3. [Part 3 — Identity vs Equality](#part-3--identity-vs-equality)
4. [Part 4 — Function Call Semantics](#part-4--function-call-semantics)
5. [Part 5 — Reference Counting](#part-5--reference-counting)
6. [Part 6 — Garbage Collection](#part-6--garbage-collection)
7. [Part 7 — Python Process Memory](#part-7--python-process-memory)
8. [Part 8 — PyMalloc](#part-8--pymalloc)
9. [Part 9 — CPython Object Layout](#part-9--cpython-object-layout)
10. [Part 10 — Containers Internals](#part-10--containers-internals)
11. [Part 11 — Memory Diagrams](#part-11--memory-diagrams)
12. [Part 12 — Production Implications](#part-12--production-implications)
13. [Part 13 — Interview Section](#part-13--interview-section)
14. [Part 14 — Coding Questions](#part-14--coding-questions)
15. [Part 15 — Exercises](#part-15--exercises)

---

# Part 1 — Python Object Model

## 1.1 Everything Is an Object

### Intuition

In C, you have different kinds of things: integers sit directly on the stack, structs sit in memory with known layouts, functions are machine code at addresses. They are fundamentally different entities.

In Python, **everything** is an object. The integer `10`, the string `"hello"`, the function `print`, the class `int` itself, the module `os` — they are all the same kind of entity at the C level: a `PyObject*` (a pointer to a heap-allocated structure).

### The Problem Python Solves

Python was designed for flexibility and uniformity. If everything is an object:
- You can put anything in a list: `[1, "hello", print, int]`
- You can pass anything to a function
- You can inspect anything at runtime (`type()`, `dir()`, `getattr()`)
- You can store metadata (attributes) on anything

### Internal Implementation (CPython)

In CPython (the reference implementation written in C), every Python object is a C struct that begins with a common header:

```c
// Include/object.h (simplified)
typedef struct _object {
    Py_ssize_t ob_refcnt;    // Reference count
    PyTypeObject *ob_type;   // Pointer to type object
} PyObject;
```

Every single Python value — `10`, `"hello"`, `[1,2,3]`, a function, a class — is represented as a `PyObject*` in C. The interpreter never deals with "raw" values; it always manipulates pointers to these structs.

### Tradeoff

| Advantage | Cost |
|-----------|------|
| Uniform interface | Every integer costs 28 bytes (CPython 3.11, 64-bit) instead of 8 bytes |
| Dynamic typing | Type checks happen at runtime, not compile time |
| Introspection | Objects carry metadata overhead |
| Garbage collection | Reference counting on every operation |

### Language Guarantee vs Implementation Detail

| Statement | Category |
|-----------|----------|
| "Everything is an object" | **Language guarantee** (Python Language Reference §3.1) |
| "Objects are C structs with ob_refcnt" | **CPython implementation detail** |
| "Integer 10 costs 28 bytes" | **CPython implementation detail** (PyPy may differ) |

---

## 1.2 Names vs Variables

### The Core Misconception

In C/C++/Java, a variable **is** a named memory location:

```c
int x = 10;  // x IS a box containing the bit pattern for 10
```

In Python, a name is **not** a box. It is a **label** attached to an object.

```python
x = 10  # x is a label/tag pointing to the object 10
```

### Why This Distinction Matters

```python
a = [1, 2, 3]
b = a
b.append(4)
print(a)  # [1, 2, 3, 4] — surprise if you think "b is a copy"
```

If variables were boxes, `b = a` would copy the contents of box `a` into box `b`. But names are labels — after `b = a`, both labels point to the **same** list object.

### Internal Implementation

At the CPython level, a "name" is:

**Global/module scope:** A key in a `PyDictObject` (the module's `__dict__`).

```
module.__dict__ = {
    "a": <pointer to list object at 0x7f...>,
    "b": <pointer to same list object at 0x7f...>,
    ...
}
```

**Local function scope:** An index into a C array (`f_localsplus`) on the frame object. The bytecode uses integer indices, not string lookups.

```c
// Simplified from Python/ceval.c
case STORE_FAST:
    v = POP();
    SETLOCAL(oparg, v);  // oparg is the integer index
    break;
```

### Memory Diagram

```
After: a = [1, 2, 3]

    Names (dict/array)              Heap
    ┌─────────┐
    │ "a" ────────────────────► ┌──────────────────┐
    └─────────┘                 │ PyListObject     │
                                │ refcount: 1      │
                                │ type: list       │
                                │ items: [1, 2, 3] │
                                └──────────────────┘

After: b = a

    Names (dict/array)              Heap
    ┌─────────┐
    │ "a" ────────────────────► ┌──────────────────┐
    ├─────────┤            ┌──► │ PyListObject     │
    │ "b" ────────────────┘     │ refcount: 2      │
    └─────────┘                 │ type: list       │
                                │ items: [1, 2, 3] │
                                └──────────────────┘
```

---

## 1.3 Objects vs References

### What Is a Reference?

A reference is the connection between a name and an object. In CPython, it is literally a `PyObject*` — a C pointer. But at the language level, you never see the pointer; you only interact with the object through its name.

### Object Properties

Every Python object has three fundamental properties:

| Property | Accessor | Meaning |
|----------|----------|---------|
| Identity | `id(obj)` | Unique identifier (memory address in CPython) |
| Type | `type(obj)` | What kind of object it is |
| Value | The object itself | The data it holds |

Once created:
- **Identity never changes** (language guarantee)
- **Type never changes** (language guarantee, with very rare exceptions via C API hacks)
- **Value may or may not change** (depends on mutability)

---

## 1.4 Assignment

### What `=` Actually Does

The `=` operator in Python does exactly **three** things:

1. Evaluate the right-hand side expression to get an object
2. Bind the left-hand side name to that object in the current namespace
3. If the name previously referred to another object, decrement that object's reference count

It does **not**:
- Copy data
- Create a new object (the RHS expression might, but `=` itself doesn't)
- Allocate a "variable"

### Bytecode Evidence

```python
import dis
dis.dis("x = 10")
```

Output:
```
  0           0 RESUME                   0

  1           2 LOAD_CONST               0 (10)
              4 STORE_NAME               0 (x)
              6 RETURN_CONST             1 (None)
```

`LOAD_CONST` pushes the pre-existing integer object `10` onto the evaluation stack.  
`STORE_NAME` pops it and puts it in the local namespace dict under key `"x"`.

No memory allocation for "the variable x" happens. The namespace dict already exists as part of the frame.

---

## 1.5 Object Identity — `id()`

### What It Returns

`id(obj)` returns a unique integer identifier for the object **for its lifetime**.

**Language guarantee:** Two objects with non-overlapping lifetimes may have the same `id()`.  
**CPython implementation:** `id()` returns the memory address of the `PyObject` struct (cast to `int`).

```python
a = [1, 2, 3]
print(id(a))    # e.g., 140234567890112
print(hex(id(a)))  # 0x7f8a1c2d3e40
```

### Common Pitfall

```python
print(id([1,2,3]) == id([4,5,6]))  # Can print True!
```

Why? The first list is created, its id is computed, then it's immediately garbage collected (refcount drops to 0). The second list may be allocated at the same address. Their lifetimes don't overlap, so CPython reuses the memory.

---

## 1.6 Object Type — `type()`

Every object knows its type. The type is stored as a pointer in the object header:

```c
typedef struct _object {
    Py_ssize_t ob_refcnt;
    PyTypeObject *ob_type;   // <-- this
} PyObject;
```

```python
type(10)        # <class 'int'>
type("hello")   # <class 'str'>
type(type)      # <class 'type'> — types are objects too!
```

The type determines:
- What operations are valid (`__add__`, `__mul__`, etc.)
- The memory layout of the object
- The behavior on attribute access

---

## 1.7 Why Python Variables Are Not Memory Boxes

### The Box Model (C/Java)

```
┌─────┐
│  x  │ = 10     x is a box containing 10
└─────┘

┌─────┐
│  y  │ = 10     y is a separate box, also containing 10
└─────┘
```

In this model, `x` and `y` are independent. Changing one cannot affect the other.

### The Label/Tag Model (Python)

```
    x ──────────►  ┌────────────────┐
                   │ int object: 10 │
    y ──────────►  └────────────────┘
```

Both `x` and `y` are labels stuck onto the **same** object. For immutable objects (like `int`), this distinction doesn't matter behaviorally. But for mutable objects, it's critical.

### Why Python Chose This Model

1. **Uniform semantics:** Everything works the same way — ints, lists, functions, classes
2. **Efficiency for large objects:** Assigning a million-element list to a new name is O(1), not O(n)
3. **Supports polymorphism:** A name can refer to any type of object at any time
4. **Simpler garbage collection:** Objects have a single canonical location; names are just references to it

---

## 1.8 Multiple References to One Object (Aliasing)

### Definition

Aliasing occurs when multiple names refer to the same object.

```python
a = [1, 2, 3]
b = a           # b is an alias for the same list
c = a           # c is also an alias

# All three names refer to the SAME object
assert a is b is c
assert id(a) == id(b) == id(c)
```

### When Aliasing Is Dangerous

```python
def process(data):
    data.append(999)  # Mutates the caller's list!

my_list = [1, 2, 3]
process(my_list)
print(my_list)  # [1, 2, 3, 999]
```

The function parameter `data` is an alias for `my_list`. Mutating through one alias is visible through all aliases.

### When Aliasing Is Safe

With immutable objects, aliasing can never cause surprises:

```python
a = "hello"
b = a
b = b + " world"  # Creates a NEW string, rebinds b
print(a)  # "hello" — unaffected
```

---

## 1.9 Rebinding

### Definition

Rebinding means making a name point to a **different** object.

```python
x = 10
x = 20    # Rebinding: x now points to a different object
```

### What Happens Internally

1. A new object (or existing cached object) for `20` is located
2. `x` is rebound to point to the `20` object
3. The reference count of the `10` object is decremented
4. If the reference count of `10` reaches 0, it would be deallocated (but small ints are cached)

### Rebinding vs Mutation

This is one of the most critical distinctions in Python:

| Operation | What It Does | Example |
|-----------|-------------|---------|
| Rebinding | Name points to a new object | `x = x + [4]` |
| Mutation | The object itself changes | `x.append(4)` |

```python
# Rebinding
a = [1, 2, 3]
b = a
a = a + [4]     # Creates NEW list, rebinds a
print(b)        # [1, 2, 3] — b still points to old list

# Mutation
a = [1, 2, 3]
b = a
a.append(4)     # Mutates the EXISTING list
print(b)        # [1, 2, 3, 4] — b sees the change
```

---

## 1.10 Object Lifetime

An object exists from creation until its reference count drops to zero (or the cyclic GC collects it if it's in a reference cycle).

```python
def foo():
    x = [1, 2, 3]   # List created, refcount = 1
    y = x            # refcount = 2
    return y         # refcount stays >= 1 (caller holds it)
    # x goes out of scope: refcount decremented
    # But y was returned, so the object survives

result = foo()       # result now holds the list, refcount = 1
del result           # refcount = 0, list is deallocated
```

### Object Lifecycle Diagram

```
    CREATE ──► LIVE (refcount > 0) ──► DESTROY (refcount == 0)
                    │                         │
                    │ (may be in cycle)        │
                    ▼                          ▼
              GC may collect            __del__ called
              if unreachable            memory freed
```

---

## 1.11 Summary Table

| Concept | C Model | Python Model |
|---------|---------|--------------|
| Variable | Named memory location | Name in a namespace |
| Assignment | Copy bits into box | Bind name to object |
| `a = b` | Copy value of b into a | Make a point to same object as b |
| Storage | Stack or heap | Always heap (for the object) |
| Type | Property of the variable | Property of the object |
| Identity | Memory address | `id()` — address in CPython |

---


# Part 2 — Mutable vs Immutable Objects

## 2.1 What Mutability Actually Means

### Intuition

An object is **mutable** if you can change its internal state (its value) after creation without changing its identity. An object is **immutable** if its value cannot be changed after creation — any "modification" creates a new object.

### Formal Definition

**Language guarantee (Python Language Reference §3.1):**
> "An object's mutability is determined by its type; for instance, numbers, strings and tuples are immutable, while dictionaries and lists are mutable."

### The Key Test

```python
x = something
original_id = id(x)
# ... perform operation on x ...
assert id(x) == original_id   # If True: mutation happened (or no change)
                                # Object identity preserved
```

If an operation changes the value but keeps the same `id()`, the object was mutated.  
If an operation requires a new `id()`, a new object was created (rebinding, not mutation).

### Classification

| Immutable | Mutable |
|-----------|---------|
| `int` | `list` |
| `float` | `dict` |
| `complex` | `set` |
| `bool` | `bytearray` |
| `str` | User-defined classes (by default) |
| `bytes` | |
| `tuple` | |
| `frozenset` | |
| `NoneType` | |

---

## 2.2 Internal State and Identity

### Mutable Object — Internal State Changes

```python
a = [1, 2, 3]
print(id(a))     # 0x7f...100
a.append(4)
print(id(a))     # 0x7f...100  ← SAME identity
print(a)         # [1, 2, 3, 4] ← different value
```

Internally, the `PyListObject` struct's internal array was reallocated (if needed) or the item was written to an existing slot. The outer `PyListObject` struct remains at the same address.

### Immutable Object — New Object Created

```python
s = "hello"
print(id(s))     # 0x7f...200
s = s + " world"
print(id(s))     # 0x7f...300  ← DIFFERENT identity
```

The concatenation creates a brand-new `PyUnicodeObject`. The name `s` is rebound to it. The old `"hello"` object still exists (if other references exist) or is deallocated.

---

## 2.3 Why Immutable Objects Exist

### Problem: Shared State Bugs

If integers were mutable:
```python
a = 10
b = a       # Both point to same int object (caching!)
a.set(20)   # Hypothetical mutation
print(b)    # Would print 20! Catastrophic.
```

Since CPython caches small integers (-5 to 256), every variable holding `10` points to the **same** object. If that object were mutable, changing it through any name would affect all of them globally. The program would become impossible to reason about.

### Reasons for Immutability

| Reason | Explanation |
|--------|-------------|
| **Hashability** | Dict keys and set members must be hashable → must be immutable |
| **Thread safety** | Immutable objects can be shared without locks |
| **Caching/interning** | Safe to share one object among many references |
| **Predictability** | Value semantics — no surprise aliasing bugs |
| **Optimization** | Compiler can constant-fold, intern, and cache freely |

### Reasons for Mutability

| Reason | Explanation |
|--------|-------------|
| **Efficiency** | Appending to a list is O(1) amortized; creating new list each time is O(n) |
| **In-place modification** | Building data structures incrementally |
| **Shared state** | Intentional communication between parts of a program |

---

## 2.4 Why Strings Are Immutable

1. **Hashing:** Strings are the most common dict key. Their hash is computed once and cached inside the object (`hash` field in `PyUnicodeObject`). If the string could change, the cached hash would be invalid.

2. **Interning:** CPython interns (shares a single copy of) many strings (identifiers, string literals). If strings were mutable, changing one would corrupt all names using that interned string.

3. **Security:** Filenames, URLs, SQL queries — if these could be mutated after validation, it would create security vulnerabilities.

### CPython Implementation

```c
// Include/cpython/unicodeobject.h (simplified)
typedef struct {
    PyObject_HEAD
    Py_hash_t hash;          // Cached hash, -1 if not computed
    Py_ssize_t length;
    // ... kind, state, data ...
} PyUnicodeObject;
```

The `hash` field is computed once on first `hash()` call and cached forever — safe because the string content never changes.

---

## 2.5 Why Integers Are Immutable

Same reasoning as strings:

1. **Small integer caching:** CPython pre-allocates integers -5 to 256. `a = 10` and `b = 10` point to the same object. Mutation would be catastrophic.

2. **Hashability:** Integers are commonly used as dict keys.

3. **Mathematical correctness:** The number 10 is a fixed mathematical concept. It doesn't make sense for `10` to "become" `20`.

---

## 2.6 Why Tuples Are Immutable But Can Contain Mutable Objects

### The Tuple's Promise

A tuple guarantees that its **structure** (which slots exist and which objects they point to) never changes. It does NOT guarantee anything about the objects inside those slots.

```python
t = ([1, 2], [3, 4])
# t[0] will ALWAYS be the same list object
# But that list object can be mutated

t[0].append(99)
print(t)  # ([1, 2, 99], [3, 4])

# But you cannot rebind slots:
t[0] = [5, 6]  # TypeError: 'tuple' object does not support item assignment
```

### Memory Diagram

```
    t ──────► ┌─────────────────┐
              │ PyTupleObject   │
              │ refcount: 1     │
              │ size: 2         │
              │ items[0] ───────────► ┌───────────────┐
              │ items[1] ──────┐      │ PyListObject  │
              └────────────────┘│     │ [1, 2, 99]    │
                                │     └───────────────┘
                                │
                                └───► ┌───────────────┐
                                      │ PyListObject  │
                                      │ [3, 4]        │
                                      └───────────────┘
```

The tuple itself is immutable (the pointer array is fixed), but the objects those pointers refer to may be mutable.

### Hashability Consequence

```python
t1 = (1, 2, 3)         # Hashable — all elements immutable
t2 = ([1, 2], 3)       # NOT hashable — contains mutable element

hash(t1)  # Works
hash(t2)  # TypeError: unhashable type: 'list'
```

---

## 2.7 Mutable Default Arguments

### The Classic Bug

```python
def append_to(element, target=[]):
    target.append(element)
    return target

print(append_to(1))   # [1]
print(append_to(2))   # [1, 2] ← WAT?!
print(append_to(3))   # [1, 2, 3]
```

### Why This Happens

Default argument values are evaluated **once** — at function **definition** time, not at call time. The default list `[]` is created once and stored as an attribute of the function object:

```python
print(append_to.__defaults__)  # ([1, 2, 3],) after the calls above
```

Every call that uses the default gets the **same** list object. Since lists are mutable, mutations accumulate.

### The Fix

```python
def append_to(element, target=None):
    if target is None:
        target = []     # New list created on each call
    target.append(element)
    return target
```

### Why Python Doesn't "Fix" This

It's not a bug — it's a consequence of consistent semantics:
1. Default values are expressions evaluated once at def time
2. Objects are shared by reference
3. The function object stores the default value object

Changing this would require evaluating the default expression on every call, which has performance implications and would break code that intentionally uses mutable defaults as persistent state.

---

## 2.8 The `+=` Operator — Mutation vs Rebinding

### The Duality of `+=`

`+=` calls `__iadd__` (in-place add) if available, falling back to `__add__` + rebinding.

**For mutable objects (list):**
```python
a = [1, 2, 3]
b = a
a += [4, 5]      # Calls list.__iadd__, mutates in place
print(b)         # [1, 2, 3, 4, 5] — same object!
print(a is b)    # True
```

**For immutable objects (int, str, tuple):**
```python
a = 10
b = a
a += 5           # Creates new int(15), rebinds a
print(b)         # 10 — unaffected
print(a is b)    # False
```

**For tuples (immutable):**
```python
a = (1, 2, 3)
b = a
a += (4, 5)      # Creates new tuple, rebinds a
print(b)         # (1, 2, 3) — unaffected
print(a is b)    # False
```

### The Infamous Tuple-with-List Puzzle

```python
t = ([1, 2],)
t[0] += [3, 4]
```

This **raises TypeError** AND **mutates the list**! Why?

`t[0] += [3, 4]` desugars to:
```python
t[0] = t[0].__iadd__([3, 4])
```

1. `t[0].__iadd__([3, 4])` — calls `list.__iadd__`, mutates the list in place, returns `self`
2. `t[0] = ...` — tries to assign back into the tuple → TypeError

The mutation already happened before the assignment fails.

```python
t = ([1, 2],)
try:
    t[0] += [3, 4]
except TypeError:
    pass
print(t)  # ([1, 2, 3, 4],) — mutated!
```

---

## 2.9 Common List Operations — Mutation vs New Object

| Operation | Mutates? | Returns |
|-----------|----------|---------|
| `lst.append(x)` | Yes | `None` |
| `lst.extend(iterable)` | Yes | `None` |
| `lst.sort()` | Yes | `None` |
| `lst.reverse()` | Yes | `None` |
| `lst.insert(i, x)` | Yes | `None` |
| `lst.pop()` | Yes | The removed item |
| `lst.remove(x)` | Yes | `None` |
| `lst + other` | No | New list |
| `sorted(lst)` | No | New list |
| `lst[:]` | No | New list (shallow copy) |
| `list(lst)` | No | New list (shallow copy) |
| `lst * n` | No | New list |

### Key Insight

Methods that mutate **return `None`** as a convention. This prevents chaining that would confuse readers:

```python
# This is a bug — sort() returns None, not the sorted list
result = my_list.sort()  # result is None!

# Correct:
my_list.sort()           # Mutates in place
# or
result = sorted(my_list) # Returns new sorted list
```

---

## 2.10 String Operations — Always New Objects

| Operation | Returns |
|-----------|---------|
| `s.replace("a", "b")` | New string |
| `s.upper()` | New string |
| `s.strip()` | New string |
| `s + other` | New string |
| `s[1:3]` | New string (or same if whole string) |

Strings **never** mutate. Every "modification" creates a new string object.

```python
s = "hello"
s_id = id(s)
s = s.replace("h", "H")
print(id(s) == s_id)  # False — new object
```

### Performance Implication

String concatenation in a loop is O(n²):

```python
# BAD: O(n²) — creates n intermediate strings
result = ""
for word in words:
    result += word    # New string each iteration

# GOOD: O(n)
result = "".join(words)
```

`str.join()` pre-calculates the total length, allocates once, and copies all strings into the buffer.

---

## 2.11 Slicing — Shallow Copy

```python
original = [[1, 2], [3, 4]]
copy = original[:]       # Shallow copy

copy.append([5, 6])      # Doesn't affect original
print(original)          # [[1, 2], [3, 4]]

copy[0].append(99)       # DOES affect original!
print(original)          # [[1, 2, 99], [3, 4]]
```

A shallow copy creates a new container but the elements inside are still shared references.

```
original ──► ┌───────┐         ┌─────────┐
             │ [0] ──────────► │ [1, 2]  │ ◄───── copy[0]
             │ [1] ──────────► │ [3, 4]  │ ◄───── copy[1]
             └───────┘         └─────────┘
                                              
copy ────────► ┌───────┐                     ┌─────────┐
               │ [0] ──────(same)             │ [5, 6]  │
               │ [1] ──────(same)             └─────────┘
               │ [2] ─────────────────────────────┘
               └───────┘
```

---

## 2.12 Rebinding vs Mutation — Master Summary

```python
# REBINDING: name points to a new object
x = x + y          # Always rebinding
x = something      # Always rebinding
x += y             # Rebinding for immutable, mutation for mutable

# MUTATION: object's internal state changes
x.append(y)        # Always mutation
x[0] = y           # Always mutation (if x supports it)
x.sort()           # Always mutation
del x[0]           # Always mutation
```

### The Golden Rule

> If an operation uses `=` (including augmented assignment on immutables), it's rebinding.  
> If an operation uses a method call or item/attribute assignment on a mutable object, it's mutation.

---


# Part 3 — Identity vs Equality

## 3.1 Two Kinds of Comparison

Python provides two distinct comparison operations:

| Operator | Tests | Meaning |
|----------|-------|---------|
| `is` | Identity | Are these the **same object** in memory? |
| `==` | Equality | Do these objects have the **same value**? |

```python
a = [1, 2, 3]
b = [1, 2, 3]
c = a

a == b    # True — same value
a is b    # False — different objects
a is c    # True — same object
```

### Internal Implementation

```python
# 'is' compares id() values (memory addresses in CPython)
a is b   ←→   id(a) == id(b)

# '==' calls __eq__ method
a == b   ←→   a.__eq__(b)
```

`is` is a pointer comparison — it compares the `PyObject*` addresses. It's always O(1).  
`==` calls `__eq__`, which may iterate over contents. For a list of n elements, it's O(n).

---

## 3.2 When to Use `is`

### Rule: Use `is` Only for Singletons

The only correct uses of `is` are:

```python
if x is None:           # ✓ Correct
if x is not None:       # ✓ Correct
if x is True:           # Rarely needed, but correct
if x is False:          # Rarely needed, but correct
if type(x) is int:      # Sometimes appropriate
```

### Why `is None` Works

`None` is a singleton — there is exactly one `None` object in any Python process:

```python
# These are ALL the same object
a = None
b = None
c = None
assert a is b is c
```

This is a **language guarantee** (not just CPython). The Python Language Reference states that `None` is a singleton.

---

## 3.3 Small Integer Caching

### CPython Implementation Detail

CPython pre-allocates integer objects for the range **-5 to 256** at startup. These are stored in a static array and reused.

```python
a = 256
b = 256
a is b    # True — same cached object

a = 257
b = 257
a is b    # ??? — implementation-defined
```

### Source Code (CPython)

```c
// Objects/longobject.c
#define NSMALLPOSINTS   257  // 0 to 256
#define NSMALLNEGINTS   5    // -5 to -1

static PyLongObject small_ints[NSMALLNEGINTS + NSMALLPOSINTS];
```

### Why 257 Might Still Be `True`

In an interactive session:
```python
>>> a = 257
>>> b = 257
>>> a is b
False
```

But in a script or single compilation unit:
```python
# In a .py file:
a = 257
b = 257
print(a is b)  # True! (constant folding)
```

The compiler notices both `257` literals in the same code object and reuses the constant. This is **constant folding**, not integer caching.

### Why Using `is` for Integers Is Wrong

```python
def is_lucky(n):
    return n is 7    # WRONG! Works by accident for small ints

is_lucky(7)          # True (small int cache)
is_lucky(int("7"))   # Might be True or False depending on implementation
```

Always use `==` for value comparison:
```python
def is_lucky(n):
    return n == 7    # Correct
```

---

## 3.4 String Interning

### What Is Interning?

Interning means storing only one copy of a string and reusing it everywhere.

CPython automatically interns:
- All identifier-like strings (letters, digits, underscores)
- String literals in source code
- Dictionary keys
- Attribute names

```python
a = "hello"
b = "hello"
a is b          # True — interned

a = "hello world"
b = "hello world"
a is b          # Might be True (compiler optimization) or False

a = "hello!"
b = "hello!"
a is b          # More likely False (not identifier-like)
```

### Manual Interning

```python
import sys
a = sys.intern("hello world!!")
b = sys.intern("hello world!!")
a is b  # True — forced interning
```

### Why Intern?

1. **Dictionary lookups:** If keys are interned, comparison is a pointer check (O(1)) instead of string comparison (O(n))
2. **Memory savings:** One copy shared among all references
3. **Attribute access:** `obj.attr` lookups are faster when attribute names are interned

### CPython Implementation

```c
// Objects/unicodeobject.c
// Interned strings are stored in a dictionary:
static PyObject *interned = NULL;  // A dict mapping string → same string
```

---

## 3.5 Constant Folding and Compiler Optimizations

### What the Compiler Does

CPython's peephole optimizer (and AST optimizer) performs constant folding:

```python
# The compiler evaluates constant expressions at compile time:
x = 3 * 4          # Compiled as x = 12
y = "ab" * 3       # Compiled as y = "ababab" (if result ≤ 4096 chars)
z = (1, 2) + (3,)  # Compiled as z = (1, 2, 3)
```

### Why This Affects `is`

```python
# In the same code object (same .py file or function):
a = "hello"
b = "hello"
# The compiler stores "hello" once in co_consts
# Both LOAD_CONST instructions load the same object
print(a is b)  # True — same constant object
```

```python
# Dynamically created:
a = "hel" + "lo"    # Compiler folds this to "hello" — same constant
b = "hello"
print(a is b)       # True

a = input()         # User types "hello"
b = "hello"
print(a is b)       # False — runtime-created vs compile-time constant
```

### Takeaway

> Never rely on `is` for value comparison. The result depends on compiler optimizations, caching strategies, and implementation details that vary between Python versions and implementations.

---

## 3.6 `None` — The Singleton

### Internal Implementation

```c
// Objects/object.c
PyObject _Py_NoneStruct = {
    _PyObject_EXTRA_INIT
    { _Py_IMMORTAL_REFCNT },
    &_PyNone_Type
};
```

There is literally one `None` object in the entire process. Every function that "returns nothing" returns a pointer to this single struct.

### Best Practice

```python
# CORRECT:
if result is None:
    handle_none()

# WRONG (but usually works):
if result == None:
    handle_none()
```

Why `is` is preferred:
1. `is` cannot be overridden — `==` can be overridden by `__eq__`
2. `is` is faster (pointer comparison vs method call)
3. Semantically clearer: you're checking if it's the None singleton, not "equal to None"

---

## 3.7 Summary Table — Identity Traps

| Expression | Result | Reason |
|-----------|--------|--------|
| `256 is 256` | `True` | Small integer cache |
| `257 is 257` | Implementation-defined | May be constant-folded |
| `"abc" is "abc"` | Usually `True` | String interning |
| `"abc!" is "abc!"` | Implementation-defined | May not be interned |
| `[] is []` | Always `False` | New object each time |
| `() is ()` | `True` | Empty tuple is cached |
| `None is None` | Always `True` | Singleton |
| `True is True` | Always `True` | Singleton |
| `float('nan') == float('nan')` | `False` | IEEE 754 NaN rule |
| `float('nan') is float('nan')` | Implementation-defined | |

---


# Part 4 — Function Call Semantics

## 4.1 The Great Debate: Pass by Value? Pass by Reference?

### Neither. Python Uses "Pass by Object Reference" (Pass by Assignment)

In C:
- **Pass by value:** A copy of the value is placed in the function's parameter. Changes inside the function don't affect the caller.
- **Pass by reference:** The function receives the memory address of the variable. Changes inside the function directly modify the caller's variable.

Python does **neither**:
- It doesn't copy the object (not pass by value)
- It doesn't give you access to the caller's name binding (not pass by reference)

It **passes the object reference** — the function parameter becomes a new name bound to the same object.

### The Correct Mental Model

```python
def func(param):
    # param is a NEW name bound to the SAME object as the argument
    pass

x = [1, 2, 3]
func(x)
# This is equivalent to:
# param = x  (at the start of the function)
```

The function call is equivalent to an assignment: `param = x`. The rules from Part 1 apply:
- If you **mutate** the object through `param`, the caller sees it (same object)
- If you **rebind** `param`, the caller is unaffected (different name)

---

## 4.2 Mutation Inside Functions

```python
def add_item(lst):
    lst.append(99)    # Mutation — modifies the object

my_list = [1, 2, 3]
add_item(my_list)
print(my_list)        # [1, 2, 3, 99] — caller's list was mutated
```

### Memory Diagram

```
Before call:
    my_list ──────► ┌────────────────┐
                    │ [1, 2, 3]      │
                    │ refcount: 1    │
                    └────────────────┘

During call (lst = my_list):
    my_list ──────► ┌────────────────┐
    lst ──────────► │ [1, 2, 3]      │
                    │ refcount: 2    │
                    └────────────────┘

After lst.append(99):
    my_list ──────► ┌────────────────┐
    lst ──────────► │ [1, 2, 3, 99]  │
                    │ refcount: 2    │
                    └────────────────┘

After function returns (lst goes out of scope):
    my_list ──────► ┌────────────────┐
                    │ [1, 2, 3, 99]  │
                    │ refcount: 1    │
                    └────────────────┘
```

---

## 4.3 Rebinding Inside Functions

```python
def reassign(lst):
    lst = [99, 100]   # Rebinding — creates new object, rebinds local name

my_list = [1, 2, 3]
reassign(my_list)
print(my_list)        # [1, 2, 3] — completely unaffected
```

### Memory Diagram

```
During call, before rebinding:
    my_list ──────► ┌────────────────┐
    lst ──────────► │ [1, 2, 3]      │
                    │ refcount: 2    │
                    └────────────────┘

After lst = [99, 100]:
    my_list ──────► ┌────────────────┐
                    │ [1, 2, 3]      │
                    │ refcount: 1    │
                    └────────────────┘

    lst ──────────► ┌────────────────┐
                    │ [99, 100]      │
                    │ refcount: 1    │
                    └────────────────┘
```

The caller's name `my_list` still points to the original object. Rebinding the local name `lst` has zero effect on `my_list`.

---

## 4.4 The Tricky Case — Mutation Then Rebinding

```python
def tricky(lst):
    lst.append(99)      # Mutation — caller sees this
    lst = [5, 6, 7]    # Rebinding — caller doesn't see this
    lst.append(100)     # Mutation of NEW local object — caller doesn't see this

my_list = [1, 2, 3]
tricky(my_list)
print(my_list)          # [1, 2, 3, 99]
```

---

## 4.5 Parameter Binding

When a function is called, parameters are bound using the same rules as assignment:

```python
def func(a, b, c=10, *args, **kwargs):
    pass

func(1, [2,3], key="val")
```

This is equivalent to:
```python
a = 1           # Bound to int object
b = [2, 3]     # Bound to list object
c = 10          # Bound to default (same object as the default)
args = ()       # New empty tuple
kwargs = {"key": "val"}  # New dict
```

---

## 4.6 Local Names and the LEGB Rule

### Namespace Hierarchy

Python resolves names using the LEGB rule:

| Level | Scope | Example |
|-------|-------|---------|
| **L** | Local | Variables defined inside the current function |
| **E** | Enclosing | Variables in enclosing function(s) — closures |
| **G** | Global | Module-level variables |
| **B** | Built-in | `print`, `len`, `int`, etc. |

### How Local Scope Works Internally

At compile time (when the function's code object is created), Python determines which names are local by scanning for assignments:

```python
x = 10          # Global

def foo():
    print(x)    # Would this use global x? Let's see...
    x = 20      # Assignment makes x LOCAL to foo

foo()           # UnboundLocalError: local variable 'x' referenced before assignment
```

The compiler sees `x = 20` anywhere in the function body and marks `x` as local for the **entire** function. The `print(x)` then tries to read the local `x` before it's been assigned.

### Bytecode Evidence

```python
import dis

x = 10
def foo():
    x = 20    # x is local
    
def bar():
    print(x)  # x is global (no assignment to x in bar)

dis.dis(foo)  # Uses STORE_FAST (local)
dis.dis(bar)  # Uses LOAD_GLOBAL
```

---

## 4.7 Closures

### What Is a Closure?

A closure is a function that remembers values from its enclosing scope, even after that scope has finished executing.

```python
def make_counter():
    count = 0
    def increment():
        nonlocal count
        count += 1
        return count
    return increment

counter = make_counter()
print(counter())  # 1
print(counter())  # 2
print(counter())  # 3
```

### Internal Implementation — Cell Objects

Closures work through **cell objects**. When the compiler detects that a variable is used in a nested function, it stores it in a "cell" rather than directly on the frame.

```python
counter.__closure__          # (<cell at 0x...: int object at 0x...>,)
counter.__closure__[0].cell_contents  # Current value of count
```

The cell is a level of indirection — both the outer function and the inner function share a pointer to the same cell, which in turn points to the actual value.

```
make_counter's frame:          increment closure:
    count_cell ──────────┐
                         ▼
                    ┌─────────────┐
                    │ Cell object  │
                    │ contents ────────► int(3)
                    └─────────────┘
                         ▲
    __closure__[0] ──────┘
```

---

## 4.8 Default Arguments — Evaluated Once

```python
import time

def log_event(msg, timestamp=time.time()):
    print(f"{timestamp}: {msg}")

# timestamp is fixed at definition time!
log_event("first")   # 1700000000.0: first
time.sleep(2)
log_event("second")  # 1700000000.0: second  ← same timestamp!
```

### Why?

Default values are stored in `func.__defaults__` (a tuple) at function definition time. They are evaluated exactly once, when the `def` statement executes.

```python
def f(x=[]):
    pass

# The default list is stored here:
f.__defaults__  # ([],)
# It's the SAME list object every call
```

---

## 4.9 The `global` and `nonlocal` Keywords

### `global` — Write to Module Scope

```python
x = 10

def modify_global():
    global x        # Without this, x = 20 would create a LOCAL x
    x = 20

modify_global()
print(x)  # 20
```

### `nonlocal` — Write to Enclosing Scope

```python
def outer():
    x = 10
    def inner():
        nonlocal x  # Without this, x = 20 would create a LOCAL x in inner
        x = 20
    inner()
    print(x)  # 20

outer()
```

Without `nonlocal`, assignment creates a new local variable. `nonlocal` tells the compiler to use the enclosing scope's cell for that name.

---

## 4.10 Summary — Function Call Rules

| Scenario | Effect on Caller |
|----------|-----------------|
| Mutate parameter object | Caller sees the change |
| Rebind parameter name | Caller is unaffected |
| `+=` on mutable parameter | Caller sees the change (mutation) |
| `+=` on immutable parameter | Caller is unaffected (rebinding) |
| Return a value | Caller gets a reference to that object |

---


# Part 5 — Reference Counting

## 5.1 What Is Reference Counting?

Reference counting is CPython's **primary** memory management mechanism. Every object carries a counter that tracks how many references point to it. When the counter reaches zero, the object is immediately deallocated.

### The Core Invariant

```
ob_refcnt == number of places that hold a pointer to this object
```

This includes:
- Names bound to the object
- Container elements pointing to it
- Temporary variables on the C stack
- Function arguments
- Global data structures

---

## 5.2 How References Increase

| Action | Example | Effect |
|--------|---------|--------|
| Assignment | `b = a` | +1 to object |
| Function argument | `func(a)` | +1 during call |
| Container insertion | `lst.append(a)` | +1 |
| Attribute assignment | `obj.x = a` | +1 |
| Adding to a tuple | `t = (a,)` | +1 |
| `LOAD_FAST`/`LOAD_GLOBAL` bytecode | Any name reference | +1 temporarily |

### Checking Reference Count

```python
import sys

a = [1, 2, 3]
print(sys.getrefcount(a))  # Prints 2 (one for 'a', one for the argument to getrefcount)
```

Note: `sys.getrefcount()` always returns at least one more than you'd expect, because passing the object to the function creates a temporary reference.

---

## 5.3 How References Decrease

| Action | Example | Effect |
|--------|---------|--------|
| Name goes out of scope | Function returns | -1 |
| Rebinding | `a = other_object` | -1 to old object |
| `del` statement | `del a` | -1 (removes name from namespace) |
| Container removal | `lst.remove(a)` | -1 |
| Container destruction | List is freed | -1 for each element |
| Attribute deletion | `del obj.x` | -1 |

---

## 5.4 The `del` Statement

### What `del` Does (And Doesn't Do)

`del` removes a **name** from the namespace. It does NOT directly free memory.

```python
a = [1, 2, 3]     # refcount: 1
b = a              # refcount: 2
del a              # refcount: 1 (name 'a' removed from namespace)
                   # Object still alive! b still references it
del b              # refcount: 0 → object deallocated
```

### Common Misconception

```python
a = [1, 2, 3]
del a          # Does NOT call free(). It decrements refcount.
               # Object is freed only because refcount hits 0.
```

If other references exist, `del` merely removes one:
```python
a = [1, 2, 3]
b = a
del a          # Object NOT freed — b still holds a reference
print(b)       # [1, 2, 3] — still alive
```

---

## 5.5 Temporary References

Many references are extremely short-lived:

```python
print(len([1, 2, 3]))
```

Internal steps:
1. `[1, 2, 3]` — list created (refcount: 1, on the eval stack)
2. `len(...)` — list passed as argument (refcount: 2)
3. `len` returns `3`, list reference popped from stack (refcount: 1)
4. After `len` returns, the list reference on the eval stack is consumed (refcount: 0)
5. List deallocated

All within a single bytecode sequence. The list lives for microseconds.

---

## 5.6 Reference Counting in Function Calls

```python
def process(data):          # data parameter: refcount +1
    result = data[::-1]     # data is referenced by LOAD_FAST: temporary +1
    return result           # data parameter about to be destroyed: -1
                           # result is being returned, stays alive

original = [1, 2, 3]       # refcount: 1
reversed_copy = process(original)  # During call, original's refcount briefly = 2
# After call: original refcount back to 1
```

---

## 5.7 Reference Counting in Containers

When an object is placed in a container, the container holds a reference:

```python
a = [1, 2, 3]       # list: refcount 1
container = [a, a]   # list: refcount 3 (a + container[0] + container[1])

del a                # list: refcount 2
del container[0]     # list: refcount 1
del container        # container destroyed, its element destroyed: list refcount 0 → freed
```

### Nested Containers

```python
outer = []
inner = [1, 2, 3]
outer.append(inner)     # inner refcount: 2 (name 'inner' + outer[0])
outer.append(inner)     # inner refcount: 3 (name 'inner' + outer[0] + outer[1])

del inner               # inner refcount: 2 (outer[0] + outer[1])
del outer               # outer destroyed → its elements decremented → inner refcount: 0 → freed
```

---

## 5.8 Reference Cycles — The Achilles Heel

### The Problem

```python
a = []
b = []
a.append(b)    # a → b (b refcount: 2)
b.append(a)    # b → a (a refcount: 2)

del a          # a refcount: 1 (still referenced by b[0])
del b          # b refcount: 1 (still referenced by a[0])
# Both objects have refcount > 0, but are unreachable!
# MEMORY LEAK if we only use reference counting
```

### Memory Diagram

```
After del a, del b:

No names reference these objects, but:

    ┌──────────┐       ┌──────────┐
    │ list A   │──────►│ list B   │
    │ refcnt:1 │◄──────│ refcnt:1 │
    └──────────┘       └──────────┘

Both have refcount 1, but NOTHING outside the cycle can reach them.
They are garbage, but reference counting can't detect this.
```

This is why CPython also has a **cyclic garbage collector** (Part 6).

---

## 5.9 Weak References

### The Problem They Solve

Sometimes you want to reference an object without preventing its deallocation. Examples:
- Caches (don't want cache entries to keep objects alive forever)
- Observer patterns (observers shouldn't prevent subject from being freed)
- Parent-child relationships (avoiding cycles)

### Using `weakref`

```python
import weakref

class MyClass:
    pass

obj = MyClass()
weak = weakref.ref(obj)    # Weak reference — does NOT increment refcount

print(weak())              # <MyClass object> — call the weakref to get the object
del obj                    # Object freed! (weak ref didn't prevent it)
print(weak())              # None — object is gone
```

### Internal Implementation

Weak references are tracked in a per-object list (`tp_weaklistoffset` in the type object). When the object is about to be deallocated, CPython walks the weakref list and sets each weak reference's pointer to `None`.

### Callbacks

```python
def on_finalize(ref):
    print(f"Object was destroyed! Ref: {ref}")

obj = MyClass()
weak = weakref.ref(obj, on_finalize)
del obj  # Prints: "Object was destroyed! Ref: <weakref at ...>"
```

---

## 5.10 Object Destruction — `__del__`

### The Finalizer

When an object's reference count hits zero (or the cyclic GC collects it), Python calls `__del__` if defined:

```python
class Resource:
    def __del__(self):
        print(f"Cleaning up {self}")

r = Resource()
del r  # Prints: "Cleaning up <Resource object>"
```

### Problems with `__del__`

| Issue | Explanation |
|-------|-------------|
| Non-deterministic timing | If in a cycle, timing depends on GC |
| Resurrection | `__del__` can create new references to the object |
| Exceptions suppressed | Exceptions in `__del__` are ignored (printed to stderr) |
| Interpreter shutdown | Objects destroyed during shutdown may find globals already `None` |
| Prevents GC of cycles | Objects with `__del__` in cycles were uncollectable (fixed in Python 3.4, PEP 442) |

### Best Practice

Use context managers (`with` statement) instead of `__del__`:

```python
# GOOD:
with open("file.txt") as f:
    data = f.read()
# File closed here, deterministically

# BAD (unreliable):
class FileHolder:
    def __init__(self):
        self.f = open("file.txt")
    def __del__(self):
        self.f.close()  # When does this run? Unknown!
```

---

## 5.11 Life Cycle of an Object — Complete

```
1. CREATION
   - Memory allocated (pymalloc or malloc)
   - ob_refcnt set to 1
   - ob_type set to the type
   - Object-specific initialization (__init__)

2. LIVING
   - References increase/decrease as names are bound/unbound
   - Object participates in computation
   - May be tracked by GC if it's a container

3. DESTRUCTION (refcount reaches 0 OR cyclic GC collects it)
   - __del__ called (if defined)
   - Weak references notified (set to None, callbacks called)
   - References the object held are decremented (cascading deallocation)
   - Memory returned to allocator (pymalloc free list or OS)
```

---

## 5.12 CPython Source: `Py_DECREF`

The core macro that decrements reference counts:

```c
// Include/object.h (simplified)
static inline void Py_DECREF(PyObject *op) {
    if (--op->ob_refcnt == 0) {
        _Py_Dealloc(op);    // Call type's tp_dealloc
    }
}
```

Every time CPython is done using a reference, it calls `Py_DECREF`. If the count hits zero, the object's deallocator runs immediately — this is why CPython has **deterministic destruction** (unlike Java/Go/PyPy which use tracing GC).

---

## 5.13 Advantages and Disadvantages of Reference Counting

| Advantage | Disadvantage |
|-----------|--------------|
| Deterministic destruction | Cannot handle reference cycles |
| Immediate memory reclamation | Overhead on every pointer operation |
| Simple to implement | Thread-unfriendly (GIL needed to protect refcounts) |
| Low latency (no GC pauses) | Memory overhead (refcount field in every object) |
| Cache-friendly (locality) | Cascading deallocations can cause latency spikes |

---


# Part 6 — Garbage Collection

## 6.1 Why Reference Counting Alone Is Insufficient

Reference counting handles ~95% of memory management perfectly. But it has one fatal flaw: **reference cycles**.

```python
# Simple cycle
a = {}
a["self"] = a      # a references itself → refcount never reaches 0

# Mutual cycle
class Node:
    def __init__(self):
        self.next = None

n1 = Node()
n2 = Node()
n1.next = n2
n2.next = n1       # Mutual reference

del n1, n2         # Both have refcount 1 (from each other), but unreachable
```

Without a supplementary mechanism, these objects would leak forever.

---

## 6.2 The Cyclic Garbage Collector

CPython's cyclic GC is a **tracing** collector that specifically handles reference cycles. It only runs on **container objects** (objects that can hold references to other objects: lists, dicts, sets, classes, instances, etc.).

### Key Design Decision

Only container objects can form cycles. Immutable objects like `int`, `str`, `float`, `None` (and tuples containing only immutables) cannot participate in cycles and are never tracked by the GC.

```python
import gc

# Tracked (container):
gc.is_tracked([1, 2, 3])       # True
gc.is_tracked({"a": 1})        # True
gc.is_tracked(object())        # True

# NOT tracked (non-container or optimized out):
gc.is_tracked(42)              # False
gc.is_tracked("hello")         # False
gc.is_tracked((1, 2, 3))      # False (tuple of only immutables)
gc.is_tracked(([1,2],))       # True (tuple containing a mutable)
```

---

## 6.3 How the Cyclic GC Works

### The Algorithm — Cycle Detection

The algorithm is based on **trial deletion**:

1. **For each container object in the generation being collected:**
   - Make a copy of its reference count (`gc_refs = ob_refcnt`)

2. **Subtract internal references:**
   - For each container object, iterate over its referents (objects it points to)
   - Decrement the `gc_refs` of each referent

3. **After this pass:**
   - Objects with `gc_refs > 0` are reachable from outside the set → definitely alive
   - Objects with `gc_refs == 0` are only referenced from within the set → potentially garbage

4. **Move reachable objects to a "survivors" list:**
   - Starting from objects with `gc_refs > 0`, traverse all objects they reference
   - Move these to the survivors list (they're reachable)

5. **Everything remaining is garbage** — collect it.

### Visual Example

```
Before GC:
    Outside world
         │
         ▼
    ┌────────┐     ┌────────┐     ┌────────┐
    │ A      │────►│ B      │────►│ C      │
    │ refs:2 │     │ refs:1 │     │ refs:1 │
    └────────┘     └────────┘     └────────┘
         ▲                              │
         └──────────────────────────────┘

Step 1: gc_refs = ob_refcnt
    A: gc_refs = 2
    B: gc_refs = 1
    C: gc_refs = 1

Step 2: Subtract internal references
    A references B: B.gc_refs -= 1 → 0
    B references C: C.gc_refs -= 1 → 0
    C references A: A.gc_refs -= 1 → 1

Step 3: A has gc_refs > 0 → reachable from outside
    Traverse from A: A → B → C all reachable
    
Result: Nothing collected (all reachable via the outside reference to A)
```

Now if we `del` the external reference to A:

```
    ┌────────┐     ┌────────┐     ┌────────┐
    │ A      │────►│ B      │────►│ C      │
    │ refs:1 │     │ refs:1 │     │ refs:1 │
    └────────┘     └────────┘     └────────┘
         ▲                              │
         └──────────────────────────────┘

Step 2: Subtract internal references
    A.gc_refs: 1 - 1 (from C) = 0
    B.gc_refs: 1 - 1 (from A) = 0
    C.gc_refs: 1 - 1 (from B) = 0

Step 3: ALL have gc_refs == 0 → no external references → GARBAGE
Result: All three collected
```

---

## 6.4 Generational Garbage Collection

### The Generational Hypothesis

Observation from decades of GC research:
> Most objects die young. Objects that survive multiple collections tend to live for a long time.

### CPython's Three Generations

| Generation | Contains | Collection Frequency |
|-----------|----------|---------------------|
| 0 (young) | Newly created objects | Most frequent |
| 1 (middle) | Survived 1 collection | Less frequent |
| 2 (old) | Survived 2+ collections | Least frequent |

### How It Works

1. New container objects are added to generation 0
2. When generation 0's threshold is reached, collect generation 0
3. Survivors of gen 0 are promoted to generation 1
4. When generation 1's threshold is reached, collect generations 0 and 1
5. Survivors of gen 1 are promoted to generation 2
6. When generation 2's threshold is reached, collect all generations

### Thresholds

```python
import gc
print(gc.get_threshold())  # (700, 10, 10) by default
```

- **700:** Collect generation 0 after 700 allocations minus deallocations
- **10:** Collect generation 1 after generation 0 has been collected 10 times
- **10:** Collect generation 2 after generation 1 has been collected 10 times

### Tuning

```python
gc.set_threshold(1000, 15, 15)  # Less frequent collection
gc.set_threshold(100, 5, 5)     # More frequent collection
```

---

## 6.5 When GC Runs

The GC runs:
1. **Automatically** when the allocation counter exceeds the threshold
2. **Explicitly** when you call `gc.collect()`
3. **At interpreter shutdown** (final cleanup)

```python
import gc

# Force collection:
collected = gc.collect()      # Returns number of unreachable objects found
print(f"Collected {collected} objects")

# Collect specific generation:
gc.collect(0)   # Only generation 0
gc.collect(1)   # Generations 0 and 1
gc.collect(2)   # All generations (same as gc.collect())
```

---

## 6.6 The `gc` Module

### Key Functions

```python
import gc

# Enable/disable automatic garbage collection
gc.enable()
gc.disable()
gc.isenabled()

# Manual collection
gc.collect(generation=2)

# Inspect objects
gc.get_objects()              # All tracked objects
gc.get_objects(generation=0)  # Objects in specific generation (Python 3.8+)

# Find what references an object
gc.get_referrers(obj)         # Objects that reference obj
gc.get_referents(obj)         # Objects that obj references

# Thresholds
gc.get_threshold()
gc.set_threshold(threshold0, threshold1, threshold2)

# Statistics
gc.get_stats()                # Collection statistics per generation

# Uncollectable objects (objects with __del__ in cycles, pre-3.4)
gc.garbage                    # List of uncollectable objects

# Debug flags
gc.set_debug(gc.DEBUG_LEAK)   # Print info about leaks
gc.set_debug(gc.DEBUG_STATS)  # Print collection statistics
```

### Finding Memory Leaks

```python
import gc

# Before the operation:
gc.collect()
gc.set_debug(gc.DEBUG_SAVEALL)

# ... perform operation that might leak ...

gc.collect()
print(f"Leaked objects: {len(gc.garbage)}")
for obj in gc.garbage:
    print(type(obj), repr(obj)[:100])
```

### Using `gc.get_referrers()` for Debugging

```python
import gc

class MyClass:
    pass

obj = MyClass()
container = [obj]
data = {"key": obj}

# What's holding references to obj?
referrers = gc.get_referrers(obj)
for r in referrers:
    print(type(r), id(r))
# Output: <class 'list'>, <class 'dict'>, <class 'frame'> (the local scope)
```

---

## 6.7 Common Production Issues

### Issue 1: Disabling GC in Performance-Critical Code

Some applications (like Instagram's Python backend) disable the GC entirely:

```python
import gc
gc.disable()  # No more cyclic GC

# Now you MUST ensure no reference cycles exist
# Or accept memory leaks as a tradeoff for performance
```

Why? The GC causes:
- Latency spikes (stop-the-world collection)
- Cache pollution (traversing all tracked objects)
- Copy-on-write issues with `fork()` (touching refcounts dirties pages)

### Issue 2: `__del__` and Cycles (Pre-Python 3.4)

Before Python 3.4 (PEP 442), objects with `__del__` in a reference cycle were **uncollectable**:

```python
class Resource:
    def __del__(self):
        print("Cleaning up")

# Cycle with finalizer — was uncollectable before Python 3.4
a = Resource()
b = Resource()
a.ref = b
b.ref = a
del a, b
# Pre-3.4: Objects put in gc.garbage, never freed
# Post-3.4: Safe finalization — GC can collect these
```

### Issue 3: Copy-on-Write with `fork()`

When a process forks (common in web servers), reference count updates dirty memory pages, defeating copy-on-write optimization. The GC exacerbates this by traversing all objects.

Solution: Disable GC before fork, re-enable in child:
```python
import gc, os

gc.collect()     # Clean up first
gc.disable()     # Freeze refcounts
pid = os.fork()
if pid == 0:
    gc.enable()  # Re-enable in child
```

---

## 6.8 GC in Other Implementations

| Implementation | GC Strategy |
|---------------|-------------|
| **CPython** | Reference counting + generational cyclic GC |
| **PyPy** | Tracing GC (no reference counting) — no deterministic destruction |
| **Jython** | JVM garbage collector |
| **MicroPython** | Reference counting only (no cyclic GC in some builds) |
| **GraalPython** | GraalVM GC |

### Implication for Portable Code

Never rely on deterministic destruction (don't assume `__del__` runs immediately when the last reference is dropped). Use `with` statements for resource management.

---


# Part 7 — Python Process Memory

## 7.1 Process Memory Layout (Linux/x86-64)

When CPython runs, it's a regular user-space process. The OS gives it a virtual address space:

```
High addresses
┌─────────────────────────────────┐ 0x7FFF...
│          KERNEL SPACE           │ (not accessible to process)
├─────────────────────────────────┤
│            STACK                │ ← grows downward
│  (C function call frames)      │
│  (local C variables)           │
│  (return addresses)            │
│                                 │
│            ↓↓↓                  │
├─────────────────────────────────┤
│                                 │
│      (unmapped gap)             │
│                                 │
├─────────────────────────────────┤
│            ↑↑↑                  │
│                                 │
│            HEAP                 │ ← grows upward
│  (malloc allocations)          │
│  (ALL Python objects live here) │
│  (PyMalloc arenas)             │
├─────────────────────────────────┤
│            BSS                  │ (uninitialized global data)
├─────────────────────────────────┤
│            DATA                 │ (initialized global data)
│  (small_ints array lives here) │
│  (_Py_NoneStruct lives here)   │
├─────────────────────────────────┤
│            TEXT (CODE)          │ (machine code of the interpreter)
│  (CPython eval loop)           │
│  (built-in functions' C code)  │
└─────────────────────────────────┘ 0x0000...
Low addresses
```

---

## 7.2 Segments Explained

### TEXT (Code) Segment

Contains the compiled machine code of the CPython interpreter itself. This is the C code that was compiled when you built Python.

- Read-only and executable
- Shared among all processes running the same Python binary (via memory mapping)
- Contains: the eval loop (`Python/ceval.c` compiled), built-in functions, type implementations

**Does NOT contain your Python code.** Your Python code is stored as bytecode objects on the heap.

### DATA Segment

Contains initialized static/global C variables:

```c
// These live in the DATA segment:
static PyLongObject small_ints[262];        // Pre-allocated integers -5..256
PyObject _Py_NoneStruct;                     // The None singleton
PyObject _Py_TrueStruct;                     // The True singleton
PyObject _Py_FalseStruct;                    // The False singleton
```

### BSS Segment

Uninitialized (zero-initialized) global variables. Takes no space in the binary file.

### HEAP

**This is where all Python objects live** (except a few statically allocated singletons).

The heap is managed by:
1. The OS (via `mmap` or `brk` system calls)
2. The C library allocator (`malloc`/`free`)
3. CPython's own allocator (`pymalloc`) — sits on top of `malloc`

```
HEAP layout (conceptual):
┌─────────────────────────────────────────────┐
│  PyMalloc Arena 1 (256 KB)                  │
│  ┌─────────────────────────────────────┐    │
│  │ Pool (4 KB) - size class 32 bytes   │    │
│  │ Pool (4 KB) - size class 48 bytes   │    │
│  │ Pool (4 KB) - size class 64 bytes   │    │
│  │ ...                                  │    │
│  └─────────────────────────────────────┘    │
├─────────────────────────────────────────────┤
│  PyMalloc Arena 2 (256 KB)                  │
│  ...                                        │
├─────────────────────────────────────────────┤
│  Large object (> 512 bytes, via malloc)     │
├─────────────────────────────────────────────┤
│  Large object (via malloc)                  │
├─────────────────────────────────────────────┤
│  Code objects (bytecode) — heap allocated   │
├─────────────────────────────────────────────┤
│  Frame objects — heap allocated              │
└─────────────────────────────────────────────┘
```

### STACK

The C stack is used for:
- CPython's own function calls (the C functions that implement the interpreter)
- Local C variables
- The recursive calls when CPython's eval loop calls itself (nested Python function calls via C)

**Python's "call stack" is NOT the C stack.** Python frames are heap-allocated objects linked together. The C stack just holds the `_PyEval_EvalFrameDefault` recursion (one C frame per Python frame, approximately).

---

## 7.3 Python Frames vs C Stack

### Python Frame Objects

Every Python function call creates a frame object (`PyFrameObject`) on the **heap**:

```c
// Include/cpython/frameobject.h (simplified)
typedef struct _frame {
    PyObject_HEAD
    struct _frame *f_back;     // Previous frame (caller)
    PyCodeObject *f_code;      // Code object being executed
    PyObject *f_builtins;      // Built-in namespace
    PyObject *f_globals;       // Global namespace
    PyObject *f_locals;        // Local namespace (may be NULL)
    PyObject **f_stacktop;     // Top of value stack
    PyObject *f_localsplus[1]; // Locals + cell vars + free vars + stack
} PyFrameObject;
```

### Relationship Between Python Frames and C Stack

```
C Stack (grows down):                Python Frame chain (heap):
┌──────────────────────┐
│ _PyEval_EvalFrame()  │──────────► ┌─────────────────┐
│   (executing foo())  │            │ Frame: foo()    │
├──────────────────────┤            │ f_back ─────────────┐
│ _PyEval_EvalFrame()  │──────────► ┌─────────────────┐   │
│   (executing bar())  │            │ Frame: bar()    │◄──┘
├──────────────────────┤            │ f_back ─────────────┐
│ _PyEval_EvalFrame()  │──────────► ┌─────────────────┐   │
│   (executing main()) │            │ Frame: main()   │◄──┘
├──────────────────────┤            │ f_back = NULL   │
│ pymain_run_file()    │            └─────────────────┘
├──────────────────────┤
│ main()               │
└──────────────────────┘
```

Each Python function call results in:
1. A new `PyFrameObject` allocated on the heap
2. A new C stack frame for `_PyEval_EvalFrameDefault`

### Python's Recursion Limit

```python
import sys
sys.getrecursionlimit()    # Default: 1000
sys.setrecursionlimit(5000)
```

This limits Python frame depth, primarily to prevent C stack overflow (since each Python frame also uses a C stack frame for the eval loop).

---

## 7.4 The Evaluation Stack

Each frame has its own evaluation stack (stored in `f_localsplus` at an offset). This is where intermediate values live during bytecode execution:

```python
result = a + b * c
```

Bytecode:
```
LOAD_FAST    b        # Push b onto eval stack
LOAD_FAST    c        # Push c onto eval stack
BINARY_MULTIPLY       # Pop b and c, push b*c
LOAD_FAST    a        # Push a onto eval stack
BINARY_ADD            # Pop a and (b*c), push a+(b*c)
STORE_FAST   result   # Pop result, store in locals
```

The eval stack is part of the frame object (heap-allocated), NOT the C stack.

---

## 7.5 Where Everything Lives — Summary

| Thing | Memory Location |
|-------|----------------|
| CPython interpreter machine code | TEXT segment |
| `None`, `True`, `False` | DATA segment (static allocation) |
| Small integers (-5 to 256) | DATA segment (static array) |
| All other Python objects | HEAP (via pymalloc or malloc) |
| Python bytecode (code objects) | HEAP |
| Frame objects | HEAP |
| Evaluation stack | HEAP (inside frame object) |
| Local variable names (at runtime) | HEAP (in code object's `co_varnames`) |
| Local variable values | HEAP (in frame's `f_localsplus`) |
| C interpreter local variables | C STACK |
| Return addresses | C STACK |

### Key Insight

> In CPython, the only things on the C stack are the interpreter's own mechanics. Every single Python-level value, name, frame, and structure is on the heap.

---

## 7.6 Memory Addressing

On a 64-bit system:
- Virtual address space: 2^48 bytes (256 TB) on x86-64 (only 48 bits used currently)
- Heap grows upward from low addresses
- Stack grows downward from high addresses
- `id(obj)` returns the heap address where the object lives

```python
import ctypes

x = [1, 2, 3]
addr = id(x)
print(f"Object at address: 0x{addr:016x}")

# You can even peek at the memory (dangerous!):
# ctypes.cast(addr, ctypes.py_object).value  # Gets the object back
```

---


# Part 8 — PyMalloc

## 8.1 Why Python Does Not Call `malloc` Every Time

### The Problem

Python creates and destroys objects at an extremely high rate. A simple `for i in range(1000000)` creates one million integer objects (though many are cached). Calling `malloc`/`free` for each one would be disastrously slow because:

1. `malloc` has overhead (metadata per allocation, lock contention, fragmentation management)
2. System calls (`brk`/`mmap`) are expensive
3. Small allocations waste space due to alignment requirements
4. The OS allocator is general-purpose — not optimized for Python's patterns

### The Solution: PyMalloc

CPython implements its own allocator (`pymalloc`) optimized for Python's allocation patterns:
- Many small, short-lived objects
- Frequent allocation/deallocation
- Objects tend to be similar sizes (28-byte ints, 50-byte strings, etc.)

---

## 8.2 The Three-Layer Allocator Architecture

```
┌───────────────────────────────────────────────────────┐
│  Layer 3: Object-specific allocators                   │
│  (int free list, float free list, tuple free lists)    │
├───────────────────────────────────────────────────────┤
│  Layer 2: Python's object allocator (pymalloc)         │
│  Arena → Pool → Block                                  │
│  Handles allocations ≤ 512 bytes                       │
├───────────────────────────────────────────────────────┤
│  Layer 1: Python's raw memory allocator                │
│  (wraps malloc/realloc/free)                           │
│  Handles allocations > 512 bytes                       │
├───────────────────────────────────────────────────────┤
│  Layer 0: OS allocator (malloc, mmap, brk)             │
│  Provides raw memory from the OS                       │
└───────────────────────────────────────────────────────┘
```

---

## 8.3 Arena → Pool → Block

### Block

The smallest unit of allocation. A block is what gets returned to a Python object.

- Blocks are aligned to their size class
- A single pool contains blocks all of the same size class

### Pool

A pool is a **4 KB** chunk of memory (same as a memory page on most systems).

- Each pool serves one **size class**
- Contains multiple blocks of that size class
- Has a free list of available blocks within it

### Arena

An arena is a **256 KB** chunk allocated from the OS via `malloc`/`mmap`.

- Contains 64 pools (256 KB / 4 KB = 64)
- Arenas are the unit of memory returned to the OS

```
Arena (256 KB):
┌─────────────────────────────────────────────────────────┐
│  Pool 0 (4 KB)        Pool 1 (4 KB)       Pool 2...    │
│  ┌──────────────┐    ┌──────────────┐                   │
│  │ size class:  │    │ size class:  │                   │
│  │ 32 bytes     │    │ 64 bytes     │                   │
│  │              │    │              │                   │
│  │ ┌──┐┌──┐┌──┐│    │ ┌────┐┌────┐ │                   │
│  │ │32││32││32││    │ │ 64 ││ 64 │ │                   │
│  │ └──┘└──┘└──┘│    │ └────┘└────┘ │                   │
│  │ ┌──┐┌──┐┌──┐│    │ ┌────┐┌────┐ │                   │
│  │ │32││32││32││    │ │ 64 ││ 64 │ │                   │
│  │ └──┘└──┘└──┘│    │ └────┘└────┘ │                   │
│  │ ...          │    │ ...          │                   │
│  └──────────────┘    └──────────────┘                   │
└─────────────────────────────────────────────────────────┘
```

---

## 8.4 Size Classes

PyMalloc divides allocations into size classes with 16-byte granularity (as of Python 3.x):

| Request size (bytes) | Size class (bytes) | Blocks per pool (4096 bytes) |
|---------------------|-------------------|------------------------------|
| 1–16 | 16 | 256 |
| 17–32 | 32 | 128 |
| 33–48 | 48 | 85 |
| 49–64 | 64 | 64 |
| 65–80 | 80 | 51 |
| 81–96 | 96 | 42 |
| ... | ... | ... |
| 497–512 | 512 | 8 |

If you request 28 bytes (a typical `int`), you get a 32-byte block.  
If you request 1 byte, you get a 16-byte block.

**Internal fragmentation:** The difference between what you requested and what you get. For a 28-byte int in a 32-byte block, 4 bytes are wasted. This is the price of efficient allocation.

---

## 8.5 Pool States

Each pool has one of three states:

| State | Meaning |
|-------|---------|
| **Full** | All blocks allocated, no free blocks |
| **Used** | Some blocks allocated, some free (has a free list) |
| **Empty** | All blocks free, pool is unassigned to any size class |

Allocation prefers **used** pools (they already have blocks available). Empty pools are kept as a reserve that can be assigned to any size class on demand.

---

## 8.6 Free Lists Within Pools

Each used pool maintains a singly-linked free list of available blocks:

```
Pool (size class 32):
┌────────────────────────────────────────────┐
│ Header:                                     │
│   nextoffset: points to next virgin block   │
│   freeblock: head of free list ─────────┐   │
│   maxnextoffset: end of pool            │   │
├─────────────────────────────────────────┤   │
│ Block 0: [ALLOCATED - int object]       │   │
├─────────────────────────────────────────┤   │
│ Block 1: [FREE] ◄──────────────────────┘   │
│           next ──────────────────────┐      │
├─────────────────────────────────────────┤   │
│ Block 2: [ALLOCATED - int object]       │   │
├─────────────────────────────────────────┤   │
│ Block 3: [FREE] ◄───────────────────┘      │
│           next → NULL                       │
├─────────────────────────────────────────┤   │
│ Block 4: [VIRGIN - never allocated]     │   │
│ ...                                      │   │
└────────────────────────────────────────────┘
```

When a block is freed, it's prepended to the pool's free list (O(1)).  
When a block is needed, it's popped from the free list (O(1)).

---

## 8.7 The Allocation Algorithm

```
pymalloc_alloc(size):
    if size > 512 bytes:
        return malloc(size)  // Use system allocator for large objects
    
    size_class_index = (size - 1) / 16  // Determine size class
    pool = usedpools[size_class_index]   // Get a used pool for this class
    
    if pool has free blocks:
        block = pool.freeblock           // Pop from free list
        pool.freeblock = block.next
        return block
    
    if pool has virgin blocks:
        block = pool + pool.nextoffset   // Use next virgin block
        pool.nextoffset += size_class
        return block
    
    // Need a new pool:
    arena = find_arena_with_free_pool()
    pool = arena.get_empty_pool()
    pool.size_class = size_class_index
    initialize_pool(pool)
    return allocate_from_pool(pool)
```

---

## 8.8 Returning Memory to the OS

### The Problem

PyMalloc can only return entire **arenas** to the OS. Even if 63 out of 64 pools in an arena are empty, that single used pool prevents the arena from being freed.

### The Strategy

- Arenas are sorted by how full they are
- The allocator prefers to allocate from the **fullest** arena
- This concentrates objects in fewer arenas, increasing the chance that other arenas become completely empty and can be freed

### Why Python Process Memory Doesn't Shrink

This is a common production issue:

```python
# Allocate a lot of objects
big_list = [object() for _ in range(10_000_000)]

# Free them
del big_list
import gc
gc.collect()

# Process memory is still high!
# Why? The arenas are fragmented — some blocks still in use scattered across arenas
```

Even after deallocation, the process's RSS (Resident Set Size) may not decrease because:
1. Arenas may not be completely empty
2. `malloc` itself may not return memory to the OS
3. The OS may keep pages mapped even if freed

### When Memory IS Returned

Memory is returned to the OS when:
1. An entire arena becomes empty (all 64 pools have all blocks free)
2. PyMalloc calls `free()` on the arena
3. The OS may or may not actually reclaim the physical pages (depends on OS)

---

## 8.9 Object-Specific Free Lists (Layer 3)

On top of pymalloc, CPython maintains **free lists** for frequently allocated types:

| Type | Free List Size | Purpose |
|------|---------------|---------|
| `float` | 100 objects | Avoid re-creating float structs |
| `tuple` | 20 per size (0-19) | Small tuples are extremely common |
| `list` | 80 objects | List wrappers (not their internal arrays) |
| `dict` | 80 objects | Dict structs |
| `frame` | Variable | Frame reuse for same code |

When a float is "freed," its memory isn't returned to pymalloc. Instead, it goes on the float free list. Next time a float is needed, it's grabbed from the free list — faster than calling pymalloc.

```python
# This is why:
import sys
a = 3.14
print(sys.getsizeof(a))  # 24 bytes

# If you create and destroy floats rapidly:
for _ in range(1000000):
    x = 1.5  # Reuses memory from float free list
```

### Clearing Free Lists

```python
# Python 3.3+: clear all free lists
# (Happens automatically during full GC collection)

# You can force it:
gc.collect()  # Full collection also clears free lists
```

---

## 8.10 Large Object Allocation

Objects larger than 512 bytes bypass pymalloc entirely:

```python
big_string = "x" * 10000     # Allocated via malloc directly
big_list = list(range(100))  # Internal array may exceed 512 bytes → malloc
```

These go directly through the system allocator. They're returned to the OS via `free()` when deallocated (subject to the system allocator's behavior).

---

## 8.11 Memory Allocator Summary

```
Request: "I need 28 bytes for an integer"

1. Layer 3: Is there a free int object on the int free list? 
   → Yes? Return it. Done.
   → No? Go to Layer 2.

2. Layer 2 (pymalloc): Size = 28, size class = 32 (round up to multiple of 16)
   → Find a used pool for size class 32
   → Pop a free block from the pool's free list
   → Return the 32-byte block
   
   (If no pool available: grab empty pool from arena,
    If no arena available: malloc(256KB) for new arena)

3. Layer 1: Only used for > 512 byte allocations
   → Call malloc(size) directly

4. Layer 0: OS provides memory via mmap/brk
   → Rarely interacted with directly
```

---

## 8.12 Relationship with Operating System Memory

```
Python requests memory:
    pymalloc → malloc() → mmap()/brk() → OS kernel → physical RAM

Python frees memory:
    pymalloc free list ← (block freed, stays in pool)
    OR: free(arena) → munmap() → OS kernel reclaims pages
```

### Virtual vs Physical Memory

- **Virtual memory:** What the process sees (address space). May be much larger than physical RAM.
- **Resident Set Size (RSS):** Physical RAM actually used by the process.
- **Virtual Size (VSZ):** Total virtual address space allocated.

```python
# Check process memory (Linux):
import resource
print(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)  # Peak RSS in KB
```

---


# Part 9 — CPython Object Layout

## 9.1 PyObject — The Universal Base

Every Python object in CPython starts with this header:

```c
// Include/object.h
typedef struct _object {
    Py_ssize_t ob_refcnt;       // 8 bytes on 64-bit
    PyTypeObject *ob_type;      // 8 bytes (pointer)
} PyObject;
```

Total header size: **16 bytes** on a 64-bit system.

This means the absolute minimum size of any Python object is 16 bytes.

---

## 9.2 PyVarObject — Variable-Sized Objects

Objects that contain a variable number of items (lists, tuples, strings, ints) extend the header:

```c
typedef struct {
    PyObject ob_base;           // 16 bytes (refcnt + type pointer)
    Py_ssize_t ob_size;         // 8 bytes (number of items)
} PyVarObject;
```

Total header size: **24 bytes**.

---

## 9.3 Reference Count Field (`ob_refcnt`)

```c
Py_ssize_t ob_refcnt;  // Signed pointer-sized integer
```

- 8 bytes on 64-bit systems
- Tracks how many references point to this object
- Manipulated by `Py_INCREF()` / `Py_DECREF()` macros
- When it reaches 0, the object is immediately deallocated

**Python 3.12+ note:** CPython introduced "immortal objects" with a special refcount value that is never modified (optimization for `None`, `True`, `False`, small ints — avoids cache line bouncing in multi-core scenarios).

---

## 9.4 Type Pointer (`ob_type`)

```c
PyTypeObject *ob_type;  // Pointer to the type object
```

- Points to the type object that describes this object's behavior
- For `10`, this points to the `PyLong_Type` struct
- For `[1,2,3]`, this points to `PyList_Type`
- `type(obj)` in Python just dereferences this pointer

---

## 9.5 How Integers Look in Memory

### CPython's Integer (PyLongObject)

Python integers have arbitrary precision. They're stored as arrays of "digits":

```c
// Include/cpython/longintrepr.h (simplified)
typedef struct _longobject {
    PyObject_VAR_HEAD              // ob_refcnt + ob_type + ob_size
    digit ob_digit[1];             // Array of digits (flexible array)
} PyLongObject;

// A "digit" is a 30-bit value stored in a 32-bit integer
typedef uint32_t digit;
#define PyLong_SHIFT 30            // Each digit holds 30 bits
```

### Memory Layout of `int(10)`

```
┌──────────────────────────────────────────┐
│ ob_refcnt:    8 bytes (e.g., 5)          │  ← reference count
│ ob_type:      8 bytes (→ PyLong_Type)    │  ← type pointer
│ ob_size:      8 bytes (1)                │  ← number of digits
│ ob_digit[0]:  4 bytes (10)               │  ← the value
│ [padding]:    4 bytes                    │  ← alignment padding
└──────────────────────────────────────────┘
Total: 28 bytes (+ 4 padding = 32 bytes in pymalloc block)
```

`sys.getsizeof(10)` returns **28** bytes.

### Large Integers

```python
import sys
sys.getsizeof(0)              # 28 bytes (0 digits, but base overhead)
sys.getsizeof(1)              # 28 bytes (1 digit)
sys.getsizeof(2**30 - 1)     # 28 bytes (1 digit, max value per digit)
sys.getsizeof(2**30)         # 32 bytes (2 digits!)
sys.getsizeof(2**60)         # 36 bytes (3 digits)
```

Each additional 30 bits of magnitude costs 4 bytes.

---

## 9.6 How Strings Look in Memory

### CPython's String (PyUnicodeObject)

CPython uses a compact representation that adapts to the string's content:

```c
// Simplified from Include/cpython/unicodeobject.h
typedef struct {
    PyObject_HEAD                  // refcnt + type
    Py_hash_t hash;               // Cached hash (-1 if not computed)
    Py_ssize_t length;            // Number of characters
    // State information:
    unsigned int kind:3;          // 1=Latin1, 2=UCS2, 4=UCS4
    unsigned int compact:1;
    unsigned int ascii:1;
    // ... more flags ...
    // Data follows immediately after the struct (compact form)
} PyUnicodeObject;
```

### String Kind (Character Width)

| Kind | Bytes per char | Used when |
|------|---------------|-----------|
| PyUnicode_1BYTE_KIND | 1 | All chars ≤ U+00FF (Latin-1/ASCII) |
| PyUnicode_2BYTE_KIND | 2 | Any char > U+00FF and ≤ U+FFFF (BMP) |
| PyUnicode_4BYTE_KIND | 4 | Any char > U+FFFF (emoji, rare CJK) |

```python
import sys
sys.getsizeof("a")          # 50 bytes (ASCII, 1 byte/char + overhead)
sys.getsizeof("à")          # 74 bytes (Latin-1, 1 byte/char + overhead)
sys.getsizeof("中")         # 76 bytes (UCS-2, 2 bytes/char + overhead)
sys.getsizeof("😀")         # 80 bytes (UCS-4, 4 bytes/char + overhead)

# A single emoji forces ALL chars to 4 bytes:
sys.getsizeof("a" * 100)            # 149 bytes (100 × 1 + 49 overhead)
sys.getsizeof("a" * 99 + "😀")     # 449 bytes (100 × 4 + 49 overhead)
```

---

## 9.7 How Tuples Look in Memory

```c
typedef struct {
    PyObject_VAR_HEAD              // refcnt + type + size
    PyObject *ob_item[1];          // Array of pointers to elements
} PyTupleObject;
```

### Memory Layout of `(1, 2, 3)`

```
┌──────────────────────────────────────────┐
│ ob_refcnt:    8 bytes                    │
│ ob_type:      8 bytes (→ PyTuple_Type)   │
│ ob_size:      8 bytes (3)                │
│ ob_item[0]:   8 bytes (→ int(1))         │  ← pointer to element
│ ob_item[1]:   8 bytes (→ int(2))         │  ← pointer to element
│ ob_item[2]:   8 bytes (→ int(3))         │  ← pointer to element
└──────────────────────────────────────────┘
Total: 48 bytes header + 24 bytes pointers = 64 bytes
```

```python
import sys
sys.getsizeof(())         # 40 bytes (empty tuple — just header)
sys.getsizeof((1,))       # 48 bytes (+8 for one pointer)
sys.getsizeof((1, 2))     # 56 bytes (+16 for two pointers)
sys.getsizeof((1, 2, 3))  # 64 bytes (+24 for three pointers)
```

The tuple stores **pointers**, not the objects themselves. The int objects are separate heap allocations.

---

## 9.8 How Lists Look in Memory

```c
typedef struct {
    PyObject_VAR_HEAD              // refcnt + type + ob_size (current length)
    PyObject **ob_item;            // Pointer to array of pointers
    Py_ssize_t allocated;          // Allocated capacity (≥ ob_size)
} PyListObject;
```

### Memory Layout of `[1, 2, 3]`

```
PyListObject (on heap):                 Separate array (on heap):
┌──────────────────────────────┐       ┌────────────────────────┐
│ ob_refcnt:  8 bytes          │       │ slot[0]: → int(1)      │
│ ob_type:    8 bytes          │       │ slot[1]: → int(2)      │
│ ob_size:    8 bytes (3)      │       │ slot[2]: → int(3)      │
│ ob_item:    8 bytes ─────────────►   │ slot[3]: (unused)      │
│ allocated:  8 bytes (e.g., 4)│       │ ...                    │
└──────────────────────────────┘       └────────────────────────┘
```

Key difference from tuple: The list's `ob_item` is a **pointer to a separately allocated array**, not an inline array. This allows the array to be reallocated (grown) independently.

```python
import sys
sys.getsizeof([])           # 56 bytes (empty list, no internal array)
sys.getsizeof([1])          # 64 bytes
sys.getsizeof([1, 2, 3])   # 80 bytes (but internal array may be larger due to overallocation)
```

---

## 9.9 How Dictionaries Look in Memory

CPython 3.6+ uses a **compact dict** implementation (made official in 3.7):

```c
typedef struct {
    PyObject_HEAD
    Py_ssize_t ma_used;            // Number of items
    uint64_t ma_version_tag;       // Version counter (for optimizations)
    PyDictKeysObject *ma_keys;     // Shared keys object
    PyObject **ma_values;          // Values array (for split-table dicts)
} PyDictObject;
```

### The Compact Layout (Python 3.6+)

Before 3.6, dicts used a single hash table where 1/3 to 2/3 of slots were empty. The new design separates the hash table indices from the key-value entries:

```
Indices array (sparse, small entries):
┌───┬───┬───┬───┬───┬───┬───┬───┐
│ - │ 0 │ - │ - │ 1 │ - │ 2 │ - │   (- means empty)
└───┴───┴───┴───┴───┴───┴───┴───┘

Entries array (dense, insertion order):
┌────────────────────────────────────────┐
│ Entry 0: hash=..., key="a", value=1    │
│ Entry 1: hash=..., key="b", value=2    │
│ Entry 2: hash=..., key="c", value=3    │
└────────────────────────────────────────┘
```

This preserves insertion order and uses less memory (indices array entries can be 1 byte for small dicts).

---

## 9.10 How Sets Look in Memory

Sets use a hash table similar to pre-3.6 dicts (since sets don't need to preserve insertion order):

```c
typedef struct {
    PyObject_HEAD
    Py_ssize_t fill;              // Active + dummy entries
    Py_ssize_t used;              // Active entries
    Py_ssize_t mask;              // Hash table size - 1
    setentry *table;              // Hash table
    Py_hash_t hash;               // Hash for frozenset (-1 for set)
    Py_ssize_t finger;            // Search finger for pop()
    setentry smalltable[8];       // Inline small table (optimization)
} PySetObject;
```

For small sets (≤ 8 elements), the hash table is inline in the struct (no separate allocation).

---

## 9.11 Memory Alignment and Padding

On 64-bit systems, the compiler aligns struct members to their natural alignment:

- `Py_ssize_t` (8 bytes): aligned to 8 bytes
- `PyObject*` (8 bytes): aligned to 8 bytes  
- `digit` (4 bytes): aligned to 4 bytes

This can create padding:

```
PyLongObject for small int:
┌────────────────────────────────────────┐
│ ob_refcnt:    8 bytes (offset 0)       │
│ ob_type:      8 bytes (offset 8)       │
│ ob_size:      8 bytes (offset 16)      │
│ ob_digit[0]:  4 bytes (offset 24)      │
│ [padding]:    4 bytes (offset 28)      │  ← wasted
└────────────────────────────────────────┘
Total allocated by pymalloc: 32 bytes (size class 32)
```

---

## 9.12 Object Size Comparison

| Object | `sys.getsizeof()` | Notes |
|--------|-------------------|-------|
| `None` | 16 bytes | Just the header (singleton) |
| `True` | 28 bytes | Bool is subclass of int |
| `0` | 28 bytes | Zero takes same space as 1 |
| `1` | 28 bytes | Small int |
| `2**30` | 32 bytes | Needs 2 digits |
| `3.14` | 24 bytes | Compact float |
| `""` | 49 bytes | Empty string overhead |
| `"a"` | 50 bytes | ASCII string |
| `()` | 40 bytes | Empty tuple |
| `(1,)` | 48 bytes | +8 per element |
| `[]` | 56 bytes | Empty list (no internal array) |
| `{}` | 64 bytes | Empty dict (3.11+) |
| `set()` | 216 bytes | Set with inline table |
| `object()` | 16 bytes | Bare object |

**Important:** `sys.getsizeof()` returns the **shallow** size — it doesn't count objects referenced by the container.

```python
import sys
lst = [[1,2,3], [4,5,6]]
sys.getsizeof(lst)              # ~72 bytes (just the list struct + pointer array)
# Doesn't include the inner lists or the integers!
```

---


# Part 10 — Containers Internals

## 10.1 Lists — Dynamic Arrays

### Internal Structure

A Python list is a dynamic array of **pointers** (not values):

```c
typedef struct {
    PyObject_VAR_HEAD
    PyObject **ob_item;     // Pointer to array of PyObject pointers
    Py_ssize_t allocated;   // Total allocated slots
} PyListObject;
```

The list stores `PyObject*` pointers (8 bytes each on 64-bit), not the actual objects.

### Overallocation Strategy

When a list needs to grow, CPython doesn't allocate exactly what's needed. It **overallocates** to amortize the cost of future appends:

```c
// Objects/listobject.c (simplified)
// Growth pattern: 0, 4, 8, 16, 24, 32, 40, 52, 64, 76, ...
new_allocated = ((size_t)newsize + (newsize >> 3) + 6) & ~(size_t)3;
// Approximately: new_size + new_size/8 + 6, rounded to multiple of 4
```

### Growth Factor Visualization

```python
import sys

lst = []
prev_size = sys.getsizeof(lst)
for i in range(50):
    lst.append(i)
    new_size = sys.getsizeof(lst)
    if new_size != prev_size:
        print(f"Length {len(lst):3d}: allocated {(new_size-56)//8:3d} slots, "
              f"size {new_size} bytes")
        prev_size = new_size
```

Output (approximate):
```
Length   1: allocated   4 slots, size  88 bytes
Length   5: allocated   8 slots, size 120 bytes
Length   9: allocated  16 slots, size 184 bytes
Length  17: allocated  24 slots, size 248 bytes
Length  25: allocated  32 slots, size 312 bytes
Length  33: allocated  40 slots, size 376 bytes
Length  41: allocated  52 slots, size 472 bytes
```

### Time Complexity

| Operation | Average Case | Worst Case | Reason |
|-----------|-------------|------------|--------|
| `lst[i]` | O(1) | O(1) | Direct pointer arithmetic |
| `lst.append(x)` | O(1) amortized | O(n) | Rare reallocation copies all pointers |
| `lst.insert(0, x)` | O(n) | O(n) | Must shift all pointers right |
| `lst.insert(i, x)` | O(n) | O(n) | Must shift pointers after i |
| `lst.pop()` | O(1) | O(1) | Just decrement size |
| `lst.pop(0)` | O(n) | O(n) | Must shift all pointers left |
| `lst.remove(x)` | O(n) | O(n) | Linear search + shift |
| `x in lst` | O(n) | O(n) | Linear search |
| `lst[i] = x` | O(1) | O(1) | Replace pointer |
| `len(lst)` | O(1) | O(1) | Read ob_size |
| `lst.extend(other)` | O(k) | O(n+k) | k = len(other); rare reallocation |
| `lst.sort()` | O(n log n) | O(n log n) | Timsort |

### Memory Layout — Visual

```
After: lst = [10, "hi", 3.14]

PyListObject (56 bytes):         Pointer array (allocated on heap):
┌─────────────────────┐         ┌──────────────────────────────────┐
│ refcnt: 1           │         │ [0]: 0x7f001 → PyLongObject(10)  │
│ type: → PyList_Type │         │ [1]: 0x7f002 → PyUnicodeObj("hi")│
│ ob_size: 3          │         │ [2]: 0x7f003 → PyFloatObject(π)  │
│ ob_item: ───────────────────► │ [3]: NULL (overallocated slot)   │
│ allocated: 4        │         └──────────────────────────────────┘
└─────────────────────┘
```

### `append()` Internals

```c
// Objects/listobject.c (simplified)
static int app1(PyListObject *self, PyObject *v) {
    Py_ssize_t n = PyList_GET_SIZE(self);
    
    if (list_resize(self, n + 1) < 0)  // May overallocate
        return -1;
    
    Py_INCREF(v);
    PyList_SET_ITEM(self, n, v);  // Set pointer at index n
    return 0;
}
```

### `insert(0, x)` — Why It's Expensive

```c
// Must shift all pointers:
// items: [A, B, C, _, _]
// insert(0, X):
// Shift: [_, A, B, C, _]  ← memmove of n pointers
// Write: [X, A, B, C, _]
```

This is why `collections.deque` exists for O(1) operations at both ends.

---

## 10.2 Tuples — Fixed-Size Arrays

### Internal Structure

```c
typedef struct {
    PyObject_VAR_HEAD
    PyObject *ob_item[1];   // Inline array (flexible array member)
} PyTupleObject;
```

Unlike lists, tuple elements are stored **inline** in the struct itself (no separate pointer array).

### Tuple vs List Memory Comparison

```python
import sys
sys.getsizeof((1, 2, 3))   # 64 bytes (40 header + 24 pointers)
sys.getsizeof([1, 2, 3])   # 80+ bytes (56 header + separate array with overallocation)
```

Tuples are more memory-efficient because:
1. No separate array allocation (elements inline)
2. No `allocated` field (fixed size)
3. No overallocation

### Tuple Free Lists

CPython maintains free lists for small tuples:

```c
// Objects/tupleobject.c
static PyTupleObject *free_list[PyTuple_MAXSAVESIZE];  // Size 20
static int numfree[PyTuple_MAXSAVESIZE];
```

Tuples of size 0-19 that are deallocated go on a free list instead of being truly freed. This makes tuple creation/destruction very fast for common sizes.

The empty tuple `()` is a singleton — there's only ever one.

---

## 10.3 Dictionaries — Hash Tables

### The Evolution

- **Pre-3.6:** Combined table (hash, key, value in each slot), 1/3 to 2/3 empty
- **3.6+:** Split design (indices array + dense entries), preserves insertion order
- **3.7:** Insertion order officially guaranteed by language spec

### Hash Table Fundamentals

A hash table maps keys to values using a hash function:

```
key → hash(key) → index into table → find entry
```

### The Compact Dict (Python 3.6+)

```
                    Indices (sparse)           Entries (dense, ordered)
                    ┌───────────────┐         ┌──────────────────────────┐
hash("a") % 8 = 2  │ [0]: -       │         │ Entry 0:                 │
hash("b") % 8 = 5  │ [1]: -       │         │   hash, key="a", val=1   │
hash("c") % 8 = 0  │ [2]: 0  ─────────────► │ Entry 1:                 │
                    │ [3]: -       │         │   hash, key="b", val=2   │
                    │ [4]: -       │         │ Entry 2:                 │
                    │ [5]: 1  ─────────────► │   hash, key="c", val=3   │
                    │ [6]: -       │         └──────────────────────────┘
                    │ [7]: 2  ─────────────►
                    └───────────────┘
```

**Index entries** are tiny (1 byte for dicts ≤ 127 entries, 2 bytes ≤ 32767, etc.)  
**Entries** are dense (no gaps), preserving insertion order.

### Collision Resolution — Open Addressing

Python uses **open addressing** with a perturbation-based probe sequence:

```c
// Simplified probe sequence:
j = hash & mask;
while (table[j] is not empty) {
    if (table[j].key == search_key)
        return found;
    // Perturbed probe:
    j = (5 * j + 1 + perturb) & mask;
    perturb >>= 5;
}
```

This isn't linear probing or quadratic probing — it's a unique probe sequence that uses all bits of the hash value, ensuring all table slots are eventually visited.

### Dict Time Complexity

| Operation | Average | Worst Case | Notes |
|-----------|---------|------------|-------|
| `d[key]` lookup | O(1) | O(n) | Worst case: all keys collide |
| `d[key] = val` | O(1) | O(n) | Amortized with resize |
| `del d[key]` | O(1) | O(n) | |
| `key in d` | O(1) | O(n) | |
| Iteration | O(n) | O(n) | Dense entries → cache-friendly |

### Dict Resizing

The hash table is resized when it becomes 2/3 full:

```
Load factor > 2/3 → resize to next power of 2 that makes load factor < 2/3
```

Resizing is O(n) — all entries must be re-inserted at new positions.

### Key Sharing Dicts (PEP 412)

For instances of the same class, Python shares the keys object:

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

p1 = Point(1, 2)
p2 = Point(3, 4)
# p1.__dict__ and p2.__dict__ share the same PyDictKeysObject
# They only differ in their values arrays
```

This saves significant memory for classes with many instances.

---

## 10.4 Sets — Hash Tables Without Values

### Internal Structure

A set is essentially a dict without values — it stores just keys:

```c
typedef struct {
    PyObject_HEAD
    Py_ssize_t fill;           // Active + dummy entries
    Py_ssize_t used;           // Number of active entries
    Py_ssize_t mask;           // Table size - 1
    setentry *table;           // Array of {hash, key} entries
    Py_hash_t hash;            // Cached hash for frozenset
    Py_ssize_t finger;         // Search start for pop()
    setentry smalltable[8];    // Inline table for small sets
} PySetObject;
```

### The Small Table Optimization

For sets with ≤ 8 elements, the hash table is embedded directly in the `PySetObject` struct (no separate heap allocation).

### Time Complexity

| Operation | Average | Worst |
|-----------|---------|-------|
| `x in s` | O(1) | O(n) |
| `s.add(x)` | O(1) | O(n) |
| `s.remove(x)` | O(1) | O(n) |
| `s \| t` (union) | O(len(s)+len(t)) | |
| `s & t` (intersection) | O(min(len(s),len(t))) | |
| `s - t` (difference) | O(len(s)) | |

---

## 10.5 Pointers vs Values — Why It Matters

Python containers store **pointers to objects**, never the objects themselves.

### Implications

1. **Heterogeneous containers:** Since all pointers are the same size (8 bytes), a list can hold pointers to any type of object.

2. **No data locality:** The objects themselves are scattered across the heap. Iterating a list means following pointers to random locations (cache-unfriendly).

3. **Memory overhead:** Each element costs at minimum 8 bytes (pointer) + the size of the object itself.

```
Python list [1, 2, 3]:

List struct:     Pointer array:        Objects (scattered on heap):
┌──────────┐    ┌──────┐
│ ob_item ──────►│ ptr0 ─────────────────► int(1): 28 bytes
│          │    │ ptr1 ─────────────────► int(2): 28 bytes
│          │    │ ptr2 ─────────────────► int(3): 28 bytes
└──────────┘    └──────┘

Total memory for [1,2,3]: 56 + 24 + 84 = ~164 bytes
Compare to C's int[3]: 12 bytes

NumPy array([1,2,3], dtype=int64):
Header + contiguous buffer: ~120 bytes header + 24 bytes data
The data is CONTIGUOUS: [00..01|00..02|00..03] — cache-friendly!
```

### Why NumPy Is Fast

NumPy arrays store raw values contiguously in memory (like C arrays), not pointers to Python objects. This gives:
- Cache locality (sequential memory access)
- No per-element overhead (no refcount, no type pointer)
- SIMD/vectorization opportunities

---


# Part 11 — Memory Diagrams

## 11.1 Variable Assignment

```python
x = 42
y = x
```

```
    Namespace                        Heap
    ┌──────────────┐
    │ "x": ────────────────────┐
    ├──────────────┤           │
    │ "y": ────────────────────┼──► ┌─────────────────┐
    └──────────────┘           └──► │ PyLongObject    │
                                    │ refcnt: 2       │
                                    │ type: int       │
                                    │ value: 42       │
                                    └─────────────────┘
```

---

## 11.2 Reference Sharing

```python
a = [1, 2, 3]
b = a
c = a
```

```
    Namespace                        Heap
    ┌──────────────┐
    │ "a": ────────────────────┐
    ├──────────────┤           │
    │ "b": ────────────────────┼──► ┌─────────────────────┐
    ├──────────────┤           │    │ PyListObject        │
    │ "c": ────────────────────┘    │ refcnt: 3           │
    └──────────────┘                │ size: 3             │
                                    │ items ─────────────────► [→int(1), →int(2), →int(3)]
                                    │ allocated: 3        │
                                    └─────────────────────┘
```

---

## 11.3 Function Call

```python
def modify(data):
    data.append(4)
    data = [99]       # Rebinding local name

original = [1, 2, 3]
modify(original)
# original is now [1, 2, 3, 4]
```

**Before call:**
```
    Global namespace                 Heap
    ┌──────────────────┐
    │ "original": ─────────────► ┌─────────────────┐
    │ "modify": ───────────┐     │ list [1, 2, 3]  │
    └──────────────────────┘│    │ refcnt: 1       │
                            │    └─────────────────┘
                            ▼
                       ┌──────────────────┐
                       │ function object  │
                       └──────────────────┘
```

**During call (after append, before rebind):**
```
    Global namespace                 Heap
    ┌──────────────────┐
    │ "original": ─────────────┐
    └──────────────────────────┘│
                                ▼
    Local namespace (frame)    ┌──────────────────┐
    ┌──────────────────┐       │ list [1,2,3,4]   │
    │ "data": ─────────────────►│ refcnt: 2       │
    └──────────────────┘       └──────────────────┘
```

**After `data = [99]`:**
```
    Global namespace                 Heap
    ┌──────────────────┐
    │ "original": ─────────────► ┌──────────────────┐
    └──────────────────────────┘ │ list [1,2,3,4]   │
                                 │ refcnt: 1        │
    Local namespace (frame)      └──────────────────┘
    ┌──────────────────┐
    │ "data": ─────────────────► ┌──────────────────┐
    └──────────────────┘         │ list [99]         │
                                 │ refcnt: 1        │
                                 └──────────────────┘
```

---

## 11.4 Stack vs Heap

```python
def outer():
    x = [1, 2]
    def inner():
        return x
    return inner

closure = outer()
result = closure()
```

```
C Stack (during outer() execution):      Heap:
┌──────────────────────────┐
│ _PyEval_EvalFrame(outer) │─────► ┌──────────────────────────┐
│   (C locals, return addr)│       │ Frame: outer()           │
└──────────────────────────┘       │ f_localsplus[0] (x): ────────► ┌────────────┐
                                   │                          │     │ [1, 2]     │
                                   └──────────────────────────┘     │ refcnt: 1  │
                                                                    └────────────┘
                                   ┌──────────────────────────┐
                                   │ Cell object              │
                                   │ cell_contents ─────────────────► (same list)
                                   └──────────────────────────┘
                                          ▲
                                   ┌──────┼───────────────────┐
                                   │ function: inner          │
                                   │ __closure__[0] ──────────┘
                                   └──────────────────────────┘
```

---

## 11.5 Reference Counting

```python
a = [1, 2, 3]      # Step 1
b = a               # Step 2
c = [a, a]          # Step 3
del b               # Step 4
c.pop()             # Step 5
```

```
Step 1: a = [1, 2, 3]
    a ──► list [1,2,3]  refcnt: 1

Step 2: b = a
    a ──► list [1,2,3]  refcnt: 2
    b ──┘

Step 3: c = [a, a]
    a ──► list [1,2,3]  refcnt: 4  (a + b + c[0] + c[1])
    b ──┘      ▲  ▲
    c ──► [────┘  │]
           └──────┘

Step 4: del b
    a ──► list [1,2,3]  refcnt: 3  (a + c[0] + c[1])
               ▲  ▲
    c ──► [────┘  │]
           └──────┘

Step 5: c.pop()  → returns reference to the list, then reference is discarded
    a ──► list [1,2,3]  refcnt: 2  (a + c[0])
               ▲
    c ──► [────┘]
```

---

## 11.6 Garbage Collection (Cycle)

```python
class Node:
    def __init__(self, name):
        self.name = name
        self.ref = None

a = Node("A")
b = Node("B")
a.ref = b         # A → B
b.ref = a         # B → A (cycle!)
del a, b          # Names removed, but cycle persists
```

```
After del a, b — before GC:

    NO external references exist!

    ┌───────────────────┐        ┌───────────────────┐
    │ Node "A"          │        │ Node "B"          │
    │ refcnt: 1         │        │ refcnt: 1         │
    │ ref ──────────────────────►│                   │
    │                   │◄───────────── ref          │
    └───────────────────┘        └───────────────────┘

    Both have refcnt > 0, but UNREACHABLE.
    GC trial deletion detects this and collects both.

After GC runs:
    Both objects deallocated. Memory freed.
```

---

## 11.7 Arena → Pool → Block

```
Arena (256 KB) obtained from OS via malloc/mmap:
┌────────────────────────────────────────────────────────────────────┐
│ Pool 0 (4KB)   │ Pool 1 (4KB)   │ Pool 2 (4KB)   │ ... Pool 63  │
│ class: 32B     │ class: 64B     │ class: 32B     │              │
│ ┌──┬──┬──┬──┐  │ ┌────┬────┬──┐ │ ┌──┬──┬──┬──┐  │              │
│ │██│  │██│██│  │ │████│    │██│ │ │  │  │██│  │  │              │
│ └──┴──┴──┴──┘  │ └────┴────┴──┘ │ └──┴──┴──┴──┘  │              │
│ ██=allocated   │                 │                 │              │
│   =free        │                 │                 │              │
└────────────────────────────────────────────────────────────────────┘

Pool detail (4KB, size class 32):
┌─────────────────────────────────────────────────────────────────┐
│ Pool Header (48 bytes):                                          │
│   ref to next pool, prev pool, arena, size class index          │
│   freeblock pointer, nextoffset                                  │
├─────────────────────────────────────────────────────────────────┤
│ Block 0 (32 bytes): [PyLongObject: value=42, refcnt=3]          │ USED
├─────────────────────────────────────────────────────────────────┤
│ Block 1 (32 bytes): [next_free → Block 3]                        │ FREE
├─────────────────────────────────────────────────────────────────┤
│ Block 2 (32 bytes): [PyLongObject: value=7, refcnt=1]           │ USED
├─────────────────────────────────────────────────────────────────┤
│ Block 3 (32 bytes): [next_free → NULL]                           │ FREE
├─────────────────────────────────────────────────────────────────┤
│ Block 4 (32 bytes): [VIRGIN — never used]                        │ VIRGIN
│ ...                                                              │
└─────────────────────────────────────────────────────────────────┘
Free list: freeblock → Block 1 → Block 3 → NULL
```

---

## 11.8 List Object Internals

```python
lst = [10, "hi", 3.14]
lst.append(True)
```

```
PyListObject:                      Internal array:              Objects:
┌────────────────────┐            ┌──────────────┐
│ refcnt: 1          │            │ [0]: ─────────────────► PyLong(10)   28B
│ type: PyList_Type  │            │ [1]: ─────────────────► PyUnicode("hi") 52B
│ ob_size: 4         │            │ [2]: ─────────────────► PyFloat(3.14) 24B
│ ob_item: ──────────────────────►│ [3]: ─────────────────► PyBool(True) 28B
│ allocated: 4       │            │ [4]: NULL    │  ← overallocated slot
└────────────────────┘            └──────────────┘

After append causes reallocation (if allocated was full):
New internal array (larger, copied from old):
┌──────────────┐
│ [0]: → 10    │  (same objects, pointers copied)
│ [1]: → "hi"  │
│ [2]: → 3.14  │
│ [3]: → True  │
│ [4]: NULL    │  ← new overallocated slots
│ [5]: NULL    │
│ [6]: NULL    │
│ [7]: NULL    │
└──────────────┘
Old array is freed.
```

---

## 11.9 Dictionary Internals

```python
d = {"name": "Alice", "age": 30}
```

```
PyDictObject:                 PyDictKeysObject:
┌──────────────────┐         ┌──────────────────────────────────────────┐
│ refcnt: 1        │         │ Indices array (size 8):                   │
│ type: PyDict_Type│         │ [-1, -1, 0, -1, -1, 1, -1, -1]           │
│ ma_used: 2       │         │        ↑              ↑                   │
│ ma_keys: ────────────────► │  hash("name")%8=2  hash("age")%8=5      │
│ ma_values: NULL  │         │                                           │
└──────────────────┘         │ Entries array (dense):                    │
                             │ ┌──────────────────────────────────────┐  │
                             │ │[0] hash=XX, key="name", val="Alice"  │  │
                             │ │[1] hash=YY, key="age",  val=30       │  │
                             │ └──────────────────────────────────────┘  │
                             └──────────────────────────────────────────┘
```

---

## 11.10 Nested Objects and Deep Copy

```python
import copy

original = [[1, 2], [3, 4]]
shallow = copy.copy(original)
deep = copy.deepcopy(original)
```

```
SHALLOW COPY:
original ──► list_A ──┬──► inner_list_1 [1, 2]
                      └──► inner_list_2 [3, 4]

shallow ───► list_B ──┬──► inner_list_1 [1, 2]  ← SHARED!
                      └──► inner_list_2 [3, 4]  ← SHARED!

list_A ≠ list_B (different objects)
But list_A[0] is list_B[0] (same inner list!)


DEEP COPY:
original ──► list_A ──┬──► inner_list_1 [1, 2]
                      └──► inner_list_2 [3, 4]

deep ──────► list_C ──┬──► inner_list_3 [1, 2]  ← INDEPENDENT COPY
                      └──► inner_list_4 [3, 4]  ← INDEPENDENT COPY

Everything is independent. Mutating deep[0] never affects original.
```

---

## 11.11 Closure Memory

```python
def make_adder(n):
    def add(x):
        return x + n
    return add

add5 = make_adder(5)
add10 = make_adder(10)
```

```
                    Heap:
add5 ──► ┌──────────────────────┐
         │ function: add        │
         │ __code__: (shared)   │────────► code object for 'add'
         │ __closure__[0]: ─────────┐
         └──────────────────────┘   │
                                    ▼
                               ┌──────────┐
                               │ Cell     │
                               │ contents ──────► int(5)
                               └──────────┘

add10 ──► ┌──────────────────────┐
          │ function: add        │
          │ __code__: (shared)   │────────► (same code object!)
          │ __closure__[0]: ─────────┐
          └──────────────────────┘   │
                                     ▼
                                ┌──────────┐
                                │ Cell     │
                                │ contents ──────► int(10)
                                └──────────┘

Both closures share the same code object but have different cell objects.
```

---


# Part 12 — Production Implications

## 12.1 Memory Leaks in Python

### Common Causes

Even with automatic memory management, Python programs can leak memory:

**1. Reference Cycles with External Resources:**
```python
class Handler:
    def __init__(self, connection):
        self.connection = connection
        connection.handler = self  # Cycle!
        # If gc is delayed, the connection stays open
```

**2. Caches That Grow Unbounded:**
```python
_cache = {}

def get_result(key):
    if key not in _cache:
        _cache[key] = expensive_computation(key)
    return _cache[key]
# _cache grows forever — use functools.lru_cache or weakref.WeakValueDictionary
```

**3. Global Variables Accumulating References:**
```python
_all_instances = []

class Widget:
    def __init__(self):
        _all_instances.append(self)  # Never removed!
```

**4. Exception Tracebacks Holding References:**
```python
try:
    process_large_data()
except Exception as e:
    # e.__traceback__ holds references to ALL local variables in the call stack!
    logger.error(f"Error: {e}")
    # Fix: del e or sys.exc_clear() after logging
```

**5. Closures Capturing More Than Needed:**
```python
def process():
    large_data = load_gigabyte_file()
    result = compute(large_data)
    
    def get_result():
        return result  # Captures 'result' — but also keeps frame alive
                       # which keeps 'large_data' alive in some implementations!
    return get_result
```

---

## 12.2 Detecting Memory Leaks

### Using `tracemalloc`

```python
import tracemalloc

tracemalloc.start()

# ... run your code ...

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

print("Top 10 memory consumers:")
for stat in top_stats[:10]:
    print(stat)
```

### Using `objgraph`

```python
import objgraph

# What types have the most instances?
objgraph.show_most_common_types(limit=10)

# What's holding a reference to this object?
objgraph.show_backrefs([my_object], filename='refs.png')

# How many new objects since last call?
objgraph.show_growth()
```

### Using `gc` Module

```python
import gc

gc.set_debug(gc.DEBUG_LEAK)  # Print objects found in cycles
gc.collect()

# Count objects by type:
from collections import Counter
type_counts = Counter(type(obj).__name__ for obj in gc.get_objects())
print(type_counts.most_common(20))
```

---

## 12.3 Reference Cycles in Production

### The Pattern

```python
# Common in: GUIs, event systems, ORMs, networking code
class EventEmitter:
    def __init__(self):
        self.listeners = []
    
    def on(self, callback):
        self.listeners.append(callback)

class Widget:
    def __init__(self, emitter):
        self.emitter = emitter
        emitter.on(self.handle_event)  # Bound method holds ref to self!
        # Cycle: Widget → emitter → listeners → bound_method → Widget
    
    def handle_event(self):
        pass
```

### Solutions

**1. Weak References:**
```python
import weakref

class EventEmitter:
    def __init__(self):
        self.listeners = []
    
    def on(self, callback):
        self.listeners.append(weakref.ref(callback))
```

**2. Explicit Cleanup:**
```python
class Widget:
    def close(self):
        self.emitter.listeners.remove(self.handle_event)
        self.emitter = None
```

**3. Context Managers:**
```python
class Widget:
    def __enter__(self):
        self.emitter.on(self.handle_event)
        return self
    
    def __exit__(self, *args):
        self.emitter.listeners.remove(self.handle_event)
```

---

## 12.4 Performance Implications

### Object Creation Cost

```python
import timeit

# Creating objects has overhead:
timeit.timeit('x = 1.5', number=10_000_000)         # ~0.4s (float from free list)
timeit.timeit('x = object()', number=10_000_000)     # ~0.5s
timeit.timeit('x = [1,2,3]', number=10_000_000)      # ~1.5s (list + array + 3 refs)
timeit.timeit('x = {"a":1}', number=10_000_000)      # ~1.2s (dict + keys + entry)
```

### Mitigation Strategies

**1. `__slots__` for memory-heavy classes:**
```python
class PointRegular:
    def __init__(self, x, y):
        self.x = x
        self.y = y
# Each instance has a __dict__ (~100+ bytes overhead)

class PointSlots:
    __slots__ = ('x', 'y')
    def __init__(self, x, y):
        self.x = x
        self.y = y
# No __dict__ — saves ~100 bytes per instance

import sys
sys.getsizeof(PointRegular(1, 2))        # 48 bytes (+ __dict__: ~100 bytes)
sys.getsizeof(PointSlots(1, 2))          # 48 bytes (total, no dict)
```

**2. Use generators for large sequences:**
```python
# BAD: Creates million-element list in memory
data = [transform(x) for x in range(1_000_000)]

# GOOD: One element at a time
data = (transform(x) for x in range(1_000_000))
```

**3. Use `array` or `numpy` for homogeneous numeric data:**
```python
import array
# Python list of 1M ints: ~28MB (28 bytes × 1M objects + 8MB pointers)
# array of 1M ints: ~4MB (4 bytes × 1M values, contiguous)
arr = array.array('i', range(1_000_000))
```

---

## 12.5 Memory Fragmentation

### The Problem

After many allocations and deallocations, pymalloc's arenas become fragmented:

```
Arena state after prolonged operation:
┌─────────────────────────────────────────────────┐
│ Pool 0: [█░█░░█░█░░█░░░█░░█░█░░░░█]           │
│ Pool 1: [░░░░░░░░░░░░░░░░░░░░░░░░░]  ← empty │
│ Pool 2: [█░░░░░░░░░░░░░░░░░░░░░░░█]  ← 2 objects prevent freeing│
│ Pool 3: [████████████████████████]    ← full  │
│ ...                                             │
└─────────────────────────────────────────────────┘

Pool 2 has only 2 objects but the entire pool (4KB) cannot be reused
for other size classes. The arena cannot be freed either.
```

### Why Process Memory Doesn't Shrink

1. **Internal fragmentation:** Pools with even one live object block the arena from being freed
2. **malloc behavior:** Even if pymalloc frees arenas, `malloc` may not return pages to the OS
3. **OS behavior:** The kernel may keep pages in RSS even after `munmap`

### Mitigation

- Use `gc.collect()` periodically in long-running services
- Use multiprocessing (fork workers that die and release all memory)
- Use memory-mapped files for large data structures
- Consider `jemalloc` or `tcmalloc` as the system allocator (better fragmentation behavior)
- Profile with `tracemalloc` to identify hotspots

---

## 12.6 Large Datasets

### Problem: Everything Is an Object

```python
# A list of 10M integers:
# 10M × 28 bytes (int objects) + 10M × 8 bytes (pointers) = ~360 MB!
data = list(range(10_000_000))

# NumPy equivalent:
# 10M × 8 bytes (raw int64 values) = 80 MB
import numpy as np
data = np.arange(10_000_000)
```

### Solutions for Large Data

| Approach | Use Case | Memory Savings |
|----------|----------|---------------|
| `numpy` arrays | Numeric data | 5-10x less |
| `pandas` with proper dtypes | Tabular data | 2-5x less |
| `array.array` | Homogeneous numeric | 3-7x less |
| Memory-mapped files | Data larger than RAM | Only pages in use loaded |
| Generators | Sequential processing | O(1) memory |
| `__slots__` | Many instances | 40-60% per instance |
| `struct` module | Binary data | No object overhead |

---

## 12.7 Long-Running Servers

### Common Issues

**1. Memory growth over time:**
```python
# Web server handling requests for days:
# - Interned strings accumulate (never freed)
# - GC generations fill up
# - Free lists hold onto memory
# - Fragmentation prevents arena release
```

**2. Copy-on-write after fork:**
```python
# Gunicorn prefork model:
# Parent process loads app, forks workers
# Each refcount update dirties a memory page → defeats CoW
# Workers end up with their own copies of all objects
```

**3. Solution: Worker recycling:**
```python
# Gunicorn config:
max_requests = 1000        # Restart worker after 1000 requests
max_requests_jitter = 100  # Randomize to avoid thundering herd
```

---

## 12.8 Optimization Strategies

### Strategy 1: Avoid Unnecessary Object Creation

```python
# BAD: Creates intermediate string objects
result = ""
for chunk in chunks:
    result += chunk  # O(n²) — new string each iteration

# GOOD: Single allocation
result = "".join(chunks)  # O(n)
```

### Strategy 2: Reuse Objects

```python
# Use __slots__:
class Point:
    __slots__ = ('x', 'y')

# Use flyweight pattern:
_cache = {}
def get_color(name):
    if name not in _cache:
        _cache[name] = Color(name)
    return _cache[name]
```

### Strategy 3: Process Isolation

```python
from multiprocessing import Pool

def process_chunk(data):
    # Runs in separate process — all memory freed when done
    result = heavy_computation(data)
    return result

with Pool(4) as pool:
    results = pool.map(process_chunk, data_chunks)
```

### Strategy 4: Profile Before Optimizing

```python
import tracemalloc

tracemalloc.start()
# ... code ...
current, peak = tracemalloc.get_traced_memory()
print(f"Current: {current / 1024 / 1024:.1f} MB")
print(f"Peak: {peak / 1024 / 1024:.1f} MB")
tracemalloc.stop()
```

---

## 12.9 Common Mistakes

| Mistake | Why It's Bad | Fix |
|---------|-------------|-----|
| Storing everything in global dicts | Never freed | Use `WeakValueDictionary` or LRU cache |
| Mutable default arguments | Accumulate state across calls | Use `None` default + create inside |
| Large closures | Capture entire frame | Extract only needed values |
| Not closing files/connections | OS resources held | Use `with` statements |
| Circular references in data models | GC overhead, delayed cleanup | Use `weakref` for back-references |
| String concatenation in loops | O(n²), n intermediate objects | Use `str.join()` |
| Creating objects in hot loops | GC pressure | Pre-allocate or reuse |
| Ignoring `__slots__` for data classes | 40-60% memory waste per instance | Add `__slots__` |

---

# Part 13 — Interview Section

## 13.1 Beginner Interview Questions (50)

### Questions & Answers

**Q1: What happens when you write `x = 10` in Python?**

A: Python creates (or reuses a cached) integer object with value 10 on the heap, then binds the name `x` to that object in the current namespace. The name `x` is not a box holding 10 — it's a reference to an object.

---

**Q2: Is Python pass-by-value or pass-by-reference?**

A: Neither. Python uses "pass by object reference" (also called "pass by assignment"). The function parameter is bound to the same object as the argument. Mutation of the object is visible to the caller; rebinding the parameter is not.

---

**Q3: What is the difference between `==` and `is`?**

A: `==` checks value equality (calls `__eq__`). `is` checks identity — whether two names refer to the exact same object in memory (compares `id()` values).

---

**Q4: What is a mutable object? Give examples.**

A: A mutable object's value can change after creation without changing its identity. Examples: `list`, `dict`, `set`, `bytearray`, and user-defined class instances (by default).

---

**Q5: What is an immutable object? Give examples.**

A: An immutable object's value cannot change after creation. Any "modification" creates a new object. Examples: `int`, `float`, `str`, `tuple`, `frozenset`, `bytes`, `bool`, `None`.

---

**Q6: Why does Python cache small integers?**

A: CPython caches integers -5 to 256 because they are extremely common. Caching avoids creating millions of duplicate objects and speeds up comparison operations.

---

**Q7: What does `del x` do?**

A: `del x` removes the name `x` from the current namespace and decrements the reference count of the object it pointed to. It does NOT directly free memory — the object is freed only if its reference count reaches zero.

---

**Q8: What is `id()` in Python?**

A: `id(obj)` returns a unique integer identifier for the object, guaranteed unique for the object's lifetime. In CPython, it's the memory address of the object.

---

**Q9: Can a tuple contain mutable objects?**

A: Yes. A tuple's immutability means you can't reassign its slots, but the objects in those slots can be mutable. `t = ([1,2],)` — you can't do `t[0] = other`, but you can do `t[0].append(3)`.

---

**Q10: What is the output of `[] is []`?**

A: `False`. Each `[]` creates a new list object with a different identity.

---

**Q11: What is the output of `() is ()`?**

A: `True`. CPython caches the empty tuple as a singleton.

---

**Q12: What is aliasing?**

A: Aliasing is when multiple names refer to the same object. After `a = [1,2]; b = a`, both `a` and `b` are aliases for the same list.

---

**Q13: What is the difference between shallow copy and deep copy?**

A: A shallow copy creates a new container but the elements inside are still shared references to the same objects. A deep copy recursively copies all nested objects — nothing is shared.

---

**Q14: How do you create a shallow copy of a list?**

A: `lst[:]`, `list(lst)`, `lst.copy()`, or `copy.copy(lst)`.

---

**Q15: Why does `a += [4]` behave differently from `a = a + [4]` for lists?**

A: `a += [4]` calls `list.__iadd__`, which mutates the list in place. `a = a + [4]` calls `list.__add__`, which creates a new list and rebinds `a`.

---

**Q16: What is `type()` used for?**

A: `type(obj)` returns the type of the object. The type determines what operations are valid and how the object behaves.

---

**Q17: Can you change an object's type after creation?**

A: At the language level, no. An object's type is fixed for its lifetime. (Extreme C-API hacks can do it, but this is unsupported and dangerous.)

---

**Q18: What does `sys.getrefcount(x)` return?**

A: The reference count of object `x`. It's always at least 1 more than you'd expect because passing `x` to the function creates a temporary reference.

---

**Q19: What is garbage collection in Python?**

A: Python uses two mechanisms: reference counting (primary, immediate) and a cyclic garbage collector (supplementary, handles reference cycles). Together they manage object deallocation.

---

**Q20: Why can't lists be dictionary keys?**

A: Lists are mutable and unhashable. Dict keys must be hashable (their hash must not change). Since a list's contents can change, its hash would change, corrupting the dict.

---

**Q21: What is string interning?**

A: Interning means Python stores only one copy of certain strings and reuses them. Identifier-like strings and literals are commonly interned, making comparisons faster (pointer check instead of character-by-character).

---

**Q22: What is the output of `"hello" is "hello"`?**

A: Usually `True` due to string interning, but this is a CPython implementation detail, not a language guarantee. Never rely on this.

---

**Q23: What is a namespace in Python?**

A: A namespace is a mapping from names to objects. In CPython, it's typically a dictionary. Examples: module globals, function locals, built-ins.

---

**Q24: What is the LEGB rule?**

A: The order Python looks up names: Local → Enclosing → Global → Built-in. If not found in any, you get `NameError`.

---

**Q25: What does `global` keyword do?**

A: It declares that a name inside a function should refer to the module-level (global) variable, allowing the function to rebind it.

---

**Q26: What does `nonlocal` keyword do?**

A: It declares that a name inside a nested function should refer to the variable in the enclosing function's scope, allowing rebinding.

---

**Q27: What is a closure?**

A: A closure is a function that remembers values from its enclosing scope even after that scope has finished executing. It does this via cell objects.

---

**Q28: Why does `sys.getsizeof(1)` return 28?**

A: On 64-bit CPython, an integer object has: 8 bytes refcount + 8 bytes type pointer + 8 bytes size + 4 bytes digit = 28 bytes.

---

**Q29: What is the `None` object?**

A: `None` is a singleton object of type `NoneType`. There is exactly one `None` object in any Python process. It represents the absence of a value.

---

**Q30: Why should you use `is None` instead of `== None`?**

A: `is` cannot be overridden (it's a pointer comparison), while `==` can be overridden by `__eq__`. An object could make `== None` return `True` unexpectedly. `is` is also faster.

---

**Q31: What happens to a function's local variables after it returns?**

A: Their reference counts are decremented. If an object's refcount reaches 0, it's immediately deallocated. If the object was returned or captured by a closure, it survives.

---

**Q32: What is the difference between `list.sort()` and `sorted(list)`?**

A: `list.sort()` mutates the list in place and returns `None`. `sorted(list)` returns a new sorted list, leaving the original unchanged.

---

**Q33: What is `__slots__`?**

A: A class attribute that replaces the instance `__dict__` with a fixed set of slot descriptors. Saves ~40-60% memory per instance and slightly speeds up attribute access.

---

**Q34: Why does Python use reference counting?**

A: It provides deterministic destruction (objects are freed immediately when the last reference is dropped), which is good for resource management (file handles, connections).

---

**Q35: What are the disadvantages of reference counting?**

A: Cannot handle reference cycles, adds overhead to every pointer operation, requires the GIL for thread safety, and the refcount field uses memory in every object.

---

**Q36: What is a reference cycle?**

A: When two or more objects reference each other, their reference counts never reach zero even when they are unreachable from the program. Example: `a = []; b = []; a.append(b); b.append(a)`.

---

**Q37: How does Python handle reference cycles?**

A: CPython has a cyclic garbage collector that periodically detects unreachable cycles using a trial-deletion algorithm and collects them.

---

**Q38: What is the difference between rebinding and mutation?**

A: Rebinding makes a name point to a different object (`x = new_value`). Mutation changes the internal state of the existing object (`x.append(item)`).

---

**Q39: What is `sys.getsizeof()`?**

A: Returns the shallow memory size of an object in bytes. It counts only the object itself, not objects it references.

---

**Q40: Is Python dynamically or statically typed?**

A: Dynamically typed. Types are associated with objects, not names. A name can be bound to objects of any type at any time.

---

**Q41: What is the `weakref` module used for?**

A: To create references to objects that don't prevent garbage collection. Useful for caches, observer patterns, and breaking reference cycles.

---

**Q42: What is the mutable default argument bug?**

A: Default argument values are evaluated once at function definition time. If a mutable default (like `[]`) is used, it's shared across calls, accumulating mutations.

---

**Q43: How do you avoid the mutable default argument bug?**

A: Use `None` as the default and create the mutable object inside the function: `def f(x=None): x = x if x is not None else []`.

---

**Q44: What does `a = b = []` do?**

A: Creates one list object and binds both `a` and `b` to it. They are aliases for the same object.

---

**Q45: What is the difference between `a = b = []` and `a, b = [], []`?**

A: The first creates one list shared by both names. The second creates two independent lists.

---

**Q46: What is `object()` in Python?**

A: The base object. It's the simplest possible Python object (just a header — 16 bytes). All classes inherit from `object`.

---

**Q47: Can you change a string after creating it?**

A: No. Strings are immutable. Any operation that appears to modify a string actually creates a new string object.

---

**Q48: Why is string concatenation in a loop slow?**

A: Each `+=` creates a new string and copies all previous characters. For n concatenations, total work is O(n²). Use `"".join(parts)` instead (O(n)).

---

**Q49: What is the output of `type(type)`?**

A: `<class 'type'>`. The type of `type` is itself. `type` is its own metaclass.

---

**Q50: What is the difference between `is` and `id()`?**

A: `a is b` is equivalent to `id(a) == id(b)`. `is` directly compares object identity. `id()` returns the identity as an integer that you can store and compare later.

---


## 13.2 Intermediate Interview Questions (50)

### Questions & Answers

**Q1: Explain how Python's generational garbage collector works.**

A: CPython uses three generations (0, 1, 2). New objects go into generation 0. When generation 0's allocation threshold is reached, it's collected. Survivors are promoted to generation 1. When generation 1's threshold is hit, generations 0 and 1 are collected together. Same for generation 2. This exploits the generational hypothesis: most objects die young, so collecting young objects frequently is efficient.

---

**Q2: What is the small integer cache range in CPython and why?**

A: -5 to 256. These integers are pre-allocated at interpreter startup. Since they're extremely common (loop counters, indices, error codes, boolean arithmetic), caching avoids creating millions of short-lived duplicate objects.

---

**Q3: Explain what happens internally when you do `lst.append(x)`.**

A: CPython checks if `ob_size < allocated`. If yes, it stores a pointer to `x` at index `ob_size`, increments `ob_size`, and increments `x`'s refcount. If not, it calls `list_resize()` which overallocates a new array (roughly `new_size + new_size/8 + 6`), copies all existing pointers, frees the old array, then appends.

---

**Q4: Why is `list.insert(0, x)` O(n)?**

A: It must shift all existing pointers one position to the right (using `memmove`) to make room at index 0. For a list of n elements, this moves n pointers.

---

**Q5: What is pymalloc and why does CPython use it?**

A: Pymalloc is CPython's custom memory allocator for small objects (≤512 bytes). It avoids the overhead of calling `malloc`/`free` for every object by managing memory in arenas (256KB) → pools (4KB) → blocks. It's optimized for Python's pattern of many small, short-lived allocations.

---

**Q6: Explain the difference between `copy.copy()` and `copy.deepcopy()`.**

A: `copy.copy()` creates a new container but fills it with references to the same objects (shallow). `copy.deepcopy()` recursively copies all nested objects, creating fully independent structures. Deep copy also handles circular references by keeping a memo dict of already-copied objects.

---

**Q7: What is the GIL and how does it relate to reference counting?**

A: The Global Interpreter Lock (GIL) is a mutex that protects CPython's reference counting. Since refcount operations are not atomic, without the GIL, concurrent threads could corrupt reference counts. The GIL ensures only one thread executes Python bytecode at a time.

---

**Q8: Explain constant folding in CPython. Give an example.**

A: The compiler evaluates constant expressions at compile time. `x = 3 * 4` is compiled as `x = 12`. `s = "ab" * 3` becomes `s = "ababab"`. This means `a = "hello"; b = "hello"` use the same constant object (not because of interning, but because of compile-time deduplication).

---

**Q9: What is the `__del__` method and why is it problematic?**

A: `__del__` is a finalizer called when an object is about to be destroyed. Problems: non-deterministic timing (especially with cycles), exceptions are suppressed, can resurrect objects, and during interpreter shutdown globals may already be `None`. Prefer context managers.

---

**Q10: Explain how Python dict maintains insertion order (3.7+).**

A: The dict uses a split design: a sparse indices array (maps hash positions to entry indices) and a dense entries array (stores key-value pairs in insertion order). Iteration walks the dense array sequentially, which is naturally in insertion order.

---

**Q11: What is the difference between `__dict__` and `__slots__`?**

A: `__dict__` is a per-instance dictionary storing attributes (flexible but memory-heavy, ~100+ bytes). `__slots__` is a class-level tuple declaring fixed attributes — instances don't get a `__dict__`, saving memory. But `__slots__` disables dynamic attribute assignment and some inheritance patterns.

---

**Q12: Why does `id([1,2,3]) == id([4,5,6])` sometimes return `True`?**

A: The first list is created for `id()`, then immediately garbage collected (refcount 0). The second list may be allocated at the same memory address. Their lifetimes don't overlap, so CPython reuses the address.

---

**Q13: Explain key sharing dicts (PEP 412).**

A: Instances of the same class typically have the same attributes. CPython shares the keys structure (`PyDictKeysObject`) among instances, storing only separate values arrays per instance. This saves significant memory for classes with many instances.

---

**Q14: What is the difference between `a += b` for lists vs tuples?**

A: For lists: calls `list.__iadd__`, mutates in place, returns the same object. For tuples: calls `tuple.__add__` (no `__iadd__`), creates a new tuple, rebinds the name. So `a += b` with lists mutates (aliases see the change); with tuples it rebinds (aliases don't see it).

---

**Q15: What is a cell object in CPython?**

A: A cell is an indirection layer used for closure variables. When a variable is shared between an outer function and a nested function, both access it through a cell object. The cell holds a pointer to the actual value, allowing the nested function to see updates to the variable.

---

**Q16: Explain why `t[0] += [3]` on `t = ([1,2],)` both raises TypeError and mutates.**

A: `t[0] += [3]` desugars to `t[0] = t[0].__iadd__([3])`. Step 1: `list.__iadd__` executes, mutating the list in place (succeeds). Step 2: assignment `t[0] = ...` attempts to write to the tuple slot (fails with TypeError). The mutation already happened.

---

**Q17: What is `sys.intern()` and when would you use it?**

A: It forces a string to be interned (deduplicated). Useful when you have many string comparisons on non-identifier strings (e.g., parsed data keys). After interning, comparison is O(1) pointer comparison instead of O(n) character comparison.

---

**Q18: How does Python's set handle collisions?**

A: Python sets use open addressing with a perturbation-based probing sequence. On collision, it probes subsequent slots using `j = (5*j + 1 + perturb) & mask; perturb >>= 5`. This ensures all slots are visited and distributes entries well.

---

**Q19: What is the cost of creating a Python object?**

A: It involves: allocating memory (pymalloc block or malloc), initializing the header (refcount=1, type pointer), running `__init__`, and potentially registering with the GC (for containers). Much more expensive than stack allocation in C/Go.

---

**Q20: Why doesn't Python process memory shrink after deleting objects?**

A: Pymalloc can only return entire arenas (256KB) to the OS. If even one block in one pool in an arena is still in use, the arena is retained. Additionally, `malloc` itself may not return memory to the OS, and free lists hold onto deallocated objects for reuse.

---

**Q21: What is the difference between `list()` and `[]`?**

A: `[]` uses the `BUILD_LIST` bytecode (fast, direct). `list()` calls the `list` type constructor, which involves a function call overhead (name lookup, argument handling). `[]` is ~2-3x faster for creating an empty list.

---

**Q22: Explain the float free list.**

A: When a float object is deallocated, CPython doesn't return its memory to pymalloc. Instead, it puts it on a free list (up to 100 floats). Next time a float is needed, it's grabbed from the free list — faster than calling the allocator.

---

**Q23: What is `gc.get_referrers(obj)` useful for?**

A: Debugging memory leaks. It returns all objects that hold a reference to `obj`. You can trace what's keeping an object alive unexpectedly.

---

**Q24: How does Python handle memory for very large integers?**

A: Python integers have arbitrary precision. They're stored as arrays of 30-bit "digits" (each in a 32-bit slot). A 1000-digit number might use ~140 digits × 4 bytes = 560 bytes plus header. Arithmetic operates on these digit arrays.

---

**Q25: What is the `__sizeof__` method?**

A: It's the method `sys.getsizeof()` calls internally. It returns the object's memory consumption in bytes (shallow — not counting referenced objects). You can override it for custom classes.

---

**Q26: Explain how `dict.get(key, default)` differs from `dict[key]` in terms of objects.**

A: `dict[key]` raises `KeyError` if key is missing. `dict.get(key, default)` returns the default object. Important: the default is NOT created per-call if it's a constant. `d.get(k, [])` uses the same `[]` expression each call (but since it's a literal, a new list IS created each call — unlike default arguments).

---

**Q27: What is an immortal object in CPython 3.12+?**

A: An object with a special refcount value that is never incremented or decremented. `None`, `True`, `False`, and small integers are immortal. This eliminates cache line bouncing on refcounts in multi-threaded code and supports the free-threading work.

---

**Q28: Explain the `STORE_FAST` vs `STORE_NAME` bytecode.**

A: `STORE_FAST` stores to the local variable array (indexed by integer, O(1), no dict lookup). Used for local variables in functions. `STORE_NAME` stores to the namespace dict (hash lookup). Used at module level. This is why local variable access in functions is faster.

---

**Q29: Why are local variables faster than globals in Python?**

A: Locals use `LOAD_FAST`/`STORE_FAST` (array index). Globals use `LOAD_GLOBAL`/`STORE_GLOBAL` (dict hash lookup). Array indexing is 2-3x faster than dict lookup.

---

**Q30: What is the tuple free list?**

A: CPython maintains free lists for tuples of size 0-19. When a small tuple is deallocated, it goes on the free list for its size. Next time a tuple of that size is needed, it's grabbed from the free list. The empty tuple `()` is a singleton.

---

**Q31: What is `gc.collect()` and when would you call it manually?**

A: It forces a garbage collection cycle. Call it when you've just deleted many objects with potential cycles, before measuring memory usage, or in memory-constrained environments. Returns the number of unreachable objects collected.

---

**Q32: Explain the overallocation strategy for Python lists.**

A: When a list's internal array is full and needs to grow, CPython allocates `new_size + new_size/8 + 6` slots (rounded). This gives amortized O(1) for append — total work to append n items is O(n), not O(n²). Growth factor is approximately 12.5%.

---

**Q33: What is the relationship between `hash()` and dict/set performance?**

A: Dicts and sets use `hash(key)` to compute the slot index. If `hash()` is slow (e.g., custom class with expensive `__hash__`), all dict/set operations slow down. If many keys hash to the same value (collisions), lookup degrades toward O(n).

---

**Q34: What does `weakref.finalize()` do?**

A: Registers a callback to be called when an object is about to be garbage collected. Unlike `__del__`, it's safer (doesn't prevent GC of cycles) and more convenient (can be registered externally).

---

**Q35: Why does CPython use open addressing instead of chaining for dicts?**

A: Open addressing has better cache locality (all data in one contiguous array vs chasing linked-list pointers scattered in memory). For Python's typical small-to-medium dicts, the cache benefit outweighs chaining's simpler collision handling.

---

**Q36: What is the `ob_size` field in `PyVarObject`?**

A: It stores the number of items in a variable-sized object. For lists: number of elements. For tuples: number of elements. For ints: number of digits (negative if the integer is negative). For strings: number of characters.

---

**Q37: How does `del obj.attr` work internally?**

A: It calls `type(obj).__delattr__(obj, 'attr')`, which typically removes the key from `obj.__dict__` and decrements the reference count of the attribute's value.

---

**Q38: What is the memory cost of a Python function object?**

A: A function object contains: `__code__` (code object), `__globals__` (module dict reference), `__defaults__` (tuple of defaults), `__closure__` (tuple of cells), `__dict__` (attribute dict), `__name__`, `__doc__`. Typically 100-200 bytes plus the code object.

---

**Q39: Explain how `from module import name` affects references.**

A: It creates a new name in the current namespace bound to the same object that `module.name` points to. It does NOT create a "link" to the module's namespace — if the module later rebinds its `name`, your imported name still points to the original object.

---

**Q40: What is the `__hash__` and `__eq__` contract?**

A: If `a == b`, then `hash(a) == hash(b)` MUST be true. The converse is not required. Objects that are equal must have the same hash. Violating this corrupts dicts and sets.

---

**Q41: How much memory does an empty dict use and why?**

A: About 64 bytes (CPython 3.11+). It includes: PyObject header (16 bytes), ma_used, ma_version_tag, ma_keys pointer, ma_values pointer, plus a minimal PyDictKeysObject with an 8-entry indices array.

---

**Q42: What is a code object (`__code__`)?**

A: A code object is a compiled representation of a block of Python code. It contains bytecode, constants, variable names, argument info, line number table, etc. It's immutable and shareable (multiple functions can use the same code object with different closures).

---

**Q43: Explain `LOAD_CONST` vs `LOAD_FAST` vs `LOAD_GLOBAL`.**

A: `LOAD_CONST` pushes a constant from `co_consts` (compile-time values). `LOAD_FAST` loads from the local variable array (frame's `f_localsplus`). `LOAD_GLOBAL` looks up in the global dict (and built-in dict as fallback). Speed: CONST > FAST > GLOBAL.

---

**Q44: Why might `gc.disable()` improve performance?**

A: The cyclic GC has overhead: traversing all tracked objects, pausing execution, polluting CPU caches, and triggering copy-on-write in forked processes. Disabling it avoids these costs — but you must ensure no reference cycles leak memory.

---

**Q45: What is the purpose of `gc.get_threshold()`?**

A: It returns `(threshold0, threshold1, threshold2)`. threshold0 is the allocation count that triggers gen-0 collection. threshold1/2 are how many gen-0/gen-1 collections trigger the next generation's collection.

---

**Q46: How does `isinstance()` work internally?**

A: It walks the type's MRO (Method Resolution Order) — the `__mro__` tuple — checking if the target type appears. For a simple class hierarchy, this is O(depth). It's faster than manual type checking with `type()` because it handles inheritance.

---

**Q47: What is `__init_subclass__` and does it affect memory?**

A: It's a hook called when a class is subclassed. It doesn't directly affect memory layout, but it can be used to add `__slots__` or modify class attributes that affect per-instance memory.

---

**Q48: What is the memory difference between a generator and a list?**

A: A generator uses O(1) memory regardless of how many items it yields (stores only the frame state). A list stores all items in memory simultaneously (O(n)). `range(10**9)` as a generator: ~100 bytes. As a list: ~8 GB.

---

**Q49: How does Python's `in` operator work for different containers?**

A: For lists/tuples: O(n) linear scan. For sets/frozensets: O(1) average hash lookup. For dicts: O(1) average hash lookup (checks keys). For strings: substring search (O(n*m) worst case, optimized).

---

**Q50: What happens to an object when the only reference to it is inside a `try/except` block?**

A: After the except block ends, Python explicitly clears the exception variable (`del e`) to break reference cycles between the exception, its traceback, and local variables. This was added to prevent memory leaks from traceback frames.

---


## 13.3 Senior Interview Questions (50)

### Questions & Answers

**Q1: Explain the internal implementation of Python's dict resize operation.**

A: When the load factor exceeds 2/3, CPython allocates a new hash table (next power of 2 in size), creates a new entries array, and re-inserts all entries by recomputing their positions. The old tables are freed. This is O(n) and involves rehashing all keys. The resize triggers at 2/3 full to keep collision chains short.

---

**Q2: How does CPython's cyclic GC avoid collecting objects reachable from outside the set being examined?**

A: The algorithm uses "trial deletion": it computes `gc_refs = ob_refcnt` for each tracked object, then subtracts internal references (references from other tracked objects). Objects with `gc_refs > 0` have external references — they and everything they reach are moved to a "reachable" set. Everything remaining is garbage.

---

**Q3: Explain the relationship between Python frames and the C stack in CPython.**

A: Each Python function call creates a `PyFrameObject` on the heap (containing locals, eval stack, code pointer) AND a C stack frame for `_PyEval_EvalFrameDefault`. The Python frames are linked via `f_back` pointers (heap linked list). The C frames are the actual call stack. Python's recursion limit prevents C stack overflow.

---

**Q4: Why did CPython 3.12 introduce immortal objects, and what problem does it solve?**

A: Immortal objects have a fixed refcount that is never modified. This eliminates cache line bouncing when multiple threads access shared objects (like `None`, `True`, small ints) — every `Py_INCREF`/`Py_DECREF` on shared objects dirtied the cache line containing `ob_refcnt`. This is foundational for the no-GIL (free-threading) effort in Python 3.13+.

---

**Q5: How does pymalloc's arena allocation strategy attempt to return memory to the OS?**

A: Pymalloc sorts arenas by how full they are and preferentially allocates from the fullest arena. This concentrates live objects into fewer arenas, increasing the probability that other arenas become completely empty. Only entirely empty arenas can be `free()`d back to the OS.

---

**Q6: Explain the copy-on-write problem with CPython's reference counting in forked processes.**

A: After `fork()`, parent and child share physical memory pages (CoW). But any `Py_INCREF`/`Py_DECREF` operation writes to `ob_refcnt`, dirtying the page and forcing a private copy. The GC exacerbates this by traversing all objects. Solution: disable GC before fork, use immortal objects, or avoid fork-based parallelism.

---

**Q7: How does CPython implement the `STORE_FAST` bytecode?**

A: `STORE_FAST i`: pops the top of the evaluation stack, decrements the refcount of the current value at `f_localsplus[i]` (if not NULL), and stores the new pointer there. No dict lookup, no hashing — just array index assignment plus refcount management.

---

**Q8: Explain how Python handles memory for string concatenation vs `str.join()`.**

A: Concatenation in a loop (`s += chunk`) creates a new string each iteration, copying all previous content — O(n²) total. `"".join(parts)` first calculates total length, allocates one buffer of that size, then copies each part once — O(n) total. CPython has an optimization for `+=` on strings with refcount=1 (in-place resize), but it's not guaranteed.

---

**Q9: What is the `tp_dealloc` function pointer in a type object?**

A: It's the C function called when an object's refcount reaches zero. It handles cleanup: calling `__del__` (if defined), decrementing references the object holds, clearing weak references, and returning memory to the allocator. Each type defines its own dealloc behavior.

---

**Q10: How does CPython's compact dict differ from the pre-3.6 implementation?**

A: Pre-3.6: single combined table where each slot held (hash, key, value) and ~1/3-2/3 slots were empty — wasted space. 3.6+: separate sparse indices array (small entries: 1-8 bytes each) and dense entries array (no gaps). Benefits: preserves insertion order, uses less memory, better cache behavior during iteration.

---

**Q11: Explain how `__slots__` affects instance memory at the C level.**

A: Without `__slots__`, each instance has a `__dict__` (PyDictObject ~100 bytes) for attributes. With `__slots__`, the type object has slot descriptors that store attribute values at fixed offsets directly in the instance's memory (like C struct fields). No dict allocation, no hash lookups for attribute access.

---

**Q12: What is PEP 442 (Safe Object Finalization) and what problem did it solve?**

A: Before Python 3.4, objects with `__del__` in reference cycles were uncollectable (put in `gc.garbage`). The GC couldn't determine a safe order to call finalizers. PEP 442 introduced safe finalization: the GC can now call finalizers in a topological order and collect the cycle, even if objects have `__del__`.

---

**Q13: How does CPython implement the evaluation stack?**

A: The evaluation stack is part of the frame object, allocated in `f_localsplus` after the locals/cells/free variables. It's a C array of `PyObject*` pointers. `f_stacktop` tracks the current top. Bytecodes push/pop by incrementing/decrementing this pointer. In Python 3.11+, the stack is on the C stack for better performance.

---

**Q14: Explain how Python's `is` operator is compiled to bytecode.**

A: `a is b` compiles to `LOAD` a, `LOAD` b, `IS_OP 0` (Python 3.9+) or `COMPARE_OP` with `is` (older). At the C level, it's a pointer comparison of two `PyObject*` values — the simplest possible comparison.

---

**Q15: What is the memory layout difference between a list and a tuple at the C level?**

A: Tuple: `PyObject_VAR_HEAD` + inline array of `PyObject*` (all one allocation). List: `PyObject_VAR_HEAD` + `ob_item` pointer + `allocated` count; `ob_item` points to a SEPARATE allocation. Tuples are one contiguous block; lists are two allocations. Tuples have no overallocation.

---

**Q16: How does CPython implement the `del` statement for different targets?**

A: `del name`: `DELETE_FAST`/`DELETE_NAME` removes from namespace, decrefs. `del obj.attr`: calls `type.__delattr__`. `del obj[key]`: calls `__delitem__`. `del obj[a:b]`: calls `__delitem__` with a slice. Each has different bytecode and different type-slot functions.

---

**Q17: Explain how `tracemalloc` tracks allocations without massive overhead.**

A: `tracemalloc` replaces the memory allocator hooks with instrumented versions that record (pointer → traceback) mappings in a hash table. It captures the Python call stack (not C stack) as frames. The overhead is mainly the hash table memory and the traceback storage.

---

**Q18: What is the `PyTypeObject` structure and why is it so large?**

A: `PyTypeObject` is ~400+ bytes containing: name, basicsize, flags, and dozens of function pointers for protocols (number, sequence, mapping, etc.) and special methods (`tp_new`, `tp_init`, `tp_dealloc`, `tp_repr`, etc.). This "slot table" design allows O(1) dispatch for common operations without dict lookups.

---

**Q19: How does the `BINARY_SUBSCR` bytecode work for list indexing?**

A: It pops the index and the list from the stack. For lists, it calls `PyList_GetItem`: validates the index, computes `ob_item[index]`, increments the result's refcount, and pushes it onto the stack. O(1) — just pointer arithmetic and array access.

---

**Q20: Explain Python's string kind system and its memory implications.**

A: CPython stores strings in the narrowest encoding that fits all characters. ASCII: 1 byte/char. Latin-1: 1 byte/char. UCS-2: 2 bytes/char. UCS-4: 4 bytes/char. A single emoji in a string forces ALL characters to 4 bytes. This is why `"a"*100` is 149 bytes but `"a"*99 + "😀"` is ~449 bytes.

---

**Q21: How does CPython implement `dict.__contains__` (the `in` operator for dicts)?**

A: Computes `hash(key)`, finds the slot via `hash & mask`, probes for matches comparing hash values first (fast rejection), then comparing keys with `==`. Average O(1). Returns True/False based on whether a matching key was found.

---

**Q22: What is the purpose of `Py_TPFLAGS_HAVE_GC` flag?**

A: It marks a type as "may participate in reference cycles." Objects of such types are tracked by the cyclic GC. The GC only traverses tracked objects. Non-container types (int, float, str) don't have this flag and are invisible to the cyclic GC.

---

**Q23: Explain the `tp_traverse` function in the context of garbage collection.**

A: `tp_traverse` is a callback in the type object that tells the GC which other objects a given object references. The GC calls it to build the reference graph. For lists, it traverses all elements. For dicts, it traverses all keys and values. It's essential for cycle detection.

---

**Q24: How does CPython implement attribute access (`obj.attr`) at the bytecode level?**

A: `LOAD_ATTR` bytecode: first checks the type's method table (data descriptors, class dict, non-data descriptors), then checks `obj.__dict__`. CPython 3.11+ uses inline caching to speed this up — after the first access, subsequent accesses use a cached slot/offset.

---

**Q25: What is `ob_refcnt` overflow protection?**

A: On 64-bit systems, `Py_ssize_t` is 64 bits — overflow is practically impossible (2^63 references). On 32-bit systems, it's 2^31 — still effectively impossible in practice. If somehow reached, CPython would just leave it high (leak the object rather than use-after-free).

---

**Q26: How does the `MAKE_FUNCTION` bytecode work?**

A: It pops a code object and (optionally) defaults, closure, annotations from the stack, allocates a new `PyFunctionObject`, fills in `__code__`, `__globals__` (from frame), `__defaults__`, `__closure__`, etc., and pushes the function object. This is why function definition has runtime cost.

---

**Q27: Explain how CPython's peephole optimizer affects object creation.**

A: The optimizer (AST optimizer + peephole) pre-computes constant expressions, folds constant operations, and deduplicates constants. `3 * 4` becomes `12` — no multiplication at runtime. `"ab" * 3` becomes `"ababab"` if ≤ 4096 chars. This reduces object creation at runtime.

---

**Q28: What is the `ma_version_tag` in dict objects?**

A: A 64-bit counter incremented on every dict modification. Used by CPython's specializing interpreter to invalidate inline caches — if the version changed, cached attribute lookups are stale and must be redone. Enables optimizations like `LOAD_ATTR_INSTANCE_VALUE`.

---

**Q29: How does `sys.getrecursionlimit()` relate to the C stack?**

A: Each Python function call also creates a C stack frame (for the eval loop). The recursion limit prevents C stack overflow. The actual C stack size is typically 1-8 MB (OS-dependent). At ~1000 Python frames, the C stack usage is typically safe (each eval frame uses ~1-3 KB of C stack).

---

**Q30: Explain the `__class__` cell in Python 3 classes.**

A: In Python 3, methods have implicit access to `__class__` (the enclosing class) via a cell variable. This enables `super()` without arguments. The compiler detects `super()` or `__class__` usage and adds a `__class__` cell to the closure.

---

**Q31: How does CPython implement multiple inheritance at the memory level?**

A: C-level types use careful struct embedding (base type's struct is a prefix). For Python classes, instances have a single `__dict__`. The MRO (C3 linearization) determines method lookup order. `__slots__` in multiple inheritance requires compatible slot layouts.

---

**Q32: What is the "compact" vs "split" dict used for instance dictionaries?**

A: Split dict: keys shared among all instances of a class, each instance stores only a values array. Compact dict: each instance has its own independent keys+values. Split is used for the common case (all instances have same attrs). If an instance diverges (adds unique attr), it converts to compact.

---

**Q33: Explain how `LOAD_GLOBAL` was optimized in Python 3.11+.**

A: Python 3.11 introduced `LOAD_GLOBAL_MODULE` and `LOAD_GLOBAL_BUILTIN` specialized opcodes. They cache the dict version + the value pointer. On cache hit (version matches), it's nearly as fast as `LOAD_FAST`. Cache miss falls back to dict lookup. The `ma_version_tag` enables invalidation.

---

**Q34: What is the `tp_basicsize` vs `tp_itemsize` in type objects?**

A: `tp_basicsize` is the fixed size of instances (header + fixed fields). `tp_itemsize` is the size of each additional element for variable-sized objects. Total size = `tp_basicsize + ob_size * tp_itemsize`. For fixed-size objects (most classes), `tp_itemsize` is 0.

---

**Q35: How does CPython handle thread safety for dict operations without per-object locks?**

A: The GIL ensures only one thread executes bytecode at a time. Dict operations that are single bytecodes (like `STORE_SUBSCR` for `d[k] = v`) are atomic at the Python level. But C extensions releasing the GIL must use their own synchronization for shared dicts.

---

**Q36: Explain the memory impact of Python's descriptor protocol.**

A: Descriptors (objects with `__get__`, `__set__`, `__delete__`) live on the class, not instances. A `@property` adds one descriptor object to the class, shared by all instances. This is memory-efficient vs storing computed values per-instance. But each access calls Python code (slower than direct attribute).

---

**Q37: What is the `wchar_t` representation issue in Python strings?**

A: Before Python 3.3 (PEP 393), CPython could be compiled with 2-byte or 4-byte `wchar_t` (narrow vs wide builds). This affected string memory usage and emoji handling. PEP 393 replaced this with the flexible representation (kind=1/2/4) chosen per-string based on content.

---

**Q38: How does `collections.OrderedDict` differ from regular dict in implementation?**

A: Since Python 3.7, regular dict preserves insertion order. `OrderedDict` additionally: maintains a doubly-linked list of entries (for O(1) `move_to_end`), overrides `__eq__` to consider order, and supports `last=True/False` in `popitem()`. It uses more memory than regular dict.

---

**Q39: Explain the concept of "zero-cost" exceptions in CPython 3.11+.**

A: Python 3.11 replaced the block stack (used for try/except) with an exception table in the code object. No setup bytecodes are needed when entering a try block — the cost is zero if no exception occurs. Only when an exception is raised does the table get consulted. This makes try blocks free in the happy path.

---

**Q40: What is the `PyObject_GC_Track` function?**

A: It registers a container object with the cyclic GC. Called during object creation for types with `Py_TPFLAGS_HAVE_GC`. After tracking, the GC can visit the object during collection. The object is added to its generation's linked list. Untracking (`PyObject_GC_UnTrack`) removes it.

---

**Q41: How does CPython's `list.sort()` (Timsort) affect memory?**

A: Timsort uses O(n) auxiliary memory in the worst case for merging. During sort, the list's `ob_item` is temporarily set to an empty array (the list appears empty to outside observers) to prevent concurrent modification. The sort operates on a private copy of the pointer array.

---

**Q42: Explain the `PREDICT` and `DISPATCH` macros in CPython's ceval.c.**

A: `PREDICT(opcode)` is a branch prediction hint — if the next opcode matches, it jumps directly without going through the dispatch switch. `DISPATCH()` handles the main opcode dispatch. In modern CPython (3.11+), computed gotos replace the switch, and the specializing interpreter replaces PREDICT.

---

**Q43: What is the "free-threading" (no-GIL) effort and how does it affect the object model?**

A: PEP 703 proposes removing the GIL. This requires: biased reference counting (fast single-thread path), deferred reference counting for immortal/global objects, per-object locks for containers, and thread-safe memory allocation. It fundamentally changes how `ob_refcnt` is managed.

---

**Q44: How does `memoryview` avoid copying data?**

A: `memoryview` wraps an existing buffer (bytes, bytearray, numpy array) and provides a view without copying. It stores a pointer to the buffer, shape, strides, and format. Operations on the view operate directly on the underlying memory. This is O(1) to create regardless of buffer size.

---

**Q45: Explain how Python 3.11's specializing interpreter works.**

A: The interpreter starts with generic bytecodes. After executing a bytecode ~8 times with the same types, it replaces it with a specialized version (e.g., `BINARY_ADD` → `BINARY_ADD_INT`). Specialized versions skip type checks and dispatch directly. On type mismatch, they deoptimize back to generic.

---

**Q46: What is the `Py_buffer` protocol and its relationship to memory management?**

A: The buffer protocol (`__buffer__`/`bf_getbuffer`) allows objects to expose their internal memory directly to other objects without copying. The consumer gets a `Py_buffer` struct with pointer, size, format, shape, strides. The exporter increments a buffer count; it can't resize/free its memory until all buffers are released.

---

**Q47: How does CPython implement `StopIteration` propagation in generators?**

A: When a generator's code raises `StopIteration` (or returns), the frame is finalized. The generator object's `gi_frame` is set to NULL. Subsequent `next()` calls raise `StopIteration` without entering any frame. The frame (and its references) is deallocated.

---

**Q48: Explain the memory model for `async`/`await` coroutines.**

A: Coroutines are similar to generators. A coroutine object wraps a frame that's suspended/resumed. Memory-wise: the frame persists across `await` points (not freed until coroutine completes). An event loop may have thousands of suspended coroutines simultaneously, each holding its frame's locals in memory.

---

**Q49: What is `PyMem_SetAllocator` and when would you use it?**

A: It allows replacing CPython's memory allocator with a custom one (e.g., for debugging, profiling, or using `jemalloc`). Libraries like `tracemalloc` use it to intercept allocations. You can set different allocators for raw memory, objects, and arenas.

---

**Q50: Explain how subinterpreters interact with Python's memory management.**

A: Each subinterpreter has its own GIL (Python 3.12+), but they share the same process memory space and pymalloc arenas. Objects from one interpreter must not leak into another. The memory allocator is process-global. True isolation requires separate per-interpreter allocators (ongoing work in CPython).

---

# Part 14 — Coding Questions (Prediction Problems)

> For each question: predict the output, then read the explanation.
> Topics covered: references, identity, mutation, functions, default arguments, closures, containers, garbage collection.

---

## Section A — References and Identity (Q1–Q25)

### Q1
```python
a = [1, 2, 3]
b = a
b.append(4)
print(a)
```

**Output:** `[1, 2, 3, 4]`

**Reasoning:** `b = a` makes `b` an alias. `b.append(4)` mutates the shared object.

---

### Q2
```python
a = [1, 2, 3]
b = a
b = [4, 5, 6]
print(a)
```

**Output:** `[1, 2, 3]`

**Reasoning:** `b = [4, 5, 6]` rebinds `b` to a new list. The original list referenced by `a` is unchanged.

---

### Q3
```python
x = 256
y = 256
print(x is y)
```

**Output:** `True`

**Reasoning:** 256 is within CPython's small integer cache (-5 to 256). Both names point to the same pre-allocated object.

---

### Q4
```python
x = 257
y = 257
print(x is y)
```

**Output:** `True` (in a script) or `False` (in interactive mode)

**Reasoning:** In a script, the compiler constant-folds both 257 literals to the same constant. In interactive mode, each line may be a separate compilation unit.

---

### Q5
```python
a = "hello"
b = "hello"
print(a is b)
```

**Output:** `True`

**Reasoning:** String interning — identifier-like string literals are interned.

---

### Q6
```python
a = "hello!"
b = "hello!"
print(a is b)
```

**Output:** Likely `True` in a script (compiler deduplication) but not guaranteed.

**Reasoning:** Non-identifier strings may or may not be interned. In a script, the compiler deduplicates constants in the same code object.

---

### Q7
```python
a = []
b = []
print(a is b)
print(a == b)
```

**Output:**
```
False
True
```

**Reasoning:** Each `[]` creates a new list object (different identity). But they have the same value (both empty).

---

### Q8
```python
a = ()
b = ()
print(a is b)
```

**Output:** `True`

**Reasoning:** The empty tuple is a singleton in CPython — there's only one.

---

### Q9
```python
a = (1, 2, 3)
b = (1, 2, 3)
print(a is b)
```

**Output:** `True` (in a script)

**Reasoning:** The compiler deduplicates constant tuples in the same code object. Both refer to the same constant.

---

### Q10
```python
a = [1, 2, 3]
b = a[:]
print(a == b)
print(a is b)
```

**Output:**
```
True
False
```

**Reasoning:** `a[:]` creates a shallow copy — same values, different object.

---

### Q11
```python
import sys
a = []
print(sys.getrefcount(a))
```

**Output:** `2`

**Reasoning:** One reference from `a`, one temporary reference from passing to `getrefcount()`.

---

### Q12
```python
a = [1, 2, 3]
b = a
c = a
print(sys.getrefcount(a) - 1)  # subtract 1 for the function argument
```

**Output:** `3`

**Reasoning:** References: `a`, `b`, `c` = 3 (minus the temporary from getrefcount).

---

### Q13
```python
a = [1, 2]
b = [a, a]
a.append(3)
print(b)
```

**Output:** `[[1, 2, 3], [1, 2, 3]]`

**Reasoning:** `b` contains two references to the same list `a`. Mutating `a` is visible through both.

---

### Q14
```python
x = 10
y = x
x = 20
print(y)
```

**Output:** `10`

**Reasoning:** `x = 20` rebinds `x` to a new int object. `y` still points to the original int(10).

---

### Q15
```python
a = [[0]] * 3
a[0].append(1)
print(a)
```

**Output:** `[[0, 1], [0, 1], [0, 1]]`

**Reasoning:** `[[0]] * 3` creates three references to the SAME inner list. Mutating via any reference affects all.

---

### Q16
```python
a = [[0] for _ in range(3)]
a[0].append(1)
print(a)
```

**Output:** `[[0, 1], [0], [0]]`

**Reasoning:** List comprehension creates three independent lists. Only `a[0]` is mutated.

---

### Q17
```python
a = "hello"
b = a
a += " world"
print(b)
```

**Output:** `hello`

**Reasoning:** Strings are immutable. `a += " world"` creates a new string and rebinds `a`. `b` still points to the original.

---

### Q18
```python
a = [1, 2]
b = a
a += [3, 4]
print(b)
```

**Output:** `[1, 2, 3, 4]`

**Reasoning:** Lists are mutable. `a += [3, 4]` calls `list.__iadd__`, mutating in place. `b` is an alias.

---

### Q19
```python
a = (1, 2)
b = a
a += (3, 4)
print(b)
print(a)
```

**Output:**
```
(1, 2)
(1, 2, 3, 4)
```

**Reasoning:** Tuples are immutable. `a += (3, 4)` creates a new tuple and rebinds `a`. `b` unchanged.

---

### Q20
```python
def f(x, y):
    return x is y

print(f([], []))
```

**Output:** `False`

**Reasoning:** Two separate list objects are created as arguments.

---

### Q21
```python
a = None
b = None
print(a is b)
```

**Output:** `True`

**Reasoning:** `None` is a singleton. All references to `None` point to the same object.

---

### Q22
```python
print(id(1000) == id(2000))
```

**Output:** Likely `True`

**Reasoning:** `id(1000)` creates a temporary int, gets its id, then the int is freed. `id(2000)` may reuse the same memory address. (Non-overlapping lifetimes.)

---

### Q23
```python
a = [1, 2, 3]
b = a
del a
print(b)
```

**Output:** `[1, 2, 3]`

**Reasoning:** `del a` removes the name `a` from the namespace, decrements refcount to 1. The list is still alive via `b`.

---

### Q24
```python
a = [1, 2, 3]
b = a
del a[:]
print(b)
```

**Output:** `[]`

**Reasoning:** `del a[:]` clears the list in place (mutation). `b` sees the empty list.

---

### Q25
```python
x = [1, 2, 3]
y = x
x = x + [4]
print(y)
print(x)
```

**Output:**
```
[1, 2, 3]
[1, 2, 3, 4]
```

**Reasoning:** `x + [4]` creates a new list. `x` is rebound. `y` still points to the original.

---


## Section B — Functions and Default Arguments (Q26–Q50)

### Q26
```python
def add(lst, item):
    lst.append(item)
    return lst

original = [1, 2]
result = add(original, 3)
print(original)
print(result is original)
```

**Output:**
```
[1, 2, 3]
True
```

**Reasoning:** `lst` is an alias for `original`. Mutation is visible to the caller. The function returns the same object.

---

### Q27
```python
def replace(lst):
    lst = [99, 100]

original = [1, 2, 3]
replace(original)
print(original)
```

**Output:** `[1, 2, 3]`

**Reasoning:** `lst = [99, 100]` rebinds the local parameter. The caller's binding is unaffected.

---

### Q28
```python
def modify(data):
    data += [4, 5]

a = [1, 2, 3]
modify(a)
print(a)
```

**Output:** `[1, 2, 3, 4, 5]`

**Reasoning:** For lists, `+=` calls `__iadd__` which mutates in place. The parameter `data` mutates the same object.

---

### Q29
```python
def modify(data):
    data += (4, 5)

a = (1, 2, 3)
modify(a)
print(a)
```

**Output:** `(1, 2, 3)`

**Reasoning:** For tuples, `+=` creates a new tuple and rebinds the local `data`. The caller's `a` is unaffected.

---

### Q30
```python
def modify(n):
    n += 10

x = 5
modify(x)
print(x)
```

**Output:** `5`

**Reasoning:** Integers are immutable. `n += 10` creates a new int and rebinds the local `n`. `x` is unaffected.

---

### Q31
```python
def append_to(element, target=[]):
    target.append(element)
    return target

print(append_to(1))
print(append_to(2))
print(append_to(3))
```

**Output:**
```
[1]
[1, 2]
[1, 2, 3]
```

**Reasoning:** The default list `[]` is created once at definition time. Each call mutates the same default list.

---

### Q32
```python
def append_to(element, target=None):
    if target is None:
        target = []
    target.append(element)
    return target

print(append_to(1))
print(append_to(2))
print(append_to(3))
```

**Output:**
```
[1]
[2]
[3]
```

**Reasoning:** Each call creates a new list when `target` is `None`.

---

### Q33
```python
def f(a, b=[]):
    b.append(a)
    return b

print(f(1))
print(f(2, []))
print(f(3))
```

**Output:**
```
[1]
[2]
[1, 3]
```

**Reasoning:** Call 1: uses default `b`, appends 1 → `[1]`. Call 2: uses a new list `[]`, default untouched. Call 3: uses the default `b` (which is `[1]` from call 1), appends 3 → `[1, 3]`.

---

### Q34
```python
def outer():
    x = 10
    def inner():
        return x
    x = 20
    return inner

print(outer()())
```

**Output:** `20`

**Reasoning:** The closure captures the variable `x` by reference (via cell object), not its value at the time of `def inner`. When `inner()` is called, `x` is 20.

---

### Q35
```python
functions = []
for i in range(5):
    functions.append(lambda: i)

print([f() for f in functions])
```

**Output:** `[4, 4, 4, 4, 4]`

**Reasoning:** All lambdas capture the same variable `i` (by reference). After the loop, `i` is 4. All lambdas return 4.

---

### Q36
```python
functions = []
for i in range(5):
    functions.append(lambda i=i: i)

print([f() for f in functions])
```

**Output:** `[0, 1, 2, 3, 4]`

**Reasoning:** `i=i` captures the current value of `i` as a default argument (evaluated at each iteration). Each lambda has its own default.

---

### Q37
```python
def make_counter():
    count = 0
    def counter():
        nonlocal count
        count += 1
        return count
    return counter

c1 = make_counter()
c2 = make_counter()
print(c1(), c1(), c1())
print(c2())
```

**Output:**
```
1 2 3
1
```

**Reasoning:** Each call to `make_counter()` creates a separate cell for `count`. `c1` and `c2` have independent counters.

---

### Q38
```python
def f():
    try:
        return 1
    finally:
        return 2

print(f())
```

**Output:** `2`

**Reasoning:** `finally` always executes. Its `return` overrides the `try` block's `return`.

---

### Q39
```python
def f(x=[]):
    x += [1]
    return x

print(f())
print(f())
print(f([5]))
print(f())
```

**Output:**
```
[1]
[1, 1]
[5, 1]
[1, 1, 1]
```

**Reasoning:** Calls 1,2,4 use the mutable default which accumulates. Call 3 uses a provided list (default unaffected). The default is `[1]` after call 1, `[1,1]` after call 2, and `[1,1,1]` after call 4.

---

### Q40
```python
def f(d={}):
    d['count'] = d.get('count', 0) + 1
    return d['count']

print(f())
print(f())
print(f({'count': 100}))
print(f())
```

**Output:**
```
1
2
101
3
```

**Reasoning:** Calls 1,2,4 use the same default dict (accumulates). Call 3 uses a provided dict (doesn't affect default).

---

### Q41
```python
x = 10
def foo():
    print(x)
    x = 20

foo()
```

**Output:** `UnboundLocalError: local variable 'x' referenced before assignment`

**Reasoning:** The compiler sees `x = 20` in `foo` and marks `x` as local for the ENTIRE function. The `print(x)` tries to read local `x` before it's assigned.

---

### Q42
```python
x = 10
def foo():
    global x
    print(x)
    x = 20

foo()
print(x)
```

**Output:**
```
10
20
```

**Reasoning:** `global x` makes `x` refer to the module-level variable. The function reads and modifies the global.

---

### Q43
```python
def outer():
    x = 1
    def inner():
        x = 2
        print("inner:", x)
    inner()
    print("outer:", x)

outer()
```

**Output:**
```
inner: 2
outer: 1
```

**Reasoning:** Without `nonlocal`, `x = 2` in `inner` creates a LOCAL `x` in `inner`. The outer `x` is unchanged.

---

### Q44
```python
def outer():
    x = 1
    def inner():
        nonlocal x
        x = 2
        print("inner:", x)
    inner()
    print("outer:", x)

outer()
```

**Output:**
```
inner: 2
outer: 2
```

**Reasoning:** `nonlocal x` makes `inner` use the same cell as `outer`. Both see the update.

---

### Q45
```python
def f(n, acc=[]):
    acc.append(n)
    if n == 0:
        return acc
    return f(n - 1, acc)

print(f(3))
print(f(2))
```

**Output:**
```
[3, 2, 1, 0]
[3, 2, 1, 0, 2, 1, 0]
```

**Reasoning:** The default `acc` is shared across all calls. Second invocation appends to the same list.

---

### Q46
```python
a = 1
def f():
    a = a + 1
    return a

print(f())
```

**Output:** `UnboundLocalError`

**Reasoning:** `a = a + 1` makes `a` local. The `a` on the right-hand side tries to read the local before assignment.

---

### Q47
```python
def make_multiplier(n):
    return lambda x: x * n

double = make_multiplier(2)
triple = make_multiplier(3)
print(double(5))
print(triple(5))
```

**Output:**
```
10
15
```

**Reasoning:** Each lambda captures its own `n` value via a closure cell.

---

### Q48
```python
def f(a, b):
    a = a + b
    return a

x = [1, 2]
y = [3, 4]
result = f(x, y)
print(x)
print(result)
```

**Output:**
```
[1, 2]
[1, 2, 3, 4]
```

**Reasoning:** `a = a + b` creates a NEW list (not `+=`), rebinds local `a`. `x` is unchanged. `result` is the new list.

---

### Q49
```python
def f(a, b):
    a += b
    return a

x = [1, 2]
y = [3, 4]
result = f(x, y)
print(x)
print(result)
print(x is result)
```

**Output:**
```
[1, 2, 3, 4]
[1, 2, 3, 4]
True
```

**Reasoning:** `a += b` on a list calls `__iadd__` (in-place). Mutates `x`. Returns the same object.

---

### Q50
```python
def swap(a, b):
    a, b = b, a

x = [1]
y = [2]
swap(x, y)
print(x, y)
```

**Output:** `[1] [2]`

**Reasoning:** `a, b = b, a` rebinds local names `a` and `b`. Has no effect on caller's bindings.

---


## Section C — Containers and Mutation (Q51–Q75)

### Q51
```python
a = {'x': [1, 2]}
b = a.copy()
b['x'].append(3)
print(a)
```

**Output:** `{'x': [1, 2, 3]}`

**Reasoning:** `dict.copy()` is shallow. `b['x']` and `a['x']` reference the same list object.

---

### Q52
```python
a = [1, 2, 3, 4, 5]
b = a[1:4]
b[0] = 99
print(a)
```

**Output:** `[1, 2, 3, 4, 5]`

**Reasoning:** Slicing creates a new list (shallow copy). Rebinding `b[0]` only affects `b`'s new list.

---

### Q53
```python
a = [[1], [2], [3]]
b = a[:]
b[0].append(99)
b[1] = [100]
print(a)
print(b)
```

**Output:**
```
[[1, 99], [2], [3]]
[[1, 99], [100], [3]]
```

**Reasoning:** `a[:]` shallow copy — inner lists are shared. `b[0].append(99)` mutates shared list. `b[1] = [100]` rebinds only `b`'s slot.

---

### Q54
```python
d = {}
a = []
d[1] = a
d[2] = a
a.append('hello')
print(d)
```

**Output:** `{1: ['hello'], 2: ['hello']}`

**Reasoning:** Both dict values reference the same list. Mutation through `a` is visible in both.

---

### Q55
```python
a = [1, 2, 3]
b = a
a = a * 2
print(a)
print(b)
```

**Output:**
```
[1, 2, 3, 1, 2, 3]
[1, 2, 3]
```

**Reasoning:** `a * 2` creates a new list. `a` is rebound. `b` still references the original.

---

### Q56
```python
a = [1, 2, 3]
b = a
a *= 2
print(a)
print(b)
print(a is b)
```

**Output:**
```
[1, 2, 3, 1, 2, 3]
[1, 2, 3, 1, 2, 3]
True
```

**Reasoning:** `*=` on a list calls `__imul__` — mutates in place. `a` and `b` are still the same object.

---

### Q57
```python
t = (1, 2, 3)
t *= 2
print(t)
```

**Output:** `(1, 2, 3, 1, 2, 3)`

**Reasoning:** Tuples are immutable, so `*=` creates a new tuple and rebinds `t`.

---

### Q58
```python
a = [1, 2, 3]
b = a.sort()
print(a)
print(b)
```

**Output:**
```
[1, 2, 3]
None
```

**Reasoning:** `list.sort()` sorts in place and returns `None`. The list was already sorted so it looks unchanged.

---

### Q59
```python
a = [3, 1, 2]
b = sorted(a)
print(a)
print(b)
print(a is b)
```

**Output:**
```
[3, 1, 2]
[1, 2, 3]
False
```

**Reasoning:** `sorted()` returns a NEW sorted list. `a` is unchanged.

---

### Q60
```python
a = {'a': 1, 'b': 2}
b = a
b['c'] = 3
print(a)
```

**Output:** `{'a': 1, 'b': 2, 'c': 3}`

**Reasoning:** `b = a` creates an alias. Mutating through `b` is visible via `a`.

---

### Q61
```python
a = {1, 2, 3}
b = a
b.add(4)
print(a)
```

**Output:** `{1, 2, 3, 4}`

**Reasoning:** Sets are mutable. `b` is an alias. Mutation visible through both names.

---

### Q62
```python
a = [1, 2, 3]
for i in a:
    a.append(i * 10)
print(a)
```

**Output:** Infinite loop (eventually MemoryError)

**Reasoning:** Modifying a list while iterating it. Each iteration appends, making the list longer forever.

---

### Q63
```python
a = [1, 2, 3]
for i in a[:]:
    a.append(i * 10)
print(a)
```

**Output:** `[1, 2, 3, 10, 20, 30]`

**Reasoning:** `a[:]` creates a copy. The loop iterates over the copy (fixed size 3). Appending to `a` doesn't affect the iteration.

---

### Q64
```python
d = {'a': 1, 'b': 2, 'c': 3}
for k in d:
    if d[k] == 2:
        del d[k]
```

**Output:** `RuntimeError: dictionary changed size during iteration`

**Reasoning:** Deleting from a dict during iteration is not allowed.

---

### Q65
```python
a = [1, [2, 3], 4]
import copy
b = copy.deepcopy(a)
b[1].append(5)
print(a)
print(b)
```

**Output:**
```
[1, [2, 3], 4]
[1, [2, 3, 5], 4]
```

**Reasoning:** Deep copy creates fully independent copies. Mutating `b[1]` doesn't affect `a[1]`.

---

### Q66
```python
a = (1, [2, 3])
b = (1, [2, 3])
print(a == b)
print(a is b)
```

**Output:**
```
True
False
```

**Reasoning:** Same values but different objects (tuples containing mutable objects are not interned/deduplicated).

---

### Q67
```python
a = (1, [2, 3])
try:
    hash(a)
except TypeError as e:
    print(e)
```

**Output:** `unhashable type: 'list'`

**Reasoning:** Tuple hashing recursively hashes elements. Lists are unhashable, so the tuple is too.

---

### Q68
```python
lst = [1, 2, 3, 4, 5]
del lst[1:3]
print(lst)
```

**Output:** `[1, 4, 5]`

**Reasoning:** Slice deletion removes elements at indices 1 and 2. Remaining elements shift left.

---

### Q69
```python
a = [0] * 5
print(a)
a[2] = 99
print(a)
```

**Output:**
```
[0, 0, 0, 0, 0]
[0, 0, 99, 0, 0]
```

**Reasoning:** `[0] * 5` creates 5 references to the same int(0). But rebinding a[2] just changes one slot. Since ints are immutable, no aliasing issue.

---

### Q70
```python
matrix = [[0] * 3] * 3
matrix[0][0] = 1
print(matrix)
```

**Output:** `[[1, 0, 0], [1, 0, 0], [1, 0, 0]]`

**Reasoning:** `[[0]*3] * 3` creates three references to the SAME inner list. Mutating one row affects all.

---

### Q71
```python
matrix = [[0] * 3 for _ in range(3)]
matrix[0][0] = 1
print(matrix)
```

**Output:** `[[1, 0, 0], [0, 0, 0], [0, 0, 0]]`

**Reasoning:** List comprehension creates three independent inner lists.

---

### Q72
```python
a = {1: 'one', 2: 'two'}
b = a
a = {3: 'three'}
print(b)
```

**Output:** `{1: 'one', 2: 'two'}`

**Reasoning:** `a = {3: 'three'}` rebinds `a` to a new dict. `b` still references the original.

---

### Q73
```python
a = {1: 'one', 2: 'two'}
b = a
a.clear()
print(b)
```

**Output:** `{}`

**Reasoning:** `a.clear()` mutates the dict in place. `b` is an alias, sees the empty dict.

---

### Q74
```python
a = [1, 2, 3]
b = a
a[:] = [4, 5, 6]
print(b)
```

**Output:** `[4, 5, 6]`

**Reasoning:** `a[:] = [4,5,6]` is a slice assignment — it mutates the list in place (replaces all elements). `b` sees the change.

---

### Q75
```python
import sys
a = [1, 2, 3]
b = (1, 2, 3)
print(sys.getsizeof(a) > sys.getsizeof(b))
```

**Output:** `True`

**Reasoning:** Lists have more overhead: separate pointer array, `allocated` field, overallocation. Tuples are more compact.

---

## Section D — Closures and Advanced (Q76–Q100)

### Q76
```python
def outer():
    funcs = []
    for i in range(3):
        def inner():
            return i
        funcs.append(inner)
    return funcs

print([f() for f in outer()])
```

**Output:** `[2, 2, 2]`

**Reasoning:** All closures share the same cell for `i`. After the loop, `i = 2`.

---

### Q77
```python
def outer():
    funcs = []
    for i in range(3):
        def inner(i=i):
            return i
        funcs.append(inner)
    return funcs

print([f() for f in outer()])
```

**Output:** `[0, 1, 2]`

**Reasoning:** Default argument `i=i` captures the value at each iteration.

---

### Q78
```python
class A:
    lst = []
    def add(self, item):
        self.lst.append(item)

a = A()
b = A()
a.add(1)
b.add(2)
print(a.lst)
print(b.lst)
print(a.lst is b.lst)
```

**Output:**
```
[1, 2]
[1, 2]
True
```

**Reasoning:** `lst` is a class attribute (shared by all instances). Both `a` and `b` mutate the same list.

---

### Q79
```python
class A:
    def __init__(self):
        self.lst = []
    def add(self, item):
        self.lst.append(item)

a = A()
b = A()
a.add(1)
b.add(2)
print(a.lst)
print(b.lst)
```

**Output:**
```
[1]
[2]
```

**Reasoning:** `self.lst = []` in `__init__` creates a separate list per instance.

---

### Q80
```python
x = [1, 2, 3]
def foo():
    x.append(4)

foo()
print(x)
```

**Output:** `[1, 2, 3, 4]`

**Reasoning:** No assignment to `x` in `foo`, so `x` refers to the global. Mutation through `x.append` is allowed without `global` keyword.

---

### Q81
```python
x = [1, 2, 3]
def foo():
    x = x + [4]

foo()
```

**Output:** `UnboundLocalError`

**Reasoning:** `x = ...` makes `x` local. The right-hand side `x + [4]` tries to read local `x` before assignment.

---

### Q82
```python
def gen():
    yield 1
    yield 2
    yield 3

g1 = gen()
g2 = gen()
print(next(g1))
print(next(g2))
print(next(g1))
```

**Output:**
```
1
1
2
```

**Reasoning:** Each call to `gen()` creates an independent generator object with its own state.

---

### Q83
```python
a = [1, 2, 3]
b = a
a = a.copy()
a.append(4)
print(b)
```

**Output:** `[1, 2, 3]`

**Reasoning:** `a = a.copy()` rebinds `a` to a new list. `b` still references the original.

---

### Q84
```python
def f():
    result = []
    for i in range(5):
        result.append(lambda x: x + i)
    return result

funcs = f()
print(funcs[0](10))
print(funcs[4](10))
```

**Output:**
```
14
14
```

**Reasoning:** All lambdas share the same `i` cell. After the loop, `i = 4`. So all return `x + 4`.

---

### Q85
```python
class Obj:
    def __init__(self, val):
        self.val = val
    def __del__(self):
        print(f"Deleting {self.val}")

a = Obj(1)
b = Obj(2)
a = Obj(3)
```

**Output:**
```
Deleting 1
```

**Reasoning:** When `a` is rebound to `Obj(3)`, the original `Obj(1)` has refcount 0 and is immediately deallocated, triggering `__del__`.

---

### Q86
```python
import weakref

class C:
    pass

obj = C()
ref = weakref.ref(obj)
print(ref() is obj)
del obj
print(ref())
```

**Output:**
```
True
None
```

**Reasoning:** Weak reference doesn't prevent deallocation. After `del obj`, the object is freed and the weakref returns `None`.

---

### Q87
```python
a = [1, 2, 3]
b = iter(a)
a.append(4)
print(list(b))
```

**Output:** `[1, 2, 3, 4]`

**Reasoning:** The iterator references the list object. Modifying the list before exhausting the iterator means the iterator sees the modified list.

---

### Q88
```python
def f():
    x = 'original'
    def g():
        print(x)
    def h():
        x = 'modified'
    h()
    g()

f()
```

**Output:** `original`

**Reasoning:** `h()` creates its own local `x` (no `nonlocal`). The outer `x` used by `g` is unchanged.

---

### Q89
```python
def f():
    x = 'original'
    def g():
        print(x)
    def h():
        nonlocal x
        x = 'modified'
    h()
    g()

f()
```

**Output:** `modified`

**Reasoning:** `nonlocal x` in `h` modifies the shared cell. `g` reads the same cell and sees 'modified'.

---

### Q90
```python
a = {'key': [1, 2, 3]}
b = a.copy()
b['key'] = [4, 5, 6]
print(a['key'])
```

**Output:** `[1, 2, 3]`

**Reasoning:** `b['key'] = [4, 5, 6]` rebinds `b`'s entry to a new list. The original list in `a` is unaffected. (This is rebinding in `b`'s dict, not mutation of the shared list.)

---

### Q91
```python
x = 10

def outer():
    x = 20
    def inner():
        x = 30
        print("inner:", x)
    inner()
    print("outer:", x)

outer()
print("global:", x)
```

**Output:**
```
inner: 30
outer: 20
global: 10
```

**Reasoning:** Three independent `x` variables in three scopes. No `global` or `nonlocal` used.

---

### Q92
```python
def cache(func):
    _cache = {}
    def wrapper(*args):
        if args not in _cache:
            _cache[args] = func(*args)
        return _cache[args]
    return wrapper

@cache
def add(a, b):
    print("computing")
    return a + b

print(add(1, 2))
print(add(1, 2))
print(add(3, 4))
```

**Output:**
```
computing
3
3
computing
7
```

**Reasoning:** First call computes and caches. Second call uses cache (no "computing"). Third call is a new key.

---

### Q93
```python
class Node:
    def __init__(self, val):
        self.val = val
        self.next = None

a = Node(1)
b = Node(2)
a.next = b
b.next = a

del a
del b
# Are the nodes collected?
```

**Output:** No immediate output. The nodes form a reference cycle (refcount 1 each after `del`). They will be collected by the cyclic GC when it runs, but not immediately via reference counting.

---

### Q94
```python
import sys
a = "hello"
b = "hello"
c = "hel" + "lo"
d = "".join(["h","e","l","l","o"])
print(a is b)
print(a is c)
print(a is d)
```

**Output:**
```
True
True
False
```

**Reasoning:** `a` and `b` are the same literal (interned). `c` is constant-folded by the compiler to `"hello"` (same constant). `d` is built at runtime — not automatically interned.

---

### Q95
```python
a = [1, 2, 3]
def f(x=a):
    return x

a.append(4)
print(f())
```

**Output:** `[1, 2, 3, 4]`

**Reasoning:** Default value is evaluated once (at def time) — but it stores the REFERENCE to `a`. Mutating `a` later is visible through the default.

---

### Q96
```python
a = 1
b = 1
print(a is b)
a = 10**100
b = 10**100
print(a is b)
```

**Output:**
```
True
False
```

**Reasoning:** `1` is cached (small int). `10**100` is a huge number outside the cache — two separate objects created.

---

### Q97
```python
a = float('nan')
print(a == a)
print(a is a)
```

**Output:**
```
False
True
```

**Reasoning:** IEEE 754: NaN is not equal to itself. But `a is a` is True because it's the same object.

---

### Q98
```python
a = [1, 2, 3]
b = a
a[:] = []
print(len(b))
```

**Output:** `0`

**Reasoning:** `a[:] = []` clears the list in place. `b` is an alias, sees the empty list.

---

### Q99
```python
import gc

class Leak:
    pass

gc.disable()
a = Leak()
b = Leak()
a.ref = b
b.ref = a
del a, b
print(gc.collect())
```

**Output:** A number ≥ 2 (e.g., `2` or more)

**Reasoning:** The cycle is unreachable. `gc.collect()` detects and collects it, returning the count of collected objects.

---

### Q100
```python
def f():
    return [lambda: i for i in range(3)]

print(f()[0]())
print(f()[1]())
print(f()[2]())
```

**Output:**
```
2
2
2
```

**Reasoning:** All lambdas in the comprehension capture the same `i` variable. After the comprehension completes, `i = 2`.

---

# Part 15 Exercises

## 15.1 Memory Tracing Exercises

### Exercise 1: Trace the Reference Count

For each line, write the reference count of the list object created in line 1:

```python
a = [1, 2, 3]       # Line 1: refcount = ?
b = a               # Line 2: refcount = ?
c = [a, b]          # Line 3: refcount = ?
del b               # Line 4: refcount = ?
c.pop()             # Line 5: refcount = ?
del c               # Line 6: refcount = ?
del a               # Line 7: refcount = ?
```

**Answer:**
- Line 1: 1 (just `a`)
- Line 2: 2 (`a` + `b`)
- Line 3: 4 (`a` + `b` + `c[0]` + `c[1]`)
- Line 4: 3 (`a` + `c[0]` + `c[1]`)
- Line 5: 2 (`a` + `c[0]`)
- Line 6: 1 (`a` only, `c` destroyed which decrements its element)
- Line 7: 0 (object is deallocated)

---

### Exercise 2: Trace Object Lifetimes

Determine when each object is destroyed:

```python
def process():
    x = [10, 20]        # Object A created
    y = {"key": x}      # Object B (dict) created
    z = x               # No new object
    del x               # ?
    del z               # ?
    return y            # ?

result = process()      # ?
del result              # ?
```

**Answer:**
- `del x`: Object A refcount goes from 3 to 2. Not destroyed.
- `del z`: Object A refcount goes from 2 to 1 (still in dict). Not destroyed.
- `return y`: Frame destroyed, but `y` is returned so dict (B) survives. Object A inside dict survives.
- `del result`: Dict (B) refcount 0 -> destroyed. Its destruction decrements Object A -> refcount 0 -> destroyed.

---

### Exercise 3: Identify Mutation vs Rebinding

For each operation, state whether it's mutation or rebinding:

```python
a = [1, 2, 3]
a.append(4)          # ?
a = a + [5]          # ?
a += [6]             # ?
a[0] = 99            # ?
a = sorted(a)        # ?
a.sort()             # ?
a[:] = [1, 2]        # ?
a = [1, 2]           # ?
```

**Answer:**
1. `a.append(4)` — Mutation
2. `a = a + [5]` — Rebinding (new list created)
3. `a += [6]` — Mutation (list.__iadd__)
4. `a[0] = 99` — Mutation
5. `a = sorted(a)` — Rebinding (sorted returns new list)
6. `a.sort()` — Mutation
7. `a[:] = [1, 2]` — Mutation (slice assignment modifies in place)
8. `a = [1, 2]` — Rebinding

---

## 15.2 Draw Object Graphs

### Exercise 4: Draw the Memory State

Draw the object graph after executing:

```python
a = [1, 2, 3]
b = [a, a, 4]
c = b[0]
```

**Expected Diagram:**

```
Namespace:              Heap:
a ──────────────────────────────────────────────► list_1: [1, 2, 3] (refcnt: 4)
                                                     ▲   ▲   ▲
b ──► list_2: [slot0, slot1, slot2] (refcnt: 1)     │   │   │
              slot0 ─────────────────────────────────┘   │   │
              slot1 ─────────────────────────────────────┘   │
              slot2 ──► int(4)                               │
                                                             │
c ───────────────────────────────────────────────────────────┘
```

`list_1` has refcount 4: `a`, `b[0]`, `b[1]`, `c`.

---

### Exercise 5: Draw After Function Call

```python
def modify(lst, val):
    lst.append(val)
    lst = [99]
    return lst

data = [1, 2, 3]
result = modify(data, 4)
```

Draw the state after `modify` returns.

**Expected Diagram:**

```
Namespace:              Heap:
data ──────────────► list_1: [1, 2, 3, 4] (refcnt: 1)

result ────────────► list_2: [99] (refcnt: 1)
```

`data` was mutated (append), but the rebinding inside `modify` created a separate list returned as `result`.

---

### Exercise 6: Draw Closure State

```python
def make_pair():
    data = []
    def add(x):
        data.append(x)
    def get():
        return data[:]
    return add, get

add, get = make_pair()
add(1)
add(2)
```

**Expected Diagram:**

```
add ──► function object
         __closure__[0] ──► Cell ──► list: [1, 2] (refcnt: 1 from cell)
                                ▲
get ──► function object         │
         __closure__[0] ────────┘

Both functions share the same cell, which points to the same list.
```

---

## 15.3 Reference Counting Exercises

### Exercise 7: When Is Memory Freed?

```python
import sys

class Heavy:
    def __init__(self, size):
        self.data = bytearray(size)

a = Heavy(1_000_000)    # 1MB allocated
b = a                   # refcount = 2
lst = [a, b]            # refcount = 4
del a                   # refcount = ?
del b                   # refcount = ?
lst.pop()               # refcount = ?
lst.clear()             # refcount = ? Is 1MB freed?
```

**Answer:** 
- After `del a`: refcount = 3
- After `del b`: refcount = 2
- After `lst.pop()`: refcount = 1
- After `lst.clear()`: refcount = 0 -> object destroyed, 1MB freed. YES.

---

### Exercise 8: Cycle Detection

Will the following objects be collected? When?

```python
import gc
gc.disable()

class Node:
    def __init__(self, val):
        self.val = val
        self.ref = None

a = Node("A")
b = Node("B")
c = Node("C")
a.ref = b
b.ref = c
c.ref = a

del a, b, c
# Are these collected now?

gc.enable()
gc.collect()
# Are they collected now?
```

**Answer:**
- After `del a, b, c`: NOT collected. Each has refcount 1 (from the cycle). GC is disabled.
- After `gc.collect()`: YES, collected. The cyclic GC detects the unreachable cycle and collects all three.

---

### Exercise 9: Weak Reference Behavior

Predict the output:

```python
import weakref

class Data:
    def __init__(self, val):
        self.val = val

strong = Data(42)
weak = weakref.ref(strong)
print(weak().val)          # Line A
another = strong           # Line B
del strong                 # Line C
print(weak().val)          # Line D
del another                # Line E
print(weak())              # Line F
```

**Answer:**
- Line A: `42` (object alive, weak ref returns it)
- Line C: refcount drops from 2 to 1 (another still holds it)
- Line D: `42` (object still alive via `another`)
- Line E: refcount drops to 0, object destroyed
- Line F: `None` (object gone, weak ref dead)

---

## 15.4 Stack vs Heap Exercises

### Exercise 10: Classify Where Things Live

For each item, state whether it lives on the C Stack, Heap, or Data Segment:

| Item | Location |
|------|----------|
| The integer object `42` (small int) | ? |
| The integer object `1000` | ? |
| A function's local variable name (at runtime) | ? |
| The `None` object | ? |
| A list object `[1, 2, 3]` | ? |
| The eval loop's C variables | ? |
| A frame object for `def foo()` | ? |
| The bytecode for `def foo()` | ? |
| The CPython interpreter's machine code | ? |

**Answer:**

| Item | Location |
|------|----------|
| The integer object `42` (small int) | **Data Segment** (pre-allocated in static array) |
| The integer object `1000` | **Heap** (allocated by pymalloc) |
| A function's local variable name (at runtime) | **Heap** (stored in code object's co_varnames tuple) |
| The `None` object | **Data Segment** (static struct `_Py_NoneStruct`) |
| A list object `[1, 2, 3]` | **Heap** (pymalloc) |
| The eval loop's C variables | **C Stack** |
| A frame object for `def foo()` | **Heap** (PyFrameObject) |
| The bytecode for `def foo()` | **Heap** (inside PyCodeObject) |
| The CPython interpreter's machine code | **Text (Code) Segment** |

---

## 15.5 Arena Allocation Exercises

### Exercise 11: Calculate Block Usage

Given: pymalloc size classes are multiples of 16 (16, 32, 48, 64, ..., 512).
A pool is 4096 bytes. Pool header is ~48 bytes.

Calculate:
1. How many 32-byte blocks fit in a pool?
2. How many 64-byte blocks fit in a pool?
3. What is the internal fragmentation when storing a 28-byte int in a 32-byte block?

**Answer:**
1. (4096 - 48) / 32 = 126.5 → **126 blocks**
2. (4096 - 48) / 64 = 63.25 → **63 blocks**
3. 32 - 28 = **4 bytes wasted** per int (12.5% fragmentation)

---

### Exercise 12: Arena Memory Accounting

An arena is 256 KB. It has 64 pools.

If 63 pools are completely empty but 1 pool has a single 32-byte block in use:
1. Can the arena be returned to the OS?
2. How much memory is "wasted" (held but unused)?
3. What strategy does pymalloc use to minimize this?

**Answer:**
1. **No.** Arenas can only be freed if ALL pools are empty.
2. 256 KB - 32 bytes = ~262,112 bytes wasted.
3. Pymalloc allocates from the **fullest** arenas first, concentrating live objects and increasing the chance other arenas become completely empty.

---

## 15.6 Interview Whiteboard Questions

### Exercise 13: Explain This Bug

A junior developer wrote this code and it has a bug. Explain what's wrong:

```python
def process_items(items, results=[]):
    for item in items:
        results.append(item.upper())
    return results

# First batch
batch1 = process_items(["hello", "world"])
print(batch1)  # ['HELLO', 'WORLD']

# Second batch
batch2 = process_items(["foo", "bar"])
print(batch2)  # Expected: ['FOO', 'BAR']
               # Actual: ['HELLO', 'WORLD', 'FOO', 'BAR']
```

**Answer:** Mutable default argument. The default `results=[]` is created once at def time. All calls that use the default share the same list. Fix: use `results=None` and create a new list inside the function.

---

### Exercise 14: Memory-Safe Data Structure

Design a cache that doesn't prevent garbage collection of its values:

```python
# Your implementation here
```

**Answer:**
```python
import weakref

class WeakCache:
    def __init__(self):
        self._cache = weakref.WeakValueDictionary()
    
    def get(self, key):
        return self._cache.get(key)
    
    def set(self, key, value):
        self._cache[key] = value
    
    def __len__(self):
        return len(self._cache)
```

When the value has no strong references elsewhere, it's automatically removed from the cache.

---

### Exercise 15: Find the Memory Leak

What's the memory leak in this server handler?

```python
class RequestHandler:
    _all_handlers = []
    
    def __init__(self, request):
        self.request = request
        self.response = None
        RequestHandler._all_handlers.append(self)
    
    def handle(self):
        self.response = self.process(self.request)
        return self.response
    
    def process(self, request):
        return {"status": "ok", "data": request.data}
```

**Answer:** `_all_handlers` is a class-level list that grows indefinitely. Every request creates a handler that's never removed from the list. Fix: use a `WeakSet`, remove after handling, or don't store handlers globally.

---

### Exercise 16: Implement Reference Counting (Simplified)

Implement a simplified reference counting system in Python that demonstrates the concept:

```python
class RefCounted:
    """Simulate reference counting."""
    _objects = {}  # id -> (object_repr, refcount)
    
    @classmethod
    def new(cls, value):
        """Create a new 'object' and track it."""
        obj_id = id(value)
        cls._objects[obj_id] = (repr(value), 1)
        print(f"Created {repr(value)} at {obj_id}, refcount=1")
        return obj_id
    
    @classmethod
    def incref(cls, obj_id):
        """Increment reference count."""
        if obj_id in cls._objects:
            name, count = cls._objects[obj_id]
            cls._objects[obj_id] = (name, count + 1)
            print(f"INCREF {name}: refcount={count + 1}")
    
    @classmethod
    def decref(cls, obj_id):
        """Decrement reference count. 'Free' if zero."""
        if obj_id in cls._objects:
            name, count = cls._objects[obj_id]
            new_count = count - 1
            if new_count == 0:
                print(f"FREED {name} (refcount reached 0)")
                del cls._objects[obj_id]
            else:
                cls._objects[obj_id] = (name, new_count)
                print(f"DECREF {name}: refcount={new_count}")
    
    @classmethod
    def status(cls):
        print("\n--- Live Objects ---")
        for obj_id, (name, count) in cls._objects.items():
            print(f"  {name}: refcount={count}")
        print()
```

Usage:
```python
# Simulate: a = [1,2,3]; b = a; del a; del b
obj = RefCounted.new([1,2,3])   # refcount=1
RefCounted.incref(obj)           # b = a, refcount=2
RefCounted.decref(obj)           # del a, refcount=1
RefCounted.decref(obj)           # del b, refcount=0, FREED
```

---

### Exercise 17: Predict GC Behavior

```python
import gc

gc.disable()

class A:
    pass

# Create 1000 objects in a cycle
objects = []
for i in range(1000):
    obj = A()
    obj.ref = None
    objects.append(obj)

# Create chain of cycles
for i in range(999):
    objects[i].ref = objects[i + 1]
objects[999].ref = objects[0]  # Close the cycle

# Remove all external references
del objects
del obj

# Questions:
# 1. Are the 1000 objects freed now?
# 2. What does gc.collect() return (approximately)?
# 3. After gc.collect(), are they freed?
```

**Answer:**
1. **No.** Each object has refcount 1 (from the cycle). Reference counting alone can't detect this.
2. `gc.collect()` returns approximately **1000** (the number of unreachable objects collected).
3. **Yes.** The cyclic GC detects the entire cycle is unreachable and collects all 1000 objects.

---

### Exercise 18: Memory Estimation

Estimate the memory usage of the following data structure:

```python
data = [{"name": f"user_{i}", "scores": [i*10, i*20, i*30]} for i in range(10000)]
```

**Approach:**
- Outer list: 56 bytes + 10000 * 8 bytes pointers = ~80 KB
- Each dict: ~200 bytes (keys + values + overhead)
- Each "name" string: ~60 bytes (short ASCII string)
- Each "scores" list: 56 + 3*8 = ~80 bytes (plus the int objects)
- Each int: 28 bytes, 3 per dict = 84 bytes
- Total per element: ~200 + 60 + 80 + 84 = ~424 bytes
- Total: ~424 * 10000 + 80 KB = **~4.3 MB**

(Actual measurement with `tracemalloc` would be ~4-5 MB)

---

### Exercise 19: Optimization Challenge

Optimize this code to use significantly less memory:

```python
# Original: stores 1M Point objects
class Point:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

points = [Point(i, i*2, i*3) for i in range(1_000_000)]
```

**Solution Options:**

```python
# Option 1: __slots__ (~40% savings)
class Point:
    __slots__ = ('x', 'y', 'z')
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

# Option 2: NamedTuple (similar to slots)
from collections import namedtuple
Point = namedtuple('Point', ['x', 'y', 'z'])

# Option 3: NumPy (massive savings for numeric data)
import numpy as np
points = np.zeros((1_000_000, 3), dtype=np.float64)
for i in range(1_000_000):
    points[i] = [i, i*2, i*3]
# Or better:
i = np.arange(1_000_000)
points = np.column_stack([i, i*2, i*3])

# Option 4: struct array (if fixed format needed)
import array
# Store as flat array: x0,y0,z0,x1,y1,z1,...
coords = array.array('d')  # double-precision floats
for i in range(1_000_000):
    coords.extend([float(i), float(i*2), float(i*3)])
```

Memory comparison:
- Original (with `__dict__`): ~200 bytes/point = **200 MB**
- With `__slots__`: ~64 bytes/point = **64 MB**
- NumPy: 24 bytes/point (just 3 float64) = **24 MB**
- struct array: 24 bytes/point = **24 MB**

---

### Exercise 20: Debug a Production Issue

A Django web server's memory grows continuously. After 24 hours, it's using 2 GB. Describe your debugging approach:

**Answer:**

1. **Reproduce and measure:**
```python
import tracemalloc
tracemalloc.start(25)  # 25 frames depth

# Take snapshots before and after requests
snapshot1 = tracemalloc.take_snapshot()
# ... handle 1000 requests ...
snapshot2 = tracemalloc.take_snapshot()

# Compare
top_stats = snapshot2.compare_to(snapshot1, 'lineno')
for stat in top_stats[:20]:
    print(stat)
```

2. **Check for cycles:**
```python
import gc
gc.set_debug(gc.DEBUG_STATS)
gc.collect()
print(f"Uncollectable: {gc.garbage}")
```

3. **Find growing collections:**
```python
import objgraph
objgraph.show_growth(limit=10)
# Run after each request batch
```

4. **Check common culprits:**
- Caches without eviction (`@lru_cache` without maxsize, global dicts)
- Signal/event handlers accumulating
- Database connection pools holding references
- Logging handlers storing messages
- Class-level lists/dicts growing
- Exception tracebacks held in variables

5. **Fix:**
- Add `maxsize` to `@lru_cache`
- Use `WeakValueDictionary` for caches
- Ensure proper cleanup in request handlers
- Set up worker recycling (`max_requests` in gunicorn)

---

## 15.7 Advanced Exercises

### Exercise 21: Implement a Simple Object Graph Traversal

Write a function that counts all objects reachable from a given object (deep size):

```python
import sys

def deep_getsizeof(obj, seen=None):
    """Calculate total memory of obj and everything it references."""
    if seen is None:
        seen = set()
    
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    seen.add(obj_id)
    
    size = sys.getsizeof(obj)
    
    if isinstance(obj, dict):
        size += sum(deep_getsizeof(k, seen) + deep_getsizeof(v, seen) 
                   for k, v in obj.items())
    elif isinstance(obj, (list, tuple, set, frozenset)):
        size += sum(deep_getsizeof(item, seen) for item in obj)
    elif hasattr(obj, '__dict__'):
        size += deep_getsizeof(obj.__dict__, seen)
    elif hasattr(obj, '__slots__'):
        size += sum(deep_getsizeof(getattr(obj, slot, None), seen) 
                   for slot in obj.__slots__ if hasattr(obj, slot))
    
    return size

# Test:
data = {"users": [{"name": "Alice", "scores": [1,2,3]}]}
print(f"Deep size: {deep_getsizeof(data)} bytes")
```

---

### Exercise 22: Detect Reference Cycles

Write a function that detects if an object is part of a reference cycle:

```python
import gc

def has_cycle(obj):
    """Check if obj participates in a reference cycle."""
    seen = set()
    
    def visit(current):
        obj_id = id(current)
        if obj_id == id(obj) and obj_id in seen:
            return True
        if obj_id in seen:
            return False
        seen.add(obj_id)
        
        referents = gc.get_referents(current)
        for ref in referents:
            if visit(ref):
                return True
        return False
    
    # Start from obj's referents
    seen.add(id(obj))
    for ref in gc.get_referents(obj):
        if visit(ref):
            return True
    return False

# Test:
a = []
b = [a]
a.append(b)  # Cycle!
print(has_cycle(a))  # True

c = [1, 2, 3]
print(has_cycle(c))  # False
```

---

### Exercise 23: Verify Integer Caching

Write code to experimentally determine your CPython's integer cache range:

```python
def find_cache_range():
    """Find the range of cached (interned) integers."""
    # Find upper bound
    upper = 0
    while True:
        # Create integers in a way that avoids constant folding
        a = int(str(upper))
        b = int(str(upper))
        if a is not b:
            break
        upper += 1
    
    # Find lower bound
    lower = 0
    while True:
        a = int(str(lower))
        b = int(str(lower))
        if a is not b:
            break
        lower -= 1
    
    return lower + 1, upper - 1

low, high = find_cache_range()
print(f"Integer cache range: [{low}, {high}]")
# Expected: [-5, 256]
```

---

### Exercise 24: Measure Allocation Overhead

Measure the overhead of different container types:

```python
import sys

def measure_overhead():
    """Compare memory overhead of different approaches."""
    N = 10000
    
    # Dict-based objects
    class PointDict:
        def __init__(self, x, y):
            self.x = x
            self.y = y
    
    # Slots-based objects
    class PointSlots:
        __slots__ = ('x', 'y')
        def __init__(self, x, y):
            self.x = x
            self.y = y
    
    # Tuples
    from collections import namedtuple
    PointNT = namedtuple('PointNT', ['x', 'y'])
    
    dict_points = [PointDict(i, i) for i in range(N)]
    slots_points = [PointSlots(i, i) for i in range(N)]
    tuple_points = [PointNT(i, i) for i in range(N)]
    plain_tuples = [(i, i) for i in range(N)]
    
    print(f"Dict-based:  {sys.getsizeof(dict_points[0])} + __dict__")
    print(f"Slots-based: {sys.getsizeof(slots_points[0])} bytes/instance")
    print(f"NamedTuple:  {sys.getsizeof(tuple_points[0])} bytes/instance")
    print(f"Plain tuple: {sys.getsizeof(plain_tuples[0])} bytes/instance")

measure_overhead()
```

---

### Exercise 25: Build a Memory Profiling Decorator

```python
import tracemalloc
import functools

def memory_profile(func):
    """Decorator that reports memory usage of a function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tracemalloc.start()
        
        result = func(*args, **kwargs)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        print(f"[{func.__name__}] Current: {current/1024:.1f} KB, "
              f"Peak: {peak/1024:.1f} KB")
        return result
    return wrapper

# Usage:
@memory_profile
def create_large_list():
    return [i**2 for i in range(100000)]

@memory_profile
def create_generator():
    return (i**2 for i in range(100000))

create_large_list()    # Reports ~4000 KB peak
create_generator()     # Reports ~1 KB peak
```

---

## 15.8 Summary Checklist

After completing all exercises, you should be able to:

- [ ] Trace reference counts through complex code
- [ ] Draw accurate memory diagrams for any Python code
- [ ] Predict output of code involving mutation, rebinding, closures, defaults
- [ ] Explain the complete lifecycle of a Python object
- [ ] Distinguish between language guarantees and CPython implementation details
- [ ] Identify memory leaks and optimization opportunities
- [ ] Explain pymalloc's arena/pool/block architecture
- [ ] Use gc, sys, weakref, tracemalloc for debugging
- [ ] Answer any interview question on Python memory management
- [ ] Write memory-efficient Python code for production systems
