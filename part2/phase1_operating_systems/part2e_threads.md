# Phase 1, Chapter 2e — Thread Types: OS Threads vs Green Threads vs Coroutines

## The Confusion

```
"Java threads — are those OS threads?"
"Go goroutines — are those threads?"
"Python asyncio — is that threading?"
"Node.js is single-threaded — how does it handle 10K connections?"
```

There are THREE models of concurrency. Let's compare them all.

---

## Model 1: OS Threads (1:1 Mapping)

**Used by:** Java, C, C++, Rust, Python (threading module)

Each language-level thread = one kernel thread (one task_struct).

```
┌──────────────────────────────────────────────────────────────────┐
│  APPLICATION                                                       │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐                    │
│  │Thread 1│ │Thread 2│ │Thread 3│ │Thread 4│  (user-space)       │
│  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘                    │
│      │          │          │          │         1:1 mapping       │
├──────┼──────────┼──────────┼──────────┼─────────────────────────┤
│      ▼          ▼          ▼          ▼                           │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐                    │
│  │Kernel  │ │Kernel  │ │Kernel  │ │Kernel  │  (kernel-space)     │
│  │Thread 1│ │Thread 2│ │Thread 3│ │Thread 4│                     │
│  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘                    │
│      │          │          │          │                           │
│  ┌───▼────┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐                   │
│  │ CPU 0  │ │ CPU 1  │ │ CPU 2  │ │ CPU 3  │  (hardware)        │
│  └────────┘ └────────┘ └────────┘ └────────┘                    │
└──────────────────────────────────────────────────────────────────┘

Properties:
✓ True parallelism (runs on multiple cores)
✓ Preemptive (OS can interrupt any thread)
✓ Can do blocking I/O (other threads continue)
✗ Heavy (each thread ~8MB stack + kernel overhead)
✗ Slow to create (~50-100μs)
✗ Context switch cost (~1-5μs per switch)
✗ Limited count (1K-10K threads before performance degrades)
```

**Cost breakdown of 10,000 OS threads:**
- Stack memory: 10,000 × 8MB = 80GB virtual (but most pages not committed)
- Actual RAM: 10,000 × ~64KB (minimum committed) = 640MB
- Kernel task_structs: 10,000 × ~6KB = 60MB
- Scheduling overhead: O(log n) per decision with CFS
- Context switches at high thread counts: thrashing

---

## Model 2: Green Threads / Goroutines (M:N Mapping)

**Used by:** Go (goroutines), Erlang (processes), Java 21+ (virtual threads)

Many language-level threads map to few OS threads. The language **runtime** does the scheduling, not the kernel.

```
┌──────────────────────────────────────────────────────────────────┐
│  APPLICATION (Runtime scheduler)                                   │
│  ┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐┌──┐                     │
│  │G1││G2││G3││G4││G5││G6││G7││G8││G9││G10│ ... (100K goroutines)│
│  └─┬┘└─┬┘└─┬┘└──┘└──┘└─┬┘└──┘└──┘└─┬┘└──┘                     │
│    │   │   │            │            │         M:N mapping       │
│    │   │   │    (runtime multiplexes goroutines onto OS threads) │
├────┼───┼───┼────────────┼────────────┼──────────────────────────┤
│    ▼   ▼   ▼            ▼            ▼                           │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐                    │
│  │OS Thr 1│ │OS Thr 2│ │OS Thr 3│ │OS Thr 4│  (kernel threads)  │
│  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘                    │
│      ▼          ▼          ▼          ▼                           │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐                    │
│  │ CPU 0  │ │ CPU 1  │ │ CPU 2  │ │ CPU 3  │                    │
│  └────────┘ └────────┘ └────────┘ └────────┘                    │
└──────────────────────────────────────────────────────────────────┘

Properties:
✓ True parallelism (OS threads run on multiple cores)
✓ Lightweight (each goroutine ~2-8KB stack, grows dynamically)
✓ Fast to create (~1-3μs)
✓ Can have MILLIONS of goroutines
✓ Cheap context switch (~100-200ns, user-space, no kernel involved)
✓ Runtime handles blocking I/O (parks goroutine, not OS thread)
✗ More complex runtime implementation
✗ Requires cooperative scheduling points (function calls, channel ops)
```

