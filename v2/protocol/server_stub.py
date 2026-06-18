#!/usr/bin/env python3
"""
SHACKLE V2.0 Guardian (Server) Reference Implementation (Stub)

This is a reference implementation showing how to build a SHACKLE Guardian.
It demonstrates the protocol flow but is not production-ready.

Requirements:
    pip install protobuf websockets

Usage:
    python server_stub.py --socket /var/run/shackle/guardian.sock
    
    Or for WebSocket:
    python server_stub.py --websocket --port 8765
"""

import asyncio
import json
import os
import socket
import struct
import uuid
import time
import logging
import argparse
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from pathlib import Path


# ============================================================================
# Protocol Enums
# ============================================================================

class Verdict(Enum):
    ALLOW = "VERDICT_ALLOW"
    DENY = "VERDICT_DENY"
    HITL = "VERDICT_HITL"
    MODIFY = "VERDICT_MODIFY"


class ReasonCode(Enum):
    # ALLOW reasons
    POLICY_WHITELIST = "REASON_POLICY_WHITELIST"
    SAFE_OPERATION = "REASON_SAFE_OPERATION"
    CACHED_VERDICT = "REASON_CACHED_VERDICT"
    
    # DENY reasons
    POLICY_BLACKLIST = "REASON_POLICY_BLACKLIST"
    DANGEROUS_OPERATION = "REASON_DANGEROUS_OPERATION"
    INSUFFICIENT_PRIVILEGES = "REASON_INSUFFICIENT_PRIVILEGES"
    TIMEOUT = "REASON_TIMEOUT"
    SESSION_INVALID = "REASON_SESSION_INVALID"
    
    # HITL reasons
    DESTRUCTIVE_OPERATION = "REASON_DESTRUCTIVE_OPERATION"
    CRITICAL_SYSTEM_PATH = "REASON_CRITICAL_SYSTEM_PATH"
    ELEVATED_PRIVILEGES = "REASON_ELEVATED_PRIVILEGES"


class RiskLevel(Enum):
    LOW = "RISK_LEVEL_LOW"
    MEDIUM = "RISK_LEVEL_MEDIUM"
    HIGH = "RISK_LEVEL_HIGH"
    CRITICAL = "RISK_LEVEL_CRITICAL"


# ============================================================================
# Session Management
# ============================================================================

@dataclass
class Session:
    session_id: str
    client_id: str
    client_version: str
    protocol_version: str
    capabilities: List[str]
    metadata: Dict[str, str]
    created_at: float
    last_heartbeat: float
    expires_at: float


