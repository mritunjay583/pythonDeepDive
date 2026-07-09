# Part 11 — Interview Questions (150 Questions)

## Beginner (50 Questions)

**Q1**: What is a Python dictionary? **A**: A mutable, unordered (pre-3.7) / ordered (3.7+) collection of key-value pairs with O(1) average lookup.

**Q2**: What data structure underlies a dict? **A**: A hash table using open addressing with perturbation-based probing.

**Q3**: What does `len(d)` return? **A**: The number of active key-value pairs (reads `ma_used` field).

**Q4**: What types can be dict keys? **A**: Any hashable type (immutable built-ins, custom classes with `__hash__`).

**Q5**: Why can't lists be dict keys? **A**: Lists are mutable — their hash would change after mutation, breaking lookup.

**Q6**: What is `hash()`? **A**: A built-in that returns an integer hash value for hashable objects.

**Q7**: What happens on `d[key]` if key doesn't exist? **A**: Raises `KeyError`.

**Q8**: What does `d.get(key, default)` do? **A**: Returns value if key exists, else returns default (no exception).

**Q9**: Is dict ordered in Python 3.7+? **A**: Yes — insertion order is preserved as a language guarantee.

**Q10**: What's the time complexity of `key in d`? **A**: O(1) average.

**Q11**: What's the time complexity of `d[key] = value`? **A**: O(1) amortized.

**Q12**: What's `d.keys()` return? **A**: A view object reflecting current keys (not a list copy).

**Q13**: What's the difference between `d.keys()` and `list(d.keys())`? **A**: The view is dynamic (reflects changes), the list is a frozen snapshot.

**Q14**: How do you merge two dicts? **A**: `d1 | d2` (3.9+), `{**d1, **d2}`, or `d1.update(d2)`.

**Q15**: What does `d.pop(key)` do? **A**: Removes key and returns its value. Raises KeyError if missing.

**Q16**: What does `d.setdefault(key, value)` do? **A**: Returns `d[key]` if exists; otherwise sets `d[key] = value` and returns value.

**Q17**: What is `defaultdict`? **A**: A dict subclass that auto-creates missing keys using a factory function.

**Q18**: What is a hash collision? **A**: Two different keys mapping to the same hash table index.

**Q19**: How does CPython handle collisions? **A**: Open addressing — probes subsequent slots using a perturbation formula.

**Q20**: What is the load factor? **A**: Ratio of entries to table size. CPython resizes at 2/3.

**Q21**: What happens when you iterate over a dict? **A**: Iterates over keys in insertion order.

**Q22**: Can you modify a dict while iterating? **A**: No — raises `RuntimeError: dictionary changed size during iteration`.

**Q23**: What's `dict.items()`? **A**: A view of (key, value) tuple pairs.

**Q24**: How do you copy a dict? **A**: `d.copy()`, `dict(d)`, or `{**d}` (all shallow copies).

**Q25**: What's a shallow copy of a dict? **A**: New dict object, but values are shared (same references).

**Q26**: How do you deep copy a dict? **A**: `copy.deepcopy(d)` — recursively copies all mutable values.

**Q27**: What does `d.clear()` do? **A**: Removes all entries, making the dict empty.

**Q28**: What is `d.update(other)`? **A**: Merges `other` into `d`, overwriting existing keys.

**Q29**: Can dict values be any type? **A**: Yes — values have no restrictions (any object).

**Q30**: What's `dict.fromkeys(keys, value)`? **A**: Creates dict with given keys, all mapping to same value.

**Q31**: What does `del d[key]` do? **A**: Removes the key-value pair. Raises KeyError if missing.

**Q32**: What's the empty dict literal? **A**: `{}` — but `set()` is needed for empty set (not `{}`!).

**Q33**: How does `d1 == d2` work? **A**: True if same keys and same values. Order doesn't matter for equality.

**Q34**: What's the maximum dict size? **A**: Limited by `sys.maxsize` and available memory.

**Q35**: Are dict comprehensions possible? **A**: Yes: `{k: v for k, v in pairs}`.

**Q36**: What's `**kwargs` in a function? **A**: Collects keyword arguments into a dict.

**Q37**: What's `{**d1, **d2}`? **A**: Dict unpacking — creates new dict merging d1 and d2 (d2 wins on conflicts).

**Q38**: Can you use `None` as a dict key? **A**: Yes — `None` is hashable.

