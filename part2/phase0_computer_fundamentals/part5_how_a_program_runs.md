# Phase 0, Lesson 5 — How a Program Actually Runs

## The Big Question

You write a Python/Java/C file, hit "run" — what actually happens? How does text on disk become something executing on a CPU?

```
source code (disk) → ??? → instructions running on CPU
```

This lesson traces the **entire journey**.

---

## Step 1: Program Lives on Disk (Just a File)

Before you run it, your program is just a file on disk — bytes like any other file.

```
DISK:
┌─────────────────────────────────┐
│  /home/user/program.exe          │
│  (or program.py, App.class)      │
│                                  │
│  Contains:                       │
│  • Machine code (instructions)   │
│  • Initial data (constants)      │
│  • Metadata (entry point, etc.)  │
└─────────────────────────────────┘
```

For compiled languages (C, Go, Rust): the file contains machine code.
For interpreted (Python): the file contains source text + bytecode is generated at runtime.
For JVM (Java): the file contains bytecode (.class), JVM interprets/JIT-compiles it.

---

## Step 2: You Type `./program` — OS Creates a Process

When you run a program, the **Operating System (OS)** does this:

```
1. OS reads the executable file from disk into RAM
2. OS creates a PROCESS — a container for running the program
3. OS sets up the process's memory layout
4. OS creates the MAIN THREAD
5. OS puts the thread on the scheduler queue
6. Scheduler eventually gives the thread a CPU core
7. CPU starts executing at the program's entry point
```

---

## Step 3: What is a Process?

A **process** is NOT what runs on the CPU. A process is a **container** — it holds:

```
┌─────────────────────────────────────────────────┐
│                 PROCESS                           │
│                                                  │
│  • PID (Process ID)                              │
│  • Memory space (virtual address space)          │
│  • File descriptors (open files, sockets)        │
│  • Security context (user, permissions)          │
│  • One or more THREADS                           │
│                                                  │
│  The process is the container.                   │
│  THREADS are what actually execute on the CPU.   │
└─────────────────────────────────────────────────┘
```

**Key insight:** The process owns resources (memory, files). The thread uses those resources and runs on the CPU. A process always has at least one thread (the main thread).

---

## Step 4: What is a Thread?

A **thread** is the actual unit of execution. It's what gets scheduled on a CPU core.

```
┌─────────────────────────────────────────────────┐
│                 THREAD                            │
│                                                  │
│  • Thread ID                                     │
│  • Program Counter (PC) — next instruction       │
│  • Registers (R0-R15, RSP, RBP, etc.)           │
│  • Stack (private to this thread)                │
│  • State (running, ready, blocked)               │
│                                                  │
│  This is what the CPU actually runs.             │
└─────────────────────────────────────────────────┘
```

**Process vs Thread:**

| | Process | Thread |
|---|---|---|
| What it is | Resource container | Execution unit |
| Has its own memory space? | Yes (isolated) | No (shares process memory) |
| Has its own stack? | N/A | Yes (each thread has its own stack) |
| Has its own registers? | N/A | Yes (when running on CPU) |
| Runs on CPU? | No | Yes |
| Can have multiple? | Multiple processes | Multiple threads per process |

```
┌──────────── Process ────────────────┐
│                                      │
│   Shared: Heap, Code, Data, Files    │
│                                      │
│   ┌─────────┐  ┌─────────┐         │
│   │ Thread 1│  │ Thread 2│          │
│   │ (main)  │  │         │          │
│   │ Stack   │  │ Stack   │          │
│   │ PC      │  │ PC      │          │
│   │ Regs    │  │ Regs    │          │
│   └─────────┘  └─────────┘         │
│                                      │
└──────────────────────────────────────┘
```

---

## Step 5: Memory Layout of a Process

When the OS creates a process, it sets up this memory layout in RAM:

```
HIGH ADDRESS (e.g., 0xFFFF...)
┌─────────────────────────────────┐
│           STACK                  │  ← grows DOWNWARD
│   • Local variables              │
│   • Function arguments           │
│   • Return addresses             │
│   • One stack PER THREAD         │
├─────────────────────────────────┤
│           ↓ grows down           │
│                                  │
│           ↑ grows up             │
├─────────────────────────────────┤
│           HEAP                   │  ← grows UPWARD
│   • Dynamic allocations          │
│   • malloc/new/object creation   │
│   • Shared between threads       │
├─────────────────────────────────┤
│           BSS                    │
│   • Uninitialized globals        │
│   • (zeroed out by OS)           │
├─────────────────────────────────┤
│           DATA                   │
│   • Initialized globals          │
│   • Static variables             │
│   • String constants             │
├─────────────────────────────────┤
│           CODE (TEXT)            │  ← your instructions live here
│   • Machine instructions         │
│   • Read-only                    │
│   • Shared if multiple instances │
├─────────────────────────────────┤
LOW ADDRESS (e.g., 0x0000...)
```

