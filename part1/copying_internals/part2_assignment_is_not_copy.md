# Part 2 — Assignment Is Not Copy

## 2.1 Name Binding Semantics

In Python, `b = a` does NOT copy the object. It creates a new **name binding** — another name that references the same object.

```python
a = [1, 2, 3]    # Create list, bind name 'a' to it
b = a             # Bind name 'b' to the SAME object
```

At the C level:
```c
// b = a (simplified bytecode execution):
PyObject *value = locals['a'];      // Get the object
Py_INCREF(value);                   // New reference → increment refcount
locals['b'] = value;                // Store same pointer under name 'b'
```

The object is NOT duplicated. The refcount goes from 1 to 2. Both `a` and `b` hold the same pointer.

---

## 2.2 Proof: Identity and Mutation

```python
a = [1, 2, 3]
b = a

# Proof 1: Same object
print(a is b)         # True — same identity
print(id(a) == id(b)) # True — same address

# Proof 2: Mutation visible through both
a.append(4)
print(b)              # [1, 2, 3, 4] — b sees the change!

b[0] = 99
print(a)              # [99, 2, 3, 4] — a sees the change!
```

---

## 2.3 Memory Diagram

```
BEFORE: a = [1, 2, 3]

  'a' ──→ PyListObject (refcnt=1)
           ob_item → [ptr→1, ptr→2, ptr→3]

AFTER: b = a

  'a' ──→ PyListObject (refcnt=2) ←── 'b'
           ob_item → [ptr→1, ptr→2, ptr→3]

STILL ONE LIST OBJECT. Two names. That's it.
```

---

## 2.4 Assignment with Rebinding

Rebinding is different from mutation:

```python
a = [1, 2, 3]
b = a           # Both point to same list

a = [4, 5, 6]  # REBIND 'a' to a NEW list!
print(b)        # [1, 2, 3] — b still points to the OLD list
print(a is b)   # False — different objects now
```

```
AFTER a = [4, 5, 6]:

  'a' ──→ [4, 5, 6]  (NEW object, refcnt=1)
  'b' ──→ [1, 2, 3]  (OLD object, refcnt=1)
```

Key distinction:
- `a.append(x)` — **mutates** the object (b sees it)
- `a = new_value` — **rebinds** the name (b is unaffected)

---

## 2.5 Function Arguments Are Assignments

```python
def modify(lst):
    lst.append(4)     # Mutates the passed object
    lst = [10, 20]    # Rebinds local name — caller unaffected

data = [1, 2, 3]
modify(data)
print(data)           # [1, 2, 3, 4] — append visible, rebind not
```

Calling `modify(data)` is equivalent to `lst = data` — it creates a new local name pointing to the same object. Mutations through `lst` affect `data`. Rebinding `lst` only changes the local variable.

---

## 2.6 The `+=` Trap

`+=` behaves differently for mutable vs immutable types:

### Mutable (list): in-place mutation
```python
a = [1, 2, 3]
b = a
a += [4, 5]       # Calls a.__iadd__([4,5]) → extends IN PLACE
print(b)          # [1, 2, 3, 4, 5] — b sees the change!
print(a is b)     # True — same object
```

### Immutable (tuple, str, int): rebinding
```python
a = (1, 2, 3)
b = a
a += (4, 5)       # Creates NEW tuple, rebinds 'a'
print(b)          # (1, 2, 3) — b unaffected
print(a is b)     # False — different objects
```

The `+=` operator:
- For mutable objects with `__iadd__`: modifies in place, returns self
- For immutable objects: falls back to `__add__`, creates new object, rebinds

---

## 2.7 Common Aliasing Bugs

### Bug 1: Default mutable argument
```python
def append_to(item, target=[]):   # DEFAULT IS SHARED!
    target.append(item)
    return target

print(append_to(1))  # [1]
print(append_to(2))  # [1, 2] — same list!
print(append_to(3))  # [1, 2, 3] — still accumulating!
```

Fix: `def append_to(item, target=None): target = [] if target is None else target`

### Bug 2: Class attribute sharing
```python
class Team:
    members = []    # SHARED among all instances!

t1 = Team()
t2 = Team()
t1.members.append("Alice")
print(t2.members)  # ["Alice"] — same list!
```

Fix: Initialize in `__init__`: `self.members = []`

### Bug 3: List of same reference
```python
row = [0] * 5       # Fine — integers are immutable
matrix = [row] * 3  # BUG — 3 references to SAME list!
matrix[0][0] = 1
print(matrix)        # [[1,0,0,0,0], [1,0,0,0,0], [1,0,0,0,0]]
```

Fix: `matrix = [[0]*5 for _ in range(3)]`

---

## 2.8 When Assignment Is Exactly What You Want

Assignment (aliasing) is correct when:
- You need multiple names for the same object (readability)
- You're passing to a function that should modify the object
- The object is immutable (sharing is always safe)
- You want zero-cost "copying" for read-only access

```python
# These are fine — aliasing intentional:
original = data
sorted_ref = data    # Will use sorted_ref for reads only
cache[key] = value   # Store reference in cache
return self.items    # Return reference (caller knows not to mutate)
```

---

## 2.9 Interview Questions — Part 2

**Q1**: After `b = a`, does modifying `b` affect `a`?
**A**: If you MUTATE through `b` (e.g., `b.append(x)`): yes, `a` sees the change. If you REBIND `b` (e.g., `b = new_value`): no, `a` is unaffected.

**Q2**: What does `a += [4]` do to `b` if `b = a` (for lists)?
**A**: `b` sees the change. `+=` for lists calls `__iadd__` which extends in place. `a` and `b` still reference the same (now longer) list.

**Q3**: What does `a += (4,)` do to `b` if `b = a` (for tuples)?
**A**: `b` is unaffected. `+=` for tuples creates a new tuple (immutable can't modify in place), rebinds `a`. `b` still points to the original.

**Q4**: Why is `def f(x=[]):` a bug?
**A**: The default `[]` is created once at function definition time. All calls that use the default share the same list object. Mutations accumulate across calls.

**Q5**: How many objects exist after `a = [1,2,3]; b = a; c = a`?
**A**: One list object (with refcount 3). Three names all point to it. Plus the three integer objects (cached singletons).
