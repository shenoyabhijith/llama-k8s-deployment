# LLM Inference on Kubernetes (LLAMA 3.2 3B)

A production-style baseline for serving the LLAMA 3.2 3B model on Kubernetes with GPU scheduling, horizontal pod autoscaling (HPA), health probes, and persistent model cache. This repository focuses on a clear, reliable single-service deployment you can run today and extend toward a larger distributed architecture.

If you’ve seen the project website in `docs/index.html`, that page also outlines an aspirational, distributed design (API Gateway + Redis Queue/PubSub + GPU Worker Pool). This repository currently ships the baseline single-service architecture; the “gateway/worker” split and Redis components are listed in the Roadmap below.

## Architecture Diagram 

    [Architecture diagram](mermaid-drawing.svg)
## TL;DR
- FastAPI app serving LLAMA 3.2 3B
- Dockerized with CUDA runtime
- K8s Deployment + Service + HPA + PVC + ConfigMap + Secret
- GPU scheduling (requests/limits), health probes, metrics annotations
- Ready to extend toward multi-service architecture

## Repository Layout
- `app/`
  - `main.py`: FastAPI service with `/health` and `/generate`
  - `model_loader.py`: LLAMA 3.2 loading with 4-bit quantization via bitsandbytes
  - `requirements.txt`: Python dependencies
- `docker/Dockerfile`: CUDA runtime image with FastAPI app
- `k8s/`: Kubernetes manifests (Deployment, Service, HPA, PVC, ConfigMap, Secret)
- `scripts/`: helper scripts to build/push image and deploy manifests
- `docs/index.html`: project website (light/dark theme), including extended design notes

## Quickstart
Prereqs: Docker, kubectl, a Kubernetes cluster with GPU nodes, and credentials to push to a container registry.

1) Build and push the Docker image:
```bash
chmod +x scripts/build-and-push.sh
./scripts/build-and-push.sh
```

2) Deploy to Kubernetes:
```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

This creates namespace `llama-deployment`, applies PVC/ConfigMap/Secret/Deployment/Service/HPA, waits for the deployment to become available, and prints the Service external address.

3) Smoke test the API:
```bash
# Replace $SERVICE_HOST with the printed IP/hostname
curl -X GET  http://$SERVICE_HOST/health
curl -X POST http://$SERVICE_HOST/generate \
  -H 'Content-Type: application/json' \
  -d '{"text":"Hello!", "max_tokens":100, "temperature":0.7}'
```

## Kubernetes Components
- `k8s/deployment.yaml`: GPU-enabled Deployment, readiness/liveness probes, security context, Prometheus annotations, model cache volume
- `k8s/service.yaml`: `LoadBalancer` Service with optional session affinity and metrics annotations
- `k8s/hpa.yaml`: Horizontal Pod Autoscaler with CPU/memory/GPU targets and scale policies
- `k8s/pvc.yaml`: Persistent cache for faster model startup
- `k8s/configmap.yaml`: Model/inference configuration and tuning parameters
- `k8s/secret.yaml`: Sensitive settings (e.g., HF token) — use base64 values in real environments

Example (HPA excerpt):
```yaml
metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: nvidia.com/gpu
      target:
        type: Utilization
        averageUtilization: 85
```

## Application
- Endpoint: `/health` for readiness checks
- Endpoint: `/generate` to perform text generation
- Implements 4-bit quantization to reduce memory footprint, suitable for 3.2B-sized models

Key files:
- `app/model_loader.py`: loads model/tokenizer with bitsandbytes 4-bit quant
- `app/main.py`: FastAPI app, simple request model, generation using a thread pool

## Configuration
Set values in `k8s/configmap.yaml` and `k8s/secret.yaml` (e.g., `MODEL_NAME`, `USE_4BIT`, `HUGGING_FACE_HUB_TOKEN`). The Deployment pulls these via `envFrom`.

## GPU Scheduling
The Deployment requests `nvidia.com/gpu: "1"` and includes a `nodeSelector` for GPU nodes. Adjust for your cloud provider labels/SKUs.

## Observability
Prometheus scrape annotations are included. Export endpoint `/metrics` can be wired up via your FastAPI metrics setup (extend the app with a Prometheus client/middleware if needed).

## Roadmap (Toward the Website’s Distributed Architecture)
Planned extensions to reach the API Gateway + Redis + Worker Pool architecture:
- Add an API Gateway service (FastAPI) for request admission and WebSocket token streaming
- Add Redis (job queue + Pub/Sub) manifests and configuration
- Add a Worker Deployment for GPU-bound inference, consuming jobs and publishing tokens
- Add token-by-token streaming to clients via WebSockets
- Introduce inference caching and queue-aware micro-batching
- Integrate distributed tracing and structured logging end-to-end

Until then, the current single-service baseline remains stable and production-friendly for smaller deployments.

## Troubleshooting
- Pods remain Pending: ensure GPU nodes are available and the node selector matches your cluster
- HPA not scaling: confirm metrics-server and GPU metric support are installed in the cluster
- Model download slow: verify PVC is bound and mounted; consider a warm-cache image layer
- OOM: tune batch size, `MAX_TOKENS`, and quantization options

## License
MIT (adjust as appropriate)
