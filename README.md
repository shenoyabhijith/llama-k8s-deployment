# LLAMA 3.2 3B Kubernetes Deployment

This project provides a complete solution for deploying and scaling the LLAMA 3.2 3B model on Kubernetes.

## Features

- **Model Optimization**: 4-bit quantization for memory efficiency
- **Parallel Processing**: Thread pool for concurrent request handling
- **Auto-scaling**: Horizontal Pod Autoscaler based on CPU/memory utilization
- **GPU Support**: NVIDIA GPU acceleration with CUDA
- **Model Caching**: Persistent volume for model weights
- **Health Monitoring**: Readiness and liveness probes
- **Load Balancing**: Kubernetes Service for traffic distribution

## Prerequisites

- Kubernetes cluster with GPU nodes (NVIDIA Tesla T4 or similar)
- kubectl configured for your cluster
- Docker with push access to a container registry
- Hugging Face token for accessing LLAMA 3.2 3B model

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/shenoyabhijith/llama-k8s-deployment.git
cd llama-k8s-deployment
