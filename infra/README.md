# Kind Cluster with ArgoCD - GitOps Infrastructure

A disposable, replicatable Kubernetes development environment using Kind, bootstrapped with ArgoCD for GitOps practices.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Terraform                                │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │  Kind Cluster   │───▶│     ArgoCD      │                     │
│  │  (1 CP + 2 W)   │    │   (Bootstrap)   │                     │
│  └─────────────────┘    └────────┬────────┘                     │
└──────────────────────────────────┼──────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    App of Apps (GitOps)                          │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────────────┐  │
│  │  cert-manager │ │   Prometheus  │ │  Gateway API + Envoy  │  │
│  │               │ │    Grafana    │ │       Gateway         │  │
│  └───────────────┘ └───────────────┘ └───────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 📋 Prerequisites

- **Docker** - Running and accessible
- **Terraform** >= 1.0
- **kubectl** - Kubernetes CLI
- **kind** - Kubernetes in Docker

### Installing Prerequisites (macOS)

```bash
# Using Homebrew
brew install terraform kubectl kind
```

## 🚀 Quick Start

```bash
# Navigate to infra directory
cd infra

# Setup everything (cluster + ArgoCD + addons)
make setup

# Or step by step:
make init    # Initialize Terraform
make plan    # Preview changes
make apply   # Apply changes
```

## 📊 Access Services

### ArgoCD

```bash
# Get admin password
make argocd-password

# Port-forward ArgoCD UI
make port-forward-argocd
# Then open: https://localhost:8080
```

**Or via NodePort:** http://localhost:30080

### Grafana

```bash
make port-forward-grafana
# Then open: http://localhost:3000
# Login: admin / admin
```

**Or via NodePort:** http://localhost:30030

### Prometheus

```bash
make port-forward-prometheus
# Then open: http://localhost:9090
```

**Or via NodePort:** http://localhost:30090

## 🗂️ Directory Structure

```
infra/
├── terraform/                    # Terraform configuration
│   ├── main.tf                   # Main orchestration
│   ├── providers.tf              # Provider configuration
│   ├── variables.tf              # Input variables
│   ├── outputs.tf                # Outputs
│   ├── versions.tf               # Version constraints
│   └── argocd-values.yaml        # ArgoCD Helm values
├── argocd/
│   └── cluster-addons/           # GitOps managed addons
│       ├── cert-manager/
│       │   ├── application.yaml  # ArgoCD Application
│       │   └── values.yaml       # Helm values
│       ├── kube-prometheus-stack/
│       │   ├── application.yaml
│       │   └── values.yaml
│       ├── gateway-api/
│       │   └── application.yaml  # Gateway API CRDs
│       └── envoy-gateway/
│           ├── application.yaml
│           └── values.yaml
├── scripts/
│   ├── setup.sh                  # Full setup script
│   └── destroy.sh                # Cleanup script
├── Makefile                      # Convenience commands
└── README.md                     # This file
```

## ⚙️ Configuration

### Terraform Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `cluster_name` | `first-responder` | Kind cluster name |
| `kubernetes_version` | `v1.31.0` | Kubernetes version |
| `worker_nodes` | `2` | Number of worker nodes |
| `argocd_chart_version` | `7.7.5` | ArgoCD Helm chart version |
| `git_repo_url` | `https://github.com/VENKATESHWARAN-R/first-responder.git` | Git repo for ArgoCD |
| `git_target_revision` | `main` | Git branch/tag to sync |
| `git_path` | `infra/argocd/cluster-addons` | Path to addons in repo |
| `enable_cluster_addons` | `true` | Deploy addons via App of Apps |

### Customizing Variables

Create a `terraform.tfvars` file:

```hcl
cluster_name        = "my-cluster"
worker_nodes        = 3
git_target_revision = "develop"
```

Or use command line:

```bash
terraform apply -var="cluster_name=my-cluster"
```

## 📦 Cluster Addons

The following addons are managed via ArgoCD's App of Apps pattern:

| Addon | Namespace | Description |
|-------|-----------|-------------|
| **cert-manager** | `cert-manager` | X.509 certificate management |
| **kube-prometheus-stack** | `monitoring` | Prometheus + Grafana + Alertmanager |
| **Gateway API CRDs** | `default` | Kubernetes Gateway API |
| **Envoy Gateway** | `envoy-gateway-system` | Gateway API implementation |

### Customizing Addons

Edit the `values.yaml` files in `argocd/cluster-addons/<addon>/`:

```bash
# Example: Edit Prometheus values
vim argocd/cluster-addons/kube-prometheus-stack/values.yaml

# Commit and push - ArgoCD will sync automatically
git add -A && git commit -m "Update Prometheus config" && git push
```

## 🔄 Common Operations

```bash
# Check cluster status
make status

# View all pods in key namespaces
make pods

# Check ArgoCD application sync status
make apps

# Force sync all ArgoCD applications
make sync

# View ArgoCD server logs
make logs-argocd
```

## 🧹 Cleanup

```bash
# Destroy everything
make destroy

# Clean Terraform working files (keep state)
make clean

# Clean ALL Terraform files
make clean-all
```

## ➕ Adding New Applications

### 1. Create Application Directory

```bash
mkdir -p argocd/cluster-addons/my-app
```

### 2. Create Application Manifest

```yaml
# argocd/cluster-addons/my-app/application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  sources:
    - repoURL: https://charts.example.com
      targetRevision: 1.0.0
      chart: my-app
      helm:
        releaseName: my-app
        valueFiles:
          - $values/infra/argocd/cluster-addons/my-app/values.yaml
    - repoURL: https://github.com/VENKATESHWARAN-R/first-responder.git
      targetRevision: main
      ref: values
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

### 3. Create Values File

```yaml
# argocd/cluster-addons/my-app/values.yaml
# Your custom Helm values here
```

### 4. Commit and Push

```bash
git add -A
git commit -m "Add my-app to cluster addons"
git push
```

ArgoCD will automatically detect and sync the new application.

## 🐛 Troubleshooting

### Cluster won't start

```bash
# Check Docker is running
docker info

# Check for port conflicts (80, 443)
lsof -i :80
lsof -i :443
```

### ArgoCD applications not syncing

```bash
# Check ArgoCD logs
make logs-argocd

# Check application status
kubectl describe application <app-name> -n argocd

# Force refresh
kubectl patch application <app-name> -n argocd --type merge -p '{"metadata": {"annotations": {"argocd.argoproj.io/refresh": "normal"}}}'
```

### Reset everything

```bash
make destroy
make clean-all
make setup
```

## 📚 Resources

- [Kind Documentation](https://kind.sigs.k8s.io/)
- [ArgoCD User Guide](https://argo-cd.readthedocs.io/)
- [Gateway API](https://gateway-api.sigs.k8s.io/)
- [Envoy Gateway](https://gateway.envoyproxy.io/)
- [cert-manager](https://cert-manager.io/)
- [kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)
