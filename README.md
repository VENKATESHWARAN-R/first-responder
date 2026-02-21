# Namespace Observatory

Phase 1 (MVP) — “Namespace Observatory” (Read-only Kubernetes Monitoring SaaS)

A production-quality MVP web application that monitors Kubernetes namespaces by reading from the Kubernetes API. It provides a read-only view of workloads, pods, events, and health status, secured by RBAC and app-managed authentication.

## Features

- **Read-only Observability**: Monitor Namespaces, Workloads (Deployments, StatefulSets, DaemonSets), Pods, and Events.
- **Diagnostics**: Rule-based "Likely cause" analysis for failed pods (e.g., ImagePullBackOff, OOMKilled).
- **Security**: App-managed login with JWT in HttpOnly cookies. RBAC-based namespace visibility (Admin vs Viewer).
- **Themes**: Switch between "Minimal" and "Neo-brutal" themes.
- **Zero-Touch**: No cluster management actions (create/update/delete) allowed.

## Tech Stack

- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS.
- **Backend**: Python FastAPI, Kubernetes Python Client.
- **Deployment**: Kubernetes Manifests (Deployment, Service, RBAC).

## Quickstart

### Prerequisites

- Docker
- Kubernetes cluster (local `kind` or remote)
- `kubectl` configured

### 1. Build Docker Images

From the repository root:

```bash
# Build Backend
docker build -f backend/Dockerfile -t namespace-observatory-backend:latest .

# Build Frontend
docker build -f frontend/Dockerfile -t namespace-observatory-frontend:latest .
```

### 2. Load Images into Kind (if using Kind)

```bash
kind load docker-image namespace-observatory-backend:latest --name otel-testing
kind load docker-image namespace-observatory-frontend:latest --name otel-testing
```

*(Replace `otel-testing` with your cluster name)*

### 3. Deploy to Kubernetes

```bash
# Apply RBAC (ServiceAccount, ClusterRole, Binding)
kubectl apply -f deploy/k8s/rbac.yaml

# Apply Deployments and Services
kubectl apply -f deploy/k8s/deployment.yaml
kubectl apply -f deploy/k8s/service.yaml
```

### 4. Access the Application

The frontend service is exposed as a NodePort on port `30000`.

If running locally with Kind/Minikube, you might need to port-forward:

```bash
kubectl port-forward svc/frontend-service 3000:3000
```

Open [http://localhost:3000](http://localhost:3000).

**Default Admin Credentials:**
- Email: `admin@example.com`
- Password: `admin123`

## Architecture Overview

1.  **Frontend (Next.js)**:
    -   Serves the UI and proxies API requests to the backend via Next.js Rewrites.
    -   Handles theme switching and responsive layout.
2.  **Backend (FastAPI)**:
    -   Exposes REST API endpoints.
    -   Authenticates users and issues JWTs.
    -   Interacts with Kubernetes API using the in-cluster ServiceAccount token.
    -   Implements caching and diagnostics logic.

## RBAC Model & Security

The application runs with a dedicated ServiceAccount `namespace-observatory-sa`. This ServiceAccount is bound to a `ClusterRole` named `namespace-observatory-viewer` which grants **read-only** permissions (`get`, `list`, `watch`) to specific resources:

-   Core: `namespaces`, `pods`, `services`, `events`, `configmaps`, `secrets`
-   Apps: `deployments`, `statefulsets`, `daemonsets`, `replicasets`
-   Batch: `jobs`, `cronjobs`

**Least Privilege:** The application cannot modify any resources. It cannot read the *content* of Secrets (only metadata), although the current RBAC allows `list` secrets which includes data in the API response. In a stricter environment, we would use a custom API aggregation or filter at the proxy level, but for this MVP, the backend code filters data and does not expose secret values to the frontend.

## Local Development

### Backend

```bash
cd backend
pip install -r requirements.txt
python -m backend.app.main:app --reload
# Runs on http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:3000
```

## How to add a new dashboard card

1.  Create a new UI component in `frontend/src/components/ui/` if needed.
2.  Navigate to `frontend/src/app/namespaces/[ns]/page.tsx` (for Namespace Detail) or `frontend/src/app/page.tsx` (for Overview).
3.  Fetch the required data using `apiFetch` in the `useEffect` hook.
4.  Add a new `<Card>` component to the grid layout.

Example:

```tsx
<Card>
  <CardHeader><CardTitle>My New Metric</CardTitle></CardHeader>
  <CardContent>{metricValue}</CardContent>
</Card>
```
