# Part 10 — Memory Layout Examples: ASCII Diagrams

## 10.1 Reading Guide

All diagrams assume a 64-bit CPython (3.11+) production build:
- `Py_ssize_t` = 8 bytes
- Pointers = 8 bytes
- `digit` (for int) = 4 bytes (uint32_t, uses only 30 bits)
- Addresses are illustrative (not real)

Notation:
```
┌─────────────────────────────────────┐
│ field_name   (size)   value         │ ← description
└─────────────────────────────────────┘
```

---

## 10.2 int Object — Small Integer (42)

```python
x = 42
# sys.getsizeof(42) → 28 bytes
```

```
PyLongObject at 0x7F80_00A0_4A20 (small int cache):
┌─────────────────────────────────────────────────────────┐
│ Offset  Field          Size    Value                     │
├─────────────────────────────────────────────────────────┤
│ +0x00   ob_refcnt      8B      IMMORTAL (cached int)    │
│ +0x08   ob_type        8B      → PyLong_Type            │
│ +0x10   ob_size        8B      1 (one digit, positive)  │
│ +0x18   ob_digit[0]    4B      42                       │
│ +0x1C   (padding)      4B      (alignment to 8 bytes)   │
└─────────────────────────────────────────────────────────┘
Total: 32 bytes (28 data + 4 padding)

Note: ob_size sign encodes integer sign.
      int(-42) would have ob_size = -1, ob_digit[0] = 42.
      int(0) has ob_size = 0, no digits.
```

### Large Integer (2^100)

```python
x = 2**100
# sys.getsizeof(2**100) → 44 bytes  (depends on version)
```

```
PyLongObject at 0x7F80_00B1_2340:
┌─────────────────────────────────────────────────────────┐
│ +0x00   ob_refcnt      8B      1                        │
│ +0x08   ob_type        8B      → PyLong_Type            │
│ +0x10   ob_size        8B      4 (four 30-bit digits)   │
│ +0x18   ob_digit[0]    4B      (least significant)      │
│ +0x1C   ob_digit[1]    4B                               │
│ +0x20   ob_digit[2]    4B                               │
│ +0x24   ob_digit[3]    4B      (most significant)       │
└─────────────────────────────────────────────────────────┘
Total: 40 bytes

2^100 in base 2^30:
  = digit[3]×(2^30)^3 + digit[2]×(2^30)^2 + digit[1]×2^30 + digit[0]
```

---

## 10.3 bool Object (True)

```python
x = True
# sys.getsizeof(True) → 28 bytes
```

```
True is stored as a PyLongObject with value 1:
┌─────────────────────────────────────────────────────────┐
│ +0x00   ob_refcnt      8B      IMMORTAL                 │
│ +0x08   ob_type        8B      → PyBool_Type            │
│ +0x10   ob_size        8B      1                        │
│ +0x18   ob_digit[0]    4B      1                        │
│ +0x1C   (padding)      4B                               │
└─────────────────────────────────────────────────────────┘
Total: 32 bytes

Note: PyBool_Type is a subclass of PyLong_Type.
      True IS the integer 1 (True + True == 2).
      False has ob_size=0 (like int(0)).
```

---

## 10.4 float Object (3.14)

```python
x = 3.14
# sys.getsizeof(3.14) → 24 bytes
```

```
PyFloatObject at 0x7F80_00C2_5680:
┌─────────────────────────────────────────────────────────┐
│ +0x00   ob_refcnt      8B      1                        │
│ +0x08   ob_type        8B      → PyFloat_Type           │
│ +0x10   ob_fval        8B      3.14 (IEEE 754 double)   │
└─────────────────────────────────────────────────────────┘
Total: 24 bytes (no padding needed — all 8-byte aligned)

Note: NO ob_size field. Float is fixed-size (uses PyObject, not PyVarObject).
      Every float is exactly 24 bytes regardless of value.
```

---

## 10.5 None Object

```python
x = None
# sys.getsizeof(None) → 16 bytes
```

