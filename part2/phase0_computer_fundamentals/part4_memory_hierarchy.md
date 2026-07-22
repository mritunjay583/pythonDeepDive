# Phase 0, Lesson 4 — Memory Hierarchy

## The Problem

The CPU is incredibly fast (~4 billion operations/second). But memory (RAM) is **slow** relative to the CPU. If the CPU had to wait for RAM every time it needed data, it would waste 99% of its time just waiting.

```
CPU speed:   ~0.25 ns per operation (4 GHz)
RAM speed:   ~100 ns to fetch data

That's a 400x gap. CPU does 400 operations in the time RAM returns 1 value.
```

This is called the **memory wall** — the CPU is starving for data.

---

## The Solution: Memory Hierarchy

Put small, fast memory close to the CPU. Put large, slow memory farther away. Most of the time, the data you need is in the fast memory.

```
┌─────────┐
│ Register│  ← fastest, smallest (bytes)
├─────────┤
│ L1 Cache│  ← very fast, small (32-64 KB)
├─────────┤
│ L2 Cache│  ← fast, medium (256 KB - 1 MB)
├─────────┤
│ L3 Cache│  ← moderate, larger (4-64 MB)
├─────────┤
│   RAM   │  ← slow, large (8-512 GB)
├─────────┤
│   SSD   │  ← very slow, very large (256 GB - 8 TB)
├─────────┤
│   HDD   │  ← glacial, massive (1-20 TB)
└─────────┘

   ↑ faster, smaller, more expensive (per byte)
   ↓ slower, larger, cheaper (per byte)
```

---

## The Numbers You Must Memorize

These latency numbers define how systems are designed:

| Level | Latency | Size | Analogy (if 1 cycle = 1 second) |
|-------|---------|------|----------------------------------|
| **Register** | ~0.5 ns (1 cycle) | 128 bytes | 1 second |
| **L1 Cache** | ~1 ns (3-4 cycles) | 32-64 KB | 3 seconds |
| **L2 Cache** | ~4 ns (12 cycles) | 256 KB - 1 MB | 12 seconds |
| **L3 Cache** | ~12 ns (40 cycles) | 4-64 MB | 40 seconds |
| **RAM** | ~100 ns (400 cycles) | 8-512 GB | 6 minutes |
| **SSD** | ~100 μs (100,000 ns) | 256 GB - 8 TB | 4 days |
| **HDD** | ~10 ms (10,000,000 ns) | 1-20 TB | 1 year |
| **Network** | ~1-100 ms | ∞ | 1-10 years |

**Key takeaway:** Going from L1 cache to RAM is like going from 3 seconds to 6 minutes. Going from RAM to disk is like going from 6 minutes to 4 days. These gaps drive every design decision in systems.

---

## Why This Hierarchy Works: Locality

The hierarchy only works because programs exhibit **locality** — they tend to access the same data (or nearby data) repeatedly.

### Temporal Locality
"If you accessed it recently, you'll probably access it again soon."

```python
# This loop accesses 'total' every iteration
total = 0
for i in range(1000000):
    total += i  # 'total' stays in register/L1 — fast!
```

### Spatial Locality
"If you accessed address X, you'll probably access X+1, X+2... soon."

```python
# Array traversal — accessing consecutive memory
arr = [1, 2, 3, 4, 5, 6, 7, 8]
for x in arr:      # elements are adjacent in memory
    process(x)     # CPU prefetches next elements into cache — fast!
```

### Why Linked Lists Are Slow

```python
# Array: elements consecutive in memory → cache-friendly
[1][2][3][4][5][6][7][8]   ← one cache line loads multiple elements

# Linked list: nodes scattered in memory → cache-hostile
[1|ptr]──→ ... [2|ptr]──→ ... [3|ptr]──→ ...
   ↑ random locations in memory, each access = potential cache miss
```

This is why **arrays are faster than linked lists in practice**, even when big-O says they should be the same. The memory hierarchy makes sequential access dramatically faster.

---

## How Cache Works (High-Level)

### Cache Lines
The CPU doesn't fetch individual bytes from RAM. It fetches **cache lines** (64 bytes on most systems).

```
You request: memory[1000] (1 byte)
CPU fetches: memory[960..1023] (entire 64-byte cache line)

Next access to memory[1001]? Already in cache. Free!
```

This is why sequential access is fast — one cache miss loads 64 bytes, giving you the next ~63 accesses for free.

