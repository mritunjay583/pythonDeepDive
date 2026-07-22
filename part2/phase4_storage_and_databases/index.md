# Phase 4 — Storage Engines & Databases

## Why This Phase?
Every serious system stores data. Understanding how databases work internally separates senior engineers from everyone else.

## Roadmap

| # | Topic | What You'll Learn |
|---|-------|-------------------|
| 1 | Why Databases Exist | Beyond files — concurrency, durability, queries |
| 2 | Disk Layout & Pages | How data lives on disk |
| 3 | Buffer Pool | Page cache, dirty pages, eviction |
| 4 | B-Trees | The workhorse of databases |
| 5 | LSM Trees | Write-optimized storage (RocksDB, Cassandra) |
| 6 | WAL (Write-Ahead Log) | Crash recovery, durability |
| 7 | Transactions & ACID | Atomicity, Consistency, Isolation, Durability |
| 8 | Isolation Levels | Read committed, repeatable read, serializable |
| 9 | MVCC | How PostgreSQL handles concurrent reads/writes |
| 10 | Indexes | B-tree, hash, composite, covering |
| 11 | Query Planner & Optimizer | How SELECT becomes a plan |
| 12 | Joins | Nested loop, hash join, merge join |
| 13 | Locking | Row locks, table locks, gap locks |

## Projects

### Project 1: Page-Based Storage
Read/write fixed-size pages to disk.

### Project 2: B-Tree Index
Build a B-tree that supports insert, search, delete.

### Project 3: WAL Implementation
Write-ahead logging with crash recovery.

### Project 4: Mini Database
Combine storage + index + WAL + simple SQL parser.

## Interview Questions Covered
- B-Tree vs LSM Tree — when to use which?
- What is a write-ahead log and why is it needed?
- Explain MVCC in PostgreSQL.
- What happens when you run a SELECT query?
- Why do indexes speed up reads but slow down writes?
- What is a buffer pool and why not just use OS page cache?
- Explain phantom reads and how to prevent them.
- How does a query optimizer choose between index scan vs sequential scan?

## Key Comparisons
- PostgreSQL (B-Tree) vs Cassandra (LSM Tree)
- Redis persistence vs PostgreSQL WAL
- MySQL InnoDB vs PostgreSQL storage engine
- SQLite (embedded) vs PostgreSQL (server)