class SessionManager:
    """Manage client sessions."""
    
    SESSION_TIMEOUT = 3600.0  # 1 hour
    STALE_HEARTBEAT_THRESHOLD = 90.0  # 3 missed heartbeats
    
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.logger = logging.getLogger(__name__)
    
    def create_session(
        self, client_id: str, client_version: str,
        protocol_version: str, capabilities: List[str],
        metadata: Dict[str, str]
    ) -> Session:
        """Create a new session."""
        session_id = str(uuid.uuid4())
        now = time.time()
        
        session = Session(
            session_id=session_id,
            client_id=client_id,
            client_version=client_version,
            protocol_version=protocol_version,
            capabilities=capabilities,
            metadata=metadata,
            created_at=now,
            last_heartbeat=now,
            expires_at=now + self.SESSION_TIMEOUT
        )
        
        self.sessions[session_id] = session
        self.logger.info(f"Created session {session_id} for client {client_id}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        return self.sessions.get(session_id)
    
    def update_heartbeat(self, session_id: str) -> bool:
        """Update session heartbeat timestamp."""
        session = self.sessions.get(session_id)
        if session:
            session.last_heartbeat = time.time()
            return True
        return False
    
    def is_valid(self, session_id: str) -> bool:
        """Check if session is valid and not expired."""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        now = time.time()
        if now > session.expires_at:
            self.logger.warning(f"Session {session_id} expired")
            del self.sessions[session_id]
            return False
        
        if now - session.last_heartbeat > self.STALE_HEARTBEAT_THRESHOLD:
            self.logger.warning(f"Session {session_id} stale (no heartbeat)")
            return False
        
        return True
    
    def remove_session(self, session_id: str):
        """Remove a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self.logger.info(f"Removed session {session_id}")
    
    def cleanup_stale_sessions(self):
        """Remove expired and stale sessions."""
        now = time.time()
        to_remove = []
        
        for session_id, session in self.sessions.items():
            if now > session.expires_at or \
               now - session.last_heartbeat > self.STALE_HEARTBEAT_THRESHOLD:
                to_remove.append(session_id)
        
        for session_id in to_remove:
            self.remove_session(session_id)


# ============================================================================
# Policy Engine
# ============================================================================

@dataclass
class PolicyRule:
    """Represents a policy rule."""
    name: str
    verdict: Verdict
    reason_code: ReasonCode
    reason_message: str
    priority: int = 100  # Lower = higher priority
    
    # Rule conditions
    command_patterns: List[str] = field(default_factory=list)
    path_patterns: List[str] = field(default_factory=list)
    user_patterns: List[str] = field(default_factory=list)
    
    # HITL configuration
    requires_hitl: bool = False
    risk_level: Optional[RiskLevel] = None


class PolicyEngine:
    """Simple rule-based policy engine for command authorization."""
    
    def __init__(self):
        self.rules: List[PolicyRule] = []
        self.logger = logging.getLogger(__name__)
        self._load_default_rules()
    
    def _load_default_rules(self):
        """Load default policy rules."""
        
        # DENY rules (high priority)
        self.rules.append(PolicyRule(
            name="block-rm-rf-root",
            verdict=Verdict.DENY,
            reason_code=ReasonCode.DANGEROUS_OPERATION,
            reason_message="Destructive operation: rm -rf on root directory",
            priority=10,
            command_patterns=["rm -rf /", "rm -rf /*"]
        ))
        
        self.rules.append(PolicyRule(
            name="block-critical-paths",
            verdict=Verdict.DENY,
            reason_code=ReasonCode.CRITICAL_SYSTEM_PATH,
            reason_message="Operation on critical system directory blocked",
            priority=20,
            path_patterns=["/etc", "/boot", "/sys", "/proc"]
        ))
        
        # HITL rules (medium priority)
        self.rules.append(PolicyRule(
            name="sudo-requires-approval",
            verdict=Verdict.HITL,
            reason_code=ReasonCode.ELEVATED_PRIVILEGES,
            reason_message="Sudo command requires human approval",
            priority=50,
            command_patterns=["sudo"],
            requires_hitl=True,
            risk_level=RiskLevel.HIGH
        ))
        
        self.rules.append(PolicyRule(
            name="destructive-ops-approval",
            verdict=Verdict.HITL,
            reason_code=ReasonCode.DESTRUCTIVE_OPERATION,
            reason_message="Destructive operation requires approval",
            priority=60,
            command_patterns=["rm", "dd", "mkfs", "fdisk"],
            requires_hitl=True,
            risk_level=RiskLevel.MEDIUM
        ))
        
        # ALLOW rules (low priority)
        self.rules.append(PolicyRule(
            name="allow-read-operations",
            verdict=Verdict.ALLOW,
            reason_code=ReasonCode.SAFE_OPERATION,
            reason_message="Read-only operation allowed",
            priority=100,
            command_patterns=["ls", "cat", "grep", "find", "echo", "pwd", "which"]
        ))
        
        self.logger.info(f"Loaded {len(self.rules)} policy rules")
    
    def evaluate(self, command: List[str], working_dir: str, user: str) -> PolicyRule:
        """
        Evaluate command against policy rules.
        
        Returns the first matching rule (by priority), or default ALLOW.
        """
        command_str = " ".join(command)
        command_name = command[0] if command else ""
        
        # Sort rules by priority
        sorted_rules = sorted(self.rules, key=lambda r: r.priority)
        
        for rule in sorted_rules:
            # Check command patterns
            if rule.command_patterns:
                matched = False
                for pattern in rule.command_patterns:
                    if pattern in command_str or pattern == command_name:
                        matched = True
                        break
                if not matched:
                    continue
            
            # Check path patterns (if command includes paths)
            if rule.path_patterns:
                matched = False
                for pattern in rule.path_patterns:
                    if any(pattern in arg for arg in command):
                        matched = True
                        break
                if rule.path_patterns and not matched:
                    continue
            
            # Check user patterns
            if rule.user_patterns:
                if not any(pattern == user or pattern == "*" for pattern in rule.user_patterns):
                    continue
            
            # Rule matched
            self.logger.info(f"Rule '{rule.name}' matched for command: {command_str}")
            return rule
        
        # Default: ALLOW
        return PolicyRule(
            name="default-allow",
            verdict=Verdict.ALLOW,
            reason_code=ReasonCode.SAFE_OPERATION,
            reason_message="No matching policy, default allow",
            priority=999
        )


# ============================================================================
# HITL Queue
# ============================================================================

@dataclass
class HitlRequest:
    """Represents a pending HITL request."""
    hitl_request_id: str
    execution_id: str
    command: List[str]
    risk_level: RiskLevel
    risk_factors: List[str]
    context: Dict[str, Any]
    created_at: float
    expires_at: float
    resolved: bool = False
    verdict: Optional[Verdict] = None
    operator_id: Optional[str] = None


class HitlQueue:
    """Manage pending human-in-the-loop requests."""
    
    DEFAULT_TIMEOUT_MS = 60000  # 1 minute
    
    def __init__(self):
        self.pending: Dict[str, HitlRequest] = {}
        self.logger = logging.getLogger(__name__)
    
    def create_request(
        self, execution_id: str, command: List[str],
        risk_level: RiskLevel, risk_factors: List[str],
        context: Dict[str, Any], timeout_ms: int = DEFAULT_TIMEOUT_MS
    ) -> HitlRequest:
        """Create a new HITL request."""
        hitl_id = str(uuid.uuid4())
        now = time.time()
        
        request = HitlRequest(
            hitl_request_id=hitl_id,
            execution_id=execution_id,
            command=command,
            risk_level=risk_level,
            risk_factors=risk_factors,
            context=context,
            created_at=now,
            expires_at=now + (timeout_ms / 1000)
        )
        
        self.pending[hitl_id] = request
        self.logger.info(f"Created HITL request {hitl_id} for execution {execution_id}")
        return request
    
    def get_request(self, hitl_request_id: str) -> Optional[HitlRequest]:
        """Get HITL request by ID."""
        return self.pending.get(hitl_request_id)
    
    def resolve_request(
        self, hitl_request_id: str, verdict: Verdict,
        operator_id: str
    ) -> bool:
        """Resolve a HITL request with operator's decision."""
        request = self.pending.get(hitl_request_id)
        if not request:
            return False
        
        request.resolved = True
        request.verdict = verdict
        request.operator_id = operator_id
        
        self.logger.info(f"HITL {hitl_request_id} resolved: {verdict.value} by {operator_id}")
        return True
    
    def cleanup_expired(self):
        """Auto-deny expired HITL requests."""
        now = time.time()
        expired = []
        
        for hitl_id, request in self.pending.items():
            if not request.resolved and now > request.expires_at:
                request.resolved = True
                request.verdict = Verdict.DENY
                request.operator_id = "system:timeout"
                expired.append(hitl_id)
        
        if expired:
            self.logger.warning(f"Auto-denied {len(expired)} expired HITL requests")


# ============================================================================
# SHACKLE Guardian (Server)
# ============================================================================

class ShackleGuardian:
    """SHACKLE V2.0 Guardian server implementation."""
    
    PROTOCOL_VERSION = "2.0.0"
    CAPABILITIES = ["hitl", "async", "batch", "streaming", "modify"]
    
    def __init__(
        self,
        socket_path: Optional[str] = None,
        websocket_port: Optional[int] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.socket_path = socket_path
        self.websocket_port = websocket_port
        self.logger = logger or logging.getLogger(__name__)
        
        # Components
        self.session_manager = SessionManager()
        self.policy_engine = PolicyEngine()
        self.hitl_queue = HitlQueue()
        
        # State
        self.server_socket: Optional[socket.socket] = None
        self.shutdown = False
        
        # Stats
        self.stats = {
            "total_requests": 0,
            "verdicts": {"ALLOW": 0, "DENY": 0, "HITL": 0},
            "sessions": 0
        }
    
    # ------------------------------------------------------------------------
    # Server Lifecycle
    # ------------------------------------------------------------------------
    
    async def start(self):
        """Start the Guardian server."""
        if self.socket_path:
            await self._start_unix_server()
        elif self.websocket_port:
            await self._start_websocket_server()
        else:
            raise ValueError("Must specify either socket_path or websocket_port")
    
    async def _start_unix_server(self):
        """Start Unix domain socket server."""
        # Create socket directory if needed
        socket_dir = os.path.dirname(self.socket_path)
        os.makedirs(socket_dir, exist_ok=True)
        
        # Remove stale socket file
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        
        # Create server socket
        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_socket.bind(self.socket_path)
        self.server_socket.listen(128)
        
        # Set permissions
        os.chmod(self.socket_path, 0o660)
        
        self.logger.info(f"Guardian listening on {self.socket_path}")
        
        # Start background tasks
        asyncio.create_task(self._cleanup_loop())
        
        # Accept connections
        while not self.shutdown:
            try:
                client_sock, _ = self.server_socket.accept()
                asyncio.create_task(self._handle_client(client_sock))
            except Exception as e:
                if not self.shutdown:
                    self.logger.error(f"Accept error: {e}")
    
    async def _start_websocket_server(self):
        """Start WebSocket server (stub - requires websockets library)."""
        self.logger.info(f"WebSocket server on port {self.websocket_port} (not implemented in stub)")
        # TODO: Implement WebSocket support
    
    async def stop(self):
        """Stop the Guardian server."""
        self.shutdown = True
        if self.server_socket:
            self.server_socket.close()
        if self.socket_path and os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        self.logger.info("Guardian stopped")
    
    async def _cleanup_loop(self):
        """Background task to cleanup stale sessions and HITL requests."""
        while not self.shutdown:
            await asyncio.sleep(30)
            self.session_manager.cleanup_stale_sessions()
            self.hitl_queue.cleanup_expired()
    
    # ------------------------------------------------------------------------
    # Client Handling
    # ------------------------------------------------------------------------
    
    async def _handle_client(self, client_sock: socket.socket):
        """Handle a client connection."""
        session_id = None
        
        try:
            while not self.shutdown:
                # Receive message
                message = await self._receive_message(client_sock)
                
                # Route message
                response = await self._route_message(message, session_id)
                
                # Update session_id if this was a registration
                if message["message_type"] == "MESSAGE_TYPE_REGISTER" and response:
                    if "register_response" in response:
                        session_id = response["register_response"]["session_id"]
                
                # Send response
                if response:
                    await self._send_message(client_sock, response)
                    
        except ConnectionError:
            self.logger.info("Client disconnected")
        except Exception as e:
            self.logger.error(f"Client handler error: {e}")
        finally:
            client_sock.close()
            if session_id:
                self.session_manager.remove_session(session_id)
    
    async def _route_message(
        self, message: Dict[str, Any], session_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Route incoming message to appropriate handler."""
        
        msg_type = message["message_type"]
        
        if msg_type == "MESSAGE_TYPE_REGISTER":
            return await self._handle_register(message)
        
        elif msg_type == "MESSAGE_TYPE_HEARTBEAT":
            return await self._handle_heartbeat(message)
        
        elif msg_type == "MESSAGE_TYPE_PRE_EXEC":
            return await self._handle_pre_exec(message)
        
        elif msg_type == "MESSAGE_TYPE_POST_EXEC":
            return await self._handle_post_exec(message)
        
        elif msg_type == "MESSAGE_TYPE_DISCONNECT":
            return await self._handle_disconnect(message)
        
        else:
            self.logger.warning(f"Unknown message type: {msg_type}")
            return None
    
    # ------------------------------------------------------------------------
    # Message Handlers
    # ------------------------------------------------------------------------
    
    async def _handle_register(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle registration request."""
        req = message["register_request"]
        
        # Create session
        session = self.session_manager.create_session(
            client_id=req["client_id"],
            client_version=req["client_version"],
            protocol_version=req["protocol_version"],
            capabilities=req["capabilities"],
            metadata=req["metadata"]
        )
        
        self.stats["sessions"] += 1
        
        # Build response
        return {
            "message_type": "MESSAGE_TYPE_REGISTER_RESPONSE",
            "message_id": str(uuid.uuid4()),
            "version": self.PROTOCOL_VERSION,
            "timestamp": int(time.time() * 1000),
            "register_response": {
                "session_id": session.session_id,
                "accepted_version": self.PROTOCOL_VERSION,
                "guardian_capabilities": self.CAPABILITIES,
                "config": {
                    "pre_exec_timeout_ms": "5000",
                    "heartbeat_interval_ms": "30000"
                },
                "session_expires_at": int(session.expires_at * 1000)
            }
        }
    
    async def _handle_heartbeat(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle heartbeat request."""
        req = message["heartbeat_request"]
        session_id = req["session_id"]
        
        # Update heartbeat
        valid = self.session_manager.update_heartbeat(session_id)
        
        return {
            "message_type": "MESSAGE_TYPE_HEARTBEAT_RESPONSE",
            "message_id": str(uuid.uuid4()),
            "version": self.PROTOCOL_VERSION,
            "timestamp": int(time.time() * 1000),
            "heartbeat_response": {
                "acknowledged": valid,
                "should_reconnect": not valid,
                "next_heartbeat_ms": 30000
            }
        }
    
    async def _handle_pre_exec(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle pre-execution authorization request."""
        req = message["pre_exec_request"]
        
        self.stats["total_requests"] += 1
        
        # Extract request data
        execution_id = req["execution_id"]
        command = req["command"]
        working_dir = req["working_directory"]
        user = req["user"]["username"]
        
        # Evaluate policy
        rule = self.policy_engine.evaluate(command, working_dir, user)
        
        # Update stats
        self.stats["verdicts"][rule.verdict.name] = \
            self.stats["verdicts"].get(rule.verdict.name, 0) + 1
        
        # Build response
        response = {
            "message_type": "MESSAGE_TYPE_PRE_EXEC_RESPONSE",
            "message_id": str(uuid.uuid4()),
            "version": self.PROTOCOL_VERSION,
            "timestamp": int(time.time() * 1000),
            "pre_exec_response": {
                "verdict": rule.verdict.value,
                "execution_id": execution_id,
                "reason_code": rule.reason_code.value,
                "reason_message": rule.reason_message,
                "timeout_ms": 0,
                "metadata": {
                    "policy_rule": rule.name
                }
            }
        }
        
        # Handle HITL
        if rule.verdict == Verdict.HITL:
            hitl_request = self.hitl_queue.create_request(
                execution_id=execution_id,
                command=command,
                risk_level=rule.risk_level or RiskLevel.MEDIUM,
                risk_factors=[rule.reason_message],
                context=req
            )
            response["pre_exec_response"]["hitl_request_id"] = hitl_request.hitl_request_id
            
            # In production, notify operators here
            self.logger.info(f"HITL escalation: {hitl_request.hitl_request_id}")
        
        return response
    
    async def _handle_post_exec(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle post-execution report."""
        req = message["post_exec_request"]
        execution_id = req["execution_id"]
        exit_code = req["exit_code"]
        
        self.logger.info(f"Execution {execution_id} completed: exit_code={exit_code}")
        
        # In production, store in audit log
        
        return {
            "message_type": "MESSAGE_TYPE_POST_EXEC_RESPONSE",
            "message_id": str(uuid.uuid4()),
            "version": self.PROTOCOL_VERSION,
            "timestamp": int(time.time() * 1000),
            "post_exec_response": {
                "acknowledged": True,
                "archived": True
            }
        }
    
    async def _handle_disconnect(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle disconnect request."""
        req = message["disconnect_request"]
        session_id = req["session_id"]
        
        self.logger.info(f"Client disconnecting: {req.get('reason', 'unknown')}")
        self.session_manager.remove_session(session_id)
        
        return None  # No response needed
    
    # ------------------------------------------------------------------------
    # Wire Protocol (Unix Socket)
    # ------------------------------------------------------------------------
    
    async def _send_message(self, sock: socket.socket, message: Dict[str, Any]):
        """Send length-prefixed message."""
        payload = json.dumps(message).encode("utf-8")
        length = struct.pack(">I", len(payload))
        sock.sendall(length + payload)
    
    async def _receive_message(self, sock: socket.socket) -> Dict[str, Any]:
        """Receive length-prefixed message."""
        # Read length header
        length_data = self._recv_exact(sock, 4)
        length = struct.unpack(">I", length_data)[0]
        
        # Read payload
        payload = self._recv_exact(sock, length)
        
        return json.loads(payload.decode("utf-8"))
    
    def _recv_exact(self, sock: socket.socket, n: int) -> bytes:
        """Receive exactly n bytes."""
        data = b""
        while len(data) < n:
            chunk = sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("Socket closed")
            data += chunk
        return data
    
    # ------------------------------------------------------------------------
    # Stats & Monitoring
    # ------------------------------------------------------------------------
    
    def print_stats(self):
        """Print current statistics."""
        print("\n" + "="*60)
        print("SHACKLE Guardian Statistics")
        print("="*60)
        print(f"Total Requests:    {self.stats['total_requests']}")
        print(f"Active Sessions:   {len(self.session_manager.sessions)}")
        print(f"Pending HITL:      {len(self.hitl_queue.pending)}")
        print(f"\nVerdicts:")
        for verdict, count in self.stats['verdicts'].items():
            print(f"  {verdict:12} {count}")
        print("="*60 + "\n")


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    parser = argparse.ArgumentParser(description="SHACKLE V2.0 Guardian Server")
    parser.add_argument("--socket", type=str, default="/tmp/shackle-test.sock",
                        help="Unix socket path")
    parser.add_argument("--websocket", action="store_true",
                        help="Use WebSocket instead of Unix socket")
    parser.add_argument("--port", type=int, default=8765,
                        help="WebSocket port")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    # Create Guardian
    if args.websocket:
        guardian = ShackleGuardian(websocket_port=args.port)
    else:
        guardian = ShackleGuardian(socket_path=args.socket)
    
    # Start server
    try:
        print(f"Starting SHACKLE Guardian v{guardian.PROTOCOL_VERSION}")
        print(f"Transport: {'WebSocket port ' + str(args.port) if args.websocket else 'Unix socket ' + args.socket}")
        print("Press Ctrl+C to stop\n")
        
        # Periodic stats display
        async def stats_loop():
            while True:
                await asyncio.sleep(10)
                guardian.print_stats()
        
        asyncio.create_task(stats_loop())
        
        await guardian.start()
        
    except KeyboardInterrupt:
        print("\nShutting down...")
        await guardian.stop()


if __name__ == "__main__":
    asyncio.run(main())
