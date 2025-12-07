# 🚀 First Responder - Local Kubernetes Development Environment

> ⚠️ **Vibe Coded Disclaimer**: This project was largely "vibe coded" for learning and experimentation with Kubernetes, ArgoCD GitOps, and monitoring. While functional and reproducible, please review carefully before adapting for production use.

A disposable, reproducible Kubernetes development environment featuring:
- **Kind** cluster with ArgoCD GitOps
- **Monitoring** with Prometheus & Grafana
- **Demo Applications** - Next.js frontend + Python FastAPI backend

## ✨ What's Included

| Component | Description |
|-----------|-------------|
| **Kind Cluster** | 1 control plane + 2 workers |
| **ArgoCD** | GitOps with App of Apps pattern |
| **cert-manager** | X.509 certificate management |
| **kube-prometheus-stack** | Prometheus + Grafana + Alertmanager |
| **Envoy Gateway** | Gateway API implementation |
| **Demo Apps** | Next.js frontend + Python FastAPI backend |

## 📋 Prerequisites

Install these tools before getting started:

```bash
# macOS (using Homebrew)
brew install docker terraform kubectl kind
```

| Tool | Required Version |
|------|------------------|
| Docker | Running |
| Terraform | >= 1.0 |
| kubectl | Latest |
| kind | Latest |

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/VENKATESHWARAN-R/first-responder.git
cd first-responder

# Setup everything (cluster + ArgoCD + addons) - takes ~3-5 minutes
cd infra
make setup

# Check status
make status
make apps

# Build and load demo applications
make build-images
```

## 📊 Access Services

```bash
# ArgoCD UI (http://localhost:8080)
make port-forward-argocd
# Username: admin | Password: make argocd-password

# Grafana (http://localhost:3000)
make port-forward-grafana
# Username: admin | Password: admin

# Prometheus (http://localhost:9090)
make port-forward-prometheus

# Demo Frontend (http://localhost:3001)
make port-forward-load-tester-frontend

# Demo Backend (http://localhost:8000/docs)
make port-forward-load-tester-backend
```

## 🗂️ Project Structure

```
first-responder/
├── infra/                    # Infrastructure & GitOps
│   ├── terraform/            # Kind cluster + ArgoCD bootstrap
│   ├── argocd/
│   │   ├── cluster-addons/   # cert-manager, prometheus, envoy
│   │   └── applications/     # Your app deployments
│   ├── scripts/              # Setup & destroy scripts
│   ├── Makefile              # 20+ convenience commands
│   └── README.md             # Detailed infrastructure docs
│
└── application/              # Demo applications
    ├── backend/              # Python FastAPI
    └── frontend/             # Next.js
```

## 🛠️ Available Commands

```bash
make help                # Show all commands
make setup              # Full cluster setup
make destroy            # Tear down everything
make status             # Check cluster status
make apps               # Show ArgoCD sync status
make build-images       # Build & load app images
```

See `infra/Makefile` for the complete list of targets.

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [infra/README.md](./infra/README.md) | Detailed infrastructure setup |
| [infra/STRUCTURE.md](./infra/STRUCTURE.md) | Directory structure guide |
| [application/README.md](./application/README.md) | Application deployment guide |
| [infra/MONITORING_GUIDE.md](./infra/MONITORING_GUIDE.md) | Monitoring configuration |

## 🧹 Cleanup

```bash
cd infra
make destroy      # Destroy cluster (prompts for confirmation)
make clean-all    # Remove all terraform files
```

## 📝 Notes

- Cluster recreation from scratch takes ~3-5 minutes
- ArgoCD syncs all addons automatically after setup
- Demo applications need `make build-images` before first deploy
- Use `make sync` to force sync all ArgoCD applications

---

**Happy experimenting!** 🎉
