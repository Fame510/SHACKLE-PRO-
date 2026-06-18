# SHACKLE V2.0 Protocol Specification

**Version:** 2.0.0  
**Status:** Draft  
**Last Updated:** 2025-01-23  

---

## 1. Overview

SHACKLE (Secure Hook Architecture for Controlled Kernel-Level Execution) is a security protocol for command execution monitoring and human-in-the-loop (HITL) authorization. It enables real-time interception, inspection, and control of command execution with support for both automated policy enforcement and human oversight.

### 1.1 Design Principles

- **Zero-trust execution**: All commands must be explicitly authorized
- **Low-latency**: Protocol optimized for minimal overhead (<10ms typical)
- **Fail-secure**: Network failures default to DENY
- **Auditability**: Complete execution trail with correlation IDs
- **Extensibility**: Version negotiation and backward compatibility

### 1.2 Architecture

```
┌─────────────┐         ┌──────────────┐         ┌──────────────┐
│   Client    │◄───────►│   Shackle    │◄───────►│    Human     │
│  (Process)  │  Unix/WS│   Guardian   │  WebUI  │  Operator    │
└─────────────┘         └──────────────┘         └──────────────┘
     │                         │
     │  1. pre_exec           │
     ├────────────────────────►│
     │                         │ 2. Policy Check
     │                         │ 3. HITL (if needed)
     │  4. Verdict            │
     │◄────────────────────────┤
     │                         │
     │  5. Execute             │
     │                         │
     │  6. post_exec          │
     ├────────────────────────►│
     │                         │
```

---

## 2. Transport Layer

### 2.1 Supported Transports

#### Unix Domain Socket (Primary)
- **Path**: `/var/run/shackle/guardian.sock`
- **Type**: `SOCK_STREAM`
- **Permissions**: `0660` (root:shackle)
- **Use case**: Local process monitoring

#### WebSocket (Secondary)
- **Endpoint**: `ws://localhost:8765/shackle/v2`
- **TLS**: `wss://` for remote connections
- **Authentication**: Bearer token in `Authorization` header
- **Use case**: Remote monitoring, web UI integration

### 2.2 Message Framing

#### Unix Socket Framing
```
[4 bytes: length (big-endian)][N bytes: protobuf payload]
```

#### WebSocket Framing
- Binary frames containing protobuf payload
- Text frames for JSON fallback (debugging only)
- Ping/pong for keepalive (30s interval)

---

## 3. Protocol Messages

### 3.1 Message Types

All messages use Protocol Buffers (see `shackle.proto`). Each message includes:
- `message_type`: Enum identifying the message
- `message_id`: UUID for request/response correlation
- `version`: Protocol version (major.minor.patch)
- `timestamp`: Unix timestamp (milliseconds)

### 3.2 Connection Lifecycle

#### 3.2.1 Register Message
**Direction**: Client → Guardian  
**Purpose**: Establish session and negotiate protocol version

**Fields**:
- `client_id` (string): Unique client identifier (UUID recommended)
- `client_version` (string): Client software version
- `protocol_version` (string): Requested protocol version (e.g., "2.0.0")
- `capabilities` (repeated string): Supported features ["hitl", "async", "batch"]
- `metadata` (map<string, string>): Client metadata (hostname, user, pid)

**Response**: `RegisterResponse`
- `session_id` (string): Assigned session UUID
- `accepted_version` (string): Negotiated protocol version
- `guardian_capabilities` (repeated string): Guardian features
- `config` (map<string, string>): Session configuration (timeout values, etc.)

**Version Negotiation**:
1. Client requests highest supported version
2. Guardian responds with highest mutually supported version
3. Both downgrade to negotiated version for session
4. Major version mismatch → connection rejected

#### 3.2.2 Heartbeat Message
**Direction**: Bidirectional  
**Purpose**: Keepalive and session validation  
**Interval**: Every 30 seconds (configurable)

**Fields**:
- `session_id` (string): Current session ID
- `status` (enum): `HEALTHY`, `DEGRADED`, `OVERLOADED`
- `metrics` (optional): CPU, memory, queue depth

**Response**: `HeartbeatResponse`
- `acknowledged` (bool): True if session valid
- `should_reconnect` (bool): True if client should restart

**Timeout Behavior**:
- 3 missed heartbeats → session marked stale
- 5 missed heartbeats → session terminated
- Client should reconnect immediately on termination

