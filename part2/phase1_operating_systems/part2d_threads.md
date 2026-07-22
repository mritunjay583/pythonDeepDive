# Phase 1, Chapter 2d — Python's GIL: The Elephant in the Room

## What is the GIL?

The **Global Interpreter Lock (GIL)** is a mutex in CPython (the standard Python implementation) that allows only ONE thread to execute Python bytecode at any time.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PYTHON GIL                                    │
│                                                                       │
│  Even with 4 threads and 8 CPU cores:                                │
│  Only ONE thread runs Python code at any given instant.              │
│                                                                       │
│  Thread 1: ████░░░░████░░░░████                                      │
│  Thread 2: ░░░░████░░░░████░░░░                                      │
│  Thread 3: ░░░░░░░░░░░░░░░░░░░░ (waiting)                           │
│  Thread 4: ░░░░░░░░░░░░░░░░░░░░ (waiting)                           │
│                                                                       │
│  ████ = holding GIL (running Python code)                            │
│  ░░░░ = waiting for GIL                                              │
│                                                                       │
│  Result: Multi-threaded Python is NOT faster for CPU work!           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Why Does the GIL Exist?

CPython's memory management uses **reference counting**. Every Python object has a reference count:

```python
import sys

a = []          # refcount of list = 1
b = a           # refcount of list = 2
print(sys.getrefcount(a))  # 3 (a, b, and the getrefcount arg)
del b           # refcount of list = 2
del a           # refcount = 0 → object freed
```

**Without the GIL, two threads could simultaneously modify reference counts:**

```
Thread 1: INCREF(obj)     Thread 2: DECREF(obj)
   read refcount=1            read refcount=1
   compute 1+1=2              compute 1-1=0
   write refcount=2           write refcount=0 → FREED!
   
# Thread 1 thinks refcount is 2 (safe)
# Thread 2 freed the object!
# Thread 1 now has a dangling pointer → CRASH
```

The GIL makes this impossible by ensuring only one thread runs at a time. It's a simple, coarse-grained solution.

---

## When Does the GIL Release?

The GIL releases in these situations:

```
1. Every N bytecode instructions (default: every 5ms in Python 3.2+)
   → This is why our race_condition.py had problems!
   → The GIL releases between LOAD_GLOBAL and STORE_GLOBAL

2. During I/O operations (file read/write, network, sleep)
   → time.sleep() releases GIL
   → socket.recv() releases GIL
   → file.read() releases GIL

3. During calls to C extensions that release it explicitly
   → numpy computations release GIL
   → hashlib.sha256() releases GIL
   → database drivers often release GIL during queries
```

---

## Proof: GIL Makes CPU-Bound Threads Useless

```python
# gil_cpu_bound.py — Threads don't help for CPU work in Python
import threading
import time

def cpu_work(n):
    """Pure CPU computation."""
    total = 0
    for i in range(n):
        total += i * i
    return total

N = 50_000_000

# Single-threaded
start = time.perf_counter()
cpu_work(N)
t_single = time.perf_counter() - start
print(f"Single-threaded:     {t_single:.3f}s")

# Two threads (same total work, split in half)
start = time.perf_counter()
t1 = threading.Thread(target=cpu_work, args=(N//2,))
t2 = threading.Thread(target=cpu_work, args=(N//2,))
t1.start(); t2.start()
t1.join(); t2.join()
t_threaded = time.perf_counter() - start
print(f"Two threads:         {t_threaded:.3f}s")
print(f"Speedup:             {t_single/t_threaded:.2f}x")
print(f"\nThreads are {'faster' if t_threaded < t_single else 'NOT faster (GIL!)'}!")
```

```bash
$ python3 gil_cpu_bound.py
Single-threaded:     4.521s
Two threads:         4.893s        ← SLOWER than single-threaded!
Speedup:             0.92x

Threads are NOT faster (GIL!)!
```

**Two threads are actually SLOWER** because of GIL contention overhead (acquiring/releasing the lock, thread switching).

---

## But Threads DO Help for I/O-Bound Work!

```python
# gil_io_bound.py — Threads shine for I/O work
import threading
import time
import urllib.request

URLS = [
    "http://httpbin.org/delay/1",
    "http://httpbin.org/delay/1",
    "http://httpbin.org/delay/1",
    "http://httpbin.org/delay/1",
]

def download(url):
    """Download a URL (I/O-bound — GIL releases during network wait)."""
    urllib.request.urlopen(url).read()

# Sequential
start = time.perf_counter()
for url in URLS:
    download(url)
t_seq = time.perf_counter() - start
print(f"Sequential:  {t_seq:.2f}s (4 requests × 1s each)")

# Threaded
start = time.perf_counter()
threads = [threading.Thread(target=download, args=(url,)) for url in URLS]
for t in threads: t.start()
for t in threads: t.join()
t_threaded = time.perf_counter() - start
print(f"Threaded:    {t_threaded:.2f}s (all 4 concurrent!)")
print(f"Speedup:     {t_seq/t_threaded:.1f}x")
```

