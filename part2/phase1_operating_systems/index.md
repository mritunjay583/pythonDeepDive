# Phase 1 — Operating Systems

## Why This Phase?
Every server, database, and distributed system runs on an OS. Understanding process management, memory, and I/O multiplexing is non-negotiable for systems work.

## Roadmap

| # | Topic | What You'll Learn |
|---|-------|-------------------|
| 1 | Program vs Process + PCB | What a process IS, how it's born (fork/exec), how Linux tracks it (task_struct), hands-on /proc inspection |
| 2 | Threads Deep Dive | Why threads exist, shared memory, race conditions, GIL, OS threads vs green threads vs event loops |
| 3 | (merged into 2) | — |
| 4 | Scheduling | Round-robin, priority, CFS |
| 5 | Context Switching | The cost of switching between processes/threads |
| 6 | System Calls | User mode vs kernel mode boundary |
| 7 | Memory Management | Paging, virtual memory, TLB |
| 8 | Stack vs Heap | How programs use memory |
| 9 | Synchronization | Mutex, Semaphore, Condition Variables |
| 10 | Deadlocks | Detection, prevention, avoidance |
| 11 | File Systems | Inodes, file descriptors, VFS |
| 12 | I/O Multiplexing | select, poll, epoll, kqueue |
| 13 | Event Loop | How Node.js/Redis handle concurrency |

## Projects

### Project 1: Mini Scheduler
Simulate process scheduling with multiple algorithms (FCFS, Round Robin, Priority).

### Project 2: Thread Pool
Build a thread pool in Python/Java that accepts tasks and manages worker threads.

### Project 3: Event Loop
Build a single-threaded event loop with I/O multiplexing (like Redis/Node.js).

### Project 4: Tiny Memory Allocator
Implement malloc/free with a free list.

## Interview Questions Covered
- Process vs Thread — when to use which?
- What happens during a context switch?
- How does virtual memory work?
- What is a page fault?
- Why does Redis use a single-threaded event loop?
- How does epoll differ from select?
- Explain deadlock conditions and how to prevent them.
- What is the thundering herd problem?

## Key Comparisons
- Java threads vs OS threads vs Green threads (Go goroutines)
- Python GIL vs true parallelism
- Redis event loop vs PostgreSQL process-per-connection
- Kafka I/O model vs Redis I/O model
