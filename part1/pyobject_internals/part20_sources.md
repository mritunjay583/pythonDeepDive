# Part 20 — Sources & References

## Primary Sources

### CPython Source Code

| File | Content |
|------|---------|
| `Include/object.h` | PyObject, PyVarObject definitions, public macros |
| `Include/cpython/object.h` | Internal/private object API |
| `Include/refcount.h` | Py_INCREF, Py_DECREF, Py_NewRef |
| `Include/pytypedefs.h` | Forward declarations of all type objects |
| `Objects/object.c` | Object protocol implementation |
| `Objects/typeobject.c` | PyTypeObject implementation, type creation |
| `Objects/longobject.c` | Integer (PyLongObject) implementation |
| `Objects/floatobject.c` | Float (PyFloatObject) implementation |
| `Objects/listobject.c` | List (PyListObject) implementation |
| `Objects/tupleobject.c` | Tuple (PyTupleObject) implementation |
| `Objects/unicodeobject.c` | String (PyUnicodeObject) implementation |
| `Objects/dictobject.c` | Dict (PyDictObject) implementation |
| `Modules/gcmodule.c` | Garbage collector implementation |
| `Objects/obmalloc.c` | pymalloc allocator |

Browse at: https://github.com/python/cpython

---

## Python Enhancement Proposals (PEPs)

| PEP | Title | Relevance |
|-----|-------|-----------|
| PEP 3123 | Making PyObject_HEAD conform to standard C | Struct layout changes |
| PEP 384 | Defining a Stable ABI | What parts of PyObject are guaranteed stable |
| PEP 442 | Safe object finalization | How __del__ interacts with GC |
| PEP 509 | Add a private version to dict | ma_version_tag for optimization |
| PEP 590 | Vectorcall: a fast calling protocol | tp_vectorcall_offset |
| PEP 659 | Specializing Adaptive Interpreter | Per-opcode type specialization |
| PEP 683 | Immortal Objects | _Py_IMMORTAL_REFCNT, ob_refcnt changes |
| PEP 703 | Making the Global Interpreter Lock Optional | Free-threading refcount changes |

Read PEPs at: https://peps.python.org/

---

## Books

### "CPython Internals" by Anthony Shaw (Real Python, 2021)
- Comprehensive guide to CPython source code
- Covers object model, compiler, interpreter
- Walks through PyObject and type system

### "Inside the Python Virtual Machine" by Obi Ike-Nwosu
- Deep dive into bytecode and execution
- Object allocation and lifecycle
- Value stack and frame objects

### "Python in a Nutshell" by Alex Martelli et al.
- Chapter on Python's object model
- Reference semantics and identity
- Type system architecture

### "Fluent Python" by Luciano Ramalho (2nd edition, 2022)
- Chapter 1: The Python Data Model
- Special methods and their C-level equivalents
- Object protocols

---

## Official Documentation

| Resource | URL |
|----------|-----|
| Python Data Model | https://docs.python.org/3/reference/datamodel.html |
| C API Reference | https://docs.python.org/3/c-api/index.html |
| Object Protocol | https://docs.python.org/3/c-api/object.html |
| Type Objects | https://docs.python.org/3/c-api/type.html |
| Memory Management | https://docs.python.org/3/c-api/memory.html |
| CPython Developer Guide | https://devguide.python.org/ |

---

## Key Blog Posts & Talks

- **"The Structure of CPython Objects"** — Series by various CPython core devs on realpython.com
- **"Python Object Internals"** — Eli Bendersky's blog (eli.thegreenplace.net)
- **"How Python Objects are Stored in Memory"** — Artem Golubin
- **"Understanding CPython's Garbage Collector"** — Pablo Galindo (PyCon talks)
- **"Immortal Objects for Python"** — Eddie Elizondo (PEP 683 author, Meta)
- **"Faster CPython"** — Mark Shannon's project (Python 3.11+ optimizations)

---

## Tools for Exploration

```python
# Inspect object sizes:
import sys
sys.getsizeof(obj)

# Inspect refcounts:
sys.getrefcount(obj)

# Inspect type:
type(obj)
type(obj).__mro__

# Inspect object id (address):
id(obj)
hex(id(obj))

# Inspect object with ctypes (low-level):
import ctypes
ctypes.c_ssize_t.from_address(id(obj)).value  # ob_refcnt

# GC interaction:
import gc
gc.get_referents(obj)  # Objects this object references
gc.get_referrers(obj)  # Objects referencing this object
gc.is_tracked(obj)     # Is GC tracking this?

# Memory profiling:
from pympler import asizeof
asizeof.asizeof(obj)   # Deep recursive size

import tracemalloc
tracemalloc.start()
```

---

## Important Distinctions

### Language Guarantee vs Implementation Detail

| Aspect | Language Guarantee | CPython Detail |
|--------|-------------------|----------------|
| `id(x)` returns unique int | ✅ Yes (during lifetime) | Returns memory address |
| `x is y` checks identity | ✅ Yes | Compares pointers |
| Objects have types | ✅ Yes | ob_type field at offset 8 |
| Integers are immutable | ✅ Yes | PyLongObject internals |
| Lists maintain order | ✅ Yes | Dynamic array implementation |
| Small ints are cached | ❌ No (impl detail) | [-5, 256] cache |
| String interning | ❌ No (impl detail) | Identifier-like strings |
| Reference counting | ❌ No (impl detail) | Other impls use tracing GC |
| GIL exists | ❌ No (impl detail) | Jython, PyPy may not have it |
| Object header is 16 bytes | ❌ No (impl detail) | Other impls differ |

Always distinguish these in interviews and production code. Never depend on implementation details for correctness.
