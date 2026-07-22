# Phase 1, Chapter 1 — From Program to Process (Combined: Program vs Process + PCB)

## Why One Chapter?

"Program" and "Process" are two sides of the same coin. You can't understand one without the other. And the Process Control Block (PCB) is just how Linux *remembers* a process. So we'll cover it all here — with a real Python program you can trace yourself.

---

## The Core Confusion (Let's Kill It)

Here's what confuses people:

```
"I wrote a Python script. I ran it. Is my script the process? Is Python the process?
 What exactly IS the process?"
```

**Answer in one line:**

> A **program** is a file on disk. A **process** is what the OS creates when you run that file. The program is the recipe. The process is the act of cooking.

You can have one program and 10 processes (run the same script 10 times). Each process is independent — its own memory, its own PID, its own state.

---

## The Real Python Program We'll Trace

Save this as `server.py`:

```python
# server.py — A simple TCP echo server
import socket
import os
import time

def main():
    print(f"Program starting...")
    print(f"My PID: {os.getpid()}")
    print(f"My Parent PID: {os.getppid()}")
    
    # Create a socket (this opens a file descriptor)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('127.0.0.1', 9999))
    sock.listen(5)
    
    print(f"Listening on port 9999...")
    print(f"Open file descriptors: {os.listdir('/proc/' + str(os.getpid()) + '/fd')}")
    
    # Allocate some memory (heap)
    data = [0] * 1_000_000  # ~8MB on heap
    print(f"Allocated 1M integers on heap")
    
    # Just wait (so we can inspect the process)
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
```

This program does real things:
- Opens a network socket (file descriptor)
- Allocates heap memory
- Stays alive so we can poke at it with Linux tools

---

## Step 1: Before You Run — It's Just a File

```bash
$ ls -la server.py
-rw-r--r-- 1 user user 612 Jan 15 10:00 server.py

$ file server.py
server.py: Python script, ASCII text executable
```

Right now `server.py` is just bytes on disk. It's not running. It's not a process. It's a **program** — a set of instructions stored in a file.

```
DISK:
┌─────────────────────────────────────┐
│  /home/user/server.py               │
│                                     │
│  Just text. Just bytes.             │
│  No PID. No memory. No state.      │
│  DEAD. INERT. A FILE.              │
└─────────────────────────────────────┘
```

**Key point:** A program has no life. It can't do anything. It just exists on disk like any other file (a photo, a PDF, whatever).

---

## Step 2: You Run It — The OS Creates a Process

```bash
$ python3 server.py &
[1] 12345
Program starting...
My PID: 12345
My Parent PID: 11000
Listening on port 9999...
```

**What just happened under the hood:**

```
YOU TYPE: python3 server.py

SHELL (bash, PID 11000):
  1. fork()          → Creates a CHILD process (copy of bash)
  2. Child process:
     exec("python3") → Replaces child's memory with Python interpreter
  3. Python interpreter:
     - Reads server.py from disk
     - Compiles to bytecode
     - Executes bytecode

KERNEL:
  - Allocates a new PID (12345)
  - Creates a task_struct (THE process control block)
  - Sets up virtual memory (page tables)
  - Opens stdin(0), stdout(1), stderr(2) file descriptors
  - Creates main thread
  - Puts thread on scheduler run queue
```

Now there's a PROCESS. It has:
- A PID (12345)
- Memory (virtual address space)
- Open files (stdin, stdout, stderr + the socket)
- A state (running/sleeping/etc.)
- A parent (bash, PID 11000)

---

## Step 3: Program vs Process — The Definitive Comparison

```
┌─────────────────────────────────────────────────────────────────┐
│                    PROGRAM vs PROCESS                             │
├─────────────────────────┬───────────────────────────────────────┤
│       PROGRAM           │           PROCESS                      │
├─────────────────────────┼───────────────────────────────────────┤
│ File on disk            │ Running instance in memory             │
│ Static (doesn't change) │ Dynamic (state changes every moment)  │
│ No PID                  │ Has a unique PID                       │
│ No memory allocated     │ Has virtual address space              │
│ No open files           │ Has file descriptor table              │
│ One copy                │ Can have many instances                │
│ Exists until deleted    │ Exists until terminated                │
│ Passive entity          │ Active entity                          │
│ Is the recipe           │ Is the cooking                         │
│ Is the blueprint        │ Is the building                        │
├─────────────────────────┴───────────────────────────────────────┤
│                                                                   │
│  ANALOGY:                                                        │
│  Program = Sheet music on paper                                  │
│  Process = Orchestra performing that music                       │
│                                                                   │
│  Same sheet music → different performances (different processes) │
│  Each performance has its own: tempo, volume, position in score  │
│  (= state, memory, program counter)                              │
└─────────────────────────────────────────────────────────────────┘
```

### Multiple Processes from One Program

```bash
# Run the SAME program 3 times
$ python3 server.py &    # Process A (PID 12345)
$ python3 server.py &    # Process B (PID 12346)  — DIFFERENT port needed!
$ python3 server.py &    # Process C (PID 12347)

# ONE program file, THREE processes
# Each has its own PID, memory, file descriptors
# They are COMPLETELY INDEPENDENT
```

```
DISK:                         RAM:
┌──────────┐                 ┌──────────────┐
│server.py │──── run ───────►│ Process 12345│ (own memory, own state)
│          │──── run ───────►│ Process 12346│ (own memory, own state)  
│(one file)│──── run ───────►│ Process 12347│ (own memory, own state)
└──────────┘                 └──────────────┘
```

---

## Step 4: SEE IT LIVE — Linux /proc Filesystem

This is where it gets real. Linux exposes every process's internals through `/proc`. Let's inspect our running `server.py`:

```bash
# Our process has PID 12345
$ ls /proc/12345/
attr       cmdline   exe      limits    mountinfo  oom_score  sched    status
cgroup     comm      fd       loginuid  mounts     pagemap    schedstat syscall
clear_refs coredump  fdinfo   map_files  net       personality smaps    task
cmd        environ   io       maps      ns         projid_map stack    wchan
```

**Every process gets this entire directory.** Let's explore the important ones:

