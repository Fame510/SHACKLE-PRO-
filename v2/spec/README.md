# SHACKLE V2 — Runtime Sovereignty Layer

> **SP/1.0 Protocol • Sidecar Daemon • Distributed State • SOC2 Compliance**
>
> The protocol that turns SHACKLE from a Python library into a runtime security standard.

---

## What This Is

SHACKLE V2 is the enterprise-grade architecture behind the V1 decorator. While V1 is the open-source distribution bait (a Python decorator anyone can use today), V2 is the protocol, daemon, and compliance framework that makes SHACKLE a defensible business.

## What's Built Here

| Artifact | Purpose | Status |
|----------|---------|--------|
| [`SPEC.md`](./SPEC.md) | Protocol specification (SP/1.0) — the canonical definition | ✅ Complete |
| [`proto/shackle.proto`](./proto/shackle.proto) | Protobuf IDL — language-agnostic wire format | ✅ Complete |
| [`src/decide.py`](./src/decide.py) | Core decision function — human-auditable, <200 lines | ✅ Complete |
| [`tests/test_decide_properties.py`](./tests/test_decide_properties.py) | Property-based tests — mathematical proof of correctness | ✅ Complete |
| [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) | Architecture diagrams, deployment models, failure modes | ✅ Complete |
| [`docs/SOC2-MAPPING.md`](./docs/SOC2-MAPPING.md) | SOC2 Trust Services Criteria mapping + audit framework | ✅ Complete |
| [`landing-redesign/index.html`](./landing-redesign/index.html) | Brutalist defense-grade landing page | ✅ Complete |

## Architecture at a Glance

```
Agent Process              SHACKLE Daemon              Storage
     │                          │                         │
     │  PRE_EXEC ──────────────►│  decide(state, call)    │
     │                          │  ┌──────────────────┐   │
     │                          │  │ Circuit check    │   │
     │                          │  │ Budget check     │   │
     │                          │  │ Repeat check     │   │
     │                          │  │ Window check     │   │
     │                          │  │ Nonce check      │   │
     │                          │  │                  │   │
     │                          │  │ → ALLOW/DENY/HITL│   │
     │                          │  └──────────────────┘   │
     │◄─ PRE_EXEC_RESPONSE ─────│                         │
     │                          │                         │
     │  [execute tool]          │                         │
     │                          │                         │
     │  POST_EXEC ─────────────►│  Write audit ──────────►│
     │                          │  Update state ─────────►│
```

## The Decisive Function

The core of SHACKLE is `decide(state, call) → Verdict` — a pure function under 200 lines that answers one question:

> *Should this agent be allowed to execute this tool with these parameters at this moment?*

It is:
- **Deterministic** — same input → same output, always
- **Property-tested** — 9 mathematical properties proven with Hypothesis
- **Human-auditable** — readable in under 10 minutes by any engineer
- **Side-effect-free** — doesn't mutate state; the daemon does that

## Protocol Principles

1. **Daemon as authority** — sole source of truth for time, state, and verdicts
2. **Append-only audit** — every decision cryptographically logged (Ed25519)
3. **Graceful degradation** — agents function without daemon in library mode
4. **Protocol > implementation** — spec outlives any single language binding
5. **Decouple mechanism from policy** — intercept anywhere, enforce centrally

## Enterprise Differentiators (vs V1)

| Dimension | V1 (Library) | V2 (Daemon) |
|-----------|-------------|-------------|
| State | Memory-only, lost on crash | Redis + Postgres, survives crashes |
| Multi-process | No shared budget | Distributed budget across serverless/K8s |
| Audit | None | Append-only, cryptographically signed, SOC2-ready |
| HITL | Terminal only | Web/mobile remote console |
| Trust boundary | Same process as agent | Separate daemon, different user |
| Compliance | Self-attested | SOC2 TSC mapped, auditor-ready |
| Licensing | AGPLv3 only | Commercial license available |

## Performance SLA

```
pre_exec (Unix socket):  < 5ms  ⚡ Critical
decide() function:       < 0.1ms ⚡ Critical (inlined)
post_exec:               < 1ms  (fire-and-forget)
audit log write:         < 2ms  (non-blocking buffer)
─────────────────────────────────
Total overhead:          < 7ms  per tool call
```

If Python can't hit these targets, the hot path (`decide()` + socket handler) gets rewritten in Rust via pyo3.

## Business Model

```
Layer 1: Open Source (AGPLv3)
  └─ V1 decorator — free, forever
  └─ Distribution bait, adoption driver

Layer 2: Implementation + Audit ($2,500)
  └─ Architecture review + custom config + integration
  └─ 30-day guarantee

Layer 3: Enterprise Sovereign (Custom pricing)
  └─ V2 sidecar daemon + distributed state
  └─ SOC2 compliance pack + signed audit logs
  └─ Commercial license (no copyleft obligations)
  └─ SLA-backed support
```

## Next Steps

- [ ] Build Python daemon scaffold (asyncio, Unix socket)
- [ ] Implement SQLite state backend
- [ ] Implement append-only audit log with Ed25519 signing
- [ ] Build `shacklectl` CLI management tool
- [ ] Build TypeScript thin client (Node.js agent support)
- [ ] Performance benchmark: prove <5ms pre_exec overhead
- [ ] SOC2 compliance report generator

---

*Sovereign Logic, 2026. AGPLv3. Contact: docspoc101@gmail.com*