```
_Py_NoneStruct (singleton, in static data):
┌─────────────────────────────────────────────────────────┐
│ +0x00   ob_refcnt      8B      IMMORTAL                 │
│ +0x08   ob_type        8B      → PyNone_Type            │
└─────────────────────────────────────────────────────────┘
Total: 16 bytes — the absolute minimum Python object

No payload. No ob_size. Just the bare PyObject header.
This is the smallest possible Python object.
```

---

## 10.6 str Object — ASCII ("hello")

```python
x = "hello"
# sys.getsizeof("hello") → 54 bytes (compact ASCII)
```

CPython 3.12+ uses a compact representation for ASCII strings:

```
PyUnicodeObject (compact ASCII) at 0x7F80_00D4_7890:
┌─────────────────────────────────────────────────────────┐
│ +0x00   ob_refcnt      8B      1                        │
│ +0x08   ob_type        8B      → PyUnicode_Type         │
│ +0x10   length         8B      5                        │
│ +0x18   hash           8B      (cached or -1)           │
│ +0x20   state          4B      (kind=1/ASCII, compact)  │
│ +0x24   (padding)      4B                               │
│         ─── inline data starts here ───                  │
│ +0x28   data[0]        1B      'h' (0x68)               │
│ +0x29   data[1]        1B      'e' (0x65)               │
│ +0x2A   data[2]        1B      'l' (0x6C)               │
│ +0x2B   data[3]        1B      'l' (0x6C)               │
│ +0x2C   data[4]        1B      'o' (0x6F)               │
│ +0x2D   data[5]        1B      '\0' (null terminator)   │
│ +0x2E   (padding)      2B      (to align total)         │
└─────────────────────────────────────────────────────────┘
Total: ~54 bytes

Note: String data is stored INLINE after the header.
      Character width depends on content:
      - ASCII only: 1 byte/char
      - Latin-1:    1 byte/char
      - BMP:        2 bytes/char (UCS-2)
      - Full Unicode: 4 bytes/char (UCS-4)
```

---

## 10.7 tuple Object — (1, 2, 3)

```python
x = (1, 2, 3)
# sys.getsizeof((1, 2, 3)) → 64 bytes
```

```
PyTupleObject at 0x7F80_00E5_6700:
┌─────────────────────────────────────────────────────────┐
│ +0x00   ob_refcnt      8B      1                        │
│ +0x08   ob_type        8B      → PyTuple_Type           │
│ +0x10   ob_size        8B      3 (three elements)       │
│         ─── ob_item array (inline) ───                   │
│ +0x18   ob_item[0]     8B      → PyLongObject(1)        │
│ +0x20   ob_item[1]     8B      → PyLongObject(2)        │
│ +0x28   ob_item[2]     8B      → PyLongObject(3)        │
└─────────────────────────────────────────────────────────┘
Total: 48 bytes (for the tuple struct)
       + size of each element (int objects)

                    ┌─────────────┐
ob_item[0] ──────→ │ int(1) 28B  │ (in small int cache)
                    └─────────────┘
                    ┌─────────────┐
ob_item[1] ──────→ │ int(2) 28B  │ (in small int cache)
                    └─────────────┘
                    ┌─────────────┐
ob_item[2] ──────→ │ int(3) 28B  │ (in small int cache)
                    └─────────────┘

Note: ob_item stores POINTERS to objects, not the objects themselves.
      Tuple data is inline (directly after header, not via indirection).
```

---

## 10.8 list Object — [1, 2, 3]

```python
x = [1, 2, 3]
# sys.getsizeof([1, 2, 3]) → 88 bytes (includes over-allocation)
```

