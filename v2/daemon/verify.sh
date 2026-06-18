#!/bin/bash
set -e

echo "=========================================="
echo "SHACKLE V2 Daemon - Verification Script"
echo "=========================================="
echo

FAILED=0

# Function to check status
check() {
    local name="$1"
    local cmd="$2"
    
    echo -n "Checking $name... "
    if eval "$cmd" > /dev/null 2>&1; then
        echo "✓ OK"
        return 0
    else
        echo "✗ FAILED"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Check Python
check "Python 3" "python3 --version"

# Check Docker
check "Docker" "docker --version"
check "Docker Compose" "docker-compose --version"

# Check Python dependencies
echo
echo "Checking Python dependencies..."
check "FastAPI" "python3 -c 'import fastapi'"
check "Uvicorn" "python3 -c 'import uvicorn'"
check "Redis client" "python3 -c 'import redis'"
check "AsyncPG" "python3 -c 'import asyncpg'"
check "Pydantic" "python3 -c 'import pydantic'"
check "HTTPX" "python3 -c 'import httpx'"
check "PyNaCl" "python3 -c 'import nacl'"

# Check infrastructure
echo
echo "Checking infrastructure..."

if docker ps | grep -q shackle-redis; then
    check "Redis container" "docker exec shackle-redis redis-cli ping | grep -q PONG"
else
    echo "⚠️  Redis container not running - start with: docker-compose up -d redis"
    FAILED=$((FAILED + 1))
fi

if docker ps | grep -q shackle-postgres; then
    check "Postgres container" "docker exec shackle-postgres pg_isready -U shackle"
else
    echo "⚠️  Postgres container not running - start with: docker-compose up -d postgres"
    FAILED=$((FAILED + 1))
fi

# Check daemon
echo
echo "Checking daemon..."

if [ -S /tmp/shackle.sock ]; then
    check "Daemon socket exists" "test -S /tmp/shackle.sock"
    check "Daemon health endpoint" "curl --unix-socket /tmp/shackle.sock -s http://localhost/health | grep -q healthy"
else
    echo "⚠️  Daemon socket not found - start with: python daemon.py"
    FAILED=$((FAILED + 1))
fi

# Check file structure
echo
echo "Checking file structure..."
check "daemon.py exists" "test -f daemon.py"
check "state.py exists" "test -f state.py"
check "audit.py exists" "test -f audit.py"
check "client.py exists" "test -f client.py"
check "docker-compose.yml exists" "test -f docker-compose.yml"
check "requirements.txt exists" "test -f requirements.txt"
check "README.md exists" "test -f README.md"

# Summary
echo
echo "=========================================="
if [ $FAILED -eq 0 ]; then
    echo "✓ All checks passed!"
    echo "=========================================="
    echo
    echo "Ready to use SHACKLE V2!"
    echo
    echo "Quick test:"
    echo "  python test_daemon.py"
    echo
    echo "Run examples:"
    echo "  python example_usage.py"
    echo
    echo "CLI help:"
    echo "  python cli.py --help"
    echo
    exit 0
else
    echo "✗ $FAILED check(s) failed"
    echo "=========================================="
    echo
    echo "To fix:"
    echo "1. Install missing dependencies: pip install -r requirements.txt"
    echo "2. Start infrastructure: docker-compose up -d redis postgres"
    echo "3. Start daemon: python daemon.py"
    echo
    exit 1
fi
