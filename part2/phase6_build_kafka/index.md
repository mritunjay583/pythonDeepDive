# Phase 6 — Build Kafka

## Why This Phase?
Kafka is the backbone of event-driven architectures. Understanding commit logs, partitioning, and consumer groups is essential for any large-scale system design.

## Roadmap

| # | Topic | What You'll Learn |
|---|-------|-------------------|
| 1 | Why Event Streaming | Problems with request/reply at scale |
| 2 | Commit Log | Append-only, immutable, ordered |
| 3 | Topics & Partitions | Parallelism, ordering guarantees |
| 4 | Producers | Batching, acks, partitioning strategies |
| 5 | Consumers & Consumer Groups | Offset management, rebalancing |
| 6 | Offsets | Committed vs latest, replay |
| 7 | Replication & ISR | In-sync replicas, leader election |
| 8 | Retention & Compaction | Time-based, size-based, log compaction |
| 9 | Exactly-Once Semantics | Idempotent producers, transactions |
| 10 | Kafka Streams | Stream processing basics |
| 11 | Kafka vs Alternatives | RabbitMQ, Pulsar, Redis Streams |

## Project: Build Kafka (Incremental)

### Step 1: Commit Log
Append-only log with segment files.

### Step 2: Topic & Partitions
Multiple partitions per topic, round-robin writes.

### Step 3: Producer & Consumer
Produce messages, consume with offset tracking.

### Step 4: Consumer Groups
Multiple consumers, partition assignment, rebalancing.

### Step 5: Replication
Leader-follower replication per partition.

### Step 6: Retention
Time-based and size-based cleanup.

## Interview Questions Covered
- How does Kafka achieve high throughput?
- What is a consumer group and how does rebalancing work?
- How does Kafka guarantee ordering?
- What happens when a Kafka broker goes down?
- Exactly-once semantics — how does Kafka achieve it?
- Kafka vs RabbitMQ — when to use which?
- How would you design a real-time notification system with Kafka?
- What is log compaction and when would you use it?

## Key Comparisons
- Kafka commit log vs PostgreSQL WAL
- Kafka replication vs Redis replication
- Kafka partitions vs database sharding
- Kafka consumer groups vs Redis pub/sub
- Kafka vs RabbitMQ vs Redis Streams