### What Lives Where:

| Segment | What's There | Example |
|---------|-------------|---------|
| **Code (Text)** | Your compiled instructions | The ADD, MOV, CALL instructions |
| **Data** | Initialized global/static variables | `static int count = 10;` |
| **BSS** | Uninitialized globals (zeroed) | `static int buffer[1000];` |
| **Heap** | Dynamically allocated objects | `new Object()`, `malloc(100)`, Python objects |
| **Stack** | Local variables, function call frames | `int x = 5;` inside a function |

### Stack vs Heap — The Key Difference

| | Stack | Heap |
|---|---|---|
| **Allocation** | Automatic (enter function = push, return = pop) | Manual (malloc/new, freed by GC or free) |
| **Speed** | Very fast (just move stack pointer) | Slower (find free block, fragmentation) |
| **Size** | Small (1-8 MB typical per thread) | Large (limited by RAM) |
| **Lifetime** | Dies when function returns | Lives until explicitly freed or GC'd |
| **Thread safety** | Private per thread (no sharing) | Shared between threads (needs synchronization) |
| **Growth** | Downward (toward lower addresses) | Upward (toward higher addresses) |

---

## Step 6: The CPU Runs a Thread

The OS scheduler picks a thread, loads its state into the CPU, and the CPU runs:

```
┌─────────────────────────────────────────────────────┐
│  OS Scheduler says: "Thread 1, your turn on Core 0" │
└──────────────────────────┬──────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────┐
│  CPU Core 0:                                         │
│                                                      │
│  Load thread's saved state:                          │
│    • PC = 0x1000 (where to start/resume)            │
│    • RSP = 0x7FFF0000 (top of thread's stack)       │
│    • R0-R15 = (thread's register values)            │
│                                                      │
│  Now: Fetch-Decode-Execute cycle runs               │
│       using this thread's PC and registers          │
└─────────────────────────────────────────────────────┘
```

**The CPU doesn't know about "processes" or "threads."** It just has a PC and registers. The OS is responsible for loading the right PC and registers before letting the CPU run.

---

## Step 7: The Full Journey (From Source to Execution)

Let's trace a C program:

```c
// program.c
#include <stdio.h>

int global_count = 42;        // → DATA segment

int add(int a, int b) {       // → CODE segment
    int result = a + b;       // → STACK (local variable)
    return result;
}

int main() {
    int x = 10;               // → STACK
    int y = 20;               // → STACK
    int *p = malloc(100);     // → HEAP (the 100 bytes)
                              //   p itself is on STACK
    int sum = add(x, y);     
    printf("%d\n", sum);      
    free(p);
    return 0;
}
```

### Journey:

```
1. DISK → RAM (OS loads program)
   ┌──────────┐     OS: "load program.exe"     ┌──────────────────┐
   │   DISK   │  ─────────────────────────────► │      RAM         │
   │program.exe│                                 │ Code: instructions│
   └──────────┘                                  │ Data: global_count│
                                                 │ Stack: (empty)    │
                                                 │ Heap: (empty)     │
                                                 └──────────────────┘

2. OS creates process + main thread
   Process gets: PID, memory space, file descriptors
   Main thread gets: PC = main's address, RSP = top of stack

3. Scheduler assigns thread to CPU Core

4. CPU starts executing at main():
   
   int x = 10;     → SUB RSP, 8 (make room on stack)
                    → MOV [RSP], 10 (store 10 on stack)
                    
   int y = 20;     → MOV [RSP+4], 20 (store 20 on stack)
   
   malloc(100);    → CALL malloc → OS finds 100 bytes on heap
                    → Returns address → stored in register/stack
   
   add(x, y);      → Push args, CALL add
                    → Inside add: result computed in register
                    → RET back to main
   
   printf(...)     → System call → kernel → writes to terminal
   
   return 0;       → Stack frame popped, thread ends
```

---

## Step 8: Real Example — Writing Text to a File

Let's trace what happens when your program writes to a file:

```python
# Python
f = open("output.txt", "w")
f.write("Hello, World!")
f.close()
```

This translates to (simplified):

```c
// What actually happens under the hood
int fd = open("output.txt", O_WRONLY | O_CREAT);  // system call
write(fd, "Hello, World!", 13);                    // system call
close(fd);                                         // system call
```

### The Full Flow:

