# Part 19A — Exercises: Reference Counts & Object Headers (Questions 1-40)

## Section A: Reference Count Tracing (20 Exercises)

### Exercise 1
Trace ob_refcnt for the list object at each step:
```python
a = [1, 2, 3]     # Step 1
b = a              # Step 2
c = [a, a]         # Step 3
del b              # Step 4
c[0] = None        # Step 5
del c              # Step 6
del a              # Step 7
```

**Answer:**
```
Step 1: refcnt=1 (name 'a')
Step 2: refcnt=2 (a, b)
Step 3: refcnt=4 (a, b, c[0], c[1])
Step 4: refcnt=3 (a, c[0], c[1])
Step 5: refcnt=2 (a, c[1]) — c[0]=None decrefs old value
Step 6: refcnt=1 (a) — c destruction decrefs c[1]
Step 7: refcnt=0 → DEALLOCATED
```

---

### Exercise 2
What is the refcount of the string "hello" after:
```python
x = "hello"
y = x
d = {"key": x}
lst = [x, x, x]
```

**Answer:** 5 references: x, y, d["key"], lst[0], lst[1], lst[2] → wait, that's 6. Actually: x(1) + y(1) + d_value(1) + lst[0](1) + lst[1](1) + lst[2](1) = 6. But if "hello" is interned, additional internal references exist.

---

### Exercise 3
Explain why `sys.getrefcount(x)` returns one more than expected:
```python
import sys
a = [1, 2, 3]
print(sys.getrefcount(a))  # Prints 2, not 1!
```

