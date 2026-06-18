# SHACKLE V2.0 Protocol Examples

This document provides practical examples of SHACKLE protocol messages in various formats for testing and implementation reference.

---

## Table of Contents

1. [Connection Lifecycle](#1-connection-lifecycle)
2. [Basic Execution Flow](#2-basic-execution-flow)
3. [Human-in-the-Loop](#3-human-in-the-loop)
4. [Error Scenarios](#4-error-scenarios)
5. [Advanced Patterns](#5-advanced-patterns)

---

## 1. Connection Lifecycle

### 1.1 Client Registration

**Request (JSON representation of protobuf)**:
```json
{
  "message_type": "MESSAGE_TYPE_REGISTER",
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "version": "2.0.0",
  "timestamp": 1706016000000,
  "register_request": {
    "client_id": "client-123e4567-e89b-12d3-a456-426614174000",
    "client_version": "shackle-client/2.0.1",
    "protocol_version": "2.0.0",
    "capabilities": ["hitl", "async", "modify"],
    "metadata": {
      "hostname": "web-server-01",
      "user": "deploy",
      "pid": "42315",
      "shell": "bash",
      "os": "Linux 5.15.0"
    }
  }
}
```

**Response**:
```json
{
  "message_type": "MESSAGE_TYPE_REGISTER_RESPONSE",
  "message_id": "550e8400-e29b-41d4-a716-446655440001",
  "version": "2.0.0",
  "timestamp": 1706016000050,
  "register_response": {
    "session_id": "session-789abcde-f012-3456-7890-abcdef123456",
    "accepted_version": "2.0.0",
    "guardian_capabilities": ["hitl", "async", "batch", "streaming", "modify"],
    "config": {
      "pre_exec_timeout_ms": "5000",
      "heartbeat_interval_ms": "30000",
      "max_command_length": "65536",
      "verdict_cache_ttl_ms": "3600000"
    },
    "session_expires_at": 1706019600000
  }
}
```

### 1.2 Heartbeat Exchange

**Request**:
```json
{
  "message_type": "MESSAGE_TYPE_HEARTBEAT",
  "message_id": "660e8400-e29b-41d4-a716-446655440010",
  "version": "2.0.0",
  "timestamp": 1706016030000,
  "heartbeat_request": {
    "session_id": "session-789abcde-f012-3456-7890-abcdef123456",
    "status": "HEALTH_STATUS_HEALTHY",
    "metrics": {
      "cpu_percent": 12.5,
      "memory_bytes": 45678912,
      "queue_depth": 2,
      "requests_per_second": 150,
      "avg_latency_ms": 8.3
    }
  }
}
```

**Response**:
```json
{
  "message_type": "MESSAGE_TYPE_HEARTBEAT_RESPONSE",
  "message_id": "660e8400-e29b-41d4-a716-446655440011",
  "version": "2.0.0",
  "timestamp": 1706016030010,
  "heartbeat_response": {
    "acknowledged": true,
    "should_reconnect": false,
    "next_heartbeat_ms": 30000
  }
}
```

---

## 2. Basic Execution Flow

### 2.1 Simple ALLOW Verdict

**Pre-Exec Request** (`ls -la /tmp`):
```json
{
  "message_type": "MESSAGE_TYPE_PRE_EXEC",
  "message_id": "770e8400-e29b-41d4-a716-446655440020",
  "version": "2.0.0",
  "timestamp": 1706016100000,
  "pre_exec_request": {
    "execution_id": "exec-11111111-2222-3333-4444-555555555555",
    "command": ["ls", "-la", "/tmp"],
    "working_directory": "/home/user",
    "environment": {
      "PATH": "/usr/local/bin:/usr/bin:/bin",
      "HOME": "/home/user",
      "USER": "user",
      "SHELL": "/bin/bash"
    },
    "user": {
      "username": "user",
      "uid": 1000,
      "gid": 1000,
      "supplementary_gids": [4, 24, 27, 30],
      "roles": ["developer"],
      "home_directory": "/home/user",
      "shell": "/bin/bash"
    },
    "process": {
      "pid": 12345,
      "parent_pid": 12340,
      "process_group_id": 12340,
      "session_id": 12340,
      "executable_path": "/bin/bash",
      "command_line": ["bash", "-c", "ls -la /tmp"],
      "terminal": "/dev/pts/3"
    },
    "context": {
      "shell": "bash",
      "session_type": "ssh",
      "source_ip": "192.168.1.100"
    }
  }
}
```

**Pre-Exec Response** (ALLOW):
```json
{
  "message_type": "MESSAGE_TYPE_PRE_EXEC_RESPONSE",
  "message_id": "770e8400-e29b-41d4-a716-446655440021",
  "version": "2.0.0",
  "timestamp": 1706016100008,
  "pre_exec_response": {
    "verdict": "VERDICT_ALLOW",
    "execution_id": "exec-11111111-2222-3333-4444-555555555555",
    "reason_code": "REASON_SAFE_OPERATION",
    "reason_message": "Read-only operation on non-sensitive directory",
    "timeout_ms": 10000,
    "metadata": {
      "policy_rule": "safe-read-operations-v1",
      "cache_hit": "false"
    }
  }
}
```

**Post-Exec Request** (after execution):
```json
{
  "message_type": "MESSAGE_TYPE_POST_EXEC",
  "message_id": "770e8400-e29b-41d4-a716-446655440022",
  "version": "2.0.0",
  "timestamp": 1706016100250,
  "post_exec_request": {
    "execution_id": "exec-11111111-2222-3333-4444-555555555555",
    "exit_code": 0,
    "duration_ms": 235,
    "stdout_preview": "dHRvdGFsIDEyOApkcnd4cnd4cnQgIDIgcm9vdCByb290IDQwOTYgSmFuIDIzIDEwOjAwIC4KZHd4cnd4cnd0IDE5IHJvb3Qgcm9vdCA0MDk2IEphbiAyMyAwOTowMCAuLgo=",
    "stderr_preview": "",
    "stdout_size": 1245,
    "stderr_size": 0,
    "resource_usage": {
      "cpu_time_us": 15234,
      "max_rss_kb": 2048,
      "page_faults": 45,
      "block_input_ops": 2,
      "block_output_ops": 0,
      "voluntary_context_switches": 12,
      "involuntary_context_switches": 3
    }
  }
}
```

**Post-Exec Response**:
```json
{
  "message_type": "MESSAGE_TYPE_POST_EXEC_RESPONSE",
  "message_id": "770e8400-e29b-41d4-a716-446655440023",
  "version": "2.0.0",
  "timestamp": 1706016100255,
  "post_exec_response": {
    "acknowledged": true,
    "archived": true
  }
}
```

### 2.2 DENY Verdict

**Pre-Exec Request** (`rm -rf /var/log/*`):
```json
{
  "message_type": "MESSAGE_TYPE_PRE_EXEC",
  "message_id": "880e8400-e29b-41d4-a716-446655440030",
  "version": "2.0.0",
  "timestamp": 1706016200000,
  "pre_exec_request": {
    "execution_id": "exec-22222222-3333-4444-5555-666666666666",
    "command": ["rm", "-rf", "/var/log/*"],
    "working_directory": "/root",
    "environment": {
      "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
      "HOME": "/root",
      "USER": "root"
    },
    "user": {
      "username": "root",
      "uid": 0,
      "gid": 0,
      "roles": ["admin"],
      "home_directory": "/root",
      "shell": "/bin/bash"
    },
    "process": {
      "pid": 23456,
      "parent_pid": 23450,
      "executable_path": "/bin/bash",
      "terminal": "/dev/pts/5"
    }
  }
}
```

**Pre-Exec Response** (DENY):
```json
{
  "message_type": "MESSAGE_TYPE_PRE_EXEC_RESPONSE",
  "message_id": "880e8400-e29b-41d4-a716-446655440031",
  "version": "2.0.0",
  "timestamp": 1706016200012,
  "pre_exec_response": {
    "verdict": "VERDICT_DENY",
    "execution_id": "exec-22222222-3333-4444-5555-666666666666",
    "reason_code": "REASON_DANGEROUS_OPERATION",
    "reason_message": "Destructive operation on critical system directory /var/log blocked by policy",
    "metadata": {
      "policy_rule": "critical-path-protection-v2",
      "threat_level": "high",
      "alternative_suggestion": "Use 'logrotate' or specify individual files"
    }
  }
}
```

---

## 3. Human-in-the-Loop

### 3.1 HITL Verdict and Request

**Pre-Exec Response** (HITL):
```json
{
  "message_type": "MESSAGE_TYPE_PRE_EXEC_RESPONSE",
  "message_id": "990e8400-e29b-41d4-a716-446655440040",
  "version": "2.0.0",
  "timestamp": 1706016300015,
  "pre_exec_response": {
    "verdict": "VERDICT_HITL",
    "execution_id": "exec-33333333-4444-5555-6666-777777777777",
    "reason_code": "REASON_ELEVATED_PRIVILEGES",
    "reason_message": "Sudo command requires human approval",
    "hitl_request_id": "hitl-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "metadata": {
      "escalation_reason": "elevated_privileges",
      "timeout_behavior": "auto_deny"
    }
  }
}
```

**HITL Request** (to operator):
```json
{
  "message_type": "MESSAGE_TYPE_HITL_REQUEST",
  "message_id": "990e8400-e29b-41d4-a716-446655440041",
  "version": "2.0.0",
  "timestamp": 1706016300020,
  "hitl_request": {
    "hitl_request_id": "hitl-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "execution_id": "exec-33333333-4444-5555-6666-777777777777",
    "command": ["sudo", "systemctl", "restart", "nginx"],
    "risk_level": "RISK_LEVEL_HIGH",
    "risk_factors": [
      "Using sudo (privilege escalation)",
      "Restarting production service",
      "Off-hours execution (outside business hours)"
    ],
    "context": {
      "execution_id": "exec-33333333-4444-5555-6666-777777777777",
      "command": ["sudo", "systemctl", "restart", "nginx"],
      "working_directory": "/home/devops",
      "user": {
        "username": "devops",
        "uid": 1001,
        "gid": 1001,
        "roles": ["operator"]
      },
      "process": {
        "pid": 34567,
        "terminal": "/dev/pts/8"
      },
      "timestamp": 1706016300000,
      "metadata": {
        "session_type": "ssh",
        "source_ip": "203.0.113.45"
      }
    },
    "suggested_verdict": "VERDICT_ALLOW",
    "timeout_ms": 60000,
    "expires_at": 1706016360000
  }
}
```

### 3.2 HITL Response (Operator Approval)

```json
{
  "message_type": "MESSAGE_TYPE_HITL_RESPONSE",
  "message_id": "990e8400-e29b-41d4-a716-446655440042",
  "version": "2.0.0",
  "timestamp": 1706016315000,
  "hitl_response": {
    "hitl_request_id": "hitl-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "verdict": "VERDICT_ALLOW",
    "reason": "Approved: Nginx restart for emergency hotfix deployment. Ticket #INC-12345",
    "operator_id": "alice@example.com",
    "expires_after_executions": 5,
    "permanent_rule": false
  }
}
```

**HITL Acknowledgment**:
```json
{
  "message_type": "MESSAGE_TYPE_HITL_ACKNOWLEDGMENT",
  "message_id": "990e8400-e29b-41d4-a716-446655440043",
  "version": "2.0.0",
  "timestamp": 1706016315010,
  "hitl_acknowledgment": {
    "hitl_request_id": "hitl-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "applied": true,
    "execution_id": "exec-33333333-4444-5555-6666-777777777777"
  }
}
```

### 3.3 HITL Response (Operator Denial)

```json
{
  "message_type": "MESSAGE_TYPE_HITL_RESPONSE",
  "message_id": "aa0e8400-e29b-41d4-a716-446655440050",
  "version": "2.0.0",
  "timestamp": 1706016400000,
  "hitl_response": {
    "hitl_request_id": "hitl-bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
    "verdict": "VERDICT_DENY",
    "reason": "Denied: Maintenance window not approved. Submit change request first.",
    "operator_id": "bob@example.com",
    "permanent_rule": false
  }
}
```

### 3.4 HITL Response (Modification)

```json
{
  "message_type": "MESSAGE_TYPE_HITL_RESPONSE",
  "message_id": "bb0e8400-e29b-41d4-a716-446655440060",
  "version": "2.0.0",
  "timestamp": 1706016500000,
  "hitl_response": {
    "hitl_request_id": "hitl-cccccccc-dddd-eeee-ffff-000000000000",
    "verdict": "VERDICT_MODIFY",
    "modified_command": ["sudo", "systemctl", "reload", "nginx"],
    "reason": "Modified: Use 'reload' instead of 'restart' to avoid dropping connections",
    "operator_id": "carol@example.com",
    "expires_after_executions": 1,
    "permanent_rule": false
  }
}
```

---

## 4. Error Scenarios

### 4.1 Protocol Version Mismatch

**Register Request** (outdated version):
```json
{
  "message_type": "MESSAGE_TYPE_REGISTER",
  "message_id": "cc0e8400-e29b-41d4-a716-446655440070",
  "version": "1.0.0",
  "timestamp": 1706016600000,
  "register_request": {
    "client_id": "client-old-aaaabbbb-cccc-dddd-eeee-ffff00001111",
    "protocol_version": "1.0.0"
  }
}
```

**Error Response**:
```json
{
  "message_type": "MESSAGE_TYPE_ERROR",
  "message_id": "cc0e8400-e29b-41d4-a716-446655440071",
  "version": "2.0.0",
  "timestamp": 1706016600005,
  "error_response": {
    "error_code": "ERROR_CODE_PROTOCOL_VERSION_MISMATCH",
    "error_message": "Protocol version 1.0.0 is no longer supported. Please upgrade to 2.0.0 or later.",
    "fatal": true,
    "details": {
      "min_supported_version": "2.0.0",
      "max_supported_version": "2.1.0",
      "upgrade_url": "https://shackle.io/docs/upgrade"
    }
  }
}
```

### 4.2 Session Expired

**Pre-Exec Request** (expired session):
```json
{
  "message_type": "MESSAGE_TYPE_PRE_EXEC",
  "message_id": "dd0e8400-e29b-41d4-a716-446655440080",
  "version": "2.0.0",
  "timestamp": 1706020000000,
  "pre_exec_request": {
    "execution_id": "exec-44444444-5555-6666-7777-888888888888",
    "command": ["echo", "hello"],
    "working_directory": "/home/user",
    "user": {
      "username": "user",
      "uid": 1000,
      "gid": 1000
    }
  }
}
```

**Error Response**:
```json
{
  "message_type": "MESSAGE_TYPE_ERROR",
  "message_id": "dd0e8400-e29b-41d4-a716-446655440081",
  "version": "2.0.0",
  "timestamp": 1706020000003,
  "error_response": {
    "error_code": "ERROR_CODE_SESSION_EXPIRED",
    "error_message": "Session has expired. Please re-register.",
    "retry_after_ms": 0,
    "fatal": false,
    "details": {
      "expired_at": "1706019600000",
      "current_time": "1706020000000"
    }
  }
}
```

### 4.3 Rate Limiting

**Error Response**:
```json
{
  "message_type": "MESSAGE_TYPE_ERROR",
  "message_id": "ee0e8400-e29b-41d4-a716-446655440090",
  "version": "2.0.0",
  "timestamp": 1706016700000,
  "error_response": {
    "error_code": "ERROR_CODE_RATE_LIMITED",
    "error_message": "Too many requests. Rate limit: 1000 req/min exceeded.",
    "retry_after_ms": 5000,
    "fatal": false,
    "details": {
      "limit": "1000",
      "window": "60000",
      "current_usage": "1247",
      "reset_at": "1706016760000"
    }
  }
}
```

---

## 5. Advanced Patterns

### 5.1 Command with Stdin Preview

**Pre-Exec Request** (piped input):
```json
{
  "message_type": "MESSAGE_TYPE_PRE_EXEC",
  "message_id": "ff0e8400-e29b-41d4-a716-446655440100",
  "version": "2.0.0",
  "timestamp": 1706016800000,
  "pre_exec_request": {
    "execution_id": "exec-55555555-6666-7777-8888-999999999999",
    "command": ["grep", "-i", "error"],
    "working_directory": "/var/log",
    "user": {
      "username": "sysadmin",
      "uid": 1002,
      "gid": 1002
    },
    "stdin_preview": "MjAyNC0wMS0yMyAxMDowMDowMSBJTkZPIFN5c3RlbSBzdGFydGVkCjIwMjQtMDEtMjMgMTA6MDU6MTUgRVJST1IgRGF0YWJhc2UgY29ubmVjdGlvbiBmYWlsZWQ=",
    "context": {
      "pipe_chain": "cat /var/log/app.log | grep -i error",
      "stdin_source": "file"
    }
  }
}
```

### 5.2 Post-Exec with Signal Termination

**Post-Exec Request** (killed by SIGTERM):
```json
{
  "message_type": "MESSAGE_TYPE_POST_EXEC",
  "message_id": "000e8400-e29b-41d4-a716-446655440110",
  "version": "2.0.0",
  "timestamp": 1706016900000,
  "post_exec_request": {
    "execution_id": "exec-66666666-7777-8888-9999-aaaaaaaaaaaa",
    "exit_code": 143,
    "signal": 15,
    "duration_ms": 45123,
    "stdout_size": 1024567,
    "stderr_size": 512,
    "resource_usage": {
      "cpu_time_us": 42350000,
      "max_rss_kb": 512000,
      "page_faults": 1234
    },
    "error_message": "Process terminated by SIGTERM"
  }
}
```

### 5.3 Version Negotiation (Downgrade)

**Client requests 2.1.0, Guardian only supports 2.0.x**:

Request:
```json
{
  "message_type": "MESSAGE_TYPE_REGISTER",
  "message_id": "110e8400-e29b-41d4-a716-446655440120",
  "version": "2.1.0",
  "timestamp": 1706017000000,
  "register_request": {
    "client_id": "client-future-1111-2222-3333-4444-555566667777",
    "protocol_version": "2.1.0",
    "capabilities": ["hitl", "async", "batch", "streaming", "x-future-feature"]
  }
}
```

Response (downgrade):
```json
{
  "message_type": "MESSAGE_TYPE_REGISTER_RESPONSE",
  "message_id": "110e8400-e29b-41d4-a716-446655440121",
  "version": "2.0.0",
  "timestamp": 1706017000010,
  "register_response": {
    "session_id": "session-downgrade-8888-9999-aaaa-bbbbccccdddd",
    "accepted_version": "2.0.0",
    "guardian_capabilities": ["hitl", "async", "batch"],
    "config": {
      "pre_exec_timeout_ms": "5000",
      "note": "Downgraded from 2.1.0 to 2.0.0 (highest mutually supported)"
    }
  }
}
```

---

## 6. Wire Format Examples

### 6.1 Unix Socket Binary Frame

```
Byte offset | Content
------------|----------------------------------------------------
0x00-0x03   | 0x00 0x00 0x01 0x2A (298 bytes payload length)
0x04-0x129  | [protobuf encoded Message]
```

### 6.2 WebSocket Frame

**Text frame (JSON, debugging only)**:
```
Opcode: 0x1 (text)
Payload: {"message_type": "MESSAGE_TYPE_HEARTBEAT", ...}
```

**Binary frame (protobuf, production)**:
```
Opcode: 0x2 (binary)
Payload: [protobuf encoded Message]
```

---

## 7. Testing Payloads

### 7.1 Minimal Valid Pre-Exec

```json
{
  "message_type": "MESSAGE_TYPE_PRE_EXEC",
  "message_id": "test-1111-2222-3333-4444-555555555555",
  "version": "2.0.0",
  "timestamp": 1706017100000,
  "pre_exec_request": {
    "execution_id": "exec-test-1111-2222-3333-4444-555555555555",
    "command": ["echo", "test"],
    "working_directory": "/tmp",
    "user": {
      "username": "test",
      "uid": 1000,
      "gid": 1000
    }
  }
}
```

### 7.2 Invalid Message (Missing Required Field)

```json
{
  "message_type": "MESSAGE_TYPE_PRE_EXEC",
  "message_id": "bad-1111-2222-3333-4444-555555555555",
  "version": "2.0.0",
  "timestamp": 1706017200000,
  "pre_exec_request": {
    "execution_id": "exec-bad-1111-2222-3333-4444-555555555555",
    "command": ["echo", "test"]
    // Missing required fields: working_directory, user
  }
}
```

Expected error:
```json
{
  "message_type": "MESSAGE_TYPE_ERROR",
  "message_id": "bad-1111-2222-3333-4444-555555555556",
  "version": "2.0.0",
  "timestamp": 1706017200002,
  "error_response": {
    "error_code": "ERROR_CODE_INVALID_MESSAGE",
    "error_message": "Missing required field: user",
    "fatal": false
  }
}
```

---

## 8. Performance Test Scenarios

### 8.1 High-Frequency Executions

Simulate 100 rapid executions with cached verdicts:
- Each pre_exec should return in <1ms (cache hit)
- Total throughput: >10,000 req/sec

### 8.2 HITL Under Load

- Send 10 concurrent HITL requests
- Operator responds to 5, ignores 5
- Verify timeout behavior on ignored requests (auto-deny after 60s)

### 8.3 Session Lifecycle Stress

- Register 1000 clients concurrently
- Each sends 1 heartbeat every 30s
- Verify guardian handles without degradation

---

**End of Examples**
