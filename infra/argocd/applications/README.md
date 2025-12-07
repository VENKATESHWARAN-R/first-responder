# Your Applications Directory

This directory is for **your application deployments**, separate from cluster infrastructure.

## Purpose

Keep your applications separate from cluster add-ons to:
- ✅ Make changes to your apps without affecting cluster infrastructure
- ✅ Maintain clear separation of concerns
- ✅ Different lifecycle management for apps vs infrastructure

## How to Use

### Quick Start: Add a Single Application

Create an ArgoCD Application manifest directly:

```bash
cat > my-app.yaml <<EOF
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
    path: apps/my-web-app  # Your app manifests
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

# Apply it
kubectl apply -f my-app.yaml
```

### Recommended: App of Apps Pattern

1. **Create App of Apps root** (one time):

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

2. **Add application manifests here**:

```bash
cat > my-app.yaml <<EOF
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

3. **Create your app directory structure**:

```bash
mkdir -p ../../../../apps/my-web-app
# Add your Kubernetes manifests or Helm chart in apps/my-web-app/
```

4. **Commit and push**:

```bash
git add infra/argocd/applications/ apps/
git commit -m "Add my web application"
git push
```

## Directory Structure

```
applications/
├── my-web-app.yaml         # ArgoCD Application for web app
├── my-api.yaml             # ArgoCD Application for API
└── my-database.yaml        # ArgoCD Application for database
```

Each application points to its manifests in the `apps/` directory at the repo root.

## Example Application Manifest

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-web-app
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  
  # Single source (plain manifests)
  source:
    repoURL: https://github.com/VENKATESHWARAN-R/first-responder.git
    targetRevision: master
    path: apps/my-web-app
  
  # OR: Multiple sources (Helm + values from Git)
  sources:
    - repoURL: https://charts.bitnami.com/bitnami
      chart: nginx
      targetRevision: 15.0.0
      helm:
        releaseName: my-nginx
        valueFiles:
          - $values/apps/my-web-app/values.yaml
    - repoURL: https://github.com/VENKATESHWARAN-R/first-responder.git
      targetRevision: master
      ref: values
  
  destination:
    server: https://kubernetes.default.svc
    namespace: my-web-app
  
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

## Best Practices

1. **One file per application** - Easy to manage
2. **Descriptive names** - `my-web-app.yaml`, `my-api.yaml`
3. **Consistent namespace naming** - Use app name as namespace
4. **Automated sync** - Let ArgoCD handle deployments
5. **CreateNamespace=true** - Auto-create target namespaces

## Differences from Cluster Add-ons

| Aspect | Cluster Add-ons | Applications |
|--------|----------------|--------------|
| **Location** | `cluster-addons/` | `applications/` |
| **Purpose** | Infrastructure | Workloads |
| **Examples** | cert-manager, monitoring | Your apps, APIs |
| **Update frequency** | Infrequent | Frequent |
| **Blast radius** | Affects cluster | Isolated |

## Next Steps

1. Create your first application manifest in this directory
2. Create corresponding app manifests in `apps/` at repo root
3. Commit and push
4. Check ArgoCD UI or `make apps` to see your application

## Need Help?

See the main [README.md](../../README.md) for more examples and troubleshooting.
