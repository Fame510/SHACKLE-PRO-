# SHACKLE V2 Architecture

## Overview

SHACKLE is a sovereign governance daemon for tool execution control. It provides budget tracking, repeat call detection, and human-in-the-loop intervention for AI agent tool calls.

## Design Principles

1. **Sovereign**: Run locally, own your data, no external dependencies
2. **Fast**: <5ms latency for authorization checks
3. **Reliable**: Fail-open with fallback mode when daemon unavailable
4. **Auditable**: Cryptographically signed append-only logs
5. **Simple**: Unix socket + HTTP/WebSocket, easy to integrate

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     AI Agent / Tool Client                   │
│                                                               │
│  @shackled decorator wraps tool functions                    │
│  ├─ Auto-detect daemon availability                          │
│  ├─ pre_exec: Check before execution                         │
│  ├─ Execute tool if ALLOW                                    │
│  └─ post_exec: Log results                                   │
└────────────────────────┬────────────────────────────────────┘
                         │ Unix Socket (/tmp/shackle.sock)
                         │ HTTP/JSON protocol
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Daemon (daemon.py)                 │
│                                                               │
│  Endpoints:                                                   │
│  ├─ POST /pre_exec    → Authorization check                  │
│  ├─ POST /post_exec   → Execution logging                    │
│  ├─ GET  /hitl_wait   → Block until HITL response            │
│  ├─ POST /hitl_response → Human decision input               │
│  └─ WS   /ws          → Real-time HITL notifications         │
│                                                               │
│  Logic:                                                       │
│  ├─ Check budget (Redis)                                     │
│  ├─ Detect repeat calls (Redis)                              │
│  ├─ Trigger HITL if needed                                   │
│  └─ Return ALLOW/DENY/HITL                                   │
└────────┬───────────────────────────┬────────────────────────┘
         │                           │
         ▼                           ▼
┌──────────────────┐      ┌──────────────────────────┐
│  Redis (state.py)│      │  Postgres (audit.py)     │
│                  │      │                          │
│  Session state:  │      │  Append-only logs:       │
│  ├─ Budgets      │      │  ├─ Decision logs        │
│  ├─ Spent $      │      │  ├─ Execution logs       │
│  └─ Call history │      │  └─ Ed25519 signatures   │
│                  │      │                          │
│  TTL: 24h/1h     │      │  Indexed by:             │
│  In-memory       │      │  ├─ Timestamp            │
│                  │      │  ├─ Session ID           │
│                  │      │  └─ Tool name            │
└──────────────────┘      └──────────────────────────┘
```

## Component Details

### 1. Client (client.py)

**Responsibilities:**
- Wrap tool functions with `@shackled` decorator
- Auto-detect daemon availability
- Fallback to local execution if daemon down
- Handle HITL blocking wait

**Flow:**
```python
@shackled(tool_name="exec", estimate_cost=lambda cmd: 0.01)
async def execute_command(cmd: str):
    # 1. Pre-exec check (daemon or fallback)
    # 2. Execute if ALLOW
    # 3. Post-exec logging
    # 4. Return result
```

**Key Features:**
- Transparent: Just add decorator
- Non-blocking: Async/await friendly
- Resilient: Fallback mode if daemon unavailable
- Zero-config: Uses environment variables

### 2. Daemon (daemon.py)

**Responsibilities:**
- Receive pre_exec/post_exec requests
- Coordinate state and audit components
- Manage HITL flow
- WebSocket notifications

**Pre-execution Logic:**
```
1. Check budget in Redis
   └─ DENY if exceeded → return immediately

2. Check repeat call pattern in Redis
   └─ If >3 repeats → Trigger HITL

3. Record call in Redis history

