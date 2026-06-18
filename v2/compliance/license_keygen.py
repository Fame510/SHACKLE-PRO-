#!/usr/bin/env python3
"""
SHACKLE-V2 License Key Generator
Generates cryptographically secure enterprise licenses with validation checksums
"""

import hashlib
import hmac
import secrets
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import base64

class LicenseGenerator:
    """Generate SHACKLE-ENT licenses with crypto validation"""
    
    def __init__(self, master_secret: Optional[str] = None):
        """
        Initialize generator with master secret for HMAC validation
        
        Args:
            master_secret: Master secret for license validation (keep secure!)
        """
        if master_secret:
            self.master_secret = master_secret.encode()
        else:
            # Generate new master secret if none provided
            self.master_secret = secrets.token_hex(32).encode()
            print(f"⚠️  Generated new master secret: {self.master_secret.decode()}")
            print("⚠️  SAVE THIS SECRET - Required for license validation!")
        
        # Generate Ed25519 signing key pair
        self.private_key = ed25519.Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
    
    def generate_license(
        self,
        customer_name: str,
        tier: str = "ENTERPRISE",
        duration_days: int = 365,
        max_nodes: Optional[int] = None,
        features: Optional[list] = None,
        node_binding: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a new SHACKLE enterprise license
        
        Args:
            customer_name: Customer/organization name
            tier: License tier (ENTERPRISE, SOVEREIGN, UNLIMITED)
            duration_days: License validity period
            max_nodes: Maximum allowed nodes (None = unlimited)
            features: List of enabled features
            node_binding: Optional node hardware ID for binding
            
        Returns:
            Complete license object with key, metadata, and signature
        """
        license_id = str(uuid.uuid4())
        issued_at = datetime.utcnow()
        expires_at = issued_at + timedelta(days=duration_days)
        
        # Build license metadata
        metadata = {
            "customer": customer_name,
            "tier": tier,
            "max_nodes": max_nodes,
            "features": features or ["proxy", "audit", "compliance_export"],
            "issued_at": issued_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "node_binding": node_binding
        }
        
        # Generate checksum: HMAC-SHA256 of license_id + metadata
        checksum_input = f"{license_id}:{json.dumps(metadata, sort_keys=True)}"
        checksum = hmac.new(
            self.master_secret,
            checksum_input.encode(),
            hashlib.sha256
        ).hexdigest()[:16]  # Use first 16 chars for readability
        
        # Construct license key: SHACKLE-ENT-{UUID}-{CHECKSUM}
        license_key = f"SHACKLE-ENT-{license_id}-{checksum}"
        
        # Sign the complete license with Ed25519
        signature_payload = f"{license_key}:{json.dumps(metadata, sort_keys=True)}"
        signature = self.private_key.sign(signature_payload.encode())
        signature_b64 = base64.b64encode(signature).decode()
        
        return {
            "license_key": license_key,
            "license_id": license_id,
            "checksum": checksum,
            "metadata": metadata,
            "signature": signature_b64,
            "public_key": base64.b64encode(
                self.public_key.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw
                )
            ).decode()
        }
    
    def export_public_key(self) -> str:
        """Export public key for license verification"""
        public_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return public_bytes.decode()
    
    def export_master_secret(self) -> str:
        """Export master secret (KEEP SECURE!)"""
        return self.master_secret.decode()


def generate_node_certificate(
    license_key: str,
    node_id: str,
    hardware_id: str,
    private_key: ed25519.Ed25519PrivateKey
) -> Dict[str, str]:
    """
    Generate node-bound certificate for hardware binding
    
    Args:
        license_key: Valid SHACKLE license key
        node_id: Unique node identifier
        hardware_id: Hardware fingerprint (MAC, CPU ID, etc.)
        private_key: Ed25519 private key for signing
        
    Returns:
        Node certificate with signature
    """
    cert_data = {
        "license_key": license_key,
        "node_id": node_id,
        "hardware_id": hardware_id,
        "issued_at": datetime.utcnow().isoformat(),
        "cert_version": "1.0"
    }
    
    # Sign certificate
    cert_json = json.dumps(cert_data, sort_keys=True)
    signature = private_key.sign(cert_json.encode())
    
    return {
        "certificate": cert_data,
        "signature": base64.b64encode(signature).decode()
    }


def main():
    """CLI for license generation"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="SHACKLE-V2 License Key Generator"
    )
    parser.add_argument("customer", help="Customer/organization name")
    parser.add_argument(
        "--tier",
        choices=["ENTERPRISE", "SOVEREIGN", "UNLIMITED"],
        default="ENTERPRISE",
        help="License tier"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="License duration in days"
    )
    parser.add_argument(
        "--max-nodes",
        type=int,
        help="Maximum nodes (omit for unlimited)"
    )
    parser.add_argument(
        "--features",
        nargs="+",
        help="Enabled features"
    )
    parser.add_argument(
        "--node-binding",
        help="Hardware ID for node binding"
    )
    parser.add_argument(
        "--master-secret",
        help="Master secret (will generate if not provided)"
    )
    parser.add_argument(
        "--output",
        help="Output JSON file path"
    )
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = LicenseGenerator(master_secret=args.master_secret)
    
    # Generate license
    license_data = generator.generate_license(
        customer_name=args.customer,
        tier=args.tier,
        duration_days=args.days,
        max_nodes=args.max_nodes,
        features=args.features,
        node_binding=args.node_binding
    )
    
    # Output
    output = {
        "license": license_data,
        "master_secret": generator.export_master_secret(),
        "public_key_pem": generator.export_public_key()
    }
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"✅ License written to {args.output}")
    else:
        print(json.dumps(output, indent=2))
    
    # Pretty print key
    print(f"\n🔑 LICENSE KEY:\n{license_data['license_key']}\n")


if __name__ == "__main__":
    main()