### Cache Hit vs Cache Miss

```
Cache HIT: Data is in cache → ~1-12 ns (L1/L2/L3)
Cache MISS: Data not in cache → must go to RAM → ~100 ns

     CPU needs data at address X
              │
              ▼
     ┌─── In L1? ───┐
     │ YES          │ NO
     │ (1 ns)       ▼
     │        ┌─── In L2? ───┐
     │        │ YES          │ NO
     │        │ (4 ns)       ▼
     │        │        ┌─── In L3? ───┐
     │        │        │ YES          │ NO
     │        │        │ (12 ns)      ▼
     │        │        │         Go to RAM (100 ns)
     ▼        ▼        ▼              │
   USE IT   USE IT   USE IT      Fetch → Fill cache → USE IT
```

### Cache Eviction
Cache is small. When it's full, old data gets kicked out (evicted) to make room for new data. Common policy: **LRU** (Least Recently Used) — evict what hasn't been used longest.

Sound familiar? **This is exactly what Redis does for key eviction.** The same idea, different level.

---

## How RAM Works

RAM (Random Access Memory) = a large grid of capacitors. Each capacitor holds 1 bit (charged = 1, discharged = 0).

**Key properties:**
- **Random access** — any address takes the same time (~100 ns)
- **Volatile** — loses data when power off
- **DRAM** — capacitors leak charge, must be refreshed thousands of times/second

**How addressing works:**
```
Memory is byte-addressable. Each byte has a unique address.

Address:   0x0000  0x0001  0x0002  0x0003 ...
Content:   [0xFF]  [0x42]  [0x00]  [0xAB] ...

CPU says: "give me the byte at address 0x0001"
RAM returns: 0x42 (after ~100 ns)
```

**Virtual Memory (preview):** Your program thinks it has a huge continuous address space (e.g., 0 to 2^48). The OS + CPU (via page tables) translate these "virtual addresses" to physical RAM locations. This gives isolation between processes. Covered in Phase 1 (OS).

---

## Disk: Where Persistence Lives

| | HDD | SSD |
|---|---|---|
| **How it works** | Spinning magnetic platters + moving read head | Flash memory chips (no moving parts) |
| **Random read** | ~10 ms (head must physically move) | ~100 μs (100x faster than HDD) |
| **Sequential read** | ~100 MB/s | ~500 MB/s - 7 GB/s (NVMe) |
| **Why sequential matters** | No head movement needed | Less internal overhead |
| **Durability** | Non-volatile (survives power loss) | Non-volatile |

**Why sequential > random on disk:**
```
HDD: Head must physically move to the right track (seek time ~5-10 ms)
     Sequential = head stays put, data streams off platter

SSD: No moving parts, but random reads still have overhead
     (address translation, page reads, garbage collection)
     Sequential is still 5-10x faster than random
```

**This is why:**
- Kafka uses **sequential append** (commit log) — 10-100x faster than random writes
- PostgreSQL WAL is **sequential append** — durability without random I/O cost
- Redis RDB dumps sequentially — fast snapshot
- B-Trees minimize random seeks (fat nodes = fewer disk accesses)
- LSM Trees (RocksDB, Cassandra) turn random writes into sequential

---

## The Complete Picture

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│    CPU Core                                                      │
│    ┌──────────┐                                                  │
│    │ Registers│ 0.5 ns, 128 B                                    │
│    └────┬─────┘                                                  │
│         │                                                        │
│    ┌────▼─────┐                                                  │
│    │ L1 Cache │ 1 ns, 64 KB  (split: 32KB data + 32KB instr)    │
│    └────┬─────┘                                                  │
│         │                                                        │
│    ┌────▼─────┐                                                  │
│    │ L2 Cache │ 4 ns, 256 KB (per-core)                          │
│    └────┬─────┘                                                  │
│         │                                                        │
├─────────┼────────────────────────────────────────────────────────┤
│         │     Shared across cores                                 │
│    ┌────▼─────┐                                                  │
│    │ L3 Cache │ 12 ns, 8-64 MB (shared by all cores)             │
│    └────┬─────┘                                                  │
│         │                                                        │
└─────────┼────────────────────────────────────────────────────────┘
          │
     ┌────▼─────┐
     │   RAM    │ 100 ns, 16-512 GB
     └────┬─────┘
          │
     ┌────▼─────┐
     │  SSD     │ 100 μs, 256 GB - 8 TB
     └────┬─────┘
          │
     ┌────▼─────┐
     │  HDD     │ 10 ms, 1-20 TB
     └─────────┘
