#!/bin/bash
set -euo pipefail

NAMESPACE=llama-deployment

echo "Creating namespace..."
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

echo "Applying core configs..."
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

echo "Deploying Redis..."
kubectl apply -f k8s/redis.yaml

echo "Deploying Gateway..."
kubectl apply -f k8s/gateway.yaml

echo "Deploying Worker GPU..."
kubectl apply -f k8s/worker-gpu.yaml

echo "Waiting for gateway..."
kubectl rollout status deployment/llama-gateway -n ${NAMESPACE} --timeout=600s

echo "Waiting for workers..."
kubectl rollout status deployment/llama-worker -n ${NAMESPACE} --timeout=1200s

echo "Service address:"
kubectl get svc llama-api-gateway -n ${NAMESPACE} -o wide | cat

echo "Done."

