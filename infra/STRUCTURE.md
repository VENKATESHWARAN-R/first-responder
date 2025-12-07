# Infrastructure Directory Structure

This document explains the current working structure of the infra directory.

## Final Clean Structure

```
infra/
├── terraform/                              # Terraform files for cluster provisioning
│   ├── main.tf                             # Creates Kind cluster + ArgoCD
│   ├── providers.tf                        # Uses kubectl provider (important!)
│   ├── variables.tf                        # Configuration variables
│   ├── versions.tf                         # Provider versions
│   ├── outputs.tf                          # Cluster outputs
│   └── argocd-values.yaml                  # ArgoCD Helm chart values
│
├── argocd/
│   ├── cluster-addons/                     # Cluster infrastructure (App of Apps)
│   │   │
│   │   ├── cert-manager-app.yaml           # ✓ Application manifest (root level)
│   │   ├── cert-manager/
│   │   │   └── values.yaml                 # ✓ Helm values only
│   │   │
│   │   ├── kube-prometheus-stack-app.yaml  # ✓ Application manifest (root level)
│   │   ├── kube-prometheus-stack/
│   │   │   └── values.yaml                 # ✓ Helm values only
│   │   │
│   │   ├── envoy-gateway-app.yaml          # ✓ Application manifest (root level)
│   │   └── envoy-gateway/
│   │       └── values.yaml                 # ✓ Helm values only
│   │
│   └── applications/                       # (To be created) Your app deployments
│       └── README.md
│
├── scripts/
│   ├── setup.sh                            # Automated cluster setup
│   └── destroy.sh                          # Cluster teardown
│
├── Makefile                                # Convenience commands
└── README.md                               # Main documentation

```

## Key Principles

### ✅ DO:
1. **Application manifests at root**: `cluster-addons/*-app.yaml`
2. **Values in subdirectories**: `cluster-addons/*/values.yaml`
3. **Separate apps from infrastructure**: Use `applications/` for your apps
4. **Commit all changes to Git**: Let ArgoCD sync automatically

### ❌ DON'T:
1. **Don't put application.yaml in subdirectories** - ArgoCD won't find them
2. **Don't mix cluster infrastructure with applications** - Keep them separate
3. **Don't modify running resources directly** - Use GitOps workflow

## Application Types

### Cluster Add-ons (Infrastructure)
- **Location**: `argocd/cluster-addons/`
- **Managed by**: App of Apps pattern via `cluster-addons` application
- **Purpose**: Cluster-wide infrastructure (cert-manager, monitoring, gateways)
- **Examples**:
  - cert-manager
  - kube-prometheus-stack
  - envoy-gateway
  - (future) kubernetes-dashboard, external-dns, etc.

### Your Applications
- **Location**: `argocd/applications/` (to be created)
- **Managed by**: Separate App of Apps or individual applications
- **Purpose**: Your workloads and services
- **Examples**:
  - Web applications
  - APIs
  - Microservices
  - Databases

## Current Deployed Applications

As of the latest commit, these applications are managed by ArgoCD:

| Application | Type | Namespace | Status | Purpose |
|------------|------|-----------|--------|---------|
| `cluster-addons` | App of Apps | argocd | ✅ Synced | Root app managing all cluster infrastructure |
| `cert-manager` | Cluster Addon | cert-manager | ✅ Synced | Certificate management |
| `kube-prometheus-stack` | Cluster Addon | monitoring | ✅ Synced | Monitoring (Prometheus + Grafana) |
| `envoy-gateway` | Cluster Addon | envoy-gateway-system | ✅ Synced | Gateway API + Envoy Gateway |

## Changes from Initial Setup

### What Changed:
1. **Removed duplicate `application.yaml` files** from subdirectories
2. **Consolidated Gateway API** into Envoy Gateway (Envoy includes CRDs)
3. **Updated README** with current structure and comprehensive guides
4. **Clarified separation** between cluster infrastructure and applications

### Why:
- **Cleaner structure** - No duplicate files
- **Simpler maintenance** - Fewer files to manage
- **Better organization** - Clear separation of concerns
- **Easier to extend** - Clear patterns for adding new components

## Next Steps

### Adding Cluster Add-ons
See README.md section "Adding New Cluster Add-ons"

Example: Adding Kubernetes Dashboard
1. Create `kubernetes-dashboard-app.yaml` at root level
2. (Optional) Create `kubernetes-dashboard/values.yaml` for customization
3. Commit and push - ArgoCD syncs automatically

### Adding Your Applications
See README.md section "Adding Your Own Applications"

Two options:
1. **Simple**: Create ArgoCD Application directly
2. **Recommended**: Create App of Apps for your applications in `argocd/applications/`

## Troubleshooting

### Application not appearing in ArgoCD
- **Check**: Is the application manifest at root level of `cluster-addons/`?
- **Check**: Does it have `.yaml` or `-app.yaml` suffix?
- **Check**: Did you commit and push to Git?
- **Action**: Force refresh: `kubectl patch application cluster-addons -n argocd --type merge -p '{"metadata": {"annotations": {"argocd.argoproj.io/refresh": "hard"}}}'`

### Application shows OutOfSync
- **Normal**: Brief OutOfSync during updates
- **Check**: `kubectl describe application <name> -n argocd` for errors
- **Action**: Force sync: `make sync`

### Can't find values.yaml changes
- **Check**: Did you commit and push changes?
- **Check**: Is ArgoCD pointing to correct branch? (Check `git_target_revision` in variables.tf)
- **Action**: Force refresh application from Git
