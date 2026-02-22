# Quickstart Guide

This guide covers how to run Namespace Observatory locally for development and how to deploy it to a Kubernetes cluster using Helm.

## Prerequisites

- Python 3.12+
- Node.js 22+
- A Kubernetes cluster (or [Kind](https://kind.sigs.k8s.io/) for local testing)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Helm 3](https://helm.sh/docs/intro/install/) (for Kubernetes deployment)

---

## Local Development

### 1. Start the Backend

The backend is a Python FastAPI application located at `backend/`.

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

Configure the backend using environment variables (all prefixed with `NSO_`):

| Variable | Default | Description |
|---|---|---|
| `NSO_SECRET_KEY` | `change-me-in-production-use-openssl-rand-hex-32` | JWT signing key |
| `NSO_ADMIN_EMAIL` | `admin@namespace-observatory.local` | Seeded admin email |
| `NSO_ADMIN_PASSWORD` | `admin` | Seeded admin password |
| `NSO_K8S_IN_CLUSTER` | `false` | Set `true` when running inside K8s |
| `NSO_K8S_KUBECONFIG` | *(not set -- uses default)* | Path to kubeconfig file |
| `NSO_CACHE_TTL_SECONDS` | `15` | Cache TTL for K8s API responses |
| `NSO_DB_PATH` | `data/users.db` | SQLite database file path |
| `NSO_CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins (JSON array) |
| `NSO_JWT_EXPIRE_MINUTES` | `480` | JWT token expiry (default 8 hours) |

Start the server on port 8000:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

On first startup, the backend will:
1. Initialize the SQLite database at `data/users.db`
2. Seed an admin user with the configured `NSO_ADMIN_EMAIL` and `NSO_ADMIN_PASSWORD`
3. Initialize the Kubernetes client (using your local `~/.kube/config` by default)

Verify the backend is running:

```bash
curl http://localhost:8000/api/health
# {"status":"ok"}
```

### 2. Start the Frontend

The frontend is a Next.js 15 application located at `frontend/`.

```bash
cd frontend

# Install dependencies
npm install

# Start the development server on port 3000
npm run dev
```

The frontend proxies all `/api/*` requests to the backend. This is configured in `frontend/next.config.ts` via Next.js rewrites:

```typescript
// frontend/next.config.ts
async rewrites() {
  return [
    {
      source: "/api/:path*",
      destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/:path*`,
    },
  ];
}
```

To point at a different backend URL, set the `NEXT_PUBLIC_API_URL` environment variable:

```bash
NEXT_PUBLIC_API_URL=http://my-backend:8000 npm run dev
```

### 3. Access the Application

Open [http://localhost:3000](http://localhost:3000) in your browser. Log in with the admin credentials you configured (defaults: `admin@namespace-observatory.local` / `admin`).

If your kubeconfig points to a running cluster, you will see namespace cards on the Overview page immediately.

### 4. Run Tests

Backend tests use pytest with FastAPI's `TestClient`:

```bash
cd backend
python -m pytest tests/ -v
```

The test suite covers:
- **API contract tests** for auth, admin, and theme endpoints (`tests/test_api.py`)
- **Diagnostics engine** rule matching (`tests/test_diagnostics.py`)
- **TTL cache** behavior (`tests/test_cache.py`)
- **RBAC namespace filtering** logic (`tests/test_rbac_filter.py`)

Frontend linting:

```bash
cd frontend
npm run lint
```

---

## Kubernetes Deployment with Helm

### 1. Build Container Images

Build and tag the backend and frontend Docker images:

```bash
# Backend (Python 3.12-slim, exposes port 8000)
docker build -t namespace-observatory/backend:latest ./backend

# Frontend (Node 22-alpine, multi-stage build, exposes port 3000)
docker build -t namespace-observatory/frontend:latest ./frontend
```

If you are using a local Kind cluster, load the images into the cluster:

```bash
kind load docker-image namespace-observatory/backend:latest --name otel-testing
kind load docker-image namespace-observatory/frontend:latest --name otel-testing
```

### 2. Create a Kind Cluster (Optional)

If you do not already have a cluster, create one using the included config:

```bash
kind create cluster --config kind-config.yaml --name otel-testing
```

This creates a 3-node cluster (1 control-plane + 2 workers) as defined in `kind-config.yaml`.

### 3. Install with Helm

```bash
helm install nso ./helm/namespace-observatory \
  --set backend.env.NSO_SECRET_KEY="$(openssl rand -hex 32)" \
  --set backend.env.NSO_ADMIN_EMAIL="admin@example.com" \
  --set backend.env.NSO_ADMIN_PASSWORD="strong-password-here"
```

The Helm chart creates the following resources:
- **ServiceAccount** (`namespace-observatory`) for the backend pod
- **ClusterRole** (`nso-readonly`) with read-only permissions (get/list/watch only)
- **ClusterRoleBinding** linking the ServiceAccount to the ClusterRole
- **Deployment** for the backend (FastAPI on port 8000, with liveness and readiness probes at `/api/health`)
- **Deployment** for the frontend (Next.js on port 3000, with readiness probe at `/`)
- **Service** for each deployment (ClusterIP by default; backend on port 8000, frontend on port 80)
- **Ingress** (disabled by default, enable with `ingress.enabled=true`)

The backend deployment automatically sets `NSO_K8S_IN_CLUSTER=true` and uses the ServiceAccount token for Kubernetes API access.

### 4. Customize Values

Override defaults in `helm/namespace-observatory/values.yaml` or pass `--set` flags:

```bash
helm install nso ./helm/namespace-observatory \
  --set replicaCount=2 \
  --set backend.env.NSO_CACHE_TTL_SECONDS="30" \
  --set ingress.enabled=true \
  --set ingress.className="nginx" \
  --set ingress.hosts[0].host="nso.example.com" \
  --set ingress.hosts[0].paths[0].path="/" \
  --set ingress.hosts[0].paths[0].pathType="Prefix"
```

Or create a custom values file:

```yaml
# my-values.yaml
replicaCount: 2

backend:
  image:
    repository: my-registry/nso-backend
    tag: v0.1.0
  env:
    NSO_SECRET_KEY: "your-production-secret"
    NSO_ADMIN_EMAIL: "admin@company.com"
    NSO_ADMIN_PASSWORD: "secure-password"
    NSO_CACHE_TTL_SECONDS: "30"
    NSO_CORS_ORIGINS: '["https://nso.company.com"]'

frontend:
  image:
    repository: my-registry/nso-frontend
    tag: v0.1.0
  env:
    NEXT_PUBLIC_API_URL: "http://nso-backend:8000"

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: nso.company.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: nso-tls
      hosts:
        - nso.company.com

resources:
  backend:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 256Mi
  frontend:
    requests:
      cpu: 50m
      memory: 64Mi
    limits:
      cpu: 200m
      memory: 128Mi
```

```bash
helm install nso ./helm/namespace-observatory -f my-values.yaml
```

### 5. Verify the Deployment

```bash
# Check pods are running
kubectl get pods -l app.kubernetes.io/name=namespace-observatory

# Check services
kubectl get svc | grep nso

# Port-forward to access locally
kubectl port-forward svc/nso-frontend 3000:80
```

Open [http://localhost:3000](http://localhost:3000) and log in.

### 6. Upgrade and Uninstall

```bash
# Upgrade with new values
helm upgrade nso ./helm/namespace-observatory -f my-values.yaml

# Uninstall (removes all created resources)
helm uninstall nso
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "Cluster API unreachable" on the Overview page | Backend cannot reach the K8s API | Check kubeconfig (local) or `NSO_K8S_IN_CLUSTER` (deployed). Ensure the ServiceAccount has the ClusterRoleBinding. |
| 401 on login | Wrong credentials | Verify `NSO_ADMIN_EMAIL` / `NSO_ADMIN_PASSWORD` env vars match what you are entering. The admin user is seeded only on first database initialization. |
| Frontend shows a blank page | Backend not reachable from the frontend proxy | Ensure backend is running on port 8000 and `NEXT_PUBLIC_API_URL` is correct. |
| Pods show `ImagePullBackOff` after Helm install | Images not in cluster registry | Use `kind load docker-image` for Kind, or push to your container registry. |
| Stale data on the dashboard | Cache has not expired | Lower `NSO_CACHE_TTL_SECONDS` or wait for the TTL to expire (default 15s). Click the Refresh button on any page to trigger a new fetch. |
| "Could not initialize Kubernetes client" in backend logs | No valid kubeconfig available | Locally: ensure `~/.kube/config` exists with a valid context. In-cluster: check that the ServiceAccount and ClusterRoleBinding were created by Helm. |
| Database already has an admin with different credentials | `init_db()` only seeds if no user with that email exists | Delete `data/users.db` to re-seed, or use the Admin page to update the user. |
