# Part 18B — Interview Questions: Intermediate (50 Questions)

### Q1: How does CPython achieve dynamic dispatch using ob_type?
**A**: Reads `obj->ob_type` to get the type object, then calls the appropriate function pointer (e.g., `tp_repr`, `tp_hash`, `nb_add`). Each type fills these pointers with its own implementation.

### Q2: Explain the struct embedding pattern CPython uses.
**A**: Every object struct starts with `PyObject ob_base` as its first member. Since C guarantees the address of a struct equals the address of its first member, casting `PyLongObject*` to `PyObject*` is safe — the header bytes are at the same location.

### Q3: Why is ob_refcnt at offset 0?
**A**: Most frequently modified field. Offset 0 means no addition needed to compute its address from the object pointer, marginally faster for the hot Py_INCREF/Py_DECREF paths.

### Q4: Explain why `hash(x)` calls `x->ob_type->tp_hash(x)`.
**A**: Dynamic dispatch. The interpreter doesn't know x's type at compile time. It reads the type at runtime, then calls the hash function registered for that type.

### Q5: What is tp_basicsize in PyTypeObject?
**A**: The size in bytes of instances of this type (without variable-length data). Used by PyObject_New to know how many bytes to allocate.

### Q6: What is tp_itemsize in PyTypeObject?
**A**: For variable-size types, the size of each "item." Total allocation = tp_basicsize + ob_size * tp_itemsize. For fixed-size types, tp_itemsize = 0.

### Q7: How does `PyObject_New` allocate memory?
**A**: Reads `type->tp_basicsize`, calls the allocator for that many bytes, initializes ob_refcnt=1 and ob_type=type, returns the pointer.

### Q8: How does `PyObject_NewVar` differ?
**A**: Allocates `tp_basicsize + nitems * tp_itemsize` bytes. Sets ob_size = nitems. For variable-size objects.

### Q9: What is the relationship between PyObject and PyVarObject in memory?
**A**: PyVarObject's first field IS a PyObject. So the first 16 bytes are identical. ob_size follows at offset 16. Any PyVarObject* can be safely cast to PyObject*.

### Q10: Explain the type chain: 42 → int → type → type.
**A**: `42` is a PyLongObject with ob_type→PyLong_Type. `PyLong_Type` is a PyTypeObject with ob_type→PyType_Type. `PyType_Type` has ob_type→PyType_Type (itself). This is the metaclass chain.

### Q11: What is the difference between tp_dealloc and tp_free?
**A**: `tp_dealloc` is the high-level destructor (decrefs contained objects, does cleanup). `tp_free` is the low-level memory deallocator (returns bytes to the allocator). tp_dealloc usually calls tp_free at the end.

### Q12: How does CPython handle the `__del__` finalizer?
**A**: If a type defines `tp_finalize` (or the object has `__del__`), it's called before deallocation. The GC handles this carefully to avoid resurrection issues.

### Q13: Explain Py_XINCREF vs Py_INCREF.
**A**: `Py_INCREF(op)` assumes op is non-NULL (crashes on NULL). `Py_XINCREF(op)` checks for NULL first and does nothing if NULL. Use X version when the pointer might be NULL.

### Q14: What is Py_NewRef?
**A**: Added in Python 3.10. Increfs and returns the object in one call: `Py_NewRef(obj)` = `Py_INCREF(obj); return obj;`. Cleaner pattern for returning owned references.

### Q15: What happens to an object's memory after deallocation?
**A**: Returned to pymalloc (for small objects) or system free(). The bytes may be reused for a new object. The old ob_refcnt/ob_type values become garbage.

### Q16: Why does CPython use signed Py_ssize_t for ob_refcnt?
**A**: Makes it easier to detect underflow bugs (negative refcount = bug). Debug builds assert ob_refcnt >= 0.

### Q17: What is the free list optimization?
**A**: For frequently created/destroyed types (list, dict, tuple, float), CPython caches recently freed struct memory. New allocations check the free list first, avoiding malloc.

### Q18: How many bytes does `sys.getsizeof([])` return and why?
**A**: ~56 bytes. PyListObject (40 bytes: GC header + PyObject header + ob_size + ob_item + allocated) + internal overhead. No pointer array allocated yet.

### Q19: Why is `sys.getsizeof(())` less than `sys.getsizeof([])`?
**A**: Tuples have no `allocated` field (immutable, no overallocation), and may not have GC tracking for empty tuples. Less metadata needed.

### Q20: Explain how ob_type enables `type(x)` to work.
**A**: `type(x)` in Python reads `x->ob_type` and returns it as a Python object. Since type objects are themselves Python objects, they can be returned directly.

### Q21: What is the ob_type of a class you define with `class Foo: pass`?
**A**: `type` — i.e., `Foo->ob_type == &PyType_Type`. Unless you use a custom metaclass.

### Q22: How does `isinstance(x, MyClass)` work at C level?
**A**: Checks if `Py_TYPE(x)` is `MyClass` or if `MyClass` appears in the MRO (method resolution order) of `Py_TYPE(x)`.

### Q23: What is tp_flags in PyTypeObject?
**A**: A bitmask of flags describing the type's characteristics: is it a heap type? Does it support GC? Is it abstract? Does it have a finalizer? Etc.

### Q24: What flag indicates an object is GC-tracked?
**A**: `Py_TPFLAGS_HAVE_GC`. Types with this flag get a GC header prepended and are tracked by the cycle collector.

