# Part 4 — Compilation Pipeline

## 4.1 The Complete Pipeline

```
Source Code (Unicode text)
      │
      │ ① Tokenizer (Parser/tokenizer.c)
      ▼
Token Stream (TOKEN_TYPE + value)
      │
      │ ② Parser (Parser/parser.c — PEG parser since 3.9)
      ▼
CST (Concrete Syntax Tree) → immediately transformed to:
AST (Abstract Syntax Tree — Python/ast.c)
      │
      │ ③ Symbol Table (Python/symtable.c)
      ▼
Annotated AST (each name: local/global/free/cell)
      │
      │ ④ Compiler (Python/compile.c)
      │    ├── CFG construction (control flow graph)
      │    ├── Bytecode emission
      │    ├── Optimization passes
      │    └── Code object assembly
      ▼
PyCodeObject (bytecode + metadata)
      │
      │ ⑤ Marshal → .pyc file (optional caching)
      ▼
Execution by ceval.c
```

---

## 4.2 Stage 1: Tokenization

The tokenizer converts source text into a stream of tokens:

```python
# Source:
x = 42 + y

# Tokens:
NAME 'x'
OP '='
NUMBER '42'
OP '+'
NAME 'y'
NEWLINE
```

```python
import tokenize, io
source = "x = 42 + y\n"
tokens = tokenize.generate_tokens(io.StringIO(source).readline)
for tok in tokens:
    print(tok)
# TokenInfo(type=1 (NAME), string='x', ...)
# TokenInfo(type=55 (OP), string='=', ...)
# TokenInfo(type=2 (NUMBER), string='42', ...)
# ...
```

