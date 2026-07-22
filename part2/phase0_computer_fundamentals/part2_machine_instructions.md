# Phase 0, Lesson 2 — Machine Instructions

## The Problem

You write this:
```python
x = 10 + 20
```

But the CPU has no idea what `x`, `+`, or `=` means. It only understands numbers — binary patterns called **instructions**.

So the question is: **How does human-readable code become something a CPU can execute?**

---

## What Is a Machine Instruction?

A machine instruction is a binary-encoded command that tells the CPU to do **one small thing**:
- Add two numbers
- Load a value from memory
- Store a value to memory
- Jump to a different instruction

That's it. Every program ever written — Redis, Linux, PostgreSQL — is just millions of these tiny operations.

---

## Anatomy of an Instruction

Every instruction has two parts:

```
┌──────────┬──────────────┐
│  OPCODE  │  OPERANDS    │
└──────────┴──────────────┘
```

- **Opcode** — WHAT to do (add, subtract, load, store, jump)
- **Operands** — WHAT to do it WITH (registers, memory addresses, constants)

### Example (Simplified):
```
ADD R1, R2, R3    →  "Add value in R2 and R3, store in R1"
│    │   │   │
│    └───┴───┘
│    operands
└── opcode
```

In binary this might look like:
```
0001 001 010 011
│    │   │   │
│    R1  R2  R3
└── ADD opcode
```

---

## Instruction Types

Every CPU supports these categories:

| Category | Examples | What It Does |
|----------|----------|--------------|
| Arithmetic | ADD, SUB, MUL, DIV | Math on registers |
| Logic | AND, OR, XOR, NOT | Bitwise operations |
| Data Transfer | LOAD, STORE, MOV | Move data between register ↔ memory |
| Control Flow | JMP, JZ, JNZ, CALL, RET | Change which instruction executes next |
| Comparison | CMP | Compare two values, set flags |

---

## How Your Code Becomes Instructions

```
Source Code (Python/Java/C)
        │
        ▼
   Compiler / Interpreter
        │
        ▼
  Assembly Language (human-readable instructions)
        │
        ▼
  Assembler
        │
        ▼
  Machine Code (binary — what CPU actually runs)
```

### Real Example — C to Assembly to Machine Code:

**C Code:**
```c
int result = a + b;
```

**Assembly (x86):**
```asm
MOV  EAX, [a]     ; Load 'a' from memory into register EAX
ADD  EAX, [b]     ; Add 'b' from memory to EAX
MOV  [result], EAX ; Store result back to memory
```

**Machine Code (hex):**
```
8B 05 00 00 00 00    ; MOV EAX, [a]
03 05 04 00 00 00    ; ADD EAX, [b]
89 05 08 00 00 00    ; MOV [result], EAX
```

**Key insight:** 3 lines of assembly = 3 instructions = what the CPU actually executes one by one.

---

## Instruction Set Architecture (ISA)

The **ISA** is the contract between hardware and software. It defines:
- What instructions exist
- What registers are available
- How memory is addressed
- How instructions are encoded

### Two Major ISA Families:

| | x86 (CISC) | ARM (RISC) |
|---|---|---|
| Philosophy | Complex instructions, fewer needed | Simple instructions, more needed |
| Instruction length | Variable (1-15 bytes) | Fixed (4 bytes) |
| Used in | Desktops, servers (Intel, AMD) | Phones, Apple M-series, AWS Graviton |
| Example | One instruction can load + add + store | Separate instructions for each |
| Trade-off | Complex decoder, but less code | Simple decoder, faster pipeline |

**Why this matters for you:**
- AWS Graviton (ARM) is cheaper than x86 instances
- Apple M-series is ARM
- Understanding RISC helps you understand why simple = fast at hardware level

---

## Registers — The Fastest Storage

Registers are tiny storage **inside the CPU**. Accessing a register takes ~0.5 nanoseconds (vs ~100ns for RAM).

### Common x86-64 Registers:

```
┌─────────────────────────────────┐
│ General Purpose                  │
│   RAX, RBX, RCX, RDX           │  ← for math, data
│   RSI, RDI                      │  ← source/destination
│   R8-R15                        │  ← extra (64-bit mode)
├─────────────────────────────────┤
│ Special Purpose                  │
│   RSP — Stack Pointer           │  ← top of stack
│   RBP — Base Pointer            │  ← stack frame base
│   RIP — Instruction Pointer     │  ← NEXT instruction to execute
│   RFLAGS — Status Flags         │  ← zero, carry, overflow
└─────────────────────────────────┘
```

**Critical registers to understand:**
- **RIP (Instruction Pointer)** — points to the NEXT instruction. This is how the CPU knows what to do next.
- **RSP (Stack Pointer)** — points to the top of the call stack.
- **RFLAGS** — result of comparisons (used by conditional jumps).

---

## How Control Flow Works at Instruction Level

### If-else becomes conditional jumps:

**Python:**
```python
if x > 5:
    y = 1
else:
    y = 0
```

**Assembly (conceptual):**
```asm
    CMP  R1, 5        ; Compare x with 5
    JLE  else_branch   ; Jump to else if x <= 5
    MOV  R2, 1        ; y = 1
    JMP  end           ; Skip else
else_branch:
    MOV  R2, 0        ; y = 0
end:
```

**Key insight:** There's no `if/else` in hardware. It's just `CMP` + `JMP`.

### Loops become backward jumps:

**Python:**
```python
for i in range(10):
    total += i
```

**Assembly (conceptual):**
```asm
    MOV  R1, 0        ; i = 0
    MOV  R2, 0        ; total = 0
loop:
    ADD  R2, R1       ; total += i
    ADD  R1, 1        ; i++
    CMP  R1, 10       ; is i < 10?
    JLT  loop         ; if yes, jump back
```

**Key insight:** A loop is just a conditional jump backwards.

### Function calls become CALL/RET:

```asm
CALL function_addr    ; Push return address to stack, jump to function
...
RET                   ; Pop return address from stack, jump back
```

---

## The Compilation Pipeline in Detail

```
┌──────────────────────────────────────────────────────────┐
│  Source: x = a + b * c                                    │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  Lexer/Tokenizer → tokens: [x, =, a, +, b, *, c]        │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  Parser → AST (Abstract Syntax Tree)                      │
│       =                                                   │
│      / \                                                  │
│     x   +                                                 │
│        / \                                                │
│       a   *                                               │
│          / \                                              │
│         b   c                                             │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│  Code Generator → Assembly/Bytecode                       │
│     LOAD R1, [b]                                          │
│     LOAD R2, [c]                                          │
│     MUL  R3, R1, R2     ; R3 = b * c                     │
│     LOAD R4, [a]                                          │
│     ADD  R5, R4, R3     ; R5 = a + (b * c)               │
│     STORE [x], R5                                         │
└──────────────────────────────────────────────────────────┘
```

---

## Python vs C vs Java — What Actually Runs?

| Language | What the CPU Runs | Indirection |
|----------|-------------------|-------------|
| C | Machine code directly | 0 (compiled to native) |
| Java | JVM interprets bytecode → JIT compiles hot paths to native | 1-2 layers |
| Python | CPython interprets bytecode → calls C functions | 2 layers |

**This is why:**
- C is fastest (CPU runs your code directly)
- Java is fast enough (JIT eliminates the interpreter for hot paths)
- Python is slow for CPU-bound work (always interpreted, always indirect)

**But Python's secret:** Redis commands, NumPy, PostgreSQL queries — the heavy lifting is in C. Python is just the glue.

---

## Real-World Relevance

| System | How Instructions Matter |
|--------|------------------------|
| Redis | Single-threaded, so every instruction counts. Cache-friendly data structures. |
| JVM | JIT compiler optimizes bytecode → native instructions at runtime |
| PostgreSQL | Query planner picks execution paths that minimize instructions |
| Linux kernel | Written in C, compiled to native, every syscall path is optimized |
| Kafka | JVM-based, relies on OS page cache + sequential I/O = fewer instructions |

