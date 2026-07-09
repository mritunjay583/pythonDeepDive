# Part 18A — Interview Questions: Beginner (50 Questions)

### Q1: What is PyObject?
**A**: The base C struct that every Python object starts with. Contains `ob_refcnt` (reference count) and `ob_type` (pointer to type object). 16 bytes on 64-bit.

### Q2: What fields does PyObject contain?
**A**: Two fields: `ob_refcnt` (Py_ssize_t, 8 bytes) for reference counting, and `ob_type` (PyTypeObject*, 8 bytes) pointing to the type object.

### Q3: What is PyVarObject?
**A**: An extension of PyObject for variable-size objects. Adds `ob_size` (Py_ssize_t, 8 bytes) which stores the number of elements. 24 bytes header.

### Q4: What is ob_refcnt?
**A**: The reference count — how many pointers currently reference this object. When it reaches 0, the object is deallocated.

### Q5: What is ob_type?
**A**: A pointer to the object's type (PyTypeObject). Used for method dispatch, type checking, and behavior definition.

### Q6: What is ob_size?
**A**: In PyVarObject, the number of items/elements in the object. For a list of 5 items, ob_size = 5. This is how len() is O(1).

### Q7: How much memory overhead does every Python object have?
**A**: Minimum 16 bytes (PyObject header). With GC tracking, 40+ bytes total. Variable-size objects add 8 more bytes (ob_size).

