# 🚀 Deployment Checklist: cert-manager Issuers & ArgoCD Gateway

Use this checklist to deploy the new components to your cluster.

## ✅ Pre-Deployment Checklist

### 1. Review Files Created

- [ ] `cert-manager-resources-app.yaml` - ArgoCD app for ClusterIssuers
- [ ] `cert-manager-resources/issuers.yaml` - ClusterIssuer definitions
- [ ] `argocd-gateway-app.yaml` - ArgoCD app for Gateway
- [ ] `argocd-gateway/gateway.yaml` - Gateway, Certificate, HTTPRoutes
- [ ] `ADDING_COMPONENTS.md` - Comprehensive guide
- [ ] `NEW_COMPONENTS_SUMMARY.md` - Quick summary

### 2. Configuration Required

#### cert-manager ClusterIssuers

- [ ] Open `infra/argocd/cluster-addons/cert-manager-resources/issuers.yaml`
- [ ] Update email address (2 places - lines 11 and 27):
  ```yaml
  email: your-email@example.com  # ← CHANGE THIS
  ```
- [ ] Verify Gateway name matches your setup (default: `eg`):
  ```yaml
  parentRefs:
    - name: eg  # Your Envoy Gateway name
  ```

#### ArgoCD Gateway

- [ ] Open `infra/argocd/cluster-addons/argocd-gateway/gateway.yaml`
- [ ] Update domain name (5 places - see below):

**Line 14 (Gateway HTTP listener):**
```yaml
hostname: "argocd.yourdomain.com"  # ← CHANGE THIS
```

**Line 22 (Gateway HTTPS listener):**
```yaml
hostname: "argocd.yourdomain.com"  # ← CHANGE THIS
```

**Line 38 (Certificate):**
```yaml
dnsNames:
  - argocd.yourdomain.com  # ← CHANGE THIS
```

**Line 52 (HTTPRoute HTTPS):**
```yaml
hostnames:
  - "argocd.yourdomain.com"  # ← CHANGE THIS
```

**Line 63 (HTTPRoute redirect):**
```yaml
hostnames:
  - "argocd.yourdomain.com"  # ← CHANGE THIS
```

- [ ] Choose issuer (line 35):
  ```yaml
  issuerRef:
    name: letsencrypt-staging  # Options: letsencrypt-staging, letsencrypt-prod, selfsigned, custom-ca-issuer
  ```

### 3. Decide Deployment Strategy

Choose one:

**Option A: Deploy Everything** (Recommended)
- [ ] Deploy both cert-manager-resources and argocd-gateway

**Option B: Deploy Only ClusterIssuers**
- [ ] Deploy only cert-manager-resources
- [ ] Skip argocd-gateway for now

**Option C: Deploy Only ArgoCD Gateway**
- [ ] Deploy only argocd-gateway
- [ ] Skip cert-manager-resources (use existing issuer)

## 🚀 Deployment Steps

### Step 1: Verify Current Cluster Status

```bash
# Check ArgoCD is healthy
kubectl get pods -n argocd

# Check current applications
kubectl get application -n argocd

# Check Envoy Gateway is running
kubectl get pods -n envoy-gateway-system
```

- [ ] ArgoCD pods are running
- [ ] Envoy Gateway pods are running
- [ ] All current applications are synced

### Step 2: Deploy to Git Repository

#### If deploying everything:

```bash
cd /Users/venkateshwaranr/projects/dev/first-responder

# Stage all new files
git add infra/argocd/cluster-addons/cert-manager-resources*
git add infra/argocd/cluster-addons/argocd-gateway*
git add infra/argocd/cluster-addons/*.md

# Commit
git commit -m "Add cert-manager ClusterIssuers and ArgoCD Gateway

- Add cert-manager-resources application with 4 ClusterIssuers
  - letsencrypt-staging (for testing)
  - letsencrypt-prod (for production)
  - selfsigned (for development)
  - custom-ca-issuer (for custom CA)

- Add argocd-gateway application for external access
  - Gateway with HTTP/HTTPS listeners
  - TLS certificate via cert-manager
  - HTTPRoutes for routing and HTTP→HTTPS redirect

- Add comprehensive documentation:
  - ADDING_COMPONENTS.md - detailed guide
  - NEW_COMPONENTS_SUMMARY.md - quick reference"

# Push to remote
git push origin master
```

