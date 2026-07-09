# Part 11 — The Callable Protocol

## 11.1 What Makes Something Callable

In CPython, anything with a `tp_call` slot (or `__call__` method) is callable:

```python
callable(print)         # True — built-in function (PyCFunction)
callable(len)           # True — built-in function
callable(lambda: 0)     # True — function (PyFunctionObject)
callable(int)           # True — type (calling creates instances)
callable(42)            # False — int has no tp_call

class MyCallable:
    def __call__(self, x):
        return x * 2

obj = MyCallable()
callable(obj)           # True — has __call__
obj(5)                  # 10
```

---

## 11.2 The tp_call Slot

```c
// Every type has a tp_call slot:
typedef PyObject *(*ternaryfunc)(PyObject *, PyObject *, PyObject *);
// ternaryfunc signature: (self, args_tuple, kwargs_dict) → result

// In PyTypeObject:
struct PyTypeObject {
    // ...
    ternaryfunc tp_call;  // Called when instance is used as callable
    // ...
};

// For PyFunction_Type:
//   tp_call = function_call → creates frame, executes bytecode

// For PyType_Type (classes):
//   tp_call = type_call → calls tp_new + tp_init (instance creation)

// For user classes with __call__:
//   tp_call = slot_tp_call → looks up __call__ method, calls it
```

---

## 11.3 Vectorcall (PEP 590)

The traditional `tp_call` protocol is slow:
```
Old: caller creates args tuple + kwargs dict → tp_call → callee unpacks them
     2 allocations + 2 deallocations per call!
```

Vectorcall passes arguments as a C array:
```c
typedef PyObject *(*vectorcallfunc)(
    PyObject *callable,
    PyObject *const *args,    // C array of arguments (NO tuple!)
    size_t nargsf,            // number of args (+ flags in high bits)
    PyObject *kwnames         // tuple of keyword names (values in args array)
);

// Usage:
result = _PyObject_VectorcallTstate(tstate, callable, args, nargs, kwnames);
```

Benefits:
- Zero allocation for argument passing
- ~20% faster function calls
- All built-in functions support vectorcall since 3.9+

---

## 11.4 Method Binding

```python
class Dog:
    def bark(self):
        return "Woof!"

rex = Dog()
rex.bark()  # How does 'self' get passed?
```

When you access `rex.bark`:
1. Python creates a **bound method** object
2. The bound method remembers: (function=Dog.bark, self=rex)
3. When called, it prepends `self` to the arguments

```c
// PyMethodObject:
typedef struct {
    PyObject_HEAD
    PyObject *im_func;   // The underlying function (Dog.bark)
    PyObject *im_self;   // The instance (rex)
} PyMethodObject;
```

```python
method = rex.bark
type(method)        # <class 'method'>
method.__func__     # <function Dog.bark at ...>
method.__self__     # rex

# rex.bark() is equivalent to:
Dog.bark.__get__(rex, Dog)()  # Descriptor protocol creates bound method
# Which calls: Dog.bark(rex)
```

---

## 11.5 functools.partial

```python
from functools import partial

def power(base, exponent):
    return base ** exponent

square = partial(power, exponent=2)
square(5)  # power(5, exponent=2) = 25
```

partial stores frozen arguments:
```c
// functools.partial is a C type:
typedef struct {
    PyObject_HEAD
    PyObject *fn;         // Original function
    PyObject *args;       // Frozen positional args (tuple)
    PyObject *kw;         // Frozen keyword args (dict)
    PyObject *dict;       // Instance __dict__
    PyObject *weakreflist;
    vectorcallfunc vectorcall;
} partialobject;
```

When called: prepends frozen args, merges frozen kwargs, calls the original function.

---

## 11.6 Interview Questions — Part 11

**Q1**: What makes an object callable in CPython?
**A**: Having a non-NULL `tp_call` slot in its type object. For Python classes with `__call__`, the slot is auto-filled with a wrapper that calls `__call__`.

**Q2**: What is vectorcall?
**A**: PEP 590's optimized calling convention that passes arguments as a C array instead of creating tuple/dict. ~20% faster for function calls.

**Q3**: How does method binding work?
**A**: Accessing `obj.method` invokes the descriptor protocol (__get__) on the function, creating a PyMethodObject that stores (function, instance). When called, it prepends `self`.

**Q4**: What is `functools.partial` at the C level?
**A**: A C extension type (partialobject) that stores a function + frozen args tuple + frozen kwargs dict. On call: combines frozen + new args and calls the original function.
