# SHACKLE V2: Enterprise Runtime Sovereignty Layer

**Status:** In active development — protocol and tests are real, daemon is being built. Target: Q3 2026.

---

## What's New in V2

SHACKLE V1 is a **single-process decorator** that works great for local development and CLI workflows. V2 adds **distributed state** and **enterprise compliance** for production deployments.

### V1 (Current - Always Free)
- ✅ One decorator (`@Guard`)
- ✅ Works locally, in-process
- ✅ Perfect for development, testing, CLI agents
- ✅ Zero infrastructure required

### V2 (Roadmap Q3 2026)
- 🔧 **Distributed state** (budget shared across serverless functions, Lambda, K8s pods)
- 🔧 **Postgres audit logs** (cryptographically signed with Ed25519)
- 🔧 **Remote HITL** (control headless agents from mobile/web)
- 🔧 **SOC2 compliance pack** (for regulated industries)
- ✅ **Commercial licensing** (available now for early partners)

---

## Components

### `/v2/protocol` ✅ 
- Complete SP/1.0 wire protocol specification
- Protobuf message schemas (shackle.proto, shackle_service.proto)
- Version negotiation, transport bindings
- Python reference stubs + TypeScript client

### `/v2/daemon` 🔧 In Development
- FastAPI server design (Unix socket + WebSocket)
- Redis state engine specification (distributed budgets)
- Postgres audit logger schema (signed, immutable logs)
- Thin client library spec (drop-in for V1 `@Guard`)

### `/v2/compliance` 🔧 In Development
- Commercial license server design
- SOC2 mapping documentation (framework, not certification)
- Audit export API specification
- Enterprise onboarding guide

---

## When to Use V2

**Stick with V1 if:**
- You're developing locally
- Single-process agents
- CLI workflows with human supervision
- Don't need audit trail compliance

**Upgrade to V2 if:**
- Multi-process (serverless, Lambda, K8s)
- Need audit logs for compliance (SOC2, ISO27001, HIPAA)
- Remote agent control (headless APIs)
- Closed-source commercial product (need commercial license)

---

## Quick Start (V1 — Ships Today)

```bash
pip install shackle-guard
```

```python
from shackle import Guard

@Guard(budget=0.25, max_repeat_calls=3, timeout_seconds=180)
def run():
    return crew.kickoff()

run()
```

### V2 (Roadmap — join waitlist)

The V2 daemon with distributed state and Ed25519 audit logging is under active development. Early design:

```python
# Planned V2 API (subject to change)
from v2.daemon.client import ShackleClient, shackled

client = ShackleClient(session_id="my-app", budget_limit=10.00)

@shackled(tool_name="kickoff", estimate_cost=lambda: 0.50, client=client)
def run():
    return crew.kickoff()
```

**Difference (planned):** V2 will track budget across **all processes sharing the same `session_id`**. Perfect for serverless.

---

## Pricing

**V1 (Open-source):** Free for open-source projects (AGPLv3)

**V2 Commercial License:**
- Custom pricing based on team size, deployment scale, and requirements
- Available for startups, enterprises, and framework partnerships
- Includes architecture audit, integration support, and SLA-backed support

**Implementation Service:** $2,500 (V1 or V2 setup + architecture audit)

📧 **Contact for pricing:** docspoc101@gmail.com

---

## Documentation

- **[Protocol Spec](protocol/PROTOCOL.md)** — Wire format, message schemas
- **[Daemon Guide](daemon/README.md)** — Deployment, configuration
- **[Compliance Pack](compliance/AI-Agent-Liability-Shield.pdf)** — SOC2 mapping for CISOs

---

**Built by Dante Bullock, Sovereign Logic**  
No VC. No corporate sponsors. Just code that works.
