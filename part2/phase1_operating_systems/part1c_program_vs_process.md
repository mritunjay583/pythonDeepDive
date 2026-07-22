# Phase 1, Chapter 1c — The Process Control Block (task_struct)

## What is the PCB?

When the kernel creates a process, it needs a data structure to track everything about it. In Linux, this is called `task_struct`. In textbooks, it's called the **Process Control Block (PCB)**.

Think of it as the process's "passport" — all its identity and state information in one place.

---

## The Linux task_struct (Simplified)

The real `task_struct` in Linux kernel source is **~800 lines** and contains hundreds of fields. Here's what matters:

```c
// Simplified from: linux/include/linux/sched.h
struct task_struct {
    // ─── IDENTITY ───
    pid_t pid;                    // Process ID (12345)
    pid_t tgid;                   // Thread Group ID (= PID for main thread)
    char comm[16];                // Name ("python3")
    
    // ─── STATE ───
    unsigned int __state;         // TASK_RUNNING, TASK_INTERRUPTIBLE, etc.
    int exit_code;                // Exit status when process dies
    
    // ─── RELATIONSHIPS ───
    struct task_struct *parent;   // Pointer to parent process
    struct list_head children;    // List of child processes
    struct list_head sibling;     // Links to other children of same parent
    
    // ─── SCHEDULING ───
    int prio;                     // Priority (0-139)
    unsigned int policy;          // Scheduling policy (SCHED_NORMAL, SCHED_FIFO)
    struct sched_entity se;       // CFS scheduling entity (vruntime, etc.)
    int on_cpu;                   // Is it currently on a CPU?
    unsigned int cpu;             // Which CPU it last ran on
    
    // ─── MEMORY ───
    struct mm_struct *mm;         // Memory descriptor (page tables, VMAs)
                                  // mm->pgd = pointer to page table root
                                  // mm->mmap = list of memory regions
    
    // ─── FILE SYSTEM ───
    struct files_struct *files;   // Open file descriptor table
                                  // files->fd_array[0] = stdin
                                  // files->fd_array[1] = stdout
                                  // files->fd_array[3] = our socket!
    struct fs_struct *fs;         // Current directory, root directory
    
    // ─── SIGNALS ───
    struct signal_struct *signal; // Signal handlers (SIGKILL, SIGTERM, etc.)
    sigset_t blocked;             // Blocked signals mask
    
    // ─── TIMING ───
    u64 utime;                    // Time spent in user mode (nanoseconds)
    u64 stime;                    // Time spent in kernel mode (nanoseconds)
    u64 start_time;               // When process was created
    
    // ─── CREDENTIALS ───
    const struct cred *cred;      // User ID, Group ID, capabilities
};
```

---

## Visualizing the PCB for Our Python Process

```
┌─────────────────────────────────────────────────────────────────────┐
│                task_struct for PID 12345                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─── Identity ────────────────────────────────────────────────┐    │
│  │ pid = 12345                                                  │    │
│  │ comm = "python3"                                             │    │
│  │ parent = &task_struct_of_bash (PID 11001)                   │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─── State ───────────────────────────────────────────────────┐    │
│  │ __state = TASK_INTERRUPTIBLE (sleeping, waiting for timer)   │    │
│  │ on_cpu = 0 (not currently running on any CPU)               │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─── Memory (mm_struct *mm) ──────────────────────────────────┐    │
│  │ pgd = 0x... (page table root — translates virtual→physical) │    │
│  │ total_vm = 52340 kB (total virtual memory)                   │    │
│  │ rss = 28456 kB (resident in physical RAM)                    │    │
│  │                                                              │    │
│  │ VMAs (Virtual Memory Areas):                                 │    │
│  │   0x55d4a2200000-0x55d4a29e0000 r-x python3 (code)         │    │
│  │   0x55d4a3000000-0x55d4a4500000 rw- [heap]                 │    │
│  │   0x7ffd12300000-0x7ffd12321000 rw- [stack]                 │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─── Files (files_struct *files) ─────────────────────────────┐    │
│  │ fd[0] → /dev/pts/0 (stdin)                                  │    │
│  │ fd[1] → /dev/pts/0 (stdout)                                 │    │
│  │ fd[2] → /dev/pts/0 (stderr)                                 │    │
│  │ fd[3] → socket (TCP, LISTEN, 127.0.0.1:9999)               │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                       │
│  ┌─── Scheduling ─────────────────────────────────────────────┐     │
│  │ prio = 120 (default normal priority)                        │     │
│  │ policy = SCHED_NORMAL (CFS scheduler)                       │     │
│  │ se.vruntime = 45230000000 (virtual runtime in ns)           │     │
│  │ last_cpu = 2 (last ran on CPU core 2)                       │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                                                                       │
│  ┌─── Timing ─────────────────────────────────────────────────┐     │
│  │ utime = 1230000000 ns (1.23s in user mode)                  │     │
│  │ stime =  150000000 ns (0.15s in kernel mode)                │     │
│  │ start_time = <boot time + offset>                           │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Where Does the Kernel Store task_structs?

The kernel maintains ALL task_structs in memory. It can find them by:

1. **PID hash table** — O(1) lookup by PID
2. **Task list** — Doubly linked list of ALL processes
3. **Run queue** — Per-CPU list of RUNNABLE processes (for scheduler)
4. **Wait queues** — Lists of SLEEPING processes (waiting for specific events)

```
KERNEL MEMORY:
┌──────────────────────────────────────────────────────────────────┐
│                                                                    │
│  PID Hash Table:                                                  │
│  [hash(1)]    → task_struct (systemd)                            │
│  [hash(800)]  → task_struct (sshd)                               │
│  [hash(12345)]→ task_struct (python3) ← OUR PROCESS              │
│                                                                    │
│  Run Queue (CPU 0):     Run Queue (CPU 1):                       │
│  ┌─────────────────┐   ┌─────────────────┐                      │
│  │ task A (running) │   │ task D (running) │                      │
│  │ task B (ready)   │   │ task E (ready)   │                      │
│  └─────────────────┘   └─────────────────┘                      │
│                                                                    │
│  Wait Queue (timer):                                              │
│  ┌─────────────────┐                                             │
│  │ python3 (12345)  │ ← Sleeping, waiting for timer to fire     │
│  │ cron (600)       │                                            │
│  └─────────────────┘                                             │
│                                                                    │
└──────────────────────────────────────────────────────────────────┘
```

---

## See task_struct Fields from Userspace

You can't directly read kernel memory, but `/proc` exposes most task_struct fields:

```bash
# ─── Mapping /proc files to task_struct fields ───

