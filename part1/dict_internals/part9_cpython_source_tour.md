# Part 9 — CPython Source Tour

## 9.1 Key Files

```
cpython/
├── Include/
│   ├── dictobject.h              ← Public C API (PyDict_New, PyDict_GetItem, etc.)
│   └── cpython/
│       └── dictobject.h          ← PyDictObject struct, internal API
├── Objects/
│   ├── dictobject.c              ← ALL dict implementation (~5800 lines)
│   ├── dictnotes.txt             ← Design notes (Tim Peters, Raymond Hettinger)
│   ├── setobject.c               ← Set implementation
│   └── clinic/
│       └── dictobject.c.h        ← Auto-generated argument clinic
├── Python/
│   └── pyhash.c                  ← Hash function implementations
└── Lib/
    └── collections/__init__.py   ← OrderedDict (Python layer)
```

---

## 9.2 PyDict_New — Creating a Dict

```c
// Objects/dictobject.c
PyObject *
PyDict_New(void)
{
    PyDictKeysObject *keys = new_keys_object(PyDict_LOG_MINSIZE, 0);
    if (keys == NULL)
        return NULL;
    return new_dict(keys, NULL, 0, 0);
}

// PyDict_LOG_MINSIZE = 3  →  initial table size = 2^3 = 8
```

```c
static PyObject *
new_dict(PyDictKeysObject *keys, PyDictValues *values,
         Py_ssize_t used, int free_values_on_failure)
{
    PyDictObject *mp;
    
    // Try free list first (reuse recently destroyed dicts)
    mp = _Py_FREELIST_POP(PyDictObject, dicts);
    if (mp == NULL) {
        mp = PyObject_GC_New(PyDictObject, &PyDict_Type);
        if (mp == NULL) { /* ... error handling ... */ }
    }
    
    mp->ma_keys = keys;
    mp->ma_values = values;
    mp->ma_used = used;
    mp->ma_version_tag = DICT_NEXT_VERSION(interp);
    
    ASSERT_CONSISTENT(mp);
    _PyObject_GC_TRACK(mp);
    return (PyObject *)mp;
}
```

