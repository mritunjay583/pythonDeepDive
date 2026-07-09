# Part 7 — Generator Functions

## 7.1 The Core Idea

A generator function is a function that can **suspend** and **resume** its execution, yielding values one at a time:

```python
def countdown(n):
    while n > 0:
        yield n      # SUSPEND here, return n to caller
        n -= 1       # RESUME here on next() call

# Calling does NOT execute the body:
gen = countdown(5)   # Creates generator OBJECT (no code runs yet!)
type(gen)            # <class 'generator'>

# Each next() RESUMES execution until the next yield:
next(gen)  # 5 (runs until first yield)
next(gen)  # 4 (resumes after yield, runs until next yield)
next(gen)  # 3
next(gen)  # 2
next(gen)  # 1
next(gen)  # StopIteration! (function body completed, implicit return)
```

---

## 7.2 How Generators Differ From Normal Functions

| Aspect | Normal Function | Generator Function |
|--------|----------------|-------------------|
| Contains `yield`? | No | Yes (at least one) |
| Calling it | Executes body immediately | Returns generator object |
| Return value | Whatever `return expr` says | The generator object |
| `return` | Returns value, destroys frame | Raises StopIteration(value) |
| Frame | Created on call, destroyed on return | Created on call, PRESERVED between yields |
| Memory | Frame lives only during call | Frame lives until generator is GC'd |
| CO_GENERATOR flag | No | Yes |

---

## 7.3 Generator State Machine

A generator is always in one of these states:

```
CREATED     → has never been started (next() not called yet)
     │ next()
     ▼
RUNNING     → currently executing (between resume and next yield/return)
     │ yield / return / exception
     ▼
SUSPENDED   → paused at a yield point (waiting for next())
     │ next() / send() / throw() / close()
     ▼
RUNNING     → executing again...
     │ ...
     ▼
CLOSED      → completed (returned or exception) — cannot be resumed
```

```python
import inspect

def gen():
    yield 1
    yield 2

g = gen()
inspect.getgeneratorstate(g)  # 'GEN_CREATED'
next(g)                        # yields 1
inspect.getgeneratorstate(g)  # 'GEN_SUSPENDED'
next(g)                        # yields 2
inspect.getgeneratorstate(g)  # 'GEN_SUSPENDED'
next(g)                        # StopIteration
inspect.getgeneratorstate(g)  # 'GEN_CLOSED'
```

---

## 7.4 What Happens at Each yield

```python
def numbers():
    print("A")
    yield 1       # Suspend point 1
    print("B")
    yield 2       # Suspend point 2
    print("C")
    # Implicit return None → StopIteration

g = numbers()
# State: CREATED, nothing printed yet

val = next(g)
# Prints "A", reaches yield 1, SUSPENDS
# val = 1, state = SUSPENDED
# Frame preserved: instruction pointer at yield 1, locals intact

val = next(g)
# RESUMES after yield 1, prints "B", reaches yield 2, SUSPENDS
# val = 2, state = SUSPENDED

val = next(g)
# RESUMES after yield 2, prints "C", reaches end of function
# Raises StopIteration, state = CLOSED
# Frame destroyed
```

---

## 7.5 Frame Preservation

Normal functions: frame destroyed on return.
Generators: frame **preserved** between yields:

```
After gen = numbers(); next(gen):  [yields 1, suspends]

Generator Object (PyGenObject):
├── gi_frame → _PyInterpreterFrame
│               ├── prev_instr = <points to yield 1 instruction>
│               ├── localsplus = [local variables preserved]
│               └── stacktop = <operand stack preserved>
├── gi_code → <code object>
├── gi_running = False
└── gi_name = "numbers"

The frame sits on the HEAP (not the C call stack).
It persists until the generator is closed/GC'd.
```

---

## 7.6 Generator as Iterator

Generators automatically implement the iterator protocol:

```python
def gen():
    yield 1; yield 2; yield 3

g = gen()
hasattr(g, '__iter__')  # True (returns self)
hasattr(g, '__next__')  # True (resumes and yields)

# So generators work in for loops directly:
for x in gen():
    print(x)  # 1, 2, 3
```

---

## 7.7 Generator Methods: send(), throw(), close()

### gen.send(value):
```python
def accumulator():
    total = 0
    while True:
        value = yield total  # yield sends total OUT, receives value IN
        total += value

acc = accumulator()
next(acc)           # Prime: runs to first yield, returns 0 (total=0)
acc.send(10)        # Resumes, value=10, total=10, yields 10
acc.send(20)        # Resumes, value=20, total=30, yields 30
acc.send(5)         # Resumes, value=5, total=35, yields 35
```

### gen.throw(exc):
```python
def careful():
    try:
        yield 1
        yield 2
    except ValueError:
        yield "caught!"

g = careful()
next(g)              # 1
g.throw(ValueError)  # Raises ValueError inside generator → caught! yields "caught!"
```

### gen.close():
```python
def resource():
    try:
        yield "data"
    finally:
        print("cleanup!")  # Always runs on close!

g = resource()
next(g)    # "data"
g.close()  # Prints "cleanup!" (throws GeneratorExit inside)
```

---

## 7.8 yield from (PEP 380)

Delegates to a sub-iterator:
```python
def sub():
    yield 1; yield 2; yield 3

def main():
    yield "start"
    yield from sub()   # Delegates ALL yields from sub()
    yield "end"

list(main())  # ['start', 1, 2, 3, 'end']
```

`yield from` handles send(), throw(), and close() transparently — the sub-generator behaves as if the caller is talking to it directly.

---

## 7.9 return in Generators

```python
def gen():
    yield 1
    yield 2
    return "final"   # Sets StopIteration.value!

g = gen()
next(g)  # 1
next(g)  # 2
try:
    next(g)
except StopIteration as e:
    print(e.value)  # "final"!

# yield from captures this:
def wrapper():
    result = yield from gen()  # result = "final"
    print(result)
```

---

## 7.10 Interview Questions — Part 7

**Q1**: What does calling a generator function return? **A**: A generator object (NOT the result of the body). The body doesn't execute until next() is called.

**Q2**: Where does the generator's frame live between yields? **A**: On the heap (inside the PyGenObject). Unlike normal functions whose frames are on the C stack/data stack and destroyed on return.

**Q3**: What is gen.send(value) used for? **A**: Resumes the generator AND passes `value` as the result of the `yield` expression inside. First call must use `next()` or `send(None)` to prime the generator.

**Q4**: What happens when a generator function executes `return value`? **A**: Raises `StopIteration` with `.value` set to the returned value. `yield from` can capture this value.

**Q5**: What does `yield from sub_iter` do? **A**: Delegates iteration to sub_iter. Each next()/send()/throw()/close() is forwarded to sub_iter. When sub_iter exhausts, the return value becomes the result of the `yield from` expression.