---

## Conceptual Questions (Think Before Reading Answers)

1. **Why can't the CPU just execute Python directly?**

2. **What's the difference between JMP and CALL?**

3. **Why does x86 have variable-length instructions while ARM has fixed-length?**

4. **If registers are so fast, why don't we just have 10,000 registers instead of RAM?**

5. **How does the CPU know what the NEXT instruction is?**

---

## Answers

1. The CPU only understands its ISA (fixed set of binary-encoded operations). Python syntax is arbitrary human convention. Something must translate.

2. JMP just changes RIP (go somewhere). CALL pushes the return address onto the stack first, then jumps — so RET knows where to come back.

3. Trade-off: Variable-length = more compact code, complex decoder. Fixed-length = simpler/faster decoder, more memory used. ARM prioritizes speed of decode.

4. Registers are expensive (transistors, wiring, power). Each register needs to be accessible in one clock cycle, which requires physical proximity to ALU. More registers = larger chip = slower access. Diminishing returns.

5. The **Instruction Pointer (RIP)** register. It auto-increments after each instruction. JMP/CALL/RET modify it directly.

---

## Interview Questions & Answers

---

### Beginner

**Q1: What is the difference between an opcode and an operand?**

**Answer:**

An **opcode** (operation code) is the part of the instruction that tells the CPU *what to do* — add, subtract, load, jump, etc.

**Operands** tell the CPU *what to do it with* — which registers, memory addresses, or constant values to use.

```
ADD R1, R2, R3
│    │   │   │
│    └───┴───┘
│    operands (where to get/put data)
└── opcode (the operation)
```

Analogy: Opcode is the verb ("add"), operands are the nouns ("these two numbers, put result here").

In binary encoding, the opcode typically occupies the first few bits, and the remaining bits encode operands:
```
0001  001  010  011
│     │    │    │
ADD   R1   R2   R3
```

---

**Q2: What happens when a function is called at the assembly level?**

**Answer:**

When the CPU executes a `CALL` instruction, **two things happen**:

1. **Push the return address onto the stack** — the address of the instruction *after* the CALL (so the CPU knows where to come back)
2. **Jump to the function's address** — set RIP (instruction pointer) to the function's first instruction

When the function finishes and hits `RET`:
1. **Pop the return address from the stack**
2. **Jump back** — set RIP to that address

```
Before CALL:              After CALL:              After RET:
RIP → CALL foo           RIP → first instr of foo  RIP → instr after CALL
RSP → [...]              RSP → [return_addr, ...]  RSP → [...]

Stack during call:
┌─────────────────┐
│ return address   │ ← pushed by CALL
├─────────────────┤
│ saved RBP        │ ← pushed by function prologue
├─────────────────┤
│ local variables  │ ← function's stack frame
└─────────────────┘
```

The full sequence (function prologue/epilogue):
```asm
; Caller
CALL foo            ; push return addr, jump to foo

; Function prologue (inside foo)
PUSH RBP            ; save caller's base pointer
MOV  RBP, RSP      ; set new base pointer
SUB  RSP, 16       ; allocate space for local vars

; ... function body ...

; Function epilogue
MOV  RSP, RBP      ; deallocate locals
POP  RBP           ; restore caller's base pointer
RET                 ; pop return address, jump back
```

**Why this matters:** This is exactly how stack overflow happens — too many nested calls, stack runs out of space. It's also why recursion has overhead (each call = push/pop/jump).

---

**Q3: What is the program counter?**

**Answer:**

The **program counter** (PC), called **RIP** (Register Instruction Pointer) on x86-64, is a special register that holds the **memory address of the next instruction to execute**.

How it works:
1. CPU reads instruction at address in RIP
2. RIP auto-increments to point to the next instruction
3. Repeat

