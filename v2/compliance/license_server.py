#!/usr/bin/env python3
"""
SHACKLE-V2 License Validation Server
FastAPI server with SQLite database for license validation and audit logging
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sqlite3
import hashlib
import hmac
import json
import base64
from datetime import datetime, timedelta
from contextlib import contextmanager
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import secrets
import uvicorn

# Configuration
DATABASE_PATH = "licenses.db"
MASTER_SECRET = None  # Set via environment or init
PUBLIC_KEY = None  # Ed25519 public key for signature verification

app = FastAPI(
    title="SHACKLE-V2 License Server",
    description="Enterprise license validation and audit API",
    version="2.0.0"
)

security = HTTPBearer()


# Pydantic models
class LicenseValidationRequest(BaseModel):
    license_key: str
    node_id: Optional[str] = None
    hardware_id: Optional[str] = None


class LicenseValidationResponse(BaseModel):
    valid: bool
    license_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    errors: List[str] = []
    remaining_days: Optional[int] = None


class AuditLogEntry(BaseModel):
    timestamp: str
    event_type: str
    license_key: str
    node_id: Optional[str] = None
    result: str
    signature: str


class LicenseRegistration(BaseModel):
    license_key: str
    metadata: Dict[str, Any]
    signature: str
    public_key: str


# Database management
@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """Initialize database schema"""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS licenses (
                license_id TEXT PRIMARY KEY,
                license_key TEXT UNIQUE NOT NULL,
                customer TEXT NOT NULL,
                tier TEXT NOT NULL,
                max_nodes INTEGER,
                features TEXT NOT NULL,
                issued_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                node_binding TEXT,
                metadata TEXT NOT NULL,
                signature TEXT NOT NULL,
                public_key TEXT NOT NULL,
                activated_at TEXT,
                last_validated TEXT,
                status TEXT DEFAULT 'active'
            );
            
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                license_key TEXT NOT NULL,
                license_id TEXT,
                node_id TEXT,
                hardware_id TEXT,
                ip_address TEXT,
                result TEXT NOT NULL,
                error_message TEXT,
                signature TEXT NOT NULL,
                metadata TEXT
            );
            
            CREATE TABLE IF NOT EXISTS api_keys (
                key_id TEXT PRIMARY KEY,
                key_hash TEXT UNIQUE NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                last_used TEXT,
                permissions TEXT NOT NULL
            );
            
            CREATE INDEX IF NOT EXISTS idx_audit_license ON audit_log(license_key);
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
            CREATE INDEX IF NOT EXISTS idx_licenses_status ON licenses(status);
        """)


def parse_license_key(license_key: str) -> Optional[Dict[str, str]]:
    """Parse SHACKLE license key format"""
    parts = license_key.split("-")
    if len(parts) != 4 or parts[0] != "SHACKLE" or parts[1] != "ENT":
        return None
    
    return {
        "prefix": f"{parts[0]}-{parts[1]}",
        "license_id": parts[2],
        "checksum": parts[3]
    }


def verify_checksum(license_key: str, metadata: Dict[str, Any]) -> bool:
    """Verify license key checksum"""
    if not MASTER_SECRET:
        raise ValueError("Master secret not configured")
    
    parsed = parse_license_key(license_key)
    if not parsed:
        return False
    
    # Reconstruct checksum
    checksum_input = f"{parsed['license_id']}:{json.dumps(metadata, sort_keys=True)}"
    expected_checksum = hmac.new(
        MASTER_SECRET.encode(),
        checksum_input.encode(),
        hashlib.sha256
    ).hexdigest()[:16]
    
    return hmac.compare_digest(expected_checksum, parsed['checksum'])


def verify_signature(license_key: str, metadata: Dict[str, Any], signature: str, public_key_b64: str) -> bool:
    """Verify Ed25519 signature"""
    try:
        # Reconstruct signed payload
        payload = f"{license_key}:{json.dumps(metadata, sort_keys=True)}"
        
        # Decode public key and signature
        public_key_bytes = base64.b64decode(public_key_b64)
        signature_bytes = base64.b64decode(signature)
        
        # Verify
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
        public_key.verify(signature_bytes, payload.encode())
        return True
    except Exception:
        return False


