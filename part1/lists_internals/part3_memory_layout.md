# Part 3 — Memory Layout

## 3.1 The Three-Level Indirection

When you write `a = [10, 20, 30]`, there are **three distinct memory regions** involved:

```
Level 1: The name 'a' (in a namespace/frame)
Level 2: The PyListObject (on the heap)
Level 3: The ob_item array (separate heap allocation)
Level 4: The actual objects (individual heap allocations)
```

Let's trace every pointer:

```
    FRAME/NAMESPACE                    HEAP
┌─────────────────┐
│ locals dict     │
│                 │
│ 'a' ──────────────────────────────────────┐
│                 │                          │
└─────────────────┘                          ▼
                                ┌──────────────────────────┐
                                │     PyListObject         │
                                │                          │
                                │  ob_refcnt:  1           │
                                │  ob_type:    ─→ PyList_Type
                                │  ob_size:    3           │
                                │  ob_item:    ────┐       │
                                │  allocated:  4   │       │
                                └──────────────────┼───────┘
                                                   │
                                                   ▼
                                ┌────────┬────────┬────────┬────────┐
                                │ ptr[0] │ ptr[1] │ ptr[2] │ (free) │
                                └───┬────┴───┬────┴───┬────┴────────┘
                                    │        │        │
                        ┌───────────┘        │        └──────────┐
                        │                    │                    │
                        ▼                    ▼                    ▼
              ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
              │ PyLongObject │    │ PyLongObject │    │ PyLongObject │
              │ value: 10    │    │ value: 20    │    │ value: 30    │
              │ refcnt: N    │    │ refcnt: N    │    │ refcnt: N    │
              └──────────────┘    └──────────────┘    └──────────────┘
```

---

## 3.2 Why Integers Are NOT Stored Inside the List

This is a fundamental misconception to address. `[10, 20, 30]` does NOT mean:

```
WRONG mental model:
┌────┬────┬────┐
│ 10 │ 20 │ 30 │   ← values stored directly
└────┴────┴────┘
```

The CORRECT model is that the list stores **pointers to objects**:

```
CORRECT mental model:
┌─────┬─────┬─────┐
│  *  │  *  │  *  │   ← pointers (8 bytes each)
└──┬──┴──┬──┴──┬──┘
   │     │     │
   ▼     ▼     ▼
  10    20    30       ← full PyLongObject on heap (28 bytes each)
```

### Why This Design?

**Reason 1: Objects have variable sizes**

```python
a = [42, "hello world", [1,2,3], 3.14159265358979]
```

- `42` (PyLongObject): 28 bytes
- `"hello world"` (PyUnicodeObject): ~60 bytes  
- `[1,2,3]` (PyListObject): 88+ bytes
- `3.14159265358979` (PyFloatObject): 24 bytes

You CANNOT store these inline in contiguous memory and still support O(1) indexing. With variable-size elements, computing the address of element `i` requires summing sizes of all previous elements — O(n).

With uniform 8-byte pointers: `address_of_item_i = ob_item + i * 8` — O(1).

**Reason 2: Reference sharing**

```python
x = 42
a = [x, x, x]  # Three pointers to the SAME object
```

```
ob_item → ┌─────┬─────┬─────┐
           │  *  │  *  │  *  │
           └──┬──┴──┬──┴──┬──┘
              │     │     │
              └─────┼─────┘
                    │
                    ▼
              ┌──────────┐
              │ 42       │  ← ONE object, refcnt = 4 (x + 3 list slots)
              │ refcnt=4 │
              └──────────┘
```

If values were stored inline, each slot would be a copy. This would break Python's identity semantics:

```python
a[0] is a[1]  # Must be True (same object)
```

**Reason 3: Mutability and lifetime independence**

```python
a = [obj]
b = a[0]    # b references the same object
del a       # list dies, but obj lives on (b still references it)
```

Objects exist independently of containers. Pointers + reference counting manage this naturally.

---

## 3.3 Detailed Memory Map for `a = [10, 20, 30]`

Let's assign concrete addresses (simplified, 64-bit system):