```
PyListObject at 0x7F80_00F6_8900:
┌─────────────────────────────────────────────────────────┐
│ +0x00   ob_refcnt      8B      1                        │
│ +0x08   ob_type        8B      → PyList_Type            │
│ +0x10   ob_size        8B      3 (current length)       │
│ +0x18   ob_item        8B      → 0x7F80_0100_0000       │ ← pointer!
│ +0x20   allocated      8B      3 (or more if over-alloc)│
└─────────────────────────────────────────────────────────┘
Total struct: 40 bytes

                          Separately allocated array:
ob_item ─────────────→  ┌─────────────────────────────┐ 0x7F80_0100_0000
                         │ slot[0]: → int(1)           │  8 bytes
                         │ slot[1]: → int(2)           │  8 bytes
                         │ slot[2]: → int(3)           │  8 bytes
                         │ (slot[3]: unused/NULL)      │  8 bytes (if over-allocated)
                         └─────────────────────────────┘
                         Array size: allocated × 8 bytes

Key difference from tuple:
- Tuple: ob_item[] is INLINE (part of the struct)
- List: ob_item is a POINTER to a separate allocation
  → Allows realloc for append/insert without moving the list object
```

---

## 10.9 dict Object — {"a": 1, "b": 2}

```python
x = {"a": 1, "b": 2}
# sys.getsizeof({"a": 1, "b": 2}) → 184 bytes (approx)
```

```
PyDictObject at 0x7F80_0110_AB00:
┌─────────────────────────────────────────────────────────┐
│ +0x00   ob_refcnt         8B    1                       │
│ +0x08   ob_type           8B    → PyDict_Type           │
│ +0x10   ma_used           8B    2 (number of items)     │
│ +0x18   ma_version_tag    8B    (version counter)       │
│ +0x20   ma_keys           8B    → PyDictKeysObject      │
│ +0x28   ma_values         8B    → values array (or NULL)│
└─────────────────────────────────────────────────────────┘
Total struct: 48 bytes

                    ┌─── PyDictKeysObject ───────────────────────┐
ma_keys ──────→    │ dk_refcnt    8B                             │
                    │ dk_log2_size 1B  (log2 of hash table size) │
                    │ dk_kind      1B  (split/combined)          │
                    │ dk_usable    8B  (slots available)         │
                    │ dk_nentries  8B  (entries used)            │
                    │ ─── hash indices table ───                  │
                    │ indices[0..7]: int8/16/32                   │
                    │ ─── entries array ───                       │
                    │ entry[0]: hash=..., key→"a", value→int(1)  │
                    │ entry[1]: hash=..., key→"b", value→int(2)  │
                    └────────────────────────────────────────────┘

Note: Dict uses PyObject_HEAD (not VAR_HEAD).
      All variable data is in separate allocations.
      The compact ordered dict (3.7+) stores entries in insertion order.
```

---

## 10.10 set Object — {1, 2, 3}

```python
x = {1, 2, 3}
# sys.getsizeof({1, 2, 3}) → 216 bytes (approx)
```

```
PySetObject at 0x7F80_0120_CD00:
┌─────────────────────────────────────────────────────────┐
│ +0x00   ob_refcnt      8B      1                        │
│ +0x08   ob_type        8B      → PySet_Type             │
│ +0x10   fill           8B      3 (active + dummy slots) │
│ +0x18   used           8B      3 (active entries)       │
│ +0x20   mask           8B      7 (table_size - 1)       │
│ +0x28   table          8B      → smalltable (below)     │
│ +0x30   hash           8B      -1 (not cached/unhashable)│
│ +0x38   finger         8B      (iteration state)        │
│ +0x40   smalltable[0]  16B     (key_ptr + hash)         │
│ +0x50   smalltable[1]  16B                              │
│ +0x60   smalltable[2]  16B                              │
│ +0x70   smalltable[3]  16B                              │
│ +0x80   smalltable[4]  16B                              │
│ +0x90   smalltable[5]  16B                              │
│ +0xA0   smalltable[6]  16B                              │
│ +0xB0   smalltable[7]  16B                              │
│ +0xC0   weakreflist    8B      NULL                     │
└─────────────────────────────────────────────────────────┘
Total: ~216 bytes

Note: Sets embed a "small table" (8 entries) directly in the struct.
      When the set grows beyond 8 entries, `table` points to a 
      separately-allocated larger table.
      Each entry is: { PyObject *key; Py_hash_t hash; } = 16 bytes.
```

