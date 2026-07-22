# Phase 1, Chapter 2f — Hands-On Experiments & Interview Questions

## Experiment 1: Measure Thread vs Process Creation Cost

```python
# creation_cost.py — How expensive is creating threads vs processes?
import threading
import multiprocessing
import os
import time

def noop():
    """Do nothing — just measure creation + teardown overhead."""
    pass

def measure_threads(n):
    start = time.perf_counter()
    threads = []
    for _ in range(n):
        t = threading.Thread(target=noop)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    return time.perf_counter() - start

def measure_processes(n):
    start = time.perf_counter()
    procs = []
    for _ in range(n):
        p = multiprocessing.Process(target=noop)
        p.start()
        procs.append(p)
    for p in procs:
        p.join()
    return time.perf_counter() - start

N = 1000

t_threads = measure_threads(N)
t_procs = measure_processes(N)

print(f"Creating {N} threads:    {t_threads:.3f}s ({t_threads/N*1000:.2f}ms each)")
print(f"Creating {N} processes:  {t_procs:.3f}s ({t_procs/N*1000:.2f}ms each)")
print(f"Processes are {t_procs/t_threads:.1f}x slower to create than threads")
```

```bash
$ python3 creation_cost.py
Creating 1000 threads:    0.152s (0.15ms each)
Creating 1000 processes:  2.340s (2.34ms each)
Processes are 15.4x slower to create than threads
```

---

## Experiment 2: See Thread Context Switching

```python
# context_switch.py — Force context switches and measure
import threading
import time
import os

switch_count = 0
lock = threading.Lock()
barrier = threading.Barrier(2)

def ping_pong(name, event_mine, event_other, iterations):
    """Alternately signal the other thread, forcing context switches."""
    global switch_count
    barrier.wait()  # Synchronize start
    
    for _ in range(iterations):
        event_mine.wait()    # Wait for my turn
        event_mine.clear()   # Reset
        switch_count += 1
        event_other.set()    # Signal the other thread

N = 100_000
event_a = threading.Event()
event_b = threading.Event()

t1 = threading.Thread(target=ping_pong, args=("A", event_a, event_b, N))
t2 = threading.Thread(target=ping_pong, args=("B", event_b, event_a, N))

t1.start()
t2.start()

# Kick off the ping-pong
event_a.set()

start = time.perf_counter()
t1.join()
t2.join()
elapsed = time.perf_counter() - start

print(f"Ping-pong iterations: {N}")
print(f"Total context switches: ~{N*2:,}")
print(f"Time: {elapsed:.3f}s")
print(f"Per switch: {elapsed/(N*2)*1_000_000:.2f}μs")
```

```bash
$ python3 context_switch.py
Ping-pong iterations: 100000
Total context switches: ~200,000
Time: 1.823s
Per switch: 9.12μs     # includes Python overhead + GIL + actual context switch
```

Compare with actual kernel context switch cost (~1-5μs) — Python adds overhead.

---

## Experiment 3: Thread vs Process Memory Usage

```python
# memory_comparison.py — Compare memory footprint
import threading
import multiprocessing
import os
import time

def get_rss_kb():
    """Get current process RSS in KB."""
    with open(f'/proc/{os.getpid()}/status') as f:
        for line in f:
            if line.startswith('VmRSS:'):
                return int(line.split()[1])
    return 0

def sleeper():
    """Just sleep — hold the thread/process alive."""
    time.sleep(30)

# Measure memory with many threads
print("=== THREADS ===")
rss_before = get_rss_kb()
threads = []
for i in range(100):
    t = threading.Thread(target=sleeper)
    t.start()
    threads.append(t)
time.sleep(1)
rss_after = get_rss_kb()
print(f"Before: {rss_before:,} KB")
print(f"After 100 threads: {rss_after:,} KB")
print(f"Per thread: ~{(rss_after - rss_before) // 100} KB")
print(f"(note: this is mostly stack virtual memory committed)")

# Cleanup
for t in threads:
    t.join(timeout=0.01)

print(f"\n=== PROCESSES ===")
print("(Run separately to avoid mixing measurements)")
print("Each process would show ~10-30MB RSS (full Python interpreter per process)")
```

