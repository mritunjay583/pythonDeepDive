# Part 18C — Interview Questions: Senior (50 Questions)

### Q1: Explain the C-level difference between `Py_DECREF` and `_Py_DECREF`.
**A**: `Py_DECREF` is the public macro (may include assertions in debug builds). `_Py_DECREF` is the internal implementation that does the actual decrement and deallocation check. In release builds, they're essentially the same.

### Q2: How does the immortal object refcount interact with sub-interpreters?
**A**: Immortal objects (3.12+) have a fixed refcount that Py_INCREF/DECREF don't modify. This is critical for sub-interpreters: shared immortal objects don't need atomic refcount operations, eliminating a major bottleneck for parallelism.

### Q3: Explain the GIL's relationship to ob_refcnt updates.
**A**: The GIL ensures only one thread modifies ob_refcnt at a time — non-atomic increment/decrement is safe. Without the GIL (PEP 703/free-threading), refcounts need atomic operations (or deferred counting), which is a major complexity driver.

### Q4: How does Python 3.12+'s per-object GC bit work?
**A**: Instead of storing GC state in a separate header, some state can be encoded in unused bits of ob_refcnt (on 64-bit systems, you don't need all 64 bits for counting). This saves memory for GC-tracked objects.

### Q5: Explain the Py_TRASHCAN mechanism.
**A**: Prevents C stack overflow during deallocation of deeply nested structures (e.g., a list of lists of lists...). When dealloc recursion gets too deep, it defers remaining deallocations to a queue processed in a flat loop.

### Q6: What is the relationship between tp_basicsize, tp_itemsize, and `__sizeof__`?
**A**: tp_basicsize = fixed overhead (header + fixed fields). tp_itemsize = per-element cost. `__sizeof__` = tp_basicsize + ob_size * tp_itemsize (for C types). Heap types may override `__sizeof__` in Python.

### Q7: Explain how a C extension type defines its object layout.
**A**: The extension defines a C struct starting with PyObject_HEAD (or PyObject_VAR_HEAD), sets tp_basicsize/tp_itemsize in the PyTypeObject, and registers function pointers for operations. PyType_Ready initializes inheritance chains.

### Q8: What is the difference between `tp_new` and `tp_init`?
**A**: `tp_new` allocates memory and creates the raw object (like `__new__`). `tp_init` initializes the object's state (like `__init__`). tp_new is the allocator, tp_init is the constructor.

### Q9: How does subclassing at C level add fields to PyObject?
**A**: The subclass struct includes the base struct as its first member, then adds fields. tp_basicsize of the subclass > tp_basicsize of the base. The header remains at offset 0.

### Q10: What happens when a type defines both `__hash__` and `__eq__` at the Python level?
**A**: CPython creates wrapper C functions (slot wrappers) that call the Python methods. These are installed at `tp_hash` and `tp_richcompare` slots in the type object.

### Q11: Explain the `tp_dictoffset` field.
**A**: The byte offset within the object struct where the instance `__dict__` pointer is stored. If 0, instances don't have a __dict__. Negative means offset from end (for variable-size types).

### Q12: How does `__slots__` relate to object memory layout?
**A**: With `__slots__`, instances don't get a __dict__ (tp_dictoffset=0). Instead, attributes are stored at fixed offsets in the struct as `PyMemberDef` entries. Saves 8+ bytes per instance.

### Q13: What is `tp_weaklistoffset`?
**A**: Byte offset of the weak reference list pointer within the object. If 0, the type doesn't support weak references. This pointer allows the weakref machinery to find all weak refs to an object.

### Q14: Explain how CPython handles object resurrection in `__del__`.
**A**: If `tp_finalize` (__del__) creates a new reference to the object (resurrection), CPython detects this (refcount > 0 after finalize) and removes the object from the "to be collected" set. It lives on.

### Q15: What is the `tp_version_tag` field?
**A**: A cache invalidation tag for method resolution. Changed when the type's MRO or attributes change. Allows cached attribute lookups to detect when they're stale.

### Q16: How does the adaptive interpreter (3.11+) interact with type objects?
**A**: LOAD_ATTR is specialized per-type. It caches the attribute's position and the type's version_tag. On cache hit (version matches), it reads the attribute directly without full lookup. Cache miss → full lookup + update cache.

### Q17: Explain the `Py_TPFLAGS_IMMUTABLETYPE` flag.
**A**: Set on built-in types that cannot be modified after creation. Prevents monkey-patching of int, str, etc. Heap types (user classes) don't have this flag.

### Q18: What is `_PyObject_GC_TRACK` and when is it called?
**A**: Adds an object to the GC's list of tracked objects. Called after an object is fully initialized (not during allocation, to avoid the GC seeing a half-initialized object).

### Q19: Explain the deferred reference counting proposal (PEP 703).
**A**: For free-threading (no GIL), some objects use biased/deferred reference counting — refcount updates are batched or thread-local, then reconciled periodically. This avoids atomic operations on every incref/decref.

### Q20: What is the `ob_refcnt_split` field in Python 3.13+ free-threading?
**A**: In free-threaded builds, ob_refcnt is split into a local count and a shared count. Local operations don't need atomic ops. Only cross-thread sharing requires atomic synchronization.

### Q21: How does CPython's object allocator handle alignment for SIMD?
**A**: pymalloc provides 8-byte aligned blocks on 64-bit. For SIMD (16/32/64 byte alignment), objects typically don't need it since Python objects don't use SIMD directly. NumPy handles its own alignment.

### Q22: What is the performance cost of the GC header per object?
**A**: 24 bytes (two pointers + GC state) on 64-bit. For a list of 1M integers, that's 24MB of GC headers alone if every int were GC-tracked (but ints aren't tracked, only containers).

