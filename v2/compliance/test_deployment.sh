#!/bin/bash
# SHACKLE-V2 Deployment Test Script

set -e

echo "🧪 SHACKLE-V2 Deployment Test Suite"
echo "===================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0

# Test function
test() {
    local name="$1"
    local command="$2"
    
    echo -n "Testing: $name ... "
    
    if eval "$command" &>/dev/null; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((FAILED++))
    fi
}

# 1. Check Python version
test "Python 3.9+" "python3 --version | grep -E 'Python 3\.(9|1[0-9])'"

# 2. Check dependencies
test "FastAPI installed" "python3 -c 'import fastapi'"
test "Cryptography installed" "python3 -c 'import cryptography'"
test "SQLAlchemy installed" "python3 -c 'import sqlalchemy'"

# 3. Generate test license
echo ""
echo "📝 Generating test license..."
MASTER_SECRET=$(openssl rand -hex 32)
export MASTER_SECRET

python3 license_keygen.py "Test Corporation" \
    --tier ENTERPRISE \
    --days 365 \
    --max-nodes 5 \
    --master-secret "$MASTER_SECRET" \
    --output test_license.json > /dev/null 2>&1

test "License generation" "test -f test_license.json"

# Extract license key
LICENSE_KEY=$(cat test_license.json | python3 -c "import json, sys; print(json.load(sys.stdin)['license']['license_key'])")
echo "License Key: $LICENSE_KEY"

# 4. Start license server in background
echo ""
echo "🚀 Starting license server..."
python3 license_server.py "$MASTER_SECRET" > server.log 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Wait for server to start
sleep 3

# 5. Test server health
test "Server health check" "curl -f http://localhost:8000/health"

# 6. Register license
echo ""
echo "📋 Registering license..."
curl -X POST http://localhost:8000/api/v1/licenses/register \
    -H "Content-Type: application/json" \
    -d @test_license.json > /dev/null 2>&1

test "License registration" "curl -s http://localhost:8000/api/v1/licenses/validate \
    -H 'Content-Type: application/json' \
    -d '{\"license_key\":\"$LICENSE_KEY\"}' | grep -q '\"valid\":true'"

# 7. Test invalid license
test "Invalid license rejection" "! curl -s http://localhost:8000/api/v1/licenses/validate \
    -H 'Content-Type: application/json' \
    -d '{\"license_key\":\"SHACKLE-ENT-invalid-key-00000000\"}' | grep -q '\"valid\":true'"

# 8. Test audit export
echo ""
echo "📊 Testing audit export..."
python3 audit_export.py export \
    --server http://localhost:8000 \
    --secret "$MASTER_SECRET" \
    --output test_audit.jsonl \
    --no-verify > /dev/null 2>&1

test "Audit export" "test -f test_audit.jsonl && test -s test_audit.jsonl"

# 9. Test signature verification
test "Signature verification" "python3 audit_export.py verify \
    --input test_audit.jsonl \
    --secret '$MASTER_SECRET' 2>&1 | grep -q 'All signatures valid'"

# 10. Test compliance report
python3 audit_export.py report \
    --server http://localhost:8000 \
    --secret "$MASTER_SECRET" \
    --output test_compliance.json \
    --days 1 > /dev/null 2>&1

test "Compliance report generation" "test -f test_compliance.json"

# 11. Verify PDF exists
test "PDF documentation exists" "test -f AI-Agent-Liability-Shield.pdf"

# Cleanup
echo ""
echo "🧹 Cleaning up..."
kill $SERVER_PID 2>/dev/null || true
rm -f test_license.json test_audit.jsonl test_compliance.json server.log licenses.db

# Summary
echo ""
echo "===================================="
echo "Test Summary:"
echo -e "  ${GREEN}Passed: $PASSED${NC}"
echo -e "  ${RED}Failed: $FAILED${NC}"
echo "===================================="

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed! Deployment is ready.${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please review the errors above.${NC}"
    exit 1
fi
