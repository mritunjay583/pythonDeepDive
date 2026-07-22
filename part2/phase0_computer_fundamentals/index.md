# Phase 0 — How Computers Actually Work

## Why This Phase?
You can't understand OS, databases, or distributed systems without knowing what the CPU actually does when it runs your code.

## Roadmap

| # | Topic | What You'll Learn |
|---|-------|-------------------|
| 1 | Binary & Number Systems | How data is stored at the lowest level |
| 2 | Machine Instructions | What code becomes after compilation |
| 3 | CPU Architecture | Registers, ALU, Fetch-Decode-Execute cycle, Pipelining, Clock |
| 4 | Memory Hierarchy | Registers → L1 → L2 → L3 → RAM → Disk, Cache, Locality |
| 5 | How a Program Runs | From source code to process to threads to CPU execution |

## Project: Tiny CPU Simulator
Build a simple CPU that:
- Has registers (4-8)
- Fetches instructions from memory
- Decodes opcodes
- Executes arithmetic + load/store + jump
- Demonstrates the fetch-decode-execute cycle

Language: Python

## Interview Questions Covered
- What happens when you run `./program`?
- Why is cache important for performance?
- Why is sequential disk access faster than random?
- What's the difference between stack and heap at hardware level?
- How does CPU branch prediction work?

## Key Comparisons
- JVM JIT compiler vs CPU instruction pipeline
- Python bytecode vs machine code
- Redis single-threaded model — why CPU cache matters here
