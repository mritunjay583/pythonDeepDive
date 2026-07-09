# Part 14 — CPython Source Tour

## 14.1 File Map

```
Objects/unicodeobject.c     16,000+ lines — THE implementation file
  ├── String creation (PyUnicode_New, PyUnicode_FromString, etc.)
  ├── String operations (concat, join, split, replace, find, etc.)
  ├── Comparison (unicode_compare, unicode_eq)
  ├── Hashing (unicode_hash)
  ├── Encoding/Decoding (UTF-8, Latin-1, ASCII fast paths)
  ├── Formatting (PyUnicode_Format — % operator)
  ├── Interning (PyUnicode_InternInPlace)
  ├── Type object definition (PyUnicode_Type at bottom)
  └── Helper macros and internal functions

Include/cpython/unicodeobject.h  — struct definitions
  ├── PyASCIIObject
  ├── PyCompactUnicodeObject  
  ├── PyUnicodeObject (legacy)
  └── Internal macros (PyUnicode_KIND, PyUnicode_DATA, etc.)

Include/unicodeobject.h  — public C API
  ├── PyUnicode_Check, PyUnicode_GET_LENGTH
  ├── PyUnicode_FromString, PyUnicode_FromFormat
  ├── PyUnicode_Decode*, PyUnicode_Encode*
  └── ~200 public API functions
```

---

## 14.2 Key Functions

| Function | Purpose | Complexity |
|----------|---------|------------|
| `PyUnicode_New(size, maxchar)` | Allocate string with optimal kind | O(size) |
| `PyUnicode_FromString(u)` | Create from C UTF-8 string | O(n) |
| `PyUnicode_Concat(a, b)` | Concatenation | O(n+m) |
| `PyUnicode_Join(sep, seq)` | join() implementation | O(total) |
| `PyUnicode_Find(str, sub, ...)` | find()/index() | O(n) avg |
| `PyUnicode_Replace(str, old, new, max)` | replace() | O(n) |
| `PyUnicode_Split(str, sep, max)` | split() | O(n) |
| `unicode_hash(self)` | Hash computation + caching | O(n)/O(1) |
| `PyUnicode_Compare(a, b)` | Comparison (<, ==, >) | O(n) |
| `PyUnicode_InternInPlace(&s)` | Intern a string | O(1) amortized |
| `PyUnicode_AsUTF8(s)` | Get UTF-8 C string (cached) | O(n)/O(1) |
| `PyUnicode_AsUTF8String(s)` | Encode to UTF-8 bytes | O(n) |
| `PyUnicode_Substring(s, start, end)` | Slicing | O(end-start) |
| `PyUnicode_Format(fmt, args)` | % formatting | O(output) |
| `unicode_upper/lower/title` | Case conversion | O(n) |

---

## 14.3 Key Macros

```c
// Read character at index (handles all kinds):
#define PyUnicode_READ(kind, data, index)                    \
    ((kind) == PyUnicode_1BYTE_KIND ?                       \
        ((const Py_UCS1 *)(data))[(index)] :                \
        ((kind) == PyUnicode_2BYTE_KIND ?                   \
            ((const Py_UCS2 *)(data))[(index)] :            \
            ((const Py_UCS4 *)(data))[(index)]))

// Write character at index:
#define PyUnicode_WRITE(kind, data, index, value)           \
    do { if ((kind) == PyUnicode_1BYTE_KIND)                \
            ((Py_UCS1 *)(data))[(index)] = (Py_UCS1)(value); \
         else if ((kind) == PyUnicode_2BYTE_KIND)           \
            ((Py_UCS2 *)(data))[(index)] = (Py_UCS2)(value); \
         else                                               \
            ((Py_UCS4 *)(data))[(index)] = (Py_UCS4)(value); \
    } while (0)

// Get data pointer for compact string:
#define PyUnicode_DATA(op)                                  \
    (PyUnicode_IS_COMPACT(op) ?                             \
        (PyUnicode_IS_ASCII(op) ?                           \
            ((void*)((PyASCIIObject*)(op) + 1)) :           \
            ((void*)((PyCompactUnicodeObject*)(op) + 1))) : \
        ((void*)((PyUnicodeObject*)(op))->data.any))

// Get kind (1, 2, or 4):
#define PyUnicode_KIND(op)  (((PyASCIIObject*)(op))->state.kind)

// Get length:
#define PyUnicode_GET_LENGTH(op)  (((PyASCIIObject*)(op))->length)

// Check types:
#define PyUnicode_IS_ASCII(op)    (((PyASCIIObject*)(op))->state.ascii)
#define PyUnicode_IS_COMPACT(op)  (((PyASCIIObject*)(op))->state.compact)
#define PyUnicode_CHECK_INTERNED(op) (((PyASCIIObject*)(op))->state.interned)
```