**Q39**: Can you use `True`/`False` as dict keys? **A**: Yes, but beware: `True == 1` and `False == 0`, so they share keys with integers.

**Q40**: What does `d.popitem()` return? **A**: Removes and returns the last (key, value) pair (LIFO since 3.7).

**Q41**: Is `{}` a dict or set? **A**: Dict. Empty set must be `set()`.

**Q42**: What's `collections.Counter`? **A**: A dict subclass for counting hashable objects.

**Q43**: What's `collections.OrderedDict`? **A**: Ordered dict (pre-3.7). Still useful for `move_to_end()` and order-sensitive equality.

**Q44**: Can dicts be nested? **A**: Yes. `d = {"a": {"b": 1}}`. Access with `d["a"]["b"]`.

**Q45**: What's the walrus operator with dicts? **A**: `if (val := d.get(key)) is not None:` — assign and check in one expression.

**Q46**: How do you iterate over keys and values simultaneously? **A**: `for k, v in d.items():`

**Q47**: What's `d | other` (Python 3.9+)? **A**: Creates a new dict merging d and other (other wins conflicts).

**Q48**: What's `d |= other`? **A**: In-place merge (updates d with other).

**Q49**: Can a dict key be a tuple? **A**: Yes, if all tuple elements are hashable.

**Q50**: What happens with `d[1]` and `d[True]`? **A**: Same key! `True == 1`, so `d[True]` accesses same slot as `d[1]`.

---

## Intermediate (50 Questions)

**Q1**: What is the CPython dict's table size constraint? **A**: Always a power of 2. Allows fast index calculation via bitwise AND.

**Q2**: What is the growth factor for dicts? **A**: 2× for large dicts, up to 4× for small dicts. Always doubling (or quadrupling) to next power of 2.

**Q3**: What's the compact dict layout? **A**: Sparse index table (small integers) + dense entries array (hash, key, value). Saves ~30-50% memory vs old layout.

**Q4**: What is key-sharing (split tables)? **A**: Multiple instances of same class share one PyDictKeysObject. Each instance only stores its own values array. Saves ~75% per instance.

**Q5**: When does key-sharing break? **A**: When an instance adds/removes attributes not in the shared layout.

**Q6**: What's `ma_version_tag`? **A**: Global version counter incremented on every dict change. Used for cached attribute lookup optimization.

**Q7**: How does CPython resolve collisions? **A**: Open addressing with perturbation: `i = (5*i + perturb + 1) & mask`, where perturb = hash >> 5 each iteration.

**Q8**: What is a tombstone/dummy entry? **A**: Marker in index table meaning "was here, deleted — keep probing past me." Prevents broken probe chains.

**Q9**: Why does CPython compare hashes before keys? **A**: Integer comparison is O(1). If hashes differ, keys definitely differ — avoids expensive `__eq__` calls.

**Q10**: What hash function does CPython use for strings? **A**: SipHash-1-3 with a random 128-bit key generated at process start.

**Q11**: Why is hash randomized? **A**: To prevent HashDoS attacks — attackers can't craft collision chains without knowing the key.

**Q12**: What's the load factor threshold? **A**: 2/3. Resize when table is 66.7% full.

**Q13**: What happens during dict resize? **A**: New larger table allocated, all active entries reinserted (preserving order), dummies eliminated, old table freed.

**Q14**: How does dict maintain insertion order? **A**: Dense entries array is append-only. New entries go at the end. Iteration walks entries sequentially.

**Q15**: What is `__missing__` in dict subclasses? **A**: Called when `__getitem__` doesn't find a key. `defaultdict` uses this.

**Q16**: How do dict views work? **A**: Views (`d.keys()`, `d.values()`, `d.items()`) are live references — they reflect dict changes dynamically.

**Q17**: Can dict views do set operations? **A**: `d.keys()` supports `&`, `|`, `-`, `^` (set-like). `d.items()` too (if values are hashable). `d.values()` does not.

**Q18**: What's `sys.getsizeof(d)` include? **A**: The dict object + PyDictKeysObject + index table + entries array. NOT the key/value objects.

**Q19**: What is `PYTHONHASHSEED`? **A**: Environment variable to control hash randomization. Set to integer for reproducible hashing, or "random" (default).

