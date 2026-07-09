# Part 12 — CPython Source Tour

## 12.1 Key Files Overview

| File | Lines | Purpose |
|------|-------|---------|
| `Python/ceval.c` | ~8000 | Main eval loop, opcode dispatch |
| `Python/bytecodes.c` | ~4000 | Opcode definitions (3.12+, generates cases) |
| `Python/compile.c` | ~9000 | AST → bytecode compiler |
| `Python/symtable.c` | ~2500 | Symbol table / scope analysis |
| `Python/flowgraph.c` | ~1500 | CFG construction |
| `Objects/funcobject.c` | ~1000 | PyFunctionObject implementation |
| `Objects/codeobject.c` | ~2500 | PyCodeObject implementation |
| `Objects/frameobject.c` | ~1500 | Frame object (Python-visible part) |
| `Include/internal/pycore_frame.h` | ~200 | _PyInterpreterFrame struct |
| `Include/cpython/code.h` | ~150 | PyCodeObject struct |
| `Include/opcode.h` | ~200 | Opcode number definitions |

---

## 12.2 Objects/funcobject.c — Function Object

```c
// Function creation (MAKE_FUNCTION calls this):
PyObject *
PyFunction_New(PyObject *code, PyObject *globals)
{
    PyFunctionObject *op = PyObject_GC_New(PyFunctionObject, &PyFunction_Type);
    
    op->func_globals = Py_NewRef(globals);
    op->func_builtins = Py_NewRef(builtins);
    op->func_code = Py_NewRef(code);
    op->func_name = Py_NewRef(((PyCodeObject *)code)->co_name);
    op->func_qualname = Py_NewRef(((PyCodeObject *)code)->co_qualname);
    op->func_defaults = NULL;
    op->func_kwdefaults = NULL;
    op->func_closure = NULL;
    op->func_doc = NULL;
    op->func_dict = NULL;
    op->func_module = NULL;
    op->func_annotations = NULL;
    op->vectorcall = _PyFunction_Vectorcall;
    op->func_version = 0;
    
    _PyObject_GC_TRACK(op);
    return (PyObject *)op;
}
```

---

## 12.3 Objects/codeobject.c — Code Object

```c
// Code object creation (compiler calls this):
PyCodeObject *
_PyCode_New(struct _PyCodeConstructor *con)
{
    PyCodeObject *co = PyObject_New(PyCodeObject, &PyCode_Type);
    
    co->co_argcount = con->argcount;
    co->co_kwonlyargcount = con->kwonlyargcount;
    co->co_nlocals = con->nlocals;
    co->co_stacksize = con->stacksize;
    co->co_flags = con->flags;
    co->co_code = Py_NewRef(con->code);       // bytecode bytes
    co->co_consts = Py_NewRef(con->consts);   // constants tuple
    co->co_names = Py_NewRef(con->names);     // global/attr names
    co->co_varnames = Py_NewRef(con->varnames);
    co->co_cellvars = Py_NewRef(con->cellvars);
    co->co_freevars = Py_NewRef(con->freevars);
    co->co_filename = Py_NewRef(con->filename);
    co->co_name = Py_NewRef(con->name);
    co->co_firstlineno = con->firstlineno;
    co->co_linetable = Py_NewRef(con->linetable);
    co->co_exceptiontable = Py_NewRef(con->exceptiontable);
    // ... more initialization ...
    
    return co;
}
```

---

## 12.4 Python/compile.c — The Compiler

```c
// Entry point: compile a module
PyCodeObject *
_PyAST_Compile(mod_ty mod, PyObject *filename, PyCompilerFlags *flags, ...)
{
    struct compiler c;
    compiler_init(&c);
    c.c_filename = filename;
    
    // Phase 1: Build symbol table (scope analysis)
    c.c_st = _PySymtable_Build(mod, filename, ...);
    
    // Phase 2: Compile AST to code object
    // (recursive: each function/class body compiles to its own code object)
    if (!compiler_body(&c, mod->v.Module.body))
        goto error;
    
    // Phase 3: Assemble into final code object
    PyCodeObject *co = assemble(&c, ...);
    
    compiler_free(&c);
    return co;
}

// Compiling a function definition:
static int
compiler_function(struct compiler *c, stmt_ty s)
{
    // 1. Push new compiler scope
    compiler_enter_scope(c, name, COMPILER_SCOPE_FUNCTION, ...);
    
    // 2. Compile parameter defaults (in enclosing scope!)
    // 3. Compile function body
    compiler_body(c, body);
    
    // 4. Emit RETURN_VALUE at end (implicit return None)
    // 5. Assemble code object for this function
    PyCodeObject *co = assemble(c, ...);
    
    // 6. Pop scope
    compiler_exit_scope(c);
    
    // 7. In enclosing scope: emit LOAD_CONST <code> + MAKE_FUNCTION
    ADDOP_LOAD_CONST(c, (PyObject *)co);
    ADDOP(c, MAKE_FUNCTION);
    
    return 1;
}
```

---

## 12.5 Python/ceval.c — The Eval Loop

```c
// The main evaluation function (simplified structure):
PyObject *
_PyEval_EvalFrameDefault(PyThreadState *tstate, _PyInterpreterFrame *frame, int throwflag)
{
    PyCodeObject *co = frame->f_code;
    PyObject **stack_pointer = frame->localsplus + frame->stacktop;
    _Py_CODEUNIT *next_instr = frame->prev_instr + 1;
    PyObject *retval = NULL;
    
    // Optional: tracing hooks
    if (tstate->c_tracefunc) {
        call_trace(...);
    }
    
    // MAIN DISPATCH LOOP:
    for (;;) {
        // Periodic checks (GIL, signals, etc.)
        if (_Py_atomic_load_relaxed(&tstate->eval_breaker)) {
            handle_eval_breaker(tstate);
        }
        
        // Fetch and dispatch:
        uint8_t opcode = _Py_OPCODE(*next_instr);
        uint8_t oparg = _Py_OPARG(*next_instr);
        next_instr++;
        
        // Computed goto dispatch (or switch):
        DISPATCH_OPCODE(opcode);
        
        // ... 150+ opcode handlers ...
    }
    
error:
    // Exception handling
    retval = handle_exception(tstate, frame);
    return retval;
}
```

---

## 12.6 Interview Questions — Part 12

**Q1**: What file contains the main interpreter loop?
**A**: `Python/ceval.c` (and `Python/generated_cases.c.h` for auto-generated opcode handlers in 3.12+).

**Q2**: Where is the compiler?
**A**: `Python/compile.c` (AST → code object), `Python/symtable.c` (scope analysis), `Python/flowgraph.c` (CFG).

**Q3**: How is a function object created at the C level?
**A**: `PyFunction_New(code, globals)` allocates a PyFunctionObject, sets func_code, func_globals, func_name from the code object, and registers for GC tracking.

**Q4**: What is the relationship between compile.c and ceval.c?
**A**: compile.c runs at import/compile time (source → code object). ceval.c runs at execution time (code object → results). They communicate through the code object data structure.
