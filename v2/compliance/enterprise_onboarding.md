# SHACKLE-V2 Enterprise Onboarding Guide

## Quick Start: Deploy Your Sovereign Proxy in 30 Minutes

Welcome to SHACKLE-V2 Enterprise. This guide will walk you through deploying a compliant, audit-ready AI proxy infrastructure.

---

## Prerequisites

- Linux server (Ubuntu 22.04+ or RHEL 8+ recommended)
- Python 3.9+
- Docker (optional, for containerized deployment)
- Valid SHACKLE-ENT license key
- Root or sudo access

---

## Step 1: Obtain Your Enterprise License

Contact your SHACKLE account manager or request a license at:
- Email: enterprise@shackle.ai
- Portal: https://portal.shackle.ai/licenses

You will receive:
- `SHACKLE-ENT-{UUID}-{CHECKSUM}` license key
- License metadata JSON file
- Public key for signature verification

**Example license key:**
```
SHACKLE-ENT-a7f3c8e2-4b9d-4c1a-8e5f-2d6c9b3a7f1c-3a8f7e2c1b5d9a4f
```

---

## Step 2: System Preparation

### Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3 python3-pip python3-venv

# Install Docker (optional)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

### Create Installation Directory

```bash
mkdir -p /opt/shackle-v2
cd /opt/shackle-v2
```

---

## Step 3: Download SHACKLE-V2

### Option A: Package Installation

```bash
# Download from enterprise portal
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://portal.shackle.ai/downloads/shackle-v2-enterprise.tar.gz \
  -o shackle-v2.tar.gz

# Extract
tar -xzf shackle-v2.tar.gz
cd shackle-v2
```

### Option B: Git Clone (if provided repository access)

```bash
git clone https://github.com/shackle-ai/shackle-v2-enterprise.git
cd shackle-v2-enterprise
```

---

## Step 4: Configure License

### Create Configuration File

```bash
cp config.example.yaml config.yaml
nano config.yaml
```

### Update Configuration

```yaml
# config.yaml
license:
  key: "SHACKLE-ENT-your-license-key-here"
  validation_server: "https://license.shackle.ai"
  
proxy:
  host: "0.0.0.0"
  port: 8080
  ssl_enabled: true
  ssl_cert: "/opt/shackle-v2/certs/server.crt"
  ssl_key: "/opt/shackle-v2/certs/server.key"

audit:
  enabled: true
  log_level: "INFO"
  retention_days: 90
  export_enabled: true
  signature_validation: true

compliance:
  soc2_mode: true
  export_api: true
  non_repudiation: true
```

---

## Step 5: Deploy License Validation Server

### Local Deployment

```bash
# Set up Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn sqlalchemy cryptography pydantic

# Start license server
export MASTER_SECRET="your-master-secret-from-license-file"
python license_server.py $MASTER_SECRET &
```

### Docker Deployment

```bash
# Build container
docker build -t shackle-license-server -f Dockerfile.license .

# Run container
docker run -d \
  --name shackle-license \
  -p 8000:8000 \
  -e MASTER_SECRET="your-master-secret" \
  -v /opt/shackle-v2/data:/data \
  shackle-license-server
```

### Verify License Server

```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy","service":"shackle-license-server","version":"2.0.0"}
```

---

## Step 6: Register Your License

```bash
# Register license with validation server
curl -X POST http://localhost:8000/api/v1/licenses/register \
  -H "Content-Type: application/json" \
  -d @license_data.json

# Expected response:
# {"status":"registered","license_id":"a7f3c8e2-4b9d-4c1a-8e5f-2d6c9b3a7f1c"}
```

---

## Step 7: Deploy SHACKLE Proxy

### Start Proxy Service

```bash
# Activate virtual environment
source venv/bin/activate

# Start proxy with license validation
./shackle-proxy start \
  --config config.yaml \
  --license-server http://localhost:8000

# Or with systemd
sudo systemctl start shackle-proxy
sudo systemctl enable shackle-proxy
```

### Verify Proxy

```bash
# Health check
curl https://localhost:8080/health

# Test AI request (with valid API key)
curl https://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer YOUR_OPENAI_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

---

## Step 8: Configure Node Binding (Optional)

For hardware-bound licenses, generate and install node certificates:

```bash
# Get hardware ID
HARDWARE_ID=$(cat /sys/class/dmi/id/product_uuid)