---

## 10.11 function Object

```python
def greet(name):
    return f"Hello, {name}!"
# sys.getsizeof(greet) → ~136 bytes
```

```
PyFunctionObject at 0x7F80_0130_EF00:
┌─────────────────────────────────────────────────────────┐
│ +0x00   ob_refcnt          8B    1                      │
│ +0x08   ob_type            8B    → PyFunction_Type      │
│ +0x10   func_globals       8B    → module __dict__      │
│ +0x18   func_builtins      8B    → builtins dict        │
│ +0x20   func_name          8B    → "greet"              │
│ +0x28   func_qualname      8B    → "greet"              │
│ +0x30   func_code          8B    → PyCodeObject         │
│ +0x38   func_defaults      8B    → NULL (no defaults)   │
│ +0x40   func_kwdefaults    8B    → NULL                 │
│ +0x48   func_closure       8B    → NULL (no closure)    │
│ +0x50   func_doc           8B    → None                 │
│ +0x58   func_dict          8B    → NULL (__dict__)      │
│ +0x60   func_module        8B    → "__main__"           │
│ +0x68   func_annotations   8B    → NULL                 │
│ +0x70   func_typeparams    8B    → NULL                 │
│ +0x78   vectorcall         8B    → (function pointer)   │
│ +0x80   func_version       4B    (version for guards)   │
│ +0x84   (padding)          4B                           │
└─────────────────────────────────────────────────────────┘
Total: ~136 bytes (many pointer fields to shared objects)

Note: Function objects are fixed-size (PyObject_HEAD, not VAR_HEAD).
      They hold POINTERS to the code object, defaults, closure cells, etc.
      The actual bytecode lives in the separate PyCodeObject.
```

---

## 10.12 class Instance (User-Defined)

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

p = Point(3.0, 4.0)
# sys.getsizeof(p) → 48 bytes (just the instance, not the dict)
```

```
Instance of Point at 0x7F80_0140_1200:
┌─────────────────────────────────────────────────────────┐
│ +0x00   ob_refcnt      8B      1                        │
│ +0x08   ob_type        8B      → Point (heap type obj)  │
│ +0x10   __dict__       8B      → PyDictObject           │
│ +0x18   __weakref__    8B      → NULL                   │
└─────────────────────────────────────────────────────────┘
Total instance struct: 32 bytes (+ GC header = 48 reported)

                    ┌─── Instance __dict__ ─────────────────┐
__dict__ ──────→   │ {"x": 3.0, "y": 4.0}                  │
                    │ (compact dict, ~100+ bytes)            │
                    └───────────────────────────────────────┘

With __slots__:
class Point:
    __slots__ = ('x', 'y')
    
┌─────────────────────────────────────────────────────────┐
│ +0x00   ob_refcnt      8B      1                        │
│ +0x08   ob_type        8B      → Point type             │
│ +0x10   x              8B      → float(3.0)             │
│ +0x18   y              8B      → float(4.0)             │
└─────────────────────────────────────────────────────────┘
Total: 32 bytes (no __dict__ overhead!)
```

---

## 10.13 None, True, False — The Singletons

```
Static memory region (never freed):

_Py_NoneStruct:                    _Py_TrueStruct:
┌──────────────────────┐          ┌──────────────────────────┐
│ ob_refcnt: IMMORTAL  │          │ ob_refcnt: IMMORTAL      │
│ ob_type: → NoneType  │          │ ob_type: → PyBool_Type   │
└──────────────────────┘          │ ob_size: 1               │
16 bytes                           │ ob_digit[0]: 1           │
                                   └──────────────────────────┘
