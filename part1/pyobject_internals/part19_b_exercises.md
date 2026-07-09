# Part 19B — Exercises: Identity, Memory Layout, Object Graphs (Questions 41-75+)

## Section C: Identity & Memory (15 Exercises)

### Exercise 41
Predict the output:
```python
a = 256
b = 256
print(a is b)

c = 257
d = 257
print(c is d)
```

**Answer:** `True` then... it depends on context. In interactive REPL: likely `False` (257 is outside the small int cache). In a script (same compilation unit): may be `True` (compiler may intern the constant).

---

### Exercise 42
Explain why:
```python
a = "hello"
b = "hello"
print(a is b)  # True

c = "hello world!"
d = "hello world!"
print(c is d)  # Might be False in REPL
```

**Answer:** "hello" looks like an identifier — CPython interns it. "hello world!" contains spaces/punctuation — not auto-interned in interactive mode. In a compiled script, both may be interned as constants.

---

### Exercise 43
```python
a = (1, 2, 3)
b = (1, 2, 3)
print(a is b)
```

**Answer:** In a script: likely `True` (constant folding — compiler reuses the tuple constant). In REPL: likely `False` (separate compilation units create separate tuples). NOT guaranteed by the language.

---

### Exercise 44
```python
a = []
b = []
print(a is b)  # ?

c = ()
d = ()
print(c is d)  # ?
```

**Answer:** `False` — each `[]` creates a new mutable list. `True` — empty tuple is a singleton (immutable, so safe to share).

---

### Exercise 45
After this code, how many distinct objects exist?
```python
x = [1, 2, 3]
y = x
z = x[:]
```

**Answer:** Objects: one list (shared by x,y), one different list (z), plus the integers 1,2,3 (shared by both lists). Total distinct objects: 2 lists + 3 integers = 5 objects. (Integers are from the small int cache, already existed.)

---

### Exercise 46
```python
def f():
    return []

a = f()
b = f()
print(a is b)
```

**Answer:** `False`. Each call to f() creates a new list object.

---

### Exercise 47
```python
a = None
b = None
print(a is b)
print(id(a) == id(b))
```

**Answer:** Both `True`. None is a singleton — there's only one None object.

---

### Exercise 48
Explain why this is dangerous:
```python
if id(a) == id(b):
    print("same object!")  # NOT always correct!
```

**Answer:** If `a` and `b` are temporary expressions, the first might be deallocated before the second is created, and the second could reuse the same address. Always use `a is b` instead.

---

### Exercise 49
```python
a = 1000
b = 1000
print(a is b)  # In a .py file

# vs interactive:
>>> a = 1000
>>> b = 1000
>>> a is b  # ?
```

**Answer:** In a .py file: likely `True` (constant folding in the same code object). Interactive: `False` (each line is a separate compilation unit, creates separate int objects).

---

### Exercise 50
What does this print?
```python
print(id([]) == id([]))
```

**Answer:** `True`! The first `[]` is created, its id is taken, then it's immediately destroyed (refcnt→0). The second `[]` is created at the same address (memory reuse). Same id!

---

### Exercise 51
```python
a = intern("hello" + " " + "world")
b = intern("hello world")
print(a is b)
```
(Assuming `from sys import intern`)

**Answer:** `True`. `intern()` ensures that equal strings share one object. After interning, both point to the same string.

---

### Exercise 52
Why does `float('nan') is float('nan')` return `False`?

**Answer:** Each `float('nan')` call creates a new PyFloatObject. Unlike small integers and short strings, floats are not cached/interned. Two NaN objects are different objects even though both are NaN.

---

### Exercise 53
```python
a = (1,)
b = (1,)
print(a is b)
print(a[0] is b[0])
```

**Answer:** `a is b`: may be True (constant folding in script) or False (REPL). `a[0] is b[0]`: Always True — int 1 is a cached small integer singleton.

---

### Exercise 54
How many objects does this create?
```python
x = {"a": 1, "b": 2, "c": 3}
```

**Answer:** 1 dict object + 3 string objects ("a", "b", "c") + 3 integer objects (1, 2, 3) = 7 objects minimum. (Strings may be interned/shared; ints are cached. The dict is the only guaranteed new object.)

---

### Exercise 55
```python
a = [1, 2]
b = [1, 2]
print(a == b)   # ?
print(a is b)   # ?
a.append(3)
print(b)        # ?
```

**Answer:** `True`, `False`, `[1, 2]`. Equal but different objects. Mutating `a` doesn't affect `b`.