---

### 3.3 Execution Flow

#### 3.3.1 Pre-Execution Message
**Direction**: Client → Guardian  
**Purpose**: Request authorization before command execution

**Fields**:
- `execution_id` (string): Unique execution UUID (for correlation)
- `command` (repeated string): Command and arguments (argv)
- `working_directory` (string): Current working directory
- `environment` (map<string, string>): Environment variables
- `user` (string): Executing user (username)
- `uid` (int32): User ID
- `gid` (int32): Group ID
- `parent_pid` (int32): Parent process ID
- `stdin_data` (bytes, optional): Stdin preview (first 4KB)
- `context` (map<string, string>): Additional context (shell, session, etc.)

**Response**: `PreExecResponse` (Verdict)
- `verdict` (enum): `ALLOW`, `DENY`, `HITL`
- `execution_id` (string): Echoed for correlation
- `reason_code` (enum): Reason for verdict (see §4)
- `reason_message` (string): Human-readable explanation
- `modified_command` (repeated string, optional): Replacement command if modified
- `timeout_ms` (int32): Max execution time (0 = unlimited)
- `hitl_request_id` (string, optional): If verdict=HITL, reference to HITL request

**Timeout**:
- Default: 5000ms
- Configurable per session
- Timeout → automatic DENY with reason `TIMEOUT`

#### 3.3.2 Post-Execution Message
**Direction**: Client → Guardian  
**Purpose**: Report execution outcome for audit trail

**Fields**:
- `execution_id` (string): Matches pre_exec execution_id
- `exit_code` (int32): Process exit code
- `signal` (int32, optional): Signal number if terminated
- `duration_ms` (int64): Execution duration
- `stdout_preview` (bytes): First 4KB of stdout
- `stderr_preview` (bytes): First 4KB of stderr
- `stdout_size` (int64): Total stdout bytes
- `stderr_size` (int64): Total stderr bytes
- `resource_usage` (ResourceUsage): CPU, memory, I/O stats
- `error_message` (string, optional): Client-side error if execution failed

**Response**: `PostExecResponse`
- `acknowledged` (bool): Receipt confirmation
- `archived` (bool): True if stored in audit log

**Fire-and-Forget**:
- Post-exec is informational only
- No blocking on response
- Delivery failures logged but don't affect client

---

### 3.4 Human-in-the-Loop (HITL)

#### 3.4.1 HITL Request Message
**Direction**: Guardian → Human Operator (via WebUI/API)  
**Purpose**: Escalate decision to human