```

---

## How Real Systems Use Memory Hierarchy

| System | How It Exploits the Hierarchy |
|--------|-------------------------------|
| **Redis** | Everything in RAM (~100 ns access). Compact data structures for cache friendliness. |
| **PostgreSQL** | Buffer pool (frequently-used pages cached in RAM). B-Tree designed for disk page sizes. |
| **Kafka** | Relies on OS page cache (RAM). Sequential disk I/O only. |
| **Linux** | Page cache automatically keeps hot disk data in RAM. |
| **JVM** | Objects in RAM + JIT-compiled hot methods fit in instruction cache. GC can destroy locality. |
| **CPU itself** | Out-of-order execution hides cache miss latency by doing other work while waiting. |

---

## Interview Questions & Answers

### Q1: Why does the memory hierarchy exist? Why not just have one fast, large memory?

**Answer:** Physics and economics. Fast memory (SRAM for cache) requires ~6 transistors per bit and must be physically close to the CPU. Large memory (DRAM) uses 1 transistor + 1 capacitor per bit but is slower due to distance and design. You can't have terabytes of SRAM — it would be enormous, hot, and impossibly expensive. The hierarchy is a compromise: keep the most-used data fast, store the rest cheaply.

---

### Q2: What is a cache miss and why does it matter for performance?

**Answer:** A cache miss occurs when the CPU requests data that isn't in any cache level, forcing a fetch from RAM (~100 ns vs ~1 ns for L1 hit). During that wait, the pipeline stalls (or the CPU finds other work via out-of-order execution). For a latency-sensitive system like Redis processing 100K ops/sec, each operation has ~10 μs budget — a single RAM access (100 ns) consumes 1% of that budget. Multiple misses per operation visibly hurt throughput.

---

### Q3: What is cache locality and why does it matter?

**Answer:** Locality means programs tend to access the same data repeatedly (temporal) and nearby data sequentially (spatial). Caches exploit this: when you access one byte, the CPU loads the entire 64-byte cache line, making subsequent nearby accesses free. Code that respects locality (array traversal) runs 10-100x faster than code that doesn't (random pointer chasing in linked lists/trees). This is why arrays beat linked lists in practice despite identical big-O.

---

### Q4: Why is Kafka so fast despite writing to disk?

**Answer:** Kafka uses **sequential I/O** exclusively. It appends to the end of a file (commit log), never does random writes. Sequential disk I/O on modern SSDs achieves 1-7 GB/s — approaching RAM bandwidth. Additionally, Kafka relies on the **OS page cache** — the OS automatically keeps recently-read disk pages in RAM. Consumers reading recent messages hit RAM, not disk. The combination of sequential writes + page cache makes Kafka's disk-based design competitive with in-memory systems for throughput.

---

### Q5: Why does Redis use compact data structures like ziplist instead of regular hash tables for small collections?

**Answer:** 
- **Ziplist**: contiguous block of memory, elements packed next to each other. Scanning is sequential → CPU prefetcher loads next cache lines automatically. Entire small collection fits in 1-2 cache lines.
- **Hash table**: array of pointers to separately-allocated nodes. Each access follows a pointer to a random location → cache miss per lookup.

For small collections (<128 entries), the cache-friendly linear scan of a ziplist is faster than O(1) hash table lookup that causes cache misses. The big-O lie: O(n) with cache hits beats O(1) with cache misses for small n.

---

### Q6: Explain the latency numbers every programmer should know.

**Answer:**
```
L1 cache:      1 ns
L2 cache:      4 ns
L3 cache:      12 ns
RAM:           100 ns
SSD random:    100 μs (100,000 ns)
HDD random:    10 ms (10,000,000 ns)
Network (same datacenter): 0.5 ms
Network (cross-continent): 100 ms
```

The key ratios: RAM is 100x slower than L1. SSD is 1000x slower than RAM. HDD is 100x slower than SSD. Every system design decision — caching, replication, sharding — traces back to these gaps.

---

### Q7: What is the difference between SRAM and DRAM?

**Answer:**

| | SRAM (Cache) | DRAM (RAM) |
|---|---|---|
| Speed | ~1 ns | ~100 ns |
| Transistors/bit | 6 | 1 + 1 capacitor |
| Needs refresh? | No | Yes (leaks charge) |
| Cost | Expensive | Cheap |
| Used for | L1/L2/L3 cache | Main memory |
| Size | KB to MB | GB to TB |

SRAM is fast because it uses a bistable flip-flop (no capacitor to charge/discharge). DRAM is dense because it uses just a tiny capacitor per bit, but the capacitor leaks and must be refreshed thousands of times per second.

---

---

## Who Moves Data Between RAM and CPU?

It's **not** the Fetch unit (that only fetches **instructions**). There's a separate unit called the **Load/Store Unit** inside the CPU.

```
┌─────────────────────────────────────────────────────────────┐
│                         CPU                                   │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Fetch Unit  │    │ Execute Unit │    │ Load/Store   │  │
│  │              │    │   (ALU)      │    │    Unit      │  │
│  │ Gets INSTR   │    │ Does math    │    │ Gets/Puts    │  │
│  │ from memory  │    │              │    │ DATA to/from │  │
│  │              │    │              │    │ memory       │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                                       │           │
│    reads instructions                     reads/writes data │
│         │                                       │           │
└─────────┼───────────────────────────────────────┼───────────┘
          │                                       │
          ▼                                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Cache Controller (hardware)                      │
