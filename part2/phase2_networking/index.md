# Phase 2 — Networking

## Why This Phase?
Every distributed system is networked. You need to understand TCP, HTTP, and connection handling to design any real system.

## Roadmap

| # | Topic | What You'll Learn |
|---|-------|-------------------|
| 1 | OSI & TCP/IP Models | Layered network architecture |
| 2 | TCP Deep Dive | 3-way handshake, reliability, ordering |
| 3 | UDP | When unreliable is better |
| 4 | Flow & Congestion Control | TCP window, slow start, backpressure |
| 5 | DNS | Name resolution, caching, TTL |
| 6 | HTTP/1.1 | Request/response, keep-alive, chunked |
| 7 | HTTPS & TLS | Handshake, certificates, encryption |
| 8 | HTTP/2 & HTTP/3 | Multiplexing, streams, QUIC |
| 9 | WebSockets | Full-duplex communication |
| 10 | REST & API Design | Practical API patterns |
| 11 | Reverse Proxy | Nginx, HAProxy patterns |
| 12 | Load Balancing | L4 vs L7, algorithms, health checks |
| 13 | Connection Pooling | Why and how |

## Projects

### Project 1: TCP Echo Server
Build a TCP server handling multiple clients (threads → epoll progression).

### Project 2: HTTP Server
Parse HTTP requests, route, serve static files. No frameworks.

### Project 3: Reverse Proxy
Route requests to multiple backend servers with load balancing.

## Interview Questions Covered
- What happens when you type a URL in the browser?
- TCP vs UDP — when to use which?
- How does TLS handshake work?
- What is head-of-line blocking?
- How does a load balancer decide where to send traffic?
- What is connection pooling and why does it matter?
- How does HTTP/2 multiplexing work?
- What is backpressure in TCP?

## Key Comparisons
- Redis RESP protocol over TCP vs HTTP APIs
- Kafka binary protocol vs REST
- PostgreSQL wire protocol
- gRPC vs REST vs WebSocket
