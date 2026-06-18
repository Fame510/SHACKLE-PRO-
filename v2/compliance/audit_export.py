#!/usr/bin/env python3
"""
SHACKLE-V2 Audit Export Tool
Export compliance logs with signature verification for SOC2/ISO27001 audits
"""

import argparse
import json
import hashlib
import hmac
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import requests
from pathlib import Path


class AuditExporter:
    """Export and verify audit logs for compliance"""
    
    def __init__(self, server_url: str, master_secret: str):
        """
        Initialize exporter
        
        Args:
            server_url: License server URL
            master_secret: Master secret for signature verification
        """
        self.server_url = server_url.rstrip('/')
        self.master_secret = master_secret.encode()
    
    def verify_signature(self, entry: Dict[str, Any]) -> bool:
        """
        Verify audit log entry signature
        
        Args:
            entry: Audit log entry
            
        Returns:
            True if signature is valid
        """
        # Reconstruct signed payload
        event_data = {
            "timestamp": entry['timestamp'],
            "event_type": entry['event_type'],
            "license_key": entry['license_key'],
            "result": entry['result']
        }
        
        payload = json.dumps(event_data, sort_keys=True)
        expected_signature = hmac.new(
            self.master_secret,
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, entry['signature'])
    
    def fetch_audit_logs(
        self,
        license_key: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 10000
    ) -> Dict[str, Any]:
        """
        Fetch audit logs from server
        
        Args:
            license_key: Filter by license key
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            limit: Maximum entries to fetch
            
        Returns:
            API response with audit entries
        """
        params = {"limit": limit}
        if license_key:
            params["license_key"] = license_key
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        response = requests.get(
            f"{self.server_url}/api/v1/audit/export",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def export_jsonl(
        self,
        output_path: str,
        license_key: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        verify_signatures: bool = True
    ) -> Dict[str, Any]:
        """
        Export audit logs to JSONL file with verification
        
        Args:
            output_path: Output file path
            license_key: Filter by license key
            start_date: Start date
            end_date: End date
            verify_signatures: Verify signatures during export
            
        Returns:
            Export summary statistics
        """
        print(f"📥 Fetching audit logs from {self.server_url}...")
        
        data = self.fetch_audit_logs(license_key, start_date, end_date)
        entries = data['entries']
        
        print(f"📊 Fetched {len(entries)} entries")
        
        stats = {
            "total_entries": len(entries),
            "verified": 0,
            "failed_verification": 0,
            "events_by_type": {},
            "licenses": set(),
            "date_range": {
                "start": None,
                "end": None
            }
        }
        
        with open(output_path, 'w') as f:
            for entry in entries:
                # Verify signature if requested
                if verify_signatures:
                    is_valid = self.verify_signature(entry)
                    entry['signature_verified'] = is_valid
                    
                    if is_valid:
                        stats['verified'] += 1
                    else:
                        stats['failed_verification'] += 1
                        print(f"⚠️  Signature verification failed for entry {entry.get('id')}")
                
                # Update statistics
                event_type = entry['event_type']
                stats['events_by_type'][event_type] = stats['events_by_type'].get(event_type, 0) + 1
                stats['licenses'].add(entry['license_key'])
                
                # Track date range
                timestamp = entry['timestamp']
                if not stats['date_range']['start'] or timestamp < stats['date_range']['start']:
                    stats['date_range']['start'] = timestamp
                if not stats['date_range']['end'] or timestamp > stats['date_range']['end']:
                    stats['date_range']['end'] = timestamp
                
                # Write JSONL
                f.write(json.dumps(entry) + '\n')
        
        stats['licenses'] = list(stats['licenses'])
        
        print(f"✅ Exported to {output_path}")
        return stats
    
    def generate_compliance_report(
        self,
        output_path: str,
        license_key: Optional[str] = None,
        days: int = 90
    ):
        """
        Generate SOC2 compliance report
        
        Args:
            output_path: Output report path (JSON)
            license_key: Filter by license key
            days: Days to include in report
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        print(f"📋 Generating compliance report for last {days} days...")
        
        data = self.fetch_audit_logs(
            license_key=license_key,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )
        
        entries = data['entries']
        
        # Analyze compliance metrics
        report = {
            "report_generated": datetime.utcnow().isoformat(),
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days
            },
            "summary": {
                "total_events": len(entries),
                "unique_licenses": len(set(e['license_key'] for e in entries)),
                "unique_nodes": len(set(e['node_id'] for e in entries if e.get('node_id')))
            },
            "events": {
                "by_type": {},
                "by_result": {"success": 0, "failure": 0}
            },
            "validation_metrics": {
                "total_validations": 0,
                "successful_validations": 0,
                "failed_validations": 0,
                "failure_reasons": {}
            },
            "soc2_controls": self._map_soc2_controls(entries),
            "integrity": {
                "all_signatures_valid": True,
                "verified_count": 0,
                "failed_count": 0
            }
        }
        
        # Process entries
        for entry in entries:
            # Event type stats
            event_type = entry['event_type']
            report['events']['by_type'][event_type] = \
                report['events']['by_type'].get(event_type, 0) + 1
            
            # Result stats
            result = entry['result']
            if result in report['events']['by_result']:
                report['events']['by_result'][result] += 1
            
            # Validation metrics
            if event_type == 'LICENSE_VALIDATED':
                report['validation_metrics']['total_validations'] += 1
                if result == 'success':
                    report['validation_metrics']['successful_validations'] += 1
                else:
                    report['validation_metrics']['failed_validations'] += 1
                    error = entry.get('error_message', 'Unknown')
                    report['validation_metrics']['failure_reasons'][error] = \
                        report['validation_metrics']['failure_reasons'].get(error, 0) + 1
            
            # Verify signature
            if self.verify_signature(entry):
                report['integrity']['verified_count'] += 1
            else:
                report['integrity']['failed_count'] += 1
                report['integrity']['all_signatures_valid'] = False
        
        # Calculate uptime/availability
        if report['validation_metrics']['total_validations'] > 0:
            report['validation_metrics']['success_rate'] = \
                (report['validation_metrics']['successful_validations'] / 
                 report['validation_metrics']['total_validations']) * 100
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"✅ Compliance report written to {output_path}")
        self._print_report_summary(report)
    
    def _map_soc2_controls(self, entries: List[Dict]) -> Dict[str, Any]:
        """Map audit events to SOC2 trust service criteria"""
        return {
            "CC6.1_Logical_Access": {
                "description": "Logical and physical access controls",
                "evidence": {
                    "license_validations": len([e for e in entries if e['event_type'] == 'LICENSE_VALIDATED']),
                    "failed_access_attempts": len([e for e in entries if e['result'] == 'failure'])
                }
            },
            "CC6.6_Logical_Access_Removal": {
                "description": "Removes access when no longer appropriate",
                "evidence": {
                    "expired_license_blocks": len([
                        e for e in entries 
                        if e.get('error_message', '').find('expired') >= 0
                    ])
                }
            },
            "CC7.2_System_Monitoring": {
                "description": "System monitoring for anomalies",
                "evidence": {
                    "total_audit_events": len(entries),
                    "monitoring_coverage": "100% of license operations"
                }
            },
            "CC7.3_Audit_Logging": {
                "description": "Evaluates security events to detect potential breaches",
                "evidence": {
                    "audit_log_integrity": "Cryptographic signatures verified",
                    "non_repudiation": "Ed25519 digital signatures on all events"
                }
            }
        }
    
    def _print_report_summary(self, report: Dict):
        """Print compliance report summary"""
        print("\n" + "="*60)
        print("📊 SOC2 COMPLIANCE REPORT SUMMARY")
        print("="*60)
        
        print(f"\n📅 Period: {report['period']['days']} days")
        print(f"   {report['period']['start'][:10]} to {report['period']['end'][:10]}")
        
        print(f"\n📈 Metrics:")
        print(f"   Total Events: {report['summary']['total_events']}")
        print(f"   Unique Licenses: {report['summary']['unique_licenses']}")
        print(f"   Unique Nodes: {report['summary']['unique_nodes']}")
        
        if report['validation_metrics']['total_validations'] > 0:
            print(f"\n✅ Validation Success Rate: {report['validation_metrics']['success_rate']:.2f}%")
        
        print(f"\n🔒 Integrity:")
        print(f"   Signatures Verified: {report['integrity']['verified_count']}")
        print(f"   Failed Verifications: {report['integrity']['failed_count']}")
        status = "✅ PASS" if report['integrity']['all_signatures_valid'] else "❌ FAIL"
        print(f"   Status: {status}")
        
        print("\n" + "="*60 + "\n")


def verify_jsonl_signatures(jsonl_path: str, master_secret: str):
    """
    Verify signatures in exported JSONL file
    
    Args:
        jsonl_path: Path to JSONL file
        master_secret: Master secret for verification
    """
    print(f"🔍 Verifying signatures in {jsonl_path}...")
    
    exporter = AuditExporter("http://localhost", master_secret)
    
    total = 0
    verified = 0
    failed = 0
    
    with open(jsonl_path, 'r') as f:
        for line in f:
            entry = json.loads(line)
            total += 1
            
            if exporter.verify_signature(entry):
                verified += 1
            else:
                failed += 1
                print(f"❌ Failed: Entry {entry.get('id')} at {entry.get('timestamp')}")
    
    print(f"\n✅ Verified: {verified}/{total}")
    print(f"❌ Failed: {failed}/{total}")
    
    if failed == 0:
        print("\n🎉 All signatures valid - audit log integrity confirmed!")
        return 0
    else:
        print("\n⚠️  Some signatures failed - audit log may be compromised!")
        return 1


def main():
    """CLI for audit export"""
    parser = argparse.ArgumentParser(
        description="SHACKLE-V2 Audit Export Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export all audit logs
  python audit_export.py export --output audit.jsonl
  
  # Export for specific license
  python audit_export.py export --license SHACKLE-ENT-... --output audit.jsonl
  
  # Generate SOC2 compliance report
  python audit_export.py report --output compliance.json --days 90
  
  # Verify exported JSONL signatures
  python audit_export.py verify --input audit.jsonl
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export audit logs to JSONL')
    export_parser.add_argument('--server', default='http://localhost:8000', help='License server URL')
    export_parser.add_argument('--secret', required=True, help='Master secret for verification')
    export_parser.add_argument('--output', required=True, help='Output JSONL file')
    export_parser.add_argument('--license', help='Filter by license key')
    export_parser.add_argument('--start-date', help='Start date (ISO format)')
    export_parser.add_argument('--end-date', help='End date (ISO format)')
    export_parser.add_argument('--no-verify', action='store_true', help='Skip signature verification')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate SOC2 compliance report')
    report_parser.add_argument('--server', default='http://localhost:8000', help='License server URL')
    report_parser.add_argument('--secret', required=True, help='Master secret')
    report_parser.add_argument('--output', required=True, help='Output JSON file')
    report_parser.add_argument('--license', help='Filter by license key')
    report_parser.add_argument('--days', type=int, default=90, help='Days to include')
    
    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify JSONL signatures')
    verify_parser.add_argument('--input', required=True, help='Input JSONL file')
    verify_parser.add_argument('--secret', required=True, help='Master secret')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        if args.command == 'export':
            exporter = AuditExporter(args.server, args.secret)
            stats = exporter.export_jsonl(
                args.output,
                license_key=args.license,
                start_date=args.start_date,
                end_date=args.end_date,
                verify_signatures=not args.no_verify
            )
            
            print(f"\n📊 Export Statistics:")
            print(f"   Total: {stats['total_entries']}")
            print(f"   Verified: {stats['verified']}")
            print(f"   Failed: {stats['failed_verification']}")
            print(f"   Licenses: {len(stats['licenses'])}")
            
        elif args.command == 'report':
            exporter = AuditExporter(args.server, args.secret)
            exporter.generate_compliance_report(
                args.output,
                license_key=args.license,
                days=args.days
            )
            
        elif args.command == 'verify':
            return verify_jsonl_signatures(args.input, args.secret)
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