---

## 14.4 The STRINGLIB Template Pattern

CPython uses C preprocessor templates to generate kind-specific code:

```c
// Objects/stringlib/ — template files included multiple times:
//   stringlib/fastsearch.h  — search algorithm
//   stringlib/find.h        — find/rfind
//   stringlib/count.h       — count occurrences
//   stringlib/split.h       — split implementations

// unicodeobject.c includes these templates THREE times:
#define STRINGLIB_CHAR Py_UCS1
#include "stringlib/fastsearch.h"
#undef STRINGLIB_CHAR

#define STRINGLIB_CHAR Py_UCS2
#include "stringlib/fastsearch.h"
#undef STRINGLIB_CHAR

#define STRINGLIB_CHAR Py_UCS4
#include "stringlib/fastsearch.h"
#undef STRINGLIB_CHAR

// This generates three specialized versions of each algorithm —
// one per kind. The compiler optimizes each fully for the specific width.
// No runtime kind branching inside the hot loops!
```

This is why `unicodeobject.c` is 16,000+ lines — each algorithm exists in 3 copies.

---

## 14.5 The PyUnicode_Type Definition

```c
// At the bottom of unicodeobject.c:
PyTypeObject PyUnicode_Type = {
    PyVarObject_HEAD_INIT(&PyType_Type, 0)
    "str",                              /* tp_name */
    sizeof(PyUnicodeObject),            /* tp_basicsize */
    0,                                  /* tp_itemsize */
    (destructor)unicode_dealloc,        /* tp_dealloc */
    0,                                  /* tp_vectorcall_offset */
    0,                                  /* tp_getattr */
    0,                                  /* tp_setattr */
    0,                                  /* tp_as_async */
    unicode_repr,                       /* tp_repr */
    &unicode_as_number,                 /* tp_as_number (for % formatting) */
    &unicode_as_sequence,               /* tp_as_sequence */
    &unicode_as_mapping,                /* tp_as_mapping (for [] indexing) */
    (hashfunc)unicode_hash,             /* tp_hash */
    0,                                  /* tp_call */
    unicode_str,                        /* tp_str */
    PyObject_GenericGetAttr,            /* tp_getattro */
    0,                                  /* tp_setattro */
    0,                                  /* tp_as_buffer (NOT SUPPORTED!) */
    Py_TPFLAGS_DEFAULT | ...,           /* tp_flags */
    unicode_doc,                        /* tp_doc */
    0,                                  /* tp_traverse (no GC needed!) */
    0,                                  /* tp_clear */
    unicode_richcompare,                /* tp_richcompare */
    0,                                  /* tp_weaklistoffset */
    unicode_iter,                       /* tp_iter */
    0,                                  /* tp_iternext */
    unicode_methods,                    /* tp_methods */
    0,                                  /* tp_members */
    0,                                  /* tp_getset */
    0,                                  /* tp_base (&PyBaseObject_Type) */
    ...
};
```

Note: `tp_traverse = 0` — strings are NOT tracked by the garbage collector. They can't form reference cycles (they don't reference other objects). This saves the 24-byte GC header per string.

---

## 14.6 Interview Questions — Part 14

**Q1**: Why is Objects/unicodeobject.c over 16,000 lines?
**A**: String operations must handle 3 kinds (1B/2B/4B). The STRINGLIB template system generates 3 specialized versions of each algorithm. Plus: creation, destruction, comparison, hashing, formatting, interning, encoding/decoding, and ~50 string methods.

**Q2**: What is the STRINGLIB template pattern?
**A**: C preprocessor trick: define STRINGLIB_CHAR as Py_UCS1/2/4, then #include the same algorithm file. Generates 3 type-specialized versions — no per-character branching in hot loops, full compiler optimization for each width.

**Q3**: Why doesn't str have tp_traverse (GC tracking)?
**A**: Strings don't reference other Python objects — they contain only character data. They can't form reference cycles. Skipping GC tracking saves 24 bytes per string and avoids GC traversal overhead.

**Q4**: What does PyUnicode_DATA return?
**A**: A void pointer to the start of character data. For compact ASCII: offset 48 (after PyASCIIObject). For compact non-ASCII: offset 64 (after PyCompactUnicodeObject). For legacy: the external data pointer.
