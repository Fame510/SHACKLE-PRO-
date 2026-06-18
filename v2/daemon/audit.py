#!/usr/bin/env python3
"""
SHACKLE Audit Logger - Postgres append-only logs with Ed25519 signatures
"""

import json
import logging
from datetime import datetime
from typing import Dict, Optional

import asyncpg
from nacl.signing import SigningKey
from nacl.encoding import HexEncoder

logger = logging.getLogger(__name__)


class AuditLogger:
    """Append-only audit logger with cryptographic signatures"""
    
    def __init__(self, postgres_url: str, signing_key: Optional[bytes] = None):
        self.postgres_url = postgres_url
        self.pool: Optional[asyncpg.Pool] = None
        
        # Initialize or load signing key
        if signing_key:
            self.signing_key = SigningKey(signing_key)
        else:
            # Generate new key (in production, load from secure storage)
            self.signing_key = SigningKey.generate()
        
        self.verify_key = self.signing_key.verify_key
        logger.info(f"Audit signing key: {self.verify_key.encode(encoder=HexEncoder).decode()}")
    
    async def connect(self):
        """Connect to Postgres and initialize schema"""
        try:
            self.pool = await asyncpg.create_pool(
                self.postgres_url,
                min_size=2,
                max_size=10
            )
            
            # Initialize schema
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id BIGSERIAL PRIMARY KEY,
                        timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        event_type VARCHAR(50) NOT NULL,
                        session_id VARCHAR(255) NOT NULL,
                        tool_name VARCHAR(255),
                        decision VARCHAR(20),
                        reason TEXT,
                        parameters JSONB,
                        result JSONB,
                        error TEXT,
                        cost DECIMAL(10, 6),
                        execution_time_ms DECIMAL(10, 2),
                        signature TEXT NOT NULL,
                        metadata JSONB
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp DESC);
                    CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_log(session_id);
                    CREATE INDEX IF NOT EXISTS idx_audit_tool ON audit_log(tool_name);
                    CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_log(event_type);
                """)
            
            logger.info("Connected to Postgres and initialized schema")
            
        except Exception as e:
            logger.error(f"Failed to connect to Postgres: {e}")
            raise
    
    async def close(self):
        """Close Postgres connection"""
        if self.pool:
            await self.pool.close()
            logger.info("Closed Postgres connection")
    
    def is_connected(self) -> bool:
        """Check if connected to Postgres"""
        return self.pool is not None
    
    def _sign_record(self, record: Dict) -> str:
        """Sign a record with Ed25519"""
        # Create canonical JSON representation
        record_json = json.dumps(record, sort_keys=True, separators=(',', ':'))
        record_bytes = record_json.encode('utf-8')
        
        # Sign
        signed = self.signing_key.sign(record_bytes)
        
        # Return signature as hex
        return signed.signature.hex()
    
    async def log_decision(
        self,
        session_id: str,
        tool_name: str,
        decision: str,
        reason: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Log a pre-execution decision"""
        try:
            timestamp = datetime.utcnow()
            
            record = {
                "timestamp": timestamp.isoformat(),
                "event_type": "decision",
                "session_id": session_id,
                "tool_name": tool_name,
                "decision": decision,
                "reason": reason,
                "metadata": metadata or {}
            }
            
            signature = self._sign_record(record)
            
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO audit_log (
                        timestamp, event_type, session_id, tool_name,
                        decision, reason, signature, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, timestamp, "decision", session_id, tool_name,
                    decision, reason, signature, json.dumps(metadata or {}))
            
            logger.info(f"Logged decision: {session_id} | {tool_name} | {decision}")
            
        except Exception as e:
            logger.error(f"Error logging decision: {e}", exc_info=True)
    
    async def log_execution(
        self,
        session_id: str,
        tool_name: str,
        parameters: Dict,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
        cost: float = 0.0,
        execution_time_ms: float = 0.0,
        metadata: Optional[Dict] = None
    ):
        """Log a post-execution result"""
        try:
            timestamp = datetime.utcnow()
            
            record = {
                "timestamp": timestamp.isoformat(),
                "event_type": "execution",
                "session_id": session_id,
                "tool_name": tool_name,
                "parameters": parameters,
                "result": result,
                "error": error,
                "cost": cost,
                "execution_time_ms": execution_time_ms,
                "metadata": metadata or {}
            }
            
            signature = self._sign_record(record)
            
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO audit_log (
                        timestamp, event_type, session_id, tool_name,
                        parameters, result, error, cost, execution_time_ms,
                        signature, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """, timestamp, "execution", session_id, tool_name,
                    json.dumps(parameters), json.dumps(result) if result else None,
                    error, cost, execution_time_ms, signature, json.dumps(metadata or {}))
            
            logger.info(f"Logged execution: {session_id} | {tool_name} | cost={cost}")
            
        except Exception as e:
            logger.error(f"Error logging execution: {e}", exc_info=True)
    
    async def verify_log_integrity(self, log_id: int) -> bool:
        """Verify the signature of a log entry"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT timestamp, event_type, session_id, tool_name,
                           decision, reason, parameters, result, error,
                           cost, execution_time_ms, signature, metadata
                    FROM audit_log WHERE id = $1
                """, log_id)
            
            if not row:
                return False
            
            # Reconstruct record
            record = {
                "timestamp": row["timestamp"].isoformat(),
                "event_type": row["event_type"],
                "session_id": row["session_id"],
                "tool_name": row["tool_name"],
            }
            
            if row["decision"]:
                record["decision"] = row["decision"]
            if row["reason"]:
                record["reason"] = row["reason"]
            if row["parameters"]:
                record["parameters"] = json.loads(row["parameters"])
            if row["result"]:
                record["result"] = json.loads(row["result"])
            if row["error"]:
                record["error"] = row["error"]
            if row["cost"]:
                record["cost"] = float(row["cost"])
            if row["execution_time_ms"]:
                record["execution_time_ms"] = float(row["execution_time_ms"])
            if row["metadata"]:
                record["metadata"] = json.loads(row["metadata"])
            
            # Verify signature
            record_json = json.dumps(record, sort_keys=True, separators=(',', ':'))
            record_bytes = record_json.encode('utf-8')
            
            signature_bytes = bytes.fromhex(row["signature"])
            
            try:
                self.verify_key.verify(record_bytes, signature_bytes)
                return True
            except Exception:
                return False
                
        except Exception as e:
            logger.error(f"Error verifying log integrity: {e}", exc_info=True)
            return False
    
    async def get_session_logs(self, session_id: str, limit: int = 100):
        """Get recent logs for a session"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, timestamp, event_type, tool_name, decision,
                           reason, cost, execution_time_ms, error
                    FROM audit_log
                    WHERE session_id = $1
                    ORDER BY timestamp DESC
                    LIMIT $2
                """, session_id, limit)
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting session logs: {e}", exc_info=True)
            return []
    
    async def get_stats(self) -> Dict:
        """Get aggregate statistics"""
        try:
            async with self.pool.acquire() as conn:
                total = await conn.fetchval("SELECT COUNT(*) FROM audit_log")
                
                by_type = await conn.fetch("""
                    SELECT event_type, COUNT(*) as count
                    FROM audit_log
                    GROUP BY event_type
                """)
                
                by_decision = await conn.fetch("""
                    SELECT decision, COUNT(*) as count
                    FROM audit_log
                    WHERE decision IS NOT NULL
                    GROUP BY decision
                """)
                
                total_cost = await conn.fetchval("""
                    SELECT COALESCE(SUM(cost), 0) FROM audit_log
                """)
            
            return {
                "total_logs": total,
                "by_type": {row["event_type"]: row["count"] for row in by_type},
                "by_decision": {row["decision"]: row["count"] for row in by_decision},
                "total_cost": float(total_cost)
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}", exc_info=True)
            return {}