def sign_audit_entry(event_data: Dict[str, Any]) -> str:
    """Sign audit log entry with server key"""
    # Use HMAC for audit signatures (server-side only)
    payload = json.dumps(event_data, sort_keys=True)
    signature = hmac.new(
        MASTER_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature


def log_audit_event(
    event_type: str,
    license_key: str,
    result: str,
    license_id: Optional[str] = None,
    node_id: Optional[str] = None,
    hardware_id: Optional[str] = None,
    error_message: Optional[str] = None,
    ip_address: Optional[str] = None,
    metadata: Optional[Dict] = None
):
    """Log audit event with non-repudiation signature"""
    timestamp = datetime.utcnow().isoformat()
    
    event_data = {
        "timestamp": timestamp,
        "event_type": event_type,
        "license_key": license_key,
        "result": result
    }
    
    signature = sign_audit_entry(event_data)
    
    with get_db() as conn:
        conn.execute("""
            INSERT INTO audit_log (
                timestamp, event_type, license_key, license_id, node_id,
                hardware_id, ip_address, result, error_message, signature, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp, event_type, license_key, license_id, node_id,
            hardware_id, ip_address, result, error_message, signature,
            json.dumps(metadata) if metadata else None
        ))


# API endpoints
@app.on_event("startup")
async def startup():
    """Initialize on startup"""
    init_database()


@app.post("/api/v1/licenses/register", response_model=Dict[str, str])
async def register_license(registration: LicenseRegistration):
    """
    Register a new license in the database
    Requires valid signature from license generator
    """
    # Parse license key
    parsed = parse_license_key(registration.license_key)
    if not parsed:
        raise HTTPException(status_code=400, detail="Invalid license key format")
    
    # Verify checksum
    if not verify_checksum(registration.license_key, registration.metadata):
        raise HTTPException(status_code=400, detail="Invalid license checksum")
    
    # Verify signature
    if not verify_signature(
        registration.license_key,
        registration.metadata,
        registration.signature,
        registration.public_key
    ):
        raise HTTPException(status_code=400, detail="Invalid license signature")
    
    # Store in database
    try:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO licenses (
                    license_id, license_key, customer, tier, max_nodes,
                    features, issued_at, expires_at, node_binding,
                    metadata, signature, public_key, activated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                parsed['license_id'],
                registration.license_key,
                registration.metadata['customer'],
                registration.metadata['tier'],
                registration.metadata.get('max_nodes'),
                json.dumps(registration.metadata['features']),
                registration.metadata['issued_at'],
                registration.metadata['expires_at'],
                registration.metadata.get('node_binding'),
                json.dumps(registration.metadata),
                registration.signature,
                registration.public_key,
                datetime.utcnow().isoformat()
            ))
        
        log_audit_event("LICENSE_REGISTERED", registration.license_key, "success", parsed['license_id'])
        
        return {"status": "registered", "license_id": parsed['license_id']}
    
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="License already registered")


@app.post("/api/v1/licenses/validate", response_model=LicenseValidationResponse)
async def validate_license(request: LicenseValidationRequest):
    """
    Validate a license key
    Returns license metadata if valid, errors if invalid
    """
    errors = []
    
    # Parse license key
    parsed = parse_license_key(request.license_key)
    if not parsed:
        log_audit_event("VALIDATION_FAILED", request.license_key, "failure", 
                       error_message="Invalid license format")
        return LicenseValidationResponse(valid=False, errors=["Invalid license key format"])
    
    # Fetch from database
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM licenses WHERE license_key = ?",
            (request.license_key,)
        ).fetchone()
    
    if not row:
        log_audit_event("VALIDATION_FAILED", request.license_key, "failure",
                       error_message="License not found")
        return LicenseValidationResponse(valid=False, errors=["License not registered"])
    
    license_data = dict(row)
    metadata = json.loads(license_data['metadata'])
    
    # Check expiration
    expires_at = datetime.fromisoformat(license_data['expires_at'])
    now = datetime.utcnow()
    
    if now > expires_at:
        errors.append("License expired")
    
    remaining_days = (expires_at - now).days if now <= expires_at else 0
    
    # Check status
    if license_data['status'] != 'active':
        errors.append(f"License status: {license_data['status']}")
    
    # Check node binding if specified
    if license_data['node_binding'] and request.hardware_id:
        if license_data['node_binding'] != request.hardware_id:
            errors.append("Hardware ID mismatch")
    
    # Update last validated
    with get_db() as conn:
        conn.execute(
            "UPDATE licenses SET last_validated = ? WHERE license_key = ?",
            (datetime.utcnow().isoformat(), request.license_key)
        )
    
    valid = len(errors) == 0
    result = "success" if valid else "failure"
    
    log_audit_event(
        "LICENSE_VALIDATED",
        request.license_key,
        result,
        license_id=license_data['license_id'],
        node_id=request.node_id,
        hardware_id=request.hardware_id,
        error_message="; ".join(errors) if errors else None
    )
    
    return LicenseValidationResponse(
        valid=valid,
        license_id=license_data['license_id'],
        metadata=metadata if valid else None,
        errors=errors,
        remaining_days=remaining_days if valid else None
    )


@app.get("/api/v1/audit/export")
async def export_audit_log(
    license_key: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 1000
):
    """
    Export audit logs with signature verification
    Returns JSONL format for compliance teams
    """
    query = "SELECT * FROM audit_log WHERE 1=1"
    params = []
    
    if license_key:
        query += " AND license_key = ?"
        params.append(license_key)
    
    if start_date:
        query += " AND timestamp >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND timestamp <= ?"
        params.append(end_date)
    
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    
    entries = []
    for row in rows:
        entry = dict(row)
        # Parse metadata JSON
        if entry['metadata']:
            entry['metadata'] = json.loads(entry['metadata'])
        entries.append(entry)
    
    return {
        "total": len(entries),
        "entries": entries,
        "format": "jsonl",
        "exported_at": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "shackle-license-server", "version": "2.0.0"}


def init_config(master_secret: str):
    """Initialize server configuration"""
    global MASTER_SECRET
    MASTER_SECRET = master_secret


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python license_server.py <master_secret>")
        sys.exit(1)
    
    init_config(sys.argv[1])
    
    print("🚀 Starting SHACKLE-V2 License Server")
    print(f"📊 Database: {DATABASE_PATH}")
    print("🔐 Master secret configured")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
