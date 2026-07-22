# Phase 1, Chapter 1b — Inspecting a Process Live on Linux

## Continuing from Part 1a...

We have `server.py` running as PID 12345. Let's inspect everything about this process using Linux tools. **Run these commands yourself.**

---

## Inspection 1: Basic Process Info

```bash
# What command started this process?
$ cat /proc/12345/cmdline | tr '\0' ' '
python3 server.py

# Process status (THE MOST IMPORTANT FILE)
$ cat /proc/12345/status
Name:   python3
Umask:  0022
State:  S (sleeping)          ← Process state! S = sleeping (waiting for I/O)
Tgid:   12345                 ← Thread Group ID (= PID for main thread)
Pid:    12345                 ← Process ID
PPid:   11000                 ← Parent PID (our bash shell)
TracerPid: 0
Uid:    1000  1000  1000  1000
Gid:    1000  1000  1000  1000
FDSize: 256                   ← File descriptor table size
VmPeak: 52340 kB             ← Peak virtual memory used
VmSize: 52340 kB             ← Current virtual memory size
VmRSS:  28456 kB             ← Resident Set Size (actual RAM used!)
VmData: 15632 kB             ← Heap size
VmStk:  8192 kB              ← Stack size
VmExe:  2780 kB              ← Code (text) segment size
Threads: 1                    ← Number of threads
```

**What we learned:**
- State is `S` (sleeping) — our process is in `time.sleep()`, waiting
- It uses 28MB of actual RAM (VmRSS)
- It has 1 thread (the main thread)
- Parent is PID 11000 (our bash shell)

---

## Inspection 2: Process States — What Does "State: S" Mean?

Every process is in exactly ONE state at any moment:

```
┌─────────────────────────────────────────────────────────────────┐
│              LINUX PROCESS STATES                                 │
├────────┬────────────────────────────────────────────────────────┤
│ Letter │ State         │ Meaning                                 │
├────────┼───────────────┼────────────────────────────────────────┤
│   R    │ Running       │ Currently on CPU OR ready to run        │
│   S    │ Sleeping      │ Waiting for event (I/O, timer, signal)  │
│        │ (Interruptible)│ Can be woken by signals                │
│   D    │ Disk Sleep    │ Waiting for disk I/O                    │
│        │ (Uninterruptible)│ CANNOT be killed (even kill -9)     │
│   T    │ Stopped       │ Paused (Ctrl+Z or debugger)            │
│   Z    │ Zombie        │ Finished but parent hasn't read exit    │
│        │               │ status yet (wait() not called)          │
│   X    │ Dead          │ Being removed (you'll never see this)   │
├────────┴───────────────┴────────────────────────────────────────┤
│                                                                   │
│  TRANSITIONS:                                                    │
│                                                                   │
│  Created ──► R (Ready) ──► R (Running on CPU)                    │
│                    ▲              │                               │
│                    │              │ needs I/O or sleep()          │
│                    │              ▼                               │
│                    │         S (Sleeping)                         │
│                    │              │                               │
│                    │              │ I/O complete / timer fires    │
│                    └──────────────┘                               │
│                                                                   │
│  Running ──► Z (Zombie) ──► X (Dead/Removed)                    │
│       (exit())      (parent calls wait())                        │
└─────────────────────────────────────────────────────────────────┘
```

### See It Live:

```bash
# See state of ALL processes
$ ps aux | head -20
USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root         1  0.0  0.1 168940 11788 ?        Ss   Jan14   0:05 /sbin/init
root         2  0.0  0.0      0     0 ?        S    Jan14   0:00 [kthreadd]
user     12345  0.1  0.7  52340 28456 pts/0    S    10:00   0:01 python3 server.py

# STAT column meanings:
# S  = sleeping (interruptible)
# Ss = sleeping + session leader
# R  = running
# Sl = sleeping + multi-threaded
# Z  = zombie
# D  = uninterruptible sleep (disk I/O)
```

### Experiment: Watch State Changes

```bash
# Terminal 1: Run a CPU-intensive Python script
$ python3 -c "
import os
print(f'PID: {os.getpid()}')
while True:
    x = sum(range(1000000))  # CPU-bound work
" &
# Note the PID

# Terminal 2: Watch its state
$ while true; do cat /proc/<PID>/status | grep State; sleep 0.1; done
State:  R (running)      ← It's on the CPU!
State:  R (running)
State:  R (running)      ← Stays in R because it's doing CPU work non-stop
```

```bash
# Now try with our sleeping server:
$ while true; do cat /proc/12345/status | grep State; sleep 0.1; done
State:  S (sleeping)     ← It's sleeping (time.sleep)
State:  S (sleeping)
State:  S (sleeping)     ← Stays in S because it's just waiting
```

**Key insight:** A process doing `time.sleep()` or waiting for network I/O is in state `S`. It's NOT using any CPU. It's just sitting in a wait queue. The scheduler ignores it until the event it's waiting for happens.

---

## Inspection 3: Memory Map — What's in This Process's Memory?

```bash
$ cat /proc/12345/maps
# Address range          Perms  Offset  Device Inode  Path
55d4a2000000-55d4a2200000 r--p  000000  08:01  12345  /usr/bin/python3.11
55d4a2200000-55d4a29e0000 r-xp  200000  08:01  12345  /usr/bin/python3.11
55d4a29e0000-55d4a2c80000 r--p  9e0000  08:01  12345  /usr/bin/python3.11
55d4a2c80000-55d4a2c90000 r--p  c70000  08:01  12345  /usr/bin/python3.11
55d4a2c90000-55d4a2d60000 rw-p  c80000  08:01  12345  /usr/bin/python3.11
55d4a3000000-55d4a4500000 rw-p  000000  00:00  0      [heap]
7f1234000000-7f1234200000 r--p  000000  08:01  67890  /usr/lib/libc.so.6
...
7ffd12300000-7ffd12321000 rw-p  000000  00:00  0      [stack]
7ffd12321000-7ffd12325000 r--p  000000  00:00  0      [vvar]
7ffd12325000-7ffd12327000 r-xp  000000  00:00  0      [vdso]
```