**Q20**: Why does `hash(-1) == -2`? **A**: CPython uses -1 internally as "not computed." Natural hash of -1 is changed to -2 to avoid confusion.

**Q21**: What's `dict.__contains__` complexity? **A**: O(1) average — same as lookup.

**Q22**: How does `d.update(other)` work internally? **A**: Iterates over `other`, inserting each key-value. May trigger resize if d grows past 2/3.

**Q23**: What's the difference between `d[key]` and `d.get(key)`? **A**: `d[key]` raises KeyError on miss. `d.get(key)` returns None (or default).

**Q24**: How do dict comprehensions compare to loop construction? **A**: Comprehensions are ~30% faster (optimized bytecode, pre-sized allocation from length hint).

**Q25**: What is `types.MappingProxyType`? **A**: A read-only view of a dict. Raises TypeError on modification attempts.

**Q26**: How does `ChainMap` work? **A**: Holds a list of dicts. Lookups search dicts in order. No copying.

**Q27**: What is `__slots__` relation to dicts? **A**: `__slots__` eliminates the instance `__dict__` entirely, storing attributes in fixed C-level slots. Major memory savings.

**Q28**: How does the GC interact with dicts? **A**: Dicts are GC-tracked (can form cycles). GC traverses all keys and values during collection.

**Q29**: What's a dict's memory after many deletions? **A**: Retains the large table (with dummies). Only shrinks on next resize-triggering operation.

**Q30**: How can you force a dict to reclaim memory after deletions? **A**: `d = dict(d)` or `d = {k: v for k, v in d.items()}` — creates compacted copy.

**Q31**: What's the `|` operator for dicts (PEP 584)? **A**: `d1 | d2` creates new dict. `d1 |= d2` updates in place. Added in Python 3.9.

**Q32**: How does `pickle` handle dicts? **A**: Serializes all key-value pairs. On unpickle, creates new dict and inserts pairs (preserving order).

**Q33**: What's the memory difference between `{}` and `dict()`? **A**: Identical result. `{}` may be slightly faster (literal → BUILD_MAP bytecode vs CALL_FUNCTION).

**Q34**: How does `json.loads()` create dicts? **A**: Parses JSON object into a Python dict. Keys are always strings. Order preserved (3.7+).

**Q35**: What's `functools.lru_cache` based on? **A**: An internal dict mapping argument tuples to results. Fixed size with LRU eviction.

**Q36**: How does Python's namespace work? **A**: Module/class/function namespaces are dicts. `globals()` and `locals()` return these dicts.

**Q37**: What's the complexity of `d.values()`? **A**: Creating the view: O(1). Iterating: O(n).

**Q38**: Can two dicts share the same keys object? **A**: Yes — key-sharing (split tables) for class instances. The PyDictKeysObject has a refcount.

**Q39**: What is dict "versioning" used for? **A**: Specializing interpreter (3.11+) caches attribute lookups. Version check = O(1) invalidation.

**Q40**: How does `str.__eq__` optimization help dicts? **A**: CPython has fast paths for comparing string objects (pointer identity, then hash comparison, then memcmp).

**Q41**: What's the initial dict size? **A**: 8 slots (2^3). Can hold 5 entries before first resize.

**Q42**: What happens with `d = {}; d[0] = 'a'; d[True] = 'b'; print(d)`? **A**: `{0: 'b'}` — because `0 == False == 0` and `True == 1`, but `0` was the first key stored. Actually: `True == 1 != 0`, so `d = {0: 'a', True: 'b'}`. Wait: `hash(0) == hash(False) == 0`, `0 == False`. And `hash(1) == hash(True) == 1`, `1 == True`. So `d[True]` when key 0 exists is a different slot. Result: `{0: 'a', True: 'b'}`.

**Q43**: What does `dict.__or__` return? **A**: A new dict (not a view, not in-place). Type is always dict (even if one operand is a subclass).

**Q44**: What's the difference between `d.copy()` and `copy.copy(d)`? **A**: Functionally identical for dicts. Both create shallow copies.

**Q45**: How are keyword arguments passed to functions? **A**: Packed into a dict by the caller. `**kwargs` receives a regular dict.

**Q46**: What optimization does CPython use for single-key dicts? **A**: The minimum table size is still 8. No special case for tiny dicts (unlike some languages with flat arrays for small maps).

