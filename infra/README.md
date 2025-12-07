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
│              App of Apps (Cluster Add-ons)                       │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────────────┐  │
│  │  cert-manager │ │   Prometheus  │ │    Envoy Gateway      │  │
│  │               │ │    Grafana    │ │  (+ Gateway API CRDs) │  │
│  └───────────────┘ └───────────────┘ └───────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│         Your Applications (Separate from Cluster Addons)         │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────────────┐  │
│  │   Your App 1  │ │   Your App 2  │ │     Your App 3        │  │
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
# Then open: http://localhost:8080 (NOT https)
```

### Grafana

```bash
make port-forward-grafana
# Then open: http://localhost:3000
# Login: admin / admin
```

### Prometheus

```bash
make port-forward-prometheus
# Then open: http://localhost:9090
```

## 🗂️ Directory Structure

```
infra/
├── terraform/                    # Terraform configuration
│   ├── main.tf                   # Main orchestration
│   ├── providers.tf              # Provider configuration (kubectl provider!)
│   ├── variables.tf              # Input variables
│   ├── outputs.tf                # Outputs
│   ├── versions.tf               # Version constraints
│   └── argocd-values.yaml        # ArgoCD Helm values
├── argocd/
│   ├── cluster-addons/           # GitOps managed cluster infrastructure
│   │   ├── *-app.yaml            # ArgoCD Application manifests (root level)
│   │   ├── cert-manager/
│   │   │   └── values.yaml       # Helm values for cert-manager
│   │   ├── kube-prometheus-stack/
│   │   │   └── values.yaml       # Helm values for monitoring stack
│   │   └── envoy-gateway/
│   │       └── values.yaml       # Helm values for Envoy Gateway
│   └── applications/             # Your application deployments (create this)
│       └── your-app/
│           ├── application.yaml  # ArgoCD Application for your app
│           └── values.yaml       # (Optional) Helm values
├── scripts/
│   ├── setup.sh                  # Full setup script
│   └── destroy.sh                # Cleanup script
├── Makefile                      # Convenience commands
└── README.md                     # This file
```

### Key Points:
- **`cluster-addons/*-app.yaml`** - Application manifests at root level for ArgoCD App of Apps pattern
- **`cluster-addons/*/values.yaml`** - Only values files in subdirectories (no duplicate application.yaml files)
- **Application manifests must be at root level** - ArgoCD scans only the directory root, not subdirectories

## ⚙️ Configuration

### Terraform Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `cluster_name` | `first-responder` | Kind cluster name |
| `kubernetes_version` | `v1.31.0` | Kubernetes version |
| `worker_nodes` | `2` | Number of worker nodes |
| `argocd_chart_version` | `7.7.5` | ArgoCD Helm chart version |
| `git_repo_url` | `https://github.com/VENKATESHWARAN-R/first-responder.git` | Git repo for ArgoCD |
| `git_target_revision` | `master` | Git branch/tag to sync |
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

## 📦 Cluster Add-ons

The following add-ons are managed via ArgoCD's App of Apps pattern:

| Addon | Namespace | Description |
|-------|-----------|-------------|
| **cert-manager** | `cert-manager` | X.509 certificate management |
| **kube-prometheus-stack** | `monitoring` | Prometheus + Grafana + Alertmanager |
| **envoy-gateway** | `envoy-gateway-system` | Envoy Gateway + Gateway API CRDs |

### Customizing Add-ons

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

## ➕ Adding New Cluster Add-ons

### Example: Kubernetes Dashboard

1. **Create values directory** (if the Helm chart needs custom values):
   ```bash
   mkdir -p argocd/cluster-addons/kubernetes-dashboard
   ```

2. **Create values file** (optional):
   ```bash
   cat > argocd/cluster-addons/kubernetes-dashboard/values.yaml <<EOF
   # Kubernetes Dashboard Helm values
   service:
     type: ClusterIP
   protocolHttp: true
   EOF
   ```

3. **Create Application manifest at root level**:
   ```bash
   cat > argocd/cluster-addons/kubernetes-dashboard-app.yaml <<EOF
   apiVersion: argoproj.io/v1alpha1
   kind: Application
   metadata:
     name: kubernetes-dashboard
     namespace: argocd
     finalizers:
       - resources-finalizer.argocd.argoproj.io
   spec:
     project: default
     sources:
       - repoURL: https://kubernetes.github.io/dashboard/
         targetRevision: 7.10.0
         chart: kubernetes-dashboard
         helm:
           releaseName: kubernetes-dashboard
           valueFiles:
             - \$values/infra/argocd/cluster-addons/kubernetes-dashboard/values.yaml
       - repoURL: https://github.com/VENKATESHWARAN-R/first-responder.git
         targetRevision: master
         ref: values
     destination:
       server: https://kubernetes.default.svc
       namespace: kubernetes-dashboard
     syncPolicy:
       automated:
         prune: true
         selfHeal: true
       syncOptions:
         - CreateNamespace=true
         - ServerSideApply=true
       retry:
         limit: 5
         backoff:
           duration: 5s
           factor: 2
           maxDuration: 3m
   EOF
   ```

