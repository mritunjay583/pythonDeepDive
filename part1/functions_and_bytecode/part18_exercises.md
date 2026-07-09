# Part 18 — Exercises: Memory Tracing, Opcode Tracing, Frame Tracing

## Section A: Opcode Execution Tracing (10 Exercises)

### Exercise 1
Trace the operand stack step by step:
```python
def f(a, b):
    c = a + b * 2
    return c

f(3, 4)
```
**Answer:**
```
Locals: [a=3, b=4, c=NULL]
IP  Opcode         Stack        Notes
0   RESUME         []
2   LOAD_FAST 0    [3]          push a
4   LOAD_FAST 1    [3, 4]       push b
6   LOAD_CONST 1   [3, 4, 2]    push 2
8   BINARY_OP *    [3, 8]       4*2=8
12  BINARY_OP +    [11]         3+8=11
16  STORE_FAST 2   []           c=11
18  LOAD_FAST 2    [11]         push c
20  RETURN_VALUE   → 11         return 11
```

### Exercise 2
Trace execution for a conditional:
```python
def abs_val(x):
    if x < 0:
        return -x
    return x

abs_val(-5)
```
**Answer:**
```
Locals: [x=-5]
0  RESUME         []
2  LOAD_FAST 0    [-5]
4  LOAD_CONST 1   [-5, 0]
6  COMPARE_OP <   [True]         -5 < 0 → True
10 POP_JUMP_IF_FALSE 16  []      True → don't jump
12 LOAD_FAST 0    [-5]
14 UNARY_NEGATIVE [5]            -(-5) = 5
16 RETURN_VALUE   → 5
```

### Exercise 3
Trace a loop:
```python
def sum_to(n):
    total = 0
    for i in range(n):
        total += i
    return total

sum_to(3)
```
**Answer:** Trace through: total=0, i=0 (total=0), i=1 (total=1), i=2 (total=3), FOR_ITER exhausted, return 3.

---

## Section B: Frame Tracing (5 Exercises)

### Exercise 4
Draw the call stack during execution of:
```python
def a(x):
    return b(x + 1)

def b(y):
    return c(y + 1)

def c(z):
    return z + 1

result = a(1)
```
**At the deepest point (inside c):**
```
Frame c: locals=[z=3], stack=[]
  ↑ caller
Frame b: locals=[y=2], stack=[waiting for c's return]
  ↑ caller  
Frame a: locals=[x=1], stack=[waiting for b's return]
  ↑ caller
Frame <module>: globals={a, b, c, result=...}
```
**Result:** c returns 4, b returns 4, a returns 4, result = 4.

### Exercise 5
Trace the creation and destruction of frames:
```python
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

factorial(4)
```
**Answer:**
```
Frame 1: factorial(4) → calls factorial(3)
Frame 2: factorial(3) → calls factorial(2)
Frame 3: factorial(2) → calls factorial(1)
Frame 4: factorial(1) → returns 1 (frame destroyed)
Frame 3: computes 2*1=2 → returns 2 (destroyed)
Frame 2: computes 3*2=6 → returns 6 (destroyed)
Frame 1: computes 4*6=24 → returns 24 (destroyed)
Result: 24
```

---

## Section C: Closure and Cell Tracing (5 Exercises)

### Exercise 6
Trace the cell object lifecycle:
```python
def make_adder(n):
    def adder(x):
        return x + n
    return adder

add5 = make_adder(5)
add5(3)  # ?
add5(7)  # ?
```
**Answer:**
```
make_adder(5):
  Cell created for 'n', cell.ob_ref = 5
  adder function created with func_closure = (cell,)
  Frame destroyed. Cell survives (held by adder's closure).

add5(3):
  Frame for adder: localsplus = [x=3, cell_for_n]
  LOAD_FAST 0 → push 3
  LOAD_DEREF 0 → read cell.ob_ref → push 5
  BINARY_OP + → push 8
  RETURN_VALUE → 8

add5(7):
  Same cell (ob_ref still = 5)
  7 + 5 = 12
```

### Exercise 7
Trace the closure-in-loop trap:
```python
funcs = []
for i in range(3):
    funcs.append(lambda: i)

[f() for f in funcs]  # What values?
```
**Answer:** All return `2`. One cell for `i`, final value `2`. All lambdas share it.

### Exercise 8
Trace `nonlocal` modification:
```python
def counter():
    n = 0
    def inc():
        nonlocal n
        n += 1
        return n
    return inc

c = counter()
c()  # ?
c()  # ?
c()  # ?
```
**Answer:** `1, 2, 3`. The cell's ob_ref is updated each time: 0→1→2→3.

---

## Section D: Compiler Exercises (5 Exercises)

### Exercise 9
Predict co_varnames, co_cellvars, co_freevars for:
```python
def outer(a, b):
    c = a + b
    def inner(d):
        return c + d
    return inner
```
**Answer:**
```
outer: co_varnames=('a','b','inner'), co_cellvars=('c',), co_freevars=()
inner: co_varnames=('d',), co_cellvars=(), co_freevars=('c',)
Note: 'a' and 'b' are in varnames (not captured), 'c' is captured → cell.
```

### Exercise 10
What constant folding happens?
```python
def f():
    x = 2 ** 10
    y = "hello" + " " + "world"
    z = (1, 2, 3) + (4, 5)
    return x, y, z
```
**Answer:**
```
co_consts includes:
  1024 (2**10 folded)
  "hello world" ("hello" + " " + "world" folded)
  (1, 2, 3, 4, 5) (tuple concat folded)
No BINARY_OP in bytecode for these — all LOAD_CONST!
```

### Exercise 11
Predict what happens with dead code:
```python
def f(x):
    return x
    print("unreachable")
```
**Answer:** In 3.12+: the `print("unreachable")` is eliminated entirely. The bytecode only contains `LOAD_FAST x; RETURN_VALUE`.

### Exercise 12
Determine the scoping for each name:
```python
x = "global"
def outer():
    y = "outer_local"
    def inner():
        z = "inner_local"
        print(x, y, z)
    return inner
```
**Answer:**
```
In inner():
  x → GLOBAL (accessed via LOAD_GLOBAL, not captured)
  y → FREE (captured from outer via cell → LOAD_DEREF)
  z → LOCAL (assigned here → LOAD_FAST)
  print → GLOBAL (LOAD_GLOBAL)
```

### Exercise 13
Predict `co_stacksize` for:
```python
def f(a, b, c, d):
    return (a + b) * (c + d)
```
**Answer:**
```
LOAD_FAST a     [a]           depth 1
LOAD_FAST b     [a, b]        depth 2
BINARY_OP +     [a+b]         depth 1
LOAD_FAST c     [a+b, c]      depth 2
LOAD_FAST d     [a+b, c, d]   depth 3 ← MAXIMUM
BINARY_OP +     [a+b, c+d]    depth 2
BINARY_OP *     [result]      depth 1
RETURN_VALUE

co_stacksize = 3
```
