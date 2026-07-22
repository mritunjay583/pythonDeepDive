# Phase 1, Chapter 1e — Hands-On Experiments & Interview Questions

## Experiment 1: Watch a Process Born and Die

```python
# lifecycle.py — Watch the full life cycle
import os
import sys
import time

def child_work():
    """Child process does some work then exits."""
    print(f"  [CHILD PID {os.getpid()}] Born! Parent is {os.getppid()}")
    print(f"  [CHILD PID {os.getpid()}] State should be R (running)")
    
    # Do some work
    total = sum(range(10_000_000))
    print(f"  [CHILD PID {os.getpid()}] Computed: {total}")
    
    # Sleep (state → S)
    print(f"  [CHILD PID {os.getpid()}] Going to sleep... (state → S)")
    time.sleep(2)
    
    # Exit (state → Z until parent calls wait)
    print(f"  [CHILD PID {os.getpid()}] Exiting with code 42...")
    os._exit(42)

def main():
    print(f"[PARENT PID {os.getpid()}] Starting...")
    
    pid = os.fork()
    
    if pid == 0:
        child_work()
    else:
        print(f"[PARENT PID {os.getpid()}] Created child PID {pid}")
        
        # Give child time to exit → becomes zombie
        time.sleep(4)
        
        # Check if child is zombie
        print(f"[PARENT] Child should be zombie now. Check:")
        print(f"[PARENT] Run: cat /proc/{pid}/status | grep State")
        print(f"[PARENT] Or:  ps -p {pid} -o pid,state,comm")
        
        time.sleep(2)
        
        # Reap the zombie
        child_pid, status = os.waitpid(pid, 0)
        exit_code = os.WEXITSTATUS(status)
        print(f"[PARENT] Reaped child {child_pid}, exit code: {exit_code}")
        print(f"[PARENT] Zombie is gone now. /proc/{pid}/ no longer exists.")

if __name__ == "__main__":
    main()
```

**Run it and in another terminal:**
```bash
# Terminal 1:
$ python3 lifecycle.py

# Terminal 2 (while it's running):
$ watch -n 0.5 "ps -p <child_pid> -o pid,state,comm 2>/dev/null || echo 'Process gone'"
```

---

## Experiment 2: Multiple Processes, One Program

```python
# multi_process.py — See isolation in action
import os
import time

shared_before_fork = "I exist before fork"
counter = 0

print(f"Main process PID {os.getpid()}, counter = {counter}")

# Create 3 child processes
children = []
for i in range(3):
    pid = os.fork()
    if pid == 0:
        # CHILD
        counter += 1  # Each child modifies its OWN copy!
        print(f"  Child {i} (PID {os.getpid()}): counter = {counter}")
        print(f"  Child {i}: shared_before_fork = '{shared_before_fork}'")
        time.sleep(5)
        os._exit(0)
    else:
        children.append(pid)

# PARENT
print(f"\nParent (PID {os.getpid()}): counter = {counter}")  # Still 0!
print("Parent's counter is unchanged — children have COPIES, not shared memory!")
print(f"\nProcess tree (run this now):")
print(f"  pstree -p {os.getpid()}")
print(f"\nAll my children:")
for c in children:
    print(f"  PID {c}: /proc/{c}/status")

# Wait for all children
for c in children:
    os.waitpid(c, 0)
print("\nAll children finished.")
```

```bash
$ python3 multi_process.py
Main process PID 7000, counter = 0
  Child 0 (PID 7001): counter = 1
  Child 1 (PID 7002): counter = 1
  Child 2 (PID 7003): counter = 1

Parent (PID 7000): counter = 0
Parent's counter is unchanged — children have COPIES, not shared memory!
```

**Key insight:** After fork(), each child gets its own COPY of `counter`. When child increments it, parent's copy is unchanged. This is **process isolation** — the whole point of processes!

---

## Experiment 3: See COW (Copy-on-Write) in Action

