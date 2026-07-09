# Part 14 — Interview Questions

## Beginner (50 Questions)

### Q1: What is the underlying data structure of a Python list?
**A**: A dynamic array of pointers (PyObject*). Not a linked list despite the name.

### Q2: What is the time complexity of accessing an element by index?
**A**: O(1). It's pointer arithmetic: `ob_item + i * 8`.

### Q3: What does `len(my_list)` do internally?
**A**: Reads the `ob_size` field of the PyListObject struct. O(1).

### Q4: Is a Python list homogeneous or heterogeneous?
**A**: Heterogeneous. It stores pointers, so elements can be any type.

### Q5: What happens when you append to a full list?
**A**: The internal pointer array is reallocated to a larger size (overallocation).

### Q6: What is the difference between `a = b` and `a = b.copy()`?
**A**: `a = b` creates an alias (both names reference the same object). `a = b.copy()` creates a new list with copied pointers (shallow copy).

### Q7: Can a list contain itself?
**A**: Yes. `a = []; a.append(a)` creates a circular reference.

### Q8: What is the time complexity of `append()`?
**A**: O(1) amortized. Occasionally O(n) when reallocation is needed.

### Q9: What is the time complexity of `insert(0, x)`?
**A**: O(n). All existing elements must shift right.

### Q10: What is the difference between `pop()` and `pop(0)`?
**A**: `pop()` is O(1) — removes last element. `pop(0)` is O(n) — removes first and shifts all.

### Q11: What does `del a[i]` do?
**A**: Decrefs the element at i, shifts all subsequent elements left, decrements ob_size. O(n).

### Q12: What's the difference between `remove()` and `del`?
**A**: `remove(x)` searches by value (O(n) search + O(n) shift). `del a[i]` removes by index directly (O(n) shift only).

### Q13: Can you use negative indexing?
**A**: Yes. `a[-1]` is `a[len(a)-1]`. Converted internally before access.

### Q14: What is slicing?
**A**: Creating a new list from a subsequence: `a[i:j]` copies pointers from index i to j-1.

### Q15: Does slicing create a view or a copy?
**A**: Always a copy (new list, new pointer array). Unlike NumPy.

### Q16: What is `a[:]`?
**A**: A shallow copy of the entire list. Equivalent to `a.copy()`.

### Q17: What is the time complexity of `x in my_list`?
**A**: O(n). Linear scan comparing each element.

### Q18: How do you check membership in O(1)?
**A**: Convert to a set: `x in my_set`.

### Q19: What does `a + b` do with lists?
**A**: Creates a NEW list containing elements from both. O(n+m).

### Q20: What does `a * 3` do?
**A**: Creates a new list with elements repeated 3 times. O(n×3).

### Q21: Is `a.sort()` stable?
**A**: Yes. Equal elements maintain original relative order.

### Q22: What's the difference between `sort()` and `sorted()`?
**A**: `sort()` sorts in-place (returns None). `sorted()` returns a new sorted list.

### Q23: What algorithm does Python use for sorting?
**A**: TimSort — hybrid merge sort + insertion sort.

### Q24: What's the complexity of `list.sort()`?
**A**: O(n log n) average/worst. O(n) best case (already sorted).

### Q25: What does `a.extend(b)` do?
**A**: Appends all elements from b to a in-place. O(k) where k = len(b).

### Q26: What's the difference between `append()` and `extend()`?
**A**: `append(x)` adds x as a single element. `extend(x)` adds each element from iterable x.

### Q27: What does `a.reverse()` return?
**A**: None. It reverses in-place. Use `a[::-1]` for a new reversed list.

### Q28: What is `a.index(x)`?
**A**: Returns the index of the first occurrence of x. O(n). Raises ValueError if not found.

### Q29: What does `a.count(x)` do?
**A**: Returns the number of times x appears. O(n) — must scan entire list.

### Q30: What is `a.clear()`?
**A**: Removes all elements, making the list empty. O(n) due to decrefs.

### Q31: What is a list comprehension?
**A**: `[expr for x in iterable]` — creates a list by evaluating expr for each x.

### Q32: Are list comprehensions faster than loops?
**A**: Yes, typically 30-50% faster due to specialized LIST_APPEND bytecode.

### Q33: What's a generator expression?
**A**: `(expr for x in iterable)` — lazy version, produces items on demand, O(1) memory.