### Q8: Why does Python integer 42 take 28 bytes?
**A**: 16 bytes PyObject header + 8 bytes ob_size (it's a PyVarObject) + 4 bytes for the digit value = 28 bytes.

### Q9: What does `id(x)` return in CPython?
**A**: The memory address of the object (cast to an integer). Unique during the object's lifetime.

### Q10: Why is id() guaranteed unique for live objects?
**A**: Two objects can't occupy the same memory address simultaneously. Once an object is deallocated, its address may be reused.

### Q11: What is a type object?
**A**: A Python object (itself with ob_refcnt and ob_type) that describes a type — contains function pointers for all operations, the type's name, size info, etc.

### Q12: What is `type(type)`?
**A**: `type` itself. The metaclass PyType_Type has its ob_type pointing to itself. This terminates the infinite regress.

### Q13: Is `None` a PyObject?
**A**: Yes. It's a singleton PyObject with ob_type pointing to PyNone_Type. Has its own refcount (very high, or immortal in 3.12+).

### Q14: What is the difference between fixed-size and variable-size objects?
**A**: Fixed-size (float, int with 1 digit) always occupy the same bytes. Variable-size (list, str, tuple) need ob_size because their data length varies.

### Q15: Give examples of fixed-size objects.
**A**: float (always 24 bytes), bool (fixed), NoneType, function objects (fixed struct size).

### Q16: Give examples of variable-size objects.
**A**: list, tuple, str, bytes, bytearray, dict, set, int (large integers use multiple digits).

### Q17: What does `sys.getsizeof(x)` measure?
**A**: The shallow memory of the object: header + internal data. Does NOT include objects it references.

### Q18: Why is `sys.getsizeof(1)` = 28 bytes?
**A**: PyVarObject header (24 bytes) + one 4-byte digit = 28 bytes. Small integers use a single 30-bit digit.

### Q19: What happens when ob_refcnt reaches 0?
**A**: The object's type's `tp_dealloc` function is called, which frees the object's memory (after decref-ing any contained objects).

### Q20: What is Py_INCREF?
**A**: A C macro/function that increments an object's ob_refcnt by 1. Called when a new reference to the object is created.

### Q21: What is Py_DECREF?
**A**: A C macro/function that decrements ob_refcnt by 1. If it reaches 0, triggers deallocation.

### Q22: What is the PyObject_HEAD macro?
**A**: Expands to `PyObject ob_base;` — used at the start of every object struct definition to embed the common header.

### Q23: What is PyObject_VAR_HEAD?
**A**: Expands to `PyVarObject ob_base;` — used for variable-size object structs, includes ob_size.

### Q24: Can two different objects have the same id()?
**A**: Not simultaneously. But after an object is deallocated, a new object may reuse its address, getting the same id().

### Q25: What is `type(42)`?
**A**: `<class 'int'>` — the PyLong_Type type object that all integers share.

### Q26: Do all integers share the same type object?
**A**: Yes. All int instances have `ob_type → PyLong_Type`. There's one type object shared by all integers.

### Q27: What is PyLong_Type?
**A**: The type object for Python integers. Contains function pointers for int operations (addition, repr, hash, etc.).

### Q28: What does `isinstance(x, int)` check internally?
**A**: Checks if `x->ob_type` is `&PyLong_Type` or a subclass of it (by traversing the type's MRO).

### Q29: Where is PyObject defined in CPython source?
**A**: `Include/object.h` (public API) and `Include/cpython/object.h` (internal details).

### Q30: What is the Py_TYPE macro?
**A**: `#define Py_TYPE(ob) (((PyObject*)(ob))->ob_type)` — reads the type pointer from any object.

### Q31: What is the Py_SIZE macro?
**A**: `#define Py_SIZE(ob) (((PyVarObject*)(ob))->ob_size)` — reads the size field from variable-size objects.

### Q32: How does len() work in O(1)?
**A**: For built-in types, `len(x)` just reads `Py_SIZE(x)` — the ob_size field. No counting needed.

### Q33: What is a reference in CPython?
**A**: A pointer (PyObject*) that "points to" an object. The object's refcount tracks how many such pointers exist.

### Q34: What creates a new reference?
**A**: Assignment (`b = a`), passing to functions, storing in containers, returning from functions — any time a new pointer to the object is stored somewhere.

### Q35: What destroys a reference?
**A**: `del name`, name going out of scope, container being modified/destroyed, variable being reassigned.

### Q36: Why does Python have reference counting?
**A**: Deterministic deallocation — objects are freed immediately when their last reference disappears. No need to wait for a GC cycle.

### Q37: What is the struct layout of PyFloatObject?
**A**: `PyObject ob_base` (16 bytes) + `double ob_fval` (8 bytes) = 24 bytes total.

### Q38: Is `True` the same object every time you use it?
**A**: Yes. `True` is a singleton. All uses of `True` reference the same object in memory.

### Q39: What does `x is y` check?
**A**: Whether `x` and `y` point to the same object (same memory address). Equivalent to `id(x) == id(y)`.

### Q40: Why is `a = 256; b = 256; a is b` True?
**A**: CPython caches integers [-5, 256]. Both `a` and `b` point to the same pre-allocated object.

### Q41: Why is `a = 257; b = 257; a is b` sometimes True?
**A**: Within the same compilation unit (same code block), CPython may intern the literal. In interactive mode, separate lines create separate objects.

### Q42: What is the small integer cache?
**A**: CPython pre-allocates integer objects for [-5, 256] at startup. These are singletons — reused, never deallocated.

### Q43: What is string interning?
**A**: CPython caches certain strings (identifiers, small strings) so that equal strings share one object. Saves memory and enables fast `is` comparison.

### Q44: What is `__sizeof__()` method?
**A**: Returns the memory size of the object in bytes (same as `sys.getsizeof` without GC overhead).

### Q45: What happens to ob_refcnt during `a = b`?
**A**: Old object referenced by `a`: Py_DECREF. Object referenced by `b`: Py_INCREF. Then `a`'s pointer is updated.

### Q46: Can ob_refcnt overflow?
**A**: On 64-bit, it's 8 bytes (max ~9.2×10^18). Practically impossible. Python 3.12+ uses immortal objects for frequently shared ones.

### Q47: What is the GC header?
**A**: 24 bytes prepended to objects that can form reference cycles (containers). Contains prev/next pointers for the GC's tracking list.

### Q48: Do all objects have GC headers?
**A**: No. Only "container" types (list, dict, set, class instances, etc.) that can form cycles. Simple types (int, float, str) typically don't.

### Q49: What does `type(x).__name__` access internally?
**A**: Reads `x->ob_type->tp_name` — the C string stored in the type object.

### Q50: What is the total memory cost of `x = 3.14`?
**A**: PyFloatObject = 24 bytes (16 header + 8 double). Plus possible GC overhead if tracked. No GC tracking for floats, so 24 bytes.
