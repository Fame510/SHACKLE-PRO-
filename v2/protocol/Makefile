# SHACKLE V2.0 Protocol Makefile

.PHONY: all help proto python go clean test run-server run-client

# Default target
all: help

help:
	@echo "SHACKLE V2.0 Protocol Build System"
	@echo ""
	@echo "Targets:"
	@echo "  proto        - Generate protobuf code for all languages"
	@echo "  python       - Generate Python protobuf bindings"
	@echo "  go           - Generate Go protobuf bindings"
	@echo "  cpp          - Generate C++ protobuf bindings"
	@echo "  rust         - Generate Rust protobuf bindings"
	@echo "  test         - Run tests"
	@echo "  run-server   - Start Guardian server (stub)"
	@echo "  run-client   - Run client example (stub)"
	@echo "  clean        - Remove generated files"
	@echo "  install-deps - Install Python dependencies"

# Install Python dependencies
install-deps:
	pip install -r requirements.txt

# Generate all protobuf code
proto: python go

# Python protobuf generation
python:
	@echo "Generating Python protobuf bindings..."
	protoc --python_out=. shackle.proto
	@echo "Generated: shackle_pb2.py"

# Go protobuf generation
go:
	@echo "Generating Go protobuf bindings..."
	mkdir -p go/shackle
	protoc --go_out=go/shackle --go_opt=paths=source_relative shackle.proto
	@echo "Generated: go/shackle/shackle.pb.go"

# C++ protobuf generation
cpp:
	@echo "Generating C++ protobuf bindings..."
	mkdir -p cpp
	protoc --cpp_out=cpp shackle.proto
	@echo "Generated: cpp/shackle.pb.{h,cc}"

# Rust protobuf generation
rust:
	@echo "Generating Rust protobuf bindings..."
	mkdir -p rust/src
	protoc --rust_out=rust/src shackle.proto
	@echo "Generated: rust/src/shackle.rs"

# Run Guardian server (development)
run-server:
	python3 server_stub.py --socket /tmp/shackle-test.sock --debug

# Run client example
run-client:
	python3 client_stub.py

# Run tests (placeholder)
test:
	@echo "Running protocol tests..."
	@echo "TODO: Implement test suite"
	# pytest tests/ -v

# Validate protobuf schema
validate:
	@echo "Validating protobuf schema..."
	protoc --decode_raw < /dev/null shackle.proto 2>&1 || echo "Schema valid"

# Format code
format:
	@echo "Formatting Python code..."
	black client_stub.py server_stub.py
	@echo "Done"

# Lint code
lint:
	@echo "Linting Python code..."
	pylint client_stub.py server_stub.py || true
	mypy client_stub.py server_stub.py || true

# Clean generated files
clean:
	@echo "Cleaning generated files..."
	rm -f shackle_pb2.py
	rm -rf go/shackle/*.pb.go
	rm -rf cpp/shackle.pb.*
	rm -rf rust/src/shackle.rs
	rm -rf __pycache__
	rm -f /tmp/shackle-test.sock
	@echo "Clean complete"

# Docker build (future)
docker-build:
	@echo "Building Docker image..."
	docker build -t shackle-guardian:2.0.0 .

# Docker run (future)
docker-run:
	@echo "Running Guardian in Docker..."
	docker run -it --rm \
		-v /var/run/shackle:/var/run/shackle \
		shackle-guardian:2.0.0

# Documentation generation
docs:
	@echo "Generating documentation..."
	@echo "Protocol docs: PROTOCOL.md"
	@echo "Examples: protocol-examples.md"
	@echo "README: README.md"

# Quick start for new developers
quickstart: install-deps
	@echo ""
	@echo "SHACKLE V2.0 Quick Start"
	@echo "======================="
	@echo ""
	@echo "1. Review the protocol: cat PROTOCOL.md | less"
	@echo "2. See examples: cat protocol-examples.md | less"
	@echo "3. Start Guardian: make run-server"
	@echo "4. In another terminal, run client: make run-client"
	@echo ""

# Version info
version:
	@echo "SHACKLE Protocol Version: 2.0.0"
	@echo "Status: Draft"
	@echo "Generated: 2025-01-23"