```
Memory:
0x1000: ADD R1, R2, R3    ← RIP points here (current)
0x1004: MOV R4, 5         ← RIP will point here next
0x1008: JMP 0x1000        ← this would set RIP back to 0x1000
```

**What modifies the program counter:**
- Normal execution: auto-increments (sequential)
- `JMP`: sets RIP to target address (unconditional)
- `JZ/JNZ`: conditionally sets RIP (if/else)
- `CALL`: pushes current RIP, sets RIP to function address
- `RET`: pops saved address into RIP

**Key insight:** The program counter is what makes a computer a computer. Without it, you can't have sequential execution or branching. It's the "cursor" scanning through your program.

---

### Intermediate

**Q4: Explain the difference between CISC and RISC architectures.**

**Answer:**

| | CISC (x86) | RISC (ARM) |
|---|---|---|
| **Philosophy** | Do more per instruction | Do less per instruction, but faster |
| **Instruction count** | Fewer instructions needed for a task | More instructions needed |
| **Instruction length** | Variable (1-15 bytes on x86) | Fixed (4 bytes on ARM) |
| **Instruction complexity** | One instruction can access memory + compute | Separate instructions for memory access and computation |
| **Decoder complexity** | Complex (must handle variable lengths) | Simple (fixed format, easy to pipeline) |
| **Registers** | Fewer (historically), specialized | Many general-purpose registers |
| **Examples** | Intel, AMD (x86-64) | ARM, RISC-V, MIPS |

**CISC example** (x86):
```asm
; One instruction: load from memory + add + store back
ADD [memory_addr], 5    ; mem[addr] = mem[addr] + 5
```

**RISC equivalent** (ARM):
```asm
LDR  R1, [memory_addr]  ; Load from memory to register
ADD  R1, R1, #5          ; Add 5
STR  R1, [memory_addr]  ; Store back to memory
```

**Why RISC is winning now:**
- Fixed-length instructions = easy to decode in parallel = better pipelining
- Simpler instructions = less power consumption (critical for mobile/cloud)
- AWS Graviton (ARM) is 20-40% cheaper than x86 instances
- Apple M-series (ARM) outperforms Intel at lower power

**Why x86 still exists:**
- Massive software ecosystem (Windows, legacy enterprise)
- Intel/AMD have thrown transistors at making CISC behave like RISC internally (micro-ops)

**The dirty secret:** Modern x86 CPUs internally decode CISC instructions into RISC-like micro-operations. So the hardware is RISC underneath, with a CISC compatibility layer.

---

**Q5: How does a JIT compiler improve performance over interpretation?**

**Answer:**

**Interpreter (CPython):**
```
Source → Bytecode → Interpreter reads each bytecode → calls C function → next bytecode
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                    This loop runs for EVERY operation, every time
```

Cost per operation: ~10-100 native instructions of overhead (decode bytecode, dispatch, type checks).

**JIT (JVM HotSpot, PyPy, V8):**
```
Source → Bytecode → Interpreter (initially)
                         │
                         │ (profiling: "this function ran 10,000 times")
                         ▼
                    JIT Compiler → Native machine code
                         │
                         ▼
                    CPU runs native directly (no interpreter overhead)
```

**Why JIT is faster:**
1. **Eliminates dispatch overhead** — no more "read bytecode, lookup handler, call handler" loop
2. **Type specialization** — if `x` is always an `int`, generate native integer ADD (skip type checks)
3. **Inlining** — paste small functions directly into callers (eliminate CALL/RET overhead)
4. **Register allocation** — keep variables in CPU registers instead of stack/heap
5. **Dead code elimination** — remove paths never taken based on profiling

**Why not compile everything upfront (like C)?**
- JIT has **runtime information**: it knows which branches are taken, what types variables actually hold
- C compiler guesses at compile time. JIT knows at runtime. This lets JIT generate *better* code than static compilation for some patterns.

**Trade-off:**
- JIT has warmup time (first run is slow while profiling/compiling)
- JIT uses runtime memory for compiled code
- Long-running servers benefit most (amortize warmup over millions of requests)

