# Phase 0, Lesson 3 — CPU Architecture

## The Big Picture

The CPU does ONE thing on repeat, billions of times per second:

```
┌────────┐     ┌────────┐     ┌─────────┐
│ FETCH  │ ──► │ DECODE │ ──► │ EXECUTE │ ──► (repeat)
└────────┘     └────────┘     └─────────┘
```

That's it. Every program — Redis serving 100K requests/sec, PostgreSQL running a complex JOIN, Linux scheduling 1000 processes — is just this cycle running really fast.

---

## CPU Components

```
┌─────────────────────────────────────────────────────────────┐
│                         CPU                                   │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Control Unit │    │     ALU      │    │  Registers   │  │
│  │              │    │              │    │              │  │
│  │ • Fetches    │    │ • Arithmetic │    │ • RAX, RBX   │  │
│  │ • Decodes    │    │ • Logic      │    │ • RIP (PC)   │  │
│  │ • Directs    │    │ • Comparison │    │ • RSP, RBP   │  │
│  │   data flow  │    │              │    │ • RFLAGS     │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  L1 Cache (32-64 KB)                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

| Component | Role |
|-----------|------|
| **Control Unit** | Orchestra conductor — fetches instructions, decodes them, tells other units what to do |
| **ALU** | Does the math — addition, subtraction, AND, OR, comparisons |
| **Registers** | Tiny ultra-fast storage inside CPU (~16 general purpose on x86-64) |
| **L1 Cache** | Small fast memory right next to the core |

---

## The Fetch-Decode-Execute Cycle

### Step 1: FETCH
- Read the instruction at address stored in **RIP** (program counter)
- RIP auto-increments to next instruction

### Step 2: DECODE
- Break instruction into opcode + operands
- Figure out what operation and which registers/memory

### Step 3: EXECUTE
- ALU performs the operation
- Result goes to a register or memory
- Flags updated (zero, carry, overflow)

### Step 4: WRITE-BACK (in pipelined CPUs)
- Write result to destination register or memory

```
Example: ADD R1, R2, R3

FETCH:   Read "ADD R1, R2, R3" from memory[RIP]
DECODE:  opcode=ADD, dest=R1, src1=R2, src2=R3
EXECUTE: ALU computes R2 + R3
WRITE:   Store result in R1
```

---

## What Does the Execute Stage Actually Produce?

A common confusion: "Execute always produces a single value like 5, right?"

**No.** The output of Execute depends on the instruction type:

| Instruction Type | Execute Output | Where It Goes |
|-----------------|---------------|---------------|
| `ADD R1, R2, R3` | A computed value (e.g., 5) | → Write-Back stores it in R1 |
| `CMP R1, R2` | No data value — sets **flags** (zero, carry, negative) | → RFLAGS register |
| `STORE [addr], R1` | A memory write (sends data to RAM/cache) | → Memory system |
| `LOAD R1, [addr]` | A memory read request | → Memory stage fetches data → Write-Back puts it in R1 |
| `JMP addr` | A new PC value | → Program counter updated |
| `JZ label` | Decision: jump or not (based on flags) | → PC changes OR stays |
| `NOP` | Nothing | → Just advances PC |

**So Execute can produce:**

1. **A data value** (arithmetic/logic) → goes to a register
2. **Flag updates** (comparisons) → goes to RFLAGS
3. **A memory operation** (load/store) → goes to memory system
4. **A control flow change** (jump/call) → modifies the program counter
5. **Nothing visible** (NOP) → just advances PC

**The ALU is more than a calculator.** It also computes memory addresses and branch targets:

```
ADD R1, R2, R3  →  ALU computes R2+R3          →  result → R1
CMP R1, 5      →  ALU computes R1-5           →  flags only (zero? negative?)
LOAD R1, [R2]  →  ALU computes address in R2  →  memory unit fetches → R1
JMP [R1+8]     →  ALU computes R1+8           →  result → PC
```

**Key insight:** "Execute" means "do whatever this instruction says." The output type is determined by the opcode that was decoded. It's not always a number — it can be a flag change, a memory operation, or a jump.

---

## Clock & Clock Cycle — The CPU's Heartbeat

Before understanding pipelining, you need to understand what drives it: the **clock**.

### What is a Clock?

The CPU has a **crystal oscillator** — a tiny piece of quartz that vibrates at a fixed frequency. It produces an electrical signal that alternates between HIGH and LOW:

```
Voltage
  │
  │   ┌──┐  ┌──┐  ┌──┐  ┌──┐  ┌──┐
  │   │  │  │  │  │  │  │  │  │  │
  │───┘  └──┘  └──┘  └──┘  └──┘  └──
  │
  └─────────────────────────────────── Time
      ^     ^     ^     ^     ^
      │     │     │     │     │
    cycle cycle cycle cycle cycle