**Reading this:**

```
┌─────────────────────────────────────────────────────────────────┐
│  MEMORY MAP DECODED                                              │
│                                                                   │
│  Permission flags: r=read, w=write, x=execute, p=private        │
│                                                                   │
│  r-xp = code (read + execute, no write → can't modify code)    │
│  rw-p = data/heap/stack (read + write, no execute → no code)    │
│  r--p = read-only data (constants, read-only sections)          │
│                                                                   │
│  What we see:                                                    │
│  /usr/bin/python3.11 r-xp  = Python interpreter CODE            │
│  /usr/bin/python3.11 rw-p  = Python interpreter DATA            │
│  [heap]              rw-p  = Our 1M integers live here!         │
│  /usr/lib/libc.so.6  r-xp  = C library code                    │
│  [stack]             rw-p  = Main thread's stack                │
│  [vdso]              r-xp  = Virtual Dynamic Shared Object      │
│                              (kernel page mapped into process    │
│                               for fast syscalls like clock)     │
└─────────────────────────────────────────────────────────────────┘
```

### More Useful: pmap

```bash
$ pmap -x 12345
Address           Kbytes     RSS   Dirty Mode  Mapping
000055d4a2000000    2048    1024       0 r---- python3.11
000055d4a2200000    7936    5120       0 r-x-- python3.11    ← CODE
000055d4a2c90000     832     832     832 rw--- python3.11    ← DATA
000055d4a3000000   21504   15360   15360 rw---   [ anon ]    ← HEAP
00007ffd12300000     132      52      52 rw---   [ stack ]   ← STACK
                  ------  ------  ------
total kB           52340   28456   16244
```

**RSS (Resident Set Size) = actual physical RAM used.** Our process uses 28MB of real RAM.

---

## Inspection 4: Open File Descriptors

```bash
$ ls -la /proc/12345/fd/
lrwx------ 1 user user 64 Jan 15 10:01 0 -> /dev/pts/0      ← stdin (terminal)
lrwx------ 1 user user 64 Jan 15 10:01 1 -> /dev/pts/0      ← stdout (terminal)
lrwx------ 1 user user 64 Jan 15 10:01 2 -> /dev/pts/0      ← stderr (terminal)
lrwx------ 1 user user 64 Jan 15 10:01 3 -> socket:[98765]  ← OUR TCP SOCKET!
```

**Every open file, socket, pipe = a file descriptor (integer).** 0, 1, 2 are always stdin/stdout/stderr. Our socket got fd=3.

```bash
# See socket details
$ cat /proc/12345/net/tcp
  sl  local_address rem_address   st tx_queue rx_queue
   0: 0100007F:270F 00000000:0000 0A 00000000:00000000
#     127.0.0.1:9999  0.0.0.0:0   LISTEN

# 0100007F = 127.0.0.1 (hex, reversed bytes)
# 270F = 9999 (hex)
# 0A = state 10 = LISTEN
```

**We can see our socket is listening on 127.0.0.1:9999!** All from /proc.

---

## Inspection 5: Using `ps`, `top`, and `htop`

```bash
# Detailed view of our process
$ ps -p 12345 -o pid,ppid,state,vsz,rss,comm,args
  PID   PPID S    VSZ   RSS COMMAND         COMMAND
12345  11000 S  52340 28456 python3         python3 server.py

# Real-time monitoring
$ top -p 12345
  PID USER      PR  NI    VIRT    RES    SHR S  %CPU %MEM     TIME+ COMMAND
12345 user      20   0   52340  28456   8200 S   0.0  0.7   0:01.23 python3
```

**Columns decoded:**
| Column | Meaning |
|--------|---------|
| PID | Process ID |
| PPID | Parent Process ID |
| S | State (S=sleeping, R=running) |
| VIRT/VSZ | Virtual memory (what process *thinks* it has) |
| RES/RSS | Resident memory (actual physical RAM used) |
| SHR | Shared memory (shared libraries, shared pages) |
| %CPU | CPU usage percentage |
| %MEM | Memory usage percentage |
| TIME+ | Total CPU time consumed |

---

## The Process Tree — Every Process Has a Parent

```bash
$ pstree -p
systemd(1)─┬─sshd(800)───sshd(11000)───bash(11001)───python3(12345)
            ├─systemd-journal(400)
            ├─networkd(500)
            └─cron(600)
```

**Process hierarchy:**
```
systemd (PID 1)          ← The FIRST process. Parent of all.
  └── sshd (800)         ← SSH daemon
       └── sshd (11000)  ← Your SSH session
            └── bash (11001)   ← Your shell
                 └── python3 (12345)  ← YOUR PROCESS
```

Every process (except PID 1) was created by another process using `fork()`. This creates a tree.

```bash
# See it yourself
$ ps -ef --forest
UID        PID  PPID  C STIME TTY          TIME CMD
root         1     0  0 Jan14 ?        00:00:05 /sbin/init
root       800     1  0 Jan14 ?        00:00:00  \_ /usr/sbin/sshd
user     11000   800  0 10:00 ?        00:00:00      \_ sshd: user@pts/0
user     11001 11000  0 10:00 pts/0    00:00:00          \_ -bash
user     12345 11001  0 10:00 pts/0    00:00:01              \_ python3 server.py
```