**Q47**: What is `dict.__ior__` vs `dict.__or__`? **A**: `__ior__` is `|=` (in-place update, returns self). `__or__` is `|` (new dict).

**Q48**: Can you subclass dict? **A**: Yes. But `__missing__` is the main extension point. Built-in methods may bypass subclass overrides in C code.

**Q49**: What's `weakref.WeakValueDictionary`? **A**: Dict where values are weak references. Entries auto-removed when value objects are garbage collected.

**Q50**: How does Python implement `switch/match` on dicts? **A**: `match` with mapping patterns uses `d.keys()` and indexing. Not a hash table optimization — regular dict operations.

---

## Senior (50 Questions)

**Q1**: Derive the expected probe count for unsuccessful lookup with load factor 2/3.
**A**: E[probes] = 1/(1-α) = 1/(1-2/3) = 3. Average 3 probes before finding EMPTY.

**Q2**: Explain the perturbation probe formula `i = (5*i + perturb + 1) & mask`.
**A**: When perturb→0, becomes `i = (5i + 1) mod 2^k` which is a full permutation of {0,...,2^k-1}. The perturb term feeds higher hash bits in, preventing clustering from keys with same low bits.

**Q3**: Why does the probe formula use multiplication by 5?
**A**: 5 is coprime with all powers of 2. This guarantees `(5i + 1) mod 2^k` visits all 2^k positions before repeating. Any odd multiplier works; 5 was chosen empirically.

**Q4**: Explain the compact dict's two-level memory savings mathematically.
**A**: Old: m × 24 bytes (m = table_size). New: m × b + n × 24 (b = 1-8 bytes per index, n = active entries < m). Since n ≈ 2m/3 and b ≤ 4: new ≈ 4m + 16m = 20m vs old = 24m → ~17% savings minimum. For small m with b=1: m + 16m = 17m → 29% savings.

**Q5**: How does the version tag enable inline caching for LOAD_ATTR?
**A**: First LOAD_ATTR: looks up attribute in dict, caches result + dict version. Subsequent calls: compare stored version with current ma_version_tag. If equal (O(1) check): return cached value without dict lookup. If different: re-lookup and update cache.

**Q6**: Explain how SipHash prevents HashDoS.
**A**: SipHash is keyed — the 128-bit key is random per process and unknown to attackers. Without the key, an attacker can't compute hash values and therefore can't craft collision sets. Breaking SipHash requires ~2^64 work.

**Q7**: What is the memory layout difference between combined and split tables?
**A**: Combined: entries contain (hash, key, value) — all in dk_entries. Split: entries contain (hash, key, NULL) — values stored in separate ma_values array. Multiple PyDictObjects can share one PyDictKeysObject.