# Generate node certificate
python license_keygen.py generate-cert \
  --license-key "SHACKLE-ENT-..." \
  --node-id "proxy-001" \
  --hardware-id "$HARDWARE_ID" \
  --output node_cert.json

# Install certificate
cp node_cert.json /opt/shackle-v2/certs/
```

---

## Step 9: Enable Compliance Monitoring

### Configure Audit Export

```bash
# Set up audit export cron job
crontab -e

# Add daily export at 2 AM
0 2 * * * /opt/shackle-v2/venv/bin/python /opt/shackle-v2/audit_export.py export \
  --server http://localhost:8000 \
  --secret "$MASTER_SECRET" \
  --output /var/log/shackle/audit-$(date +\%Y-\%m-\%d).jsonl
```

### Generate Initial Compliance Report

```bash
python audit_export.py report \
  --server http://localhost:8000 \
  --secret "$MASTER_SECRET" \
  --output compliance_report_$(date +%Y%m%d).json \
  --days 30
```

---

## Step 10: Integration with Existing Systems

### OpenAI SDK Integration

```python
import openai

# Point to SHACKLE proxy
openai.api_base = "https://your-shackle-proxy:8080/v1"
openai.api_key = "your-openai-key"

# Use as normal - all requests audited
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### LangChain Integration

```python
from langchain.llms import OpenAI

llm = OpenAI(
    openai_api_base="https://your-shackle-proxy:8080/v1",
    openai_api_key="your-openai-key"
)

# All LangChain calls now go through SHACKLE
response = llm("Hello, world!")
```

### Reverse Proxy Setup (NGINX)

```nginx
upstream shackle_backend {
    server localhost:8080;
}

server {
    listen 443 ssl http2;
    server_name ai-proxy.yourcompany.com;
    
    ssl_certificate /etc/ssl/certs/yourcompany.crt;
    ssl_certificate_key /etc/ssl/private/yourcompany.key;
    
    location / {
        proxy_pass http://shackle_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # Audit headers
        proxy_set_header X-Audit-User $remote_user;
        proxy_set_header X-Audit-Session $request_id;
    }
}
```

---

## Step 11: Monitoring & Alerting

### Prometheus Metrics

SHACKLE exposes Prometheus metrics at `/metrics`:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'shackle-proxy'
    static_configs:
      - targets: ['localhost:8080']
```

**Key metrics:**
- `shackle_requests_total` - Total API requests
- `shackle_license_validations_total` - License validation count
- `shackle_license_validation_failures` - Failed validations
- `shackle_audit_events_total` - Total audit events logged

### Grafana Dashboard

Import the provided Grafana dashboard:

```bash
curl https://portal.shackle.ai/grafana/shackle-v2-dashboard.json > dashboard.json
# Import via Grafana UI
```

### Alert Configuration

```yaml
# alerts.yaml
groups:
  - name: shackle_alerts
    interval: 1m
    rules:
      - alert: LicenseExpiringSoon
        expr: shackle_license_days_remaining < 30
        labels:
          severity: warning
        annotations:
          summary: "SHACKLE license expiring in {{ $value }} days"
      
      - alert: LicenseValidationFailed
        expr: rate(shackle_license_validation_failures[5m]) > 0
        labels:
          severity: critical
        annotations:
          summary: "License validation failures detected"