**Go's scheduler:**
```
Goroutine states:
• Runnable — ready to run (in a queue)
• Running — currently executing on an OS thread
• Waiting — blocked on I/O, channel, timer, etc.

Go scheduler (work-stealing):
┌─────────────────────────────────────────────────────────────┐
│  P0 (Processor)        P1 (Processor)       P2 (Processor) │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────┐ │
│  │ Local run queue  │  │ Local run queue  │  │ Local queue│ │
│  │ G1, G4, G7       │  │ G2, G5           │  │ G3         │ │
│  └────────┬────────┘  └────────┬────────┘  └─────┬──────┘ │
│           │                     │                   │        │
│           ▼                     ▼                   ▼        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────┐ │
│  │ M0 (OS Thread)  │  │ M1 (OS Thread)  │  │ M2 (OS Thr)│ │
│  │ Running: G1     │  │ Running: G2     │  │ Running: G3│ │
│  └─────────────────┘  └─────────────────┘  └────────────┘ │
│                                                              │
│  Global run queue: G6, G8, G9, G10...                       │
│  (overflow from local queues)                                │
└─────────────────────────────────────────────────────────────┘
```

**Why Go can handle 1 million concurrent connections:**
- Each goroutine: ~4KB (vs 8MB for OS thread)
- 1M goroutines: ~4GB RAM (vs ~80TB virtual for OS threads — impossible)
- Scheduling: user-space (no kernel mode switch)
- Blocking I/O: runtime parks goroutine, reuses OS thread for another goroutine

---

## Model 3: Event Loop / Coroutines (1:0 — Single Thread!)

**Used by:** Node.js, Python asyncio, Redis, Nginx (single event loop)

ONE thread handles ALL connections using non-blocking I/O.

```
┌──────────────────────────────────────────────────────────────────┐
│  SINGLE OS THREAD (main)                                          │
│                                                                    │
│  Event Loop:                                                      │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                                                              │  │
│  │  while True:                                                 │  │
│  │    ready_events = epoll.wait()  ← Ask kernel: which fds     │  │
│  │                                    have data ready?          │  │
│  │    for event in ready_events:                                │  │
│  │      if event.type == NEW_CONNECTION:                        │  │
│  │        accept_connection()                                   │  │
│  │      elif event.type == DATA_READY:                          │  │
│  │        handle_request(event.fd)                              │  │
│  │      elif event.type == WRITE_READY:                         │  │
│  │        send_response(event.fd)                               │  │
│  │                                                              │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌────────┐                                                       │
│  │ CPU 0  │ (only uses ONE core)                                  │
│  └────────┘                                                       │
└──────────────────────────────────────────────────────────────────┘

Properties:
✓ Extremely lightweight (no thread creation at all)
✓ No locks needed (single thread = no race conditions!)
✓ No context switch overhead
✓ Can handle 100K+ connections (each is just a file descriptor + state)
✓ Excellent for I/O-bound servers
✗ Cannot use multiple CPU cores (for one event loop)
✗ CPU-bound work blocks EVERYTHING (no preemption)
✗ Requires non-blocking APIs throughout (can't call blocking code)
✗ Complex callback/async programming model
```

### Python asyncio example:

```python
# asyncio_demo.py — Single thread, many concurrent operations
import asyncio
import time

async def fetch(name, delay):
    """Simulates an I/O operation (network request)."""
    print(f"  [{name}] Starting fetch (will take {delay}s)...")
    await asyncio.sleep(delay)  # Non-blocking! Event loop runs other tasks.
    print(f"  [{name}] Done!")
    return f"{name}-result"

async def main():
    start = time.perf_counter()
    
    # Launch 5 concurrent "fetches" — ALL in ONE thread!
    tasks = [
        asyncio.create_task(fetch("A", 1)),
        asyncio.create_task(fetch("B", 1)),
        asyncio.create_task(fetch("C", 1)),
        asyncio.create_task(fetch("D", 1)),
        asyncio.create_task(fetch("E", 1)),
    ]
    
    results = await asyncio.gather(*tasks)
    
    elapsed = time.perf_counter() - start
    print(f"\n5 tasks × 1s each = {elapsed:.2f}s total (concurrent in 1 thread!)")
    print(f"Results: {results}")

asyncio.run(main())
```