```
════════════════════════════════════════════════════════════════════
STACK FRAME for the function containing 'a = [10, 20, 30]'
════════════════════════════════════════════════════════════════════
Variable    Type          Points To
────────────────────────────────────────────────────────────────────
a           PyObject*     0x00007F80_A000_1000  (the PyListObject)
════════════════════════════════════════════════════════════════════


════════════════════════════════════════════════════════════════════
HEAP: PyListObject at 0x00007F80_A000_1000
════════════════════════════════════════════════════════════════════
Offset  Address              Field        Value
──────────────────────────────────────────────────────────────────
+0x00   0x7F80_A000_1000     ob_refcnt    1
+0x08   0x7F80_A000_1008     ob_type      0x0000_0000_009046A0 → PyList_Type
+0x10   0x7F80_A000_1010     ob_size      3
+0x18   0x7F80_A000_1018     ob_item      0x7F80_B000_2000 → (pointer array)
+0x20   0x7F80_A000_1020     allocated    4
════════════════════════════════════════════════════════════════════


════════════════════════════════════════════════════════════════════
HEAP: Pointer Array at 0x00007F80_B000_2000  (ob_item target)
════════════════════════════════════════════════════════════════════
Offset  Address              Slot        Value (pointer to object)
──────────────────────────────────────────────────────────────────
+0x00   0x7F80_B000_2000     [0]         0x0000_0000_00904A20 → int(10)
+0x08   0x7F80_B000_2008     [1]         0x0000_0000_00904B60 → int(20)
+0x10   0x7F80_B000_2010     [2]         0x0000_0000_00904CA0 → int(30)
+0x18   0x7F80_B000_2018     [3]         (uninitialized — free slot)
════════════════════════════════════════════════════════════════════
Total array size: 4 slots × 8 bytes = 32 bytes


════════════════════════════════════════════════════════════════════
HEAP: PyLongObject for integer 10 at 0x00904A20
(Pre-allocated in small integer cache)
════════════════════════════════════════════════════════════════════
Offset  Field          Value
──────────────────────────────────────────────────────────────────
+0x00   ob_refcnt      137  (many things reference cached int 10)
+0x08   ob_type        → PyLong_Type
+0x10   ob_size        1    (one digit needed)
+0x18   ob_digit[0]    10   (the actual value)
════════════════════════════════════════════════════════════════════
Size: 28 bytes (for single-digit integers)
```

---

## 3.4 Heterogeneous List Layout

```python
mixed = [42, "hi", 3.14, None]
```

```
PyListObject
┌─────────────────────┐
│ ob_size = 4         │
│ ob_item → ──────────┼──────┐
│ allocated = 4       │      │
└─────────────────────┘      │
                              ▼
                    ┌──────┬──────┬──────┬──────┐
                    │ ptr0 │ ptr1 │ ptr2 │ ptr3 │
                    └──┬───┴──┬───┴──┬───┴──┬───┘
                       │      │      │      │
           ┌───────────┘      │      │      └────────────┐
           │                  │      │                    │
           ▼                  ▼      ▼                    ▼
    ┌────────────┐    ┌────────────────┐  ┌───────────┐  ┌───────────┐
    │PyLongObject│    │PyUnicodeObject │  │PyFloatObj │  │ Py_None   │
    │ value: 42  │    │ value: "hi"    │  │ val: 3.14 │  │(singleton)│
    │ size: 28B  │    │ size: ~54B     │  │ size: 24B │  │ size: 16B │
    └────────────┘    └────────────────┘  └───────────┘  └───────────┘
```

Key observations:
- All four pointers in the array are the same size (8 bytes)
- The objects they point to are **completely different sizes**
- The list doesn't know or care about the types of contained objects
- `None` is a singleton — every `None` in every list points to the same object

---

## 3.5 Nested Lists

```python
outer = [[1, 2], [3, 4]]
```

This creates THREE list objects and FOUR integer objects:

```
'outer' variable
     │
     ▼
┌──────────────────────┐
│ PyListObject (outer) │
│ ob_size = 2          │
│ ob_item → ───────────┼──┐
│ allocated = 2        │  │
└──────────────────────┘  │
                           ▼
                ┌────────┬────────┐
                │ ptr[0] │ ptr[1] │
                └───┬────┴───┬────┘
                    │        │
         ┌──────────┘        └──────────┐
         │                              │
         ▼                              ▼
┌──────────────────┐          ┌──────────────────┐
│ PyListObject     │          │ PyListObject     │
│ [1, 2]           │          │ [3, 4]           │
│ ob_size = 2      │          │ ob_size = 2      │
│ ob_item → ──┐    │          │ ob_item → ──┐    │
└──────────────┼───┘          └──────────────┼───┘
               │                              │
               ▼                              ▼
         ┌─────┬─────┐                 ┌─────┬─────┐
         │ *1  │ *2  │                 │ *3  │ *4  │
         └──┬──┴──┬──┘                 └──┬──┴──┬──┘
            │     │                       │     │
            ▼     ▼                       ▼     ▼
          int(1) int(2)                 int(3) int(4)
```

**Memory cost:**
- outer list: 56 + 2×8 = 72 bytes
- inner list [1,2]: 56 + 2×8 = 72 bytes
- inner list [3,4]: 56 + 2×8 = 72 bytes
- 4 integers (cached): 0 extra bytes (already in small int cache)
- **Total: ~216 bytes** for four integers!

Compare: C's `int arr[2][2]` = 16 bytes.

---

## 3.6 Shared References in Lists

```python
x = [1, 2, 3]
a = [x, x, x]  # Three references to the SAME list
```

```
'a' ──→ PyListObject
         ob_item → ┌─────┬─────┬─────┐
                    │ ptr │ ptr │ ptr │
                    └──┬──┴──┬──┴──┬──┘
                       │     │     │
                       └─────┼─────┘  (ALL point to same object!)
                             │
                             ▼
                    ┌──────────────────┐
                    │ PyListObject (x) │
                    │ ob_refcnt = 4    │  ← 'x' + a[0] + a[1] + a[2]
                    │ [1, 2, 3]        │
                    └──────────────────┘
```

This means:
```python
a[0] is a[1] is a[2]  # True — same object
a[0].append(4)
print(a)  # [[1,2,3,4], [1,2,3,4], [1,2,3,4]] — all "changed"
```

The list `a` doesn't contain three copies of `[1,2,3]`. It contains three pointers to ONE list object. This is the direct consequence of storing pointers rather than values.

---

## 3.7 The `*` Operator Trap

```python
a = [[]] * 3
```

```
'a' ──→ PyListObject
         ob_item → ┌─────┬─────┬─────┐
                    │ ptr │ ptr │ ptr │
                    └──┬──┴──┬──┴──┬──┘
                       │     │     │
                       └─────┼─────┘
                             │
                             ▼
                    ┌──────────────┐
                    │ PyListObject │  ONE empty list, refcnt = 4
                    │ []           │
                    └──────────────┘

a[0].append(1)
print(a)  # [[1], [1], [1]]  — "surprise!"
```

vs the correct approach:

```python
a = [[] for _ in range(3)]
```

```
'a' ──→ PyListObject
         ob_item → ┌─────┬─────┬─────┐
                    │ ptr │ ptr │ ptr │
                    └──┬──┴──┬──┴──┬──┘
                       │     │     │
           ┌───────────┘     │     └───────────┐
           ▼                 ▼                  ▼
    ┌────────────┐   ┌────────────┐   ┌────────────┐
    │ [] refcnt=1│   │ [] refcnt=1│   │ [] refcnt=1│  THREE objects
    └────────────┘   └────────────┘   └────────────┘

a[0].append(1)
print(a)  # [[1], [], []]  — correct!
```

---

## 3.8 Memory Layout After Mutations

### After `a.append(40)`:

Starting: `a = [10, 20, 30]` (ob_size=3, allocated=4)

```
BEFORE append(40):
ob_item → [ptr→10, ptr→20, ptr→30, FREE]
           ob_size=3, allocated=4

AFTER append(40):
ob_item → [ptr→10, ptr→20, ptr→30, ptr→40]
           ob_size=4, allocated=4

Operations performed:
1. Check: ob_size (3) < allocated (4)? YES → no realloc needed
2. ob_item[3] = pointer_to_40
3. Py_INCREF(40_object)
4. ob_size = 4
```

### After `a.append(50)` (triggers reallocation):

