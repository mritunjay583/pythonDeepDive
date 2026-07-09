# Part 7 — Adaptive Specialization (Python 3.11+)

## 7.1 The Specializing Adaptive Interpreter

Python 3.11 introduced a **specializing adaptive interpreter** that rewrites bytecode at runtime based on observed types:

```
Traditional interpreter:
  BINARY_OP + → check types → dispatch to int_add or float_add or generic_add

Specializing interpreter:
  After seeing int + int several times:
  BINARY_OP + → REWRITTEN to → BINARY_OP_ADD_INT
  
  BINARY_OP_ADD_INT:
    - Assumes both operands are int
    - Skips type checking
    - Directly calls int addition
    - If assumption wrong → deoptimize back to generic BINARY_OP
```

---

## 7.2 How It Works

### Quickening (First Phase):

After a function is called a few times, its bytecode is "quickened":
1. Generic opcodes get counters
2. After N executions with consistent types: **specialize**
3. Specialized opcode has an inline cache for type info

### Inline Caches:

Extra bytes after specialized instructions store cached data:
```
Instruction layout (specialized):
┌──────────────┬──────┬─────────────────────┐
│ LOAD_ATTR    │ arg  │ [cache: type_ver][cache: offset] │
│ (specialized)│      │ (4-8 extra bytes for inline cache)│
└──────────────┴──────┴─────────────────────┘

The cache stores:
  - Expected type version (tp_version_tag)
  - Attribute offset or method pointer
  
On hit (type version matches): direct access → O(1)
On miss: deoptimize → full lookup → update cache
```

---

## 7.3 Specialized Opcodes (Examples)

```
Generic              Specialized              Assumption
─────────────────────────────────────────────────────────────
BINARY_OP +          BINARY_OP_ADD_INT        Both are int
BINARY_OP +          BINARY_OP_ADD_FLOAT      Both are float
BINARY_OP +          BINARY_OP_ADD_UNICODE    Both are str
LOAD_ATTR            LOAD_ATTR_INSTANCE_VALUE Instance attribute
LOAD_ATTR            LOAD_ATTR_MODULE         Module attribute
LOAD_ATTR            LOAD_ATTR_SLOT           __slots__ attribute
LOAD_GLOBAL          LOAD_GLOBAL_MODULE       Known module global
LOAD_GLOBAL          LOAD_GLOBAL_BUILTIN      Known builtin
CALL                 CALL_PY_EXACT_ARGS       Python func, exact arg count
CALL                 CALL_BUILTIN_FAST        C function (METH_FASTCALL)
COMPARE_OP           COMPARE_OP_INT           Both int
FOR_ITER             FOR_ITER_LIST            Iterating over list
STORE_ATTR           STORE_ATTR_INSTANCE_VALUE Instance attribute store
```

---

## 7.4 The Specialization Cycle

```
1. Function defined → generic bytecode
2. Function called → ADAPTIVE opcodes (counters start)
3. Counter threshold reached → SPECIALIZE based on observed types
4. Specialized opcode executes (fast path)
5. If type assumption fails → DEOPTIMIZE back to adaptive
6. After too many failures → PERMANENTLY GENERIC (stop trying)
```

### Performance Impact:

Typical Python 3.11 vs 3.10 improvement: **10-60% faster** for attribute access, numeric operations, and function calls — without any code changes.

---

## 7.5 Viewing Specialization

```python
import dis, sys

def add_ints(a, b):
    return a + b

# Call several times to trigger specialization:
for _ in range(100):
    add_ints(1, 2)

# View specialized bytecode:
dis.dis(add_ints, adaptive=True)
# Shows BINARY_OP_ADD_INT instead of generic BINARY_OP
```

---

## 7.6 Interview Questions — Part 7

**Q1**: What is the specializing adaptive interpreter?
**A**: Since Python 3.11, CPython rewrites generic bytecode into type-specialized versions at runtime. After observing that `x + y` always involves ints, BINARY_OP becomes BINARY_OP_ADD_INT — skipping type dispatch.

**Q2**: What are inline caches?
**A**: Extra bytes stored after specialized instructions containing cached type info (version tags, offsets). On cache hit: fast direct access. On miss: deoptimize and re-specialize.

**Q3**: What happens when specialization assumptions fail?
**A**: Deoptimization: the specialized opcode detects the type mismatch, falls back to the generic version, and may re-specialize for the new type or give up after too many failures.

**Q4**: How much speedup does specialization provide?
**A**: 10-60% for typical Python code in 3.11+, without any source changes. Attribute access, numeric ops, and function calls benefit most.
