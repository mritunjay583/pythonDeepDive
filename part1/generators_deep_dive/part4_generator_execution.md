# Part 4 — Generator Execution: Step by Step

## 4.1 First next() — Starting Execution

```python
def gen():
    x = 10
    yield x
    x += 5
    yield x

g = gen()       # GEN_CREATED (body not started)
val = next(g)   # What happens here?
```

### C-level flow:

```
1. Python: next(g)
2. → builtin_next() → calls g.__next__()
3. → PyGen_Type.tp_iternext → gen_iternext(g)
4. → gen_send_ex2(g, Py_None, 0, 0)

Inside gen_send_ex2:
5. Check: gi_frame != NULL? YES (not closed)
6. Check: gi_running? NO (not reentrant)
7. Push Py_None onto frame's operand stack
   (first next() sends None as "yield result" — but body hasn't reached yield yet)
8. gen->gi_running = 1
9. gen->gi_frame = NULL (frame now "in use")
10. tstate->current_frame = gen's frame (push onto call stack)
11. Call _PyEval_EvalFrame(frame)

Inside eval loop:
12. RESUME 1 — no-op (marks re-entry point)
13. POP_TOP — discard the None that was pushed (no yield expr to receive it)
14. LOAD_CONST 10 → stack: [10]
15. STORE_FAST x → localsplus[0] = 10, stack: []
16. LOAD_FAST x → stack: [10]
17. YIELD_VALUE:
    - Pop 10 from stack
    - Save frame (prev_instr = this YIELD_VALUE)
    - gen->gi_frame = frame (save back)
    - tstate->current_frame = caller's frame
    - Return 10

Back in gen_send_ex2:
18. gen->gi_running = 0
19. result = 10 (not NULL → generator yielded, not returned)
20. Return 10 to caller

Result: val = 10, generator is GEN_SUSPENDED
```

---

## 4.2 Second next() — Resuming After Yield

```python
val2 = next(g)  # Resume after first yield
```

```
1-6. Same setup as before (gen_send_ex2, push None)
7. Push None onto generator's stack
   (This None becomes the result of `yield x` expression — discarded here)

Inside eval loop:
8. Resumes at instruction AFTER the first YIELD_VALUE
9. RESUME 1 — marks re-entry
10. POP_TOP — discard the None (yield expr result unused)
11. LOAD_FAST x → stack: [10]
12. LOAD_CONST 5 → stack: [10, 5]
13. BINARY_OP += → stack: [15]
14. STORE_FAST x → localsplus[0] = 15, stack: []
15. LOAD_FAST x → stack: [15]
16. YIELD_VALUE:
    - Pop 15, save frame, return 15

Result: val2 = 15, generator still GEN_SUSPENDED
```

---

## 4.3 Final next() — Exhaustion

```python
val3 = next(g)  # Attempt to get third value
```

```
Inside eval loop (resumes after second yield):
1. RESUME, POP_TOP (discard None)
2. LOAD_CONST None → stack: [None]  (implicit return None)
3. RETURN_VALUE:
   - Pops None
   - Sets StopIteration exception (with value=None)
   - Returns NULL to gen_send_ex2

Back in gen_send_ex2:
4. result = NULL → generator returned/raised
5. gen->gi_frame = NULL (frame freed!)
6. gen->gi_closed = 1
7. StopIteration is set → propagates to caller

Result: StopIteration raised, generator is GEN_CLOSED
Any future next(g) immediately raises StopIteration (gi_frame == NULL check)
```

---

## 4.4 Complete Trace with Operand Stack

```python
def adder(a, b):
    c = a + b
    yield c
    yield c * 2
```

| Step | Instruction | Stack | Locals [a,b,c] | Action |
|------|-------------|-------|-----------------|--------|
| — | (creation) | [] | [3, 4, NULL] | Frame created, args bound |
| 1 | RESUME 1 | [] | [3, 4, NULL] | First next() entry |
| 2 | POP_TOP | [] | [3, 4, NULL] | Discard None |
| 3 | LOAD_FAST 0 | [3] | [3, 4, NULL] | Push a |
| 4 | LOAD_FAST 1 | [3, 4] | [3, 4, NULL] | Push b |
| 5 | BINARY_OP + | [7] | [3, 4, NULL] | 3+4=7 |
| 6 | STORE_FAST 2 | [] | [3, 4, 7] | c = 7 |
| 7 | LOAD_FAST 2 | [7] | [3, 4, 7] | Push c |
| 8 | YIELD_VALUE | **suspended** | [3, 4, 7] | **Returns 7 to caller** |
| — | (second next) | [] | [3, 4, 7] | Resume |
| 9 | RESUME 1 | [None] | [3, 4, 7] | None pushed by send |
| 10 | POP_TOP | [] | [3, 4, 7] | Discard None |
| 11 | LOAD_FAST 2 | [7] | [3, 4, 7] | Push c |
| 12 | LOAD_CONST 2 | [7, 2] | [3, 4, 7] | Push 2 |
| 13 | BINARY_OP * | [14] | [3, 4, 7] | 7*2=14 |
| 14 | YIELD_VALUE | **suspended** | [3, 4, 7] | **Returns 14** |
| — | (third next) | | | |
| 15 | LOAD_CONST None | [None] | [3, 4, 7] | |
| 16 | RETURN_VALUE | — | — | **StopIteration** |

---

## 4.5 The send(value) Difference

```python
def echo():
    received = yield "ready"
    yield f"got: {received}"

g = echo()
print(next(g))          # "ready"
print(g.send("hello"))  # "got: hello"
```

The difference: `send("hello")` pushes `"hello"` (not None) onto the stack before resume. So when the generator resumes after `yield "ready"`, the yield EXPRESSION evaluates to `"hello"` instead of `None`:

```
Step 8 resumed with send("hello"):
  Stack before RESUME: ["hello"]  ← send pushed this!
  POP_TOP?? NO! Here 'received = yield ...' uses the value!
  STORE_FAST received → received = "hello"
```

---

## 4.6 Interview Questions — Part 4

**Q1**: What does the first next() on a fresh generator do? **A**: Enters gen_send_ex2 with arg=None, pushes None onto generator stack, re-enters the eval loop. Executes body from the beginning (after RETURN_GENERATOR/RESUME) until the first YIELD_VALUE. Returns the yielded value.

**Q2**: What value does `yield x` expression evaluate to when resumed with next()? **A**: None. next(g) is equivalent to g.send(None). The None is pushed onto the stack and becomes the yield expression's result.

**Q3**: What happens at RETURN_VALUE in a generator? **A**: Sets StopIteration exception (with value = the returned value), returns NULL to gen_send_ex2, which sets gi_frame=NULL and gi_closed=True. The generator is permanently closed.

**Q4**: Can you observe partially-evaluated expressions across a yield? **A**: Yes! The operand stack is preserved. If `yield` is inside `a + (yield b)`, the `a` is already on the stack when yield suspends. On resume, computation continues with `a` still there.

**Q5**: What's the cost of each next() call? **A**: gen_send_ex2 overhead (~30ns) + frame push/resume (~50ns) + bytecode execution (varies) + yield save/return (~50ns) ≈ 130ns minimum overhead per yield, plus the actual computation.
