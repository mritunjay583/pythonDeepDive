# Part 9 — PyGenObject: Complete C Structure

## 9.1 The Struct Definition

```c
// Include/cpython/genobject.h

// Shared base for generators, coroutines, and async generators:
#define _PyGenObject_HEAD(prefix)    \
    PyObject_HEAD                    \
    PyObject *prefix##_name;         \
    PyObject *prefix##_qualname;     \
    _PyInterpreterFrame *prefix##_frame; \
    PyObject *prefix##_code;         \
    PyObject *prefix##_weakreflist;  \
    PyObject *prefix##_exc_state;    \
    char prefix##_hooks_inited;      \
    char prefix##_closed;            \
    char prefix##_running_async;

// Generator object:
typedef struct {
    _PyGenObject_HEAD(gi)
    // gi_name, gi_qualname, gi_frame, gi_code, gi_weakreflist,
    // gi_exc_state, gi_hooks_inited, gi_closed, gi_running_async
} PyGenObject;

// Coroutine object (same layout, different type):
typedef struct {
    _PyGenObject_HEAD(cr)
    PyObject *cr_origin_or_finalizer;  // Extra field for coroutines
} PyCoroObject;

// Async generator object:
typedef struct {
    _PyGenObject_HEAD(ag)
    PyObject *ag_finalizer;            // Weak ref finalizer
    int ag_hooks_inited;
    int ag_closed;
    int ag_running_async;
} PyAsyncGenObject;
```

---

## 9.2 Field-by-Field Analysis

### `gi_frame` (_PyInterpreterFrame *)
```
THE most important field. Points to the suspended execution frame.

When GEN_CREATED:  Points to frame with args bound, IP at start
When GEN_SUSPENDED: Points to frame with full state at yield point  
When GEN_RUNNING:  NULL (frame is on active call stack)
When GEN_CLOSED:   NULL (frame has been freed)

Size of pointed-to frame: varies
  = sizeof(_PyInterpreterFrame header) 
  + co_nlocals * 8 (locals)
  + co_ncellvars * 8 (cells)
  + co_nfreevars * 8 (free vars)  
  + co_stacksize * 8 (operand stack)
  
Typical: 100-500 bytes for the frame
```

### `gi_code` (PyObject *)
```
Pointer to the generator function's code object.
Used for: name resolution, bytecode access, debugging.
Same code object shared by all generators created from same function.
Reference count: Py_INCREF'd by the generator.
```

### `gi_name` / `gi_qualname` (PyObject *)
```
Name of the generator function:
  gi_name = "my_gen"
  gi_qualname = "MyClass.my_gen" (qualified for nested)
  
Used by: repr(gen) → "<generator object my_gen at 0x...>"
```

### `gi_exc_state` (PyObject *)
```
Saved exception state when generator is suspended with an active exception.
When a generator is inside a try/except and yields, the exception 
context must be preserved for when it resumes.

Maps to: tstate->exc_info at yield time → saved here
Restored on resume → tstate->exc_info set back
```

### `gi_closed` (char, 1 byte)
```
True (1): generator has completed (return/exception/close)
False (0): generator is alive (created or suspended)

Once closed: ALL future next()/send()/throw() immediately raise StopIteration
(except throw with non-GeneratorExit → that propagates)
```

### `gi_running_async` (char, 1 byte)
```
True: generator is being used in an async context (awaited)
Used for: detecting improper use of generators as coroutines
```

### `gi_weakreflist` (PyObject *)
```
Head of the weak reference list for this generator.
Allows weakref.ref(gen) to work.
Used by: debugging tools, resource tracking.
```

---

## 9.3 Complete Memory Layout (64-bit)

```
PyGenObject at address 0x7F001000:
═══════════════════════════════════════════════════════════════
Offset  Field                Size   Value
─────────────────────────────────────────────────────────────
+0x00   ob_refcnt            8      1
+0x08   ob_type              8      → &PyGen_Type
+0x10   gi_name              8      → "my_generator" (str)
+0x18   gi_qualname          8      → "my_generator" (str)
+0x20   gi_frame             8      → 0x7F002000 (frame on heap)
+0x28   gi_code              8      → PyCodeObject
+0x30   gi_weakreflist       8      NULL
+0x38   gi_exc_state         8      → Py_None (no saved exception)
+0x40   gi_hooks_inited      1      0
+0x41   gi_closed            1      0
+0x42   gi_running_async     1      0
+0x43   (padding)            5      
═══════════════════════════════════════════════════════════════
Total: ~72 bytes (with alignment to 80)
Plus: GC header (~24 bytes before ob_refcnt)
Effective: ~104 bytes for the generator object itself
Plus: frame allocation (~100-500 bytes typically)
Grand total: ~200-600 bytes per generator
═══════════════════════════════════════════════════════════════
```