The tokenizer handles:
- Indentation (generates INDENT/DEDENT tokens)
- String literal concatenation
- Line continuations (`\`)
- Encoding declarations
- f-string parsing (since 3.12: tokenized as a structured token)

---

## 4.3 Stage 2: Parsing (PEG Parser)

Since Python 3.9, CPython uses a PEG (Parsing Expression Grammar) parser:

```python
import ast
source = "x = 42 + y"
tree = ast.parse(source)
print(ast.dump(tree, indent=2))
```

```
Module(
  body=[
    Assign(
      targets=[Name(id='x', ctx=Store())],
      value=BinOp(
        left=Constant(value=42),
        op=Add(),
        right=Name(id='y', ctx=Load())
      )
    )
  ]
)
```

The AST is a clean tree structure without parsing artifacts (no parentheses nodes, no comma tokens — just the semantic structure).

---

## 4.4 Stage 3: Symbol Table Analysis

Before generating bytecode, the compiler must determine the **scope** of every name:

```python
def outer(x):
    y = 10
    def inner(z):
        return x + y + z
    return inner
```

Symbol table analysis determines:
```
outer:
  x → CELL (referenced by inner)
  y → CELL (referenced by inner)
  inner → LOCAL
  
inner:
  z → LOCAL (parameter)
  x → FREE (from outer)
  y → FREE (from outer)
```

This information is critical for choosing the correct opcodes:
- LOCAL → LOAD_FAST / STORE_FAST
- GLOBAL → LOAD_GLOBAL / STORE_GLOBAL
- FREE → LOAD_DEREF (through cell)
- CELL → LOAD_DEREF / STORE_DEREF (creates cell)

```python
import symtable
st = symtable.symtable("def f(x): return x + y", "<test>", "exec")
f_table = st.get_children()[0]
for sym in f_table.get_symbols():
    print(f"{sym.get_name()}: local={sym.is_local()}, free={sym.is_free()}, global={sym.is_global()}")
```

---

## 4.5 Stage 4: Bytecode Compilation

The compiler (Python/compile.c) walks the AST and emits bytecode:

```python
def add(x, y):
    return x + y
```

Compiler walks AST nodes:
```
Visit FunctionDef('add'):
  → Create new code object scope
  → Visit body:
    Visit Return:
      Visit BinOp(Add):
        Visit Name('x', Load) → emit LOAD_FAST 0
        Visit Name('y', Load) → emit LOAD_FAST 1
        → emit BINARY_OP 0 (Add)
      → emit RETURN_VALUE
  → Finalize code object (compute stacksize, etc.)
```

Result:
```
RESUME          0
LOAD_FAST       0  (x)
LOAD_FAST       1  (y)
BINARY_OP       0  (+)
RETURN_VALUE
```

### The Control Flow Graph (CFG):

The compiler first builds a graph of **basic blocks** (straight-line code with no jumps in the middle):

```python
def example(x):
    if x > 0:
        return x
    else:
        return -x
```

```
Block 0 (entry):
  RESUME 0
  LOAD_FAST 0 (x)
  LOAD_CONST 1 (0)
  COMPARE_OP > 
  POP_JUMP_IF_FALSE → Block 2

Block 1 (if-true):
  LOAD_FAST 0 (x)
  RETURN_VALUE

Block 2 (else):
  LOAD_FAST 0 (x)
  UNARY_NEGATIVE
  RETURN_VALUE
```

The CFG is then linearized, optimized (peephole), and assembled into the final bytecode bytes.

---

## 4.6 Stage 5: .pyc Caching

Compiled code objects are cached in `.pyc` files (in `__pycache__/`):

```
__pycache__/module.cpython-312.pyc:
  [4 bytes: magic number (identifies Python version)]
  [4 bytes: flags]
  [8 bytes: source modification timestamp]
  [4 bytes: source file size]
  [marshalled code object bytes]
```

On next import: if .pyc is newer than .py and magic matches → load cached code object directly (skip tokenize + parse + compile). Saves ~100ms for large modules.

---

## 4.7 Optimization Passes

### Constant Folding:
```python
x = 2 * 3 + 1    # Compiled to: LOAD_CONST 7 (pre-computed!)
s = "hel" + "lo"  # Compiled to: LOAD_CONST "hello"
```

### Dead Code Elimination:
```python
if False:
    expensive()   # Entire block removed from bytecode (3.12+)
```

### Peephole Optimizations:
```
LOAD_CONST True; POP_JUMP_IF_FALSE label
  → removed (always falls through)

JUMP label; label: (next instruction)
  → jump removed (target is next instruction anyway)
```

---

## 4.8 Seeing the Pipeline in Action

```python
import dis, ast, tokenize, io

source = '''
def greet(name):
    return "Hello, " + name
'''

# Stage 1: Tokens
print("=== TOKENS ===")
tokens = tokenize.generate_tokens(io.StringIO(source).readline)
for tok in tokens:
    if tok.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, 
                         tokenize.DEDENT, tokenize.ENCODING, tokenize.ENDMARKER):
        print(f"  {tokenize.tok_name[tok.type]:10s} {tok.string!r}")

# Stage 2: AST
print("\n=== AST ===")
tree = ast.parse(source)
print(ast.dump(tree, indent=2))

# Stage 4: Bytecode
print("\n=== BYTECODE ===")
code = compile(source, "<test>", "exec")
dis.dis(code)

# The inner function's bytecode:
print("\n=== greet() BYTECODE ===")
greet_code = code.co_consts[0]  # code object for greet
dis.dis(greet_code)
```

---

## 4.9 Interview Questions — Part 4

**Q1**: What are the stages of Python's compilation pipeline?
**A**: Source → Tokenizer → Parser (PEG) → AST → Symbol Table → Compiler (CFG + bytecode emission) → Code Object. Optionally: → Marshal → .pyc file.

**Q2**: What does the symbol table phase determine?
**A**: The scope of every name: LOCAL, GLOBAL, FREE (from closure), or CELL (captured by inner function). This determines which opcode (LOAD_FAST vs LOAD_GLOBAL vs LOAD_DEREF) to use.

**Q3**: What is a basic block in the CFG?
**A**: A straight-line sequence of instructions with no jumps except at the end, and no jump targets except at the beginning. The CFG connects these blocks with edges representing control flow.

**Q4**: What optimization does CPython perform at compile time?
**A**: Constant folding (2*3→6), dead code elimination (if False: removed), peephole optimizations (redundant jumps removed), and some constant propagation.

**Q5**: What is stored in a .pyc file?
**A**: Magic number (version identifier), source timestamp, source size, and the marshalled code object. Used to skip recompilation on import if source hasn't changed.