```

Each **tick** (rising edge) = 1 clock cycle. It's a heartbeat — nothing more.

### What is a Clock Cycle?

One clock cycle = **the smallest unit of time** the CPU works in. On every tick, something moves forward by one step.

- **4 GHz** = 4 billion ticks per second
- Each tick = 0.25 nanoseconds (a quarter of a billionth of a second)

### Key Terminology

| Term | Meaning |
|------|---------|
| **Clock** | A crystal that ticks at a fixed rate (the heartbeat) |
| **Clock cycle** | One tick — the minimum time unit |
| **Clock speed (GHz)** | How many ticks per second |
| **CPI** | Cycles Per Instruction (ideal = 1 with pipeline) |
| **IPC** | Instructions Per Cycle (inverse of CPI, can be >1 with superscalar) |
| **Latency** | How long 1 instruction takes start to finish (multiple cycles) |
| **Throughput** | How many instructions complete per cycle |

The clock is the metronome. Everything in the CPU dances to it.

---

## Pipelining — The Assembly Line

### Why Pipelining Exists

The CPU has **separate hardware units** for each stage. They're physically different circuits:

```
┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  Fetch Unit   │   │  Decode Unit  │   │ Execute Unit  │   │ Write-Back    │
│               │   │               │   │               │   │               │
│ Reads instr   │──►│ Cracks opcode │──►│ ALU computes  │──►│ Stores result │
│ from memory   │   │ + operands    │   │               │   │ in register   │
└───────────────┘   └───────────────┘   └───────────────┘   └───────────────┘
```

**Without pipelining** — only ONE unit is busy at a time, the rest sit idle:

```
Cycle:   1    2    3    4    5    6    7    8
Fetch:  [I1]  -    -    -   [I2]  -    -    -
Decode:  -   [I1]  -    -    -   [I2]  -    -
Execute: -    -   [I1]  -    -    -   [I2]  -
Write:   -    -    -   [I1]  -    -    -   [I2]

→ 2 instructions in 8 cycles. 3 units idle at any time. Wasteful!
```

**With pipelining** — ALL units are busy simultaneously, each working on a different instruction:

```
Cycle:   1    2    3    4    5    6    7
Fetch:  [I1] [I2] [I3] [I4]  -    -    -
Decode:  -   [I1] [I2] [I3] [I4]  -    -
Execute: -    -   [I1] [I2] [I3] [I4]  -
Write:   -    -    -   [I1] [I2] [I3] [I4]

→ 4 instructions in 7 cycles. All units busy after cycle 4!
```

### What Happens at Cycle 4 (All Units Busy):

```
At cycle 4, simultaneously:
  • Fetch Unit   → fetching Instruction 4
  • Decode Unit  → decoding Instruction 3
  • Execute Unit → executing Instruction 2
  • Write-Back   → writing result of Instruction 1

Four different instructions, four different stages, ALL at the same time.
```

Like a car factory: one car is getting painted while another gets its engine while another gets wheels. Different cars at different stations, all moving together.

### How Clock Drives the Pipeline

Each pipeline stage takes **exactly 1 clock cycle**. On every tick, every instruction advances one stage:

```
         Cycle 1    Cycle 2    Cycle 3    Cycle 4