---

## Experiment 4: See the GIL with sys.getswitchinterval

```python
# gil_timing.py — Explore GIL switch interval
import sys
import threading
import time

print(f"GIL switch interval: {sys.getswitchinterval()}s ({sys.getswitchinterval()*1000}ms)")
print("(This is how often the GIL checks if another thread should run)")

# Demonstrate: shorter interval = more context switches = slower for CPU work
def cpu_work(n):
    total = 0
    for i in range(n):
        total += i
    return total

N = 20_000_000

# Default interval (5ms)
sys.setswitchinterval(0.005)
start = time.perf_counter()
t1 = threading.Thread(target=cpu_work, args=(N,))
t2 = threading.Thread(target=cpu_work, args=(N,))
t1.start(); t2.start(); t1.join(); t2.join()
t_default = time.perf_counter() - start
print(f"\n5ms interval (default):    {t_default:.3f}s")

# Very short interval (100μs) — more switches
sys.setswitchinterval(0.0001)
start = time.perf_counter()
t1 = threading.Thread(target=cpu_work, args=(N,))
t2 = threading.Thread(target=cpu_work, args=(N,))
t1.start(); t2.start(); t1.join(); t2.join()
t_short = time.perf_counter() - start
print(f"0.1ms interval (frequent): {t_short:.3f}s")

# Very long interval (100ms) — fewer switches
sys.setswitchinterval(0.1)
start = time.perf_counter()
t1 = threading.Thread(target=cpu_work, args=(N,))
t2 = threading.Thread(target=cpu_work, args=(N,))
t1.start(); t2.start(); t1.join(); t2.join()
t_long = time.perf_counter() - start
print(f"100ms interval (rare):     {t_long:.3f}s")

print(f"\nMore switching = MORE overhead (shorter interval is SLOWER)")

# Reset
sys.setswitchinterval(0.005)
```

---

## Experiment 5: Verify Threads Share File Descriptors

```python
# shared_fd.py — Prove threads share the same file descriptor table
import threading
import os
import time

def open_file_in_thread(filename):
    """Opens a file in a thread — affects the whole process!"""
    f = open(filename, 'w')
    fd = f.fileno()
    print(f"  [Thread {threading.current_thread().name}] Opened '{filename}', fd={fd}")
    time.sleep(5)  # Hold it open
    f.close()
    print(f"  [Thread {threading.current_thread().name}] Closed fd={fd}")

print(f"PID: {os.getpid()}")
print(f"Initial fds: {sorted(os.listdir(f'/proc/{os.getpid()}/fd'))}")

# Open files in different threads
t1 = threading.Thread(target=open_file_in_thread, args=('/tmp/thread_test_1.txt',))
t2 = threading.Thread(target=open_file_in_thread, args=('/tmp/thread_test_2.txt',))
t1.start()
t2.start()
time.sleep(1)

# Main thread sees all open fds (because they're SHARED)
print(f"\nAll fds (seen from main thread): {sorted(os.listdir(f'/proc/{os.getpid()}/fd'))}")
print("Files opened by OTHER threads are visible here!")
print("This is because threads SHARE the file descriptor table.")

t1.join()
t2.join()
print(f"\nAfter threads closed files: {sorted(os.listdir(f'/proc/{os.getpid()}/fd'))}")
```

---