### Q34: Can lists be dictionary keys?
**A**: No. Lists are mutable and unhashable. Use tuples instead.

### Q35: What is `id(a)` for a list?
**A**: The memory address of the PyListObject. Never changes even after mutations.

### Q36: What is `==` vs `is` for lists?
**A**: `==` compares contents (element-by-element). `is` checks if same object (same id).

### Q37: What is the empty list literal?
**A**: `[]` — creates a new PyListObject with no elements.

### Q38: What does `list()` with no arguments do?
**A**: Creates a new empty list. Equivalent to `[]`.

### Q39: Can you multiply a list by a non-integer?
**A**: No. `a * 2.5` raises TypeError. Must be integer.

### Q40: What does `a.copy()` return?
**A**: A shallow copy — new list, same element objects.

### Q41: What is the maximum list size?
**A**: `sys.maxsize` elements (2^63 - 1 on 64-bit). Practically limited by RAM.

### Q42: How do you create a list of n zeros?
**A**: `[0] * n`. Fast, single allocation.

### Q43: What's wrong with `[[]] * n`?
**A**: Creates n references to the SAME inner list. Mutating one mutates all.

### Q44: How do you flatten a list of lists?
**A**: `[x for sublist in nested for x in sublist]` or `itertools.chain.from_iterable()`.

### Q45: What does `a += [1,2,3]` do?
**A**: Calls `a.extend([1,2,3])`. Modifies a in-place (unlike `a = a + [1,2,3]` which creates new list).

### Q46: Is `a += b` the same as `a = a + b`?
**A**: No! `a += b` extends in-place (same id). `a = a + b` creates a NEW list (different id).

### Q47: What does `bool([])` return?
**A**: `False`. Empty lists are falsy. Non-empty lists are truthy.

### Q48: How do you check if a list is empty?
**A**: `if not my_list:` (Pythonic). Or `if len(my_list) == 0:` (explicit).

### Q49: What's the difference between a list and a tuple?
**A**: Lists are mutable (can modify after creation). Tuples are immutable (fixed after creation).

### Q50: Can a list contain different types simultaneously?
**A**: Yes. `[1, "hello", 3.14, None, [1,2]]` is valid.

---

## Intermediate (50 Questions)

### Q1: What is the growth factor of CPython lists?
**A**: ~1.125 (12.5%) for large lists. Formula: `newsize + newsize/8 + 6`, aligned to multiple of 4.

### Q2: What is the overallocation sequence?
**A**: 0, 4, 8, 16, 24, 32, 40, 52, 64, 76, 92, ...

### Q3: Why doesn't CPython double the capacity like std::vector?
**A**: Memory efficiency. 2× wastes up to 50%. 1.125× wastes ~12.5%. Still amortized O(1).

### Q4: What fields does PyListObject contain?
**A**: ob_refcnt, ob_type, ob_size (length), ob_item (pointer to array), allocated (capacity).

### Q5: What is the size of an empty PyListObject on 64-bit?
**A**: ~56 bytes (struct + GC header). ob_item is NULL.

### Q6: Why is ob_item a separate allocation from PyListObject?
**A**: So the list object's address (identity) doesn't change during resize. Only ob_item moves.

### Q7: What is the free list for lists?
**A**: A cache of up to 80 recently destroyed PyListObject structs, reused for new list creation.

### Q8: At what size does ob_item switch from pymalloc to system malloc?
**A**: When `allocated * 8 > 512 bytes`, i.e., more than 64 elements.

### Q9: How does CPython detect list mutation during sort?
**A**: Sets `allocated = -1`. Any resize attempt sees this sentinel and raises ValueError.

### Q10: What's the complexity of `a[i:j] = b` when len(b) != j-i?
**A**: O(n) due to shifting elements. Plus O(len(b)) for inserting new items.

### Q11: Explain the difference between shallow and deep copy for nested lists.
**A**: Shallow copies top-level pointers (inner lists are shared). Deep copy recursively creates new copies of all mutable objects.

### Q12: How does deepcopy handle circular references?
**A**: Uses a memo dictionary keyed by id(). When an already-copied object is encountered, returns the existing copy.

### Q13: Why is `sum(x**2 for x in range(n))` better than `sum([x**2 for x in range(n)])`?
**A**: The generator doesn't materialize a list. O(1) memory vs O(n).