# task_struct.pid
$ cat /proc/12345/status | grep "^Pid:"
Pid:    12345

# task_struct.__state
$ cat /proc/12345/status | grep "^State:"
State:  S (sleeping)

# task_struct.mm (memory info)
$ cat /proc/12345/status | grep "^Vm"
VmPeak:    52340 kB
VmSize:    52340 kB
VmRSS:     28456 kB

# task_struct.files (open file descriptors)
$ ls /proc/12345/fd/
0  1  2  3

# task_struct scheduling info
$ cat /proc/12345/sched
python3 (12345, #threads: 1)
-----------------------------------------------------------
se.exec_start                :      98765432100
se.vruntime                  :      45230000000
se.sum_exec_runtime          :       1380000000
nr_switches                  :            15234
nr_voluntary_switches        :            15200  ← went to sleep voluntarily
nr_involuntary_switches      :               34  ← preempted by scheduler

# task_struct timing
$ cat /proc/12345/stat | awk '{print "utime="$14, "stime="$15}'
utime=123 stime=15   # In clock ticks (usually 100 ticks/sec)
```

---

## The Life Cycle of a Process

```
                    fork()
    Parent ───────────────────► Child (copy of parent)
    (bash)                         │
                                   │ exec("python3")
                                   ▼
                              New program loaded
                              (python3 server.py)
                                   │
                                   │ Runs...
                                   │
            ┌──────────────────────┼──────────────────────────┐
            │                      │                           │
            ▼                      ▼                           ▼
       RUNNING (R)           SLEEPING (S)               DISK SLEEP (D)
    (doing CPU work)      (time.sleep, I/O wait)      (waiting for disk)
            │                      │                           │
            │                      │                           │
            └──────────────────────┼───────────────────────────┘
                                   │
                                   │ exit() or signal
                                   ▼
                              ZOMBIE (Z)
                         (exit code stored,
                          waiting for parent
                          to call wait())
                                   │
                                   │ Parent calls wait()
                                   ▼
                              REMOVED (X)
                         (task_struct freed,
                          PID recycled)
```

### Seeing a Zombie Process:

```python
# zombie_demo.py — Creates a zombie process!
import os
import time

pid = os.fork()  # Create child process

if pid == 0:
    # CHILD: exit immediately
    print(f"Child (PID {os.getpid()}) exiting...")
    os._exit(0)
else:
    # PARENT: don't call wait() — child becomes zombie!
    print(f"Parent (PID {os.getpid()}) NOT calling wait()")
    print(f"Child PID was: {pid}")
    print("Check: ps aux | grep Z")
    time.sleep(60)  # Keep parent alive so zombie stays
```

```bash
$ python3 zombie_demo.py &
Parent (PID 20000) NOT calling wait()
Child PID was: 20001
Child (PID 20001) exiting...

$ ps aux | grep 20001
user     20001  0.0  0.0  0  0 pts/0  Z    10:05   0:00 [python3] <defunct>
#                                      ^ ZOMBIE!

$ cat /proc/20001/status | grep State
State:  Z (zombie)
```

**Why zombies are bad:** Each zombie holds a task_struct (a few KB) and a PID. If you create millions of zombies, you run out of PIDs (max is usually 32768 or 4194304).

**Fix:** Parent must call `wait()` or `waitpid()` to collect the child's exit status. Or use `signal(SIGCHLD, SIG_IGN)` to auto-reap children.