---

## 9.4 The Type Object: PyGen_Type

```c
PyTypeObject PyGen_Type = {
    PyVarObject_HEAD_INIT(&PyType_Type, 0)
    "generator",                        /* tp_name */
    sizeof(PyGenObject),                /* tp_basicsize */
    0,                                  /* tp_itemsize */
    (destructor)gen_dealloc,           /* tp_dealloc */
    0,                                  /* tp_vectorcall_offset */
    0,                                  /* tp_getattr */
    0,                                  /* tp_setattr */
    &gen_as_async,                     /* tp_as_async (for await compat) */
    (reprfunc)gen_repr,                /* tp_repr */
    0,                                  /* tp_as_number */
    0,                                  /* tp_as_sequence */
    0,                                  /* tp_as_mapping */
    PyObject_HashNotImplemented,        /* tp_hash (generators unhashable!) */
    0,                                  /* tp_call */
    0,                                  /* tp_str */
    PyObject_GenericGetAttr,           /* tp_getattro */
    0,                                  /* tp_setattro */
    0,                                  /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC,  /* tp_flags */
    0,                                  /* tp_doc */
    (traverseproc)gen_traverse,        /* tp_traverse (GC!) */
    0,                                  /* tp_clear */
    0,                                  /* tp_richcompare */
    offsetof(PyGenObject, gi_weakreflist), /* tp_weaklistoffset */
    PyObject_SelfIter,                 /* tp_iter → returns self */
    (iternextfunc)gen_iternext,        /* tp_iternext → calls next */
    gen_methods,                       /* tp_methods → send, throw, close */
    gen_memberlist,                    /* tp_members → gi_* attributes */
    gen_getsetlist,                    /* tp_getset → name, qualname */
    0,                                  /* tp_base */
    ...
};
```

Key slots:
- `tp_iter = PyObject_SelfIter` → `iter(gen) is gen` (generators are their own iterables)
- `tp_iternext = gen_iternext` → implements `next(gen)`
- `tp_dealloc = gen_dealloc` → cleanup + close on GC
- `tp_traverse = gen_traverse` → GC can scan generator's frame references
- `Py_TPFLAGS_HAVE_GC` → generators are GC-tracked (can form cycles!)

---

## 9.5 GC Interaction

Generators are GC-tracked because they can form reference cycles:

```python
def gen():
    myself = yield  # Generator references itself via 'myself' local!
    yield myself

g = gen()
next(g)
g.send(g)  # Now: g.gi_frame.localsplus["myself"] → g (cycle!)
```

`gen_traverse` visits all objects reachable from the generator's frame:
```c
static int gen_traverse(PyGenObject *gen, visitproc visit, void *arg) {
    Py_VISIT(gen->gi_code);
    Py_VISIT(gen->gi_name);
    Py_VISIT(gen->gi_qualname);
    Py_VISIT(gen->gi_exc_state);
    if (gen->gi_frame) {
        // Visit all objects in the frame's localsplus:
        _PyInterpreterFrame *frame = gen->gi_frame;
        for (int i = 0; i < frame_size; i++) {
            Py_VISIT(frame->localsplus[i]);
        }
    }
    return 0;
}
```

---

## 9.6 Interview Questions — Part 9

**Q1**: How large is a PyGenObject? **A**: ~104 bytes for the object itself (with GC header), plus 100-500 bytes for the suspended frame. Total: typically 200-600 bytes per generator.

**Q2**: Why are generators GC-tracked (Py_TPFLAGS_HAVE_GC)? **A**: Generators hold references to all locals in their frame. These locals can reference the generator itself (or form other cycles). The cycle collector must be able to traverse generator internals.

**Q3**: What is gi_exc_state used for? **A**: Saves the exception context when a generator yields from inside a try/except. On resume, the saved exception state is restored so exception handling continues correctly.

**Q4**: Are generators hashable? **A**: No. `tp_hash = PyObject_HashNotImplemented`. You can't use a generator as a dict key or set element. (Each generator is a unique mutable stateful object.)

**Q5**: How do generators, coroutines, and async generators share code? **A**: They all use the same `_PyGenObject_HEAD` macro (shared field layout). They differ only in type object (PyGen_Type vs PyCoro_Type vs PyAsyncGen_Type) and some extra fields. gen_send_ex2 works for all three.
