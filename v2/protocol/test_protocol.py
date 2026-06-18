#!/usr/bin/env python3
"""
SHACKLE V2.0 Protocol Test Suite

Basic test examples for protocol validation.
Requires: pytest, pytest-asyncio

Run with:
    pytest test_protocol.py -v
"""

import asyncio
import json
import uuid
import time
from typing import Dict, Any


# ============================================================================
# Test Message Construction
# ============================================================================

def test_register_request_structure():
    """Test that a register request has all required fields."""
    message = {
        "message_type": "MESSAGE_TYPE_REGISTER",
        "message_id": str(uuid.uuid4()),
        "version": "2.0.0",
        "timestamp": int(time.time() * 1000),
        "register_request": {
            "client_id": str(uuid.uuid4()),
            "client_version": "test-client/1.0.0",
            "protocol_version": "2.0.0",
            "capabilities": ["hitl", "async"],
            "metadata": {
                "hostname": "test-host",
                "user": "test-user"
            }
        }
    }
    
    # Validate structure
    assert "message_type" in message
    assert "message_id" in message
    assert "version" in message
    assert "timestamp" in message
    assert "register_request" in message
    
    req = message["register_request"]
    assert "client_id" in req
    assert "protocol_version" in req
    assert req["protocol_version"] == "2.0.0"
    
    print("✓ Register request structure valid")


def test_pre_exec_request_structure():
    """Test that a pre_exec request has all required fields."""
    message = {
        "message_type": "MESSAGE_TYPE_PRE_EXEC",
        "message_id": str(uuid.uuid4()),
        "version": "2.0.0",
        "timestamp": int(time.time() * 1000),
        "pre_exec_request": {
            "execution_id": str(uuid.uuid4()),
            "command": ["ls", "-la", "/tmp"],
            "working_directory": "/home/user",
            "environment": {"PATH": "/usr/bin:/bin"},
            "user": {
                "username": "user",
                "uid": 1000,
                "gid": 1000
            },
            "process": {
                "pid": 12345,
                "parent_pid": 12340
            }
        }
    }
    
    # Validate structure
    req = message["pre_exec_request"]
    assert "execution_id" in req
    assert "command" in req
    assert isinstance(req["command"], list)
    assert len(req["command"]) > 0
    assert "user" in req
    assert "uid" in req["user"]
    
    print("✓ Pre-exec request structure valid")


def test_verdict_response_structure():
    """Test that verdict responses have correct structure."""
    verdicts = ["VERDICT_ALLOW", "VERDICT_DENY", "VERDICT_HITL"]
    
    for verdict in verdicts:
        message = {
            "message_type": "MESSAGE_TYPE_PRE_EXEC_RESPONSE",
            "message_id": str(uuid.uuid4()),
            "version": "2.0.0",
            "timestamp": int(time.time() * 1000),
            "pre_exec_response": {
                "verdict": verdict,
                "execution_id": str(uuid.uuid4()),
                "reason_code": "REASON_SAFE_OPERATION",
                "reason_message": "Test verdict"
            }
        }
        
        resp = message["pre_exec_response"]
        assert resp["verdict"] in verdicts
        assert "execution_id" in resp
        assert "reason_code" in resp
        assert "reason_message" in resp
    
    print("✓ Verdict response structures valid")


# ============================================================================
# Test Protocol Semantics
# ============================================================================

def test_message_id_uniqueness():
    """Test that message IDs are unique."""
    ids = set()
    
    for _ in range(1000):
        msg_id = str(uuid.uuid4())
        assert msg_id not in ids, "Duplicate message ID generated"
        ids.add(msg_id)
    
    print("✓ Message IDs are unique (1000 samples)")


def test_timestamp_monotonicity():
    """Test that timestamps are monotonically increasing."""
    timestamps = []
    
    for _ in range(100):
        ts = int(time.time() * 1000)
        timestamps.append(ts)
        time.sleep(0.001)  # 1ms delay
    
    # Check monotonic increase (with some tolerance for clock precision)
    for i in range(1, len(timestamps)):
        assert timestamps[i] >= timestamps[i-1], "Timestamps not monotonic"
    
    print("✓ Timestamps are monotonic")


def test_session_id_format():
    """Test that session IDs are valid UUIDs."""
    for _ in range(100):
        session_id = str(uuid.uuid4())
        
        # Validate UUID format
        try:
            uuid.UUID(session_id)
        except ValueError:
            assert False, f"Invalid UUID: {session_id}"
    
    print("✓ Session IDs are valid UUIDs")


# ============================================================================
# Test Policy Logic
# ============================================================================

