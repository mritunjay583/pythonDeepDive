# Part 2 — Closures and Nested Functions

## 2.1 The Problem Closures Solve

```python
def make_counter():
    count = 0
    def increment():
        nonlocal count
        count += 1
        return count
    return increment

counter = make_counter()
counter()  # 1
counter()  # 2
counter()  # 3
# How does increment() access 'count' after make_counter() has returned?
# make_counter's frame is gone! Where does 'count' live?
```

The local variable `count` outlives the function that created it. CPython solves this with **cell objects**.

---

## 2.2 Cell Objects

A **cell object** is a tiny wrapper that holds a reference to a value:

```c
// Include/cpython/cellobject.h
typedef struct {
    PyObject_HEAD           // ob_refcnt + ob_type (16 bytes)
    PyObject *ob_ref;       // Pointer to the contained value (8 bytes)
} PyCellObject;
```

Size: 24 bytes (just a header + one pointer).

The cell is an extra level of indirection:
```
WITHOUT cell (normal local):
  fast_locals[i] → value_object

WITH cell (closure variable):
  fast_locals[i] → CellObject → value_object
                   (lives on heap, survives frame destruction)
```

---

## 2.3 How Closures Work Step by Step

```python
def make_counter():
    count = 0               # 'count' identified as CELL variable
    def increment():
        nonlocal count
        count += 1          # 'count' is FREE variable here
        return count
    return increment
```

### At Compile Time:

The compiler's symbol table analysis identifies:
- `make_counter`: `count` is a **cell variable** (referenced by inner function)
- `increment`: `count` is a **free variable** (comes from enclosing scope)

```
make_counter's code object:
  co_cellvars = ('count',)    ← variables captured by inner functions
  co_varnames = ()            ← count is NOT in varnames (it's a cell)

increment's code object:
  co_freevars = ('count',)    ← variables from enclosing scope
  co_varnames = ()
```

### At Runtime (make_counter() called):

```
Step 1: Frame created for make_counter
  localsplus = [cell_for_count]  ← CellObject created
  cell_for_count.ob_ref = NULL (not yet assigned)

Step 2: count = 0
  Bytecode: LOAD_CONST 0 (int 0)
            STORE_DEREF 0 (count)
  → cell_for_count.ob_ref = int(0)

Step 3: def increment(): ... (MAKE_FUNCTION with closure)
  Bytecode: LOAD_CLOSURE 0 (count's cell)    ← push cell object
            BUILD_TUPLE 1                     ← (cell,)
            LOAD_CONST <code for increment>
            MAKE_FUNCTION 8                   ← 8 = has closure
  → Creates PyFunctionObject with func_closure = (cell_for_count,)

Step 4: return increment
  → Returns the function object. make_counter's frame is destroyed.
  → BUT: cell_for_count still alive (refcount > 0: held by func_closure)
```

### Memory After make_counter() Returns:

```
'counter' ──→ PyFunctionObject (increment)
               │
               ├── func_code ──→ PyCodeObject (increment's bytecode)
               │                   co_freevars = ('count',)
               │
               └── func_closure ──→ tuple: (cell_obj,)
                                            │
                                            ▼
                                     PyCellObject
                                       ob_ref ──→ int(0)
                                       
make_counter's frame: DESTROYED (gone!)
But the cell survives because func_closure holds a reference to it.
```

### When counter() is Called:

```
Step 1: Frame created for increment
  The cell from func_closure is placed in the frame's localsplus
  at the position for free variable 'count'

Step 2: count += 1
  LOAD_DEREF 0          → reads cell.ob_ref → gets int(0) → pushes
  LOAD_CONST 1 (int 1)  → pushes int(1)
  BINARY_OP ADD          → pushes int(1) (0+1)
  STORE_DEREF 0         → cell.ob_ref = int(1)  ← updates the cell!

Step 3: return count
  LOAD_DEREF 0          → reads cell.ob_ref → gets int(1)
  RETURN_VALUE
```

---

## 2.4 LOAD_DEREF and STORE_DEREF

```c
// Python/ceval.c (simplified)
case LOAD_DEREF: {
    PyObject *cell = GETLOCAL(oparg);  // Get the cell from localsplus
    PyObject *value = PyCell_GET(cell); // Read cell->ob_ref
    if (value == NULL) {
        // UnboundLocalError or NameError
    }
    Py_INCREF(value);
    PUSH(value);
    break;
}

case STORE_DEREF: {
    PyObject *cell = GETLOCAL(oparg);
    PyObject *value = POP();
    PyObject *old = PyCell_GET(cell);
    PyCell_SET(cell, value);    // cell->ob_ref = value
    Py_XDECREF(old);           // Release old value
    break;
}
```