4. Return ALLOW/DENY/HITL
```

**HITL Flow:**
```
1. Client requests pre_exec
2. Daemon detects trigger condition (e.g., repeats)
3. Daemon creates hitl_token, stores Future
4. Daemon broadcasts WebSocket notification
5. Client blocks on /hitl_wait/{token}
6. Human responds via WebSocket or POST
7. Daemon resolves Future
8. Client receives final decision
```

**Technology:**
- FastAPI for HTTP endpoints
- Uvicorn with Unix socket support
- WebSocket for real-time HITL
- Async/await for non-blocking I/O

### 3. State Manager (state.py)

**Responsibilities:**
- Budget tracking per session
- Repeat call detection
- Session state management

**Redis Schema:**
```
shackle:budget:{session_id}           → Float (spent amount)
shackle:budget:{session_id}:limit     → Float (budget limit)
shackle:calls:{session_id}            → List (call history)
```

**Budget Flow:**
```
check_budget(session_id, cost):
  spent = GET shackle:budget:{session_id}
  limit = GET shackle:budget:{session_id}:limit
  return (spent + cost) <= limit

update_budget(session_id, cost):
  INCRBYFLOAT shackle:budget:{session_id} cost
  EXPIRE shackle:budget:{session_id} 86400
```

**Repeat Detection:**
```
record_call(session_id, tool, params):
  hash = SHA256(tool + params)
  call = {tool, hash, timestamp}
  LPUSH shackle:calls:{session_id} call
  LTRIM shackle:calls:{session_id} 0 99  (keep last 100)

check_repeat(session_id, tool, params):
  hash = SHA256(tool + params)
  history = LRANGE shackle:calls:{session_id} 0 19
  return hash in history
```

**TTL Strategy:**
- Budgets: 24 hours (reset daily)
- Call history: 1 hour (recent repeats)
- Limits: 24 hours (aligned with budget)

### 4. Audit Logger (audit.py)

**Responsibilities:**
- Append-only logging
- Cryptographic signatures (Ed25519)
- Integrity verification
- Query interface

**Schema:**
```sql
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    event_type VARCHAR(50) NOT NULL,     -- 'decision' or 'execution'
    session_id VARCHAR(255) NOT NULL,
    tool_name VARCHAR(255),
    decision VARCHAR(20),                 -- ALLOW/DENY/HITL
    reason TEXT,
    parameters JSONB,
    result JSONB,
    error TEXT,
    cost DECIMAL(10, 6),
    execution_time_ms DECIMAL(10, 2),
    signature TEXT NOT NULL,              -- Ed25519 hex
    metadata JSONB
);
```

**Signature Process:**
```
1. Create canonical JSON of record
2. Sign with Ed25519 private key
3. Store hex-encoded signature
4. Verification uses public key
```

**Why Ed25519:**
- Fast: 64-byte signatures, quick verify
- Secure: 128-bit security level
- Simple: No certificate chains
- Deterministic: Same input = same signature

**Query Patterns:**
```sql
-- Recent logs for session
SELECT * FROM audit_log 
WHERE session_id = ? 
ORDER BY timestamp DESC 
LIMIT 100;

-- Cost analysis
SELECT tool_name, SUM(cost), COUNT(*) 
FROM audit_log 
WHERE event_type = 'execution' 
GROUP BY tool_name;

-- Decision breakdown
SELECT decision, COUNT(*) 
FROM audit_log 
WHERE event_type = 'decision' 
GROUP BY decision;
```

## Protocol Specification

### Pre-execution Request

```http
POST /pre_exec HTTP/1.1
Content-Type: application/json

{
  "session_id": "user_session_123",
  "tool_name": "exec",
  "parameters": {
    "command": "ls -la"
  },
  "estimated_cost": 0.001,
  "context": {
    "agent_id": "agent_alpha",
    "task_id": "task_456"
  }
}
```

### Pre-execution Response

```json
{
  "decision": "ALLOW",
  "reason": "Passed all checks"
}
```

or

```json
{
  "decision": "DENY",
  "reason": "Budget exceeded"
}
```

or

```json
{
  "decision": "HITL",
  "reason": "Repeat call detected (4 times)",
  "hitl_token": "hitl_user_session_123_1234567890.123"
}
```

### Post-execution Request

```http
POST /post_exec HTTP/1.1
Content-Type: application/json

