# Part 1 — Function Objects

## 1.1 Why Functions Are Objects

In Python, functions are **first-class objects** — they are instances of `PyFunctionObject`, have reference counts, type pointers, and can be assigned to variables, stored in containers, passed as arguments, and returned from other functions.

```python
def greet(name):
    return f"Hello, {name}"

# greet is a PyObject* on the heap:
type(greet)         # <class 'function'>
id(greet)           # memory address
greet.__name__      # 'greet'
greet.__code__      # <code object greet at 0x...>
greet.__globals__   # module's global dictionary

# Functions ARE objects:
funcs = [greet, len, print]  # store in list
funcs[0]("World")            # call from list
```

---

## 1.2 PyFunctionObject — The C Structure

```c
// Include/cpython/funcobject.h
typedef struct {
    PyObject_HEAD                    // ob_refcnt + ob_type (16 bytes)
    PyObject *func_globals;         // Global dict (the module's __dict__)
    PyObject *func_builtins;        // Builtins dict  
    PyObject *func_name;            // __name__ (str)
    PyObject *func_qualname;        // __qualname__ (str, includes enclosing)
    PyObject *func_code;            // __code__ (PyCodeObject)
    PyObject *func_defaults;        // __defaults__ (tuple of default arg values)
    PyObject *func_kwdefaults;      // __kwdefaults__ (dict of kw-only defaults)
    PyObject *func_closure;         // __closure__ (tuple of cell objects)
    PyObject *func_doc;             // __doc__ (str or None)
    PyObject *func_dict;            // __dict__ (arbitrary attributes)
    PyObject *func_weakreflist;     // weak references
    PyObject *func_module;          // __module__ (str)
    PyObject *func_annotations;     // __annotations__ (dict)
    PyObject *func_typeparams;      // __type_params__ (3.12+)
    vectorcallfunc vectorcall;      // fast call function pointer
    uint32_t func_version;          // version for specialization
} PyFunctionObject;
```

A function object is ~150 bytes of pointers alone (not counting what they point to).

---

## 1.3 Function Creation at Runtime

When Python encounters a `def` statement at runtime:

```python
def add(x, y):
    return x + y
```

This is NOT just "defining a function." At runtime, `def` is an **assignment statement** that:
1. Takes a pre-compiled **code object** (created at compile time)
2. Wraps it in a **function object** (created at runtime)
3. Binds the function object to the name in the current namespace

Bytecode for `def add(x, y): return x + y`:
```
RESUME                 0
LOAD_CONST             0 (<code object add>)   ← code compiled earlier
MAKE_FUNCTION          0                        ← create PyFunctionObject
STORE_NAME             0 ('add')                ← bind name 'add'
```

`MAKE_FUNCTION`:
- Pops the code object from the stack
- Creates a new PyFunctionObject
- Sets func_globals = current frame's globals
- Sets func_builtins = current frame's builtins
- If closures: attaches closure tuple
- If defaults: attaches defaults tuple
- Pushes the function object onto the stack

---

## 1.4 Memory Layout

```
Variable 'add' (in namespace dict or fast locals):
     │
     ▼
┌──────────────────────────────────────────────────┐
│ PyFunctionObject                                  │
│                                                   │
│ ob_refcnt:       1                                │
│ ob_type:         → &PyFunction_Type               │
│ func_globals:    → module.__dict__                │
│ func_builtins:   → builtins.__dict__              │
│ func_name:       → "add" (str, interned)          │
│ func_qualname:   → "add" (str)                    │
│ func_code:       ──────────────────────┐          │
│ func_defaults:   NULL (no defaults)    │          │
│ func_closure:    NULL (no closure)     │          │
│ func_doc:        NULL (no docstring)   │          │
│ ...                                    │          │
└────────────────────────────────────────┼──────────┘
                                         │
                                         ▼
                      ┌─────────────────────────────────────┐
                      │ PyCodeObject                         │
                      │                                     │
                      │ co_code:     b'd\x01S\x00'         │
                      │ co_consts:   (None,)                │
                      │ co_varnames: ('x', 'y')            │
                      │ co_argcount: 2                      │
                      │ co_stacksize: 2                     │
                      │ ...                                 │
                      └─────────────────────────────────────┘
```

---

## 1.5 Function Identity and Equality

