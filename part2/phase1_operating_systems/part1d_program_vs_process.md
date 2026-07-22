# Phase 1, Chapter 1d — fork() and exec(): How Processes Are Born

## The Two System Calls That Create Every Process

On Linux, there is only ONE way to create a new process: `fork()`. And there's ONE way to load a new program into a process: `exec()`.

```
fork()  = Create a COPY of the current process
exec()  = REPLACE current process's memory with a new program
```

Every process you see on your machine (except PID 1) was created by fork(). Let's see it.

---

## fork() — Creating a Copy

```python
# fork_demo.py
import os

print(f"Before fork. I am PID {os.getpid()}")

pid = os.fork()  # THIS IS WHERE THE MAGIC HAPPENS

if pid == 0:
    # This code runs in the CHILD
    print(f"  CHILD: My PID = {os.getpid()}, My parent = {os.getppid()}")
    print(f"  CHILD: I'm a copy of my parent!")
else:
    # This code runs in the PARENT
    print(f"  PARENT: My PID = {os.getpid()}, I created child PID = {pid}")
    os.wait()  # Wait for child to finish (prevents zombie)
```

```bash
$ python3 fork_demo.py
Before fork. I am PID 5000
  PARENT: My PID = 5000, I created child PID = 5001
  CHILD: My PID = 5001, My parent = 5000
  CHILD: I'm a copy of my parent!
```

### What Happened in the Kernel:

```
BEFORE fork():
┌──────────────────────────────────┐
│ Process 5000 (python3)           │
│ • Memory: code + data + heap     │
│ • Files: fd 0,1,2                │
│ • State: Running                 │
│ • PC: at fork() call             │
└──────────────────────────────────┘

AFTER fork():
┌──────────────────────────────────┐    ┌──────────────────────────────────┐
│ Process 5000 (PARENT)            │    │ Process 5001 (CHILD)             │
│ • Memory: same code+data+heap    │    │ • Memory: COPY of parent's       │
│ • Files: fd 0,1,2                │    │ • Files: COPY of fd 0,1,2        │
│ • fork() returned: 5001 (child)  │    │ • fork() returned: 0             │
│ • Continues after fork()         │    │ • Continues after fork()         │
└──────────────────────────────────┘    └──────────────────────────────────┘
```

