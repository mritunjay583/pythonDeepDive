# Part 10 — Decorators Internals

## 10.1 Decorator Desugaring

Decorators are purely syntactic sugar. The compiler transforms:

```python
@decorator
def func():
    pass
```

Into exactly:
```python
def func():
    pass
func = decorator(func)
```

Bytecode for `@decorator def func(): pass`:
```
LOAD_GLOBAL      decorator       ← push the decorator callable
LOAD_CONST       <code object>   ← push func's code object  
MAKE_FUNCTION    0               ← create function object
CALL             1               ← call decorator(func)
STORE_FAST       func            ← store result as 'func'
```

The decorator is called AFTER the function is created. The result (whatever the decorator returns) is bound to the name.

---

## 10.2 Stacked Decorators

```python
@dec_a
@dec_b
@dec_c
def func():
    pass
```

Desugars to:
```python
def func():
    pass
func = dec_a(dec_b(dec_c(func)))
```

Bytecode:
```
LOAD_GLOBAL    dec_a          ← push dec_a (applied LAST)
LOAD_GLOBAL    dec_b          ← push dec_b (applied second)
LOAD_GLOBAL    dec_c          ← push dec_c (applied first)
LOAD_CONST     <code object>
MAKE_FUNCTION  0              ← create original func
CALL           1              ← call dec_c(func)
CALL           1              ← call dec_b(result)
CALL           1              ← call dec_a(result)
STORE_FAST     func           ← bind final result
```

Application order: innermost (closest to `def`) applied FIRST.

---

## 10.3 Decorators with Arguments

```python
@repeat(3)
def func():
    pass
```

This is NOT `repeat` as a decorator. It's `repeat(3)` as a **decorator factory**:

```python
# Equivalent to:
_decorator = repeat(3)   # Call factory → returns actual decorator
func = _decorator(func)  # Apply the decorator
```

Bytecode:
```
LOAD_GLOBAL    repeat
LOAD_CONST     3
CALL           1              ← repeat(3) → returns decorator
LOAD_CONST     <code object>
MAKE_FUNCTION  0
CALL           1              ← decorator(func)
STORE_FAST     func
```

Implementation pattern:
```python
def repeat(n):                    # Factory (takes decorator args)
    def decorator(func):          # Actual decorator (takes function)
        def wrapper(*args, **kw): # Replacement function
            for _ in range(n):
                result = func(*args, **kw)
            return result
        return wrapper
    return decorator
```

---

## 10.4 functools.wraps

Without `@wraps`, the decorator replaces the function's identity:

```python
def my_decorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@my_decorator
def greet(name):
    """Greet someone."""
    return f"Hello, {name}"

greet.__name__    # 'wrapper' — WRONG! Lost original name!
greet.__doc__     # None — WRONG! Lost docstring!
```

`@functools.wraps(func)` copies metadata:

```python
from functools import wraps

def my_decorator(func):
    @wraps(func)  # Copies __name__, __doc__, __module__, __qualname__, __dict__, __wrapped__
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@my_decorator
def greet(name):
    """Greet someone."""
    return f"Hello, {name}"

greet.__name__     # 'greet' ✓
greet.__doc__      # 'Greet someone.' ✓
greet.__wrapped__  # <original greet function> (for introspection)
```

`functools.wraps` internally calls `functools.update_wrapper`:
```python
def update_wrapper(wrapper, wrapped):
    wrapper.__name__ = wrapped.__name__
    wrapper.__qualname__ = wrapped.__qualname__
    wrapper.__doc__ = wrapped.__doc__
    wrapper.__module__ = wrapped.__module__
    wrapper.__dict__.update(wrapped.__dict__)
    wrapper.__wrapped__ = wrapped
    return wrapper
```

---

## 10.5 Class Decorators

```python
@singleton
class Database:
    pass

# Desugars to:
class Database:
    pass
Database = singleton(Database)
```

The decorator receives the **class object** (a PyTypeObject) and can return:
- The same class (modified)
- A different class
- A completely different object (function, instance, etc.)

```python
def singleton(cls):
    instances = {}
    @wraps(cls, updated=[])
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance

@singleton
class DB:
    pass

# DB is now a FUNCTION, not a class!
# DB() calls get_instance() → returns cached instance
```

---

## 10.6 Decorator Performance Cost

Each decorator adds one function call layer:

```python
@decorator
def func():
    return 42

# Calling func() actually calls: decorator's wrapper → func()
# Extra cost per call: one additional frame creation + function dispatch
# Typical overhead: ~200-500 ns per decorator layer
```

For hot inner loops, this matters:
```python
# If called 10M times, each 200ns decorator adds 2 seconds!
# Solutions:
# 1. Don't decorate hot functions
# 2. Use C-level decorators (like @functools.lru_cache)
# 3. Apply decorator at a higher level (decorate caller, not callee)
```

---

## 10.7 Interview Questions — Part 10

**Q1**: What do decorators compile to in bytecode?
**A**: Push decorator, create function, CALL decorator with function as argument, store result. `@dec def f(): pass` = `f = dec(f)` exactly.

**Q2**: In what order are stacked decorators applied?
**A**: Bottom-up (innermost first). `@a @b @c def f()` → `f = a(b(c(f)))`. `c` is applied first, `a` last.

**Q3**: What does `@functools.wraps(func)` do?
**A**: Copies `__name__`, `__doc__`, `__module__`, `__qualname__`, `__dict__`, and sets `__wrapped__` on the wrapper function. Preserves the original function's identity for introspection.

**Q4**: Can a decorator return a non-function?
**A**: Yes. A decorator can return ANY object. Common patterns: return the same class (modified), return a descriptor, return a cached instance. The name just gets bound to whatever is returned.

**Q5**: What is the performance cost of a decorator?
**A**: One additional function call per invocation (~200-500ns per layer). For functions called millions of times, this adds measurable overhead.
