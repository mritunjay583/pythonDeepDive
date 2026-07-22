# Phase 5 — Distributed Systems

## Why This Phase?
Single-machine systems hit limits. Every large-scale system (Google, Netflix, Uber) is distributed. This is where senior engineers differentiate themselves.

## Roadmap

| # | Topic | What You'll Learn |
|---|-------|-------------------|
| 1 | Why Distributed Systems | Scalability, availability, partition tolerance |
| 2 | Replication | Leader-follower, multi-leader, leaderless |
| 3 | Consistency Models | Strong, eventual, causal |
| 4 | CAP Theorem | What you actually give up |
| 5 | Leader Election | Bully algorithm, Raft election |
| 6 | Consensus — Raft | Log replication, term, commit |
| 7 | Paxos (Overview) | Why it exists, when to use |
| 8 | Gossip Protocol | Epidemic broadcast, failure detection |
| 9 | Sharding & Partitioning | Range, hash, consistent hashing |
| 10 | Distributed Locks | Redlock, fencing tokens |
| 11 | Vector Clocks & Ordering | Causality in distributed systems |
| 12 | Unique ID Generation | Snowflake, ULID, UUID trade-offs |
| 13 | Failure Modes | Network partitions, split brain, Byzantine |

## Projects

### Project 1: Raft Consensus
Implement leader election + log replication (simplified Raft).

### Project 2: Consistent Hashing
Build a consistent hash ring with virtual nodes.

### Project 3: Distributed KV Store
Combine Raft + sharding into a replicated key-value store.

## Interview Questions Covered
- Explain CAP theorem with real examples.
- How does Raft handle leader failure?
- What is split brain and how to prevent it?
- Consistent hashing — why virtual nodes?
- How do distributed locks work? Why is Redlock controversial?
- What is a vector clock and when do you need it?
- How does Cassandra achieve eventual consistency?
- Design a globally unique ID generator.

## Key Comparisons
- Redis Sentinel vs Raft leader election
- Kafka ISR vs Raft commit
- PostgreSQL streaming replication vs Raft
- DynamoDB (leaderless) vs PostgreSQL (leader-based)
- Snowflake ID vs UUID vs ULID