```
YOUR PROGRAM (user space)          │  OS KERNEL                │  HARDWARE
                                   │                           │
1. f = open("output.txt", "w")     │                           │
   │                               │                           │
   ├── SYSCALL (trap to kernel) ──►│ 2. Kernel:                │
   │   Mode switch:                │    • Find/create file     │
   │   User mode → Kernel mode     │    • Allocate file        │
   │                               │      descriptor (fd=3)    │
   │                               │    • Return fd to program │
   │◄── Return fd=3 ──────────────│                           │
   │                               │                           │
3. f.write("Hello, World!")        │                           │
   │                               │                           │
   ├── SYSCALL write(fd=3, buf) ──►│ 4. Kernel:                │
   │                               │    • Copy data from       │
   │                               │      user buffer to       │
   │                               │      kernel page cache    │
   │                               │    • Mark pages dirty     │
   │                               │    • Return "success"     │
   │◄── Return 13 (bytes written)──│                           │
   │                               │                           │
   │                               │ 5. LATER (async):         │
   │                               │    Kernel flushes dirty ──►│ 6. Disk write
   │                               │    pages to disk           │    (actual I/O)
   │                               │                           │
7. f.close()                       │                           │
   │                               │                           │
   ├── SYSCALL close(fd=3) ───────►│ 8. Kernel:                │
   │                               │    • Flush remaining      │
   │                               │      data to disk         │──► 9. Final disk write
   │                               │    • Release fd           │
   │◄── Return success ───────────│                           │
```

### Key Insights from This Example:

1. **Your program doesn't talk to disk directly.** It asks the kernel (via system calls).

2. **Mode switch happens:** User mode → Kernel mode → User mode. This is expensive (~1-5 μs).

3. **write() doesn't write to disk immediately.** It copies data to the kernel's **page cache** (RAM). The kernel flushes to disk later (asynchronously).

4. **This is why:**
   - Redis `fsync` is expensive (forces kernel to flush page cache to disk NOW)
   - PostgreSQL WAL uses `fsync` for durability (must guarantee data is on disk)
   - Kafka gets speed by relying on page cache (OS manages the flush)

5. **File descriptor (fd)** is just an integer — a handle to an open file. The kernel maintains a table mapping fd → actual file/socket/pipe.

---

## Step 9: Putting It ALL Together

```
┌─────────────────────────────────────────────────────────────────┐
│                        FULL PICTURE                               │
│                                                                   │
│  DISK                                                            │
│  ├── program.exe (your compiled code)                            │
│  └── output.txt (data files)                                     │
│       │                                                          │
│       │ OS loads program into RAM                                │
│       ▼                                                          │
│  RAM                                                             │
│  ├── CODE segment (instructions)                                 │
│  ├── DATA segment (global/static vars)                           │
│  ├── HEAP (dynamic allocations, shared between threads)          │
│  ├── STACK per thread (local vars, call frames)                  │
│  └── Page Cache (kernel's disk cache)                            │
│       │                                                          │
│       │ CPU fetches instructions + data into cache               │
│       ▼                                                          │
│  CPU                                                             │
│  ├── L1i Cache (instructions)                                    │
│  ├── L1d Cache (data)                                            │
│  ├── Registers (active computation)                              │
│  └── Runs the thread's fetch-decode-execute cycle                │
│                                                                   │
│  FLOW:                                                           │
│  Disk → RAM (OS loads once)                                      │
│  RAM → Cache → Registers (CPU fetches on-demand, per cache line) │
│  Registers → Cache → RAM (stores write back lazily)              │
│  RAM (page cache) → Disk (kernel flushes when ready)             │
└─────────────────────────────────────────────────────────────────┘
```

---

## The Critical Mental Model

```
PROCESS = container (owns memory + files + threads)
THREAD  = what actually runs on CPU (has PC + registers + stack)
CPU     = just runs fetch-decode-execute (doesn't know about processes)
OS      = manages everything: loads programs, creates processes, 
          schedules threads, handles I/O, provides isolation
```

**What RUNS:**
- Thread runs on CPU core
- CPU just follows the PC (program counter)

**What OWNS:**
- Process owns memory space, file descriptors, threads
- Thread owns its stack, PC, and register values

**What MOVES:**
- Instructions: Disk → RAM → L1i Cache → Fetch Unit
- Data: Disk → RAM → L1d Cache → Registers (and back)
- File writes: Registers → RAM (page cache) → Disk (async)

---

## Interview Questions & Answers

### Q1: What happens when you run `./program` on Linux?

**Answer:**
1. Shell calls `fork()` → creates child process
2. Child calls `exec("./program")` → replaces its memory with new program
3. OS loader reads ELF headers, maps code/data sections into RAM (mmap)
4. OS sets up stack, initializes registers (PC = entry point)
5. Creates main thread, puts it on scheduler run queue
6. Scheduler assigns it to a CPU core
7. CPU begins fetch-decode-execute at the entry point

