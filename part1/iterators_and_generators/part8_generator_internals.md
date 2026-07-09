# Part 8 — Generator Internals

## 8.1 PyGenObject Structure

```c
// Include/cpython/genobject.h
typedef struct {
    PyObject_HEAD                    // 16 bytes
    PyObject *gi_name;              // Generator name (__name__)
    PyObject *gi_qualname;          // Qualified name (__qualname__)
    _PyInterpreterFrame *gi_frame;  // Suspended frame (NULL when running/closed)
    PyObject *gi_code;              // Code object
    PyObject *gi_weakreflist;       // Weak references
    PyObject *gi_exc_state;         // Saved exception state
    char gi_hooks_inited;           // Profile/trace hooks initialized
    char gi_closed;                 // True if generator is closed
    char gi_running_async;          // True if running in async context
} PyGenObject;
// ~112 bytes + the frame allocation
```

---

## 8.2 Frame Preservation Mechanism

When a generator yields:
```c
// Inside YIELD_VALUE opcode handler (simplified):
case YIELD_VALUE: {
    PyObject *retval = POP();        // Get the yielded value
    
    // Save frame state:
    frame->prev_instr = next_instr - 1;  // Save instruction pointer
    frame->stacktop = stack_pointer;      // Save stack pointer
    
    // Return to caller with the yielded value:
    tstate->current_frame = frame->previous;  // Pop this frame
    gen->gi_frame = frame;                     // Store frame in generator
    return retval;                             // Return to whoever called next()
}
```

When next(gen) is called to resume:
```c
// gen_send_ex (Objects/genobject.c simplified):
static PyObject *
gen_send_ex(PyGenObject *gen, PyObject *arg)
{
    _PyInterpreterFrame *frame = gen->gi_frame;
    
    // Push the sent value onto the generator's stack:
    // (this becomes the result of the `yield` expression)
    frame->localsplus[frame->stacktop++] = arg;
    
    // Resume execution:
    gen->gi_frame = NULL;  // Mark as running (frame not "saved" anymore)
    tstate->current_frame = frame;  // Push frame back as active
    
    result = _PyEval_EvalFrame(tstate, frame);
    
    // After generator yields/returns:
    if (result == NULL) {
        // Generator returned or raised → closed
        gen->gi_closed = 1;
    }
    return result;
}
```

---

## 8.3 Memory Layout When Suspended

```python
def counter(start):
    n = start
    while True:
        yield n
        n += 1

c = counter(10)
next(c)  # 10
next(c)  # 11
# Now suspended: n=12, about to yield again
```

```
PyGenObject 'c':
├── gi_name: "counter"
├── gi_code: <code object counter>
├── gi_frame ──→ _PyInterpreterFrame
│                ├── f_code → counter's code
│                ├── prev_instr → YIELD_VALUE instruction
│                ├── localsplus:
│                │   [0] start = 10  (parameter, unchanged)
│                │   [1] n = 12      (local variable, current state!)
│                │   [stack...] = []  (operand stack empty at yield point)
│                └── stacktop = (points to stack base)
├── gi_closed: False
└── gi_running: False (not currently executing)
```

The entire function's state — local variables, instruction position, operand stack — is frozen in the frame. Resuming just continues from where it stopped.

---

## 8.4 Generator Lifecycle at C Level

```
1. CALL gen_func  →  RETURN_GENERATOR opcode
   - Creates PyGenObject
   - Attaches the frame (with args bound to locals)
   - Returns the generator WITHOUT executing body
   
2. next(gen) → gen_send_ex(gen, Py_None)
   - Pushes frame as current
   - Resumes execution at prev_instr + 1
   - Runs until YIELD_VALUE or RETURN_VALUE
   
3. YIELD_VALUE → saves frame, returns value to caller
   - gen->gi_frame = frame (save)
   - Returns yielded value
   
4. RETURN_VALUE → closes generator
   - gen->gi_closed = True
   - gen->gi_frame = NULL (frame freed)
   - Raises StopIteration (with .value = returned value)
   
5. gen.close() → gen_close(gen)
   - Throws GeneratorExit into the generator
   - Generator's finally blocks execute
   - Generator is marked closed
   
6. GC collects gen → gen_dealloc
   - If frame exists (not closed): gen.close() called first
   - Frame deallocated
   - Generator object freed
```

---

## 8.5 RETURN_GENERATOR Opcode (Python 3.12+)

```c
// When a generator function is CALLED:
case RETURN_GENERATOR: {
    PyGenObject *gen = (PyGenObject *)_Py_MakeCoro(func);
    // gen->gi_frame = current frame (detached from C stack)
    // Return gen to caller (don't execute body!)
    
    // The frame stays allocated but is NOT on the active call stack
    // It's owned by the generator object
    RETURN_VALUE(gen);
}
```

This replaced the old mechanism where calling a generator function would enter the frame and immediately return. Now it's cleaner: the frame is created and immediately handed to the generator object.

---

## 8.6 Generator Finalization (GC Interaction)

```python
def leaky():
    f = open("file.txt")
    try:
        for line in f:
            yield line
    finally:
        f.close()  # CRITICAL: must run even if generator is abandoned!

gen = leaky()
next(gen)       # Opens file, yields first line
# If gen is garbage collected without being closed:
# The GC calls gen.close() → triggers finally → f.close()
# Resource is properly cleaned up!
```

```c
// gen_dealloc:
static void gen_dealloc(PyGenObject *gen) {
    if (gen->gi_frame != NULL) {
        // Generator was abandoned while suspended!
        // Must run finally blocks:
        gen_close(gen);  // Throws GeneratorExit into generator
    }
    // Now safe to free
    Py_XDECREF(gen->gi_code);
    // ... free frame memory ...
    PyObject_GC_Del(gen);
}
```

---

## 8.7 Performance Characteristics

```python
# Generator overhead per yield/resume cycle:
# - Save/restore frame state: ~50ns
# - Function call to gen_send_ex: ~30ns
# - Frame push/pop: ~20ns
# Total: ~100-200ns per yield

# Compare to list iteration:
# - list_iterator.__next__: ~30ns (just index++)
# Generators are ~3-5× slower PER ITERATION than list iterators

# But generators WIN on memory:
# list(range(1M)): 8 MB
# generator yielding 1M items: ~200 bytes (generator + frame)
```

---

## 8.8 Interview Questions — Part 8

**Q1**: What C structure represents a generator? **A**: PyGenObject (~112 bytes). Contains gi_frame (the suspended execution frame), gi_code, gi_name, gi_closed, gi_running flags.

**Q2**: Where does a generator's execution state live between yields? **A**: In the gi_frame (_PyInterpreterFrame on the heap). Contains: instruction pointer (prev_instr), local variables (localsplus), and operand stack state.

**Q3**: What happens when a generator object is garbage collected while suspended? **A**: GC calls gen.close() which throws GeneratorExit into the generator. This triggers any finally blocks, ensuring resource cleanup.

**Q4**: How does YIELD_VALUE work at the C level? **A**: Pops the yielded value from the operand stack, saves the frame state (instruction pointer + stack pointer) into the generator object, pops the frame from the active call stack, and returns the value to the caller of next().

**Q5**: Why are generators slower per-element than list iteration? **A**: Each yield requires: saving frame state, returning from eval loop, then on resume: restoring frame, re-entering eval loop. List iteration is just an index increment + pointer dereference. ~3-5× overhead.