Each `def` execution creates a **new** function object:

```python
def make_adder():
    def add(x, y):
        return x + y
    return add

f1 = make_adder()
f2 = make_adder()

f1 is f2           # False! Different PyFunctionObject each call!
f1.__code__ is f2.__code__  # True! Same PyCodeObject (shared, immutable)
```

The code object is compiled once and shared. The function object is created fresh each time `def` executes (because it captures the current globals, potentially different defaults, closures, etc.).

---

## 1.6 Default Arguments: The Mutable Default Trap Explained

```python
def append_to(item, target=[]):
    target.append(item)
    return target
```

At compile time: code object for `append_to` is created.
At function-definition time (when `def` runs):
1. `[]` is evaluated → creates a list object
2. The list is stored as `func_defaults = ([],)` — a tuple of default values
3. This tuple is stored in the **function object**, not the code object

```
PyFunctionObject:
  func_defaults → tuple: ( list_obj, )
                           │
                           ▼
                        [  ]  ← THIS SAME LIST is reused on every call!
```

Every call that uses the default gets the **same list object** from `func_defaults`. Mutations accumulate:
```python
append_to(1)  # [1]         ← mutates the default list
append_to(2)  # [1, 2]      ← same list, keeps growing!
append_to(3)  # [1, 2, 3]
```

---

## 1.7 Lambdas

Lambdas are syntactically restricted but structurally identical to named functions:

```python
f = lambda x, y: x + y
```

Bytecode:
```
LOAD_CONST         <code object <lambda>>
MAKE_FUNCTION      0
STORE_NAME         'f'
```

The ONLY differences from `def`:
1. `__name__` and `__qualname__` are `"<lambda>"` instead of a real name
2. Body is limited to a single expression
3. No docstring by default

Internally: **identical** PyFunctionObject wrapping a PyCodeObject.

---

## 1.8 Callable Objects (`__call__`)

Any object with `__call__` is callable:

```python
class Adder:
    def __init__(self, n):
        self.n = n
    def __call__(self, x):
        return self.n + x

add5 = Adder(5)
add5(10)  # 15 — calls Adder.__call__(add5, 10)
```

How CPython dispatches:
```c
// When CALL opcode encounters a callable:
if (PyFunction_Check(callable)) {
    // Fast path: Python function → create frame, execute
} else if (PyCFunction_Check(callable)) {
    // Built-in C function → call directly
} else {
    // General path: look up tp_call (or __call__) 
    result = Py_TYPE(callable)->tp_call(callable, args, kwargs);
}
```

---

## 1.9 functools.partial

```python
from functools import partial
add5 = partial(add, 5)  # "Freeze" first argument
add5(3)  # add(5, 3) = 8
```

partial creates a `functools.partial` object:
```
partial object:
  .func   → the original function (add)
  .args   → (5,)  (frozen positional args)
  .keywords → {}   (frozen keyword args)
```

When called, it prepends `.args` and merges `.keywords` with the call arguments, then calls `.func`.

---

## 1.10 Interview Questions — Part 1

**Q1**: Are Python functions objects?
**A**: Yes. They're instances of PyFunctionObject with refcount, type pointer, and attributes. They can be assigned to variables, stored in containers, passed as arguments.

**Q2**: What happens at runtime when Python encounters `def`?
**A**: `def` is an assignment: MAKE_FUNCTION creates a PyFunctionObject wrapping the pre-compiled code object, then STORE_NAME binds it to the function name.

**Q3**: Why do different calls to a factory function return different function objects with the same code?
**A**: Each `def` execution creates a new PyFunctionObject (captures current globals, defaults, closure). But all share the same immutable PyCodeObject (compiled once).

**Q4**: Explain the mutable default argument bug at the object level.
**A**: Default values are evaluated ONCE at function-definition time and stored in `func_defaults`. The same mutable object is reused on every call that uses the default — mutations accumulate.

**Q5**: How is a lambda different from def internally?
**A**: Structurally identical — same PyFunctionObject wrapping a PyCodeObject. Only differences: __name__ is "<lambda>", body limited to one expression, no docstring by default.

**Q6**: How does CPython call an object with `__call__`?
**A**: The CALL opcode checks the object's type's `tp_call` slot. For classes with `__call__`, the descriptor protocol resolves `__call__` → calls it with the instance as first arg.
