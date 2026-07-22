# Phase 1, Chapter 2a — Threads: What They Actually Are

## The Big Confusion

Here's what confuses everyone:

```
"If a process is what runs on the CPU... what's a thread?"
"Is a thread inside a process? Or is it separate?"
"When I create a thread in Python, what is the OS actually doing?"
"What's the difference between a thread and just calling a function?"
```

Let's kill all of this confusion permanently.

---

## The One-Line Answer

> A **thread** is an independent path of execution **within** a process. It's what the CPU actually runs. A process is just the container — threads do the work.

If a process is an apartment, threads are the people living in it. They share the kitchen, bathroom, and living room (heap, code, files), but each person has their own bedroom (stack).

---

## Wait — Didn't We Already See This in Chapter 1?

Yes! In Chapter 1 we said:
- Process = container (owns memory, files, PID)
- Thread = what runs on the CPU (has PC, registers, stack)

Now we go DEEP. We'll see threads created, inspect them in Linux, watch them share memory, see them fight over shared data, and understand why the GIL exists.

---

## Why Threads Exist: The Problem They Solve

Imagine you're building a web server. A request comes in:

```
Without threads (single-threaded process):

Request 1 arrives → process handles it (takes 100ms)
                    ↓
                    Request 2 arrives → WAITS
                                        ↓
                                        Request 2 handled (100ms later)
                                        ↓
                                        Request 3 arrives → WAITS

Total for 3 requests: ~300ms (sequential!)
```

**Option A: Use multiple PROCESSES (fork per request)**
```
Request 1 → fork() → Child process 1 handles it
Request 2 → fork() → Child process 2 handles it
Request 3 → fork() → Child process 3 handles it

Problems:
• fork() is expensive (~100-500μs each)
• Each process has its OWN memory (can't easily share data)
• 10,000 connections = 10,000 processes = memory explosion
• IPC (inter-process communication) is complex and slow
```

**Option B: Use multiple THREADS (threads within one process)**
```
Request 1 → create thread 1 → handles it
Request 2 → create thread 2 → handles it
Request 3 → create thread 3 → handles it

Advantages:
• Thread creation is FAST (~10-50μs, 10x faster than fork)
• All threads SHARE the same memory (easy communication)
• 10,000 threads use much less memory than 10,000 processes
• Shared heap = can share data structures directly (no IPC needed)
```

**This is why threads exist:** lightweight concurrency with shared memory.

---

