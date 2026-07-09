# Part 5 — Bytecode Fundamentals

## 5.1 The Stack Machine Model

CPython's VM is a **stack-based** machine. All operations work on an operand stack:

```
Instruction      Stack Before    Stack After      Operation
─────────────────────────────────────────────────────────────
LOAD_CONST 42    [...]           [..., 42]        Push constant
LOAD_FAST 0      [...]           [..., x]         Push local var
BINARY_OP ADD    [..., a, b]     [..., a+b]       Pop 2, push result
STORE_FAST 1     [..., val]      [...]            Pop, store to local
RETURN_VALUE     [..., val]      (frame exits)    Pop, return to caller
```

### Why Stack-Based (not Register-Based)?

| Aspect | Stack VM (CPython) | Register VM (Lua, Dalvik) |
|--------|-------------------|--------------------------|
| Instruction size | Small (opcode + 1 arg) | Larger (opcode + 2-3 reg args) |
| Code density | Higher (compact) | Lower (more bits per instruction) |
| Dispatch overhead | More instructions | Fewer instructions |
| Implementation | Simpler compiler | More complex register allocation |
| Performance | Adequate for interpreter | Better for JIT |

CPython chose stack-based for simplicity — the compiler doesn't need register allocation, which is a hard optimization problem.

---

## 5.2 Instruction Format

Since Python 3.6, all instructions are **2 bytes** (word-code, not byte-code):

```
┌─────────┬─────────┐
│ opcode  │   arg   │    2 bytes per instruction
│ (1 byte)│(1 byte) │
└─────────┴─────────┘

For arguments > 255: EXTENDED_ARG prefix:
┌──────────────┬──────┐ ┌─────────┬──────┐
│ EXTENDED_ARG │ high │ │ opcode  │ low  │    4 bytes (extended)
└──────────────┴──────┘ └─────────┴──────┘
Effective arg = (high << 8) | low
```

---

## 5.3 Key Opcode Categories

### Load/Store Operations:
```python
LOAD_CONST i        # Push co_consts[i]
LOAD_FAST i         # Push localsplus[i] (local variable)
STORE_FAST i        # Pop → localsplus[i]
LOAD_GLOBAL i       # Push globals[co_names[i]] (or builtins)
STORE_GLOBAL i      # Pop → globals[co_names[i]]
LOAD_DEREF i        # Push cell.ob_ref (closure variable)
STORE_DEREF i       # Pop → cell.ob_ref
LOAD_ATTR i         # Pop obj → push obj.co_names[i]
STORE_ATTR i        # Pop val, pop obj → obj.co_names[i] = val
```

### Arithmetic/Binary:
```python
BINARY_OP op        # Pop b, pop a → push a <op> b
  # op: 0=+, 1=&, 2=^, 5=*, 6=-, 10=//, 11=/, ...
UNARY_NEGATIVE      # Pop a → push -a
UNARY_NOT           # Pop a → push not a
COMPARE_OP op       # Pop b, pop a → push a <cmp> b
```

### Control Flow:
```python
JUMP_FORWARD off    # Unconditional jump: ip += off
JUMP_BACKWARD off   # Unconditional back-jump: ip -= off  
POP_JUMP_IF_TRUE t  # Pop, jump if truthy
POP_JUMP_IF_FALSE t # Pop, jump if falsy
FOR_ITER off        # Advance iterator or jump (end of loop)
```

### Function Calls:
```python
CALL n              # Call callable with n args from stack
RETURN_VALUE        # Return TOS to caller
MAKE_FUNCTION flags # Create function object from code object
```

### Collection Operations:
```python
BUILD_LIST n        # Pop n items → push list
BUILD_TUPLE n       # Pop n items → push tuple
BUILD_MAP n         # Pop 2n items (k,v pairs) → push dict
LIST_APPEND i       # Append TOS to list at stack[i] (comprehensions)
```

---

## 5.4 The Operand Stack In Action

```python
def example(x, y):
    z = x + y * 2
    return z
```

```
Bytecode          Stack State              Notes
─────────────────────────────────────────────────────────
RESUME 0          []                       Entry
LOAD_FAST 0       [x]                      Push local 'x'
LOAD_FAST 1       [x, y]                   Push local 'y'
LOAD_CONST 1      [x, y, 2]               Push constant 2
BINARY_OP MUL     [x, y*2]                 Pop 2, push product
BINARY_OP ADD     [x+y*2]                  Pop 2, push sum
STORE_FAST 2      []                       Pop → local 'z'
LOAD_FAST 2       [z]                      Push 'z'
RETURN_VALUE      (returns z)              Pop, return to caller
```

