# Part 11 — Object Relationships: References, Aliasing, and Cycles

## 11.1 The Reference Graph

Every Python program creates a **directed graph** of objects connected by references. Each edge is a pointer from one object to another (stored in a container slot, attribute, or variable frame).

```python
a = [1, 2]
b = {"key": a}
c = (a, b)
```

```
Reference Graph:

    Frame locals                    Heap Objects
    ┌──────────┐
    │ a ───────┼────→ [list] ←──────────────────────────────┐
    │ b ───────┼────→ {dict} ──→ "key" (key)                │
    │ c ───────┼────→ (tuple)    a (value) ─────────────────┘
    └──────────┘        │ │                                  
                        │ └──→ [list] (same object as 'a')   
                        └────→ {dict} (same object as 'b')   

Refcounts:
  list [1,2]:  3 (a + dict_value + tuple[0])
  dict:        2 (b + tuple[1])
  tuple:       1 (c)
```

---

## 11.2 Aliasing

**Aliasing** occurs when multiple names (or container slots) reference the same object:

```python
x = [1, 2, 3]
y = x           # Alias — same object
z = x           # Another alias

# x, y, z all point to the SAME list object
x.append(4)
print(y)        # [1, 2, 3, 4] — y sees the change!
print(z)        # [1, 2, 3, 4] — z sees it too!
```

```
Memory:                    
                           ┌────────────────────────┐
    x ─────────────────→   │  list [1, 2, 3, 4]     │
    y ─────────────────→   │  ob_refcnt: 3          │
    z ─────────────────→   │  ob_type: list         │
                           └────────────────────────┘

All three names hold the SAME pointer value (same address).
Mutation through ANY name affects the shared object.
```

### Aliasing vs Copying

```python
import copy

# Aliasing (shared reference):
a = [1, [2, 3]]
b = a                    # b IS a (same object)
b[0] = 99               # a[0] is now 99 too!

# Shallow copy (new container, shared elements):
c = copy.copy(a)         # c is a NEW list, but c[1] IS a[1]
c[0] = 0                 # a[0] unaffected (different top-level list)
c[1].append(4)           # a[1] affected! (shared nested list)

# Deep copy (everything new):
d = copy.deepcopy(a)     # d and all nested objects are new copies
d[1].append(5)           # a[1] unaffected
```

```
After shallow copy:

a → [list A]                 c → [list C] (NEW)
     │                            │
     ├─ [0]: → int(99)           ├─ [0]: → int(0)     (different)
     │                            │
     └─ [1]: → [list B] ←────────└─ [1]: → [list B]  (SHARED!)
               refcnt: 2
```

---

## 11.3 Container References

Containers hold pointers to their elements. Each slot in a container is a `PyObject*` that keeps the referenced object alive:

```python
my_list = [obj_a, obj_b, obj_c]
```

```
PyListObject:
┌────────────────────────┐
│ ob_refcnt: 1           │
│ ob_type: list          │
│ ob_size: 3             │
│ ob_item: ──────────────┼──→ ┌──────────────────┐
│ allocated: 4           │    │ [0]: → obj_a     │  Py_INCREF(obj_a)
└────────────────────────┘    │ [1]: → obj_b     │  Py_INCREF(obj_b)
                              │ [2]: → obj_c     │  Py_INCREF(obj_c)
                              │ [3]: NULL         │
                              └──────────────────┘

Each slot holds a STRONG reference (INCREFs the object).
When the list is deallocated, each slot is DECREFed:
  Py_DECREF(obj_a);  Py_DECREF(obj_b);  Py_DECREF(obj_c);
```

### Nested Containers

```python
matrix = [[1, 2], [3, 4]]
```

```
matrix → ┌──────────────────┐
         │ list (outer)     │
         │ ob_size: 2       │
         │ items: ──────────┼──→ ┌────────────┐
         └──────────────────┘    │ [0]: ──────┼──→ [list: 1, 2]
                                 │ [1]: ──────┼──→ [list: 3, 4]
                                 └────────────┘
                                 
The outer list holds pointers to the inner lists.
Inner lists hold pointers to integers.

Total reference chain:
  matrix → outer_list → inner_list_0 → int(1)
                                      → int(2)
                       → inner_list_1 → int(3)
                                      → int(4)
```

