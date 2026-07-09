# Part 13 — Memory Alignment, Padding, and Cache Lines

## 13.1 Why Alignment Matters

CPUs don't read memory one byte at a time. They read in **aligned chunks** — typically matching the data width:

```
64-bit CPU reads memory in 8-byte aligned blocks:
Address:   0x00  0x08  0x10  0x18  0x20  0x28  ...
           ├──8──┤──8──┤──8──┤──8──┤──8──┤──8──┤

Reading a 64-bit value at address 0x08: ONE bus transaction
Reading a 64-bit value at address 0x05: MISALIGNED
  → Two bus transactions needed (straddles 0x00-0x07 and 0x08-0x0F)
  → Or hardware exception on strict-alignment architectures (ARM, SPARC)
```

Alignment requirements on 64-bit x86:

| Type | Size | Must be at address divisible by |
|------|------|---------------------------------|
| `char` | 1 byte | 1 (any address) |
| `short` | 2 bytes | 2 |
| `int` / `uint32_t` | 4 bytes | 4 |
| `long` / `int64_t` | 8 bytes | 8 |
| `pointer` | 8 bytes | 8 |
| `double` | 8 bytes | 8 |

---

## 13.2 Alignment in PyObject

```c
typedef struct _object {
    Py_ssize_t ob_refcnt;    // 8 bytes, requires 8-byte alignment
    PyTypeObject *ob_type;   // 8 bytes (pointer), requires 8-byte alignment
} PyObject;
```

Memory allocators (`malloc`, `pymalloc`) guarantee at least 8-byte (often 16-byte) aligned addresses. So:

```
Allocator returns address 0x7F80_0000_1000 (divisible by 16):

+0x00: ob_refcnt (Py_ssize_t)  → 0x1000 % 8 == 0 ✓
+0x08: ob_type   (pointer)     → 0x1008 % 8 == 0 ✓
+0x10: [data starts here]      → 0x1010 % 8 == 0 ✓ (after 16 bytes)

Perfect alignment with no padding needed!
```

---

## 13.3 Padding in Object Structs

### No Padding Needed (Common Case)

When all fields are 8-byte aligned:
```c
typedef struct {
    PyObject ob_base;       // 16 bytes (8 + 8)
    double ob_fval;         // 8 bytes at offset 16 → aligned ✓
} PyFloatObject;
// Total: 24 bytes, no padding
```

### Padding Required

When smaller fields precede larger ones:
```c
// HYPOTHETICAL example showing padding:
typedef struct {
    PyObject ob_base;       // 16 bytes
    int flags;              // 4 bytes at offset 16
    // *** 4 bytes PADDING *** to align next field
    double value;           // 8 bytes at offset 24 (needs 8-byte alignment)
} BadlyOrderedObject;
// Total: 32 bytes (4 bytes wasted)
```

```
Memory layout:
Offset  Size  Field
+0x00   8B    ob_refcnt
+0x08   8B    ob_type
+0x10   4B    flags
+0x14   4B    ████ PADDING ████    ← wasted!
+0x18   8B    value
─────────────────────────────────
Total: 32 bytes (28 useful + 4 pad)
```

### Fixing It: Reorder Fields

```c
typedef struct {
    PyObject ob_base;       // 16 bytes
    double value;           // 8 bytes at offset 16 → aligned ✓
    int flags;              // 4 bytes at offset 24 → aligned ✓
    // *** 4 bytes TAIL PADDING *** (struct size must be multiple of max align)
} BetterOrderedObject;
// Total: 32 bytes (still 4 padding, but at the end — sometimes unavoidable)
```

CPython developers carefully order fields to minimize internal padding.

---

## 13.4 Struct Size Rules

The C standard requires:
1. Each field is aligned to its natural alignment
2. The total struct size is a multiple of the largest field's alignment

```c
// Example: struct with mixed sizes
typedef struct {
    char a;       // 1 byte at +0
    // 7 bytes padding
    double b;     // 8 bytes at +8
    char c;       // 1 byte at +16
    // 7 bytes padding
} Mixed;
// sizeof(Mixed) = 24 (needs to be multiple of 8 for array alignment)

// Better ordering:
typedef struct {
    double b;     // 8 bytes at +0
    char a;       // 1 byte at +8
    char c;       // 1 byte at +9
    // 6 bytes tail padding
} BetterMixed;
// sizeof(BetterMixed) = 16 (saved 8 bytes!)
```

---

## 13.5 32-bit vs 64-bit Differences

### PyObject Header

