#!/bin/bash
set -e

echo "Creating namespace..."
kubectl create namespace llama-deployment --dry-run=client -o yaml | kubectl apply -f -

echo "Applying configurations..."
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml

echo "Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=600s deployment/llama-deployment -n llama-deployment

echo "Getting service IP..."
SERVICE_IP=$(kubectl get svc llama-service -n llama-deployment -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [ -z "$SERVICE_IP" ]; then
  SERVICE_IP=$(kubectl get svc llama-service -n llama-deployment -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
fi

echo "Service available at: http://$SERVICE_IP"
echo "To test the service, run:"
echo "curl -X POST http://$SERVICE_IP/generate -H 'Content-Type: application/json' -d '{\"text\":\"Hello, how are you?\",\"max_tokens\":100}'"