**Fields**:
- `hitl_request_id` (string): Unique HITL request UUID
- `execution_id` (string): Associated execution ID
- `command` (repeated string): Command requiring approval
- `risk_level` (enum): `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
- `risk_factors` (repeated string): Reasons for escalation
- `context` (ExecutionContext): Full context from pre_exec
- `suggested_verdict` (enum): AI/policy suggestion
- `timeout_ms` (int32): Time until auto-deny (default 60000)
- `expires_at` (int64): Unix timestamp of expiration

**Presentation**:
```
┌─────────────────────────────────────┐
│  ⚠️  AUTHORIZATION REQUIRED         │
├─────────────────────────────────────┤
│  Command: rm -rf /var/log/*        │
│  User: root                         │
│  Risk: HIGH                         │
│  Reason: Destructive operation      │
│          in critical directory      │
├─────────────────────────────────────┤
│  [ ALLOW ]  [ DENY ]  [ MODIFY ]   │
└─────────────────────────────────────┘
```

#### 3.4.2 HITL Response Message
**Direction**: Human Operator → Guardian  
**Purpose**: Provide human decision

**Fields**:
- `hitl_request_id` (string): Matches request
- `verdict` (enum): `ALLOW`, `DENY`, `MODIFY`
- `modified_command` (repeated string, optional): If verdict=MODIFY
- `reason` (string): Human justification
- `operator_id` (string): Who made the decision
- `expires_after_executions` (int32, optional): Cache this decision for N similar executions
- `permanent_rule` (bool): Convert to permanent policy rule

**Response**: `HitlAcknowledgment`
- `applied` (bool): True if verdict delivered to client
- `execution_id` (string): Associated execution

**Timeout Behavior**:
- If no response before `timeout_ms` → automatic DENY
- Timeout reason code: `HITL_TIMEOUT`
- Operator notified of timeout after the fact

---

## 4. Verdict System

### 4.1 Verdict Types

| Verdict | Meaning | Client Action |
|---------|---------|---------------|
| `ALLOW` | Approved for execution | Execute command as-is |
| `DENY` | Rejected | Abort, return error to user |
| `HITL` | Human decision required | Block until HITL response |
| `MODIFY` | Allowed with changes | Execute modified_command instead |

### 4.2 Reason Codes

#### ALLOW Reasons
- `POLICY_WHITELIST`: Command matches whitelist
- `SAFE_OPERATION`: Low-risk command
- `PREVIOUS_APPROVAL`: Cached HITL approval
- `OPERATOR_OVERRIDE`: Manual approval

#### DENY Reasons
- `POLICY_BLACKLIST`: Command matches blacklist
- `DANGEROUS_OPERATION`: High-risk command
- `INSUFFICIENT_PRIVILEGES`: User lacks permissions
- `RESOURCE_LIMIT`: Would exceed quota
- `TIMEOUT`: Decision took too long
- `HITL_TIMEOUT`: Human didn't respond in time
- `HITL_DENIED`: Human explicitly denied
- `MALFORMED_REQUEST`: Invalid protocol message
- `SESSION_INVALID`: Session expired or unknown

#### HITL Reasons
- `DESTRUCTIVE_OPERATION`: Irreversible changes
- `CRITICAL_SYSTEM_PATH`: Affects sensitive directories
- `UNUSUAL_PATTERN`: Anomaly detection triggered
- `POLICY_AMBIGUOUS`: Rules don't cover this case
- `ELEVATED_PRIVILEGES`: Sudo/root execution
- `NETWORK_OPERATION`: External communication

### 4.3 Verdict Caching

Guardian may cache verdicts to reduce latency:

**Cache Key**: Hash of (command, user, working_directory, environment_subset)

**Cache Behavior**:
- `ALLOW` verdicts: Cached for 1 hour (configurable)
- `DENY` verdicts: Cached for 5 minutes
- `HITL` verdicts: Cached per operator's `expires_after_executions`
- Cache invalidated on policy update

---

## 5. Error Handling

### 5.1 Error Response Message

**Fields**:
- `error_code` (enum): Machine-readable error
- `error_message` (string): Human-readable description
- `retry_after_ms` (int32, optional): Suggested retry delay
- `fatal` (bool): If true, client should disconnect

### 5.2 Error Codes

| Code | Meaning | Recovery |
|------|---------|----------|
| `PROTOCOL_VERSION_MISMATCH` | Version negotiation failed | Upgrade client/guardian |
| `SESSION_EXPIRED` | Session no longer valid | Re-register |
| `RATE_LIMITED` | Too many requests | Back off, retry after delay |
| `INTERNAL_ERROR` | Guardian fault | Retry with exponential backoff |
| `INVALID_MESSAGE` | Malformed protobuf | Fix client bug |
| `AUTHENTICATION_FAILED` | Bad credentials (WebSocket) | Re-authenticate |

### 5.3 Connection Failures

**Unix Socket**:
- Connection refused → Guardian not running
- Broken pipe → Guardian crashed
- Timeout → Guardian overloaded

**Fallback Behavior**:
- Client should implement fail-secure: DENY all on connection loss
- Optional: Fail-open mode for non-critical systems (configurable)

---

## 6. Security Considerations

### 6.1 Authentication

**Unix Socket**:
- Relies on filesystem permissions
- Guardian validates `SO_PEERCRED` for uid/gid
- Only trusted users in `shackle` group can connect

**WebSocket**:
- Bearer token authentication (JWT)
- Token includes: user_id, roles, expiration
- Tokens issued by Guardian's auth endpoint
- Refresh tokens for long-lived sessions

### 6.2 Authorization

- Guardian enforces role-based access control (RBAC)
- Roles: `operator` (HITL), `auditor` (read-only), `admin` (config)
- Execution context includes user's roles for policy evaluation

### 6.3 Audit Logging

All messages logged with:
- Timestamp (microsecond precision)
- Session ID and execution ID
- Client metadata
- Verdict and reason
- Operator identity (for HITL)

Log format: Structured JSON, one event per line (JSONL)

### 6.4 Replay Protection

- Each message_id must be unique (UUID v4)
- Guardian maintains 1-hour sliding window of seen message_ids
- Duplicate message_id → rejected with `DUPLICATE_MESSAGE` error

---

## 7. Performance

### 7.1 Latency Targets

| Operation | Target | P99 |
|-----------|--------|-----|
| Pre-exec (cached) | <1ms | <5ms |
| Pre-exec (policy eval) | <10ms | <50ms |
| Pre-exec (HITL) | <2s | <60s |
| Post-exec | <5ms | <20ms |
| Heartbeat | <1ms | <5ms |

### 7.2 Throughput

- Guardian should handle 10,000 pre-exec/sec per core
- Backpressure via response delays when overloaded
- Client should implement connection pooling for high-volume scenarios

### 7.3 Resource Usage

**Guardian**:
- Memory: <100MB baseline + ~1KB per active session
- CPU: <5% idle, <50% under load
- Disk I/O: Async writes to audit log

**Client**:
- Overhead: <0.5ms per exec() call
- Memory: <1MB per process

---

## 8. Version Compatibility

### 8.1 Semantic Versioning

Protocol follows semver: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (incompatible)
- **MINOR**: New features (backward-compatible)
- **PATCH**: Bug fixes (backward-compatible)

### 8.2 Compatibility Matrix

| Guardian | Client | Compatible? |
|----------|--------|-------------|
| 2.0.x | 2.0.x | ✅ Full |
| 2.1.x | 2.0.x | ✅ Backward |
| 2.0.x | 2.1.x | ⚠️ Forward (limited) |
| 3.0.x | 2.x.x | ❌ Incompatible |

### 8.3 Deprecation Policy

- Features marked deprecated in MINOR release
- Removed in next MAJOR release (minimum 6 months notice)
- Deprecation warnings in protocol responses

---

## 9. Extensions

### 9.1 Capability Negotiation

Clients and Guardian advertise optional capabilities:

**Standard Capabilities**:
- `hitl`: Human-in-the-loop support
- `async`: Asynchronous execution tracking
- `batch`: Batch pre-exec requests
- `streaming`: Stream stdout/stderr during execution
- `modify`: Support command modification

**Custom Capabilities**:
- Format: `x-vendor-feature` (e.g., `x-acme-gpu-tracking`)
- Ignored if unknown (graceful degradation)

### 9.2 Metadata Extensions

Both `ExecutionContext` and `RegisterRequest` support metadata maps for custom fields:

```protobuf
map<string, string> metadata = 99;
```

Standard metadata keys (optional):
- `shell`: Shell name (bash, zsh, etc.)
- `terminal`: TTY device
- `session_id`: Login session identifier
- `container_id`: Docker/Kubernetes container

---

## 10. Implementation Checklist

### 10.1 Minimum Viable Client

- [ ] Register with Guardian
- [ ] Send pre_exec for each command
- [ ] Handle ALLOW/DENY verdicts
- [ ] Send post_exec after execution
- [ ] Heartbeat every 30s
- [ ] Reconnect on connection loss

### 10.2 Minimum Viable Guardian

- [ ] Accept registrations
- [ ] Policy evaluation (whitelist/blacklist)
- [ ] Return verdicts
- [ ] Log audit trail
- [ ] HITL queue management
- [ ] Session lifecycle management

### 10.3 Production Readiness

- [ ] TLS for WebSocket
- [ ] Token authentication
- [ ] Rate limiting
- [ ] Verdict caching
- [ ] Metrics export (Prometheus)
- [ ] Health check endpoint
- [ ] Graceful shutdown
- [ ] Configuration reload without restart

---

## 11. References

- **Protocol Buffers**: https://protobuf.dev/
- **WebSocket RFC 6455**: https://tools.ietf.org/html/rfc6455
- **Unix Domain Sockets**: `man 7 unix`
- **JWT RFC 7519**: https://tools.ietf.org/html/rfc7519

---

## Appendix A: Glossary

- **Client**: Process or shell integration that sends execution requests
- **Guardian**: Central decision-making service that issues verdicts
- **HITL**: Human-in-the-loop; manual authorization step
- **Verdict**: Authorization decision (ALLOW/DENY/HITL)
- **Execution ID**: Unique identifier correlating pre_exec and post_exec
- **Session**: Connection lifetime between client and guardian

---

**End of Specification**