**Real example:** Java's HotSpot JVM compiles hot methods after ~10,000 invocations. This is why Java servers get faster after warming up.

---

**Q6: Why is branch prediction important?**

**Answer:**

**The problem:** Modern CPUs use **pipelining** — they start executing the next instruction before the current one finishes:

```
Time →   1    2    3    4    5    6
Inst 1: [F]  [D]  [E]  
Inst 2:      [F]  [D]  [E]
Inst 3:           [F]  [D]  [E]

F=Fetch, D=Decode, E=Execute
```

But when the CPU hits a **conditional branch** (if/else):
```asm
CMP R1, 5
JLE else_branch    ← which path? CPU doesn't know yet!
; ... true path ...
else_branch:
; ... false path ...
```

The CPU has already fetched the next few instructions (pipelining). But it doesn't know which path to take until the CMP finishes executing (3+ stages away).

**Without branch prediction:** CPU stalls, waits, wastes cycles.
```
CMP:   [F] [D] [E]
JLE:        [F] [D] [?? wait for CMP result ??]
next:                     [stall] [stall] [F] [D] [E]
                          ^^^^^^^^^^^^^^
                          wasted cycles (pipeline bubble)
```

**With branch prediction:** CPU **guesses** which way the branch goes and speculatively executes that path:
- If correct (95%+ of the time): no penalty, full speed
- If wrong: flush pipeline, restart from correct path (15-20 cycle penalty)

**How prediction works:**
- **Static:** backward jumps predicted taken (loops), forward predicted not taken
- **Dynamic:** CPU maintains a history table of past branch outcomes
- **Pattern matching:** CPU detects patterns like TTTTTTTTTF (loop that runs 9 times)

**Real-world impact:**

```python
# Branch-prediction-friendly (sorted data):
for x in sorted_array:
    if x > threshold:  # after some point, ALWAYS true → predictor learns
        process(x)

# Branch-prediction-hostile (random data):
for x in random_array:
    if x > threshold:  # 50/50 random → predictor keeps guessing wrong
        process(x)
```

This is why **sorting data before processing can speed up code**, even though sorting itself has a cost. Famous Stack Overflow question: "Why is processing a sorted array faster than an unsorted array?" — this is the answer.

**Relevance:**
- JVM JIT uses profiling to reorder branches (put likely path first)
- Linux kernel uses `likely()`/`unlikely()` macros to hint the compiler
- Redis's simple code paths = highly predictable branches = fast

---

### Senior / Systems

**Q7: How does instruction pipelining work and what causes pipeline stalls?**

**Answer:**

**Pipelining** is the CPU's assembly line. Instead of finishing one instruction before starting the next, the CPU overlaps them:

```
Without pipelining (4 cycles per instruction):
Inst 1: [F][D][E][W]
Inst 2:             [F][D][E][W]
Inst 3:                         [F][D][E][W]
→ 3 instructions take 12 cycles

With pipelining:
Inst 1: [F][D][E][W]
Inst 2:    [F][D][E][W]
Inst 3:       [F][D][E][W]
→ 3 instructions take 6 cycles (after pipeline is full: 1 instruction/cycle)

F=Fetch, D=Decode, E=Execute, W=Write-back
```

**Modern CPUs have 14-20+ pipeline stages** (not just 4). Deeper pipeline = higher clock speed possible, but higher penalty for stalls.

**What causes pipeline stalls (hazards):**

**1. Data Hazard** — instruction needs result that isn't ready yet:
```asm
ADD R1, R2, R3     ; R1 = R2 + R3 (result ready after Execute stage)
SUB R4, R1, R5     ; needs R1! But ADD hasn't written it yet
```
**Solution:** Forwarding/bypassing — route result directly from ALU output to next instruction's input without waiting for write-back.

**2. Control Hazard** — branch outcome unknown:
```asm
CMP R1, 0
JZ  label          ; which path? Pipeline already fetched next instructions
```
**Solution:** Branch prediction (guess) + speculative execution. Wrong guess = flush pipeline (15-20 cycle penalty on modern CPUs).