## Summary: The Complete Mental Model

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     THREADS — THE COMPLETE PICTURE                        │
│                                                                           │
│  WHAT IS A THREAD?                                                       │
│  • An independent execution context within a process                     │
│  • Has its own: stack, PC, registers, TID, state                        │
│  • Shares with other threads: heap, code, files, signals                │
│  • In Linux kernel: just a task_struct with shared mm + files           │
│                                                                           │
│  HOW IT'S CREATED (Linux):                                               │
│  clone(CLONE_VM | CLONE_FILES | CLONE_FS | CLONE_THREAD | ...)          │
│  = "Create a new task that shares everything with parent"               │
│                                                                           │
│  THE TRADEOFF:                                                           │
│  Process: safe (isolated) but heavy (separate memory, expensive IPC)    │
│  Thread:  fast (shared memory) but dangerous (race conditions, locks)   │
│                                                                           │
│  PYTHON SPECIFICS:                                                       │
│  • GIL prevents true parallelism for CPU-bound threads                  │
│  • Threads still useful for I/O-bound work (GIL releases during I/O)   │
│  • Use multiprocessing for CPU parallelism                              │
│  • Use asyncio for many concurrent I/O operations                       │
│                                                                           │
│  THREE CONCURRENCY MODELS:                                               │
│  1. OS threads (1:1) — Java, C, Python threading                        │
│  2. Green threads (M:N) — Go, Erlang, Java virtual threads             │
│  3. Event loop (single thread) — Node.js, Redis, asyncio               │
│                                                                           │
│  REAL SYSTEMS:                                                           │
│  • Redis: single-threaded event loop (fast, no locks)                   │
│  • PostgreSQL: process-per-connection (isolated, simple)                │
│  • Go servers: goroutine-per-connection (lightweight, scalable)         │
│  • Java traditional: thread-per-connection (heavy, limited)             │
│  • Nginx: multi-process, event loop per worker                          │
│                                                                           │
│  LINUX TOOLS:                                                            │
│  • /proc/<pid>/task/     — list all threads                             │
│  • ps -T -p <pid>       — show threads of a process                    │
│  • top -H -p <pid>      — thread-level monitoring                       │
│  • strace -f            — trace syscalls across threads                 │
│  • htop (press H)       — toggle thread view                            │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Interview Questions

### Q1: What is a thread and how does it differ from a process?

**Answer:** A thread is an execution unit within a process. It has its own stack, program counter, and registers, but shares the process's virtual address space (heap, code, data), file descriptors, and signal handlers with other threads. In Linux, both are task_structs — the difference is that threads are created with `clone(CLONE_VM | CLONE_FILES | ...)` (share everything) while processes use `fork()` / `clone()` without sharing flags (copy everything).

Key tradeoff: threads are lightweight (fast creation, shared memory = easy communication) but dangerous (race conditions require synchronization). Processes are heavy (separate memory, expensive IPC) but safe (isolation by default).

---

### Q2: If threads share memory, why does each thread need its own stack?

**Answer:** The stack stores function call frames — local variables, return addresses, and function arguments. If two threads share a stack, their function calls would interleave and corrupt each other's data. Each thread executes different code paths at different speeds, so each needs its own call stack to track where it is in its execution. The stack is the "thread-private" workspace.

The heap is shared because it stores long-lived objects that multiple threads need to access. The stack is private because it stores short-lived, execution-specific data.

---

### Q3: Explain the GIL. Why does Python have it? When do threads still help?

**Answer:** The GIL (Global Interpreter Lock) is a mutex in CPython that allows only one thread to execute Python bytecode at a time. It exists because CPython uses reference counting for memory management — without the GIL, concurrent reference count modifications would corrupt memory.

Threads still help for I/O-bound work because the GIL is released during I/O operations (network, file, sleep). While one thread waits for a network response, other threads can run Python code. For CPU-bound work, use `multiprocessing` (separate processes with separate GILs) or C extensions that release the GIL (numpy).

---

### Q4: What is a race condition? Give an example and how to fix it.

**Answer:** A race condition occurs when the correctness of a program depends on the timing of thread execution. Example: two threads doing `counter += 1` — this is read-modify-write (3 operations). If both read the same value before either writes, one increment is lost.

