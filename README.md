# First Responder

A comprehensive suite of AI-powered tools for monitoring, observability, and troubleshooting Kubernetes environments.

## Project Overview

This project aims to build intelligent agents that help with:

- **Monitoring**: Real-time system health and performance tracking
- **Observability**: Deep insights into distributed system behavior
- **Troubleshooting**: Automated issue detection and resolution

To develop and test these tools in a realistic environment, we use a local Kubernetes cluster with a production-like microservices application.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation) (Kubernetes in Docker)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Helm](https://helm.sh/docs/intro/install/)

## Setup

### 1. Create the Kind Cluster

Create a local Kubernetes cluster using the provided configuration:

```bash
kind create cluster --config kind-config.yaml --name otel-testing
```

This creates a cluster with 1 control plane node and 2 worker nodes.

### 2. Deploy the OpenTelemetry Demo Application

We use the [OpenTelemetry Demo Application](https://opentelemetry.io/docs/demo/kubernetes-deployment/) as a realistic microservices environment.

```bash
# Add the OpenTelemetry Helm repository
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update

# Install the demo application
helm install my-otel-demo open-telemetry/opentelemetry-demo
```

### 3. Verify the Deployment

Check that all pods are running:

```bash
kubectl get pods
```

Wait for all pods to reach the `Running` status.

### 4. Access the Application

The demo application includes several frontend and backend services. To access them locally:

```bash
# Port-forward to the frontend service
kubectl port-forward svc/my-otel-demo-frontendproxy 8080:8080
```

Then open [http://localhost:8080](http://localhost:8080) in your browser.

## Cleanup

When you're done, delete the cluster:

```bash
kind delete cluster --name otel-testing
```

## Status

🚧 **Early Development** - The AI-powered monitoring and troubleshooting tools are currently under development.