**Q8**: How does Python detect dict mutation during iteration?
**A**: The iterator stores `di_mod_count` (dict's modification counter at iterator creation). Each `__next__` checks if dict's counter changed. If so: RuntimeError.

**Q9**: Explain the relationship between dict and `__dict__` attribute.
**A**: Most objects store attributes in `obj.__dict__`, which is a regular PyDictObject. Class objects also have a `__dict__` (actually a mappingproxy wrapping the real dict). The `LOAD_ATTR` opcode directly accesses the underlying dict.

**Q10**: What is the "string-only" dict optimization?
**A**: When all keys are strings (dk_kind = DICT_KEYS_UNICODE), CPython uses a faster lookup path that skips type checking and uses Unicode-specific comparison.

**Q11**: How does `__slots__` interact with the dict system at the C level?
**A**: `__slots__` adds `tp_members` entries to the type object. Instance allocation omits `__dict__` (no dict slot in the object's memory). Attribute access uses direct struct offsets instead of dict lookup.

**Q12**: Explain the interaction between dict resize and garbage collection.
**A**: During resize, both old and new keys objects exist briefly. If GC runs during this window, it may traverse the new (incomplete) table. CPython uses careful ordering to ensure consistency.

**Q13**: What is the free list for dicts and why is it per-interpreter in 3.12+?
**A**: Up to 80 PyDictObject structs are cached for reuse. Per-interpreter (rather than global) to support sub-interpreters without cross-interpreter memory sharing.

**Q14**: How does `dict.pop(key, default)` differ from `del d[key]` internally?
**A**: Both do a lookup. `pop` returns the value (transfers ownership). `del` just decrefs. `pop` with default doesn't raise on missing key (returns default instead). One fewer lookup than `if key in d: val = d[key]; del d[key]`.

**Q15**: Explain how `dict.__eq__` works at the C level.
**A**: First compare `ma_used` (O(1)). If different: False. Then iterate entries of one dict, checking each key exists in the other with equal value. O(n) total.

**Q16**: What is the memory overhead of a single additional attribute on a class instance?
**A**: If key-sharing is maintained: 8 bytes (one pointer in values array). If key-sharing breaks: potentially hundreds of bytes for the new unshared dict.

**Q17**: How does the adaptive/specializing interpreter (3.11+) optimize dict operations?
**A**: `LOAD_ATTR` specializes based on observed types. For instances: caches the offset in the values array + keys version. For modules: caches the dict index + version. Avoids full lookup on repeated calls.

**Q18**: What happens to dict ordering when you do `d[existing_key] = new_value`?
**A**: The key's position is unchanged. Only the value pointer in the entries array is updated. Insertion order is not affected by value updates.

**Q19**: Explain the dk_indices variable-width encoding.
**A**: For tables ≤ 128 slots: 1-byte indices (int8). ≤ 32768: 2-byte (int16). ≤ 2^31: 4-byte (int32). Larger: 8-byte (int64). EMPTY=-1, DUMMY=-2 encoded as the signed version of each type.

**Q20**: How does CPython handle dict subclass overrides in C?
**A**: Many internal dict operations call `_PyDict_*` directly, bypassing Python-level `__getitem__`/`__setitem__`. Subclass overrides may not be called in all cases. This is a known limitation.

**Q21**: What is the "shared keys" dk_refcnt mechanism?
**A**: PyDictKeysObject has its own refcount (separate from Python refcnt). When a split table instance is created, it increfs the shared keys. When destroyed, it decrefs. When refcnt hits 0, keys object is freed.

**Q22**: Explain the interaction between hash tables and Python's `is` operator in dict lookup.
**A**: Dict lookup first does `key is entry.key` (pointer identity). If True: guaranteed match (no need for hash or eq comparison). This is why interned strings and small int keys are blazingly fast.

**Q23**: How does `dict.update()` handle different input types?
**A**: If input has `.keys()` method: iterate keys, lookup values. If iterable of pairs: iterate (k, v) pairs. If keyword args: merge from kwargs dict. Internally: calls `dict_merge()` or `dict_mergefromseq2()`.

**Q24**: What's the worst-case resize cost for a dict with n entries?
**A**: O(n) — must reinsert all n entries into new table. Each reinsertion probes for new position. With good hash: O(1) per reinsertion. Total: O(n).

**Q25**: How does CPython's dict compare to Java's HashMap?
**A**: Both: hash table, ~2/3 load factor. Differences: CPython uses open addressing (Java uses chaining with red-black trees for long chains since Java 8). CPython has compact layout. Java doubles capacity (CPython may quadruple for small dicts).

**Q26**: Explain why `dict(a=1, b=2)` is slower than `{"a": 1, "b": 2}`.
**A**: The literal uses BUILD_MAP bytecode (direct construction). The constructor call has function call overhead + kwargs dict creation + dict_merge into new dict.

**Q27**: What is DKIX_ERROR and when does it occur?
**A**: Value -3 in some versions. Returned when a comparison raises an exception during lookup. Signals the caller to propagate the exception.

**Q28**: How does `json.dumps(d)` interact with dict ordering?
**A**: Since Python 3.7, `json.dumps` outputs keys in insertion order by default. Pre-3.7: order was undefined.

**Q29**: What is the `Py_TPFLAGS_MAPPING` flag?
**A**: Added in Python 3.10 for pattern matching. Marks a type as a mapping (supports `match` with `{key: value}` patterns). Set on dict and dict subclasses.

**Q30**: Explain memory fragmentation issues with dicts.
**A**: Frequent create/resize/destroy cycles fragment pymalloc pools. Large dicts (>512 bytes) use system malloc which may fragment the heap. Mitigation: reuse dicts when possible.

**Q31**: How does the `unicodekeys_lookup_unicode` fast path work?
**A**: When both the stored key and lookup key are exact `str` type (not subclass), uses `_PyUnicode_EQ` which compares by kind + length + memcmp. Skips general `PyObject_RichCompareBool`.

**Q32**: What optimizations does CPython apply for `d = {}`? 
**A**: `BUILD_MAP 0` creates an empty dict using `PyDict_New()`. The empty dict initially shares a global "empty keys" singleton — no real allocation until first insert.

**Q33**: How does CPython handle `d[k]` when k's `__hash__` or `__eq__` has side effects?
**A**: The lookup may trigger arbitrary Python code. CPython guards against re-entrancy issues — after calling `__eq__`, it re-validates that the dict hasn't been mutated.

**Q34**: What's the relationship between dict operations and the GIL?
**A**: Individual dict operations (get, set, delete) are atomic under the GIL — they complete without other threads running Python code between steps. But sequences of operations are not atomic.

**Q35**: Explain the `LOAD_GLOBAL` optimization using dict versioning.
**A**: `LOAD_GLOBAL x` checks the module dict for `x`. With versioning: cache the dict version + result. On subsequent calls: if version unchanged → return cached (O(1)). This is the "inline cache" mechanism.

**Q36**: How does `vars(obj)` relate to dict internals?
**A**: `vars(obj)` returns `obj.__dict__` directly (the actual dict, not a copy). Mutations to the result affect the object.

**Q37**: What is the "compact dict" impact on `**kwargs` passing?
**A**: kwargs dict preserves argument order (3.7+ guarantee). Function receives kwargs in the order they were specified at the call site.

**Q38**: Explain the dk_log2_size vs direct size storage choice.
**A**: Storing log2 instead of size saves 7 bytes (uint8 vs Py_ssize_t). Since size is always a power of 2, log2 is lossless. Compute actual size with `1 << dk_log2_size`.

**Q39**: How does `dict.__sizeof__` work?
**A**: Returns `sizeof(PyDictObject) + keys_size` where keys_size = header + indices + entries. Does NOT include referenced key/value objects.

**Q40**: What's the performance impact of hash collisions in practice?
**A**: With SipHash and 2/3 load factor, collision rate is very low. Benchmarks show average 1.1-1.3 probes per lookup in real-world code. Performance is near-ideal.

**Q41**: Explain how `dict.keys() & set` works internally.
**A**: `dict_keys.__and__` creates a new set, iterating over the smaller operand and checking membership in the larger. O(min(n,m)).

**Q42**: What happens when you inherit from dict and override `__setitem__`?
**A**: `dict.update()` and `dict.__init__` may call the C-level `insertdict` directly, bypassing your `__setitem__`. Use `collections.UserDict` for reliable subclassing.

**Q43**: How does Python's match/case with mapping patterns work internally?
**A**: Uses `PyMapping_Keys()` to get available keys, then `PyObject_GetItem()` for each pattern key. Not a specialized hash table operation.

**Q44**: What's the minimum possible memory for a dict with 1 entry?
**A**: ~232 bytes typical. PyDictObject(48) + PyDictKeysObject header(40) + indices(8×1=8) + entries(1×24=24) ≈ 120 bytes struct. Plus GC overhead and alignment → ~184-232 bytes.

**Q45**: Explain how the free list interacts with dict creation patterns.
**A**: Creating and destroying dicts in loops reuses free list structs (no malloc). The PyDictKeysObject is separately allocated each time (not cached on free list).

**Q46**: What is the "empty keys" singleton?
**A**: A shared PyDictKeysObject used by all empty dicts. Has 0 entries, size 0. First insert replaces it with a real keys object. Saves allocation for the many temporary empty dicts.

**Q47**: How does `sys.intern()` interact with dict performance?
**A**: Interned strings are guaranteed to have the same pointer for same content. Dict lookup with interned keys often resolves at the `key is entry.key` identity check — O(1) without even comparing strings.

**Q48**: What's the overhead of `d.keys()` view creation?
**A**: O(1). The view just stores a pointer to the dict. No iteration until the view is consumed.

**Q49**: How do type annotations (`d: dict[str, int]`) affect dict internals?
**A**: Not at all at runtime. Annotations are metadata stored separately. The dict operates the same regardless of declared types. Only static type checkers use this info.

**Q50**: Explain the trade-off between CPython's 2/3 load factor and alternatives.
**A**: 2/3 gives ~1.5 probes average. Lower (1/2): fewer probes but 2× memory. Higher (3/4): more collisions but less memory. 2/3 is the empirically optimal balance for Python's typical small-dict-heavy workloads.
