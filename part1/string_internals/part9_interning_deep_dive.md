# Part 9 — String Interning Deep Dive

## 9.1 What Interning Is at the C Level

Interning ensures ONE canonical object exists for each unique string value. The intern table is a Python dict mapping strings to themselves:

```c
// Objects/unicodeobject.c
static PyObject *interned = NULL;  // The intern table (a regular dict!)

// Interning a string:
void PyUnicode_InternInPlace(PyObject **p)
{
    PyObject *s = *p;
    
    // Only intern compact ASCII/Latin-1 strings (not UCS-2/4 by default)
    if (!PyUnicode_CheckExact(s))
        return;
    if (PyUnicode_CHECK_INTERNED(s))
        return;  // Already interned
    
    // Look up in intern table:
    PyObject *t = PyDict_SetDefault(interned, s, s);
    // SetDefault: if key exists, returns existing value
    //             if key doesn't exist, inserts s→s and returns s
    
    if (t != s) {
        // String already existed in table — use the existing one
        Py_INCREF(t);
        Py_SETREF(*p, t);  // Replace caller's pointer with canonical version
        // Old string s will be freed (its refcount drops)
    }
    else {
        // String is new in the table — mark it as interned
        _PyUnicode_STATE(s).interned = SSTATE_INTERNED_MORTAL;
    }
}
```

---

## 9.2 Interning States

```c
#define SSTATE_NOT_INTERNED      0  // Normal string
#define SSTATE_INTERNED_MORTAL   1  // In table, can be removed when unreferenced
#define SSTATE_INTERNED_IMMORTAL 2  // In table, NEVER removed (lives forever)
```

### MORTAL Interning
```
Created by: sys.intern(), runtime identifier lookups
Behavior: String stays in intern table as long as external references exist.
           When only the intern table holds a reference → eligible for removal.
Deallocation: During GC or when intern table is cleaned up.
```

### IMMORTAL Interning
```
Created by: Interpreter startup for built-in names, type names, "__init__", etc.
Behavior: NEVER deallocated, even if no external references.
           ob_refcnt may be the special immortal value (3.12+).
Examples: "__init__", "__main__", "None", "True", "False",
          all built-in function names, all keyword names
```

---

## 9.3 What Gets Automatically Interned

### At Compile Time (by the compiler/peephole optimizer):

```python
# 1. String constants that look like identifiers:
"hello"        # Valid identifier → INTERNED at compile time
"my_var"       # Valid identifier → INTERNED
"__init__"     # Valid identifier → INTERNED
"CamelCase"    # Valid identifier → INTERNED

# 2. NOT interned automatically:
"hello world"  # Contains space → NOT an identifier → NOT interned
"hello!"       # Contains punctuation → NOT interned
"123abc"       # Starts with digit → NOT interned
""             # Empty string → actually IS interned (special case)
```

### The Identifier Check:
```c
// A string is "identifier-like" if it matches [A-Za-z_][A-Za-z0-9_]*
// CPython uses a simplified check for Latin-1 ASCII identifiers:
static int all_name_chars(PyObject *o) {
    const unsigned char *s = (unsigned char*)PyUnicode_1BYTE_DATA(o);
    const unsigned char *e = s + PyUnicode_GET_LENGTH(o);
    for (; s != e; s++) {
        if (!Py_ISALNUM(*s) && *s != '_')
            return 0;
    }
    if (Py_ISDIGIT(*(unsigned char*)PyUnicode_1BYTE_DATA(o)))
        return 0;  // Can't start with digit
    return 1;
}
```

### At Runtime (by the interpreter):

```python
# Variable names in code execution:
x = 42  # The name "x" is interned (used as dict key in locals/globals)

# Attribute names:
obj.method  # "method" is interned (used as dict key in type.__dict__)

# Dict literal keys that are string constants:
d = {"key": value}  # "key" is interned
```

---

## 9.4 How Interning Speeds Up Dict Lookup

The critical optimization is in `lookdict_unicode` (the dict lookup for string keys):

```c
// dictobject.c — string-key dict lookup (simplified):
static Py_ssize_t
lookdict_unicode(PyDictObject *mp, PyObject *key, Py_hash_t hash, ...)
{
    // ... probe to find the slot ...
    
    PyObject *ep_key = entries[ix].me_key;
    
    // FAST PATH: pointer comparison!
    if (ep_key == key) {
        return ix;  // FOUND! O(1)! No string comparison!
    }
    
    // SLOW PATH: same hash → must compare characters
    if (ep->me_hash == hash && unicode_eq(ep_key, key)) {
        return ix;
    }
    
    // ... continue probing ...
}
```

When BOTH the lookup key AND the stored key are interned, they're the same object → the pointer comparison `ep_key == key` succeeds immediately. This is why attribute access is fast:

```python
obj.name  # Internally: lookup "name" in obj.__dict__
# "name" (the attribute name) is interned by the compiler
# obj.__dict__ keys are interned during class creation
# → pointer comparison succeeds → O(1) without character comparison!
```