Clock:   ──┐  ┌──  ──┐  ┌──  ──┐  ┌──  ──┐  ┌──
           │  │      │  │      │  │      │  │
           └──┘      └──┘      └──┘      └──┘

Instr 1: [FETCH]   [DECODE]  [EXECUTE] [WRITE]
              ↑          ↑         ↑         ↑
         "tick!"    "tick!"   "tick!"   "tick! done"
```

On every clock tick the CPU says: "everyone advance one step." Like a conveyor belt that moves one position every beat.

### Latency vs Throughput — The Key Distinction

| | Without Pipelining | With Pipelining |
|---|---|---|
| **Latency** (time for 1 instruction) | 4 cycles | Still 4 cycles |
| **Throughput** (instructions completed per cycle) | 1 every 4 cycles | 1 every 1 cycle (after warmup) |

Pipelining doesn't make a single instruction faster. Each still takes 4 cycles. But a **new instruction finishes every cycle** after the pipeline is full.

**Analogy:** A pizza oven takes 10 minutes per pizza. But if you put a new pizza in every minute (conveyor oven), a finished pizza comes out every minute after the first 10 minutes. Latency = 10 min. Throughput = 1/min.

### What "4 GHz" Actually Means for Performance

```
4 GHz = 4 billion cycles/second
With pipelining: ~1 instruction/cycle (ideal)
With superscalar (4-wide): ~4 instructions/cycle