Key observations:
- Free list reuse (like list objects)
- Initial table size is 8 (smallest power of 2 that's practical)
- GC tracked immediately (dicts can form cycles)
- Version tag assigned from global counter

---

## 9.3 new_keys_object — Allocating the Keys Structure

```c
static PyDictKeysObject *
new_keys_object(uint8_t log2_size, bool unicode)
{
    Py_ssize_t usable;
    PyDictKeysObject *dk;
    Py_ssize_t es = unicode ? sizeof(PyDictUnicodeEntry) : sizeof(PyDictKeyEntry);
    Py_ssize_t size = (Py_ssize_t)1 << log2_size;  // 2^log2_size
    
    usable = USABLE_FRACTION(size);  // size * 2 / 3
    
    // Allocate: struct + indices array + entries array
    // All in one contiguous block!
    dk = PyObject_Malloc(sizeof(PyDictKeysObject)
                         + (size << log2_index_bytes)    // indices
                         + es * usable);                 // entries
    
    dk->dk_refcnt = 1;
    dk->dk_log2_size = log2_size;
    dk->dk_kind = unicode ? DICT_KEYS_UNICODE : DICT_KEYS_GENERAL;
    dk->dk_nentries = 0;
    dk->dk_usable = usable;
    
    // Initialize all indices to EMPTY (-1)
    memset(DK_INDICES(dk), 0xff, size << log2_index_bytes);
    
    return dk;
}
```

Key observations:
- **Single allocation** for struct + indices + entries (cache-friendly!)
- USABLE_FRACTION = 2/3 of table size
- Indices initialized to 0xff bytes = -1 (EMPTY) for all sizes
- The unicode vs general distinction allows optimized paths for string-only dicts

---

## 9.4 dict_getitem — The Lookup

```c
// Public API (borrowed reference):
PyObject *
PyDict_GetItem(PyObject *op, PyObject *key)
{
    Py_hash_t hash;
    
    if (!PyUnicode_CheckExact(key) ||
        (hash = unicode_get_hash(key)) == -1) {
        hash = PyObject_Hash(key);
        if (hash == -1) {
            PyErr_Clear();
            return NULL;
        }
    }
    
    PyObject *value;
    Py_ssize_t ix = _Py_dict_lookup(mp, key, hash, &value);
    if (ix < 0) return NULL;
    return value;
}
```

The actual lookup (simplified from `_Py_dict_lookup`):
```c
static Py_ssize_t
_Py_dict_lookup(PyDictObject *mp, PyObject *key, Py_hash_t hash, PyObject **value_addr)
{
    PyDictKeysObject *dk = mp->ma_keys;
    size_t mask = DK_MASK(dk);
    size_t perturb = hash;
    size_t i = (size_t)hash & mask;
    
    for (;;) {
        Py_ssize_t ix = dictkeys_get_index(dk, i);
        
        if (ix == DKIX_EMPTY) {
            *value_addr = NULL;
            return DKIX_EMPTY;
        }
        if (ix >= 0) {
            PyDictKeyEntry *ep = &DK_ENTRIES(dk)[ix];
            assert(ep->me_hash != -1);
            if (ep->me_key == key) {              // Identity fast-path
                *value_addr = ep->me_value;
                return ix;
            }
            if (ep->me_hash == hash) {            // Hash match
                PyObject *startkey = ep->me_key;
                Py_INCREF(startkey);
                int cmp = PyObject_RichCompareBool(startkey, key, Py_EQ);
                Py_DECREF(startkey);
                if (cmp > 0) {                    // Key match!
                    *value_addr = ep->me_value;
                    return ix;
                }
            }
        }
        // Probe next slot
        perturb >>= PERTURB_SHIFT;
        i = (i * 5 + perturb + 1) & mask;
    }
}
```

---

## 9.5 insertdict — Inserting a Key-Value Pair

```c
static int
insertdict(PyDictObject *mp, PyObject *key, Py_hash_t hash, PyObject *value)
{
    PyObject *old_value;
    Py_ssize_t ix;
    
    // First, try to find if key already exists
    ix = _Py_dict_lookup(mp, key, hash, &old_value);
    
    if (ix == DKIX_EMPTY) {
        // Key not found — insert new entry
        assert(old_value == NULL);
        
        if (mp->ma_keys->dk_usable <= 0) {
            // No space! Need to resize first
            if (insertion_resize(mp, 1) < 0)
                return -1;
        }
        
        // Add to entries array
        Py_ssize_t hashpos;  // position in index table
        // ... find the insertion slot using same probe ...
        
        PyDictKeysObject *keys = mp->ma_keys;
        Py_ssize_t dk_nentries = keys->dk_nentries;
        
        // Store in next entry slot
        PyDictKeyEntry *ep = &DK_ENTRIES(keys)[dk_nentries];
        ep->me_hash = hash;
        ep->me_key = Py_NewRef(key);
        ep->me_value = Py_NewRef(value);
        
        // Update index table
        dictkeys_set_index(keys, hashpos, dk_nentries);
        
        keys->dk_usable--;
        keys->dk_nentries++;
        mp->ma_used++;
    }
    else {
        // Key exists — update value
        assert(old_value != NULL);
        Py_INCREF(value);
        DK_ENTRIES(mp->ma_keys)[ix].me_value = value;
        Py_DECREF(old_value);
    }
    
    mp->ma_version_tag = DICT_NEXT_VERSION(interp);
    return 0;
}
```

---

## 9.6 dictresize — Resizing the Table

```c
static int
dictresize(PyDictObject *mp, uint8_t log2_newsize, int unicode)
{
    Py_ssize_t newsize = (Py_ssize_t)1 << log2_newsize;
    PyDictKeysObject *oldkeys = mp->ma_keys;
    
    // Allocate new keys object
    PyDictKeysObject *newkeys = new_keys_object(log2_newsize, unicode);
    if (newkeys == NULL) return -1;
    
    // Reinsert all active entries into new table
    Py_ssize_t numentries = oldkeys->dk_nentries;
    PyDictKeyEntry *oldentries = DK_ENTRIES(oldkeys);
    PyDictKeyEntry *newentries = DK_ENTRIES(newkeys);
    
    Py_ssize_t newi = 0;
    for (Py_ssize_t i = 0; i < numentries; i++) {
        PyDictKeyEntry *ep = &oldentries[i];
        if (ep->me_value != NULL) {
            // Active entry — reinsert
            newentries[newi] = *ep;  // Copy entry
            
            // Find new index position
            size_t mask = newsize - 1;
            size_t j = ep->me_hash & mask;
            // Probe until empty slot found
            while (dictkeys_get_index(newkeys, j) != DKIX_EMPTY) {
                j = (j * 5 + (ep->me_hash >> 5) + 1) & mask;
                // Simplified — actual code does full perturb
            }
            dictkeys_set_index(newkeys, j, newi);
            newi++;
        }
        // Skip deleted entries (value == NULL)
    }
    
    newkeys->dk_nentries = newi;
    newkeys->dk_usable = USABLE_FRACTION(newsize) - newi;
    
    mp->ma_keys = newkeys;
    // Free old keys
    dictkeys_decref(oldkeys);
    
    return 0;
}
```

Key observations:
- All entries are reinserted in order (preserving insertion order!)
- Deleted entries (value==NULL) are skipped → compaction
- New indices computed via fresh probing in new table
- Old keys object freed after new one is ready

---

## 9.7 dict_dealloc — Destroying a Dict

```c
static void
dict_dealloc(PyDictObject *mp)
{
    PyObject_GC_UnTrack(mp);
    Py_TRASHCAN_BEGIN(mp, dict_dealloc)
    
    // Decref all entries
    Py_ssize_t i = mp->ma_keys->dk_nentries;
    PyDictKeyEntry *entries = DK_ENTRIES(mp->ma_keys);
    while (--i >= 0) {
        Py_XDECREF(entries[i].me_key);
        Py_XDECREF(entries[i].me_value);
    }
    
    // Free/decref keys object
    dictkeys_decref(mp->ma_keys);
    
    // Free values array (split table only)
    if (mp->ma_values) free_values(mp->ma_values);
    
    // Cache on free list or free
    // ...
    
    Py_TRASHCAN_END
}
```

---

## 9.8 Key Macros and Constants

```c
// Load factor: 2/3
#define USABLE_FRACTION(n)  (((n) << 1) / 3)   // n * 2 / 3

// Minimum size
#define PyDict_LOG_MINSIZE  3  // 2^3 = 8 slots

// Perturb shift amount
#define PERTURB_SHIFT  5

// Index table access (variable-width):
#define DK_MASK(dk)  ((1 << (dk)->dk_log2_size) - 1)

// Get entries pointer (immediately after indices in memory):
#define DK_ENTRIES(dk)  ((PyDictKeyEntry*)(&(dk)->dk_indices[(1 << (dk)->dk_log2_size) << (dk)->dk_log2_index_bytes]))

// Sentinel values for indices:
#define DKIX_EMPTY  (-1)
#define DKIX_DUMMY  (-2)
```

---

## 9.9 The Version Tag (PEP 509)

```c
// Every modification increments the global version counter:
#define DICT_NEXT_VERSION(interp) \
    ((interp)->dict_state.global_version++)

// Used by:
// - LOAD_ATTR optimization (cached attribute lookups)
// - Specializing adaptive interpreter (Python 3.11+)
// - Detecting dict changes without comparing contents
```

This allows fast "has this dict changed?" checks:
```python
# Internally, cached LOAD_ATTR stores the dict version
# On next access: compare stored version with current
# If same: use cached value (no lookup needed!)
# If different: re-lookup and update cache
```

---

## 9.10 Summary of Key Functions

| Function | Purpose | Complexity |
|----------|---------|------------|
| `PyDict_New()` | Create empty dict | O(1) |
| `_Py_dict_lookup()` | Find key in dict | O(1) avg |
| `insertdict()` | Insert/update key-value | O(1) amortized |
| `dictresize()` | Grow/shrink table | O(n) |
| `PyDict_GetItem()` | Public lookup API | O(1) avg |
| `PyDict_SetItem()` | Public insert API | O(1) amortized |
| `PyDict_DelItem()` | Public delete API | O(1) avg |
| `dict_dealloc()` | Destroy dict | O(n) |
| `PyDict_Contains()` | `key in d` | O(1) avg |
| `dict_merge()` | `d.update(other)` | O(len(other)) |

---

## 9.11 Interview Questions — Part 9

**Q1**: Where is the dict implementation in CPython source?
**A**: `Objects/dictobject.c` (~5800 lines). Struct definition in `Include/cpython/dictobject.h`.

**Q2**: How is the PyDictKeysObject allocated?
**A**: As a single contiguous block containing the struct header + index table + entries array. This ensures cache locality.

**Q3**: What is `PERTURB_SHIFT` and why is it 5?
**A**: The number of bits shifted from the perturb value each probe iteration. 5 was empirically chosen to give good distribution — it feeds 5 new bits of the hash into each probe step.

**Q4**: What is `ma_version_tag`?
**A**: A global counter incremented on every dict modification. Used for optimization (inline caching of attribute lookups) — allows O(1) "has this dict changed?" checks.

**Q5**: Does CPython have a free list for dicts?
**A**: Yes. Recently destroyed PyDictObject structs are cached for reuse, similar to the list free list.