### Q14: What is the LIST_APPEND bytecode?
**A**: A specialized instruction used in comprehensions that directly calls PyList_Append, bypassing method lookup and call overhead.

### Q15: Why are list comprehensions faster than loops with append?
**A**: LIST_APPEND avoids: (1) attribute lookup, (2) bound method creation, (3) Python CALL_FUNCTION overhead per iteration.

### Q16: What is galloping mode in TimSort?
**A**: Exponential search used during merge when one run consistently provides smaller elements. Copies blocks in bulk.

### Q17: What is a "run" in TimSort?
**A**: A maximal naturally ordered subsequence (ascending or strictly descending).

### Q18: What is minrun in TimSort?
**A**: The minimum run length (32-64). Short natural runs are extended with insertion sort.

### Q19: How much auxiliary space does sort() use?
**A**: O(n) — up to n/2 for the merge temporary buffer.

### Q20: What does `sys.getsizeof(a)` include for a list?
**A**: The PyListObject struct + the ob_item pointer array. Does NOT include the elements themselves.

### Q21: How do you get the total memory of a list including contained objects?
**A**: `pympler.asizeof.asizeof(a)` or manual recursive calculation.

### Q22: What's the cache locality problem with Python lists?
**A**: Objects are scattered on heap. Dereferencing pointers to elements causes random cache misses.

### Q23: Why is deque better than list for FIFO?
**A**: deque.popleft() is O(1). list.pop(0) is O(n) due to shifting.

### Q24: What does `collections.deque` use internally?
**A**: A doubly-linked list of fixed-size blocks (each holding 64 items). O(1) at both ends.

### Q25: What is the difference between `a.extend(b)` and `a += b`?
**A**: For lists, they're equivalent — both call list_extend in-place. `a = a + b` is different (creates new list).

### Q26: Can you reserve capacity in a Python list?
**A**: Not directly (no `reserve()` method). Workaround: `a = [None] * n` then overwrite.

### Q27: What happens to allocated capacity after many pops?
**A**: Shrinks when ob_size drops below allocated/2. Prevents permanent memory waste.

### Q28: Is `a.remove(x)` O(1) if x is at index 0?
**A**: No, still O(n). Even though search is O(1), the left-shift of remaining elements is O(n).

### Q29: What does `a.insert(len(a), x)` do?
**A**: Same as `a.append(x)`. No shifting needed since inserting at end.

### Q30: How does `reversed(a)` differ from `a[::-1]`?
**A**: `reversed(a)` returns an iterator (lazy, O(1) memory). `a[::-1]` creates a new list (O(n) memory).

### Q31: What is `array.array` and when to use it over list?
**A**: Stores typed C values inline (no pointers). Use for homogeneous numeric data with less memory.

### Q32: Why does `a = a + [x]` have different behavior from `a += [x]` for aliased variables?
**A**: `a = a + [x]` creates a new list (rebinds `a`). `a += [x]` modifies in-place (aliases still see the change).

### Q33: What is the time complexity of `a.index(x, start, stop)`?
**A**: O(stop - start). Linear scan within the specified range.

### Q34: How does list comparison (`a == b`) work?
**A**: Element-by-element comparison. Stops at first difference. O(min(n,m)) worst case.

### Q35: What is the complexity of `a * n` for a list?
**A**: O(len(a) * n). Creates new list, copies pointers len(a)*n times.

### Q36: Does `a * n` deep-copy the elements?
**A**: No. It copies pointers. All "copies" reference the same objects.

### Q37: What exception does `a[100]` raise for a 5-element list?
**A**: IndexError: list index out of range.

### Q38: What exception does `a.remove(x)` raise if x not in list?
**A**: ValueError: list.remove(x): x not in list.

### Q39: Is `list.sort(key=f)` equivalent to calling f during each comparison?
**A**: No. Keys are pre-computed once (n calls to f), then comparisons use the pre-computed keys.

### Q40: What is the Schwartzian transform?
**A**: Decorate-sort-undecorate pattern. Python's `key=` parameter implements this internally.

### Q41: What does `a.sort()` return?
**A**: None. It sorts in-place. Use `sorted(a)` to get a new sorted list.

### Q42: Can you sort a list of mixed types?
**A**: In Python 3, no (raises TypeError for incompatible types like int vs str). Python 2 allowed it.

### Q43: What is `bisect.insort(a, x)`?
**A**: Binary search for position (O(log n)) then insert (O(n) shift). Total O(n).