```python
# cow_demo.py — Watch RSS (physical memory) before and after writes
import os
import time

def get_rss(pid):
    """Get Resident Set Size in KB."""
    with open(f'/proc/{pid}/status') as f:
        for line in f:
            if line.startswith('VmRSS:'):
                return line.split()[1] + ' kB'
    return 'unknown'

# Allocate 100MB of data
print("Allocating 100MB...")
big_data = bytearray(100 * 1024 * 1024)  # 100MB
for i in range(0, len(big_data), 4096):
    big_data[i] = 1  # Touch every page to ensure it's in RAM

print(f"Parent PID {os.getpid()}, RSS: {get_rss(os.getpid())}")

pid = os.fork()

if pid == 0:
    # CHILD
    print(f"\n  [CHILD PID {os.getpid()}] Just after fork:")
    print(f"  [CHILD] RSS: {get_rss(os.getpid())}")
    print(f"  [CHILD] (Pages are SHARED with parent — COW!)")
    
    time.sleep(2)
    
    # Now WRITE to the data — triggers COW page faults
    print(f"\n  [CHILD] Writing to all pages (triggering COW)...")
    for i in range(0, len(big_data), 4096):
        big_data[i] = 2  # Write to every page → each page gets copied
    
    print(f"  [CHILD] After writes, RSS: {get_rss(os.getpid())}")
    print(f"  [CHILD] (Now we have our OWN copy of all 100MB)")
    
    time.sleep(5)
    os._exit(0)
else:
    # PARENT
    time.sleep(1)
    print(f"\n  [PARENT PID {os.getpid()}] RSS: {get_rss(os.getpid())}")
    time.sleep(5)
    print(f"\n  [PARENT] After child wrote (COW happened):")
    print(f"  [PARENT] RSS: {get_rss(os.getpid())}")
    os.waitpid(pid, 0)
```

**Expected output:**
```
Parent PID 8000, RSS: 105000 kB

  [CHILD PID 8001] Just after fork:
  [CHILD] RSS: 105000 kB          ← Looks like 100MB but pages are SHARED!
  (Physical RAM used: still ~105MB total, not 210MB)

  [CHILD] Writing to all pages (triggering COW)...
  [CHILD] After writes, RSS: 105000 kB
  (NOW physical RAM: ~210MB — both parent and child have their own copies)
```

---

## Experiment 4: strace Your Python Script

```bash
# See EVERY system call Python makes when starting
$ strace -c python3 -c "print('hello')"
hello
% time     seconds  usecs/call     calls    errors syscall
------ ----------- ----------- --------- --------- ----------------
 25.00    0.003200         2       1420           read
 20.00    0.002560         5        456           mmap
 15.00    0.001920         3        550           fstat
 10.00    0.001280         8        152           openat
  8.00    0.001024         4        215           close
  5.00    0.000640         3        187           rt_sigaction
  ...
------ ----------- ----------- --------- --------- ----------------
100.00    0.012800                  3500        30 total

# Python makes ~3500 system calls just to print "hello"!
# Most are: reading .py files, loading modules, setting up signal handlers
```

```bash
# Trace JUST process-related calls
$ strace -f -e trace=clone,execve,wait4 bash -c "python3 -c 'import os; print(os.getpid())'"
execve("/bin/bash", [...]) = 0
clone(...) = 9000                        ← bash forks
[pid 9000] execve("/usr/bin/python3", [...]) = 0   ← child execs python
[pid 9000] write(1, "9000\n", 5) = 5
[pid 9000] +++ exited with 0 +++
wait4(-1, ...) = 9000                    ← bash reaps child
```

---

## Summary: The Mental Model

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                       │
│  PROGRAM (disk)                                                      │
│  └── Just a file. Dead. Inert.                                       │
│                                                                       │
│  PROCESS (RAM + kernel)                                              │
│  └── Living instance of a program                                    │
│      Created by fork() + exec()                                      │
│      Tracked by task_struct (PCB) in kernel                          │
│      Has: PID, memory space, file descriptors, state                 │
│      Inspectable via /proc/<pid>/                                    │
│                                                                       │
│  KEY OPERATIONS:                                                     │
│  • fork()  → clone current process (COW optimization)               │
│  • exec()  → replace process memory with new program                │
│  • wait()  → parent collects child's exit status                    │
│  • exit()  → process terminates, becomes zombie until reaped        │
│                                                                       │
│  STATES: R(running) → S(sleeping) → R → ... → Z(zombie) → gone    │
│                                                                       │
│  LINUX TOOLS:                                                        │
│  • /proc/<pid>/status  — state, memory, threads                     │
│  • /proc/<pid>/maps    — memory layout                              │
│  • /proc/<pid>/fd/     — open files/sockets                         │
│  • /proc/<pid>/sched   — scheduling info                            │
│  • ps, top, htop       — process monitoring                         │
│  • strace              — trace system calls                         │
│  • pstree              — process tree                               │
│  • pmap                — memory map                                  │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Interview Questions

