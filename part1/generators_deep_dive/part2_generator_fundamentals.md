# Part 2 — Generator Fundamentals

## 2.1 The yield Keyword

`yield` is the single keyword that transforms a normal function into a generator function:

```python
# Normal function (no yield): executes immediately, returns value
def normal():
    return 42

# Generator function (has yield): returns generator object, body deferred
def gen():
    yield 42

normal()  # 42 (executed immediately)
gen()     # <generator object gen at 0x...> (NOT executed!)
```

**Rule**: If a function body contains `yield` (anywhere, even in dead code), the compiler sets the `CO_GENERATOR` flag on its code object. Calling it returns a PyGenObject instead of executing the body.

---

## 2.2 Generator Function vs Generator Object

```python
def countdown(n):       # This is the GENERATOR FUNCTION
    while n > 0:
        yield n
        n -= 1

c = countdown(5)        # This is the GENERATOR OBJECT

type(countdown)   # <class 'function'>     — PyFunctionObject
type(c)           # <class 'generator'>    — PyGenObject

# The function is reusable (call many times):
c1 = countdown(10)  # Independent generator 1
c2 = countdown(3)   # Independent generator 2

# Each generator has its own state:
next(c1)  # 10
next(c2)  # 3 (independent!)
```

---

## 2.3 Lazy Execution

Generator body executes **lazily** — only when values are requested:

```python
def gen():
    print("Step 1")
    yield 1
    print("Step 2")
    yield 2
    print("Step 3")
    yield 3
    print("Done")

g = gen()
# Nothing printed yet! Body hasn't started.

next(g)  # prints "Step 1", returns 1
next(g)  # prints "Step 2", returns 2
next(g)  # prints "Step 3", returns 3
next(g)  # prints "Done", raises StopIteration
```

Each `next()` runs the body until the next `yield`, then pauses.

---

## 2.4 Generator Object Properties

```python
def gen(x, y):
    z = x + y
    yield z
    yield z * 2

g = gen(3, 4)

# Attributes:
g.gi_frame        # Frame object (or None when closed)
g.gi_code         # Code object (same as gen.__code__)
g.gi_running      # False (not currently executing)
g.gi_yieldfrom    # None (not delegating via yield from)
g.__name__        # 'gen'
g.__qualname__    # 'gen'

# Generator IS an iterator:
iter(g) is g      # True (returns self)
hasattr(g, '__next__')  # True
```

---

## 2.5 Generator Lifecycle Memory Diagram

```
Phase 1: Creation (gen(3, 4) called)
─────────────────────────────────────
PyGenObject on heap:
  gi_frame → Frame{locals=[x=3, y=4, z=NULL], IP=start}
  gi_closed = False
  gi_running = False
State: GEN_CREATED

Phase 2: First next() 
─────────────────────────────────────
Frame resumes at start → executes z = x + y → hits yield z
PyGenObject:
  gi_frame → Frame{locals=[x=3, y=4, z=7], IP=yield_1}
  Operand stack at yield: [7] (the yielded value was popped and returned)
State: GEN_SUSPENDED
Returns: 7

Phase 3: Second next()
─────────────────────────────────────
Frame resumes after yield_1 → hits yield z*2
PyGenObject:
  gi_frame → Frame{locals=[x=3, y=4, z=7], IP=yield_2}
State: GEN_SUSPENDED
Returns: 14

Phase 4: Third next()
─────────────────────────────────────
Frame resumes after yield_2 → reaches end of function
PyGenObject:
  gi_frame = NULL (freed!)
  gi_closed = True
State: GEN_CLOSED
Raises: StopIteration
```

---

## 2.6 Generators Implement the Iterator Protocol Automatically

```python
def gen():
    yield 1; yield 2; yield 3

g = gen()
# Has __iter__ (returns self) and __next__ (returns next yield):
for x in g:
    print(x)  # 1, 2, 3

# Generators ARE iterators — no __iter__/__next__ boilerplate needed!
# The compiler + runtime provide these automatically.
```

---

## 2.7 Interview Questions — Part 2

**Q1**: What distinguishes a generator function from a normal function at compile time? **A**: The CO_GENERATOR flag in co_flags. Set by the compiler when it detects any `yield` (or `yield from`) in the function body.

**Q2**: What is the type of `gen()` vs `gen`? **A**: `gen` is `<class 'function'>` (PyFunctionObject). `gen()` is `<class 'generator'>` (PyGenObject). Calling the function creates the generator object.

**Q3**: When does a generator function's body start executing? **A**: On the FIRST `next()` call (or `send(None)`). Not when the generator function is called — that only creates the generator object and attaches the frame.

**Q4**: What is gi_frame? **A**: Pointer to the suspended _PyInterpreterFrame containing the generator's execution state (locals, instruction pointer, operand stack). NULL when generator is running or closed.

**Q5**: Is a generator reusable? **A**: No. A generator object is a one-shot iterator. Once exhausted (StopIteration raised), it's permanently closed. Call the generator FUNCTION again to get a fresh generator.
