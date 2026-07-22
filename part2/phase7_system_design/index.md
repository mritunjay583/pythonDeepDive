# Phase 7 — System Design

## Why This Phase?
System design interviews are the #1 differentiator for senior roles. This phase applies everything from Phase 0-6 to real design problems.

## Approach for Every Design

1. **Requirements** — Functional + Non-functional
2. **Estimations** — Traffic, storage, bandwidth
3. **High-Level Design** — Core components
4. **Deep Dive** — Critical paths, data flow
5. **Scaling** — Bottlenecks and solutions
6. **Failure Cases** — What breaks and how to handle it
7. **Trade-offs** — What you chose and why

## Roadmap

| # | Problem | Key Concepts |
|---|---------|--------------|
| 1 | URL Shortener | Hashing, base62, read-heavy, caching |
| 2 | Rate Limiter | Token bucket, sliding window, distributed |
| 3 | Notification System | Push vs pull, fanout, delivery guarantees |
| 4 | Chat System (WhatsApp) | WebSocket, presence, message ordering |
| 5 | News Feed (Instagram) | Fanout-on-write vs read, ranking |
| 6 | Video Streaming (YouTube) | CDN, encoding, chunking, adaptive bitrate |
| 7 | Ride Sharing (Uber) | Geospatial, matching, real-time |
| 8 | Collaborative Editing (Google Docs) | CRDT, OT, conflict resolution |
| 9 | Search Engine | Inverted index, ranking, crawling |
| 10 | API Gateway | Routing, auth, rate limiting, circuit breaker |
| 11 | Distributed Cache | Consistent hashing, eviction, invalidation |
| 12 | Payment System | Idempotency, saga pattern, reconciliation |
| 13 | Metrics & Monitoring | Time-series DB, aggregation, alerting |

## Interview Format Practice
For each problem, practice:
- 5 min: clarify requirements
- 10 min: high-level design
- 15 min: deep dive into 2-3 components
- 5 min: scaling and trade-offs

## Key Patterns Across Designs
- Read-heavy → Cache + CDN + Read replicas
- Write-heavy → Queue + Async processing + LSM
- Real-time → WebSocket + Pub/Sub + Push
- Consistency → WAL + Raft + Transactions
- Availability → Replication + Failover + Circuit breaker
- Scalability → Sharding + Partitioning + Load balancing
