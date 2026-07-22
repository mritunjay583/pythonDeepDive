# Phase 1, Chapter 2c — The Danger of Shared Memory: Race Conditions

## The Dark Side of Threads

Threads share memory. That's their superpower AND their curse. When two threads read/write the same data without coordination, you get **race conditions** — bugs that appear randomly, are impossible to reproduce consistently, and will ruin your life.

---

## The Classic Race Condition

```python
# race_condition.py — Demonstrates the problem
import threading

counter = 0

def increment():
    global counter
    for _ in range(1_000_000):
        counter += 1  # THIS IS NOT ATOMIC!

# Create 2 threads that both increment the same counter
t1 = threading.Thread(target=increment)
t2 = threading.Thread(target=increment)

t1.start()
t2.start()
t1.join()
t2.join()

print(f"Expected: 2,000,000")
print(f"Got:      {counter:,}")
print(f"Lost:     {2_000_000 - counter:,} increments!")
```

```bash
$ python3 race_condition.py
Expected: 2,000,000
Got:      1,437,692
Lost:     562,308 increments!

$ python3 race_condition.py    # Run again — different result!
Expected: 2,000,000
Got:      1,521,043
Lost:     478,957 increments!
```

**Wait — in CPython with the GIL, shouldn't this be safe?** Actually no! `counter += 1` compiles to MULTIPLE bytecode instructions. The GIL can release between them.

---

## Why Does This Happen? — The Non-Atomic Operation

`counter += 1` in Python compiles to:

```python
import dis
dis.dis(compile("counter += 1", "", "exec"))

#   LOAD_GLOBAL    0 (counter)    ← Step 1: Read current value
#   LOAD_CONST     1 (1)          ← Step 2: Load the constant 1
#   BINARY_ADD                     ← Step 3: Add them
#   STORE_GLOBAL   0 (counter)    ← Step 4: Write result back
```

**The problem: the GIL can release between any of these steps.** Here's the race:

```
TIME ──────────────────────────────────────────────────────────────►

counter = 100 (current value in memory)

Thread 1:                          Thread 2:
─────────                          ─────────
LOAD_GLOBAL counter → gets 100
                                   LOAD_GLOBAL counter → gets 100 (SAME!)
LOAD_CONST 1
BINARY_ADD → 101
                                   LOAD_CONST 1
                                   BINARY_ADD → 101 (ALSO 101!)
STORE_GLOBAL counter = 101
                                   STORE_GLOBAL counter = 101 (OVERWRITES!)

# Result: counter = 101 (should be 102!)
# We lost one increment!
```

Both threads read 100, both compute 101, both write 101. We did TWO increments but counter only went up by ONE. This is a **lost update**.

---

## Visualizing the Race (What's Actually Happening on CPU)

```
CPU Core 0 (Thread 1):          CPU Core 1 (Thread 2):
┌─────────────────────┐         ┌─────────────────────┐
│ Read counter=100    │         │                     │
│ from shared memory  │         │                     │
│                     │         │ Read counter=100    │ ← STALE!
│ Compute 100+1=101  │         │ from shared memory  │
│                     │         │                     │
│ Write counter=101   │         │ Compute 100+1=101  │
│ to shared memory    │         │                     │
│                     │         │ Write counter=101   │ ← OVERWRITES!
│                     │         │ to shared memory    │
└─────────────────────┘         └─────────────────────┘

Shared Memory (Heap):
counter: 100 → 101 → 101 (should be 102!)
```

---

## The Fix: Locks (Mutex)

A **mutex** (mutual exclusion lock) ensures only ONE thread can execute a section of code at a time:

```python
# race_condition_fixed.py
import threading

counter = 0
lock = threading.Lock()  # Create a mutex

def increment():
    global counter
    for _ in range(1_000_000):
        lock.acquire()      # 🔒 Lock — only one thread can pass
        counter += 1        # Safe! No other thread can be here
        lock.release()      # 🔓 Unlock — next thread can enter

# Or cleaner with context manager:
def increment_clean():
    global counter
    for _ in range(1_000_000):
        with lock:          # 🔒 Acquire on enter, 🔓 release on exit
            counter += 1

t1 = threading.Thread(target=increment_clean)
t2 = threading.Thread(target=increment_clean)
t1.start()
t2.start()
t1.join()
t2.join()

print(f"Expected: 2,000,000")
print(f"Got:      {counter:,}")  # Always 2,000,000!
```

```bash
$ python3 race_condition_fixed.py
Expected: 2,000,000
Got:      2,000,000       ← Always correct now!
```

**But there's a cost:** Locks are SLOW. Each lock acquire/release is a system call or at minimum an atomic CPU instruction. And while one thread holds the lock, other threads are BLOCKED (sleeping). With heavy contention, threads spend more time waiting than working.

---

## What a Mutex Looks Like in Memory