_Py_FalseStruct:                   28 bytes
┌──────────────────────────┐
│ ob_refcnt: IMMORTAL      │
│ ob_type: → PyBool_Type   │
│ ob_size: 0               │
│ (no digits needed)       │
└──────────────────────────┘
24 bytes
```

---

## 10.14 Complete Memory Map: `x = [1, "hi", None]`

```
┌─────────────────────────────────────────────────────────────────────┐
│ FRAME LOCAL VARIABLES                                                │
│   x → 0x7F80_AAA0                                                   │
└─────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PyListObject at 0x7F80_AAA0                                          │
│ ┌───────────────────────────────────────┐                           │
│ │ ob_refcnt: 1                          │                           │
│ │ ob_type: → PyList_Type                │                           │
│ │ ob_size: 3                            │                           │
│ │ ob_item: → 0x7F80_BBB0               │──┐                        │
│ │ allocated: 4                          │  │                        │
│ └───────────────────────────────────────┘  │                        │
└────────────────────────────────────────────┼────────────────────────┘
                                             │
         ┌───────────────────────────────────┘
         ▼
┌────────────────────────────────────┐
│ Item array at 0x7F80_BBB0          │
│ [0]: → 0x7F80_CC00 (int 1)        │──→ PyLongObject(1) [cached]
│ [1]: → 0x7F80_DD00 (str "hi")     │──→ PyUnicodeObject("hi")
│ [2]: → 0x5600_EE00 (None)         │──→ _Py_NoneStruct [singleton]
│ [3]: NULL (unused capacity)        │
└────────────────────────────────────┘
```

---

## 10.15 Source References

| File | What to look at |
|------|----------------|
| `Include/cpython/longintrepr.h` | PyLongObject memory layout |
| `Include/cpython/floatobject.h` | PyFloatObject (24 bytes) |
| `Include/cpython/tupleobject.h` | PyTupleObject (inline items) |
| `Include/cpython/listobject.h` | PyListObject (pointer to items) |
| `Include/cpython/dictobject.h` | PyDictObject + PyDictKeysObject |
| `Include/cpython/setobject.h` | PySetObject (inline smalltable) |
| `Include/cpython/funcobject.h` | PyFunctionObject fields |
| `Include/cpython/unicodeobject.h` | String representations |

---

## 10.16 Interview Questions — Part 10

**Q1**: Draw the memory layout of `x = 3.14` and explain why all floats are the same size.
**A**: PyFloatObject = 24 bytes: [ob_refcnt(8) | ob_type(8) | ob_fval(8)]. All floats store one IEEE 754 double (8 bytes) regardless of value. The type uses PyObject_HEAD (no ob_size) because size never varies.

**Q2**: What's the key structural difference between a tuple and a list in memory?
**A**: Tuple stores its item pointers INLINE (directly after the header) — they're part of the struct allocation. List stores a POINTER to a separately-allocated array of item pointers. This indirection allows lists to grow/shrink without moving the list object.

**Q3**: Why does `sys.getsizeof(0)` return less than `sys.getsizeof(1)`?
**A**: `int(0)` has `ob_size = 0` (zero digits needed), while `int(1)` has `ob_size = 1` (one digit = 4 bytes). The zero integer is just the header without any digit storage.

**Q4**: How does a set store its entries, and what is the "smalltable" optimization?
**A**: PySetObject embeds an 8-entry hash table directly in the struct (smalltable). For small sets (≤5 items with load factor), no separate allocation is needed. When the set grows beyond this, a separately-allocated larger table is used.

**Q5**: What's the difference between a class instance with `__dict__` vs `__slots__`?
**A**: With `__dict__`: instance has a pointer to a separately-allocated dict (~100+ bytes overhead). With `__slots__`: attributes are stored as fixed slots directly in the instance struct (8 bytes each), eliminating the dict entirely. Slots save memory but prevent dynamic attribute addition.

**Q6**: Why is None only 16 bytes while True is 28 bytes?
**A**: None is the bare minimum — just PyObject header (ob_refcnt + ob_type). True is a PyLongObject (subclass of int) with ob_size=1 and one digit storing the value 1. Booleans carry integer machinery.

**Q7**: In `x = [1, "hi", None]`, how many separately-allocated memory blocks exist?
**A**: At least 3: (1) the PyListObject struct, (2) the item pointer array, (3) the PyUnicodeObject for "hi". The int(1) and None are pre-existing cached/singleton objects, not newly allocated.