```

---

## Step 12: SOC2 Compliance Certification

### Prepare for Audit

1. **Generate compliance reports:**
   ```bash
   python audit_export.py report \
     --output soc2_evidence_Q1_2024.json \
     --days 90
   ```

2. **Export audit logs:**
   ```bash
   python audit_export.py export \
     --output audit_logs_Q1_2024.jsonl \
     --start-date 2024-01-01 \
     --end-date 2024-03-31
   ```

3. **Verify log integrity:**
   ```bash
   python audit_export.py verify \
     --input audit_logs_Q1_2024.jsonl \
     --secret "$MASTER_SECRET"
   ```

### Submit to Auditors

Provide auditors with:
- ✅ Compliance reports (JSON)
- ✅ Audit logs (JSONL with verified signatures)
- ✅ AI-Agent-Liability-Shield.pdf (control mapping)
- ✅ System architecture diagram
- ✅ License validation records

### Control Evidence Mapping

Reference `AI-Agent-Liability-Shield.pdf` for complete SOC2 TSC mapping:

- **CC6.1** (Logical Access): License validation logs
- **CC6.6** (Access Removal): Expired license blocks
- **CC7.2** (Monitoring): Real-time audit logging
- **CC7.3** (Audit Logging): Cryptographic signatures

---

## Step 13: Ongoing Operations

### Daily Operations Checklist

- [ ] Monitor license expiration (check dashboard)
- [ ] Review audit logs for anomalies
- [ ] Verify backup integrity
- [ ] Check system resource utilization

### Weekly Operations Checklist

- [ ] Generate weekly compliance report
- [ ] Review failed validation attempts
- [ ] Update security patches
- [ ] Rotate audit log archives

### Monthly Operations Checklist

- [ ] Full compliance report for management
- [ ] License renewal check (if <60 days)
- [ ] Disaster recovery test
- [ ] Security posture review

---

## Troubleshooting

### License Validation Fails

```bash
# Check license server status
curl http://localhost:8000/health

# Validate license manually
curl -X POST http://localhost:8000/api/v1/licenses/validate \
  -H "Content-Type: application/json" \
  -d '{"license_key":"SHACKLE-ENT-..."}'

# Check logs
tail -f /var/log/shackle/license.log
```

### Audit Logs Not Generated

```bash
# Check audit service status
systemctl status shackle-audit

# Verify disk space
df -h /var/log/shackle

# Test manual export
python audit_export.py export --output test.jsonl
```

### Signature Verification Failures

```bash
# Verify master secret is correct
echo $MASTER_SECRET

# Check system time synchronization (NTP)
timedatectl status

# Revalidate signatures
python audit_export.py verify --input audit.jsonl
```

---

## Support & Resources

### Documentation
- Full API docs: https://docs.shackle.ai/v2
- Architecture guide: https://docs.shackle.ai/v2/architecture
- Security whitepaper: https://shackle.ai/security

### Support Channels
- Enterprise support: support@shackle.ai
- Emergency hotline: +1-888-SHACKLE (24/7)
- Slack workspace: shackle-enterprise.slack.com

### Training
- SOC2 compliance webinar: https://shackle.ai/training/soc2
- Advanced deployment course: https://shackle.ai/training/advanced
- Security best practices: https://shackle.ai/training/security

---

## Appendix: Sample Files

### systemd Service File

```ini
# /etc/systemd/system/shackle-proxy.service
[Unit]
Description=SHACKLE-V2 Enterprise Proxy
After=network.target

[Service]
Type=simple
User=shackle
WorkingDirectory=/opt/shackle-v2
Environment="MASTER_SECRET=your-secret-here"
ExecStart=/opt/shackle-v2/venv/bin/python shackle-proxy.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  license-server:
    build:
      context: .
      dockerfile: Dockerfile.license
    ports:
      - "8000:8000"
    environment:
      - MASTER_SECRET=${MASTER_SECRET}
    volumes:
      - ./data:/data
    restart: unless-stopped

  proxy:
    build:
      context: .
      dockerfile: Dockerfile.proxy
    ports:
      - "8080:8080"
    environment:
      - LICENSE_SERVER=http://license-server:8000
      - LICENSE_KEY=${LICENSE_KEY}
    depends_on:
      - license-server
    restart: unless-stopped
    
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped
```

---

## Next Steps

✅ **Deployment complete!** Your SHACKLE-V2 enterprise proxy is now operational.

**What's next:**
1. **Monitor** - Set up Grafana dashboards and alerts
2. **Integrate** - Connect your AI applications to the proxy
3. **Audit** - Schedule regular compliance reports
4. **Optimize** - Fine-tune performance based on your workload
5. **Certify** - Complete SOC2 audit with provided evidence

**Need help?** Contact your dedicated enterprise support team.

---

**SHACKLE-V2 Enterprise**  
*Sovereign AI Infrastructure with Built-in Compliance*

Version: 2.0.0  
Last Updated: 2024  
© SHACKLE AI Systems
