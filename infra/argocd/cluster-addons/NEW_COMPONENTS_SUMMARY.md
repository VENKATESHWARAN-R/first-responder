# New Components Summary

## What We Added

### 1. **cert-manager ClusterIssuers** (cert-manager-resources)

**Files Created:**
```
infra/argocd/cluster-addons/
├── cert-manager-resources-app.yaml     # NEW: ArgoCD Application
└── cert-manager-resources/             # NEW: Directory
    └── issuers.yaml                    # NEW: ClusterIssuers manifest
```

**What it does:**
- Provides 4 ClusterIssuers for certificate management:
  - `letsencrypt-staging` - Let's Encrypt staging (testing)
  - `letsencrypt-prod` - Let's Encrypt production
  - `selfsigned` - Self-signed certificates (dev)
  - `custom-ca-issuer` - Custom CA support

**Usage:**
```yaml
# In a Certificate resource
spec:
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
```

### 2. **ArgoCD Gateway** (External Access with TLS)

**Files Created:**
```
infra/argocd/cluster-addons/
├── argocd-gateway-app.yaml            # NEW: ArgoCD Application
└── argocd-gateway/                    # NEW: Directory
    └── gateway.yaml                   # NEW: Gateway API resources
```

**What it includes:**
- **Gateway**: Handles HTTP (80) and HTTPS (443) traffic
- **Certificate**: Auto-managed TLS certificate via cert-manager
- **HTTPRoute (HTTPS)**: Routes traffic to ArgoCD server
- **HTTPRoute (HTTP redirect)**: Redirects HTTP → HTTPS

**Access:**
```bash
# After configuration:
https://argocd.yourdomain.com
```

## Updated Cluster Structure

```
┌──────────────────────────────────────────────────────────────────┐
│                        Terraform                                  │
│  ┌─────────────────┐    ┌─────────────────┐                      │
│  │  Kind Cluster   │───▶│     ArgoCD      │                      │
│  │  (1 CP + 2 W)   │    │   (Bootstrap)   │                      │
│  └─────────────────┘    └────────┬─────────┘                     │
└───────────────────────────────────┼───────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────┐
│              App of Apps (Cluster Add-ons)                        │
│  ┌───────────────────┐ ┌──────────────────┐ ┌─────────────────┐ │
│  │   cert-manager    │ │    Prometheus    │ │  Envoy Gateway  │ │
│  │  (Helm Chart)     │ │     Grafana      │ │  + Gateway API  │ │
│  └───────────────────┘ └──────────────────┘ └─────────────────┘ │
│  ┌───────────────────┐ ┌──────────────────┐                     │
│  │ cert-manager      │ │  argocd-gateway  │                     │ 
│  │   Resources       │ │  (External TLS)  │          ← NEW      │
│  │ (ClusterIssuers)  │ │                  │                     │
│  └───────────────────┘ └──────────────────┘                     │
└──────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                       ┌────────────────────┐
                       │  External Traffic  │
                       │  (Gateway API +    │
                       │   TLS/HTTPS)       │
                       └────────────────────┘
```

## Directory Structure

```
infra/argocd/cluster-addons/
│
├── ADDING_COMPONENTS.md                    # ← Guide for adding components
│
├── cert-manager-app.yaml                   # Helm: cert-manager installation
├── cert-manager/
│   └── values.yaml                         # Helm values
│
├── cert-manager-resources-app.yaml         # ← NEW: Manifests for issuers
├── cert-manager-resources/                 # ← NEW
│   └── issuers.yaml                        # ← NEW: ClusterIssuer definitions
│
├── envoy-gateway-app.yaml                  # Helm: Envoy Gateway
├── envoy-gateway/
│   └── values.yaml                         # Helm values
│
├── kube-prometheus-stack-app.yaml          # Helm: Prometheus + Grafana
├── kube-prometheus-stack/
│   └── values.yaml                         # Helm values
│
├── argocd-gateway-app.yaml                 # ← NEW: Gateway for ArgoCD UI
└── argocd-gateway/                         # ← NEW
    └── gateway.yaml                        # ← NEW: Gateway, Certificate, HTTPRoutes
```

## Configuration Needed

### Before Committing

You **MUST** update these values:

#### 1. In `cert-manager-resources/issuers.yaml`:
```yaml
# Line 11 & 27
email: your-email@example.com  # ← CHANGE THIS
```

#### 2. In `argocd-gateway/gateway.yaml`:
```yaml
# Lines 14, 22, 38, 52, 63
hostname: "argocd.yourdomain.com"  # ← CHANGE THIS (3 places)
dnsNames:
  - argocd.yourdomain.com          # ← CHANGE THIS (1 place)
```