---

## Section D: Object Graph Exercises (10 Exercises)

### Exercise 56
Draw the complete object graph for:
```python
a = [1, [2, 3], "hello"]
```
Show all objects and reference edges.

**Answer:**
```
name 'a' ──→ list_A [refcnt=1]
               │
               ├──[0]──→ int(1) [cached, high refcnt]
               ├──[1]──→ list_B [refcnt=1]
               │           ├──[0]──→ int(2)
               │           └──[1]──→ int(3)
               └──[2]──→ str("hello") [may be interned]
```

---

### Exercise 57
Draw the object graph showing a cycle:
```python
a = {}
b = {}
a["b"] = b
b["a"] = a
```

**Answer:**
```
name 'a' ──→ dict_A [refcnt=2: 'a' + dict_B["a"]]
               │
               └── "b" → dict_B [refcnt=2: 'b' + dict_A["b"]]
                           │
                           └── "a" → dict_A (circular!)

After del a, del b:
  dict_A refcnt=1 (from dict_B)
  dict_B refcnt=1 (from dict_A)
  Neither reaches 0 → cycle collector needed!
```

---

### Exercise 58
How many reference count increments occur during:
```python
result = [x**2 for x in range(5)]
```

**Answer:** For each of the 5 iterations:
- range iterator produces int → refcnt management
- x**2 creates new int → refcnt=1
- LIST_APPEND increfs the new int into the list
- x is reassigned each iteration (old decref, new incref)
Total: approximately 5 increfs for list storage + ~10 for iteration variable management + list creation = ~20+ refcount operations.

---

### Exercise 59
Draw the object graph after:
```python
class Node:
    def __init__(self, val, next=None):
        self.val = val
        self.next = next

c = Node(3)
b = Node(2, c)
a = Node(1, b)
```

**Answer:**
```
'a' → Node_A [__dict__: {val:1, next: →Node_B}]
                                         │
'b' → Node_B [__dict__: {val:2, next: →Node_C}]
                                         │
'c' → Node_C [__dict__: {val:3, next: None}]

Node_A.refcnt = 1 (name 'a')
Node_B.refcnt = 2 (name 'b' + Node_A.next)
Node_C.refcnt = 2 (name 'c' + Node_B.next)
```

---

### Exercise 60
What happens to refcounts when you do `a.next = a` (making a cycle in Exercise 59)?
```python
a.next = a  # self-referential!
```

**Answer:** 
- Old a.next (Node_B) gets decref'd: Node_B.refcnt = 2→1 (still alive via 'b')
- a (Node_A) gets incref'd: Node_A.refcnt = 1→2 (name 'a' + a.__dict__['next'])
- Now Node_A has a self-reference cycle

---

### Exercise 61
After `del a, b, c` from Exercise 59 (without the cycle), what's deallocated?

**Answer:**
- del a: Node_A.refcnt = 1→0 → dealloc Node_A → decrefs val(1) and next(Node_B)
  - Node_B.refcnt = 2→1 (still referenced by 'b')
- del b: Node_B.refcnt = 1→0 → dealloc Node_B → decrefs val(2) and next(Node_C)  
  - Node_C.refcnt = 2→1
- del c: Node_C.refcnt = 1→0 → dealloc Node_C
- All nodes deallocated by reference counting alone (no cycles).

---

### Exercise 62
Explain why this leaks memory without the GC:
```python
def leak():
    a = []
    b = []
    a.append(b)
    b.append(a)
    # a and b go out of scope
```

**Answer:** After the function returns, names a and b are destroyed. But a.refcnt=1 (from b[0]) and b.refcnt=1 (from a[0]). Neither reaches 0. Without the cycle GC, these are leaked.

---

### Exercise 63
How does `gc.collect()` resolve the cycle in Exercise 62?

**Answer:** The cycle collector: 1) Copies refcounts to gc_refs. 2) For each tracked object, decrements gc_refs for each internal reference. 3) Objects with gc_refs=0 after this are unreachable from outside the set. 4) Calls tp_clear to break cycles. 5) Deallocates.

---

### Exercise 64
Draw the object graph for:
```python
funcs = [lambda x: x+i for i in range(3)]
```

**Answer:**
```
'funcs' → list [func_0, func_1, func_2]
                  │        │        │
                  ▼        ▼        ▼
            PyFunction PyFunction PyFunction
                  │        │        │
                  └────────┼────────┘
                           ▼
                    cell object → int(2)  ← ALL share same cell!
                    (closure variable 'i')
```
Note: All three lambdas share the SAME closure cell for `i`, which holds the final value 2. This is the classic "closure in loop" gotcha.