### Q44: How does `list.__contains__` work?
**A**: Linear scan calling `==` on each element until found or exhausted.

### Q45: What is `operator.itemgetter` used for with sort?
**A**: `key=itemgetter(1)` efficiently extracts index 1 from each element. Faster than `key=lambda x: x[1]`.

### Q46: How does `a.copy()` differ from `copy.copy(a)`?
**A**: Identical for lists. Both create shallow copies. `copy.copy` has slightly more overhead (dispatch logic).

### Q47: What is the GC header on a list?
**A**: 24 bytes prepended (gc_prev, gc_next, gc_refs) for cycle detection tracking.

### Q48: When does the GC visit a list?
**A**: During periodic collection (generation 0/1/2). Follows internal pointers looking for unreachable cycles.

### Q49: What is `Py_TRASHCAN` in list deallocation?
**A**: Prevents stack overflow from deeply nested structures. Defers deallocations to avoid deep recursion.

### Q50: How does `filter()` compare to list comprehension with `if`?
**A**: `list(filter(f, a))` is slightly slower due to function call overhead. `[x for x in a if f(x)]` uses LIST_APPEND.

---

## Senior (50 Questions)

### Q1: Derive the amortized O(1) complexity of append using the potential method.
**A**: Define Φ = 2*ob_size - allocated. Normal append: amortized = 1 + 2 = 3. Resize append: amortized = (n+1) + (2-n) = 3. Both O(1).

### Q2: Why does CPython's growth formula include `& ~3` (alignment to 4)?
**A**: Aligns allocated count to multiples of 4. Reduces fragmentation in memory allocators that work with aligned blocks. Also ensures the byte-size is a multiple of 32 (4×8).

### Q3: Explain the transition from pymalloc to system malloc during list growth.
**A**: pymalloc handles ≤ 512 bytes. At 64 elements, ob_item = 512 bytes. At 65 elements, it exceeds pymalloc and falls through to system malloc/realloc. This can cause a performance cliff.

### Q4: How does `realloc()` interact with pymalloc?
**A**: pymalloc has its own realloc. If the new size crosses the 512-byte boundary, it allocates via system malloc, copies data, then frees the pymalloc block. This is an expensive transition.

### Q5: Explain the mutation detection mechanism during sort.
**A**: `allocated = -1` before sort. Any operation calling `list_resize` triggers if statement checking allocated. Finding -1, it returns error. `ob_item = NULL` prevents direct access.

### Q6: Why does list dealloc decref items in reverse order?
**A**: Micro-optimization. CPython's reference counting often deallocates objects immediately when refcnt hits 0. Reverse order may improve locality for recently appended items.

### Q7: How does the free list improve performance?
**A**: Avoids malloc/free for the PyListObject struct on frequent list creation/destruction. Up to 80 structs are cached. The ob_item array is always freed (variable size, not cacheable).

### Q8: What is the impact of GC generations on lists?
**A**: Long-lived lists get promoted to higher generations, collected less frequently. Short-lived temp lists are collected in gen0. Lists with no reference cycles are deallocated by refcounting alone.

### Q9: Explain how `list_ass_slice` handles self-referential assignment like `a[1:3] = a`.
**A**: It first copies the RHS iterable's items to a temporary array before modifying the list. This prevents corruption from overlapping source/destination.

### Q10: What is the worst-case memory usage of TimSort?
**A**: O(n/2) ≈ O(n). The merge operation copies the shorter of two runs. Worst case: merging two equal-length runs requires n/2 temporary slots.

### Q11: How does galloping mode's MIN_GALLOP adapt?
**A**: MIN_GALLOP starts at 7. If galloping succeeds (finds large blocks), it decreases (more aggressive). If galloping fails (interleaved data), it increases (less aggressive). Adapts to data patterns.

### Q12: Explain the merge stack invariant and why it ensures O(n log n).
**A**: Invariant: |A| > |B| + |C| and |B| > |C| for consecutive runs A,B,C. This ensures stack depth is O(log n) and merges happen between roughly equal runs, giving balanced merge tree.

### Q13: What happens if a comparison function during sort raises an exception?
**A**: The sort is aborted. The list is left in a valid but partially sorted state. The original items are all preserved (no loss), just in an undefined order.