{
  "session_id": "user_session_123",
  "tool_name": "exec",
  "parameters": {
    "command": "ls -la"
  },
  "result": {
    "output": "total 48\ndrwxr-xr-x ...",
    "exit_code": 0
  },
  "error": null,
  "actual_cost": 0.0012,
  "execution_time_ms": 45.3
}
```

### Post-execution Response

```json
{
  "status": "ACK",
  "message": "Execution logged"
}
```

### HITL Wait (Blocking)

```http
GET /hitl_wait/hitl_user_session_123_1234567890.123 HTTP/1.1
```

Blocks up to 5 minutes, returns:

```json
{
  "decision": "ALLOW",
  "notes": "User approved after review"
}
```

### HITL Response Submission

```http
POST /hitl_response HTTP/1.1
Content-Type: application/json

{
  "hitl_token": "hitl_user_session_123_1234567890.123",
  "decision": "ALLOW",
  "notes": "Reviewed and approved"
}
```

### WebSocket Protocol

Connect: `ws://localhost/ws` (via Unix socket)

**Server → Client (HITL Request):**
```json
{
  "type": "hitl_request",
  "data": {
    "hitl_token": "hitl_...",
    "session_id": "user_session_123",
    "tool_name": "exec",
    "parameters": {"command": "rm -rf /"},
    "reason": "Dangerous command detected",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

**Client → Server (HITL Response):**
```json
{
  "type": "hitl_response",
  "data": {
    "hitl_token": "hitl_...",
    "decision": "DENY",
    "notes": "Too dangerous"
  }
}
```

## Performance Characteristics

### Latency

- **Pre-exec (ALLOW)**: 2-5ms
  - Redis lookup: 1-2ms
  - Hash computation: <1ms
  - Response: <1ms

- **Pre-exec (HITL)**: 5-300,000ms (5min timeout)
  - Depends on human response time
  - Async - doesn't block daemon

- **Post-exec**: 3-10ms
  - Redis update: 1-2ms
  - Postgres insert: 2-5ms
  - Signature: <1ms

### Throughput

- **Daemon**: 1000+ req/sec (single instance)
- **Redis**: 10,000+ ops/sec
- **Postgres**: 500+ inserts/sec

### Storage

- **Redis**: ~1KB per session (budget + 100 calls)
- **Postgres**: ~500 bytes per log entry
- **Example**: 1M tool calls = ~500MB audit log

## Security Considerations

### 1. Unix Socket Permissions

Default: `0666` (world-readable/writable)

For production:
```bash
chmod 0600 /tmp/shackle.sock
chown agent:agent /tmp/shackle.sock
```

### 2. Signing Key Protection

Current: Generated on startup (in-memory)

For production:
```bash
# Generate key once
python -c "from nacl.signing import SigningKey; print(SigningKey.generate().encode().hex())" > key.txt

# Load from secure storage
export SHACKLE_SIGNING_KEY=$(cat key.txt)
```

### 3. Database Credentials

Current: Hardcoded in docker-compose

For production:
```yaml
environment:
  POSTGRES_PASSWORD_FILE: /run/secrets/db_password
secrets:
  db_password:
    external: true
```

### 4. Budget Enforcement

Current: Soft limits (advisory)

For production:
- Add authentication layer
- Enforce at network level
- Rate limiting per user/session

## Deployment Patterns

### 1. Local Development

```bash
# Start infra
docker-compose up -d redis postgres

# Run daemon locally
python daemon.py
```

### 2. Docker Compose (All-in-one)

```bash
# Start everything
docker-compose up -d