---

### Exercise 65
What is the total refcount of `int(1)` in a fresh Python interpreter?

**Answer:** Extremely high (hundreds or thousands). The integer 1 is used everywhere internally: True==1, list/dict sizes, function argument counts, etc. In 3.12+, it's immortal with a special refcount.

---

## Section E: PyObject vs PyVarObject Classification (10 Exercises)

### Exercise 66
Classify each as PyObject-based (fixed) or PyVarObject-based (variable):
- float → **Fixed** (PyObject + double = always 24 bytes)
- int → **Variable** (ob_size = number of digits, variable for large ints)
- complex → **Fixed** (PyObject + two doubles = always 32 bytes)
- str → **Variable** (ob_size = length, variable character data)
- bytes → **Variable** (ob_size = length)
- list → **Variable** (but ob_size is in PyVarObject, actual items via pointer)
- tuple → **Variable** (ob_size items stored inline)
- dict → **Fixed** struct (PyDictObject is fixed size; variable data is in separate allocations)
- set → **Fixed** struct (PySetObject with embedded small table)
- bool → **Fixed** (always same size, subclass of int with 1 digit)

### Exercise 67
Why is dict a fixed-size object even though it holds variable data?

**Answer:** PyDictObject is a fixed-size struct (ob_refcnt, ob_type, ma_used, ma_keys pointer, ma_values pointer). The VARIABLE-SIZE data (the hash table + entries) is in a SEPARATE heap allocation pointed to by ma_keys. The dict object itself is always the same size.

### Exercise 68
Why is tuple a variable-size object?

**Answer:** PyTupleObject stores its element pointers INLINE (as a flexible array member). A 3-element tuple is physically larger than a 2-element tuple. ob_size tells how many pointers follow the header.

### Exercise 69
What is ob_size for `x = -123456789012345678`?

**Answer:** The absolute value needs multiple 30-bit digits. 123456789012345678 requires ceil(log2(123456789012345678) / 30) = ceil(57/30) = 2 digits. ob_size = -2 (negative sign encoded in ob_size sign).

### Exercise 70
What is ob_size for an empty tuple `()`?

**Answer:** 0. No element pointers follow the header.

### Exercise 71
Draw the struct layout difference between a 2-element and 5-element tuple:

**Answer:**
```
Tuple (1,2):                    Tuple (1,2,3,4,5):
+0x00: ob_refcnt (8)           +0x00: ob_refcnt (8)
+0x08: ob_type (8)             +0x08: ob_type (8)
+0x10: ob_size = 2 (8)         +0x10: ob_size = 5 (8)
+0x18: item[0] (8) → int(1)   +0x18: item[0] (8)
+0x20: item[1] (8) → int(2)   +0x20: item[1] (8)
Total: 40 bytes                 +0x28: item[2] (8)
                                +0x30: item[3] (8)
                                +0x38: item[4] (8)
                                Total: 64 bytes
```

### Exercise 72
Why doesn't list use inline storage like tuple?

**Answer:** Lists are mutable (can grow/shrink). If elements were inline, every append would require reallocating the ENTIRE list object (changing its address, breaking references). Instead, list uses a separate pointer array (ob_item) that can be reallocated independently.

### Exercise 73
What is tp_itemsize for:
- tuple: 8 (sizeof(PyObject*) — one pointer per element)
- str (compact ASCII): 1 (one byte per character)
- bytes: 1 (one byte per element)
- int: 4 (sizeof(digit) — one uint32_t per digit)
- list: 0 (fixed-size struct; items stored elsewhere)

### Exercise 74
Calculate the allocation size for `tuple(range(100))`:
```
tp_basicsize + 100 * tp_itemsize
= sizeof(PyTupleObject base) + 100 * 8
= 24 (header with ob_size) + 800
= 824 bytes (+ possible GC header of 24 = 848 bytes)
```

### Exercise 75
Explain why `sys.getsizeof(42)` returns 28 but `sys.getsizeof(2**100)` returns 36:
- 42: ob_refcnt(8) + ob_type(8) + ob_size(8) + 1 digit(4) = 28
- 2^100: needs ceil(101/30) = 4 digits. 8+8+8+4*4 = 40? Actually: 24 (PyVarObject header) + 4*4 = 40. Check with sys.getsizeof confirms.
- The difference: more digits for larger numbers = more bytes.