│   Checks L1 → L2 → L3 → if all miss → asks RAM             │
└─────────────────────────────────────────────────────────────┘
          │                                       │
          ▼                                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Memory Controller → RAM                          │
└─────────────────────────────────────────────────────────────┘
```

### The Flow for `LOAD R1, [address]` (reading data)

```
1. CPU decodes instruction: "LOAD R1 from address 0x1000"

2. Load/Store Unit sends request to Cache Controller:
   "I need data at address 0x1000"

3. Cache Controller checks:
   L1? → miss
   L2? → miss
   L3? → miss
   → Sends request to Memory Controller

4. Memory Controller fetches 64-byte cache line from RAM
   (takes ~100 ns)

5. Data flows back: RAM → L3 → L2 → L1 → Load/Store Unit → Register R1

6. CPU continues (R1 now has the value)
```

### The Flow for `STORE [address], R1` (writing data)

```
1. CPU decodes: "STORE R1 value to address 0x2000"

2. Load/Store Unit takes value from R1, sends to Cache Controller:
   "Write this value to address 0x2000"

3. Cache Controller writes to L1 cache (fast!)
   → Marks cache line as "dirty" (modified)

4. Later (not immediately!), dirty cache line gets flushed to RAM
   (write-back policy — lazy write)

   Data is NOT immediately in RAM. It's in cache.
   RAM gets updated later when the cache line is evicted.
```

### Who Does What

| Question | Answer |
|----------|--------|
| Who fetches **instructions** from memory? | Fetch Unit |
| Who fetches/stores **data** from/to memory? | Load/Store Unit |
| Who decides if data is in cache or RAM? | Cache Controller (hardware, automatic) |
| Who physically talks to RAM chips? | Memory Controller |
| Does the programmer control any of this? | No. It's all automatic hardware. You just say LOAD/STORE. |

The CPU doesn't talk to RAM directly. Everything goes through the cache controller. It's called a **transparent cache** — invisible to the program. The same instruction works whether data is in L1 (1 ns) or RAM (100 ns). The only difference is how long you wait.

---

## Where Do Instructions and Data Live?

When you run a program, **both instructions AND data live in RAM** initially. The CPU fetches them into cache/registers as needed.

```
RAM (when program starts):
┌──────────────────────────────────────────────────┐
│                                                   │
│   CODE SECTION (instructions)                     │
│   ┌──────────────────────────────────┐           │
│   │ 0x1000: MOV R0, 4               │           │
│   │ 0x1004: MOV R1, 5               │           │
│   │ 0x1008: ADD R0, R0, R1   (x=4+5)│           │
│   │ 0x100C: MOV R1, 10              │           │
│   │ 0x1010: ADD R0, R0, R1   (x=x+10)│          │
│   │ 0x1014: MOV R0, 100     (x=100) │           │
│   │ 0x1018: CALL print              │           │
│   └──────────────────────────────────┘           │
│                                                   │
│   DATA SECTION (variables)                        │
│   ┌──────────────────────────────────┐           │
│   │ 0x5000: x = ???  (will be here)  │           │
│   └──────────────────────────────────┘           │
│                                                   │
└──────────────────────────────────────────────────┘
```

**Key point:** Instructions and data are BOTH just bytes in RAM. They're in different sections, but both start in RAM.

### Tracing Through: `x = 4+5; x = x+10; x = 100; print(x)`

```
STEP 1: Program starts. All instructions are in RAM.
        CPU's PC (program counter) = 0x1000 (first instruction)