### Q25: What is a "heap type" vs a "static type"?
**A**: Static types (int, str, list) are defined in C as global structs. Heap types are created at runtime by `class` statements — allocated on the heap, can be garbage collected.

### Q26: Why does `int.__class__` work?
**A**: Because `int` (PyLong_Type) is itself a PyObject with ob_type→PyType_Type. `__class__` just reads ob_type. Types are objects.

### Q27: What is the memory layout of a Python function object?
**A**: PyObject header (16B) + pointers to: code object, globals dict, defaults tuple, closure, name, qualname, annotations, etc. ~100+ bytes.

### Q28: How does CPython allocate memory for large objects (>512 bytes)?
**A**: Falls through pymalloc to the system allocator (malloc/realloc). pymalloc only handles objects ≤512 bytes.

### Q29: What is the tp_traverse function?
**A**: Used by the GC. Visits all object references (calls a visitor function on each PyObject* the object holds). Enables the cycle collector to build the reference graph.

### Q30: What is tp_clear?
**A**: Breaks reference cycles by NULLing out the object's references. Called by the GC when it detects a cycle it needs to break.

### Q31: Explain the immortal objects feature in Python 3.12.
**A**: Objects like None, True, False, small ints have a special refcount (very large constant). Py_INCREF/Py_DECREF detect this and skip modification. Eliminates cache contention for these frequently-shared objects.

### Q32: What is _Py_IMMORTAL_REFCNT?
**A**: A special refcount value used for immortal objects. When Py_INCREF/Py_DECREF see this value, they don't modify it. The object is never deallocated.

### Q33: How does CPython handle memory alignment for objects?
**A**: Objects are allocated at 8-byte aligned addresses (on 64-bit). pymalloc pools provide aligned blocks. The struct layout follows C alignment rules with padding.

### Q34: What padding exists in PyLongObject for a small integer?
**A**: ob_refcnt(8) + ob_type(8) + ob_size(8) + ob_digit[1](4) = 28 bytes. May be padded to 32 for alignment.

### Q35: Why does CPython store ob_digit as uint32_t[flexible array]?
**A**: Arbitrary precision integers: store value as array of 30-bit "digits." More digits = larger number. The array length = ob_size.

### Q36: What is a "borrowed reference" vs "owned reference"?
**A**: Owned: you're responsible for calling Py_DECREF when done. Borrowed: someone else owns it, you shouldn't decref. PyList_GetItem returns borrowed; PyObject_Repr returns owned.

### Q37: Why is the distinction important?
**A**: Decref-ing a borrowed reference can free the object while it's still in use elsewhere → use-after-free crash. Not decref-ing an owned reference → memory leak.

### Q38: What is the value stack in the CPython interpreter?
**A**: An array of PyObject* pointers. Each stack entry holds a reference to a Python object. PUSH/POP operations manage references.

### Q39: How does the `STORE_NAME` bytecode interact with ob_refcnt?
**A**: Increfs the value being stored (new reference in namespace), decrefs the old value previously bound to that name (if any).

### Q40: What is `_Py_NoneStruct`?
**A**: The actual singleton object for Python's `None`. It's a statically-allocated PyObject in the CPython data segment.

### Q41: How does `x = None` work at the object level?
**A**: The local variable's slot gets a pointer to `_Py_NoneStruct`. Py_INCREF is called on None (though in 3.12+ it's immortal and the incref is skipped).

### Q42: What is the ob_type of None?
**A**: `&_PyNone_Type` — the NoneType type object. `type(None)` returns this.

### Q43: Explain how `x + y` is dispatched at the C level.
**A**: 1) Read `x->ob_type->tp_as_number->nb_add`. 2) If defined, call it with (x, y). 3) If returns NotImplemented, try `y->ob_type->tp_as_number->nb_radd(y, x)`. 4) If both fail, TypeError.

### Q44: What is tp_as_number?
**A**: A pointer to PyNumberMethods struct inside PyTypeObject. Contains function pointers for numeric operations: nb_add, nb_subtract, nb_multiply, etc.

### Q45: What is tp_as_sequence?
**A**: A pointer to PySequenceMethods struct. Contains: sq_length (for len()), sq_concat, sq_repeat, sq_item (indexing), etc.

### Q46: What is tp_as_mapping?
**A**: A pointer to PyMappingMethods struct. Contains: mp_length, mp_subscript (for []), mp_ass_subscript (for []=).

### Q47: How does CPython decide whether to use nb_add or sq_concat for `+`?
**A**: The bytecode BINARY_ADD first tries tp_as_number->nb_add. If that returns NotImplemented or isn't defined, falls back to sq_concat. Priority: number > sequence.

### Q48: What is tp_richcompare?
**A**: Function pointer for all comparison operations (<, <=, ==, !=, >, >=). Takes the operator as a parameter. Replaces the old tp_compare from Python 2.

### Q49: What is the "slots" mechanism for type object fields?
**A**: Each operation (add, repr, hash, etc.) has a "slot" — a position in the type object where its function pointer lives. `__add__` maps to the nb_add slot.

### Q50: How does CPython resolve `obj.method` at the C level?
**A**: 1) Check `type(obj)` for data descriptor with that name. 2) Check `obj.__dict__` for instance attribute. 3) Check `type(obj)` for non-data descriptor or class attribute. Uses tp_getattro.
