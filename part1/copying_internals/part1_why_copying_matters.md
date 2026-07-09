# Part 1 — Why Copying Matters

## 1.1 Python's Reference Semantics

In Python, variables don't contain objects — they contain **references** (pointers) to objects. This is fundamentally different from languages like C where variables directly hold values.

```python
a = [1, 2, 3]
# 'a' doesn't contain [1,2,3] — it points to a list object on the heap

b = a
# 'b' now points to the SAME object — NOT a copy!
# There is still only ONE list in memory.
```

```
    'a' ──→ [1, 2, 3]  ←── 'b'
              (one object, refcnt=2)
```

This means **every assignment is aliasing**, not copying. If you need an independent copy, you must explicitly create one.

---

## 1.2 The Problem: Unintended Mutation

```python
def process(data):
    data.sort()        # MODIFIES the original!
    return data[:5]

original = [3, 1, 4, 1, 5, 9, 2, 6]
top_five = process(original)
print(original)  # [1, 1, 2, 3, 4, 5, 6, 9] — SORTED! Not what we wanted!
```

The caller didn't expect `original` to be modified. This is the **aliasing trap** — passing a mutable object to a function gives the function power to mutate the caller's data.

Fix:
```python
def process(data):
    data = sorted(data)  # Creates new list, doesn't modify original
    return data[:5]
# OR:
def process(data):
    data = data.copy()   # Explicit copy before mutating
    data.sort()
    return data[:5]
```

---

## 1.3 Why Copying Is Non-Trivial

For a simple list of integers:
```python
a = [1, 2, 3]
b = a.copy()
# Simple — integers are immutable, sharing them is safe.
```

But for nested structures:
```python
a = [[1, 2], [3, 4], {"key": [5, 6]}]
b = a.copy()  # Shallow — inner lists and dict are SHARED!

b[0].append(99)
print(a[0])  # [1, 2, 99] — OOPS! Inner list is shared!
```

The question becomes: **how deep do you copy?**

---

## 1.4 The Three Levels

```
Level 0: Assignment (No Copy)
  b = a
  ┌───┐    ┌─────────┐
  │ a │──→ │ Object  │ ←──│ b │
  └───┘    └─────────┘    └───┘
  One object, two names.

Level 1: Shallow Copy
  b = a.copy()
  ┌───┐    ┌─────────────────┐
  │ a │──→ │ List A          │
  └───┘    │ [ptr0, ptr1]    │
           └──┬───────┬──────┘
              │       │
              ▼       ▼
           obj_0   obj_1      ← SHARED elements
              ↑       ↑
           ┌──┴───────┴──────┐
  ┌───┐    │ List B (NEW)    │
  │ b │──→ │ [ptr0, ptr1]    │
  └───┘    └─────────────────┘
  Two containers, shared elements.

Level 2: Deep Copy
  b = copy.deepcopy(a)
  ┌───┐    ┌─────────────────┐
  │ a │──→ │ List A          │
  └───┘    │ [ptr0, ptr1]    │
           └──┬───────┬──────┘
              │       │
              ▼       ▼
           obj_0   obj_1      ← originals
           
  ┌───┐    ┌─────────────────┐
  │ b │──→ │ List B (NEW)    │
  └───┘    │ [ptr0', ptr1']  │
           └──┬───────┬──────┘
              │       │
              ▼       ▼
           obj_0'  obj_1'     ← COPIES (independent)
  Everything independent.
```

---

## 1.5 When Each Level Is Appropriate

| Scenario | Level | Method |
|----------|-------|--------|
| Just need another name | Assignment | `b = a` |
| Return value you'll use read-only | Assignment | `return data` |
| Independent list, immutable contents | Shallow | `a.copy()` |
| Pass to function that might mutate container | Shallow | `func(a.copy())` |
| Independent nested structure | Deep | `copy.deepcopy(a)` |
| Configuration with nested dicts | Deep | `copy.deepcopy(config)` |
| Protect from all mutation | Deep | `copy.deepcopy(a)` |
| Performance-critical, read-only use | None | Just reference |

---

## 1.6 The Cost Spectrum

```
Assignment:     O(1)      — just increment refcount
Shallow copy:   O(n)      — copy n pointers + incref each
Deep copy:      O(N)      — copy entire object graph
                            (may be orders of magnitude slower)

For a list of 1M items:
  Assignment:  ~20 ns
  Shallow:     ~5 ms (copy 1M pointers)
  Deep:        ~500 ms+ (recursively copy all nested objects)
```

---

## 1.7 Language Guarantee vs Implementation Detail

**Language guarantee:**
- Assignment creates a new reference to the same object
- `a is b` after `b = a` is always True
- Mutating through one reference is visible through the other
- `.copy()` methods create shallow copies
- `copy.deepcopy()` creates fully independent copies

**Implementation detail (CPython-specific):**
- Small integers/strings may be shared even without explicit assignment
- Some copy operations may return the original for immutables
- The memo dict in deepcopy uses object id() (memory address)

---

## 1.8 Interview Questions — Part 1

**Q1**: Why is `b = a` not a copy in Python?
**A**: Python uses reference semantics. Variables hold pointers to objects, not the objects themselves. Assignment copies the pointer, not the object. Both names reference the same object.

**Q2**: What's the danger of passing mutable objects to functions?
**A**: The function can mutate the object, affecting the caller's data. This is aliasing — the function and caller share the same object through different names.

**Q3**: What are the three levels of "copying" in Python?
**A**: Assignment (no copy, shared object), shallow copy (new container, shared elements), deep copy (everything new, fully independent).

**Q4**: When is a shallow copy sufficient?
**A**: When the container elements are immutable (int, str, tuple) or when you only need independence at the container level (add/remove items independently but sharing elements is fine).

**Q5**: When must you use deep copy?
**A**: When you have nested mutable objects (list of lists, dict of dicts) and need full independence — mutations to any level of nesting must not affect the original.