### Q14: How does CPython handle `a.sort(key=f)` when f raises?
**A**: Keys computed before sorting. If f raises during key computation, sort never starts. List unchanged. If exception during comparison of keys, sort aborts with items preserved.

### Q15: Explain the interaction between list resizing and address space layout randomization (ASLR).
**A**: ASLR randomizes heap base addresses. realloc may move ob_item to unpredictable addresses. This doesn't affect correctness (ob_item pointer is updated) but makes cache behavior less predictable.

### Q16: Why does CPython use `memmove` instead of `memcpy` in list operations?
**A**: memmove handles overlapping source/destination correctly. During insert/delete, the source and destination regions of ob_item overlap.

### Q17: What is the `Py_NewRef` pattern vs old `Py_INCREF` + assignment?
**A**: `Py_NewRef(v)` atomically increfs and returns v. Cleaner than `Py_INCREF(v); item[i] = v;`. Added in Python 3.10.

### Q18: How do sub-interpreters affect the list free list?
**A**: Since Python 3.12, the free list is per-interpreter state. Each sub-interpreter has its own cache of 80 list structs. No sharing between interpreters.

### Q19: What is the `valid_index` macro and why is it branchless?
**A**: `#define valid_index(i, limit) ((size_t)(i) < (size_t)(limit))`. Casting to unsigned makes negative indices become large positive numbers, failing the `<` check. One comparison covers both < 0 and >= limit.

### Q20: Explain how `PyList_SET_ITEM` differs from `PyList_SetItem`.
**A**: `SET_ITEM` is a macro — no refcount management, no bounds check. Used only for initialization of fresh lists. `SetItem` is a function that decrefs old value, increfs new, and checks bounds.

### Q21: How does CPython's list interact with the buffer protocol?
**A**: Lists do NOT support the buffer protocol. You can't get a memoryview of a list. This is because the elements are pointers to objects, not raw data.

### Q22: Explain the complexity of `a[::k] = b` (extended slice assignment with step).
**A**: O(n/k) elements must be replaced. Each replacement is O(1). But lengths must match exactly: `len(b) == len(a[::k])` or ValueError. No shifting needed.

### Q23: What optimizations does CPython have for `list(range(n))`?
**A**: `range` provides `__length_hint__`, allowing `list()` to pre-allocate the exact size. Then iterates and fills without any reallocation.

### Q24: How does `list.__mul__` handle memory for `[x] * n`?
**A**: Allocates exactly n slots (no overallocation). Copies the pointer n times. One incref of x by n (or n increfs of 1). Result has allocated == ob_size.

### Q25: What happens to memory when you do `a = a[10:]`?
**A**: Creates a new list (slice copy) with ob_size = len(a)-10. Old list's refcnt decrements. If old list has no other references, it's freed (decref elements, free ob_item, cache struct). Name 'a' now points to new list.

### Q26: Explain the complexity of converting a list to a set.
**A**: O(n) average. Each element is hashed (O(1) average) and inserted into the hash table. Total: n hashes + n insertions = O(n) average, O(n²) worst case (all hash collisions).

### Q27: Why can't you use `list.sort()` on a list of mixed types in Python 3?
**A**: Python 3 removed arbitrary type ordering. `int < str` raises TypeError. The sort's comparison encounters incompatible types and propagates the exception.

### Q28: How does Python's sort maintain stability across multiple sort passes?
**A**: Each sort is independently stable. Sorting by secondary key first, then primary key, gives correct multi-key sort because equal primary keys preserve secondary order.

### Q29: What is the worst case for TimSort's run detection?
**A**: Alternating elements (e.g., [1,0,1,0,...]). Every "run" is length 1 or 2. Must extend every run with insertion sort. Still O(n log n) overall.