#### If deploying only ClusterIssuers:

```bash
git add infra/argocd/cluster-addons/cert-manager-resources*
git add infra/argocd/cluster-addons/*.md
git commit -m "Add cert-manager ClusterIssuers"
git push origin master
```

#### If deploying only ArgoCD Gateway:

```bash
git add infra/argocd/cluster-addons/argocd-gateway*
git add infra/argocd/cluster-addons/*.md
git commit -m "Add ArgoCD Gateway for external access"
git push origin master
```

- [ ] Changes committed
- [ ] Changes pushed to remote

### Step 3: Trigger ArgoCD Sync

```bash
# Force refresh of cluster-addons (App of Apps)
kubectl patch application cluster-addons -n argocd \
  --type merge -p '{"metadata": {"annotations": {"argocd.argoproj.io/refresh": "hard"}}}'

# Wait a few seconds, then check status
sleep 10
kubectl get application -n argocd
```

- [ ] ArgoCD detected new applications
- [ ] New applications appear in list

### Step 4: Monitor Application Sync

```bash
# Watch all applications
watch kubectl get application -n argocd

# Or use ArgoCD UI
make port-forward-argocd
# Open http://localhost:8080
```

Wait for:
- [ ] `cert-manager-resources` - Synced & Healthy (if deployed)
- [ ] `argocd-gateway` - Synced & Healthy (if deployed)

**Expected sync time:** 1-3 minutes

## 🔍 Verification Steps

### Verify ClusterIssuers (if deployed)

```bash
# List ClusterIssuers
kubectl get clusterissuer

# Expected output:
# NAME                  READY   AGE
# custom-ca-issuer      True    Xm  (if CA secret exists, otherwise False)
# letsencrypt-prod      True    Xm
# letsencrypt-staging   True    Xm
# selfsigned            True    Xm

# Detailed view
kubectl describe clusterissuer letsencrypt-prod
kubectl describe clusterissuer letsencrypt-staging
```

- [ ] All issuers show READY=True (except custom-ca-issuer if no CA secret)
- [ ] No error messages in description

### Verify ArgoCD Gateway (if deployed)

```bash
# Check Gateway
kubectl get gateway -n argocd
kubectl describe gateway -n argocd argocd-gateway

# Check Certificate
kubectl get certificate -n argocd
kubectl describe certificate -n argocd argocd-tls-cert

# Check HTTPRoutes
kubectl get httproute -n argocd

# Check cert-manager Certificate status
kubectl get certificaterequest -n argocd
```

- [ ] Gateway exists and shows listeners configured
- [ ] Certificate shows "Ready" status (may take 1-2 minutes)
- [ ] HTTPRoutes are attached to gateway
- [ ] No error events

### Certificate Troubleshooting

If certificate is not ready after 2 minutes:

```bash
# Check Certificate details
kubectl describe certificate -n argocd argocd-tls-cert

# Check CertificateRequest
kubectl describe certificaterequest -n argocd

# Check cert-manager logs
kubectl logs -n cert-manager deploy/cert-manager --tail=50

# Check for challenges (HTTP-01)
kubectl get challenges -n argocd
kubectl describe challenge -n argocd
```

**Common issues:**
- Domain not pointing to Gateway IP (HTTP-01 challenge fails)
- Rate limit hit (use letsencrypt-staging)
- Gateway name mismatch

## 🌐 Accessing ArgoCD Externally

### For Kind Cluster (Local Development)

Since Kind doesn't provide external LoadBalancer IPs:

