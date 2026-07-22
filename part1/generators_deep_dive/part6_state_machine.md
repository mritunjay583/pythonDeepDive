# Part 6 — Generator State Machine

## 6.1 The Four States

```python
import inspect

def gen():
    yield 1
    yield 2

g = gen()
inspect.getgeneratorstate(g)  # 'GEN_CREATED'
next(g)
inspect.getgeneratorstate(g)  # 'GEN_SUSPENDED'
# (During execution: 'GEN_RUNNING' — can't observe easily)
next(g)
inspect.getgeneratorstate(g)  # 'GEN_SUSPENDED'
next(g)  # StopIteration
inspect.getgeneratorstate(g)  # 'GEN_CLOSED'
```

## 6.2 State Determination at C Level

```c
// Lib/inspect.py (Python) uses these checks:
// But at C level it's:

const char* get_state(PyGenObject *gen) {
    if (gen->gi_closed) return "GEN_CLOSED";
    if (gen->gi_running) return "GEN_RUNNING";
    if (gen->gi_frame == NULL) return "GEN_CLOSED";  // redundant with gi_closed
    if (gen->gi_frame->prev_instr == gen->gi_code->co_code - 1)
        return "GEN_CREATED";  // Frame exists but never entered
    return "GEN_SUSPENDED";
}
```

## 6.3 Complete Transition Diagram

```
                    gen_func(args) called
                           │
                           ▼
              ┌─────────────────────────┐
              │      GEN_CREATED        │
              │                         │
              │ gi_frame: valid         │
              │ gi_closed: False        │
              │ gi_running: False       │
              │ prev_instr: start       │
              └───────────┬─────────────┘
                          │
                          │ next(g) / g.send(None)
                          │
                          ▼
              ┌─────────────────────────┐
              │      GEN_RUNNING        │◄──────────────────────┐
              │                         │                        │
              │ gi_frame: NULL (in use) │                        │
              │ gi_closed: False        │                        │
              │ gi_running: True        │                        │
              └───┬───────────┬─────────┘                        │
                  │           │                                   │
        yield val│           │ return / unhandled exception       │
                  │           │                                   │
                  ▼           ▼                                   │
  ┌──────────────────┐  ┌──────────────────────┐                 │
  │  GEN_SUSPENDED   │  │     GEN_CLOSED       │                 │
  │                  │  │                      │                 │
  │ gi_frame: saved  │  │ gi_frame: NULL       │                 │
  │ gi_closed: False │  │ gi_closed: True      │                 │
  │ gi_running: False│  │ gi_running: False    │                 │
  └──────┬───────────┘  └──────────────────────┘                 │
         │                        ▲                               │
         │ next()/send()/throw()  │ close() or GC                │
         │                        │                               │
         └────────────────────────┴───────────────────────────────┘
              (from SUSPENDED: next/send/throw → RUNNING → yield or finish)
```

## 6.4 Transitions in Detail

### CREATED → RUNNING (first activation)
```
Trigger: next(g) or g.send(None)
Action:  gen_send_ex2 pushes None, enters eval loop from start
Note:    g.send(non_None) on CREATED raises TypeError!
         "can't send non-None value to a just-started generator"
```

### RUNNING → SUSPENDED (yield)
```
Trigger: YIELD_VALUE opcode
Action:  Save frame state, return value to caller
         gi_frame = frame, gi_running = False
```

### RUNNING → CLOSED (return / exception)
```
Trigger: RETURN_VALUE or unhandled exception
Action:  gi_frame = NULL, gi_closed = True
         Frame freed, StopIteration raised (for return)
         or exception propagates (for unhandled exception)
```

### SUSPENDED → RUNNING (resume)
```
Trigger: next(g), g.send(val), g.throw(exc)
Action:  Push value/raise exc in frame, re-enter eval loop
         gi_running = True, gi_frame = NULL (frame active)
```

### SUSPENDED → CLOSED (close)
```
Trigger: g.close() or GC finalization
Action:  Throw GeneratorExit into generator
         Generator's finally blocks run
         Then: gi_frame = NULL, gi_closed = True
```

### ANY → RUNNING (reentrant call — FORBIDDEN)
```
Trigger: next(g) while g is already RUNNING
Action:  ValueError: "generator already executing"
         gi_running check prevents corruption
```

---

## 6.5 The gi_running Guard

```python
def evil():
    global g
    next(g)  # Try to re-enter ITSELF!
    yield 1

g = evil()
next(g)  # ValueError: generator already executing
```

At C level:
```c
if (gen->gi_running) {
    PyErr_SetString(PyExc_ValueError, "generator already executing");
    return NULL;
}
```

Without this check, re-entering the generator would corrupt the frame (two execution contexts sharing one frame).

---

## 6.6 Inspecting State from Python

```python
import inspect

def gen():
    yield 1

g = gen()
print(inspect.getgeneratorstate(g))   # GEN_CREATED
print(inspect.getgeneratorlocals(g))  # {} (no locals assigned yet)

next(g)
print(inspect.getgeneratorstate(g))   # GEN_SUSPENDED
print(inspect.getgeneratorlocals(g))  # shows local variable values!

try: next(g)
except StopIteration: pass
print(inspect.getgeneratorstate(g))   # GEN_CLOSED
```

---

## 6.7 Interview Questions — Part 6

**Q1**: What are the four generator states? **A**: GEN_CREATED (never started), GEN_RUNNING (currently executing), GEN_SUSPENDED (paused at yield), GEN_CLOSED (finished/closed).

**Q2**: Can you send a non-None value to a just-created generator? **A**: No. TypeError raised. Must prime the generator with `next(g)` or `g.send(None)` first (to advance to the first yield point).

**Q3**: What prevents a generator from being re-entered while running? **A**: The `gi_running` flag. Checked at the start of gen_send_ex2. If True → ValueError.

**Q4**: What triggers the CLOSED transition? **A**: RETURN_VALUE (function body ends), unhandled exception, g.close() (throws GeneratorExit), or GC finalization of an abandoned generator.

**Q5**: How does g.close() differ from normal exhaustion? **A**: close() explicitly throws GeneratorExit into the suspended frame. This triggers finally blocks. Normal exhaustion happens when body reaches the end or explicit return — also runs finally blocks, but via normal flow.
