"""
SHACKLE V2.0 Protocol - Python Client Reference Implementation

This is a reference implementation demonstrating how to implement a SHACKLE client.
It includes connection handling, message serialization, and the core client API.

Language-agnostic: This pattern can be adapted to Rust, Go, TypeScript, etc.
"""

import asyncio
import json
import struct
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
import hashlib
import time
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Enums (Mirror shackle.proto)
# ============================================================================


class MessageType(Enum):
    """Protocol message types"""
    CLIENT_HELLO = 1
    SERVER_HELLO = 2
    HEARTBEAT = 3
    HEARTBEAT_RESPONSE = 4
    REGISTER = 5
    REGISTER_RESPONSE = 6
    PRE_EXEC_REQUEST = 10
    PRE_EXEC_RESPONSE = 11
    POST_EXEC_LOG = 12
    POST_EXEC_ACK = 13
    HITL_POLL_REQUEST = 22
    HITL_POLL_RESPONSE = 23
    LICENSE_CHECK = 30
    LICENSE_RESPONSE = 31
    ERROR = 99


class Verdict(Enum):
    """Pre-execution verdict"""
    ALLOW = "ALLOW"
    DENY = "DENY"
    HITL = "HITL"


class RiskLevel(Enum):
    """Operation risk levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ExecutionStatus(Enum):
    """Post-execution status"""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"
    PARTIAL = "PARTIAL"


class HITLStatus(Enum):
    """HITL request status"""
    PENDING = "PENDING"
    DECIDED = "DECIDED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


# ============================================================================
# Data Classes (Protocol Messages)
# ============================================================================


@dataclass
class OperationDescriptor:
    """Describes an operation to be executed"""
    operation_type: str
    operation_name: str
    risk_level: RiskLevel = RiskLevel.MEDIUM
    tags: List[str] = field(default_factory=list)
    description: Optional[str] = None
    parameters_json: Optional[str] = None
    content_hash: Optional[bytes] = None
    content_size_bytes: int = 0
    estimated_duration_ms: int = 0
    estimated_cost_cents: int = 0

    def compute_content_hash(self, data: Union[str, bytes, Dict]) -> bytes:
        """Compute SHA256 hash for zero-knowledge mode"""
        if isinstance(data, dict):
            data = json.dumps(data, sort_keys=True)
        if isinstance(data, str):
            data = data.encode('utf-8')
        return hashlib.sha256(data).digest()


@dataclass
class ExecutionContext:
    """Context about the execution environment"""
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    recursion_depth: int = 0
    call_chain: List[str] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)
    source_file: Optional[str] = None
    source_line: Optional[int] = None
    source_function: Optional[str] = None
    initiated_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))


@dataclass
class PreExecResponse:
    """Response from pre-execution check"""
    verdict: Verdict
    reason: str
    reason_code: str
    audit_id: str
    decision_time_ms: int
    hitl_request_id: Optional[str] = None
    hitl_timeout_ms: Optional[int] = None
    modifications: Dict[str, str] = field(default_factory=dict)
    policy_version: Optional[str] = None
    matched_rules: List[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """Result of operation execution"""
    status: ExecutionStatus
    result_hash: Optional[bytes] = None
    result_size_bytes: int = 0
    summary: Optional[str] = None
    result_json: Optional[str] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    stack_trace: Optional[str] = None


@dataclass
class HITLDecision:
    """Human decision for HITL request"""
    verdict: Verdict
    approver_id: str
    approver_name: str
    reason: str
    decided_at_ms: int


# ============================================================================
# Transport Layer (Abstract)
# ============================================================================


class Transport(ABC):
    """Abstract transport layer for protocol communication"""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to daemon"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection"""
        pass

    @abstractmethod
    async def send_message(self, message_type: MessageType, payload: Dict[str, Any]) -> None:
        """Send a message to the daemon"""
        pass

    @abstractmethod
    async def receive_message(self, timeout_ms: int = 5000) -> tuple[MessageType, Dict[str, Any]]:
        """Receive a message from the daemon"""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connection is active"""
        pass


class UnixSocketTransport(Transport):
    """Unix domain socket transport implementation"""

    def __init__(self, socket_path: str = "/var/run/shackle/shackle.sock"):
        self.socket_path = socket_path
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

    async def connect(self) -> None:
        """Connect to Unix socket"""
        self.reader, self.writer = await asyncio.open_unix_connection(self.socket_path)
        logger.info(f"Connected to SHACKLE daemon via {self.socket_path}")

    async def disconnect(self) -> None:
        """Close Unix socket connection"""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.reader = None
        self.writer = None
        logger.info("Disconnected from SHACKLE daemon")

    async def send_message(self, message_type: MessageType, payload: Dict[str, Any]) -> None:
        """Send length-prefixed JSON message"""
        if not self.writer:
            raise RuntimeError("Not connected")

        # Create envelope
        envelope = {
            "message_id": str(uuid.uuid4()),
            "protocol_version": 200,
            "timestamp_ms": int(time.time() * 1000),
            "type": message_type.name,
            "payload": payload
        }

        # Serialize to JSON
        message_bytes = json.dumps(envelope).encode('utf-8')
        length = len(message_bytes)

        # Send: [4 bytes length][message bytes]
        self.writer.write(struct.pack('>I', length))
        self.writer.write(message_bytes)
        await self.writer.drain()

    async def receive_message(self, timeout_ms: int = 5000) -> tuple[MessageType, Dict[str, Any]]:
        """Receive length-prefixed JSON message"""
        if not self.reader:
            raise RuntimeError("Not connected")

        # Read length (4 bytes, big-endian)
        length_bytes = await asyncio.wait_for(
            self.reader.readexactly(4),
            timeout=timeout_ms / 1000.0
        )
        length = struct.unpack('>I', length_bytes)[0]

        # Read message
        message_bytes = await asyncio.wait_for(
            self.reader.readexactly(length),
            timeout=timeout_ms / 1000.0
        )

        # Parse envelope
        envelope = json.loads(message_bytes.decode('utf-8'))
        message_type = MessageType[envelope["type"]]
        payload = envelope["payload"]

        return message_type, payload

    def is_connected(self) -> bool:
        return self.writer is not None and not self.writer.is_closing()


# ============================================================================
# SHACKLE Client
# ============================================================================


class ShackleClient:
    """
    SHACKLE V2.0 Protocol Client

    Usage:
        async with ShackleClient() as client:
            response = await client.pre_exec_check(operation, context)
            if response.verdict == Verdict.ALLOW:
                result = execute_operation()
                await client.post_exec_log(operation_id, result)
    """

    def __init__(
        self,
        transport: Optional[Transport] = None,
        agent_id: Optional[str] = None,
        agent_name: str = "UnnamedAgent",
        agent_version: str = "1.0.0",
        license_key: Optional[str] = None,
        fallback_to_v1: bool = True
    ):
        self.transport = transport or UnixSocketTransport()
        self.agent_id = agent_id or f"agent-{uuid.uuid4().hex[:8]}"
        self.agent_name = agent_name
        self.agent_version = agent_version
        self.license_key = license_key
        self.fallback_to_v1 = fallback_to_v1

        self.session_id: Optional[str] = None
        self.server_capabilities: Dict[str, Any] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._connected = False

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()

    async def connect(self) -> None:
        """Establish connection and register with daemon"""
        try:
            # Connect transport
            await self.transport.connect()

            # Send CLIENT_HELLO
            await self.transport.send_message(MessageType.CLIENT_HELLO, {
                "supported_versions": [200, 100],
                "client_id": self.agent_id,
                "client_version": self.agent_version,
                "metadata": {
                    "language": "python",
                    "framework": "reference-implementation"
                }
            })

            # Receive SERVER_HELLO
            msg_type, payload = await self.transport.receive_message()
            if msg_type != MessageType.SERVER_HELLO:
                raise RuntimeError(f"Expected SERVER_HELLO, got {msg_type}")

            self.server_capabilities = payload.get("capabilities", {})
            logger.info(f"Connected to SHACKLE daemon (version {payload['selected_version']})")

            # Register agent
            await self._register()

            # Start heartbeat
            self._start_heartbeat()

            self._connected = True

        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            if self.fallback_to_v1:
                logger.warning("Falling back to V1 in-process mode")
                # TODO: Initialize V1 fallback
            raise

    async def disconnect(self) -> None:
        """Disconnect from daemon"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        await self.transport.disconnect()
        self._connected = False
        logger.info("Disconnected from SHACKLE daemon")

    async def _register(self) -> None:
        """Register agent with daemon"""
        await self.transport.send_message(MessageType.REGISTER, {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_version": self.agent_version,
            "environment": "development",
            "metadata": {},
            "capabilities": [],
            "license_key": self.license_key or ""
        })

        msg_type, payload = await self.transport.receive_message()
        if msg_type == MessageType.ERROR:
            raise RuntimeError(f"Registration failed: {payload['message']}")

        if msg_type != MessageType.REGISTER_RESPONSE:
            raise RuntimeError(f"Expected REGISTER_RESPONSE, got {msg_type}")

        if not payload.get("success"):
            raise RuntimeError(f"Registration failed: {payload.get('error_message')}")

        self.session_id = payload["session_id"]
        logger.info(f"Registered with session ID: {self.session_id}")

    def _start_heartbeat(self, interval_ms: int = 30000) -> None:
        """Start background heartbeat task"""
        async def heartbeat_loop():
            while True:
                try:
                    await asyncio.sleep(interval_ms / 1000.0)
                    await self._send_heartbeat()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Heartbeat error: {e}")

        self._heartbeat_task = asyncio.create_task(heartbeat_loop())

    async def _send_heartbeat(self) -> None:
        """Send heartbeat to daemon"""
        await self.transport.send_message(MessageType.HEARTBEAT, {
            "session_id": self.session_id,
            "uptime_ms": 0,  # TODO: track actual uptime
            "operations_total": 0,
            "operations_success": 0,
            "operations_failed": 0
        })

        # Receive response (non-blocking)
        try:
            msg_type, payload = await asyncio.wait_for(
                self.transport.receive_message(),
                timeout=1.0
            )
            if msg_type == MessageType.HEARTBEAT_RESPONSE:
                logger.debug("Heartbeat acknowledged")
        except asyncio.TimeoutError:
            pass

    # ========================================================================
    # Core API Methods
    # ========================================================================

    async def pre_exec_check(
        self,
        operation: OperationDescriptor,
        context: Optional[ExecutionContext] = None,
        timeout_ms: int = 5000,
        zero_knowledge: bool = False
    ) -> PreExecResponse:
        """
        Request pre-execution permission from daemon.

        Args:
            operation: Operation descriptor
            context: Execution context (optional)
            timeout_ms: Maximum time to wait for decision
            zero_knowledge: Use content hashing instead of full parameters

        Returns:
            PreExecResponse with verdict and metadata

        Raises:
            RuntimeError: If not connected or request fails
        """
        if not self._connected:
            raise RuntimeError("Not connected to daemon")

        operation_id = str(uuid.uuid4())
        context = context or ExecutionContext()

        # Build request payload
        payload = {
            "session_id": self.session_id,
            "operation_id": operation_id,
            "operation": {
                "operation_type": operation.operation_type,
                "operation_name": operation.operation_name,
                "risk_level": operation.risk_level.value,
                "tags": operation.tags,
                "description": operation.description,
                "parameters_json": operation.parameters_json,
            },
            "context": {
                "user_id": context.user_id,
                "conversation_id": context.conversation_id,
                "recursion_depth": context.recursion_depth,
                "call_chain": context.call_chain,
                "environment": context.environment,
                "initiated_at_ms": context.initiated_at_ms,
            },
            "timeout_ms": timeout_ms,
            "zero_knowledge": zero_knowledge
        }

        if zero_knowledge and operation.content_hash:
            payload["operation"]["content_hash"] = operation.content_hash.hex()
            payload["operation"]["content_size_bytes"] = operation.content_size_bytes

        # Send request
        await self.transport.send_message(MessageType.PRE_EXEC_REQUEST, payload)

        # Receive response
        msg_type, response_payload = await self.transport.receive_message(timeout_ms)

        if msg_type == MessageType.ERROR:
            raise RuntimeError(f"Pre-exec check failed: {response_payload['message']}")

        if msg_type != MessageType.PRE_EXEC_RESPONSE:
            raise RuntimeError(f"Expected PRE_EXEC_RESPONSE, got {msg_type}")

        # Parse response
        return PreExecResponse(
            verdict=Verdict(response_payload["verdict"]),
            reason=response_payload["reason"],
            reason_code=response_payload["reason_code"],
            audit_id=response_payload["audit_id"],
            decision_time_ms=response_payload["decision_time_ms"],
            hitl_request_id=response_payload.get("hitl_request_id"),
            hitl_timeout_ms=response_payload.get("hitl_timeout_ms"),
            modifications=response_payload.get("modifications", {}),
            policy_version=response_payload.get("policy_version"),
            matched_rules=response_payload.get("matched_rules", [])
        )

    async def post_exec_log(
        self,
        operation_id: str,
        result: ExecutionResult,
        execution_time_ms: int,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Log execution result to daemon.

        Args:
            operation_id: Operation ID from pre_exec_check
            result: Execution result
            execution_time_ms: How long execution took
            metadata: Optional metadata

        Returns:
            Audit ID

        Raises:
            RuntimeError: If not connected or logging fails
        """
        if not self._connected:
            raise RuntimeError("Not connected to daemon")

        payload = {
            "session_id": self.session_id,
            "operation_id": operation_id,
            "result": {
                "status": result.status.value,
                "result_size_bytes": result.result_size_bytes,
                "summary": result.summary,
                "error_message": result.error_message,
                "error_code": result.error_code,
            },
            "execution_time_ms": execution_time_ms,
            "completed_at_ms": int(time.time() * 1000),
            "metadata": metadata or {}
        }

        if result.result_hash:
            payload["result"]["result_hash"] = result.result_hash.hex()

        # Send log
        await self.transport.send_message(MessageType.POST_EXEC_LOG, payload)

        # Receive acknowledgment (non-blocking)
        try:
            msg_type, response_payload = await asyncio.wait_for(
                self.transport.receive_message(),
                timeout=1.0
            )
            if msg_type == MessageType.POST_EXEC_ACK:
                return response_payload["audit_id"]
        except asyncio.TimeoutError:
            logger.warning("Post-exec log acknowledgment timed out")
            return ""

    async def poll_hitl_decision(
        self,
        hitl_request_id: str,
        timeout_ms: int = 30000
    ) -> Optional[HITLDecision]:
        """
        Poll for HITL decision.

        Args:
            hitl_request_id: HITL request ID from pre_exec_check
            timeout_ms: How long to wait for decision (0 = immediate, -1 = block forever)

        Returns:
            HITLDecision if decided, None if still pending

        Raises:
            RuntimeError: If request fails or times out
        """
        if not self._connected:
            raise RuntimeError("Not connected to daemon")

        await self.transport.send_message(MessageType.HITL_POLL_REQUEST, {
            "hitl_request_id": hitl_request_id,
            "timeout_ms": timeout_ms
        })

        msg_type, payload = await self.transport.receive_message(timeout_ms + 1000)

        if msg_type == MessageType.ERROR:
            raise RuntimeError(f"HITL poll failed: {payload['message']}")

        if msg_type != MessageType.HITL_POLL_RESPONSE:
            raise RuntimeError(f"Expected HITL_POLL_RESPONSE, got {msg_type}")

        status = HITLStatus(payload["status"])

        if status == HITLStatus.DECIDED:
            decision = payload["decision"]
            return HITLDecision(
                verdict=Verdict(decision["verdict"]),
                approver_id=decision["approver_id"],
                approver_name=decision["approver_name"],
                reason=decision["reason"],
                decided_at_ms=decision["decided_at_ms"]
            )
        elif status == HITLStatus.TIMEOUT:
            raise RuntimeError("HITL request timed out")
        elif status == HITLStatus.CANCELLED:
            raise RuntimeError("HITL request was cancelled")
        else:
            return None  # Still pending


# ============================================================================
# Decorator API (Pythonic Interface)
# ============================================================================


def shackle(
    operation_type: str,
    operation_name: str,
    risk_level: RiskLevel = RiskLevel.MEDIUM,
    tags: Optional[List[str]] = None,
    zero_knowledge: bool = False
):
    """
    Decorator for SHACKLE-protected functions.

    Usage:
        @shackle("tool_call", "exec.shell", risk_level=RiskLevel.HIGH)
        def run_command(cmd: str):
            return subprocess.run(cmd, shell=True)

    The decorator will:
    1. Request pre-execution permission
    2. Execute function if ALLOW
    3. Block if DENY
    4. Wait for human approval if HITL
    5. Log execution result
    """
    def decorator(func: Callable):
        async def async_wrapper(*args, **kwargs):
            # TODO: Get client from context or global
            client = None  # Placeholder

            # Create operation descriptor
            operation = OperationDescriptor(
                operation_type=operation_type,
                operation_name=operation_name,
                risk_level=risk_level,
                tags=tags or [],
                parameters_json=json.dumps({"args": args, "kwargs": kwargs})
            )

            # Pre-execution check
            response = await client.pre_exec_check(operation, zero_knowledge=zero_knowledge)

            if response.verdict == Verdict.DENY:
                raise PermissionError(f"SHACKLE: {response.reason}")

            if response.verdict == Verdict.HITL:
                # Wait for human decision
                decision = await client.poll_hitl_decision(
                    response.hitl_request_id,
                    timeout_ms=response.hitl_timeout_ms
                )
                if decision.verdict == Verdict.DENY:
                    raise PermissionError(f"SHACKLE: Human denied - {decision.reason}")

            # Execute function
            start_time = time.time()
            try:
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                execution_status = ExecutionStatus.SUCCESS
                error_msg = None
            except Exception as e:
                result = None
                execution_status = ExecutionStatus.FAILURE
                error_msg = str(e)
                raise
            finally:
                # Post-execution log
                execution_time_ms = int((time.time() - start_time) * 1000)
                exec_result = ExecutionResult(
                    status=execution_status,
                    error_message=error_msg
                )
                await client.post_exec_log(
                    response.audit_id,
                    exec_result,
                    execution_time_ms
                )

            return result

        return async_wrapper
    return decorator


# ============================================================================
# Example Usage
# ============================================================================


async def example_usage():
    """Example of using the SHACKLE client"""

    # Create and connect client
    async with ShackleClient(
        agent_name="ExampleAgent",
        agent_version="1.0.0",
        license_key="SHACKLE-TRIAL-XXXXX"
    ) as client:

        # Define an operation
        operation = OperationDescriptor(
            operation_type="tool_call",
            operation_name="fs.read",
            risk_level=RiskLevel.LOW,
            tags=["filesystem", "read"],
            description="Read config file",
            parameters_json='{"path": "/etc/app/config.yaml"}'
        )

        # Check if operation is allowed
        response = await client.pre_exec_check(operation)

        print(f"Verdict: {response.verdict.value}")
        print(f"Reason: {response.reason}")

        if response.verdict == Verdict.ALLOW:
            # Execute operation
            # result = do_file_read()

            # Log result
            exec_result = ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                summary="File read successfully"
            )
            await client.post_exec_log("op_123", exec_result, execution_time_ms=50)

        elif response.verdict == Verdict.HITL:
            # Wait for human decision
            print("Waiting for human approval...")
            decision = await client.poll_hitl_decision(
                response.hitl_request_id,
                timeout_ms=60000
            )
            print(f"Human decision: {decision.verdict.value}")


if __name__ == "__main__":
    asyncio.run(example_usage())