```bash
$ python3 gil_io_bound.py
Sequential:  4.12s (4 requests × 1s each)
Threaded:    1.08s (all 4 concurrent!)
Speedup:     3.8x
```

**Why?** When a thread calls `socket.recv()`, it RELEASES the GIL and sleeps. Other threads can run Python code. When the network response arrives, the thread re-acquires the GIL and continues.

```
Thread 1: [Python code] → socket.recv() [RELEASE GIL, sleep] → [wake, acquire GIL]
Thread 2:                  [Python code] → socket.recv() [RELEASE GIL, sleep] → ...
Thread 3:                                  [Python code] → socket.recv() [sleep] → ...
Thread 4:                                                  [Python code] → ...

All 4 network waits happen simultaneously!
```

---

## Escaping the GIL: multiprocessing

For CPU-bound work, use **processes** instead of threads:

```python
# multiprocessing_demo.py — True parallelism with processes
import multiprocessing
import threading
import time

def cpu_work(n):
    total = 0
    for i in range(n):
        total += i * i
    return total

N = 50_000_000

# Single-threaded
start = time.perf_counter()
cpu_work(N)
t_single = time.perf_counter() - start
print(f"Single process:      {t_single:.3f}s")

# Two threads (GIL bottleneck)
start = time.perf_counter()
t1 = threading.Thread(target=cpu_work, args=(N//2,))
t2 = threading.Thread(target=cpu_work, args=(N//2,))
t1.start(); t2.start(); t1.join(); t2.join()
t_threads = time.perf_counter() - start
print(f"Two threads:         {t_threads:.3f}s ({t_single/t_threads:.2f}x)")

# Two processes (true parallelism!)
start = time.perf_counter()
p1 = multiprocessing.Process(target=cpu_work, args=(N//2,))
p2 = multiprocessing.Process(target=cpu_work, args=(N//2,))
p1.start(); p2.start(); p1.join(); p2.join()
t_procs = time.perf_counter() - start
print(f"Two processes:       {t_procs:.3f}s ({t_single/t_procs:.2f}x)")
print(f"\nProcesses achieve TRUE parallelism (each has its own GIL!)")
```

```bash
$ python3 multiprocessing_demo.py
Single process:      4.521s
Two threads:         4.893s (0.92x)    ← GIL kills parallelism
Two processes:       2.341s (1.93x)    ← Nearly 2x speedup! True parallel!
```

**Each process has its OWN Python interpreter with its OWN GIL.** They can truly run in parallel on different CPU cores.

---

## The GIL Decision Flowchart

```
What kind of work are your threads doing?
│
├── CPU-bound (computation, math, data processing)
│   │
│   ├── Use multiprocessing (separate processes)     ✓ True parallelism
│   ├── Use C extensions that release GIL (numpy)   ✓ True parallelism
│   ├── Use subprocess (external programs)           ✓ True parallelism
│   └── Use Python threads                          ✗ NO speedup (GIL)
│
├── I/O-bound (network, files, databases)
│   │
│   ├── Use threading                               ✓ Good! GIL releases during I/O
│   ├── Use asyncio                                 ✓ Even better for many connections
│   └── Use multiprocessing                         ✓ Works but overkill
│
└── Mixed (some CPU, some I/O)
    │
    ├── Use multiprocessing + threads               ✓ Processes for CPU, threads for I/O
    └── Use concurrent.futures (ThreadPool/ProcessPool) ✓ Easy API
```

---

## Python 3.13+ : Free-Threaded Python (No GIL!)

Starting with Python 3.13 (2024), there's an EXPERIMENTAL build without the GIL:

```bash
# Install free-threaded Python (experimental)
$ python3.13t  # The 't' suffix means "free-threaded" (no GIL)
```

This is still experimental and opt-in. Most Python code and C extensions assume the GIL exists, so removing it is a massive undertaking. But it's coming!

---

## Summary: When to Use What in Python

```
┌─────────────────────────────────────────────────────────────────┐
│                    PYTHON CONCURRENCY GUIDE                       │
├───────────────────┬──────────────────┬──────────────────────────┤
│ Use Case          │ Tool             │ Why                       │
├───────────────────┼──────────────────┼──────────────────────────┤
│ I/O-bound         │ threading        │ GIL releases during I/O  │
│ (network, files)  │ or asyncio       │ asyncio = single thread  │
│                   │                  │ but non-blocking          │
├───────────────────┼──────────────────┼──────────────────────────┤
│ CPU-bound         │ multiprocessing  │ Separate GILs per process│
│ (computation)     │ or C extensions  │ numpy/scipy release GIL  │
├───────────────────┼──────────────────┼──────────────────────────┤
│ Many connections  │ asyncio          │ 10K+ connections, single │
│ (web server)      │                  │ thread, event loop       │
├───────────────────┼──────────────────┼──────────────────────────┤
│ Simple parallel   │ concurrent.      │ High-level API, auto     │
│ tasks             │ futures          │ manages pool             │
└───────────────────┴──────────────────┴──────────────────────────┘
```