### Q23: Explain how `PyType_FromSpec` creates types dynamically.
**A**: Takes a PyType_Spec struct (name, size, flags, slot definitions), allocates a new PyTypeObject on the heap, fills in the slots, calls PyType_Ready. Used by extension modules for PEP 384 stable ABI.

### Q24: What is the stable ABI and how does it relate to PyObject?
**A**: The stable ABI (PEP 384) allows C extensions to work across Python versions. PyObject's layout (ob_refcnt + ob_type) is part of the stable ABI — it cannot change without breaking extensions.

### Q25: Explain how `__init_subclass__` interacts with type object creation.
**A**: During `type.__init__` (when a class is created), Python calls `__init_subclass__` on each base class. This happens after the type object is allocated but before the class is fully available.

### Q26: What is the `tp_vectorcall_offset` field?
**A**: Byte offset in the type object (or instance) where a vectorcall function pointer is stored. Enables the fast vectorcall protocol (PEP 590) without dictionary lookup.

### Q27: Explain vectorcall and how it avoids tuple/dict creation for function calls.
**A**: Normal call: create args tuple + kwargs dict, pass to tp_call. Vectorcall: pass arguments as a C array + names tuple, no tuple/dict allocation. ~20% faster for typical function calls.

### Q28: How does CPython's mark-and-sweep interact with reference counting?
**A**: Reference counting handles most deallocation. The cycle collector only deals with container objects that might form cycles. It uses tp_traverse to walk references, identifies unreachable cycle groups, uses tp_clear to break them.

### Q29: What is the `gc_refs` field in the GC header?
**A**: During collection, stores a copy of ob_refcnt. The GC subtracts internal references (within the tracked set) to find objects with zero external references — these are garbage.

### Q30: Explain how weakref interacts with ob_refcnt.
**A**: Weak references don't increment ob_refcnt. They use a separate linked list (at tp_weaklistoffset). When ob_refcnt hits 0 and dealloc begins, all weakrefs are invalidated (set to dead) before the object is freed.

### Q31: What is the `tp_subclasses` field?
**A**: A weak-reference set of all direct subclasses of this type. Used for cache invalidation: when a base class changes, it must notify all subclasses to update their method caches.

### Q32: How does CPython handle C-level operator overloading priorities?
**A**: For `x + y`: try `x.__add__(y)` first. If it returns NotImplemented AND type(y) is a subclass of type(x), try `y.__radd__(x)` first (subclass gets priority). Complex dispatch logic in abstract.c.

### Q33: Explain the `tp_as_buffer` protocol.
**A**: Defines how an object exports raw memory (buffer protocol). Contains function pointers for getting/releasing buffers. Used by memoryview, struct, ctypes, NumPy for zero-copy data sharing.

### Q34: What is the `Py_buffer` struct?
**A**: Describes a memory region: pointer to data, length, itemsize, format string, shape, strides, readonly flag. Returned by objects implementing the buffer protocol.

