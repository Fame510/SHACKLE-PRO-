#!/bin/bash
set -e

echo "=========================================="
echo "SHACKLE V2 Daemon - Quickstart"
echo "=========================================="
echo

# Check if Python 3.11+ is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.11+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Python version: $PYTHON_VERSION"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install docker-compose"
    exit 1
fi

echo "✓ Docker available"
echo

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -q -r requirements.txt
echo "✓ Dependencies installed"
echo

# Start Redis and Postgres
echo "Starting Redis and Postgres..."
docker-compose up -d redis postgres

# Wait for services to be healthy
echo "Waiting for services to be ready..."
sleep 5

# Check Redis
if docker exec shackle-redis redis-cli ping > /dev/null 2>&1; then
    echo "✓ Redis ready"
else
    echo "❌ Redis not responding"
    exit 1
fi

# Check Postgres
if docker exec shackle-postgres pg_isready -U shackle > /dev/null 2>&1; then
    echo "✓ Postgres ready"
else
    echo "❌ Postgres not responding"
    exit 1
fi

echo
echo "=========================================="
echo "Infrastructure Ready!"
echo "=========================================="
echo
echo "Redis:     localhost:6379"
echo "Postgres:  localhost:5432"
echo "           User: shackle / Pass: shackle / DB: shackle"
echo
echo "Next steps:"
echo "1. Start daemon:  python daemon.py"
echo "2. Run tests:     python test_daemon.py"
echo "3. Run examples:  python example_usage.py"
echo "4. CLI help:      python cli.py --help"
echo
echo "Or use Make:"
echo "  make dev    - Start infrastructure only"
echo "  make up     - Start full stack (daemon + infra)"
echo "  make logs   - Show logs"
echo "  make down   - Stop everything"
echo
