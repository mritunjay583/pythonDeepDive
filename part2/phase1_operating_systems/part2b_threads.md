# Phase 1, Chapter 2b — Inspecting Threads Live on Linux

## See Threads in /proc

Every thread gets its own directory inside `/proc/<pid>/task/`:

```bash
# Our process PID is 15000, it has 4 threads
$ ls /proc/15000/task/
15000  15001  15002  15003
#  │      │      │      │
#  │      │      │      └── Worker-2 (TID 15003)
#  │      │      └── Worker-1 (TID 15002)
#  │      └── Worker-0 (TID 15001)
#  └── Main thread (TID 15000 = same as PID)
```

Each thread has its OWN `/proc/<pid>/task/<tid>/` with its own status, stack, etc:

```bash
# Main thread status
$ cat /proc/15000/task/15000/status | grep -E "^(Name|State|Pid|Tgid)"
Name:   python3
State:  S (sleeping)       ← main thread sleeping (in time.sleep or join)
Pid:    15000              ← TID of this thread
Tgid:   15000             ← Thread Group ID (= the "PID" everyone sees)

# Worker-0 thread status
$ cat /proc/15000/task/15001/status | grep -E "^(Name|State|Pid|Tgid)"
Name:   python3
State:  R (running)        ← this thread is actually computing!
Pid:    15001              ← TID of this thread
Tgid:   15000             ← Same process! Same tgid!
```

---

## See Threads with ps

```bash
# Show threads for PID 15000
$ ps -T -p 15000
  PID   SPID TTY          TIME CMD
15000  15000 pts/0    00:00:00 python3    ← main thread
15000  15001 pts/0    00:00:01 python3    ← Worker-0
15000  15002 pts/0    00:00:01 python3    ← Worker-1
15000  15003 pts/0    00:00:01 python3    ← Worker-2

# SPID = "scheduler PID" = TID (thread ID)
# PID is the same for all (15000) — they're all in the same process

# More detail:
$ ps -T -p 15000 -o pid,spid,state,pcpu,comm
  PID   SPID S %CPU COMMAND
15000  15000 S  0.0 python3     ← main: sleeping
15000  15001 R 24.5 python3     ← Worker-0: running (computing)
15000  15002 S  0.1 python3     ← Worker-1: sleeping
15000  15003 R 24.8 python3     ← Worker-2: running
```

---

## See Threads with top (per-thread view)

```bash
# -H shows individual threads
$ top -H -p 15000

  PID USER      PR  NI    VIRT    RES    SHR S  %CPU %MEM     TIME+ COMMAND
15000 user      20   0  285432  28456   8200 S   0.0  0.7   0:00.05 python3
15001 user      20   0  285432  28456   8200 R  25.0  0.7   0:01.23 python3
15002 user      20   0  285432  28456   8200 S   0.1  0.7   0:01.22 python3
15003 user      20   0  285432  28456   8200 R  24.8  0.7   0:01.21 python3

# Notice: VIRT and RES are SAME for all threads!
# They share the same memory space!
# But %CPU differs — each thread does its own work
```

---

## Thread Stacks: Each Thread Has Its Own

```bash
# See the memory map — look for thread stacks
$ cat /proc/15000/maps | grep stack
7f3dc0000000-7f3dc0800000 rw-p 00000000 00:00 0    ← Worker-2 stack (8MB)
7f3dc8000000-7f3dc8800000 rw-p 00000000 00:00 0    ← Worker-1 stack (8MB)
7f3dd0000000-7f3dd0800000 rw-p 00000000 00:00 0    ← Worker-0 stack (8MB)
7ffd12300000-7ffd12321000 rw-p 00000000 00:00 0 [stack]  ← Main thread stack
```

Each thread has ~8MB of stack space allocated. They're at DIFFERENT addresses because each thread needs its own stack for:
- Local variables
- Function call frames
- Return addresses

**But the heap, code, and data are the SAME mappings** for all threads. That's the whole point.

---

## Proof: Threads Share Memory