```
BEFORE append(50):
ob_item → [ptr→10, ptr→20, ptr→30, ptr→40]  (FULL: ob_size==allocated==4)

AFTER append(50):
ob_item → [ptr→10, ptr→20, ptr→30, ptr→40, ptr→50, FREE, FREE, FREE]
           ob_size=5, allocated=8

Operations performed:
1. Check: ob_size (4) < allocated (4)? NO → need realloc
2. Calculate new_allocated = 4 + (4 >> 3) + 6 = 4 + 0 + 6 = 10? 
   (actual formula depends on version, typical growth to ~8)
3. PyMem_Realloc(ob_item, new_allocated * sizeof(PyObject*))
4. Update ob_item pointer (may have new address)
5. ob_item[4] = pointer_to_50
6. Py_INCREF(50_object)
7. ob_size = 5
8. allocated = 8
```

---

## 3.9 Verifying Memory Layout in Python

```python
import sys
import ctypes

a = [10, 20, 30]

# Size of list object (includes pointer array, excludes contained objects)
print(sys.getsizeof(a))  # 88 bytes (56 base + 4 slots * 8)

# Actual addresses
print(f"List object at:   {id(a):#x}")
print(f"a[0] (int 10) at: {id(a[0]):#x}")
print(f"a[1] (int 20) at: {id(a[1]):#x}")
print(f"a[2] (int 30) at: {id(a[2]):#x}")

# Prove small ints are cached:
b = [10, 20, 30]
print(a[0] is b[0])  # True — same cached object
print(a[1] is b[1])  # True
print(a[2] is b[2])  # True

# Prove identity:
print(id(a) == id(a))  # Always True
a.append(40)
print(id(a) == id(a))  # Still True — list didn't move
```

---

## 3.10 Memory Diagram — List of Strings

```python
words = ["hello", "world"]
```

```
PyListObject (words)
┌─────────────────────┐
│ ob_refcnt = 1       │
│ ob_type → list      │
│ ob_size = 2         │
│ ob_item → ────┐     │
│ allocated = 2  │    │
└────────────────┼────┘
                 │
                 ▼
       ┌────────┬────────┐
       │ ptr[0] │ ptr[1] │
       └───┬────┴───┬────┘
           │        │
           ▼        ▼
┌─────────────────┐  ┌─────────────────┐
│ PyUnicodeObject │  │ PyUnicodeObject │
│                 │  │                 │
│ ob_refcnt: 1    │  │ ob_refcnt: 1    │
│ kind: PyUnicode │  │ kind: PyUnicode │
│   _1BYTE_KIND  │  │   _1BYTE_KIND  │
│ length: 5      │  │ length: 5      │
│ hash: (cached) │  │ hash: (cached) │
│ data → "hello" │  │ data → "world" │
│ ┌─┬─┬─┬─┬─┬─┐ │  │ ┌─┬─┬─┬─┬─┬─┐ │
│ │h│e│l│l│o│\0│ │  │ │w│o│r│l│d│\0│ │
│ └─┴─┴─┴─┴─┴─┘ │  │ └─┴─┴─┴─┴─┴─┘ │
└─────────────────┘  └─────────────────┘
```

---

## 3.11 Interview Questions — Part 3

**Q1**: How many pointer dereferences are needed to access `a[2]` where `a = [10, 20, 30]`?
**A**: Two. First dereference `a` to get the PyListObject, then dereference `ob_item[2]` to get the PyLongObject. (The initial name lookup to get `a` is additional.)

**Q2**: If `a = [x, x, x]`, how many objects exist?
**A**: Two: one PyListObject and one object `x`. The list stores three pointers all pointing to the same `x` object.

**Q3**: Why does `[[]] * 3` create aliasing but `[[] for _ in range(3)]` doesn't?
**A**: `*` replicates the pointer — all three slots point to the one `[]` object created before multiplication. The comprehension calls `[]` three times, creating three independent objects.

**Q4**: Does `sys.getsizeof([1,2,3])` include the memory for integers 1, 2, 3?
**A**: No. It reports only the list object + pointer array. The integers' memory is not counted.

**Q5**: How much total memory does `a = [10, 20, 30]` really use?
**A**: ~88 bytes (list + 4-slot pointer array). The integers 10, 20, 30 are from the small int cache so they're "free" (already allocated at interpreter startup). For non-cached integers (>256), add 28 bytes each.