---

## 5.5 Local Variables: Fast Locals

Local variables are stored in a C array (`localsplus[]`), NOT in a dict:

```
Frame's localsplus array:
┌─────────┬─────────┬─────────┬───────────────────────────┐
│ local 0 │ local 1 │ local 2 │ ... │ stack[0] │ stack[1] │
│  (x)    │  (y)    │  (z)    │     │          │          │
└─────────┴─────────┴─────────┴───────────────────────────┘
← co_nlocals + co_ncellvars + co_nfreevars →← co_stacksize →

LOAD_FAST 0 → push localsplus[0] (O(1) array access!)
STORE_FAST 2 → localsplus[2] = popped_value (O(1)!)
```

This is **much faster** than dict lookup (LOAD_NAME/LOAD_GLOBAL):
- Array access: 1 pointer dereference + offset computation
- Dict lookup: hash computation + probing + comparison

That's why function locals are fast (hence "FAST" in the opcode name) and why accessing `x` inside a function is faster than accessing `x` at module level.

---

## 5.6 Global Variables

```python
LOAD_GLOBAL name_index
```

Implementation:
```c
// Simplified:
PyObject *name = co_names[name_index];
PyObject *value = PyDict_GetItem(f_globals, name);  // Try globals first
if (value == NULL)
    value = PyDict_GetItem(f_builtins, name);       // Then builtins
if (value == NULL)
    raise NameError(name);
PUSH(value);
```

Two dict lookups in the worst case (globals miss → try builtins). This is why global access is slower than local.

---

## 5.7 Using the dis Module

```python
import dis

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

dis.dis(fibonacci)
```

Output:
```
  2           0 RESUME                   0

  3           2 LOAD_FAST                0 (n)
              4 LOAD_CONST               1 (1)
              6 COMPARE_OP              68 (<=)
             10 POP_JUMP_IF_FALSE        1 (to 14)

  4          12 LOAD_FAST                0 (n)
             14 RETURN_VALUE

  5     >>   16 LOAD_GLOBAL              1 (fibonacci + NULL)
             26 LOAD_FAST                0 (n)
             28 LOAD_CONST               1 (1)
             30 BINARY_OP                10 (-)
             34 CALL                     1
             42 LOAD_GLOBAL              1 (fibonacci + NULL)
             52 LOAD_FAST                0 (n)
             54 LOAD_CONST               2 (2)
             56 BINARY_OP                10 (-)
             60 CALL                     1
             68 BINARY_OP                0 (+)
             72 RETURN_VALUE
```

Reading dis output: `offset OPCODE arg (human_readable_arg)`

---

## 5.8 Bytecode Object Inspection

```python
import dis, opcode

def add(x, y):
    return x + y

code = add.__code__
raw = code.co_code  # Raw bytes

# Manual disassembly:
i = 0
while i < len(raw):
    op = raw[i]
    arg = raw[i + 1]
    name = opcode.opname[op]
    print(f"  {i:4d} {name:20s} {arg}")
    i += 2

# Structured disassembly:
for instr in dis.get_instructions(add):
    print(f"  {instr.offset:4d} {instr.opname:20s} {instr.argval}")
```

---

## 5.9 Interview Questions — Part 5

**Q1**: Is CPython's VM stack-based or register-based?
**A**: Stack-based. All operations push/pop from an operand stack. No named registers. This simplifies the compiler (no register allocation needed).

**Q2**: How big is each bytecode instruction?
**A**: 2 bytes (1 byte opcode + 1 byte argument). For arguments > 255, EXTENDED_ARG prefix adds 2 more bytes.

**Q3**: Why is LOAD_FAST faster than LOAD_GLOBAL?
**A**: LOAD_FAST is an O(1) array index into `localsplus[]`. LOAD_GLOBAL requires a dict lookup in globals (and possibly builtins) — hash computation + probing.

**Q4**: What is co_stacksize?
**A**: The maximum number of items that will be on the operand stack at any point during execution. The compiler computes this statically.

**Q5**: What does BINARY_OP do?
**A**: Pops two operands from the stack, performs the specified operation (the arg selects +, -, *, /, etc.), pushes the result.