**3. Structural Hazard** — two instructions need the same hardware unit:
```
Both instructions need the ALU at the same time
```
**Solution:** Duplicate hardware (modern CPUs have multiple ALUs, load/store units).

**4. Memory Stall** — cache miss:
```asm
LOAD R1, [addr]    ; if not in L1/L2/L3 cache → wait 100+ cycles for RAM
ADD  R2, R1, R3    ; stuck waiting for R1
```
**Solution:** Out-of-order execution — CPU finds other independent instructions to execute while waiting.

**Real-world impact:**
- Intel/AMD CPUs execute instructions **out of order** to avoid stalls
- They can have 200+ instructions "in flight" at once
- This is why single-threaded performance is still improving even without higher clock speeds

---

**Q8: What is speculative execution and what are its security implications (Spectre/Meltdown)?**

**Answer:**

**Speculative execution:** When the CPU hits a branch it can't resolve yet, it **guesses** and starts executing the predicted path. If the guess is right, it commits the results. If wrong, it rolls back.

```
CMP R1, limit
JGE out_of_bounds       ← prediction: "not taken" (bounds check usually passes)
LOAD R2, [array + R1]   ← CPU speculatively executes this
... uses R2 ...          ← and this too (speculative)
```

If the branch was mispredicted, the CPU discards all speculative results. **Architecturally**, nothing happened.

**But microarchitecturally, something DID happen:**

The speculative LOAD brought data into the **CPU cache**. Even after rollback, that cache line remains. An attacker can **time** subsequent memory accesses to determine what was loaded into cache.

**Spectre (simplified):**
```
// Attacker's code (conceptual)
if (x < array_size) {          // CPU speculatively enters (even if x is out of bounds)
    y = array2[array1[x] * 256];  // speculatively reads secret, then accesses array2
}                                   // at an index derived from the secret

// After rollback: array2[secret * 256] is in cache
// Attacker times access to array2[0], array2[256], array2[512]...
// The fast one reveals the secret byte
```

**Meltdown:** Similar but exploits speculative reads of **kernel memory** from user space. CPU speculatively loads kernel data before the permission check completes.

**Mitigations and their cost:**
- **KPTI (Kernel Page Table Isolation):** Separate page tables for user/kernel. Prevents Meltdown. Cost: ~5-30% performance hit on syscall-heavy workloads.
- **Retpoline:** Replace indirect jumps with a construct that confuses the branch predictor. Prevents Spectre variant 2. Cost: ~5-10%.
- **Microcode patches:** CPU firmware updates that restrict speculation.

**Why this matters for systems engineers:**
- PostgreSQL/Redis on patched kernels run measurably slower
- Cloud providers (AWS, GCP) had to patch all host machines
- Demonstrates that performance optimizations can create security holes
- "No architectural side effects" was assumed safe — but microarchitecture leaks information

---

**Q9: How does the JVM's JIT compiler decide what to compile vs interpret?**

**Answer:**

The JVM uses **tiered compilation** (since Java 7+):

```
┌─────────────────────────────────────────────────────┐
│ Tier 0: Interpreter                                  │
│   - All code starts here                             │
│   - Collects basic profiling (invocation counts)     │
├─────────────────────────────────────────────────────┤
│ Tier 1-3: C1 Compiler (Client)                       │
│   - Quick compilation, modest optimizations          │
│   - Triggered at ~1,500 invocations                  │
│   - Inserts profiling counters for C2                │
├─────────────────────────────────────────────────────┤
│ Tier 4: C2 Compiler (Server)                         │
│   - Aggressive optimizations, slow compilation       │
│   - Triggered at ~10,000 invocations                 │
│   - Inlining, escape analysis, loop unrolling        │
│   - Uses profiling data from C1                      │
└─────────────────────────────────────────────────────┘
```

**What triggers compilation:**
1. **Method invocation counter** — method called N times
2. **Back-edge counter** — loop body executes N times (OSR: On-Stack Replacement — compile a loop mid-execution)

