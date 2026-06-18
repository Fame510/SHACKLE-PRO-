# SHACKLE V2 Architecture

## The Runtime Security Envelope

```
                        ┌─────────────────────────────────┐
                        │        SHACKLE PROTOCOL          │
                        │         SP/1.0 (SPEC.md)         │
                        │                                  │
                        │  ┌────────────────────────────┐  │
                        │  │     Policy Language DSL     │  │
                        │  │  (Future: guard rules as    │  │
                        │  │   versioned configuration)  │  │
                        │  └────────────┬───────────────┘  │
                        │               │                  │
                        │  ┌────────────▼───────────────┐  │
                        │  │   decide(state, call) → V   │  │
                        │  │   ┌─────────────────────┐  │  │
                        │  │   │ Properties P1-P9     │  │  │
                        │  │   │ Deterministic        │  │  │
                        │  │   │ Human-auditable      │  │  │
                        │  │   │ < 200 lines          │  │  │
                        │  │   └─────────────────────┘  │  │
                        │  └────────────┬───────────────┘  │
                        │               │                  │
                        │  ┌────────────▼───────────────┐  │
                        │  │    Message Protocol         │  │
                        │  │  pre_exec / post_exec       │  │
                        │  │  register / heartbeat       │  │
                        │  │  Envelope + HMAC            │  │
                        │  └────────────┬───────────────┘  │
                        │               │                  │
                        │  ┌────────────▼───────────────┐  │
                        │  │   Transport Bindings        │  │
                        │  │  Unix Socket │ gRPC │ WSS   │  │
                        │  └────────────────────────────┘  │
                        └─────────────────────────────────┘
```

---

## Deployment Topology

### Model A: Library Mode (V1 Compatible, Zero Infrastructure)

```
┌──────────────────────────────────────┐
│           Agent Process              │
│                                      │
│  from shackle import Guard           │
│                                      │
│  @Guard(budget=0.25,                 │
│         max_repeat_calls=3)          │
│  def run():                          │
│      return crew.kickoff()           │
│                                      │
│  ┌──────────────────────────────┐    │
│  │  In-Process Guard Layer      │    │
│  │  ┌────────────────────────┐  │    │
│  │  │ litellm.completion hook│  │    │
│  │  │ BaseTool.run hook      │  │    │
│  │  │ decide() in-process    │  │    │
│  │  │ Memory-only state      │  │    │
│  │  │ Terminal HITL console  │  │    │
│  │  └────────────────────────┘  │    │
│  └──────────────────────────────┘    │
│                                      │
│  Use case: Development, debugging,   │
│  single-process agents.              │
│  Limitation: No cross-process state. │
│  State lost on crash.                │
└──────────────────────────────────────┘
```

### Model B: Sidecar Daemon (V2, Persistent State)

```
┌─────────────────────┐          ┌──────────────────────────────┐
│   Agent Process     │          │     SHACKLE Daemon           │
│                     │          │     (shackle user, NOT root) │
│  ┌───────────────┐  │  Unix    │                              │
│  │  Thin Client  │◄─┼─Socket──►│  ┌────────────────────────┐  │
│  │  Shim         │  │ pre_exec │  │  Policy Engine         │  │
│  │               │  │ response │  │  ┌──────────────────┐  │  │
│  │  ~50 lines    │  │ post_exec│  │  │ decide()         │  │  │
│  │  of code      │  │ heartbeat│  │  │ Property-tested  │  │  │
│  └───────────────┘  │          │  │  │ Deterministic    │  │  │
│                     │          │  │  └──────────────────┘  │  │
│  CrewAI / LangGraph │          │  │                        │  │
│  / AutoGen agents   │          │  │  State Engine          │  │
│                     │          │  │  ┌──────────────────┐  │  │
└─────────────────────┘          │  │  │ Budgets          │  │  │
                                 │  │  │ Counters         │  │  │
┌─────────────────────┐          │  │  │ Circuit Breakers │  │  │
│   HITL Console      │          │  │  │ Time Windows     │  │  │
│                     │  Unix    │  │  └──────────────────┘  │  │
│  Terminal / Web /   │◄─Socket─►│  │                        │  │
│  Mobile control     │          │  │  Audit Logger          │  │
│                     │          │  │  ┌──────────────────┐  │  │
│  Resume / Skip /    │          │  │  │ Append-only file │  │  │
│  Abort / Override   │          │  │  │ Ed25519 signed   │  │  │
│                     │          │  │  │ Hash-chained     │  │  │
└─────────────────────┘          │  │  │ Daily rotation   │  │  │
                                 │  │  └──────────────────┘  │  │
                                 │  └────────────────────────┘  │
                                 │                              │
                                 │  Storage Backends            │
                                 │  ┌────────────────────────┐  │
                                 │  │ SQLite (default)       │  │
                                 │  │ Postgres (enterprise)  │  │
                                 │  │ Redis (state sync)     │  │
                                 │  └────────────────────────┘  │
                                 └──────────────────────────────┘

  File Permissions:
    /var/run/shackle.sock   0660  shackle:agents
    /var/log/shackle/audit  0640  shackle:shackle  (O_APPEND only)
    /etc/shackle/config.yaml 0640  root:shackle
```