Note: The entire file isn't loaded immediately. Pages are loaded **on-demand** (page faults). First access to a code page → OS loads that page from disk.

---

### Q2: What is the difference between a process and a thread?

**Answer:**
- **Process** = resource container. Owns virtual address space, file descriptors, PIDs. Provides isolation between programs.
- **Thread** = execution unit. Has its own PC, registers, and stack. Shares the process's memory (heap, code, data) with other threads.

Multiple threads in one process share memory (fast communication, but need synchronization). Multiple processes have separate memory (safe isolation, but expensive IPC).

Real-world: Redis = single-threaded process. PostgreSQL = multi-process (one per connection). Java server = multi-threaded single process.

---

### Q3: What is a system call and why is it expensive?

**Answer:**
A system call is how user programs request OS services (file I/O, networking, memory allocation). It requires a **mode switch** from user mode to kernel mode:

1. Save user registers
2. Switch to kernel stack
3. Validate arguments
4. Execute kernel code
5. Switch back to user stack
6. Restore user registers

Cost: ~1-5 μs (thousands of CPU cycles). This is why:
- Redis batches commands (fewer syscalls per operation)
- Kafka uses `sendfile()` (zero-copy, fewer user↔kernel transitions)
- High-performance systems use `io_uring` (batch syscalls, reduce transitions)

---

### Q4: Explain the memory layout of a process (stack, heap, code, data).

**Answer:**
From low to high address:
- **Code (Text):** Read-only machine instructions. Shared between instances.
- **Data:** Initialized global/static variables.
- **BSS:** Uninitialized globals (zeroed by OS).
- **Heap:** Dynamic allocations (malloc/new). Grows upward. Shared between threads.
- **Stack:** Local variables, function call frames. Grows downward. One per thread. Small (1-8 MB).

Key difference: Stack is LIFO, automatic (function enter/exit). Heap is manual/GC-managed, arbitrary lifetime. Stack is thread-private, heap is shared.

---

### Q5: When you call `write()` to a file, does data go to disk immediately?

**Answer:**
No. The write path is:
1. `write()` syscall copies data from user buffer → kernel **page cache** (RAM)
2. Kernel marks page as dirty
3. Returns immediately to user (fast!)
4. **Later**, a background kernel thread (pdflush/writeback) flushes dirty pages to disk

Data is in RAM, not disk, after write() returns. If power fails before flush → data lost.

To guarantee durability:
- `fsync(fd)` → forces flush to disk NOW (expensive, ~1-10 ms)
- PostgreSQL uses fsync after WAL writes (guarantees durability)
- Redis `appendfsync always` calls fsync per command (slow but safe)
- Kafka relies on replication for durability instead of fsync per message

---

### Q6: Why is Redis single-threaded but still fast?

**Answer:**
- All data in RAM → no disk I/O wait (100 ns vs 100 μs per access)
- Single-threaded → no lock contention, no context switches, no cache line bouncing
- Event loop with epoll → handles 10K+ connections without thread-per-connection overhead
- Simple operations → each command is microseconds of CPU work
- Cache-friendly data structures → minimal cache misses

The bottleneck for Redis is **network I/O**, not CPU. One core can process 100K+ ops/sec because each op is just a hash table lookup in RAM.

---

### Q7: What is virtual memory and why does it exist?

**Answer:**
Virtual memory gives each process the illusion of having its own large, contiguous memory space (e.g., 0 to 2^48). The CPU's **MMU (Memory Management Unit)** + **page tables** translate virtual addresses to physical RAM addresses.

Why it exists:
1. **Isolation:** Process A can't access Process B's memory (different page tables)
2. **Simplicity:** Every process thinks it starts at address 0 (no coordination needed)
3. **Overcommit:** Can allocate more virtual memory than physical RAM (pages loaded on-demand)
4. **Sharing:** Code pages can be shared between processes (same physical page, multiple virtual mappings)

Cost: TLB (Translation Lookaside Buffer) caches recent translations. TLB miss = walk page table = ~10-100 ns extra latency.

---

## What's Next

You now understand the complete journey of a program: from file on disk → process → thread → CPU execution, and how data moves between all levels.

**Phase 0 is complete.** You have the foundation:
- How the CPU executes instructions (Part 2-3)
- Memory hierarchy and why it matters (Part 4)
- How programs run, processes, threads, memory layout (Part 5)

**Next: Phase 1 — Operating Systems** where we go deep into:
- Process/thread management
- Scheduling
- Synchronization (mutexes, deadlocks)
- I/O multiplexing (epoll — how Redis works)

→ [Phase 1: Operating Systems](../phase1_operating_systems/index.md)