### Q30: Explain the security implications of list internals.
**A**: Buffer overflow if ob_size > allocated (can't happen through Python API). Controlled via C API checks. Use-after-free if list is mutated during iteration (CPython detects some cases but not all via `RuntimeError: list changed size during iteration`).

### Q31: How does CPython detect "list changed size during iteration"?
**A**: The list iterator stores the initial `ob_size`. On each `__next__`, it checks if `ob_size` changed. If so, raises RuntimeError.

### Q32: What is the difference between `PyList_Append` and `_PyList_AppendTakeRef`?
**A**: `PyList_Append` increfs the item (borrowing semantics). `_PyList_AppendTakeRef` steals the reference (no incref needed — caller transfers ownership).

### Q33: Explain how `list.sort()` with key= avoids calling the key function O(n log n) times.
**A**: Keys are computed once upfront into a separate array (n calls). Sorting comparisons use this pre-computed key array. The original items are moved in parallel with their keys.

### Q34: What is the `ob_digit` field in PyLongObject that list elements point to?
**A**: The actual integer value storage. Digits are stored in base 2^30 (or 2^15 on 32-bit). Small ints (|value| < 2^30) have ob_size=1, one digit.

### Q35: How does CPython prevent use-after-free during list iteration with deletion?
**A**: It doesn't fully prevent it. `for x in a: a.remove(x)` may skip elements. The iterator checks ob_size changed and raises RuntimeError for size changes.

### Q36: Explain the optimization in `list_repeat` for small repeat counts.
**A**: For `a * 1`, returns a copy. For `a * 0`, returns empty list. For others, allocates exact size and uses memcpy for pointer blocks.

### Q37: How does `list.__iadd__` (+=) differ from `list.__add__` (+) at the C level?
**A**: `__iadd__` calls `list_extend` (modifies self, returns self). `__add__` calls `list_concat` (creates new list). The former reuses the object, the latter always allocates.

### Q38: What is the memory layout difference between `list(range(1000))` and manually appending 1000 items?
**A**: `list(range(1000))` pre-allocates exactly 1000 slots (allocated=1000). Manual appending results in overallocation: allocated ≈ 1112 (extra 12.5%).

### Q39: Explain the Py_TRASHCAN mechanism in list deallocation.
**A**: Prevents stack overflow from deeply nested lists like `a = [[[[...]]]]`. Sets a recursion counter. When too deep, defers deallocation to a queue processed later in a flat loop.

### Q40: How does the `tp_traverse` function work for lists in GC?
**A**: `list_traverse` visits each element by calling the visitor function on each ob_item[i]. This tells the GC about all objects the list references, enabling cycle detection.

### Q41: Why is `list_clear` called before `list_dealloc` in some cases?
**A**: The GC may call `tp_clear` to break cycles before deallocation. `list_clear` decrefs all items (potentially breaking cycles) without freeing the list struct itself.

### Q42: Explain how `ob_refcnt` overflow is handled.
**A**: On 64-bit, ob_refcnt is 8 bytes (max ~9.2 × 10^18). Practically impossible to overflow. Python 3.12+ has "immortal" objects with special refcnt values that never change.

### Q43: What is the `_PyObject_GC_TRACK` macro and why is it called in PyList_New?
**A**: Adds the list to the GC's doubly-linked list of tracked objects. Required because lists can form reference cycles. Must be called after the object is fully initialized.

### Q44: How does CPython handle `a[i] = a.pop()` atomically?
**A**: It doesn't need to be atomic. CPython evaluates `a.pop()` first (returns value, shrinks list), then assigns to `a[i]`. Single-threaded execution under GIL ensures this sequence is safe.

### Q45: Explain the difference between `list_resize` being called with newsize > ob_size vs newsize < ob_size.
**A**: Larger newsize: may grow allocation (overallocation formula). Smaller newsize: may shrink allocation (if < allocated/2). Both update ob_size.

### Q46: What happens when you pickle a list?
**A**: Pickle serializes the list structure and all contained objects recursively. On unpickle, new list and new objects are created. Circular references are handled via a memo.

### Q47: How does the `__sizeof__` method work for lists?
**A**: Returns `sizeof(PyListObject) + allocated * sizeof(PyObject*)`. This is what `sys.getsizeof()` calls.

### Q48: Explain the interaction between list and the `__length_hint__` protocol.
**A**: When `list(iterable)` is called, CPython queries `operator.length_hint(iterable)` to pre-size the list. Falls back to growing dynamically if hint unavailable or wrong.

### Q49: What is the performance impact of having a list in GC generation 2?
**A**: Gen2 is collected rarely. A long-lived list stays there. But on collection, the GC must traverse it (visiting all elements). Large lists in gen2 make gen2 collections slower.

### Q50: Explain how to implement a list-like container in C that outperforms CPython's list for a specific use case.
**A**: For homogeneous typed data: store values inline (no pointer indirection). For FIFO: use circular buffer. For sorted access: use B-tree. For concurrent access: use lock-free ring buffer. The key is eliminating the generality that CPython must maintain.