STEP 2: Fetch Unit needs instruction at 0x1000
        → Cache controller checks L1 instruction cache
        → MISS (first time) → fetches from RAM
        → Entire cache line (64 bytes = ~16 instructions) loaded into L1
        → Now instructions at 0x1000-0x103F are ALL in L1 cache!

STEP 3: CPU executes instructions — all from L1 cache now (fast!)
```

The actual execution:

```
Instruction         │ What Happens                    │ Where is 'x'?
────────────────────┼─────────────────────────────────┼──────────────────
MOV R0, 4          │ R0 = 4                           │ In register R0
MOV R1, 5          │ R1 = 5                           │ -
ADD R0, R0, R1     │ R0 = 4 + 5 = 9                  │ In register R0
MOV R1, 10         │ R1 = 10                          │ -
ADD R0, R0, R1     │ R0 = 9 + 10 = 19                │ In register R0
MOV R0, 100        │ R0 = 100                         │ In register R0
CALL print         │ Print value in R0                │ In register R0
```

**Notice:** For this simple program, `x` **never goes to RAM at all!** It lives entirely in a register. The compiler is smart enough to keep it there.

### When Does Data Actually Go Back to RAM?

Data goes to RAM only when:
1. **You run out of registers** (too many variables, must "spill" to stack/RAM)
2. **Function returns** (local variables on stack may be needed later)
3. **You explicitly store** (writing to an array, object field, etc.)
4. **Another thread needs it** (shared data must be in RAM for visibility)

```
Simple case (stays in registers):
    x = 4 + 5        → register only, never touches RAM

Complex case (must use RAM):
    array[100] = 42   → must STORE to RAM (array too big for registers)
    obj.field = x     → must STORE to RAM (object lives on heap)
```

### The Two Separate L1 Caches

Most CPUs have **split L1 cache** — separate caches for instructions and data:

```
┌────────────────────────────────────────┐
│              CPU Core                    │
│                                         │
│   Fetch Unit ──→ L1i (Instruction Cache, 32KB)
│                                         │
│   Load/Store ──→ L1d (Data Cache, 32KB) │
│                                         │
│   Both ────────→ L2 (Unified, 256KB)    │
│                                         │
└────────────────────────────────────────┘
```

Why split? Because the CPU fetches instructions AND data simultaneously (pipelining). Two caches = no conflict.

### The Full Journey of a Program

```
DISK (before run):
  program.exe file contains both instructions + initial data

     │  (OS loads program into RAM when you run it)
     ▼

RAM (program loaded):
  Code section: instructions at 0x1000-0x1020
  Data section: global/static variables
  Stack: local variables (grows as functions are called)
  Heap: dynamic allocations (malloc/new)

     │  (CPU fetches as needed)
     ▼

L1i Cache: recently-fetched instructions
L1d Cache: recently-accessed data (variables, array elements)

     │  (active computation)
     ▼

Registers: currently-being-used values (x = R0 in our example)
```

### Summary

| Question | Answer |
|----------|--------|
| Where are instructions stored initially? | RAM (code section) |
| Where are instructions when executing? | L1 instruction cache (fetched automatically) |
| Where is variable data initially? | RAM (stack or heap) |
| Where is data during computation? | Registers (if compiler can) or L1 data cache |
| Does the whole program load into CPU? | No. Only the current cache lines. Rest stays in RAM. |
| Do instructions and data share cache? | L1 is split (L1i + L1d). L2/L3 are unified (shared). |
| Who decides what's in cache? | Hardware (cache controller). Automatic. Invisible. |

The big insight: **A program starts on disk, gets loaded to RAM by the OS, and the CPU pulls instructions + data into cache on-demand, a cache line at a time.** Only the currently "hot" portions are ever in cache. For small programs, everything fits in L1 after the first access. For large programs (big data, databases), cache management becomes critical for performance.

---

## What's Next

You now understand the memory hierarchy and why every system is designed around it. Next: **Cache deep dive** — cache lines, associativity, write policies, and false sharing.

→ [Part 5: Cache](./part5_cache.md)
