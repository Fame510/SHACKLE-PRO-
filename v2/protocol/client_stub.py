#!/usr/bin/env python3
"""
SHACKLE V2.0 Client Reference Implementation (Stub)

This is a reference implementation showing how to build a SHACKLE client.
It demonstrates the protocol flow but is not production-ready.

Requirements:
    pip install protobuf websockets

Usage:
    from client_stub import ShackleClient
    
    client = ShackleClient(socket_path="/var/run/shackle/guardian.sock")
    await client.connect()
    
    verdict = await client.pre_exec(["ls", "-la", "/tmp"])
    if verdict.verdict == "ALLOW":
        # Execute command
        result = subprocess.run(...)
        await client.post_exec(execution_id, result)
"""

import asyncio
import json
import os
import socket
import struct
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import time
import logging

# Note: In production, import from generated protobuf:
# from shackle.v2 import shackle_pb2


# ============================================================================
# Protocol Enums (mirror protobuf definitions)
# ============================================================================

class Verdict(Enum):
    UNSPECIFIED = 0
    ALLOW = 1
    DENY = 2
    HITL = 3
    MODIFY = 4


class ReasonCode(Enum):
    UNSPECIFIED = 0
    # ALLOW reasons
    POLICY_WHITELIST = 100
    SAFE_OPERATION = 101
    PREVIOUS_APPROVAL = 102
    OPERATOR_OVERRIDE = 103
    CACHED_VERDICT = 104
    # DENY reasons
    POLICY_BLACKLIST = 200
    DANGEROUS_OPERATION = 201
    INSUFFICIENT_PRIVILEGES = 202
    RESOURCE_LIMIT = 203
    TIMEOUT = 204
    HITL_TIMEOUT = 205
    HITL_DENIED = 206
    MALFORMED_REQUEST = 207
    SESSION_INVALID = 208
    RATE_LIMITED = 209
    # HITL reasons
    DESTRUCTIVE_OPERATION = 300
    CRITICAL_SYSTEM_PATH = 301
    UNUSUAL_PATTERN = 302
    POLICY_AMBIGUOUS = 303
    ELEVATED_PRIVILEGES = 304
    NETWORK_OPERATION = 305


class HealthStatus(Enum):
    UNSPECIFIED = 0
    HEALTHY = 1
    DEGRADED = 2
    OVERLOADED = 3
    SHUTTING_DOWN = 4


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class UserContext:
    username: str
    uid: int
    gid: int
    supplementary_gids: List[int] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)
    home_directory: str = ""
    shell: str = ""


@dataclass
class ProcessContext:
    pid: int
    parent_pid: int
    process_group_id: int = 0
    session_id: int = 0
    executable_path: str = ""
    command_line: List[str] = field(default_factory=list)
    terminal: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class ResourceUsage:
    cpu_time_us: int = 0
    max_rss_kb: int = 0
    page_faults: int = 0
    block_input_ops: int = 0
    block_output_ops: int = 0
    voluntary_context_switches: int = 0
    involuntary_context_switches: int = 0


@dataclass
class PreExecResponse:
    verdict: Verdict
    execution_id: str
    reason_code: ReasonCode
    reason_message: str
    modified_command: Optional[List[str]] = None
    timeout_ms: int = 0
    hitl_request_id: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class RegisterResponse:
    session_id: str
    accepted_version: str
    guardian_capabilities: List[str]
    config: Dict[str, str]
    session_expires_at: int


# ============================================================================
# SHACKLE Client
# ============================================================================