## Process vs Thread: The Definitive Comparison

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     PROCESS vs THREAD                                      │
├────────────────────────────────┬─────────────────────────────────────────┤
│          PROCESS               │              THREAD                       │
├────────────────────────────────┼─────────────────────────────────────────┤
│ Has OWN address space          │ SHARES address space with other threads │
│ Has OWN page tables            │ SHARES page tables (same mappings)      │
│ Has OWN file descriptor table  │ SHARES file descriptor table            │
│ Has OWN PID                    │ Has own TID (Thread ID) within process  │
│ Created by fork() — expensive  │ Created by clone() — cheap              │
│ Isolated (safe by default)     │ Shared (fast but dangerous)             │
│ Communication: pipes, sockets  │ Communication: shared memory directly   │
│ Crash kills only that process  │ Crash kills ALL threads in process      │
│ Context switch: ~1-10μs        │ Context switch: ~0.5-5μs (less to save) │
├────────────────────────────────┴─────────────────────────────────────────┤
│                                                                            │
│  WHAT'S SHARED between threads in same process:                           │
│  ✓ Code (text segment)                                                    │
│  ✓ Heap (malloc'd memory, objects)                                        │
│  ✓ Global/static variables                                                │
│  ✓ Open file descriptors                                                  │
│  ✓ Signal handlers                                                        │
│  ✓ Current working directory                                              │
│  ✓ User and group IDs                                                     │
│                                                                            │
│  WHAT'S PRIVATE per thread:                                               │
│  ✗ Stack (each thread has its own)                                        │
│  ✗ Registers (PC, SP, general purpose)                                    │
│  ✗ Thread ID (TID)                                                        │
│  ✗ Signal mask                                                            │
│  ✗ errno (thread-local storage)                                           │
│  ✗ Scheduling priority                                                    │
│                                                                            │
└──────────────────────────────────────────────────────────────────────────┘
```

### Visual:

```
┌─────────────────── Process (PID 5000) ───────────────────────────────┐
│                                                                        │
│   SHARED MEMORY:                                                      │
│   ┌──────────────────────────────────────────────────────────────┐   │
│   │  Code (text)    │  Heap (objects, data)  │  Global variables  │   │
│   │  open files     │  signal handlers       │  working dir       │   │
│   └──────────────────────────────────────────────────────────────┘   │
│                                                                        │
│   PRIVATE PER THREAD:                                                 │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│   │  Thread 1    │  │  Thread 2    │  │  Thread 3    │              │
│   │  (main)      │  │              │  │              │              │
│   │              │  │              │  │              │              │
│   │  TID: 5000   │  │  TID: 5001   │  │  TID: 5002   │              │
│   │  Stack: 8MB  │  │  Stack: 8MB  │  │  Stack: 8MB  │              │
│   │  PC: 0x1234  │  │  PC: 0x5678  │  │  PC: 0x9ABC  │              │
│   │  Registers   │  │  Registers   │  │  Registers   │              │
│   │  State: R    │  │  State: S    │  │  State: R    │              │
│   └──────────────┘  └──────────────┘  └──────────────┘              │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## The Key Insight: Threads Are "Lightweight Processes"

In Linux, **there is no fundamental difference between a thread and a process at the kernel level.** Both are represented by a `task_struct`. The difference is:

```
fork()   → clone(CLONE_NEWPID | CLONE_NEWNS | ...)
             Creates new PID namespace, new memory space, new file table
             = SEPARATE everything = PROCESS

pthread_create() → clone(CLONE_VM | CLONE_FILES | CLONE_FS | CLONE_SIGHAND | ...)
                    SHARES memory (VM), file table, filesystem info, signal handlers
                    = SHARE everything = THREAD
```

**In Linux kernel, a "thread" is just a process that shares stuff with another process.** The kernel calls them all "tasks." The `clone()` system call lets you pick exactly what to share.

```
clone() flags — pick your sharing:
┌──────────────────────┬───────────────────────────────────────────┐
│ Flag                 │ What it shares                             │
├──────────────────────┼───────────────────────────────────────────┤
│ CLONE_VM             │ Share virtual memory (same page tables)   │
│ CLONE_FILES          │ Share file descriptor table               │
│ CLONE_FS             │ Share filesystem info (cwd, root)         │
│ CLONE_SIGHAND        │ Share signal handlers                     │
│ CLONE_THREAD         │ Same thread group (share PID externally)  │
│ CLONE_PARENT         │ Share same parent                         │
└──────────────────────┴───────────────────────────────────────────┘

fork()           = clone(nothing shared)     → new process
pthread_create() = clone(everything shared)  → new thread
```

---

## The Real Python Program: Creating Threads

```python
# threads_demo.py — Creating and inspecting threads
import threading
import os
import time
import ctypes

# Get the Linux thread ID (different from Python's threading.get_ident())
def gettid():
    """Get the real Linux Thread ID (TID) via syscall."""
    return ctypes.CDLL('libc.so.6').syscall(186)  # SYS_gettid = 186

def worker(name, sleep_time):
    """Worker function that runs in a thread."""
    tid = gettid()
    print(f"  [{name}] Started! PID={os.getpid()}, TID={tid}")
    print(f"  [{name}] Python thread ID: {threading.get_ident()}")
    print(f"  [{name}] Thread name: {threading.current_thread().name}")
    
    # Do some work
    total = 0
    for i in range(5_000_000):
        total += i
    
    print(f"  [{name}] Computed: {total}")
    print(f"  [{name}] Going to sleep for {sleep_time}s...")
    time.sleep(sleep_time)
    print(f"  [{name}] Done!")

def main():
    print(f"=== Main Thread ===")
    print(f"PID: {os.getpid()}")
    print(f"Main TID: {gettid()}")
    print(f"Thread count: {threading.active_count()}")
    print()
    
    # Create 3 threads
    threads = []
    for i in range(3):
        t = threading.Thread(target=worker, args=(f"Worker-{i}", 10))
        threads.append(t)
    
    print("Starting threads...")
    for t in threads:
        t.start()
    
    time.sleep(1)
    print(f"\n=== After starting threads ===")
    print(f"Active threads: {threading.active_count()}")
    print(f"Thread list: {[t.name for t in threading.enumerate()]}")
    print(f"\n--- INSPECT NOW ---")
    print(f"Run these commands in another terminal:")
    print(f"  cat /proc/{os.getpid()}/status | grep -i thread")
    print(f"  ls /proc/{os.getpid()}/task/")
    print(f"  ps -T -p {os.getpid()}")
    print(f"  top -H -p {os.getpid()}")
    
    # Wait for all threads
    for t in threads:
        t.join()
    
    print("\nAll threads finished!")

if __name__ == "__main__":
    main()
```

```bash
$ python3 threads_demo.py
=== Main Thread ===
PID: 15000
Main TID: 15000
Thread count: 1

Starting threads...
  [Worker-0] Started! PID=15000, TID=15001
  [Worker-1] Started! PID=15000, TID=15002
  [Worker-2] Started! PID=15000, TID=15003
  [Worker-0] Python thread ID: 140234567890432
  [Worker-1] Python thread ID: 140234567881216
  [Worker-2] Python thread ID: 140234567872000

=== After starting threads ===
Active threads: 4
Thread list: ['MainThread', 'Thread-1 (worker)', 'Thread-2 (worker)', 'Thread-3 (worker)']

--- INSPECT NOW ---
Run these commands in another terminal:
  cat /proc/15000/status | grep -i thread
  ls /proc/15000/task/
  ps -T -p 15000
  top -H -p 15000
```

**Notice:** All threads have the SAME PID (15000) but different TIDs (15000, 15001, 15002, 15003). From the outside, it looks like one process. Inside, there are 4 execution contexts.

---

## Threads in Linux: What the Kernel Actually Does

When Python calls `threading.Thread.start()`, here's the actual chain:

```
Python: threading.Thread.start()
   │
   ▼
CPython: _thread module (C code)
   │
   ▼
C library: pthread_create()
   │
   ▼
Linux kernel: clone(CLONE_VM | CLONE_FILES | CLONE_FS | CLONE_THREAD | CLONE_SIGHAND, 
                    child_stack=<new_stack_address>, ...)
   │
   ▼
Kernel:
  1. Allocate new task_struct (the "thread" is a new task)
  2. Copy parent's task_struct fields
  3. Point mm (memory descriptor) to SAME mm as parent (CLONE_VM)
  4. Point files to SAME files_struct as parent (CLONE_FILES)
  5. Allocate new stack (at child_stack address)
  6. Set PC (instruction pointer) to thread function start
  7. Set thread state to TASK_RUNNING
  8. Put on scheduler's run queue
  9. Return new TID
```

**After this, the kernel has TWO task_structs that share (almost) everything:**

```
┌──────────────────────────────┐    ┌──────────────────────────────┐
│ task_struct (TID 15000)      │    │ task_struct (TID 15001)      │
│ (main thread)                │    │ (Worker-0)                   │
├──────────────────────────────┤    ├──────────────────────────────┤
│ pid = 15000                  │    │ pid = 15001                  │
│ tgid = 15000                 │    │ tgid = 15000  ← SAME!       │
│ mm = 0xFFFF8800 ─────────┐  │    │ mm = 0xFFFF8800 ──────┐     │
│ files = 0xFFFF9900 ──┐   │  │    │ files = 0xFFFF9900 ─┐ │     │
│ state = SLEEPING     │   │  │    │ state = RUNNING     │ │     │
│ stack = 0x7FFF0000   │   │  │    │ stack = 0x7F3E0000  │ │     │
│ PC = (in sleep())    │   │  │    │ PC = (in worker())  │ │     │
└──────────────────────┼───┼──┘    └─────────────────────┼─┼─────┘
                       │   │                              │ │
                       │   └──── SAME mm_struct ──────────┘ │
                       │         (shared memory!)            │
                       └──────── SAME files_struct ──────────┘
                                 (shared file descriptors!)
```

**Key: `tgid` (Thread Group ID)** = what `getpid()` returns. All threads in a process have the same `tgid`. The `pid` field in task_struct is actually the TID. Confusing naming, but:
- `getpid()` → returns tgid (process ID, same for all threads)
- `gettid()` → returns pid field (thread ID, unique per thread)

