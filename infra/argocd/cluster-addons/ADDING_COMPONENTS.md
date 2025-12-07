# Adding Custom Components to GitOps Cluster

This guide explains how to add custom components to your GitOps-managed Kubernetes cluster using ArgoCD.

## 📋 Table of Contents

1. [Understanding the Structure](#understanding-the-structure)
2. [Adding cert-manager ClusterIssuers](#adding-cert-manager-clusterissuers)
3. [Exposing Services with Gateway API](#exposing-services-with-gateway-api)
4. [Complete Example: Exposing ArgoCD UI](#complete-example-exposing-argocd-ui)
5. [Best Practices](#best-practices)

## Understanding the Structure

Your GitOps setup has two types of components:

### 1. **Helm-based Cluster Add-ons**
Components installed via Helm charts (e.g., cert-manager, Prometheus):
```
argocd/cluster-addons/
├── cert-manager-app.yaml           # ArgoCD Application (Helm)
└── cert-manager/
    └── values.yaml                 # Helm values
```

### 2. **Manifest-based Resources**
Pure Kubernetes manifests (e.g., Gateways, Issuers, Certificates):
```
argocd/cluster-addons/
├── cert-manager-resources-app.yaml  # ArgoCD Application (manifests)
└── cert-manager-resources/
    └── issuers.yaml                 # Kubernetes manifests
```

## Adding cert-manager ClusterIssuers

ClusterIssuers are Kubernetes resources managed by cert-manager. They define how certificates should be issued.

### Available Issuers

The `cert-manager-resources/issuers.yaml` file includes:

1. **letsencrypt-staging** - Let's Encrypt staging (for testing, has higher rate limits)
2. **letsencrypt-prod** - Let's Encrypt production (use for real domains)
3. **selfsigned** - Self-signed certificates (for development)
4. **custom-ca-issuer** - Custom CA (if you have your own CA)

### Configuration Steps

1. **Edit the issuers.yaml file**:
   ```bash
   vim infra/argocd/cluster-addons/cert-manager-resources/issuers.yaml
   ```

2. **Update your email** (required for Let's Encrypt):
   ```yaml
   spec:
     acme:
       email: your-email@example.com  # CHANGE THIS
   ```

3. **Verify Gateway name** (must match your Envoy Gateway):
   ```yaml
   solvers:
     - http01:
         gatewayHTTPRoute:
           parentRefs:
             - name: eg  # Default Envoy Gateway name
   ```

4. **Commit and push**:
   ```bash
   git add infra/argocd/cluster-addons/cert-manager-resources*
   git commit -m "Add cert-manager ClusterIssuers"
   git push
   ```

5. **Verify deployment**:
   ```bash
   # Check ArgoCD sync status
   kubectl get application -n argocd cert-manager-resources
   
   # Verify issuers are created
   kubectl get clusterissuer
   ```

### For Custom CA Issuer

If using your own CA:

```bash
# Create secret with your CA certificate and key
kubectl create secret tls ca-key-pair \
  --cert=ca.crt \
  --key=ca.key \
  --namespace=cert-manager

# The custom-ca-issuer will reference this secret
```

## Exposing Services with Gateway API

Your cluster uses **Gateway API** (not Ingress) for routing external traffic. Here's the component hierarchy:

```
Gateway (L4/L7 load balancer)
  ↓
HTTPRoute/TLSRoute (Routing rules)
  ↓
Service (Kubernetes service)
  ↓
Pods
```

### Key Components

1. **Gateway** - Defines listeners (ports, protocols, TLS)
2. **HTTPRoute** - Routing rules for HTTP/HTTPS traffic
3. **Certificate** - TLS certificate (managed by cert-manager)

## Complete Example: Exposing ArgoCD UI

The `argocd-gateway/gateway.yaml` file exposes ArgoCD UI with TLS.

### Architecture

```
Internet
  ↓
Gateway (argocd-gateway)
  ├─ Listener: HTTP (port 80)  → Redirects to HTTPS
  └─ Listener: HTTPS (port 443) → TLS termination
       ↓
HTTPRoute (argocd-server-https)
  ↓
Service (argocd-server)
  ↓
ArgoCD Server Pods
```

### Configuration Steps

1. **Edit the gateway manifest**:
   ```bash
   vim infra/argocd/cluster-addons/argocd-gateway/gateway.yaml
   ```

2. **Update your domain** (3 places):
   ```yaml
   # In Gateway spec
   hostname: "argocd.yourdomain.com"  # CHANGE THIS
   
   # In Certificate spec
   dnsNames:
     - argocd.yourdomain.com  # CHANGE THIS
   
   # In HTTPRoute spec
   hostnames:
     - "argocd.yourdomain.com"  # CHANGE THIS
   ```

3. **Choose your issuer**:
   ```yaml
   # In Certificate spec
   issuerRef:
     name: letsencrypt-staging  # or letsencrypt-prod, selfsigned, custom-ca-issuer
     kind: ClusterIssuer
   ```

4. **For Kind cluster (local development)**:
   
   Since Kind doesn't have external IPs, you need to:
   
   a. **Use port-forwarding**:
   ```bash
   # Find the Envoy Gateway pod
   kubectl get pods -n envoy-gateway-system
   
   # Port forward the gateway
   kubectl port-forward -n envoy-gateway-system \
     service/envoy-gateway-system-gateway-eg 8443:443
   ```
   
   b. **Update /etc/hosts**:
   ```bash
   echo "127.0.0.1 argocd.yourdomain.com" | sudo tee -a /etc/hosts
   ```
   
   c. **Access**: https://argocd.yourdomain.com:8443

5. **For real clusters with LoadBalancer**:
   
   a. **Get Gateway external IP**:
   ```bash
   kubectl get gateway -n argocd argocd-gateway
   ```
   
   b. **Configure DNS**:
   Create an A record pointing `argocd.yourdomain.com` to the Gateway IP
   
   c. **Access**: https://argocd.yourdomain.com

6. **Commit and deploy**:
   ```bash
   git add infra/argocd/cluster-addons/argocd-gateway*
   git commit -m "Add ArgoCD Gateway for external access"
   git push
   ```

7. **Verify deployment**:
   ```bash
   # Check ArgoCD application
   kubectl get application -n argocd argocd-gateway
   
   # Check Gateway
   kubectl get gateway -n argocd
   
   # Check Certificate (may take a minute to issue)
   kubectl get certificate -n argocd
   kubectl describe certificate -n argocd argocd-tls-cert
   
   # Check HTTPRoutes
   kubectl get httproute -n argocd
   ```

### Troubleshooting

#### Certificate not issuing

```bash
# Check certificate status
kubectl describe certificate -n argocd argocd-tls-cert

# Check CertificateRequest
kubectl get certificaterequest -n argocd

# Check cert-manager logs
kubectl logs -n cert-manager deploy/cert-manager
```

**Common issues**:
- Domain not pointing to Gateway IP (for HTTP-01 challenge)
- Rate limits (switch to `letsencrypt-staging`)
- Gateway name mismatch in ClusterIssuer

#### Gateway not getting IP

```bash
# Check Gateway status
kubectl describe gateway -n argocd argocd-gateway

# Check Envoy Gateway logs
kubectl logs -n envoy-gateway-system deploy/envoy-gateway
```

**Fix**: Ensure `envoy-gateway` application is synced and healthy

#### HTTPRoute not working

```bash
# Check HTTPRoute status
kubectl describe httproute -n argocd argocd-server-https

# Check backend service exists
kubectl get svc -n argocd argocd-server
```

## Best Practices

### 1. Separate Helm and Manifests

```
✅ GOOD:
cert-manager-app.yaml          # Helm chart
cert-manager-resources-app.yaml # Pure manifests

❌ BAD:
cert-manager-app.yaml          # Mixing Helm + manifests
```

### 2. Use Staging Before Production

```yaml
# First deploy with staging
issuerRef:
  name: letsencrypt-staging

# Test thoroughly, then switch to production
issuerRef:
  name: letsencrypt-prod
```

### 3. Namespace Organization

```yaml
# Gateway in same namespace as service
metadata:
  namespace: argocd  # ← Same as argocd-server service

# Or use cross-namespace refs (more complex)
```

### 4. Use Sync Waves for Dependencies

```yaml
# In cert-manager-resources-app.yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "1"  # After cert-manager (wave 0)
```

### 5. Test Locally First

For Kind clusters:
1. Use `selfsigned` issuer first
2. Use port-forwarding to test
3. Then switch to Let's Encrypt staging
4. Finally use production issuer

## Adding Other Services

Use the same pattern for other services:

### Example: Exposing Grafana

```yaml
# grafana-gateway-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: grafana-gateway
  namespace: argocd
spec:
  source:
    repoURL: https://github.com/VENKATESHWARAN-R/first-responder.git
    targetRevision: master
    path: infra/argocd/cluster-addons/grafana-gateway
  destination:
    server: https://kubernetes.default.svc
    namespace: monitoring  # Where Grafana service is
```

```yaml
# grafana-gateway/gateway.yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: grafana-gateway
  namespace: monitoring
spec:
  gatewayClassName: eg
  listeners:
    - name: https
      protocol: HTTPS
      port: 443
      hostname: "grafana.yourdomain.com"
      tls:
        certificateRefs:
          - name: grafana-tls-cert
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: grafana-tls-cert
  namespace: monitoring
spec:
  secretName: grafana-tls-cert
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
    - grafana.yourdomain.com
---
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: grafana
  namespace: monitoring
spec:
  parentRefs:
    - name: grafana-gateway
  hostnames:
    - "grafana.yourdomain.com"
  rules:
    - backendRefs:
        - name: kube-prometheus-stack-grafana
          port: 80
```

## Quick Reference

### Commands

```bash
# List all Gateways
kubectl get gateway -A

# List all HTTPRoutes
kubectl get httproute -A

# List all Certificates
kubectl get certificate -A

# List all ClusterIssuers
kubectl get clusterissuer

# Force ArgoCD sync
kubectl patch application <app-name> -n argocd \
  --type merge -p '{"metadata": {"annotations": {"argocd.argoproj.io/refresh": "hard"}}}'
```

### File Structure

```
infra/argocd/cluster-addons/
├── <component>-app.yaml              # Helm-based application
├── <component>/values.yaml           # Helm values
├── <component>-resources-app.yaml    # Manifest-based application
└── <component>-resources/            # Kubernetes manifests
    ├── issuers.yaml
    ├── certificates.yaml
    └── gateway.yaml
```

## Resources

- [Gateway API Documentation](https://gateway-api.sigs.k8s.io/)
- [cert-manager Documentation](https://cert-manager.io/docs/)
- [Envoy Gateway Documentation](https://gateway.envoyproxy.io/)
- [Let's Encrypt Rate Limits](https://letsencrypt.org/docs/rate-limits/)