---

## 11.4 Reference Cycles

A **cycle** exists when objects reference each other in a loop:

### Simple Self-Reference

```python
a = []
a.append(a)  # a[0] IS a
```

```
┌───────────────────────┐
│ list                  │
│ ob_refcnt: 2          │←──┐
│ items[0]: ────────────┼───┘  (points to itself!)
└───────────────────────┘

After 'del a':
ob_refcnt drops from 2 to 1 (not 0!) → NOT freed by refcounting.
Cyclic GC must detect and break this.
```

### Mutual Reference

```python
class Node:
    def __init__(self):
        self.next = None

a = Node()
b = Node()
a.next = b    # a → b
b.next = a    # b → a (cycle!)
del a, b      # Both unreachable but refcnt = 1 each
```

```
After del a, b:

    ┌───────────────────┐       ┌───────────────────┐
    │ Node A            │       │ Node B            │
    │ refcnt: 1         │←──────┤ refcnt: 1         │
    │ next: ────────────┼──────→│ next: (points to A)│
    └───────────────────┘       └───────────────────┘
    
Both have refcnt=1 (from the other's .next attribute).
Both are unreachable from any root. Memory leak without GC.
```

### Complex Cycles

```python
# Frame object cycle (common in tracebacks):
import sys
frame = sys._getframe()
# frame → f_locals dict → 'frame' variable → frame (cycle!)
```

---

## 11.5 How the Cyclic GC Breaks Cycles

The GC uses **trial deletion**:

1. For every tracked object, compute what refcount would be if all internal references were removed
2. Objects whose "external refcount" (references from outside tracked objects) is 0 are unreachable
3. Call `tp_clear()` on unreachable objects to break cycles
4. Let normal refcounting handle deallocation

```
GC Algorithm (simplified):

1. Start: All tracked objects have their real refcount
   Node A: refcnt=1, Node B: refcnt=1

2. Trial subtract: For each tracked object, subtract references FROM other tracked objects
   Node A: 1 - 1 = 0 (B's reference subtracted)
   Node B: 1 - 1 = 0 (A's reference subtracted)

3. Objects with trial_refcnt = 0 are in cycles and unreachable → collect them
```

---

## 11.6 Shared References: The Immutable Advantage

For immutable objects, sharing is always safe:

```python
a = "hello"
b = "hello"  # May be the SAME object (interned)
# No risk: neither can modify the shared string
```

For mutable objects, sharing creates aliasing risks:

```python
# Danger: shared mutable default argument
def append_to(item, target=[]):  # target is shared across calls!
    target.append(item)
    return target

append_to(1)  # [1]
append_to(2)  # [1, 2] — NOT [2]! Same list object!
```

---

## 11.7 Ownership Semantics

CPython uses **reference counting as ownership**:
- Holding a reference = partial ownership
- When all owners release (DECREF), the object is freed
- No single "owner" — shared ownership model

### Strong vs Weak References

```python
import weakref

class Foo:
    pass

obj = Foo()

# Strong reference (affects lifetime):
strong = obj                   # refcnt += 1

# Weak reference (does NOT affect lifetime):
weak = weakref.ref(obj)       # refcnt unchanged!

del obj, strong               # refcnt → 0 → deallocated
print(weak())                 # None (object is dead)
```

```
Strong reference:
    name ──[strong ref]──→ Object (refcnt includes this)

Weak reference:
    weakref ──[weak ref]──→ Object (refcnt does NOT include this)
                  │
                  └── callback called when object dies
```

---

## 11.8 Reference Patterns in Real Code

### Function Closures

```python
def make_counter():
    count = [0]
    def increment():
        count[0] += 1
        return count[0]
    return increment

counter = make_counter()
```

```
counter → PyFunctionObject
            │
            └── func_closure → (cell_object,)
                                    │
                                    └── cell_contents → [0]  (the list)
                                    
The list [0] is kept alive by:
  cell_object → which is in the closure → which is in the function → 
  which is referenced by 'counter'
  
When 'counter' is deleted, the whole chain is released.
```

### Class Instance Attributes

```python
class Graph:
    def __init__(self):
        self.nodes = []
        self.edges = {}
        
g = Graph()
g.nodes.append(g)  # Cycle! g → g.__dict__ → nodes_list → g
```