# Client connects via socket volume
```

### 3. Kubernetes

```yaml
apiVersion: v1
kind: Service
metadata:
  name: shackle-daemon
spec:
  ports:
  - port: 8000
    targetPort: 8000

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: shackle-daemon
spec:
  replicas: 3  # Scale horizontally
  template:
    spec:
      containers:
      - name: daemon
        image: shackle:v2
        env:
        - name: REDIS_URL
          value: redis://redis-service:6379/0
        - name: POSTGRES_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
```

### 4. Serverless (Lambda-like)

Not recommended - daemon requires persistent state in Redis/Postgres.

Alternative: Use client fallback mode, daemon on separate VM.

## Extension Points

### 1. Custom Decision Logic

Extend `daemon.py`:

```python
async def custom_check(req: PreExecRequest) -> bool:
    # Your custom logic
    if req.tool_name == "dangerous_tool":
        return False
    return True

# In pre_exec:
if not await custom_check(req):
    return PreExecResponse(decision="DENY", reason="Custom rule")
```

### 2. Additional Trigger Conditions

Extend `state.py`:

```python
async def check_time_of_day(session_id: str) -> bool:
    """Block operations during off-hours"""
    hour = datetime.now().hour
    return 9 <= hour <= 17

# In daemon:
if not await state_manager.check_time_of_day(req.session_id):
    return PreExecResponse(decision="HITL", reason="Outside business hours")
```

### 3. Cost Estimation Hooks

Extend `client.py`:

```python
def estimate_exec_cost(command: str) -> float:
    """Estimate cost based on command complexity"""
    if "rm" in command or "delete" in command:
        return 1.0  # High cost for dangerous ops
    return 0.001

@shackled(tool_name="exec", estimate_cost=estimate_exec_cost)
async def execute_command(cmd: str):
    ...
```

### 4. Custom Audit Metadata

Extend `audit.py`:

```python
await audit_logger.log_execution(
    session_id=session_id,
    tool_name=tool_name,
    parameters=parameters,
    metadata={
        "user_ip": "192.168.1.1",
        "api_version": "v2",
        "request_id": "req_123"
    }
)
```

## Monitoring & Observability

### Health Checks

```bash
# Daemon health
curl --unix-socket /tmp/shackle.sock http://localhost/health

# Redis health
redis-cli -h localhost -p 6379 PING

# Postgres health
pg_isready -h localhost -p 5432 -U shackle
```

### Metrics to Track

1. **Daemon**:
   - Request rate (pre_exec, post_exec)
   - Decision distribution (ALLOW/DENY/HITL)
   - HITL response times
   - Error rate

2. **State (Redis)**:
   - Memory usage
   - Key count
   - Hit/miss ratio

3. **Audit (Postgres)**:
   - Log volume (entries/sec)
   - Table size
   - Query latency

### Logging

Structured JSON logs:

```python
import structlog

logger = structlog.get_logger()
logger.info("pre_exec_decision", 
            session_id=session_id,
            tool_name=tool_name,
            decision=decision,
            duration_ms=duration)
```

### Alerting

Key alerts:
- Daemon down (health check fail)
- Redis/Postgres connection lost
- HITL queue backing up (>10 pending)
- Budget exceeded rate spike
- Signature verification failures

## Roadmap

### V2.1 (Next)
- [ ] gRPC support (faster than HTTP)
- [ ] Prometheus metrics endpoint
- [ ] Budget alerts (webhooks)
- [ ] CLI improvements (TUI mode)

### V2.2 (Future)
- [ ] Multi-tenancy (user isolation)
- [ ] Policy DSL (YAML rules)
- [ ] ML-based anomaly detection
- [ ] Distributed tracing (OpenTelemetry)

### V3.0 (Vision)
- [ ] Distributed daemon (multi-node)
- [ ] Real-time budget pooling
- [ ] Zero-knowledge proofs for privacy
- [ ] Smart contract integration