### Model C: Distributed Cluster (V2 Enterprise, Multi-Process)

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ Agent A  │   │ Agent B  │   │ Agent C  │   │ Agent D  │
│ (Lambda) │   │ (K8s Pod)│   │ (EC2)    │   │ (local)  │
└────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘
     │              │              │              │
     └──────────────┴──────────────┴──────────────┘
                           │
                    gRPC + TLS 1.3
                    (mTLS in production)
                           │
              ┌────────────┴────────────┐
              │   SHACKLE Daemon        │
              │   Cluster               │
              │                         │
              │  ┌───────────────────┐  │
              │  │ Load Balancer     │  │
              │  │ (session affinity │  │
              │  │  by session_id)   │  │
              │  └───────┬───────────┘  │
              │          │              │
              │  ┌───────▼───────────┐  │
              │  │ Daemon Instance 1 │  │
              │  │ Daemon Instance 2 │  │
              │  │ Daemon Instance N │  │
              │  └───────┬───────────┘  │
              │          │              │
              │  ┌───────▼───────────┐  │
              │  │ Redis Cluster     │  │
              │  │ (State Sync)      │  │
              │  │                   │  │
              │  │ Hash slot per     │  │
              │  │ session_id for    │  │
              │  │ linearizable      │  │
              │  │ budget checks     │  │
              │  └───────┬───────────┘  │
              │          │              │
              │  ┌───────▼───────────┐  │
              │  │ Postgres          │  │
              │  │ (Audit Log)       │  │
              │  │                   │  │
              │  │ Partitioned by    │  │
              │  │ organization_id   │  │
              │  │ + timestamp       │  │
              │  └───────────────────┘  │
              └─────────────────────────┘
```

---

## Data Flow: One Tool Execution

```
Agent                    Daemon                    Storage
  │                        │                         │
  │  1. PRE_EXEC           │                         │
  │  ┌──────────────────┐  │                         │
  │  │ session_id        │  │                         │
  │  │ call_number: 42   │  │                         │
  │  │ tool: "web_search"│  │                         │
  │  │ params_hash: 0x.. │  │                         │
  │  │ estimated: $0.002 │  │                         │
  │  │ nonce: 987654321  │  │                         │
  │  └──────────────────┘  │                         │
  │ ──────────────────────►│                         │
  │                        │  2. Load state          │
  │                        │ ──────────────────────► │
  │                        │ ◄────────────────────── │
  │                        │                         │
  │                        │  3. decide(state, call) │
  │                        │  ┌───────────────────┐  │
  │                        │  │ Circuit? ✓        │  │
  │                        │  │ Budget?  ✓        │  │
  │                        │  │ Repeat?  ✓        │  │
  │                        │  │ Window?  ✓        │  │
  │                        │  │ Nonce?   ✓        │  │
  │                        │  │                    │  │
  │                        │  │ → ALLOW           │  │
  │                        │  └───────────────────┘  │
  │                        │                         │
  │  4. PRE_EXEC_RESPONSE  │                         │
  │ ◄──────────────────────│                         │
  │  ┌──────────────────┐  │                         │
  │  │ verdict: ALLOW    │  │                         │
  │  │ budget_left: $0.48│  │                         │
  │  │ repeat_count: 0   │  │                         │
  │  └──────────────────┘  │                         │
  │                        │                         │
  │  5. [Execute tool]     │                         │
  │  ═══════════════════   │                         │
  │                        │                         │
  │  6. POST_EXEC          │                         │
  │  ┌──────────────────┐  │                         │
  │  │ call_number: 42   │  │                         │
  │  │ actual_cost: $0.01│  │                         │
  │  │ success: true     │  │                         │
  │  │ duration: 234ms   │  │                         │
  │  │ tokens_in: 1200   │  │                         │
  │  │ tokens_out: 300   │  │                         │
  │  └──────────────────┘  │                         │
  │ ──────────────────────►│                         │
  │                        │  7. Write audit entry   │
  │                        │ ──────────────────────► │
  │                        │  8. Update state        │
  │                        │ ──────────────────────► │
  │                        │                         │
  │                        │  9. Heartbeat (30s)     │
  │                        │ ◄──────────────────────►│
  │                        │    State sync check     │
