#!/bin/bash
set -euo pipefail

REGISTRY=${REGISTRY:-your-registry}

echo "Building gateway image..."
docker build -f docker/Dockerfile.gateway -t ${REGISTRY}/llama-gateway:latest .

echo "Building worker image (CUDA)..."
docker build -f docker/Dockerfile.worker -t ${REGISTRY}/llama-worker:latest .

echo "Pushing images..."
docker push ${REGISTRY}/llama-gateway:latest
docker push ${REGISTRY}/llama-worker:latest

echo "Done."

