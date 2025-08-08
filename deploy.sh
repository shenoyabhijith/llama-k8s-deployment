#!/bin/bash
set -e

echo "Building and pushing Docker image..."
chmod +x scripts/build-and-push.sh
./scripts/build-and-push.sh

echo "Deploying to Kubernetes..."
chmod +x scripts/deploy.sh
./scripts/deploy.sh

echo "Deployment complete!"
