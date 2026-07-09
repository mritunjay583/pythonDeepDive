# Part 15 — Iteration Bytecode

## 15.1 Key Opcodes

| Opcode | Purpose |
|--------|---------|
| `GET_ITER` | Call `iter(TOS)`, replace TOS with iterator |
| `FOR_ITER` | Call `next(TOS_iter)`, push value or jump on exhaustion |
| `END_FOR` | Clean up after loop (pop iterator) |
| `YIELD_VALUE` | Suspend generator, return value to caller |
| `RETURN_GENERATOR` | Create generator object from current frame |
| `SEND` | Resume generator with a value (gen.send()) |
| `GET_YIELD_FROM_ITER` | Get iterator for `yield from` |

## 15.2 For Loop Bytecode

```python
for x in [1, 2, 3]:
    print(x)
```

```
LOAD_CONST          (1, 2, 3)   ← Or BUILD_LIST for [1,2,3]
GET_ITER                         ← iter([1,2,3]) → list_iterator
FOR_ITER            12 (to END)  ← next(iter) → push value or jump
STORE_FAST          x            ← x = value
LOAD_GLOBAL         print
LOAD_FAST           x
CALL                1
POP_TOP
JUMP_BACKWARD       (to FOR_ITER)
END_FOR                          ← Pop exhausted iterator
```

## 15.3 Generator Function Bytecode

```python
def gen():
    yield 1
    yield 2
```

```
# Calling gen() produces:
RETURN_GENERATOR              ← Creates PyGenObject, attaches frame, returns it
                               (body NOT executed yet!)

# Body (executed on each next()):
RESUME          0
LOAD_CONST      1 (1)
YIELD_VALUE     1             ← Suspend, return 1 to caller
RESUME          1             ← Resume point after first yield
LOAD_CONST      2 (2)
YIELD_VALUE     1             ← Suspend, return 2 to caller
RESUME          1
LOAD_CONST      None
RETURN_VALUE                  ← End → StopIteration
```

## 15.4 yield from Bytecode

```python
def delegator():
    result = yield from sub_gen()
```

```
LOAD_GLOBAL       sub_gen
CALL              0
GET_YIELD_FROM_ITER           ← Ensure it's an iterator
LOAD_CONST        None        ← Initial send value
SEND              <exit>      ← Send to sub-generator, get result or jump
YIELD_VALUE                   ← Yield sub-gen's value to OUR caller
JUMP_BACKWARD     <SEND>      ← Loop back for next value from sub-gen
<exit>:
STORE_FAST        result      ← Sub-gen's return value
```

## 15.5 Generator Expression Bytecode

```python
gen = (x**2 for x in items)
```

Compiles to:
```
# At creation point:
LOAD_FAST         items
GET_ITER                      ← iter(items)
LOAD_CONST        <code object <genexpr>>
MAKE_FUNCTION     0
CALL              1           ← Call genexpr function with iterator
STORE_FAST        gen         ← Store resulting generator

# Inside <genexpr> code object:
RETURN_GENERATOR              ← Create generator, don't execute
RESUME
FOR_ITER          <end>       ← Iterate over the passed-in iterator
STORE_FAST        x
LOAD_FAST         x
LOAD_CONST        2
BINARY_OP         **
YIELD_VALUE                   ← Yield x**2
RESUME
JUMP_BACKWARD     <FOR_ITER>
<end>:
END_FOR
LOAD_CONST        None
RETURN_VALUE
```

## 15.6 Interview Questions — Part 15

**Q1**: What opcode starts iteration in a for loop? **A**: GET_ITER — calls iter() on the iterable, replaces it on the stack with the resulting iterator.

**Q2**: What does RETURN_GENERATOR do? **A**: Creates a PyGenObject wrapping the current frame and returns it WITHOUT executing the body. The caller gets the generator object.

**Q3**: How does YIELD_VALUE suspend execution? **A**: Saves frame state (instruction pointer, stack) into the generator object, pops frame from call stack, returns the yielded value.

**Q4**: What is SEND used for? **A**: Implements `gen.send(value)`. Pushes value onto the generator's stack (becomes the yield expression's result) and resumes execution.
