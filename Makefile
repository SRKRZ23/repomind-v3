.PHONY: up down build logs shell-backend test-health dev-backend dev-frontend demo-offline test

# Start full stack
up:
	docker compose up --build

# Offline demo — NO GPU, NO API keys. Runs the full SC-TIR loop against the mock vLLM.
demo-offline:
	AIR_GAP=1 VLLM_BASE_URL=http://vllm-mock:8080 docker compose --profile mock up --build

# Run the unit test suite (deterministic tools, router, parser, path-traversal)
test:
	cd backend && python -m pytest -q

# Start detached
up-d:
	docker compose up --build -d

# Stop
down:
	docker compose down

# View logs
logs:
	docker compose logs -f

# Rebuild images only
build:
	docker compose build --no-cache

# Health check
test-health:
	curl -s http://localhost:8000/health | python3 -m json.tool

# Quick CUDA→ROCm test (paste code inline)
test-cuda:
	curl -s -X POST http://localhost:8000/cuda-to-rocm \
	  -H "Content-Type: application/json" \
	  -d '{"code": "#include <cuda_runtime.h>\n__global__ void kernel() {}\nvoid run() { float *d; cudaMalloc(&d, 1024); cudaFree(d); cudaDeviceSynchronize(); }"}' \
	  | python3 -m json.tool

# Test with demo CUDA file
test-cuda-demo:
	curl -s -X POST http://localhost:8000/cuda-to-rocm \
	  -H "Content-Type: application/json" \
	  -d "{\"code\": $$(python3 -c 'import json; print(json.dumps(open("demo/cuda_sample.cu").read()))')}" \
	  | python3 -m json.tool

# Dev: backend only (without Docker)
dev-backend:
	cd backend && pip install -r requirements.txt -q && uvicorn main:app --reload --port 8000

# Dev: frontend only (without Docker)
dev-frontend:
	cd frontend && npm install && npm run dev

# Shell into running backend container
shell-backend:
	docker compose exec backend /bin/bash

# Clean cached repos
clean-repos:
	docker compose exec backend rm -rf /tmp/repos/*

# Show env template
env:
	@echo "Copy .env.example to .env and fill in:"
	@cat .env.example