**Answer:** The function argument itself is a reference. Passing `a` to `getrefcount` creates a temporary reference (the function's local parameter), so the count is 1 (from `a`) + 1 (function argument) = 2.

---

### Exercise 4
Trace refcount of the integer object `42`:
```python
x = 42
y = 42
z = x
del x
del y
del z
```

**Answer:** Small integer 42 is cached (immortal in 3.12+). Its refcount starts very high (many internal references). x, y, z all point to the SAME cached object. del operations decrement, but it never reaches 0 (too many other references from the cache). The integer is never deallocated.

---

### Exercise 5
What happens to refcounts during a function call?
```python
def foo(param):
    local = param
    return local

obj = [1, 2, 3]    # obj refcnt = 1
result = foo(obj)   # What happens inside?
```

**Answer:**
```
Before call:         obj refcnt = 1
Enter foo:           param created → refcnt = 2 (obj + param)
local = param:       refcnt = 3 (obj + param + local)
return local:        return value → refcnt = 3 (obj + param + return_val)
Exit foo:            param destroyed, local destroyed → refcnt = 2 (obj + result)
After assignment:    result = return_val → refcnt = 2 (obj + result)
                     (obj and result point to same object)
```

---

### Exercise 6
Trace refcounts for circular reference:
```python
a = []          # a's list refcnt = 1
b = []          # b's list refcnt = 1
a.append(b)     # b's list refcnt = 2
b.append(a)     # a's list refcnt = 2
del a           # a's list refcnt = 1 (b[0] still holds it)
del b           # b's list refcnt = 1 (the list formerly known as a[0] still holds it)
# Both refcnts are 1, not 0 → memory leak without GC!
```

**Answer:** This is exactly why CPython has a cycle-detecting garbage collector. Reference counting alone cannot free these objects.

---

### Exercise 7
What is the refcount of `None` and why?
```python
import sys
print(sys.getrefcount(None))  # Very large number (thousands!)
```

**Answer:** None is used internally everywhere (default return values, uninitialized variables, etc.). Every function that returns None, every None default argument, every unset attribute contributes. In 3.12+, None is immortal (refcount never changes).

---

### Exercise 8
Trace refcounts during slice assignment:
```python
a = [10, 20, 30]
b = a[0]           # b → int(10), int(10).refcnt += 1
a[0] = 99          # int(10).refcnt -= 1, int(99).refcnt += 1
```

**Answer:** When a[0] is replaced, the old object (10) is decref'd and the new object (99) is incref'd. Since 10 is a cached small int, it won't be deallocated.

---

### Exercise 9
What's wrong with this C extension code?
```c
PyObject *result = PyLong_FromLong(42);
PyList_SetItem(mylist, 0, result);
Py_DECREF(result);  // BUG?
```

**Answer:** PyList_SetItem "steals" the reference — it does NOT incref the item. So after SetItem, the list owns the reference. Calling Py_DECREF after is a double-decref bug. The correct code omits the Py_DECREF.

---

### Exercise 10
Explain the refcount flow in:
```python
x = [1, 2, 3]
y = x.copy()
```

**Answer:** 
- x's list: refcnt stays at 1 (copy creates a new list, not a new ref to x)
- y's list: refcnt = 1 (just y references it)
- int(1), int(2), int(3): each gets +1 refcnt (now in BOTH lists)

---

### Exercises 11-20: (Pattern — provide similar tracing exercises)

### Exercise 11
```python
def make_pair(x):
    return (x, x)
obj = object()       # refcnt = 1
pair = make_pair(obj) # After this line, what is obj's refcnt?
```
**Answer:** 3 — `obj` (1) + `pair[0]` (1) + `pair[1]` (1). The tuple holds two references.

### Exercise 12
```python
a = "test"
b = a
c = a
d = {a: 1}
del a, b
```
After this, what references to the string "test" remain? **Answer:** c (1) + dict key (1) = refcnt ≥ 2 (plus interning if applicable).

### Exercise 13
```python
lst = [None] * 1000
```
What is None's refcount change? **Answer:** +1000 (each slot holds a reference to None).

### Exercise 14
```python
a = []
a.append(a)
sys.getrefcount(a)  # What value?
```
**Answer:** 3 — variable `a` (1) + a[0] (1) + getrefcount argument (1).

### Exercise 15
```python
x = (1, 2, 3)
y = x
del x
# Is the tuple deallocated?
```
**Answer:** No. y still holds a reference. refcnt went from 2 to 1, not 0.

### Exercise 16
What's the refcount of `True` after `[True] * 10000`?
**Answer:** +10000 from the list. True is immortal in 3.12+ so effectively unchanged operationally.

### Exercise 17
```python
d = {"a": 1}
k = list(d.keys())[0]  # "a"
del d
# Is "a" still alive?
```
**Answer:** Yes — k holds a reference to the string "a" (refcnt ≥ 1).

### Exercise 18
```python
import weakref
class Foo: pass
obj = Foo()
ref = weakref.ref(obj)
# What is obj's refcnt?
```
**Answer:** 1 — only `obj`. Weak references do NOT increment refcnt.

### Exercise 19
```python
a = [1, 2, 3]
b = a
a = a + [4]  # Note: creates new list!
# Is b affected?
```
**Answer:** No. `a + [4]` creates a NEW list, rebinds `a`. `b` still points to the original [1,2,3]. Original list's refcnt: was 2 (a,b), now 1 (just b).

### Exercise 20
```python
a = [1, 2, 3]
b = a
a += [4]  # Note: extends in place!
# Is b affected?
```
**Answer:** Yes! `+=` calls extend (in-place). Both a and b point to same [1,2,3,4]. refcnt stays at 2.

---

## Section B: Object Header Questions (20 Exercises)

### Exercise 21
Draw the memory layout (with byte offsets) for `x = 3.14`:
```
Offset 0x00: ob_refcnt = 1        (8 bytes)
Offset 0x08: ob_type → PyFloat_Type (8 bytes)
Offset 0x10: ob_fval = 3.14       (8 bytes)
Total: 24 bytes
```

### Exercise 22
Draw the memory layout for `x = True`:
```
PyLongObject (True is an int subclass):
Offset 0x00: ob_refcnt = (high/immortal)  (8 bytes)
Offset 0x08: ob_type → PyBool_Type         (8 bytes)
Offset 0x10: ob_size = 1                   (8 bytes)
Offset 0x18: ob_digit[0] = 1              (4 bytes)
Total: ~28 bytes (padded to 32)
```

### Exercise 23
What is the ob_type chain for a user-defined class instance?
```python
class Dog: pass
rex = Dog()
```
**Answer:**
```
rex.ob_type → Dog (class object)
Dog.ob_type → type (PyType_Type)
type.ob_type → type (itself)
```

### Exercise 24
If `sys.getsizeof(42)` returns 28, break down those bytes:
**Answer:** ob_refcnt(8) + ob_type(8) + ob_size(8) + ob_digit[0](4) = 28 bytes.

### Exercise 25
Why does `sys.getsizeof(2**30)` return 32 while `sys.getsizeof(2**30 - 1)` returns 28?
**Answer:** 2^30 requires 2 digits in CPython's internal representation (each digit holds 30 bits). 28 + 4 (extra digit) = 32 bytes. 2^30-1 fits in one digit → 28 bytes.

### Exercise 26
What is ob_size for `x = -42`?
**Answer:** ob_size = -1. The sign of ob_size encodes the sign of the integer. Negative ob_size = negative number. |ob_size| = number of digits used.

### Exercise 27
What is ob_size for `x = 0`?
**Answer:** ob_size = 0. Zero is represented with zero digits.

### Exercise 28
Draw the ob_type pointer chain for: `x = [1, 2, 3]`
```
x (PyListObject) → ob_type → PyList_Type (PyTypeObject) → ob_type → PyType_Type → ob_type → PyType_Type (self)
```

### Exercise 29
What is the sizeof(PyObject) on 32-bit vs 64-bit?
**Answer:** 32-bit: 4 (refcnt) + 4 (type ptr) = 8 bytes. 64-bit: 8 + 8 = 16 bytes.

### Exercise 30
How many bytes does a tuple `(1, 2, 3)` use (approximately)?
**Answer:** PyVarObject header (24) + 3 pointers (3×8=24) = 48 bytes. Plus possible GC header (24) = 72 bytes total for the tuple object itself. (The integers are cached separately.)

### Exercise 31-40: Additional layout exercises

### Exercise 31
What fields distinguish PyListObject from PyTupleObject structurally?
**Answer:** PyListObject has `ob_item` (pointer to array) + `allocated` (capacity). PyTupleObject has `ob_item[1]` (flexible array, inline). Lists have indirection + overallocation; tuples store pointers inline.

### Exercise 32
Why is `id(x) == id(y)` possible even when x and y are different objects?
**Answer:** Only if they don't exist simultaneously. After x is deallocated, y may reuse its address. `id()` is unique only during an object's lifetime.

### Exercise 33
Draw the ob_type pointer for `type` itself.
**Answer:** `PyType_Type.ob_type = &PyType_Type` — points to itself. The bootstrap paradox is resolved at interpreter initialization.

### Exercise 34
What GC header fields exist and what are their sizes on 64-bit?
**Answer:** `_gc_next` (8 bytes) + `_gc_prev` (8 bytes) + gc state bits (often encoded in the pointers' unused bits or a separate field). ~16-24 bytes.

### Exercise 35
If an object is at address 0x7F001000 and has a GC header, where does the GC header start?
**Answer:** Before the object: at approximately 0x7F000FE8 (24 bytes before the PyObject header). The "pointer to object" points past the GC header.

### Exercise 36
Why does `sys.getsizeof('')` return 49-50 bytes (not 16)?
**Answer:** PyUnicodeObject has: PyObject header (16) + hash (8) + length (8) + various flags/kind (several bytes) + null terminator. Even empty strings carry all this metadata.

### Exercise 37
What happens to ob_type when you do `x.__class__ = OtherType`?
**Answer:** `x->ob_type` is changed to point to OtherType's type object. Only works if layouts are compatible (same tp_basicsize, same GC tracking status, etc.).

### Exercise 38
How can you tell from the C struct whether an object is GC-tracked?
**Answer:** Check `Py_TYPE(obj)->tp_flags & Py_TPFLAGS_HAVE_GC`. If set, the object has a GC header prepended and is in the GC's tracking list.

### Exercise 39
What is the overhead of storing a million `float` objects in a list?
**Answer:** Each float: 24 bytes. List pointer array: 1M × 8 = 8MB. Total: 24M (floats) + 8M (pointers) + list overhead = ~32 MB. Compare to C: 8 MB (just the doubles).

### Exercise 40
Explain why `sys.getsizeof({})` ≠ `sys.getsizeof(dict())`.
**Answer:** They're actually the same — both create empty dicts. If you see different values, it's because one was measured after insertion/deletion changed internal allocation.
