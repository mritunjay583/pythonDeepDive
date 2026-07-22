# Phase 8 — Linux & Kubernetes

## Why This Phase?
Everything you build runs on Linux in containers orchestrated by Kubernetes. Understanding the infra layer completes the picture.

## Roadmap

| # | Topic | What You'll Learn |
|---|-------|-------------------|
| 1 | Linux Process Model | fork, exec, zombie, orphan |
| 2 | Namespaces | Isolation — PID, network, mount, user |
| 3 | Cgroups | Resource limits — CPU, memory, I/O |
| 4 | Containers from Scratch | Namespace + cgroup + chroot = container |
| 5 | Docker Internals | Images, layers, overlay filesystem |
| 6 | Container Networking | Bridge, veth pairs, iptables |
| 7 | Kubernetes Architecture | Control plane, kubelet, etcd |
| 8 | Pods & Containers | Scheduling, lifecycle, probes |
| 9 | ReplicaSets & Deployments | Scaling, rolling updates, rollback |
| 10 | Services & Networking | ClusterIP, NodePort, LoadBalancer |
| 11 | Ingress | Routing external traffic |
| 12 | Storage | PV, PVC, StorageClass |
| 13 | Service Mesh | Sidecar, Istio/Envoy basics |
| 14 | Observability | Logs, metrics, tracing |

## Projects

### Project 1: Container from Scratch
Use namespaces + cgroups to isolate a process (Linux only).

### Project 2: Dockerize All Previous Projects
Package Redis clone, HTTP server, KV store in containers.

### Project 3: Kubernetes Deployment
Deploy your distributed KV store on K8s with:
- Deployments + ReplicaSets
- Services for internal communication
- Ingress for external access
- Health checks and probes

### Project 4: Helm Chart
Package your deployment as a reusable Helm chart.

## Interview Questions Covered
- What is a container at the Linux level?
- How do namespaces provide isolation?
- What is a cgroup and why does K8s need it?
- How does Kubernetes networking work?
- What happens when you run `kubectl apply`?
- How does a rolling update work?
- What is a sidecar pattern?
- How would you debug a pod stuck in CrashLoopBackOff?

## Key Comparisons
- Docker container vs VM
- Kubernetes Services vs traditional load balancers
- etcd (Raft) vs ZooKeeper (ZAB)
- Docker networking vs Kubernetes networking
- Linux cgroups vs JVM memory limits