---

## 9.5 sys.intern() for Manual Interning

```python
import sys

# Intern a string that wouldn't be auto-interned:
key = sys.intern("hello world")  # Now in the intern table

# All future intern requests for same value return the SAME object:
key2 = sys.intern("hello world")
key is key2  # True!

# Use case: millions of repeated strings from external data
data = [sys.intern(row["category"]) for row in csv_reader]
# If there are only 10 unique categories among 10M rows:
# 10M references to just 10 string objects (instead of 10M objects!)
```

### Memory Impact:
```python
# Without interning (10M rows, 100 unique values, avg 15 chars each):
# 10,000,000 × (64 + 16) = ~800 MB  (each string ~80 bytes)

# With interning:
# 100 × 80 = 8,000 bytes (100 unique strings)
# + 10,000,000 × 8 = 80 MB (pointers in the list)
# Total: ~80 MB vs ~800 MB = 10× reduction!
```

---

## 9.6 Interning and Garbage Collection

### Mortal Interned Strings:
```
The intern table dict holds a reference to each interned string.
If ONLY the intern table references it (refcnt = 1 from the table),
the string is effectively unreachable from user code.

CPython has a mechanism to clean these up:
  - When the intern table is resized/rebuilt
  - When _PyUnicode_ClearInterned() is called during shutdown
  
In practice: mortal interned strings persist until interpreter shutdown
             unless explicitly removed from the table.
```

### Memory Leak Warning:
```python
# BAD: interning dynamically generated unique strings
for i in range(1000000):
    sys.intern(f"key_{i}")  # 1M unique strings → 1M permanent entries!
    # These will NEVER be freed until interpreter shuts down!

# GOOD: only intern strings with high repetition
categories = set(row["cat"] for row in data)  # Find unique values first
intern_cache = {sys.intern(c) for c in categories}  # Intern only uniques
```

---

## 9.7 Compiler Interning vs Runtime Interning

### Compile-Time (in marshal/code object creation):
```
When the compiler creates code objects:
1. All identifier-like string constants are interned
2. All attribute names referenced in code are interned
3. All variable names are interned
4. These become IMMORTAL interned strings

Example:
  def foo():
      x = obj.method
  
  Interned at compile time: "foo", "x", "obj", "method"
  These strings exist in co_names/co_varnames of the code object.
```

### Runtime (during execution):
```
When code executes and creates string values:
1. String literals → already interned from compilation
2. Dynamic strings → NOT interned unless sys.intern() called
3. Attribute names in __dict__ → interned when class is created
4. Method names → interned

Example:
  name = "hello"      # "hello" was interned at compile time
  name = input()      # NOT interned (dynamic, unknown at compile time)
  name = sys.intern(input())  # Explicitly interned
```

---

## 9.8 Constant Folding and Interning

```python
# The compiler folds constant expressions:
a = "hel" + "lo"     # Folded to "hello" at compile time → interned ✓
b = "hello"          # Same constant → same interned object
a is b               # True! Both are the same compile-time constant.

# But runtime operations create NEW strings:
c = "hel"
d = c + "lo"         # Runtime concat → NOT interned!
d is a               # False! Different object!
d == a               # True (same value)

# Unless you explicitly intern:
d = sys.intern(c + "lo")
d is a               # True! (after interning, points to same object)
```

---

## 9.9 Interview Questions — Part 9

**Q1**: What data structure is the intern table?
**A**: A regular Python dict mapping string objects to themselves: `{s: s}`. Lookup uses the string's hash. The table is a module-level static variable in `unicodeobject.c`.

**Q2**: What's the difference between MORTAL and IMMORTAL interning?
**A**: IMMORTAL strings are never freed (built-in names, type names, keywords). MORTAL strings can theoretically be freed if no external references exist, but in practice persist until shutdown.

**Q3**: Why is attribute access fast in CPython?
**A**: Attribute names are interned at compile time. Instance __dict__ keys are also interned. Dict lookup does `key == stored_key` as a pointer comparison first — if both are interned (same object), it's O(1) without character comparison.

**Q4**: Does `sys.intern()` work for non-ASCII strings?
**A**: Yes, but with less benefit. Non-ASCII strings use PyCompactUnicodeObject (larger struct). The interning still ensures one object per unique value, but auto-interning by the compiler typically only applies to ASCII identifier-like strings.

**Q5**: What's the risk of interning too many strings?
**A**: Memory leak. Interned strings (especially mortal ones) persist in the intern table until interpreter shutdown. Interning millions of unique dynamic strings wastes memory with no deduplication benefit.

**Q6**: After `a = "test"; b = "test"`, why is `a is b` True without explicit intern?
**A**: The compiler detected "test" is identifier-like and interned it at compile time. Both `a` and `b` reference the same compile-time constant from `co_consts`. This happens during bytecode compilation, not at runtime.
