#!/bin/bash
set -e

IMAGE="your-registry/llama-inference:latest"
echo "Building Docker image: $IMAGE"
docker build -f docker/Dockerfile -t $IMAGE .

echo "Pushing Docker image..."
docker push $IMAGE

echo "Docker image built and pushed successfully!"