## Deployment Steps

### Option 1: Deploy Both Components

```bash
# 1. Update configuration (see above)
vim infra/argocd/cluster-addons/cert-manager-resources/issuers.yaml
vim infra/argocd/cluster-addons/argocd-gateway/gateway.yaml

# 2. Commit and push
git add infra/argocd/cluster-addons/
git commit -m "Add cert-manager issuers and ArgoCD gateway"
git push

# 3. Wait for ArgoCD to sync (auto-sync is enabled)
# Or force sync:
kubectl patch application cluster-addons -n argocd \
  --type merge -p '{"metadata": {"annotations": {"argocd.argoproj.io/refresh": "hard"}}}'

# 4. Check status
kubectl get application -n argocd
kubectl get clusterissuer
kubectl get gateway -n argocd
kubectl get certificate -n argocd
```

### Option 2: Deploy Only ClusterIssuers

```bash
# Don't commit argocd-gateway files
git add infra/argocd/cluster-addons/cert-manager-resources*
git commit -m "Add cert-manager ClusterIssuers"
git push
```

### Option 3: Deploy Only ArgoCD Gateway

```bash
# Don't commit cert-manager-resources files
git add infra/argocd/cluster-addons/argocd-gateway*
git commit -m "Add ArgoCD external gateway"
git push
```

## Verification

### Check ArgoCD Applications

```bash
kubectl get application -n argocd

# Should show:
# NAME                        SYNC STATUS   HEALTH STATUS
# cluster-addons              Synced        Healthy
# cert-manager                Synced        Healthy
# cert-manager-resources      Synced        Healthy  ← NEW
# envoy-gateway               Synced        Healthy
# kube-prometheus-stack       Synced        Healthy
# argocd-gateway              Synced        Healthy  ← NEW
```

### Check ClusterIssuers

```bash
kubectl get clusterissuer

# Should show:
# NAME                  READY   AGE
# letsencrypt-staging   True    Xm
# letsencrypt-prod      True    Xm
# selfsigned            True    Xm
# custom-ca-issuer      True    Xm  (if CA secret exists)
```

### Check Gateway and Certificate

```bash
# Gateway
kubectl get gateway -n argocd
kubectl describe gateway -n argocd argocd-gateway

# Certificate
kubectl get certificate -n argocd
kubectl describe certificate -n argocd argocd-tls-cert

# HTTPRoutes
kubectl get httproute -n argocd
```

## Accessing ArgoCD Externally

### For Kind Cluster (Local)

```bash
# 1. Port forward Envoy Gateway
kubectl port-forward -n envoy-gateway-system \
  service/envoy-gateway-system-gateway-eg 8443:443

# 2. Add to /etc/hosts
echo "127.0.0.1 argocd.yourdomain.com" | sudo tee -a /etc/hosts

# 3. Access
open https://argocd.yourdomain.com:8443
```

### For Real Cluster

```bash
# 1. Get Gateway external IP
kubectl get gateway -n argocd argocd-gateway -o jsonpath='{.status.addresses[0].value}'

# 2. Configure DNS A record
# argocd.yourdomain.com → <GATEWAY_IP>

# 3. Access
open https://argocd.yourdomain.com
```

## Troubleshooting

See [`ADDING_COMPONENTS.md`](./ADDING_COMPONENTS.md) for detailed troubleshooting.

### Quick Checks

```bash
# ArgoCD application not syncing
kubectl describe application cert-manager-resources -n argocd
kubectl describe application argocd-gateway -n argocd

# Certificate not issuing
kubectl describe certificate argocd-tls-cert -n argocd
kubectl get certificaterequest -n argocd
kubectl logs -n cert-manager deploy/cert-manager

# Gateway not working
kubectl describe gateway argocd-gateway -n argocd
kubectl logs -n envoy-gateway-system deploy/envoy-gateway
```

## Next Steps

### Other Services to Expose

Use the same pattern for:
- **Grafana**: `grafana.yourdomain.com`
- **Prometheus**: `prometheus.yourdomain.com`
- **Your applications**: `app.yourdomain.com`

See examples in [`ADDING_COMPONENTS.md`](./ADDING_COMPONENTS.md)

### Additional Issuers

- **DNS-01 challenge**: For wildcard certificates
- **Multiple CAs**: Different issuers for different purposes
- **Vault integration**: Enterprise PKI

## Resources

- [ADDING_COMPONENTS.md](./ADDING_COMPONENTS.md) - Detailed guide
- [Gateway API Docs](https://gateway-api.sigs.k8s.io/)
- [cert-manager Docs](https://cert-manager.io/docs/)
- [Envoy Gateway Docs](https://gateway.envoyproxy.io/)