Theoretical max: ~4-16 billion instructions/second
Actual (cache misses, branches, stalls): ~2-6 billion useful instructions/second
```

**Modern CPUs:** 14-20 pipeline stages + **superscalar** (multiple pipelines = multiple instructions per cycle).

---

## What Breaks the Pipeline

| Hazard | Problem | How CPU Handles It |
|--------|---------|-------------------|
| **Data hazard** | Next instruction needs result not ready yet | Forwarding (bypass result directly) |
| **Control hazard** | Branch — don't know next instruction | Branch prediction (guess, flush if wrong) |
| **Cache miss** | Data not in cache, wait for RAM (~100 cycles) | Out-of-order execution (do other work while waiting) |

**Pipeline stall cost:**
- Branch misprediction: ~15-20 cycles wasted
- L1 cache miss: ~4 cycles
- L2 miss: ~12 cycles
- L3 miss (go to RAM): ~100+ cycles

---

## Modern CPU Tricks (High-Level)

| Technique | What It Does | Why It Matters |
|-----------|-------------|----------------|
| **Superscalar** | Multiple instructions execute per cycle | More throughput without higher clock |
| **Out-of-order execution** | Reorder instructions to avoid stalls | Hides memory latency |
| **Branch prediction** | Guess branch direction, execute speculatively | Keeps pipeline full |
| **Hyper-threading** | One physical core looks like 2 logical cores | Uses idle execution units |
| **SIMD** | One instruction operates on multiple data items | Vectorized math (useful for ML, media) |

---

## Clock Speed vs Actual Speed

**Clock speed** (e.g., 4 GHz = 4 billion cycles/second) is NOT the full picture.

What matters is: **Instructions Per Cycle (IPC) × Clock Speed = Actual throughput**

- A 3 GHz CPU with IPC of 4 = 12 billion instructions/second
- A 5 GHz CPU with IPC of 1 = 5 billion instructions/second
- The slower clock wins!

This is why Apple M-series (lower clock, high IPC) beats Intel (higher clock, lower IPC per watt).

---

## How This Connects to Systems You'll Build

| Concept | Real-World Impact |
|---------|-------------------|
| Pipelining | Why branchless code is faster (Redis uses this) |
| Cache miss | Why Redis uses compact data structures (ziplist) |
| Out-of-order | Why single-threaded Redis is still fast despite sequential code |
| Superscalar | Why simple instructions > complex ones (RISC philosophy) |
| Hyper-threading | Why a 4-core machine shows 8 CPUs in `htop` |
| Clock speed | Why AWS Graviton (ARM, lower clock) is cheaper AND competitive |

---

## Interview Questions & Answers

### Q1: Explain the fetch-decode-execute cycle.

**Answer:** The CPU continuously: (1) **Fetches** the instruction at the program counter address, (2) **Decodes** it into opcode + operands, (3) **Executes** it via ALU or memory unit, (4) **Writes back** the result. The program counter advances each cycle. This repeats billions of times per second.

---

### Q2: What is pipelining and why does every modern CPU use it?

**Answer:** Pipelining overlaps execution stages of multiple instructions — like an assembly line. While instruction 1 is executing, instruction 2 is decoding, and instruction 3 is being fetched. This gives ~1 instruction/cycle throughput instead of 1 instruction every 4+ cycles. Every CPU uses it because it multiplies throughput without increasing clock speed.

---

### Q3: What is out-of-order execution?

**Answer:** The CPU doesn't execute instructions strictly in program order. If instruction 5 is waiting for a cache miss but instruction 6-10 are independent, the CPU executes 6-10 first. Results are **committed in order** (so the program behaves correctly), but executed out of order to hide latency. This is why even single-threaded code benefits from modern CPUs — the hardware parallelizes it.

---

### Q4: What is hyper-threading and does it double performance?

**Answer:** Hyper-threading lets one physical core maintain **two architectural states** (two sets of registers, two program counters). The core shares execution units between two threads. It does NOT double performance — typical gain is 15-30% because both threads compete for the same ALU, cache, and execution units. It helps when one thread is stalled (cache miss, branch mispredict) — the other thread uses the idle units.

**When it hurts:** latency-sensitive workloads (Redis disables HT on dedicated servers because it adds unpredictable jitter).

---

### Q5: Why are modern CPUs so much faster than 1990s CPUs at similar clock speeds?

**Answer:** Clock speed plateaued around 2004 (~4 GHz, power wall). Performance improvements since then come from:
- Deeper pipelines + more pipeline stages
- Wider superscalar (4-8 instructions/cycle vs 1)
- Larger caches (L1: 32KB → 64KB, L3: 0 → 32MB+)
- Better branch prediction (97%+ accuracy)
- More aggressive out-of-order execution
- SIMD units for parallel math

A 2024 CPU at 4 GHz is ~10-20x faster than a 2000 CPU at 4 GHz because of IPC improvements.

---

## What's Next

You now understand how the CPU executes code. Next: **Memory Hierarchy** — why the CPU can't just talk to RAM directly and why cache exists.

→ [Part 4: Instruction Cycle (detailed)](./part4_instruction_cycle.md) *(optional deep dive)*
→ [Part 5: Memory Hierarchy](./part5_memory_hierarchy.md) *(recommended next)*

---

## Ready for the Project?

You now have enough knowledge to build the **Tiny CPU Simulator**. Here's the spec:

### Tiny CPU Simulator — Requirements

```
Registers: R0-R7 (8 general purpose) + PC (program counter)
Memory: 256 bytes (instruction + data)
Instructions:
  LOAD  Rd, addr      — Rd = memory[addr]
  STORE addr, Rs      — memory[addr] = Rs
  ADD   Rd, Rs1, Rs2  — Rd = Rs1 + Rs2
  SUB   Rd, Rs1, Rs2  — Rd = Rs1 - Rs2
  MOV   Rd, immediate — Rd = immediate value
  JMP   addr          — PC = addr
  JZ    addr          — if last result == 0: PC = addr
  HALT                — stop execution

Cycle: Fetch → Decode → Execute → repeat until HALT
```

### Example Program (add 5 + 3):
```
MOV  R0, 5      ; R0 = 5
MOV  R1, 3      ; R1 = 3
ADD  R2, R0, R1 ; R2 = 8
HALT
```

Build it in Python. Implement the fetch-decode-execute loop. Print register state after each cycle. That's your proof you understand how computers work at the lowest level.