### Q35: How does CPython detect and handle reference count corruption?
**A**: In debug builds, assertions check ob_refcnt > 0 before decref. Some builds add a "secret" value to detect double-free. `sys.getrefcount()` helps debugging (note: it adds 1 for the argument itself).

### Q36: Explain the interaction between `__del__`, GC, and reference counting.
**A**: If an object in a cycle has `__del__`, the GC (pre-3.4) couldn't safely collect it (finalization order unclear). Since 3.4 (PEP 442), the GC calls finalizers safely by separating finalization from deallocation.

### Q37: What is `tp_alloc` and how does it differ from `tp_new`?
**A**: `tp_alloc` is the low-level allocator (allocates raw bytes, initializes header). `tp_new` is the higher-level factory (calls tp_alloc, then does type-specific initialization). tp_alloc is usually PyType_GenericAlloc.

### Q38: How does `PyType_GenericAlloc` initialize an object?
**A**: 1) Compute size (tp_basicsize + nitems*tp_itemsize). 2) Allocate (pymalloc or malloc). 3) Zero-fill. 4) Set ob_refcnt=1, ob_type=type. 5) If GC-tracked: add GC header. 6) Return.

### Q39: What is the `Py_TPFLAGS_BASETYPE` flag?
**A**: If set, the type can be subclassed. If not set (e.g., some C types), attempting to subclass raises TypeError. Controls whether other types can inherit from this type.

### Q40: Explain the `__class__` assignment (`obj.__class__ = NewType`).
**A**: Changes ob_type pointer. Only works if the memory layout is compatible (same tp_basicsize, same GC status, etc.). Very restrictive in practice — mostly for same-layout types.

### Q41: How does CPython implement per-opcode specialization (PEP 659)?
**A**: Each bytecode instruction can be "specialized" based on observed types. The specialized version embeds type assumptions. If the type (checked via ob_type) doesn't match, it deoptimizes to the generic path.

### Q42: What is the `_PyObject_HEAD_EXTRA` macro in debug builds?
**A**: In `Py_TRACE_REFS` builds, adds `_ob_next` and `_ob_prev` pointers to PyObject, creating a doubly-linked list of ALL live objects. Used for leak detection. Adds 16 bytes per object.

### Q43: Explain how `copy.copy()` interacts with object layout.
**A**: Calls `cls.__copy__()` if defined, else for built-in types does type-specific shallow copy. Must allocate new memory (tp_basicsize), copy header, copy internal data, incref contained references.

### Q44: What is the memory layout of a Python class object (user-defined class)?
**A**: A heap-allocated PyTypeObject (~400+ bytes) with: all tp_* fields, __dict__ (the class's namespace), __bases__, __mro__, method descriptors. Plus the methods/attributes in its __dict__.

### Q45: How does multiple inheritance affect object memory layout?
**A**: Each base class may contribute to tp_basicsize. CPython uses C3 linearization for MRO. The object struct must be large enough for all bases' fields. Conflicts → TypeError at class creation.

### Q46: Explain the relationship between ob_type and `__class__` attribute.
**A**: `obj.__class__` reads `obj->ob_type` and returns it as a Python object. `obj.__class__ = X` writes `obj->ob_type = X` (with compatibility checks).

### Q47: What are "inline caches" in CPython 3.11+ and how do they use type info?
**A**: Bytecode instructions have cache entries (extra words after the instruction). LOAD_ATTR caches the type's version_tag + attribute offset. On each execution, check if obj->ob_type's version matches → fast path.

### Q48: Explain how `del obj.attr` triggers tp_setattro with NULL.
**A**: Attribute deletion calls `tp_setattro(obj, name, NULL)`. A NULL value argument means "delete this attribute." The type's setattr implementation checks for NULL and handles deletion.

### Q49: What is the `Py_TPFLAGS_SEQUENCE` vs `Py_TPFLAGS_MAPPING` distinction?
**A**: Added in 3.10 for pattern matching. Determines whether an object matches a `[pattern]` (sequence) or `{pattern}` (mapping) in match/case. Checked via ob_type->tp_flags.

### Q50: Explain how a future no-GIL Python (PEP 703) changes the PyObject layout.
**A**: ob_refcnt becomes atomic (or split into thread-local/shared counts). Additional synchronization bits may be stored in unused refcount bits. Type pointer reads need memory fences. The fundamental layout (refcnt + type) persists but with concurrency primitives.
