.PHONY: help install dev up down logs test clean

help:
	@echo "SHACKLE V2 Daemon - Make targets:"
	@echo "  install    - Install Python dependencies"
	@echo "  dev        - Start development environment (Redis + Postgres)"
	@echo "  up         - Start full stack (including daemon)"
	@echo "  down       - Stop all services"
	@echo "  logs       - Show logs"
	@echo "  test       - Run tests"
	@echo "  clean      - Clean up containers and volumes"

install:
	pip install -r requirements.txt

dev:
	docker-compose up -d redis postgres
	@echo "Waiting for services to be healthy..."
	@sleep 5
	@echo "Dev stack ready. Run 'python daemon.py' to start daemon."

up:
	docker-compose up -d
	@echo "Full stack started."
	@echo "Socket: /tmp/shackle.sock"
	@echo "Health: curl --unix-socket /tmp/shackle.sock http://localhost/health"

down:
	docker-compose down

logs:
	docker-compose logs -f

test:
	python client.py

clean:
	docker-compose down -v
	rm -f /tmp/shackle.sock
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