---

## 11.9 Visualizing with gc and objgraph

```python
import gc
import sys

# See what refers to an object:
a = [1, 2, 3]
b = {'data': a}
c = (a,)

# gc.get_referrers(a) → returns [b, c, <frame>]
referrers = gc.get_referrers(a)

# gc.get_referents(b) → returns objects that b references
referents = gc.get_referents(b)  # ['data', a]

# Count references:
print(sys.getrefcount(a))  # 4 (a, b['data'], c[0], getrefcount arg)
```

---

## 11.10 The Root Set

Objects reachable from "roots" are alive. Roots include:
- Module-level global variables (all loaded modules)
- Stack frames (local variables in active functions)
- Built-in objects (True, False, None, type objects)
- C-level static references

```
Root Set:
┌──────────────────┐
│ Module globals   │──→ objects in module __dict__
│ Active frames    │──→ local variables on the stack
│ Builtins         │──→ None, True, int, str, etc.
│ Interned strings │──→ string table
│ Small int cache  │──→ integers [-5, 256]
└──────────────────┘

From roots, follow ALL references transitively → "reachable set"
Anything NOT in the reachable set is garbage.
```

---

## 11.11 Source References

| File | Contents |
|------|----------|
| `Modules/gcmodule.c` | Cyclic garbage collector, trial deletion |
| `Include/internal/pycore_gc.h` | GC header, tracking macros |
| `Lib/weakref.py` | Weak reference implementation |
| `Objects/listobject.c` | list_dealloc (DECREFs all items) |
| `Objects/dictobject.c` | dict_dealloc (DECREFs keys/values) |
| `Lib/gc.py` | gc module (get_referrers, get_referents) |
| `Python/ceval.c` | Frame cleanup (DECREF all locals) |

---

## 11.12 Interview Questions — Part 11

**Q1**: What is aliasing in Python and when does it cause unexpected behavior?
**A**: Aliasing is when multiple names refer to the same mutable object. Mutation through one name is visible through all others. Common pitfall: mutable default arguments, shared list/dict references passed to functions.

**Q2**: Draw the reference graph for `a = []; b = [a]; a.append(b)`. Is there a cycle?
**A**: Yes — `a → b` (a contains b at a[0]) and `b → a` (b contains a at b[0]). This forms a 2-node cycle. After `del a; del b`, both have refcnt=1 (from the other's list slot) and are unreachable. Only the cyclic GC can free them.

**Q3**: Why does CPython need a cyclic garbage collector if it already has reference counting?
**A**: Reference counting can't handle cycles. When objects form a reference loop, their refcounts never reach 0 even when unreachable. The cyclic GC periodically finds and collects these cycles using trial deletion (subtracting internal references to identify truly unreachable objects).

**Q4**: What's the difference between `gc.get_referrers(obj)` and `gc.get_referents(obj)`?
**A**: `get_referrers(obj)` returns objects that REFERENCE obj (who points TO it). `get_referents(obj)` returns objects that obj REFERENCES (what it points TO). Referrers are the "parents" in the reference graph; referents are the "children."

**Q5**: Explain why weak references exist and give a use case.
**A**: Weak references observe an object without keeping it alive (don't contribute to refcount). Use case: caches — you want to cache expensive objects but allow them to be freed when memory is tight. `weakref.WeakValueDictionary` does this automatically.

**Q6**: What is the "root set" in garbage collection, and why does it matter?
**A**: The root set is the set of objects known to be alive (module globals, stack frames, builtins). The GC traces references from roots to find all reachable objects. Anything not reachable from the root set is garbage. Without a root set, the GC wouldn't know where to start.

**Q7**: How does a shallow copy differ from aliasing in terms of reference counting?
**A**: Aliasing: one object, one extra INCREF (same pointer stored in another name). Shallow copy: NEW container object created (new allocation), but elements inside get INCREF'd (shared with original). The container itself has refcnt=1, but elements may have higher refcounts.

**Q8**: Why is the mutable default argument bug so common in Python?
**A**: Default argument values are evaluated ONCE at function definition time and stored as part of the function object. Every call that uses the default shares the SAME object. For mutable defaults (lists, dicts), mutations persist across calls because it's always the same object.