### Q1: What is the difference between a program and a process?

**Answer:** A program is a passive entity — a file on disk containing instructions. A process is an active entity — a running instance of a program managed by the OS. A process has a PID, virtual address space, open file descriptors, and a state. You can run the same program as multiple independent processes.

### Q2: What happens when you type `python3 app.py` in a terminal?

**Answer:**
1. Shell (bash) calls `fork()` → creates child process (COW copy of bash)
2. Child calls `execve("/usr/bin/python3", ["python3", "app.py"])` → replaces its memory with Python interpreter
3. Kernel allocates a new task_struct, sets up page tables, opens default fds (0,1,2)
4. Python interpreter starts, reads `app.py`, compiles to bytecode, executes
5. Shell calls `waitpid()` to wait for child (or continues if `&` was used)

### Q3: What is the Process Control Block (PCB)? What does it contain?

**Answer:** The PCB (called `task_struct` in Linux) is the kernel's data structure for tracking a process. It contains:
- PID and parent PID
- Process state (running, sleeping, zombie, etc.)
- Pointer to memory descriptor (page tables, VMAs)
- Open file descriptor table
- Scheduling info (priority, vruntime, policy)
- CPU register save area (for context switches)
- Signal handlers and pending signals
- Credentials (UID, GID, capabilities)
- Accounting info (CPU time used, start time)

### Q4: What is Copy-on-Write and why does it matter?

**Answer:** COW means that after `fork()`, parent and child initially SHARE the same physical memory pages (marked read-only). Only when one of them WRITES to a page does the kernel copy that specific page. This makes fork() nearly instant (O(page_table_size) not O(memory_size)) and is critical for:
- Redis BGSAVE (fork child to write snapshot, shares data with parent)
- Shell operations (fork+exec — no pages need copying since exec replaces everything)
- PostgreSQL connection handling (fork per client, shared buffer pool initially)

### Q5: What is a zombie process and how do you fix it?

**Answer:** A zombie is a process that has exited but whose parent hasn't called `wait()` to collect its exit status. The kernel keeps the task_struct alive (with exit code) until the parent reads it. Fix: ensure parent calls `wait()`/`waitpid()`, use `SIGCHLD` handler with `SIG_IGN`, or fix the parent process. If parent dies, `init` (PID 1) becomes the new parent and auto-reaps zombies.

### Q6: Can a process exist without a program?

**Answer:** Sort of. After `fork()` and before `exec()`, the child process is running the parent's program. Kernel threads (like `kworker`, `ksoftirqd`) are processes without a user-space program — they run kernel code only and have `mm = NULL` (no user address space). The `[kthreadd]` process (PID 2) creates all kernel threads.

### Q7: Why does Linux use fork()+exec() instead of a single "create process from file" call?

**Answer:** Separation of concerns. Between fork() and exec(), the child can:
- Redirect stdin/stdout (for shell pipes: `cmd1 | cmd2`)
- Change directory (`cd` before exec)
- Set environment variables
- Close/open file descriptors
- Change user ID (for privilege dropping)
- Set resource limits

Windows uses `CreateProcess()` which does everything at once — less flexible, needs many parameters.

### Q8: If fork() copies the process, why doesn't it double memory usage?

**Answer:** Copy-on-Write. After fork(), both processes share the same physical pages (marked read-only in page tables). Memory is only duplicated when one process writes to a page, and only THAT page is copied. If the child immediately calls exec() (the common case in shells), zero pages need copying because exec() replaces all memory anyway.

---

## What's Next

Now you understand:
- What a process IS (and isn't)
- How it's created (fork + exec)
- How the kernel tracks it (task_struct / PCB)
- How to inspect it on Linux (/proc, ps, strace)
- Process states and lifecycle

**Next Chapter:** Threads — why they exist, how they share memory within a process, and the difference between OS threads, green threads, and Python's GIL problem.