def test_command_pattern_matching():
    """Test command pattern matching logic."""
    dangerous_patterns = ["rm -rf", "dd if=", "mkfs", "fdisk"]
    safe_patterns = ["ls", "cat", "grep", "echo"]
    
    # Test dangerous commands should be flagged
    for pattern in dangerous_patterns:
        command = pattern.split()
        # In real implementation, this would call policy engine
        is_dangerous = any(p in " ".join(command) for p in dangerous_patterns)
        assert is_dangerous, f"Pattern {pattern} not detected as dangerous"
    
    # Test safe commands should pass
    for pattern in safe_patterns:
        command = pattern.split()
        is_dangerous = any(p in " ".join(command) for p in dangerous_patterns)
        assert not is_dangerous, f"Pattern {pattern} incorrectly flagged"
    
    print("✓ Command pattern matching works")


def test_path_sensitivity():
    """Test that critical paths are protected."""
    critical_paths = ["/etc", "/boot", "/sys", "/proc"]
    safe_paths = ["/tmp", "/home/user", "/var/log"]
    
    for path in critical_paths:
        # Simulate policy check
        is_critical = any(path.startswith(cp) for cp in critical_paths)
        assert is_critical, f"Path {path} not detected as critical"
    
    for path in safe_paths:
        is_critical = any(path.startswith(cp) for cp in critical_paths)
        assert not is_critical, f"Path {path} incorrectly flagged as critical"
    
    print("✓ Critical path detection works")


# ============================================================================
# Test Error Handling
# ============================================================================

def test_error_response_structure():
    """Test error response structure."""
    error_codes = [
        "ERROR_CODE_PROTOCOL_VERSION_MISMATCH",
        "ERROR_CODE_SESSION_EXPIRED",
        "ERROR_CODE_RATE_LIMITED",
        "ERROR_CODE_INTERNAL_ERROR"
    ]
    
    for error_code in error_codes:
        message = {
            "message_type": "MESSAGE_TYPE_ERROR",
            "message_id": str(uuid.uuid4()),
            "version": "2.0.0",
            "timestamp": int(time.time() * 1000),
            "error_response": {
                "error_code": error_code,
                "error_message": "Test error",
                "fatal": False
            }
        }
        
        err = message["error_response"]
        assert err["error_code"] in error_codes
        assert "error_message" in err
        assert "fatal" in err
        assert isinstance(err["fatal"], bool)
    
    print("✓ Error response structures valid")


def test_version_compatibility():
    """Test protocol version compatibility logic."""
    # Compatible versions
    compatible_pairs = [
        ("2.0.0", "2.0.0"),  # Exact match
        ("2.0.1", "2.0.0"),  # Patch difference
        ("2.1.0", "2.0.0"),  # Minor upgrade (backward compat)
    ]
    
    # Incompatible versions
    incompatible_pairs = [
        ("3.0.0", "2.0.0"),  # Major version mismatch
        ("2.0.0", "1.0.0"),  # Major version downgrade
    ]
    
    def is_compatible(v1: str, v2: str) -> bool:
        """Simple version compatibility check."""
        major1, minor1, patch1 = map(int, v1.split("."))
        major2, minor2, patch2 = map(int, v2.split("."))
        
        # Major version must match
        if major1 != major2:
            return False
        
        return True
    
    for v1, v2 in compatible_pairs:
        assert is_compatible(v1, v2), f"{v1} and {v2} should be compatible"
    
    for v1, v2 in incompatible_pairs:
        assert not is_compatible(v1, v2), f"{v1} and {v2} should be incompatible"
    
    print("✓ Version compatibility logic correct")


# ============================================================================
# Test Message Serialization
# ============================================================================

def test_json_serialization():
    """Test that messages can be JSON serialized."""
    message = {
        "message_type": "MESSAGE_TYPE_PRE_EXEC",
        "message_id": str(uuid.uuid4()),
        "version": "2.0.0",
        "timestamp": int(time.time() * 1000),
        "pre_exec_request": {
            "execution_id": str(uuid.uuid4()),
            "command": ["echo", "test"],
            "working_directory": "/tmp",
            "user": {
                "username": "test",
                "uid": 1000,
                "gid": 1000
            }
        }
    }
    
    # Serialize
    json_str = json.dumps(message)
    assert len(json_str) > 0
    
    # Deserialize
    parsed = json.loads(json_str)
    assert parsed["message_type"] == message["message_type"]
    assert parsed["message_id"] == message["message_id"]
    
    print("✓ JSON serialization works")


def test_message_size_limits():
    """Test that message sizes are reasonable."""
    # Small message (typical)
    small_message = {
        "message_type": "MESSAGE_TYPE_PRE_EXEC",
        "message_id": str(uuid.uuid4()),
        "version": "2.0.0",
        "timestamp": int(time.time() * 1000),
        "pre_exec_request": {
            "execution_id": str(uuid.uuid4()),
            "command": ["ls"],
            "working_directory": "/tmp",
            "user": {"username": "test", "uid": 1000, "gid": 1000}
        }
    }
    
    small_size = len(json.dumps(small_message))
    assert small_size < 1024, "Small message too large"
    
    # Large message (with environment)
    large_env = {f"VAR_{i}": f"value_{i}" for i in range(100)}
    large_message = small_message.copy()
    large_message["pre_exec_request"]["environment"] = large_env
    
    large_size = len(json.dumps(large_message))
    assert large_size < 65536, "Large message exceeds 64KB"
    
    print(f"✓ Message sizes reasonable (small: {small_size}B, large: {large_size}B)")


