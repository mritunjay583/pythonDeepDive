# Phase 3 — Build Redis

## Why This Phase?
Redis combines everything from Phase 0-2: memory management, event loop, networking, data structures. Building it solidifies all prior knowledge.

## Roadmap

| # | Topic | What You'll Learn |
|---|-------|-------------------|
| 1 | Why In-Memory Storage | Speed, use cases, limitations |
| 2 | Hash Tables | Open addressing, chaining, load factor |
| 3 | RESP Protocol | Redis serialization protocol |
| 4 | Event Loop & I/O | Single-threaded multiplexing |
| 5 | Core Commands | GET, SET, DEL, EXPIRE |
| 6 | Data Structures | Strings, Lists, Sets, Sorted Sets, Hashes |
| 7 | Expiration & Eviction | TTL, lazy vs active expiry, LRU/LFU |
| 8 | Persistence — RDB | Point-in-time snapshots |
| 9 | Persistence — AOF | Append-only file, fsync strategies |
| 10 | Replication | Leader-follower, sync/async |
| 11 | Sentinel | Failover, monitoring |
| 12 | Cluster | Sharding, hash slots, gossip |

## Project: Build Redis (Incremental)

### Step 1: In-Memory KV Store
Hash table with GET/SET/DEL.

### Step 2: RESP Protocol Parser
Parse and serialize Redis protocol.

### Step 3: TCP Server with Event Loop
Handle multiple clients, single-threaded.

### Step 4: Expiration
TTL support with lazy + active expiry.

### Step 5: Persistence
RDB snapshots + AOF logging.

### Step 6: Replication
Leader-follower with command propagation.

## Interview Questions Covered
- Why is Redis single-threaded yet fast?
- How does Redis handle expiration?
- RDB vs AOF — trade-offs?
- How does Redis Cluster shard data?
- What happens during a failover with Sentinel?
- How would you design a rate limiter with Redis?
- What is cache stampede and how to prevent it?

## Key Comparisons
- Redis vs Memcached (threading model)
- Redis AOF vs PostgreSQL WAL
- Redis replication vs Kafka replication
- Redis Cluster vs Consistent Hashing