```bash
# 1. Find Envoy Gateway service
kubectl get svc -n envoy-gateway-system

# 2. Port forward to local machine
kubectl port-forward -n envoy-gateway-system \
  service/envoy-gateway-system-gateway-eg 8443:443 &

# 3. Add to /etc/hosts
echo "127.0.0.1 argocd.yourdomain.com" | sudo tee -a /etc/hosts

# 4. Test access (may need to accept self-signed cert for staging)
curl -k https://argocd.yourdomain.com:8443

# 5. Open in browser
open https://argocd.yourdomain.com:8443
```

- [ ] Port forward is running
- [ ] Host entry added
- [ ] Can access ArgoCD UI via domain name

### For Cloud Cluster (AWS, GCP, Azure)

```bash
# 1. Get Gateway external IP/hostname
kubectl get gateway -n argocd argocd-gateway \
  -o jsonpath='{.status.addresses[0].value}'

# Save this IP/hostname
GATEWAY_IP=$(kubectl get gateway -n argocd argocd-gateway \
  -o jsonpath='{.status.addresses[0].value}')
echo "Gateway IP: $GATEWAY_IP"

# 2. Configure DNS
# Create an A record (or CNAME if hostname):
#   argocd.yourdomain.com → $GATEWAY_IP

# 3. Wait for DNS propagation (1-5 minutes)
nslookup argocd.yourdomain.com

# 4. Test
curl https://argocd.yourdomain.com

# 5. Access
open https://argocd.yourdomain.com
```

- [ ] Gateway has external IP
- [ ] DNS configured
- [ ] DNS resolves correctly
- [ ] Can access via HTTPS

## ✅ Final Verification Checklist

- [ ] All ArgoCD applications show "Synced" and "Healthy"
- [ ] ClusterIssuers are Ready
- [ ] Certificate is issued and Ready
- [ ] Gateway is configured with listeners
- [ ] HTTPRoutes are attached
- [ ] Can access ArgoCD UI via configured domain
- [ ] HTTP redirects to HTTPS
- [ ] TLS certificate is valid

## 📊 Monitoring

### Regular Health Checks

```bash
# Quick status check
kubectl get application -n argocd
kubectl get clusterissuer
kubectl get gateway -n argocd
kubectl get certificate -n argocd

# Detailed ArgoCD app status
kubectl describe application cert-manager-resources -n argocd
kubectl describe application argocd-gateway -n argocd
```

### Logs

```bash
# cert-manager logs
kubectl logs -n cert-manager deploy/cert-manager --tail=50 -f

# Envoy Gateway logs
kubectl logs -n envoy-gateway-system deploy/envoy-gateway --tail=50 -f

# ArgoCD logs
kubectl logs -n argocd deploy/argocd-server --tail=50 -f
```

## 🔄 Rollback (if needed)

If something goes wrong:

```bash
# Delete ArgoCD applications
kubectl delete application cert-manager-resources -n argocd
kubectl delete application argocd-gateway -n argocd

# Or revert Git commit
git revert HEAD
git push origin master

# ArgoCD will automatically remove the resources
```

## 📚 Next Steps

After successful deployment:

1. **Expose other services**
   - [ ] Grafana (`grafana.yourdomain.com`)
   - [ ] Prometheus (`prometheus.yourdomain.com`)

2. **Try DNS-01 challenge** (for wildcard certs)
   - See `ADDING_COMPONENTS.md` for examples

3. **Production hardening**
   - [ ] Switch from staging to production issuer
   - [ ] Configure rate limiting
   - [ ] Add monitoring alerts

4. **Document your custom domain setup**
   - [ ] Update README.md with your specific instructions

## 🆘 Getting Help

- **Detailed Guide**: See `ADDING_COMPONENTS.md`
- **Quick Reference**: See `NEW_COMPONENTS_SUMMARY.md`
- **Troubleshooting**: Check logs and describe resources
- **Gateway API Docs**: https://gateway-api.sigs.k8s.io/
- **cert-manager Docs**: https://cert-manager.io/docs/

## 📝 Notes

Add your deployment-specific notes here:

```
Deployment Date: _______________
Domain Used: _______________
Issuer Used: _______________
Gateway IP: _______________
Special Configuration: _______________

Issues Encountered:
- 
- 

Solutions Applied:
- 
- 
```