| Field | 32-bit | 64-bit |
|-------|--------|--------|
| `ob_refcnt` (Py_ssize_t) | 4 bytes | 8 bytes |
| `ob_type` (pointer) | 4 bytes | 8 bytes |
| **Total PyObject** | **8 bytes** | **16 bytes** |
| `ob_size` (PyVarObject extra) | 4 bytes | 8 bytes |
| **Total PyVarObject** | **12 bytes** | **24 bytes** |

### Impact on Object Sizes

```
Object sizes on 32-bit vs 64-bit:

                32-bit      64-bit      Difference
None:           8 bytes     16 bytes    2× header
float:          16 bytes    24 bytes    1.5×
int(42):        14 bytes    28 bytes    2×
empty tuple:    12 bytes    24 bytes    2×
3-element tuple:24 bytes    48 bytes    2×
empty list:     20 bytes    40 bytes    2×
```

32-bit systems use roughly half the memory for object headers — one reason why 32-bit Python can handle more small objects in limited memory.

---

## 13.6 Cache Lines

Modern CPUs have hierarchical caches:
- **L1 cache**: ~32-64 KB, ~4 cycles latency
- **L2 cache**: ~256 KB - 1 MB, ~10 cycles
- **L3 cache**: ~4-32 MB, ~40 cycles
- **RAM**: ~100-300 cycles

Data is loaded in **cache lines** — typically 64 bytes:

```
Cache line (64 bytes):
┌────────────────────────────────────────────────────────────────────┐
│  Byte 0  │  Byte 1  │  ...  │  Byte 62  │  Byte 63              │
└────────────────────────────────────────────────────────────────────┘

Accessing ANY byte in this line loads the ENTIRE 64 bytes into cache.
```

### Cache Line Implications for Python Objects

A small Python object (e.g., float = 24 bytes) fits within one cache line:
```
Cache line at 0x...000:
┌──────────────────────────────────────────────────────┐
│ float object (24B)  │  another float (24B)  │ unused │
└──────────────────────────────────────────────────────┘
```

A larger object (e.g., dict = ~64 bytes) may span two cache lines:
```
Cache line 1:  ┌─ dict header + first fields ─────────────────────┐
               └──────────────────────────────────────────────────┘
Cache line 2:  ┌─ remaining dict fields ──────────────────────────┐
               └──────────────────────────────────────────────────┘
```

---

## 13.7 Cache Behavior with Reference Counting

Every `Py_INCREF/Py_DECREF` writes to `ob_refcnt` at offset 0 of the object. This means:

```
Py_INCREF(obj):
  1. Load cache line containing obj into L1 (if not already there)
  2. Modify ob_refcnt (write to cache line)
  3. Cache line marked as "dirty" (needs write-back)
```

For objects referenced by many threads (in free-threaded builds):
```
Thread 1: Py_INCREF(None) → modifies cache line X
Thread 2: Py_INCREF(None) → modifies cache line X → CACHE LINE BOUNCING!

Cache line X bounces between CPU cores (MESI protocol):
  Core 1: Modified → Invalid → Core 2: Modified → Invalid → ...
  
This is called "false sharing" or "cache contention."
Solution: Immortal objects (Python 3.12+) — skip refcount modification.
```

---

## 13.8 Allocator Alignment Guarantees

### Standard malloc

```c
// POSIX guarantees: malloc returns pointer aligned to max_align_t
// On 64-bit Linux: 16-byte alignment
// On 64-bit macOS: 16-byte alignment
// On Windows: 16-byte alignment (for MSVC)
```

### CPython's PyMalloc

```c
// CPython's small object allocator (obmalloc.c):
// Returns 8-byte aligned pointers for small allocations
// Pool alignment: 4096 bytes (page-aligned)
// Block alignment: 8 bytes (ALIGNMENT constant)

#define ALIGNMENT 8
#define ALIGNMENT_MASK (ALIGNMENT - 1)

// All objects from pymalloc are 8-byte aligned minimum
```

### GC-tracked objects

```c
// GC header (16 bytes) + object must maintain alignment:
// Allocator provides: 8-byte or 16-byte aligned pointer
// GC header is at that pointer
// Object (after GC header) is at pointer + 16 → still 8-byte aligned ✓
```

---

## 13.9 Impact on CPython Internals

### PyLongObject (int) Digit Array

```c
typedef uint32_t digit;  // 4 bytes per digit

typedef struct {
    PyObject ob_base;     // 16 bytes
    Py_ssize_t ob_size;   // 8 bytes
    digit ob_digit[1];    // 4 bytes per digit
} PyLongObject;
```

```
int(42) layout:
+0x00: ob_refcnt    8B
+0x08: ob_type      8B
+0x10: ob_size      8B
+0x18: ob_digit[0]  4B (value = 42)
+0x1C: (padding)    4B (to reach 8-byte multiple for next allocation)
─────────────────────────
Total: 32 bytes (28 useful)

int(2^60) layout:
+0x00: ob_refcnt    8B
+0x08: ob_type      8B
+0x10: ob_size      8B
+0x18: ob_digit[0]  4B
+0x1C: ob_digit[1]  4B
+0x20: ob_digit[2]  4B
+0x24: (padding)    4B
─────────────────────────
Total: 40 bytes (36 useful)
```