Fix options:
1. **Mutex (lock):** `with lock: counter += 1` — serializes access
2. **Atomic operations:** Use `threading.Lock` or atomic types
3. **Thread-local storage:** Each thread has its own copy
4. **Immutable data:** If data never changes, no synchronization needed
5. **Message passing:** Use `queue.Queue` instead of shared variables

---

### Q5: Compare OS threads, green threads (goroutines), and event loops. When would you use each?

**Answer:**
- **OS threads (1:1):** Each user thread = one kernel thread. True parallelism, ~8MB stack each. Best for: CPU-bound work on multiple cores, limited concurrency (< 10K). Used by: Java, C, Python.
- **Green threads (M:N):** Many lightweight threads mapped to few OS threads. ~2-8KB each, millions possible. Runtime does scheduling. Best for: servers with many concurrent connections. Used by: Go, Erlang, Java 21.
- **Event loop (single thread):** One thread handles all I/O with epoll/kqueue. No context switches, no locks. Best for: I/O-bound servers (Redis, Node.js). Limited by: can't use multiple cores from one loop, CPU work blocks everything.

---

### Q6: Why is Redis single-threaded? Isn't that slow?

**Answer:** Redis operations are in-memory and take nanoseconds-microseconds of CPU time. The bottleneck is network I/O, not computation. A single-threaded event loop with epoll can handle 100K+ ops/sec because:
1. No lock contention (single thread = no shared-state problems)
2. No context switch overhead
3. CPU operations are trivially fast (hash table lookups in RAM)
4. epoll efficiently multiplexes thousands of connections

If Redis were multi-threaded, every data structure would need locks, adding complexity and overhead for no benefit (since each operation is already sub-microsecond). Redis 6.0+ uses threads only for network I/O (reading/writing socket buffers), not for command execution.

---

### Q7: A Java server creates one thread per connection. At 10,000 concurrent connections, what problems arise? How do you solve them?

**Answer:** Problems at 10K threads:
1. **Memory:** 10K × 8MB stack = 80GB virtual memory, actual RSS ~640MB minimum
2. **Scheduling:** O(log n) per scheduling decision, frequent context switches
3. **Cache thrashing:** Threads compete for CPU cache, causing misses
4. **Lock contention:** If threads share data structures, locks become bottlenecks

Solutions:
1. **Thread pool:** Fixed pool of 200-500 threads, queue excess requests
2. **Non-blocking I/O (NIO):** Java NIO with Selector (event loop pattern)
3. **Virtual threads (Java 21):** Green threads, millions supported, cheap
4. **Reactive frameworks:** Project Reactor, Vert.x — event-driven, non-blocking

---

### Q8: In Linux, what's the actual difference between a thread and a process at the kernel level?

**Answer:** Nothing fundamental. Both are task_structs (tasks). The difference is what they share:
- `fork()` → `clone(0)` → new task with COPIED mm, files, fs, signals
- `pthread_create()` → `clone(CLONE_VM | CLONE_FILES | CLONE_FS | CLONE_THREAD | CLONE_SIGHAND)` → new task SHARING mm, files, fs, signals

The scheduler treats them identically — it schedules task_structs regardless of whether they share memory. `getpid()` returns `tgid` (thread group ID) so threads in the same process appear to have the same PID. `gettid()` returns the unique task ID.

---

## What's Next

You now understand threads deeply:
- What they are (shared-memory execution contexts within a process)
- How Linux implements them (clone with sharing flags)
- Why they're dangerous (race conditions)
- Python's GIL and when threads help vs don't
- The three concurrency models and when to use each
- How real systems (Redis, PostgreSQL, Go, Nginx) make their choices

**Next Chapter:** Scheduling — how the OS decides WHICH thread/process runs on WHICH CPU, and for HOW LONG. (Round-robin, priority, CFS, real-time scheduling)