```
lock = threading.Lock()

In kernel/memory:
┌──────────────────────────────────────┐
│ Lock (pthread_mutex_t)               │
│                                      │
│ state: 0 = unlocked, 1 = locked     │
│ owner: TID of thread holding it      │
│ waiters: list of blocked threads     │
│                                      │
│ Implementation:                      │
│ Uses CPU atomic instruction:         │
│   CMPXCHG (compare-and-swap)        │
│   or LOCK XCHG (locked exchange)    │
└──────────────────────────────────────┘

Thread 1 calls lock.acquire():
  CPU: CMPXCHG [lock_addr], 0 → 1    (atomically: if lock==0, set to 1)
  Success! Thread 1 owns the lock.

Thread 2 calls lock.acquire():
  CPU: CMPXCHG [lock_addr], 0 → 1    (atomically: if lock==0, set to 1)
  FAILS! Lock is 1 (owned by Thread 1).
  Thread 2 → added to waiters list → state = SLEEPING
  (Thread 2 is now blocked, uses ZERO CPU)

Thread 1 calls lock.release():
  CPU: set lock = 0
  Kernel: wake up first thread in waiters list
  Thread 2 wakes up, retries acquire → succeeds!
```

---

## Seeing Lock Contention in Practice

```python
# lock_contention.py — Measure the cost of locks
import threading
import time

counter = 0
lock = threading.Lock()

def increment_no_lock(n):
    global counter
    for _ in range(n):
        counter += 1

def increment_with_lock(n):
    global counter
    for _ in range(n):
        with lock:
            counter += 1

N = 5_000_000

# Single-threaded, no lock
counter = 0
start = time.perf_counter()
increment_no_lock(N)
t_single = time.perf_counter() - start
print(f"Single-threaded, no lock:   {t_single:.3f}s  counter={counter:,}")

# Two threads, no lock (BUGGY but fast)
counter = 0
start = time.perf_counter()
t1 = threading.Thread(target=increment_no_lock, args=(N//2,))
t2 = threading.Thread(target=increment_no_lock, args=(N//2,))
t1.start(); t2.start(); t1.join(); t2.join()
t_nolock = time.perf_counter() - start
print(f"Two threads, no lock:       {t_nolock:.3f}s  counter={counter:,} (WRONG!)")

# Two threads, with lock (correct but slow)
counter = 0
start = time.perf_counter()
t1 = threading.Thread(target=increment_with_lock, args=(N//2,))
t2 = threading.Thread(target=increment_with_lock, args=(N//2,))
t1.start(); t2.start(); t1.join(); t2.join()
t_locked = time.perf_counter() - start
print(f"Two threads, with lock:     {t_locked:.3f}s  counter={counter:,} (CORRECT)")
print(f"\nLock overhead: {t_locked/t_single:.1f}x slower than single-threaded!")
```

```bash
$ python3 lock_contention.py
Single-threaded, no lock:   0.312s  counter=5,000,000
Two threads, no lock:       0.287s  counter=4,235,671 (WRONG!)
Two threads, with lock:     2.841s  counter=5,000,000 (CORRECT)

Lock overhead: 9.1x slower than single-threaded!
```

**This is why "just add threads" doesn't always help.** If threads constantly fight over the same lock, you get WORSE performance than single-threaded code. The lock adds overhead and serializes execution.

---

## Common Thread Safety Problems

### Problem 1: Lost Update (we just saw this)
```python
# Two threads read-modify-write the same variable
counter += 1  # NOT ATOMIC → race condition
```

### Problem 2: Inconsistent Read
```python
# Thread 1 updates a data structure
user.name = "Alice"
user.email = "alice@example.com"

# Thread 2 reads between the two writes:
print(user.name)   # "Alice" (new)
print(user.email)  # "bob@old.com" (old!) — inconsistent!
```

### Problem 3: Use-After-Free / Dangling Reference
```python
# Thread 1
data = shared_dict.pop("key")  # Remove from dict

# Thread 2 (concurrent)
value = shared_dict["key"]  # KeyError! It was just removed!
```

### Problem 4: Iterator Invalidation
```python
# Thread 1: iterating
for item in shared_list:
    process(item)

# Thread 2: modifying during iteration
shared_list.append(new_item)  # RuntimeError: dictionary/list changed during iteration
```

---

## Thread-Safe Data Structures in Python

Python provides `queue.Queue` — a thread-safe FIFO queue:

```python
# safe_queue.py — The correct way to communicate between threads
import threading
import queue
import time

# Thread-safe queue (has internal locks)
work_queue = queue.Queue()
results_queue = queue.Queue()

def producer(producer_id):
    """Produces work items."""
    for i in range(5):
        item = f"Task-{producer_id}-{i}"
        work_queue.put(item)  # Thread-safe! Has internal lock.
        print(f"  [Producer-{producer_id}] Put: {item}")
        time.sleep(0.1)

def consumer(consumer_id):
    """Consumes work items."""
    while True:
        try:
            item = work_queue.get(timeout=2)  # Blocks until item available
            print(f"  [Consumer-{consumer_id}] Processing: {item}")
            time.sleep(0.2)  # Simulate work
            results_queue.put(f"{item} → DONE")
            work_queue.task_done()
        except queue.Empty:
            print(f"  [Consumer-{consumer_id}] No more work, exiting.")
            break

# 2 producers, 3 consumers
producers = [threading.Thread(target=producer, args=(i,)) for i in range(2)]
consumers = [threading.Thread(target=consumer, args=(i,)) for i in range(3)]

for t in producers + consumers:
    t.start()
for t in producers:
    t.join()

work_queue.join()  # Wait until all items processed
print(f"\nAll work done! Results: {results_queue.qsize()} items processed.")
```

**`queue.Queue` is the recommended way to pass data between threads** — no manual locking needed.