The key insight: LOAD_DEREF/STORE_DEREF go through the **cell indirection**. The cell's `ob_ref` can be updated, and all functions sharing that cell see the new value.

---

## 2.5 Multiple Closures Sharing a Cell

```python
def make_pair():
    value = 0
    def getter():
        return value
    def setter(x):
        nonlocal value
        value = x
    return getter, setter

get, set = make_pair()
set(42)
get()  # 42 — both share the SAME cell!
```

```
get.func_closure ──→ (cell_obj,) ──┐
                                    │
                                    ▼
                              PyCellObject
                                ob_ref → int(42)
                                    ↑
                                    │
set.func_closure ──→ (cell_obj,) ──┘

SAME cell object shared by both closures!
set's STORE_DEREF updates cell.ob_ref
get's LOAD_DEREF reads from same cell.ob_ref
```

---

## 2.6 The "Closure in Loop" Trap

```python
funcs = []
for i in range(3):
    funcs.append(lambda: i)

funcs[0]()  # 2 (NOT 0!)
funcs[1]()  # 2 (NOT 1!)
funcs[2]()  # 2 — all return 2!
```

Why? All three lambdas share the **same cell** for `i`. After the loop, `i`'s cell contains `int(2)`. All closures read from that same cell.

```
funcs[0].func_closure → (cell_for_i,) ─┐
funcs[1].func_closure → (cell_for_i,) ─┤ ALL SAME CELL!
funcs[2].func_closure → (cell_for_i,) ─┘
                                         │
                                         ▼
                                   PyCellObject
                                     ob_ref → int(2)  ← final value of loop!
```

Fix: capture `i` by value using a default argument:
```python
funcs = [lambda i=i: i for i in range(3)]
# Each lambda has its OWN default value (frozen at creation time)
# func_defaults = (0,), (1,), (2,) — different for each!
```

---

## 2.7 co_cellvars and co_freevars

```python
def outer(x):
    y = 10
    def inner(z):
        return x + y + z
    return inner
```

```
outer's code object:
  co_varnames = ()           ← no "normal" locals (all are cells!)
  co_cellvars = ('x', 'y')  ← variables referenced by inner functions
  
inner's code object:
  co_varnames = ('z',)      ← z is a regular local
  co_freevars = ('x', 'y')  ← variables from enclosing scope (via cells)
```

In the frame's `localsplus` array, the layout is:
```
[regular locals | cell vars | free vars | operand stack]
 co_varnames     co_cellvars  co_freevars
```

For `outer`: `[cell(x), cell(y) | (stack space)]`
For `inner`: `[z | cell(x), cell(y) | (stack space)]`

---

## 2.8 Closure Memory Cost

Each closure variable adds:
- 1 PyCellObject (24 bytes) on the heap
- 1 pointer in func_closure tuple (8 bytes + tuple overhead)
- The cell keeps the captured value alive (prevents GC)

For a closure capturing 3 variables:
```
func_closure = tuple of 3 cells:  56 + 3×8 = 80 bytes (tuple)
3 PyCellObjects: 3 × 24 = 72 bytes
Total closure overhead: ~152 bytes (excluding the captured values themselves)
```

---

## 2.9 Interview Questions — Part 2

**Q1**: What is a cell object in CPython?
**A**: A small heap-allocated wrapper (PyCellObject, 24 bytes) containing one pointer (ob_ref) to a value. Used to share variables between closures and their enclosing function after the enclosing frame is destroyed.

**Q2**: How does a closure variable survive after the enclosing function returns?
**A**: The variable is stored in a cell object (not directly in the frame). The returned closure's func_closure tuple holds a reference to the cell, keeping it alive on the heap.

**Q3**: Why does the "closure in loop" trap happen?
**A**: All lambdas/functions created in the loop share the SAME cell for the loop variable. After the loop, the cell contains the final value. All closures read from this shared cell.

**Q4**: What opcodes access closure variables?
**A**: LOAD_DEREF (read through cell indirection), STORE_DEREF (write through cell), LOAD_CLOSURE (push cell itself onto stack for MAKE_FUNCTION).

**Q5**: What's the difference between co_cellvars and co_freevars?
**A**: co_cellvars = variables in THIS function that are captured by inner functions (this function creates the cells). co_freevars = variables that THIS function captures from an enclosing scope (this function uses cells created elsewhere).