**Critical details:**
1. `fork()` is called ONCE but returns TWICE (once in parent, once in child)
2. In parent: `fork()` returns child's PID
3. In child: `fork()` returns 0
4. Child is a COPY of parent — same code, same data, same open files
5. But they have SEPARATE memory after fork (changes in one don't affect the other)

---

## Copy-on-Write (COW) — The Efficiency Trick

"Wait, copying all memory every fork() would be insanely expensive!"

You're right. Linux uses **Copy-on-Write (COW)**:

```
AFTER fork() — REALITY (with COW):

Both processes initially SHARE the same physical pages (read-only):

Physical RAM:
┌────────────────────────────────────────┐
│ Page of code    (shared, read-only)    │ ← Both processes point here
│ Page of data    (shared, read-only)    │ ← Both processes point here  
│ Page of heap    (shared, read-only)    │ ← Both processes point here
└────────────────────────────────────────┘

Process 5000 page table:  virtual addr → physical page (read-only)
Process 5001 page table:  virtual addr → SAME physical page (read-only)

WHEN child WRITES to a page:
1. CPU triggers a PAGE FAULT (tried to write to read-only page)
2. Kernel handles fault:
   - Copies JUST THAT ONE PAGE to new physical memory
   - Updates child's page table to point to the copy
   - Makes the copy writable
3. Now child has its own copy of that page
4. Parent still uses the original

This is "copy-on-WRITE" — only copy when someone writes!
```

**Why this matters for real systems:**
- `fork()` is nearly instant (just copy page tables, not pages)
- Redis uses fork() for `BGSAVE` — child shares parent's data (COW), writes snapshot to disk
- PostgreSQL uses fork() for each connection
- If child just calls exec() immediately (like shell does), no pages need copying at all!

---

## exec() — Loading a New Program

`exec()` replaces the current process's memory with a new program:

```python
# exec_demo.py
import os

print(f"I am PID {os.getpid()}, about to exec 'ls'")
print("After exec(), this Python code is GONE forever")

# Replace this process with 'ls -la'
os.execvp('ls', ['ls', '-la', '/tmp'])

# THIS LINE NEVER EXECUTES — the process is now running 'ls'!
print("You will NEVER see this message")
```

```bash
$ python3 exec_demo.py
I am PID 6000, about to exec 'ls'
After exec(), this Python code is GONE forever
drwxrwxrwt 15 root root 4096 Jan 15 10:30 /tmp    ← This is 'ls' output!
# Note: "You will NEVER see this message" never appears
```

### What exec() Does in the Kernel:

```
BEFORE exec():
┌──────────────────────────────────┐
│ Process 6000                     │
│ Code: Python interpreter         │
│ Data: Python objects, variables  │
│ Heap: Python allocations         │
│ Stack: Python call stack         │
│ PID: 6000 (unchanged)           │
│ Files: fd 0,1,2 (unchanged)     │
└──────────────────────────────────┘

AFTER exec("ls"):
┌──────────────────────────────────┐
│ Process 6000  ← SAME PID!       │
│ Code: ls binary code (NEW)       │
│ Data: ls data (NEW)              │
│ Heap: empty (NEW)                │
│ Stack: fresh stack (NEW)         │
│ PID: 6000 (unchanged!)          │
│ Files: fd 0,1,2 (inherited!)    │
└──────────────────────────────────┘

exec() keeps: PID, PPID, file descriptors, signal mask, UID/GID
exec() replaces: code, data, heap, stack, registers
```

---

## The fork()+exec() Pattern — How Shells Work

When you type `python3 server.py` in bash:

```python
# What bash does (simplified pseudocode):
while True:
    cmd = input("$ ")                    # Read command
    
    pid = os.fork()                      # Step 1: Create child
    
    if pid == 0:
        # CHILD process
        os.execvp(cmd[0], cmd)           # Step 2: Replace with new program
        # If exec succeeds, this line never runs
        # If exec fails (command not found):
        print(f"bash: {cmd[0]}: command not found")
        os._exit(127)
    else:
        # PARENT (bash)
        os.waitpid(pid, 0)              # Step 3: Wait for child to finish
        # Then show prompt again
```

### The Full Picture When You Run `python3 server.py`:

```
TIME ──────────────────────────────────────────────────────────►

BASH (PID 11001):
│
├── You type: python3 server.py
│
├── fork() ─────────────────────────────────────────────────────
│         │                                                     
│         │ Creates child (PID 12345)                          
│         │                                                     
│         │         CHILD (PID 12345):                         
│         │         │                                          
│         │         ├── exec("python3", "server.py")           
│         │         │   • Old memory GONE                      
│         │         │   • Python interpreter loaded            
│         │         │   • Python reads server.py               
│         │         │   • Bytecode compiled and executed       
│         │         │                                          
│         │         ├── socket(), bind(), listen()             
│         │         │                                          
│         │         ├── while True: time.sleep(1)             
│         │         │       │                                  
│         │         │       ▼                                  
│         │         │   (process sleeping...)                   
│         │                                                     
├── waitpid(12345) ← bash waits here (blocked)                 
│   (or if you used &, bash doesn't wait)                      
│                                                               
```

---

## Practical: Trace fork/exec with strace

`strace` shows every system call a process makes. This is GOLD for understanding what happens:

```bash
# Trace bash as it runs a command
$ strace -f -e trace=process bash -c "python3 -c 'import os; print(os.getpid())'"

execve("/bin/bash", ["bash", "-c", "python3 -c 'import os; print(os.getpid())'"], ...) = 0
clone(child_stack=NULL, flags=CLONE_CHILD_CLEARTID|...) = 12345    ← fork!
[pid 12345] execve("/usr/bin/python3", ["python3", "-c", ...]) = 0  ← exec!
[pid 12345] write(1, "12345\n", 6) = 6                             ← print()
[pid 12345] exit_group(0) = ?                                       ← exit
--- SIGCHLD {si_signo=SIGCHLD, si_pid=12345, si_status=0} ---      ← parent notified
wait4(-1, [{WIFEXITED(s) && WEXITSTATUS(s) == 0}], ...) = 12345   ← parent reaps
```

**Note:** Linux actually uses `clone()` instead of `fork()`. `clone()` is more flexible — it lets you choose what to share (memory, files, etc.) between parent and child. `fork()` is just `clone()` with "share nothing" flags. `pthread_create()` is `clone()` with "share everything" flags.

---

## Real World: Why This Matters

### Redis BGSAVE (fork for snapshots):
```
Redis (PID 100, 10GB RAM):
│
├── Client: BGSAVE
│
├── fork() ──► Child (PID 101)
│              │
│              ├── COW: shares all 10GB with parent (no copy yet!)
│              ├── Iterates over data, writes to .rdb file
│              │   (any page parent modifies → COW copies just that page)
│              ├── Done writing snapshot
│              └── exit()
│
├── Parent continues serving clients
│   (only pages that change get copied: maybe 200MB instead of 10GB)
│
└── wait() → reaps child
```

### PostgreSQL (fork per connection):
```
PostgreSQL master (PID 200):
│
├── Client connects
├── fork() ──► Child (PID 201) — handles this client
│
├── Another client connects  
├── fork() ──► Child (PID 202) — handles this client
│
├── Another client connects
├── fork() ──► Child (PID 203) — handles this client
│
└── Master keeps listening for new connections
```

### Why NGINX uses fork():
```
NGINX master (PID 300):
│
├── fork() ──► Worker 1 (PID 301) — handles requests (event loop)
├── fork() ──► Worker 2 (PID 302) — handles requests (event loop)
├── fork() ──► Worker 3 (PID 303) — handles requests (event loop)
├── fork() ──► Worker 4 (PID 304) — handles requests (event loop)
│
└── Master: manages workers (restart if crash, config reload)
```