class ShackleClient:
    """
    SHACKLE V2.0 Client implementation for Unix socket transport.
    
    This client handles:
    - Connection lifecycle (register, heartbeat, disconnect)
    - Pre-execution authorization requests
    - Post-execution reporting
    - Automatic reconnection on failure
    """
    
    PROTOCOL_VERSION = "2.0.0"
    DEFAULT_SOCKET_PATH = "/var/run/shackle/guardian.sock"
    DEFAULT_TIMEOUT = 5.0  # seconds
    HEARTBEAT_INTERVAL = 30.0  # seconds
    
    def __init__(
        self,
        socket_path: str = DEFAULT_SOCKET_PATH,
        client_id: Optional[str] = None,
        client_version: str = "shackle-client-stub/2.0.0",
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, str]] = None,
        timeout: float = DEFAULT_TIMEOUT,
        fail_secure: bool = True,
        logger: Optional[logging.Logger] = None
    ):
        self.socket_path = socket_path
        self.client_id = client_id or str(uuid.uuid4())
        self.client_version = client_version
        self.capabilities = capabilities or ["hitl", "async", "modify"]
        self.metadata = metadata or self._get_default_metadata()
        self.timeout = timeout
        self.fail_secure = fail_secure  # Deny on connection failure
        self.logger = logger or logging.getLogger(__name__)
        
        # Connection state
        self.socket: Optional[socket.socket] = None
        self.session_id: Optional[str] = None
        self.session_config: Dict[str, str] = {}
        self.guardian_capabilities: List[str] = []
        self.connected = False
        
        # Heartbeat task
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._shutdown = False
    
    def _get_default_metadata(self) -> Dict[str, str]:
        """Generate default client metadata."""
        import platform
        return {
            "hostname": platform.node(),
            "os": platform.system(),
            "pid": str(os.getpid()),
            "user": os.getenv("USER", "unknown"),
        }
    
    # ------------------------------------------------------------------------
    # Connection Management
    # ------------------------------------------------------------------------
    
    async def connect(self) -> bool:
        """
        Connect to Guardian and complete registration handshake.
        
        Returns:
            True if connected successfully, False otherwise.
        """
        try:
            # Create Unix domain socket
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect(self.socket_path)
            
            # Send registration request
            register_request = self._build_register_request()
            await self._send_message(register_request)
            
            # Receive registration response
            response = await self._receive_message()
            
            if response.get("register_response"):
                reg_resp = response["register_response"]
                self.session_id = reg_resp["session_id"]
                self.session_config = reg_resp.get("config", {})
                self.guardian_capabilities = reg_resp.get("guardian_capabilities", [])
                self.connected = True
                
                self.logger.info(f"Connected to Guardian: session={self.session_id}")
                
                # Start heartbeat task
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
                
                return True
            else:
                self.logger.error(f"Registration failed: {response}")
                return False
                
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            return False
    
    async def disconnect(self, reason: str = "Client shutdown"):
        """Gracefully disconnect from Guardian."""
        self._shutdown = True
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        if self.connected and self.socket:
            try:
                disconnect_msg = self._build_disconnect_request(reason)
                await self._send_message(disconnect_msg)
            except Exception as e:
                self.logger.warning(f"Error during disconnect: {e}")
            finally:
                self.socket.close()
                self.connected = False
                self.logger.info("Disconnected from Guardian")
    
    async def _heartbeat_loop(self):
        """Background task to send periodic heartbeats."""
        while not self._shutdown and self.connected:
            try:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                
                heartbeat_msg = self._build_heartbeat_request()
                await self._send_message(heartbeat_msg)
                
                response = await self._receive_message()
                hb_resp = response.get("heartbeat_response", {})
                
                if hb_resp.get("should_reconnect"):
                    self.logger.warning("Guardian requested reconnection")
                    await self.disconnect("Guardian requested reconnect")
                    await self.connect()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Heartbeat failed: {e}")
                self.connected = False
                break
    
    # ------------------------------------------------------------------------
    # Execution Flow
    # ------------------------------------------------------------------------
    
    async def pre_exec(
        self,
        command: List[str],
        working_directory: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        user: Optional[UserContext] = None,
        process: Optional[ProcessContext] = None,
        stdin_preview: Optional[bytes] = None,
        context: Optional[Dict[str, str]] = None,
        execution_id: Optional[str] = None
    ) -> PreExecResponse:
        """
        Request authorization to execute a command.
        
        Args:
            command: Command and arguments (argv)
            working_directory: Current working directory
            environment: Environment variables
            user: User context (defaults to current user)
            process: Process context (defaults to current process)
            stdin_preview: First 4KB of stdin (optional)
            context: Additional context metadata
            execution_id: Unique execution ID (auto-generated if None)
        
        Returns:
            PreExecResponse with verdict and details
        """
        if not self.connected:
            if self.fail_secure:
                return PreExecResponse(
                    verdict=Verdict.DENY,
                    execution_id=execution_id or str(uuid.uuid4()),
                    reason_code=ReasonCode.SESSION_INVALID,
                    reason_message="Not connected to Guardian (fail-secure mode)"
                )
            else:
                # Fail-open: allow execution without authorization
                self.logger.warning("Not connected, fail-open mode: allowing execution")
                return PreExecResponse(
                    verdict=Verdict.ALLOW,
                    execution_id=execution_id or str(uuid.uuid4()),
                    reason_code=ReasonCode.UNSPECIFIED,
                    reason_message="Fail-open: Guardian unavailable"
                )
        
        exec_id = execution_id or str(uuid.uuid4())
        
        # Build request
        pre_exec_msg = self._build_pre_exec_request(
            exec_id, command, working_directory, environment,
            user, process, stdin_preview, context
        )
        
        try:
            # Send request
            await self._send_message(pre_exec_msg)
            
            # Receive response
            response = await self._receive_message()
            
            if "pre_exec_response" in response:
                resp = response["pre_exec_response"]
                return PreExecResponse(
                    verdict=Verdict[resp["verdict"]],
                    execution_id=resp["execution_id"],
                    reason_code=ReasonCode[resp["reason_code"]],
                    reason_message=resp["reason_message"],
                    modified_command=resp.get("modified_command"),
                    timeout_ms=resp.get("timeout_ms", 0),
                    hitl_request_id=resp.get("hitl_request_id"),
                    metadata=resp.get("metadata", {})
                )
            elif "error_response" in response:
                err = response["error_response"]
                self.logger.error(f"Pre-exec error: {err}")
                return PreExecResponse(
                    verdict=Verdict.DENY,
                    execution_id=exec_id,
                    reason_code=ReasonCode.UNSPECIFIED,
                    reason_message=err["error_message"]
                )
            else:
                raise ValueError(f"Unexpected response: {response}")
                
        except Exception as e:
            self.logger.error(f"Pre-exec failed: {e}")
            if self.fail_secure:
                return PreExecResponse(
                    verdict=Verdict.DENY,
                    execution_id=exec_id,
                    reason_code=ReasonCode.TIMEOUT,
                    reason_message=f"Communication error: {e}"
                )
            else:
                return PreExecResponse(
                    verdict=Verdict.ALLOW,
                    execution_id=exec_id,
                    reason_code=ReasonCode.UNSPECIFIED,
                    reason_message=f"Fail-open: {e}"
                )
    
    async def post_exec(
        self,
        execution_id: str,
        exit_code: int,
        duration_ms: int,
        stdout_preview: bytes = b"",
        stderr_preview: bytes = b"",
        stdout_size: int = 0,
        stderr_size: int = 0,
        signal: Optional[int] = None,
        resource_usage: Optional[ResourceUsage] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Report execution outcome to Guardian (fire-and-forget).
        
        Returns:
            True if acknowledged, False otherwise
        """
        if not self.connected:
            self.logger.warning("Not connected, skipping post_exec")
            return False
        
        post_exec_msg = self._build_post_exec_request(
            execution_id, exit_code, duration_ms,
            stdout_preview, stderr_preview, stdout_size, stderr_size,
            signal, resource_usage, error_message
        )
        
        try:
            await self._send_message(post_exec_msg)
            response = await self._receive_message()
            
            if "post_exec_response" in response:
                return response["post_exec_response"].get("acknowledged", False)
            else:
                return False
                
        except Exception as e:
            self.logger.warning(f"Post-exec failed: {e}")
            return False
    
    # ------------------------------------------------------------------------
    # Message Building (JSON representation of protobuf)
    # ------------------------------------------------------------------------
    
    def _build_register_request(self) -> Dict[str, Any]:
        return {
            "message_type": "MESSAGE_TYPE_REGISTER",
            "message_id": str(uuid.uuid4()),
            "version": self.PROTOCOL_VERSION,
            "timestamp": int(time.time() * 1000),
            "register_request": {
                "client_id": self.client_id,
                "client_version": self.client_version,
                "protocol_version": self.PROTOCOL_VERSION,
                "capabilities": self.capabilities,
                "metadata": self.metadata
            }
        }
    
    def _build_heartbeat_request(self) -> Dict[str, Any]:
        return {
            "message_type": "MESSAGE_TYPE_HEARTBEAT",
            "message_id": str(uuid.uuid4()),
            "version": self.PROTOCOL_VERSION,
            "timestamp": int(time.time() * 1000),
            "heartbeat_request": {
                "session_id": self.session_id,
                "status": "HEALTH_STATUS_HEALTHY"
            }
        }
    
    def _build_disconnect_request(self, reason: str) -> Dict[str, Any]:
        return {
            "message_type": "MESSAGE_TYPE_DISCONNECT",
            "message_id": str(uuid.uuid4()),
            "version": self.PROTOCOL_VERSION,
            "timestamp": int(time.time() * 1000),
            "disconnect_request": {
                "session_id": self.session_id,
                "reason": reason,
                "graceful": True
            }
        }
    
    def _build_pre_exec_request(
        self, execution_id: str, command: List[str],
        working_directory: Optional[str], environment: Optional[Dict[str, str]],
        user: Optional[UserContext], process: Optional[ProcessContext],
        stdin_preview: Optional[bytes], context: Optional[Dict[str, str]]
    ) -> Dict[str, Any]:
        
        # Default user context
        if user is None:
            user = UserContext(
                username=os.getenv("USER", "unknown"),
                uid=os.getuid(),
                gid=os.getgid()
            )
        
        # Default process context
        if process is None:
            process = ProcessContext(
                pid=os.getpid(),
                parent_pid=os.getppid()
            )
        
        return {
            "message_type": "MESSAGE_TYPE_PRE_EXEC",
            "message_id": str(uuid.uuid4()),
            "version": self.PROTOCOL_VERSION,
            "timestamp": int(time.time() * 1000),
            "pre_exec_request": {
                "execution_id": execution_id,
                "command": command,
                "working_directory": working_directory or os.getcwd(),
                "environment": environment or dict(os.environ),
                "user": {
                    "username": user.username,
                    "uid": user.uid,
                    "gid": user.gid,
                    "supplementary_gids": user.supplementary_gids,
                    "roles": user.roles,
                    "home_directory": user.home_directory,
                    "shell": user.shell
                },
                "process": {
                    "pid": process.pid,
                    "parent_pid": process.parent_pid,
                    "process_group_id": process.process_group_id,
                    "session_id": process.session_id,
                    "executable_path": process.executable_path,
                    "command_line": process.command_line,
                    "terminal": process.terminal,
                    "metadata": process.metadata
                },
                "context": context or {}
            }
        }
    
    def _build_post_exec_request(
        self, execution_id: str, exit_code: int, duration_ms: int,
        stdout_preview: bytes, stderr_preview: bytes,
        stdout_size: int, stderr_size: int,
        signal: Optional[int], resource_usage: Optional[ResourceUsage],
        error_message: Optional[str]
    ) -> Dict[str, Any]:
        
        req = {
            "message_type": "MESSAGE_TYPE_POST_EXEC",
            "message_id": str(uuid.uuid4()),
            "version": self.PROTOCOL_VERSION,
            "timestamp": int(time.time() * 1000),
            "post_exec_request": {
                "execution_id": execution_id,
                "exit_code": exit_code,
                "duration_ms": duration_ms,
                "stdout_preview": stdout_preview.decode("utf-8", errors="ignore"),
                "stderr_preview": stderr_preview.decode("utf-8", errors="ignore"),
                "stdout_size": stdout_size,
                "stderr_size": stderr_size
            }
        }
        
        if signal is not None:
            req["post_exec_request"]["signal"] = signal
        
        if resource_usage:
            req["post_exec_request"]["resource_usage"] = {
                "cpu_time_us": resource_usage.cpu_time_us,
                "max_rss_kb": resource_usage.max_rss_kb,
                "page_faults": resource_usage.page_faults
            }
        
        if error_message:
            req["post_exec_request"]["error_message"] = error_message
        
        return req
    
    # ------------------------------------------------------------------------
    # Wire Protocol (Unix Socket Framing)
    # ------------------------------------------------------------------------
    
    async def _send_message(self, message: Dict[str, Any]):
        """Send a message over Unix socket with length-prefixed framing."""
        # In production, serialize to protobuf here
        # For stub, we use JSON
        payload = json.dumps(message).encode("utf-8")
        
        # Length-prefixed framing: 4 bytes big-endian length + payload
        length = struct.pack(">I", len(payload))
        
        self.socket.sendall(length + payload)
    
    async def _receive_message(self) -> Dict[str, Any]:
        """Receive a length-prefixed message from Unix socket."""
        # Read 4-byte length header
        length_data = self._recv_exact(4)
        length = struct.unpack(">I", length_data)[0]
        
        # Read payload
        payload = self._recv_exact(length)
        
        # In production, deserialize from protobuf here
        # For stub, we use JSON
        return json.loads(payload.decode("utf-8"))
    
    def _recv_exact(self, n: int) -> bytes:
        """Receive exactly n bytes from socket."""
        data = b""
        while len(data) < n:
            chunk = self.socket.recv(n - len(data))
            if not chunk:
                raise ConnectionError("Socket closed")
            data += chunk
        return data


# ============================================================================
# Example Usage
# ============================================================================

async def example_usage():
    """Demonstrate basic SHACKLE client usage."""
    
    logging.basicConfig(level=logging.INFO)
    
    client = ShackleClient(
        socket_path="/var/run/shackle/guardian.sock",
        fail_secure=True
    )
    
    # Connect to Guardian
    if not await client.connect():
        print("Failed to connect to Guardian")
        return
    
    try:
        # Request authorization for a command
        verdict = await client.pre_exec(
            command=["ls", "-la", "/tmp"],
            context={"shell": "bash", "source": "interactive"}
        )
        
        print(f"Verdict: {verdict.verdict.name}")
        print(f"Reason: {verdict.reason_message}")
        
        if verdict.verdict == Verdict.ALLOW:
            # Execute command (simplified)
            import subprocess
            start_time = time.time()
            
            result = subprocess.run(
                verdict.modified_command or ["ls", "-la", "/tmp"],
                capture_output=True,
                timeout=verdict.timeout_ms / 1000 if verdict.timeout_ms else None
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Report outcome
            await client.post_exec(
                execution_id=verdict.execution_id,
                exit_code=result.returncode,
                duration_ms=duration_ms,
                stdout_preview=result.stdout[:4096],
                stderr_preview=result.stderr[:4096],
                stdout_size=len(result.stdout),
                stderr_size=len(result.stderr)
            )
            
            print(f"Command executed successfully")
        
        elif verdict.verdict == Verdict.DENY:
            print(f"Command denied: {verdict.reason_message}")
        
        elif verdict.verdict == Verdict.HITL:
            print(f"Waiting for human approval (HITL ID: {verdict.hitl_request_id})")
            # In production, poll for HITL resolution
        
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(example_usage())
