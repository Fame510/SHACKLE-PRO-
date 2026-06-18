# SHACKLE SOC2 Compliance Framework

## Trust Services Criteria Mapping

SHACKLE maps to SOC2 Type II Trust Services Criteria (TSC) as defined by AICPA.
This document provides the control mapping for enterprise compliance officers and auditors.

---

## CC Series: Common Criteria (Security)

### CC6.1 — Logical and Physical Access Controls

| Control Activity | SHACKLE Implementation | Evidence |
|-----------------|----------------------|----------|
| Authenticate agent identity before execution | `RegisterRequest` with `agent_id` + `organization_id` | `AuditEntry.agent_id` in append-only logs |
| Restrict tool access by agent role | `GuardConfig` per-agent tool allowlists (future) | Configuration audit trail |
| Terminate sessions on auth failure | Duplicate nonce → `DENY(AUTHENTICATION_FAILED)` | `AuditEntry.deny_reason` |
| Multi-tenant data isolation | `organization_id` namespace segregation | Row-level security in Postgres audit store |

**SOC2 Control:** "The entity implements logical access security measures to protect information assets from unauthorized access."

**SHACKLE Evidence:** Every tool execution is gated through `decide()` with authenticated session identity. No agent executes without a registered, validated session.

---

### CC6.3 — Security Incident Detection

| Control Activity | SHACKLE Implementation | Evidence |
|-----------------|----------------------|----------|
| Detect anomalous agent behavior | Circuit breaker trip on repeat calls, budget exhaustion | `AuditEntry.verdict = DENY` |
| Alert on policy violations | `PostExecNotification` with error signals | Error amplification in `decide()` |
| Real-time incident detection | Daemon-side monitoring of all sessions | `SessionState.circuit_tripped` timestamp |
| Incident correlation across agents | Centralized audit log with session/agent/org IDs | Postgres query across `AuditEntry` |

**SOC2 Control:** "The entity detects and monitors security incidents through automated mechanisms."

**SHACKLE Evidence:** The daemon detects violations at the interpreter level — before the tool executes. Every DENY verdict is a detected incident with full context (who, what, when, why).

---

### CC7.2 — System Monitoring

| Control Activity | SHACKLE Implementation | Evidence |
|-----------------|----------------------|----------|
| Monitor agent health | Heartbeat protocol (every 30s) | `HeartbeatAck.drift_detected` |
| Detect stale/dead sessions | Missed heartbeats → `SESSION_STALE` | `SessionState.status` transitions |
| Track resource consumption | Budget tracking per session/agent/org | `SessionState.budget_spent_usd` |
| Monitor execution latency | `PostExecNotification.duration_ms` | Audit log performance metrics |

**SOC2 Control:** "The entity monitors system operations and detects deviations from expected performance."

**SHACKLE Evidence:** Continuous heartbeat monitoring with drift detection. Budget consumption tracked in real-time. Execution latency recorded for every tool call.

---

### CC7.3 — Incident Response

| Control Activity | SHACKLE Implementation | Evidence |
|-----------------|----------------------|----------|
| Human-in-the-loop intervention | HITL console with Resume/Skip/Abort | `operator_id` in `AuditEntry` |
| Document incident response | Every DENY includes reason code + human-readable description | `AuditEntry.deny_reason` + `AuditEntry.human_readable` |
| Preserve incident evidence | Append-only, cryptographically signed audit log | `AuditEntry.signature` (Ed25519) |
| Chain of custody | Hash-linked audit entries | `AuditEntry.previous_entry_hash` |

**SOC2 Control:** "The entity responds to security incidents and takes corrective action."

**SHACKLE Evidence:** When the circuit breaker trips, execution halts immediately. HITL console provides human override with full audit trail. Operator identity recorded with every manual intervention.

---

### CC8.1 — Change Management

| Control Activity | SHACKLE Implementation | Evidence |
|-----------------|----------------------|----------|
| Version-controlled configuration | `GuardConfig` as versioned protobuf | Configuration schema versioning |
| Backward compatibility | Protocol version negotiation (Section 8 of SPEC.md) | LTS commitment through 2031 |
| Rollback capability | Daemon supports multiple protocol versions simultaneously | `negotiated_protocol` in `RegisterResponse` |
| Audit configuration changes | All configuration changes logged (future) | Configuration audit trail |

**SOC2 Control:** "The entity manages changes to infrastructure, data, and software."

**SHACKLE Evidence:** Protocol version negotiation ensures agents and daemon agree on capabilities. LTS policy guarantees 5-year backward compatibility. Configuration changes are tracked.

---

## A Series: Availability

### A1.2 — Availability Monitoring

| Control Activity | SHACKLE Implementation | Evidence |
|-----------------|----------------------|----------|
| Detect hung/dead agents | Execution timeout guard | `GuardConfig.timeout_seconds` |
| Prevent resource exhaustion | Budget enforcement prevents infinite spend loops | `DENY(BUDGET_EXHAUSTED)` |
| Circuit breaker prevents cascading failure | One agent's loop doesn't consume shared resources | `DENY(CIRCUIT_OPEN)` on parent guard |
| Monitor daemon health | Daemon heartbeat + health check endpoint (future) | Operational metrics |

**SOC2 Control:** "The entity monitors system availability and responds to availability incidents."

**SHACKLE Evidence:** Timeout guard kills hung tool calls. Budget guard prevents infinite loops from consuming all available credits. Circuit breaker isolates failing components.