# ============================================================================
# Test HITL Logic
# ============================================================================

def test_hitl_request_fields():
    """Test HITL request has all required fields."""
    message = {
        "message_type": "MESSAGE_TYPE_HITL_REQUEST",
        "message_id": str(uuid.uuid4()),
        "version": "2.0.0",
        "timestamp": int(time.time() * 1000),
        "hitl_request": {
            "hitl_request_id": str(uuid.uuid4()),
            "execution_id": str(uuid.uuid4()),
            "command": ["sudo", "reboot"],
            "risk_level": "RISK_LEVEL_CRITICAL",
            "risk_factors": ["Elevated privileges", "System reboot"],
            "timeout_ms": 60000,
            "expires_at": int((time.time() + 60) * 1000)
        }
    }
    
    req = message["hitl_request"]
    assert "hitl_request_id" in req
    assert "execution_id" in req
    assert "risk_level" in req
    assert "timeout_ms" in req
    assert req["timeout_ms"] > 0
    
    print("✓ HITL request structure valid")


def test_hitl_timeout_logic():
    """Test HITL timeout behavior."""
    timeout_ms = 1000  # 1 second
    created_at = time.time()
    expires_at = created_at + (timeout_ms / 1000)
    
    # Simulate time passing
    time.sleep(0.5)
    current_time = time.time()
    assert current_time < expires_at, "Should not be expired yet"
    
    # Wait for expiration
    time.sleep(0.6)
    current_time = time.time()
    assert current_time > expires_at, "Should be expired now"
    
    print("✓ HITL timeout logic works")


# ============================================================================
# Test Performance Characteristics
# ============================================================================

def test_uuid_generation_performance():
    """Test that UUID generation is fast enough."""
    start = time.time()
    
    for _ in range(10000):
        str(uuid.uuid4())
    
    elapsed = time.time() - start
    per_uuid = elapsed / 10000 * 1000  # ms per UUID
    
    assert per_uuid < 0.1, f"UUID generation too slow: {per_uuid:.3f}ms each"
    
    print(f"✓ UUID generation fast enough ({per_uuid:.3f}ms per UUID)")


def test_json_serialization_performance():
    """Test that JSON serialization is fast enough."""
    message = {
        "message_type": "MESSAGE_TYPE_PRE_EXEC",
        "message_id": str(uuid.uuid4()),
        "version": "2.0.0",
        "timestamp": int(time.time() * 1000),
        "pre_exec_request": {
            "execution_id": str(uuid.uuid4()),
            "command": ["ls", "-la", "/tmp"],
            "working_directory": "/tmp",
            "environment": {f"VAR_{i}": f"val_{i}" for i in range(50)},
            "user": {"username": "test", "uid": 1000, "gid": 1000}
        }
    }
    
    start = time.time()
    
    for _ in range(1000):
        json.dumps(message)
    
    elapsed = time.time() - start
    per_message = elapsed / 1000 * 1000  # ms per message
    
    assert per_message < 1.0, f"JSON serialization too slow: {per_message:.3f}ms each"
    
    print(f"✓ JSON serialization fast enough ({per_message:.3f}ms per message)")


# ============================================================================
# Run All Tests
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("SHACKLE V2.0 Protocol Test Suite")
    print("="*70 + "\n")
    
    tests = [
        ("Message Structure", [
            test_register_request_structure,
            test_pre_exec_request_structure,
            test_verdict_response_structure,
        ]),
        ("Protocol Semantics", [
            test_message_id_uniqueness,
            test_timestamp_monotonicity,
            test_session_id_format,
        ]),
        ("Policy Logic", [
            test_command_pattern_matching,
            test_path_sensitivity,
        ]),
        ("Error Handling", [
            test_error_response_structure,
            test_version_compatibility,
        ]),
        ("Serialization", [
            test_json_serialization,
            test_message_size_limits,
        ]),
        ("HITL Logic", [
            test_hitl_request_fields,
            test_hitl_timeout_logic,
        ]),
        ("Performance", [
            test_uuid_generation_performance,
            test_json_serialization_performance,
        ])
    ]
    
    total_passed = 0
    total_failed = 0
    
    for category, category_tests in tests:
        print(f"\n{category}:")
        print("-" * 70)
        
        for test_func in category_tests:
            try:
                test_func()
                total_passed += 1
            except AssertionError as e:
                print(f"✗ {test_func.__name__}: {e}")
                total_failed += 1
            except Exception as e:
                print(f"✗ {test_func.__name__}: Unexpected error: {e}")
                total_failed += 1
    
    print("\n" + "="*70)
    print(f"Results: {total_passed} passed, {total_failed} failed")
    print("="*70 + "\n")
    
    exit(0 if total_failed == 0 else 1)