```python
# shared_memory_demo.py — Prove threads share the same memory
import threading
import time
import os

# This list lives on the HEAP — shared between all threads
shared_list = []
shared_counter = [0]  # Using list to avoid Python closure issues

def writer(thread_id):
    """Writes to shared data structure."""
    for i in range(5):
        shared_list.append(f"Thread-{thread_id} wrote item {i}")
        shared_counter[0] += 1
        time.sleep(0.1)
    print(f"  [Writer-{thread_id}] Done. Counter = {shared_counter[0]}")

def reader():
    """Reads the shared data structure."""
    time.sleep(0.3)  # Let writers get ahead
    print(f"  [Reader] Shared list has {len(shared_list)} items:")
    for item in shared_list:
        print(f"    {item}")
    print(f"  [Reader] Counter = {shared_counter[0]}")

def main():
    print(f"PID: {os.getpid()}")
    print(f"Initial: shared_list = {shared_list}")
    print(f"Initial: shared_counter = {shared_counter[0]}")
    print()
    
    # Start 3 writer threads and 1 reader thread
    threads = []
    for i in range(3):
        t = threading.Thread(target=writer, args=(i,))
        threads.append(t)
    
    reader_thread = threading.Thread(target=reader)
    threads.append(reader_thread)
    
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    print(f"\nFinal: shared_list has {len(shared_list)} items")
    print(f"Final: shared_counter = {shared_counter[0]}")
    print("ALL threads wrote to the SAME list and counter in the SAME process memory!")

if __name__ == "__main__":
    main()
```

```bash
$ python3 shared_memory_demo.py
PID: 16000
Initial: shared_list = []
Initial: shared_counter = 0

  [Writer-0] Done. Counter = 7
  [Writer-1] Done. Counter = 12
  [Writer-2] Done. Counter = 15
  [Reader] Shared list has 9 items:
    Thread-0 wrote item 0
    Thread-1 wrote item 0
    Thread-2 wrote item 0
    Thread-0 wrote item 1
    ...
  [Reader] Counter = 15

Final: shared_list has 15 items
Final: shared_counter = 15
ALL threads wrote to the SAME list and counter in the SAME process memory!
```

**Compare this to processes:** If we used `fork()`, each child would get its OWN copy of `shared_list`. The parent's list would stay empty. With threads, everyone writes to the SAME list because they share the heap.

---

## Contrast: Same Program with Processes (Isolation)

```python
# process_isolation_demo.py — Same idea but with processes
import os
import time

shared_list = []
shared_counter = [0]

def writer_process(proc_id):
    """In a child process — has its OWN copy of everything."""
    for i in range(5):
        shared_list.append(f"Process-{proc_id} wrote item {i}")
        shared_counter[0] += 1
    print(f"  [Process-{proc_id}] My list has {len(shared_list)} items")
    print(f"  [Process-{proc_id}] My counter = {shared_counter[0]}")
    os._exit(0)

def main():
    print(f"Parent PID: {os.getpid()}")
    print(f"Parent list: {shared_list}")
    
    children = []
    for i in range(3):
        pid = os.fork()
        if pid == 0:
            writer_process(i)
        children.append(pid)
    
    for c in children:
        os.waitpid(c, 0)
    
    print(f"\nParent list: {shared_list}")
    print(f"Parent counter: {shared_counter[0]}")
    print("Parent's data is UNCHANGED — children modified their OWN copies!")

if __name__ == "__main__":
    main()
```

```bash
$ python3 process_isolation_demo.py
Parent PID: 17000
Parent list: []
  [Process-0] My list has 5 items
  [Process-0] My counter = 5
  [Process-1] My list has 5 items
  [Process-1] My counter = 5
  [Process-2] My list has 5 items
  [Process-2] My counter = 5

Parent list: []              ← UNCHANGED! Children had their own copies!
Parent counter: 0            ← UNCHANGED!
```

**This is THE fundamental difference:**
- **Threads** share memory → easy communication, but need synchronization
- **Processes** have isolated memory → safe, but need IPC for communication

---

## Thread Control Block (TCB) — What the Kernel Stores Per Thread

Just like processes have task_struct, each thread has its own task_struct (remember: in Linux, threads ARE tasks). But threads share most of the pointers:

```
┌─────────────────────────────────────────────────────────────────────┐
│ task_struct for Thread (TID 15001, Worker-0)                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  THREAD-SPECIFIC (different per thread):                             │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ pid (TID) = 15001                                             │   │
│  │ state = TASK_RUNNING                                          │   │
│  │ stack pointer = 0x7F3DD07FF000                                │   │
│  │ instruction pointer (PC) = 0x... (somewhere in worker())     │   │
│  │ registers = {RAX=..., RBX=..., ...}                          │   │
│  │ on_cpu = 3 (running on CPU core 3)                           │   │
│  │ prio = 120                                                    │   │
│  │ se.vruntime = ...                                             │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  SHARED (point to SAME structures as other threads):                 │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ tgid = 15000 (thread group = process)                         │   │
│  │ mm → (same mm_struct as TID 15000, 15002, 15003)             │   │
│  │ files → (same files_struct as all other threads)              │   │
│  │ signal → (same signal_struct)                                 │   │
│  │ parent → task_struct of bash                                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

**The scheduler doesn't distinguish between "threads" and "processes."** It schedules task_structs. Each task_struct gets CPU time independently. Whether it shares memory with another task or not doesn't matter to the scheduler.

---

## Thread Stack Layout in Memory

```
PROCESS VIRTUAL ADDRESS SPACE (simplified):
┌─────────────────────────────────────────────────┐ HIGH
│                                                   │
│  Main thread stack (grows ↓)                     │ ← 0x7FFF...
│  ┌─────────────────────────────────────────────┐ │
│  │ main() frame                                 │ │
│  │ worker() frame (if called from main)         │ │
│  │ ... (grows downward)                         │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  guard page (unmapped — causes SIGSEGV on overflow)│
│                                                   │
│  Worker-0 stack (8MB allocated, grows ↓)         │ ← 0x7F3DD...
│  ┌─────────────────────────────────────────────┐ │
│  │ worker("Worker-0", 10) frame                 │ │
│  │ range() iterator frame                       │ │
│  │ ... (grows downward)                         │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  guard page                                      │
│                                                   │
│  Worker-1 stack (8MB allocated, grows ↓)         │ ← 0x7F3DC8...
│  ┌─────────────────────────────────────────────┐ │
│  │ worker("Worker-1", 10) frame                 │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  ...                                             │
│                                                   │
│  ═══════════════════════════════════════════════  │
│  HEAP (shared between ALL threads)               │ ← grows ↑
│  ┌─────────────────────────────────────────────┐ │
│  │ shared_list object                           │ │
│  │ shared_counter object                        │ │
│  │ all Python objects                           │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  DATA / BSS (globals)                            │
│  CODE (text) — Python interpreter instructions   │
└─────────────────────────────────────────────────┘ LOW
```

**Guard pages:** Between thread stacks, the kernel places unmapped pages. If a stack overflows (grows past its limit), it hits the guard page → CPU generates SIGSEGV → process crashes. This prevents one thread's stack from silently corrupting another thread's stack.

---

## strace: Watch Thread Creation

```bash
# Trace system calls including threads (-f follows forks/clones)
$ strace -f -e trace=clone,write python3 -c "
import threading
import time

def worker():
    time.sleep(1)

t = threading.Thread(target=worker)
t.start()
t.join()
"

clone(child_stack=0x7f3dd07fefb0, 
      flags=CLONE_VM|CLONE_FS|CLONE_FILES|CLONE_SIGHAND|CLONE_THREAD|
            CLONE_SYSVSEM|CLONE_SETTLS|CLONE_PARENT_SETTID|CLONE_CHILD_CLEARTID,
      parent_tid=[15001], tls=0x7f3dd0800700, child_tidptr=0x7f3dd08009d0) = 15001
#                                                                              ^^^
#                                                              New thread's TID!

# FLAGS DECODED:
# CLONE_VM       = share virtual memory (CRITICAL — this makes it a thread!)
# CLONE_FS       = share filesystem info
# CLONE_FILES    = share file descriptor table
# CLONE_SIGHAND  = share signal handlers
# CLONE_THREAD   = same thread group (same PID from outside)
```

**This is the proof:** Creating a thread is literally calling `clone()` with flags that say "share everything." Creating a process is `clone()` with flags that say "copy everything."