4. **Commit and push**:
   ```bash
   git add argocd/cluster-addons/kubernetes-dashboard*
   git commit -m "Add Kubernetes Dashboard to cluster addons"
   git push
   ```

5. **Wait for ArgoCD to sync** (or force sync):
   ```bash
   make sync
   make apps  # Check status
   ```

### Important Notes:
- Application manifests MUST be at root level of `cluster-addons/` directory
- Use `*-app.yaml` naming convention for clarity
- Values files go in subdirectories: `cluster-addons/<addon-name>/values.yaml`
- The `$values` reference in `valueFiles` refers to the second source (your Git repo)

## 🚀 Adding Your Own Applications

Your applications should be managed **separately from cluster add-ons** to:
- Keep infrastructure and application deployments independent
- Allow easy updates without affecting cluster core components
- Maintain clear separation of concerns

### Option 1: Single Application (Simple)

Create an ArgoCD Application directly in the cluster:

```bash
cat <<EOF | kubectl apply -f -
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-web-app
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: https://github.com/VENKATESHWARAN-R/first-responder.git
    targetRevision: master
    path: apps/my-web-app  # Your app k8s manifests or Helm chart
  destination:
    server: https://kubernetes.default.svc
    namespace: my-web-app
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
EOF
```

### Option 2: App of Apps for Your Applications (Recommended)

Create a separate App of Apps structure for your applications:

1. **Create directory structure**:
   ```bash
   mkdir -p argocd/applications
   ```

2. **Create your application manifest**:
   ```bash
   cat > argocd/applications/my-web-app.yaml <<EOF
   apiVersion: argoproj.io/v1alpha1
   kind: Application
   metadata:
     name: my-web-app
     namespace: argocd
     finalizers:
       - resources-finalizer.argocd.argoproj.io
   spec:
     project: default
     source:
       repoURL: https://github.com/VENKATESHWARAN-R/first-responder.git
       targetRevision: master
       path: apps/my-web-app
     destination:
       server: https://kubernetes.default.svc
       namespace: my-web-app
     syncPolicy:
       automated:
         prune: true
         selfHeal: true
       syncOptions:
         - CreateNamespace=true
   EOF
   ```

3. **Create root application** (one time):
   ```bash
   cat <<EOF | kubectl apply -f -
   apiVersion: argoproj.io/v1alpha1
   kind: Application
   metadata:
     name: applications
     namespace: argocd
     finalizers:
       - resources-finalizer.argocd.argoproj.io
   spec:
     project: default
     source:
       repoURL: https://github.com/VENKATESHWARAN-R/first-responder.git
       targetRevision: master
       path: infra/argocd/applications
     destination:
       server: https://kubernetes.default.svc
       namespace: argocd
     syncPolicy:
       automated:
         prune: true
         selfHeal: true
   EOF
   ```

4. **Add your application code/manifests**:
   ```bash
   mkdir -p apps/my-web-app
   # Add your Kubernetes manifests or Helm chart here
   ```

5. **Commit and push**:
   ```bash
   git add argocd/applications/ apps/
   git commit -m "Add my web application"
   git push
   ```

### Benefits of Separate App of Apps:
- ✅ Cluster infrastructure (`cluster-addons`) separate from applications (`applications`)
- ✅ Easy to update apps without touching cluster components
- ✅ Can have different sync policies, retention policies, etc.
- ✅ Clear organizational structure

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

### ArgoCD UI not accessible

**Important:** ArgoCD is configured with `server.insecure: true` for local development.
- Use **HTTP** not HTTPS: `http://localhost:8080`
- NOT: `https://localhost:8080`

### Reset everything

```bash
make destroy
make clean-all
make setup
```

## 📝 Best Practices

1. **Cluster Add-ons vs Applications**
   - Use `cluster-addons/` for infrastructure (cert-manager, monitoring, gateways)
   - Use `applications/` for your workloads
   - Keep them separate for easier management

2. **GitOps Workflow**
   - All changes through Git commits
   - Let ArgoCD automatically sync
   - Use `make apps` to monitor sync status

3. **Values Files**
   - Store all customizations in `values.yaml` files
   - Never modify charts directly
   - Use image pull secrets and registry configs in values

4. **Application Naming**
   - Cluster addons: `<name>-app.yaml` (e.g., `cert-manager-app.yaml`)
   - Clear, descriptive names
   - Consistent naming conventions

## 📚 Resources

- [Kind Documentation](https://kind.sigs.k8s.io/)
- [ArgoCD User Guide](https://argo-cd.readthedocs.io/)
- [Gateway API](https://gateway-api.sigs.k8s.io/)
- [Envoy Gateway](https://gateway.envoyproxy.io/)
- [cert-manager](https://cert-manager.io/)
- [kube-prometheus-stack](https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack)
- [Kubernetes Dashboard](https://kubernetes.io/docs/tasks/access-application-cluster/web-ui-dashboard/)