### PyTupleObject (pointer array)

```c
// Pointers are 8-byte aligned — no padding between them:
+0x18: ob_item[0]  8B → element 0
+0x20: ob_item[1]  8B → element 1
+0x28: ob_item[2]  8B → element 2
// No padding needed — all 8-byte values naturally aligned
```

---

## 13.10 Platform-Specific Alignment

### x86-64 (Intel/AMD)

```
- Misaligned access WORKS but is SLOWER (spans two cache lines)
- SSE/AVX instructions may REQUIRE 16/32-byte alignment
- Default struct alignment: 8 bytes
- Cache line: 64 bytes
```

### ARM (Apple Silicon, mobile)

```
- Stricter alignment requirements
- Some ARM CPUs fault on misaligned access
- Others handle it in hardware (with penalty)
- Cache line: typically 64 bytes (Apple M-series: 128 bytes for some levels)
```

### Implications

CPython doesn't use SIMD instructions for object manipulation, so the standard 8-byte alignment from malloc/pymalloc is sufficient. The key concern is cache efficiency, not hardware faults.

---

## 13.11 Checking Alignment in Practice

```python
import ctypes
import sys

x = 42
addr = id(x)
print(f"Address: {addr:#x}")
print(f"Aligned to 8 bytes: {addr % 8 == 0}")   # Always True
print(f"Aligned to 16 bytes: {addr % 16 == 0}")  # Usually True

# Check multiple objects:
objects = [1.0, "hello", [], {}, (), None, True]
for obj in objects:
    addr = id(obj)
    print(f"{type(obj).__name__:8s} at {addr:#018x}  "
          f"mod8={addr%8}  mod16={addr%16}")
```

---

## 13.12 Source References

| File | Contents |
|------|----------|
| `Objects/obmalloc.c` | PyMalloc: ALIGNMENT constant, block/pool alignment |
| `Include/pymem.h` | Memory allocation API |
| `Include/cpython/pymem.h` | Internal memory allocator details |
| `Include/object.h` | Struct definitions (alignment determined by field order) |
| `Objects/longobject.c` | digit array layout and alignment |

---

## 13.13 Interview Questions — Part 13

**Q1**: What is memory alignment and why do CPUs require it?
**A**: Memory alignment means placing data at addresses divisible by the data's size. CPUs read memory in aligned chunks (bus width). Misaligned reads may require two bus transactions or cause faults on strict architectures. Aligned access is always single-transaction.

**Q2**: Why is PyObject's header naturally aligned without any padding?
**A**: Both fields (ob_refcnt and ob_type) are 8 bytes and require 8-byte alignment. The allocator returns 8+ byte aligned addresses. Field at offset 0 → aligned. Field at offset 8 → aligned. No gaps needed.

**Q3**: What is a cache line and how does it affect Python object access?
**A**: A cache line is the minimum unit of data transferred between RAM and CPU cache (typically 64 bytes). When any byte is accessed, the entire 64-byte line is loaded. Small Python objects (≤64 bytes) fit in one cache line, meaning accessing any field loads the entire object.

**Q4**: Explain "cache line bouncing" in the context of reference counting.
**A**: When multiple threads frequently INCREF/DECREF the same object (like None), each write to ob_refcnt invalidates the cache line on other cores. Cores must re-acquire the line in exclusive state before writing, causing it to "bounce" between cores. This is why Python 3.12+ made None/True/etc. immortal (skip refcount updates).

**Q5**: How does object size differ between 32-bit and 64-bit Python?
**A**: Pointers and Py_ssize_t are 4 bytes on 32-bit vs 8 bytes on 64-bit. The PyObject header is 8 bytes on 32-bit vs 16 on 64-bit — objects are roughly 1.5-2× larger on 64-bit. This is the "pointer tax" of 64-bit.

**Q6**: What alignment does CPython's pymalloc allocator guarantee?
**A**: 8-byte alignment for all allocations (the ALIGNMENT constant in obmalloc.c). This is sufficient for all standard C types used in Python object structs.

**Q7**: If a struct has fields `int (4B)`, `double (8B)`, `char (1B)` in that order, what's the total size and where is padding?
**A**: `int` at +0 (4B), padding at +4 (4B), `double` at +8 (8B), `char` at +16 (1B), tail padding at +17 (7B). Total: 24 bytes. Reordering as `double, int, char` gives 16 bytes (saved 8 bytes).