```

---

## Guard Tree: Hierarchical Composition

```
Organization: $500/month
│
├── Agent A: Development ($100)
│   ├── Task 1: Research ($20)
│   │   ├── web_search (repeat ≤ 3)
│   │   └── read_page (repeat ≤ 2)
│   └── Task 2: Analysis ($40)
│       ├── run_analysis (repeat ≤ 1)
│       └── write_report (repeat ≤ 2)
│
├── Agent B: Production ($300)
│   ├── Pipeline 1 ($150)
│   │   ├── etl_extract (repeat ≤ 5)
│   │   └── etl_transform (repeat ≤ 3)
│   └── Pipeline 2 ($150)
│       ├── api_call (repeat ≤ 2, window: 10/min)
│       └── store_result (repeat ≤ 1)
│
└── Agent C: QA ($100)
    ├── test_suite ($50)
    └── report ($50)

Rules:
- Child budgets draw from parent. Child exhaustion → parent not affected.
- Parent exhaustion → ALL children halt immediately.
- Sibling budgets are independent. Agent B can't burn Agent A's budget.
- Circuit breaker propagation: if Pipeline 1 trips, Agent B reports it.
  Agent B does NOT trip unless its own budget is exhausted.
```

---

## Performance Budget

```
Operation                    Target     Critical?
─────────────────────────    ────────   ────────
pre_exec (Unix socket)       < 5ms      YES
post_exec (fire-and-forget)  < 1ms      NO
register                     < 50ms     NO
heartbeat                    < 2ms      NO
decide() function            < 0.1ms    YES (inlined)
audit log write              < 2ms      YES (non-blocking buffer)

Total overhead per tool call: < 7ms

Design decisions for performance:
1. decide() is a pure function — no I/O, no allocations (reuse objects)
2. Unix socket with length-prefixed protobuf — no HTTP overhead
3. Audit log uses O_APPEND + write buffer — no seek, no fsync on every write
4. Redis for state with pipelined reads — one round trip, not N
5. Connection pooling + keepalive — no TCP handshake per call

If < 5ms is unachievable in Python:
  → Rust rewrite of decide() + socket handler via pyo3
  → Python thin client stays, Rust handles the hot path
```

---

## Failure Modes & Recovery

| Failure | Detection | Recovery |
|---------|-----------|----------|
| Daemon crash | Heartbeat timeout (3x missed) | Agent reverts to library mode (local state, no persistence) |
| Agent crash | Heartbeat timeout → STALE | Daemon persists state; agent resumes with same session_id |
| Redis partition | Read timeout → fallback to local | Library mode with stale-state warning; sync on reconnect |
| Postgres down | Write buffer fills → backpressure | Audit log buffers in memory (ring buffer, configurable size) |
| Budget drift | Heartbeat comparison | Daemon overrides agent's local view; agent adjusts |
| Nonce exhaustion | 2^64 nonces is 584 years at 1B calls/sec | Not a practical concern |
| Disk full | Audit log write fails | Alert; daemon continues enforcing policy (audit gap logged) |

---

## Security Boundary Hardening

```
TRUST BOUNDARY
═══════════════════════════════════════════════════
  UNTRUSTED AGENT PROCESS
  - Same host, different UID
  - Can only connect to Unix socket
  - Cannot read daemon files (different user)
  - Cannot write to audit log (different user, no append permission)
  - Can flood socket → rate limiting per session
  - Can send malformed messages → forked parser process
───────────────────────────────────────────────────
  TRUSTED DAEMON
  - Runs as 'shackle' user
  - Owns /var/run/shackle.sock (0660 shackle:agents)
  - Owns /var/log/shackle/ (0700 shackle:shackle)
  - Owns /etc/shackle/config.yaml (0640 root:shackle)
  - Root privilege NEVER required for operation
  - systemd unit handles socket creation + permissions
───────────────────────────────────────────────────
  TRUSTED STORAGE
  - Postgres with TLS + certificate auth
  - Redis with AUTH password
  - Both on private network, not exposed to agents
```

---

## Implementation Roadmap

```
Phase 1: Foundation (Current)
  ✅ SPEC.md — Protocol specification
  ✅ shackle.proto — Wire format
  ✅ decide.py — Core decision function
  ✅ test_decide_properties.py — Property-based tests
  ✅ SOC2-MAPPING.md — Compliance framework
  ⏳ Daemon scaffold (Python, asyncio, Unix socket)

Phase 2: Core Daemon
  ⏳ Unix socket server with protobuf framing
  ⏳ SQLite state backend
  ⏳ Append-only audit log with Ed25519 signing
  ⏳ Heartbeat protocol
  ⏳ CLI management tool (shacklectl)

Phase 3: Enterprise
  ⏳ Postgres audit log backend
  ⏳ Redis state backend with linearizable budget checks
  ⏳ gRPC transport
  ⏳ Multi-tenant isolation
  ⏳ License key validation
  ⏳ WSS remote HITL console

Phase 4: Ecosystem
  ⏳ TypeScript client library (Node.js agents)
  ⏳ Rust reference daemon (performance-critical path)
  ⏳ Kubernetes operator
  ⏳ SOC2 compliance report generator
  ⏳ Terraform / Pulumi deployment modules
```

---

*SHACKLE V2 Architecture. Sovereign Logic, 2026.*