---

## C Series: Confidentiality

### C1.1 — Confidential Information Protection

| Control Activity | SHACKLE Implementation | Evidence |
|-----------------|----------------------|----------|
| No external telemetry | 100% client-side in library mode | No network calls in V1 |
| Self-hosted daemon | On-premise deployment model | Docker-based Sovereign Proxy |
| Encrypted transport | HMAC-SHA256 on all protocol messages | `Envelope.hmac` |
| Encrypted remote control | E2E encrypted WebSocket for HITL | WSS with Bearer token auth |
| Data-at-rest encryption | Postgres TDE + Redis AOF encryption (future) | Enterprise configuration |

**SOC2 Control:** "The entity protects confidential information throughout its lifecycle."

**SHACKLE Evidence:** Library mode has zero telemetry. Daemon mode runs on-premise. All protocol messages are authenticated. Remote HITL uses encrypted WebSocket.

---

## PI Series: Processing Integrity

### PI1.3 — Processing Integrity Monitoring

| Control Activity | SHACKLE Implementation | Evidence |
|-----------------|----------------------|----------|
| Deterministic enforcement | `decide()` is mathematically provable (properties P1-P9) | Property-based test suite |
| Input validation | `GuardConfig.__post_init__` rejects invalid configs | ValueError on negative budgets |
| Output verification | `PostExecNotification` confirms actual vs estimated cost | `actual_cost_usd` in audit log |
| Error handling | Every DENY includes machine-readable reason code | `DenyReason` enum |

**SOC2 Control:** "The entity processes information accurately, completely, and in a timely manner."

**SHACKLE Evidence:** The decision function is deterministic and property-tested. Every decision is logged with full context. Actual costs are reconciled against estimates.

---

## Audit Log Specifications

### Cryptographic Properties

| Property | Implementation |
|----------|---------------|
| Signature algorithm | Ed25519 |
| Hash algorithm | SHA-256 |
| Chain linking | Each entry contains `previous_entry_hash` |
| Timestamp source | Daemon monotonic clock |
| Rotation | Daily, compressed, archived |
| Retention | Configurable (default: 7 years) |

### Audit Query Examples

```sql
-- All DENY events in last 24 hours
SELECT * FROM audit_entries
WHERE verdict = 'DENY'
  AND timestamp_ns > NOW() - INTERVAL '24 hours'
ORDER BY timestamp_ns DESC;

-- Budget consumption by organization
SELECT organization_id,
       SUM(budget_before_usd - budget_after_usd) as total_spent
FROM audit_entries
GROUP BY organization_id;

-- Repeat call violations by agent
SELECT agent_id, tool_name, COUNT(*) as violations
FROM audit_entries
WHERE deny_reason = 'MAX_REPEAT_CALLS_EXCEEDED'
GROUP BY agent_id, tool_name;

-- HITL operator actions
SELECT operator_id, COUNT(*) as interventions
FROM audit_entries
WHERE operator_id IS NOT NULL
GROUP BY operator_id;

-- Chain integrity verification
SELECT entry_id, previous_entry_hash,
       LAG(entry_id) OVER (ORDER BY timestamp_ns) as expected_previous
FROM audit_entries
WHERE previous_entry_hash != LAG(signature) OVER (ORDER BY timestamp_ns);
```

---

## Compliance Report Template

```markdown
# SHACKLE SOC2 Compliance Report
## Period: [START_DATE] — [END_DATE]

### 1. Executive Summary
- Active Sessions: [COUNT]
- Total Tool Calls: [COUNT]
- DENY Events: [COUNT]
- HITL Interventions: [COUNT]
- Budget Enforced: $[AMOUNT]
- Incidents Detected: [COUNT]

### 2. Control Effectiveness
| TSC | Control | Status | Evidence |
|-----|---------|--------|----------|
| CC6.1 | Access Control | [PASS/FAIL] | [LOG REFERENCE] |
| CC6.3 | Incident Detection | [PASS/FAIL] | [LOG REFERENCE] |
| CC7.2 | Monitoring | [PASS/FAIL] | [LOG REFERENCE] |
| CC7.3 | Incident Response | [PASS/FAIL] | [LOG REFERENCE] |
| CC8.1 | Change Management | [PASS/FAIL] | [LOG REFERENCE] |
| A1.2 | Availability | [PASS/FAIL] | [LOG REFERENCE] |
| C1.1 | Confidentiality | [PASS/FAIL] | [LOG REFERENCE] |
| PI1.3 | Processing Integrity | [PASS/FAIL] | [LOG REFERENCE] |

### 3. Audit Log Integrity
- Chain verified: [YES/NO]
- Signatures valid: [YES/NO]
- Gap analysis: [NONE/DETAILS]

### 4. Recommendations
[N/A or specific items]

### 5. Signatures
- SHACKLE Administrator: _______________
- Compliance Officer: _______________
- Date: _______________
```

---

## Integration with Existing Compliance Frameworks

SHACKLE audit logs can be ingested by:

| SIEM / Compliance Tool | Integration Method |
|------------------------|-------------------|
| Splunk | Postgres JDBC connector → Splunk DB Connect |
| ELK Stack | Logstash JDBC input plugin |
| DataDog | Custom metric from audit log queries |
| Vanta / Drata | API endpoint for automated evidence collection (future) |
| ServiceNow | Webhook on DENY events (future) |

---

*Appendix to SHACKLE Protocol SP/1.0. Last updated 2026-06-18.*
