# Part 14 — Coroutine Evolution: From Generators to async/await

## 14.1 The Timeline

```
2001  PEP 255  - Simple Generators (yield)
                 Problem solved: lazy iteration
                 
2005  PEP 342  - Enhanced Generators (send/throw/close)
                 Problem solved: bidirectional communication
                 Enabled: generator-based coroutines (Twisted, Tornado)

2009  PEP 380  - yield from
                 Problem solved: generator delegation, return values
                 Enabled: clean coroutine composition

2014  PEP 479  - StopIteration handling fix
                 Problem solved: silent generator termination bugs

2015  PEP 492  - async def / await (native coroutines)
                 Problem solved: separate type for coroutines, clear semantics
                 Enabled: asyncio as first-class

2016  PEP 525  - Async Generators (async def + yield)
                 Problem solved: lazy async iteration

2016  PEP 530  - Async Comprehensions
                 Problem solved: [x async for x in aiter]
```

---

## 14.2 PEP 255: Simple Generators (2001)

**Problem**: Functions can only produce one result. Iterators require verbose classes.

**Solution**: `yield` statement pauses function, produces value to caller.

```python
# Before PEP 255: must write iterator class
class Fib:
    def __init__(self):
        self.a, self.b = 0, 1
    def __iter__(self): return self
    def __next__(self):
        result = self.a
        self.a, self.b = self.b, self.a + self.b
        return result

# After PEP 255: natural code
def fib():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b
```

**Limitation**: Communication is one-way (generator → caller only). Caller can't send values back in.

---

## 14.3 PEP 342: Enhanced Generators (2005)

**Problem**: Need bidirectional communication for coroutines (Twisted's inlineCallbacks, Tornado).

**Solution**: `yield` becomes an EXPRESSION (not just statement). Add `send()`, `throw()`, `close()`.

```python
# Before PEP 342: yield is a statement (one-way)
def gen():
    yield 1  # Can only produce, not receive

# After PEP 342: yield is an expression (bidirectional!)
def accumulator():
    total = 0
    while True:
        value = yield total  # RECEIVE value, SEND total
        total += value

acc = accumulator()
next(acc)         # Prime → 0
acc.send(10)      # → 10
acc.send(20)      # → 30
```

**Key innovations**:
- `gen.send(value)`: resume generator, yield expression evaluates to `value`
- `gen.throw(exc)`: raise exception at yield point
- `gen.close()`: throw GeneratorExit (cleanup mechanism)
- `yield` as expression: `x = yield value` (send out AND receive)

**This enabled generator-based coroutines:**
```python
# Tornado-style (pre-async/await):
@gen.coroutine
def fetch():
    response = yield http_client.fetch("http://example.com")
    # yield suspends, event loop resumes when response ready
    # send() injects the response back
    return response.body
```

---

## 14.4 PEP 380: yield from (2009)

**Problem**: Delegating to sub-generators requires boilerplate (forward next/send/throw/close manually).

**Solution**: `yield from iterable` delegates ALL protocol operations.

```python
# Before PEP 380: manual delegation (broken!)
def delegator():
    for value in sub_gen():
        yield value  # Doesn't forward send/throw/close!

# After PEP 380: transparent delegation
def delegator():
    result = yield from sub_gen()  # Forwards EVERYTHING!
    return result
```

**yield from** handles:
- Forwarding `next()` calls to sub-generator
- Forwarding `send(value)` to sub-generator
- Forwarding `throw(exc)` to sub-generator
- Forwarding `close()` to sub-generator
- Capturing sub-generator's `return` value (→ StopIteration.value)
- Propagating sub-generator's final return as the `yield from` expression's value

**This enabled coroutine composition:**
```python
@asyncio.coroutine
def fetch_all(urls):
    results = []
    for url in urls:
        result = yield from fetch(url)  # Delegate to sub-coroutine
        results.append(result)
    return results
```

---

## 14.5 PEP 492: Native Coroutines — async/await (2015)

**Problem**: Generators serving double-duty (iteration AND coroutines) is confusing. No type distinction. Can accidentally iterate a coroutine or await a generator.

**Solution**: Separate `async def` / `await` syntax with distinct types.

```python
# Generator-based coroutine (old, PEP 342/380):
@asyncio.coroutine
def old_style():
    data = yield from some_awaitable  # Uses "yield from" for suspension
    return data

# Native coroutine (PEP 492):
async def new_style():
    data = await some_awaitable  # Clear syntax, separate type!
    return data
```

**Key changes**:
- `async def` creates a **coroutine function** (CO_COROUTINE flag)
- Calling it returns a **coroutine object** (PyCoroObject, NOT PyGenObject)
- `await expr` replaces `yield from expr` (but ONLY works in async def)
- Can't use `yield` and `await` in the same function (until PEP 525)
- `for x in coroutine` is TypeError (prevents confusion)
- `await generator` is TypeError (prevents confusion)

**Under the hood**: async/await uses the SAME frame suspension mechanism as generators! The PyCoroObject struct is nearly identical to PyGenObject. The difference is semantic/type-level, not mechanical.

---

## 14.6 PEP 525: Async Generators (2016)

**Problem**: Can't have lazy async iteration (async def + yield together).

**Solution**: Allow `yield` inside `async def` → creates an async generator.

```python
async def async_range(n):
    for i in range(n):
        await asyncio.sleep(0.01)  # Async operation
        yield i                     # Produce value lazily

async for x in async_range(10):
    print(x)
```

Creates `PyAsyncGenObject` — combines:
- Frame suspension (like generators)
- Awaitable protocol (like coroutines)
- Async iterator protocol (__aiter__, __anext__)

---

## 14.7 The Shared Mechanism

All four types use the SAME underlying frame-suspension mechanism:

```
Generator (PEP 255):     yield value → suspend frame
Enhanced Gen (PEP 342):  value = yield → suspend + receive
Coroutine (PEP 492):     await future → suspend until future ready
Async Gen (PEP 525):     yield value (inside async def) → async suspend

ALL use:
  - Frame on heap (gi_frame / cr_frame / ag_frame)
  - YIELD_VALUE / SEND opcodes
  - gen_send_ex2() for resumption
  - Same frame save/restore mechanics

The difference is TYPE (PyGen_Type vs PyCoro_Type vs PyAsyncGen_Type)
and which PROTOCOLS they implement (iterator vs awaitable vs async-iterator).
```

---

## 14.8 Interview Questions — Part 14

**Q1**: How did PEP 342 change yield? **A**: Made yield an EXPRESSION (not just statement). Added send() to inject values, throw() for exceptions, close() for cleanup. Enabled bidirectional communication needed for coroutines.

**Q2**: What does `yield from` do that a loop with yield can't? **A**: Transparently forwards send(), throw(), and close() to the sub-generator. A naive `for x in sub: yield x` only forwards next() — send/throw/close go to the wrong generator.

**Q3**: Why did Python need async/await if generators already supported coroutines? **A**: Type safety. Generator coroutines and regular generators were indistinguishable by type. You could accidentally `for x in coroutine` or `await generator`. Separate types prevent these errors.

**Q4**: How similar are PyGenObject and PyCoroObject at C level? **A**: Nearly identical. Both use _PyGenObject_HEAD macro (same fields). Both use gen_send_ex2 for execution. The difference is the type object (different protocol methods) and some extra fields on PyCoroObject.

**Q5**: What is PEP 479 about? **A**: Before PEP 479, StopIteration raised inside a generator body would silently terminate it (looked like normal exhaustion). After: it becomes RuntimeError. Prevents bugs where a sub-iterator's StopIteration accidentally ends the outer generator.