```bash
$ python3 asyncio_demo.py
  [A] Starting fetch (will take 1s)...
  [B] Starting fetch (will take 1s)...
  [C] Starting fetch (will take 1s)...
  [D] Starting fetch (will take 1s)...
  [E] Starting fetch (will take 1s)...
  [A] Done!
  [B] Done!
  [C] Done!
  [D] Done!
  [E] Done!

5 tasks × 1s each = 1.00s total (concurrent in 1 thread!)
```

---

## The Grand Comparison

```
┌────────────────────┬──────────────────┬──────────────────┬──────────────────┐
│                    │ OS Threads (1:1) │ Green Threads    │ Event Loop       │
│                    │                  │ (M:N)            │ (Single Thread)  │
├────────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Examples           │ Java, Python     │ Go goroutines    │ Node.js, Redis   │
│                    │ threads, C       │ Java virtual     │ Python asyncio   │
│                    │ pthreads         │ threads, Erlang  │ Nginx            │
├────────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Memory per unit    │ ~8MB (stack)     │ ~2-8KB           │ ~bytes (no stack)│
├────────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Max count          │ ~10K             │ ~1M+             │ ~100K+ tasks     │
├────────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Creation cost      │ ~50-100μs        │ ~1-3μs           │ ~0.1μs           │
├────────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Context switch     │ ~1-5μs (kernel)  │ ~100-300ns       │ ~ns (function    │
│                    │                  │ (user-space)     │  call)           │
├────────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Parallelism        │ Yes (multi-core) │ Yes (multi-core) │ No (one core)    │
├────────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Blocking I/O       │ Blocks one       │ Runtime parks    │ MUST use non-    │
│                    │ thread only      │ goroutine        │ blocking I/O!    │
├────────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Race conditions    │ Yes (shared mem) │ Yes (shared mem) │ No (single       │
│                    │                  │ but channels     │ thread)          │
│                    │                  │ preferred        │                  │
├────────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Best for           │ CPU-bound +      │ Many concurrent  │ I/O-bound,       │
│                    │ I/O-bound        │ tasks (servers)  │ many connections │
└────────────────────┴──────────────────┴──────────────────┴──────────────────┘
```

---

## Real-World Architectures

### Redis: Single-Threaded Event Loop
```
Why: All operations are in-memory (sub-microsecond). Bottleneck is network I/O, not CPU.
     Single thread → no locks → simple code → no race conditions.
     
Architecture:
  1 event loop thread (handles all commands)
  + Background threads for: disk persistence (fork + write), lazy deletion
  
Redis 6.0+: Multi-threaded I/O (reading/writing network packets)
             but command execution is still single-threaded.
```

### Nginx: Multi-Process Event Loop
```
Why: Need to use multiple CPU cores, but each core handles I/O-bound work.

Architecture:
  Master process (1): manages workers
  Worker processes (N = num_cpus): each runs its own event loop
  
  Each worker handles thousands of connections with epoll.
  No shared memory between workers (process isolation).
```

### Go HTTP Server: Goroutines
```
Why: Simple programming model (write blocking code, runtime handles the rest).

Architecture:
  1 goroutine per connection (can have 100K+ goroutines)
  Go runtime multiplexes onto ~GOMAXPROCS OS threads
  Netpoller: background thread using epoll, wakes goroutines when I/O ready

  Developer writes:
    conn, _ := listener.Accept()
    go handleConnection(conn)  // Goroutine — looks like thread, costs nothing
```

### Java Traditional: Thread-Per-Connection
```
Why: Simple model (one thread per client), OS handles scheduling.

Architecture:
  Thread pool (200-500 threads)
  Each request gets a thread from pool
  Thread blocks on DB query → OS schedules other threads
  
Problem: 10K connections → 10K threads → memory explosion + scheduling overhead
Solution: Java 21 Virtual Threads (green threads!) or reactive frameworks
```

### PostgreSQL: Process-Per-Connection
```
Why: Isolation. One bad query can't corrupt another connection's memory.

Architecture:
  Postmaster (main process): accepts connections
  fork() per connection: each client gets a dedicated process
  Shared memory (shared_buffers): processes share buffer pool via mmap
  
Problem: 1000 connections = 1000 processes. Heavy.
Solution: PgBouncer (connection pooler) reduces actual backend processes.
```