**What C2 optimizes based on profiling:**

1. **Type profiling** → monomorphic dispatch:
   ```java
   // If obj is ALWAYS a String at runtime:
   obj.toString()  // → direct call to String.toString() (skip vtable lookup)
   ```

2. **Branch profiling** → dead code elimination:
   ```java
   if (config.isDebug()) { ... }  // never true in production → eliminate entirely
   ```

3. **Escape analysis** → stack allocation:
   ```java
   Point p = new Point(x, y);  // if p doesn't escape method → allocate on stack (no GC)
   ```

4. **Inlining** → eliminate call overhead:
   ```java
   // Small methods called frequently get pasted inline
   int result = Math.max(a, b);  // becomes: int result = (a > b) ? a : b;
   ```

**Deoptimization:**
If assumptions are violated (e.g., a new class is loaded that changes type hierarchy), the JVM **deoptimizes**: throws away compiled code, falls back to interpreter, and recompiles with new information.

**Why this matters:**
- Java warmup time is real: first 10-30 seconds of a server's life are slow
- This is why benchmarking Java requires warmup iterations
- Kubernetes readiness probes should account for JVM warmup
- GraalVM native-image compiles ahead-of-time to eliminate warmup (trade-off: no runtime profiling)

---

**Q10: Why does Redis care about CPU cache even though it's "just" a key-value store?**

**Answer:**

Redis is **single-threaded** for command execution. It can't throw more cores at the problem. Every nanosecond per operation matters because it directly determines throughput (ops/second).

**The numbers:**
```
Register access:    ~0.5 ns
L1 cache hit:       ~1 ns
L2 cache hit:       ~4 ns
L3 cache hit:       ~12 ns
RAM access:         ~100 ns       ← 100x slower than L1!
```

If Redis's hot data structures cause frequent cache misses, performance drops dramatically.

**How Redis is cache-friendly:**

1. **Compact data structures:**
   - Small hashes use `ziplist` (contiguous memory, sequential scan) instead of hash tables (pointer-chasing)
   - Small sorted sets use `ziplist` instead of skip lists
   - Sequential memory = CPU prefetcher loads next cache lines automatically

2. **Memory allocator (jemalloc):**
   - Reduces fragmentation → related data stays on same/adjacent cache lines
   - Objects allocated near each other in time are near each other in memory

3. **Simple, branchless hot paths:**
   - Predictable code paths = branch predictor is happy
   - Tight loops = instruction cache friendly (code fits in L1i)

4. **Single-threaded advantage:**
   - No lock contention = no cache line bouncing between cores
   - In multi-threaded systems, a shared mutex causes the cache line containing it to ping-pong between cores (false sharing)
   - Redis avoids this entirely

5. **SDS (Simple Dynamic Strings):**
   ```
   ┌────┬────┬──────────────────┐
   │len │free│ string data...    │   ← single allocation, one cache line for small strings
   └────┴────┴──────────────────┘
   ```
   Compare with C++ `std::string`: pointer to heap buffer = extra indirection = potential cache miss.

**The math:**
- Redis handles ~100,000 ops/second/core
- At 100K ops/sec: 10 μs per operation budget
- A single L3 miss (cache miss to RAM) costs 100 ns = 1% of your per-operation budget
- 10 cache misses per operation = 10% throughput loss

**Why this matters beyond Redis:**
- Any latency-sensitive system (trading systems, game servers, databases) must think about cache
- PostgreSQL buffer pool is designed for cache efficiency
- Kafka's sequential I/O pattern is cache-friendly by nature
- Java's GC can destroy cache locality by moving objects around (G1 tries to preserve it)

---

## What's Next

Now you know what the CPU executes. Next: **How the CPU actually processes these instructions** — the Fetch → Decode → Execute cycle, pipelining, and why modern CPUs can execute multiple instructions per clock.

→ [Part 3: CPU Architecture](./part3_cpu_architecture.md)
