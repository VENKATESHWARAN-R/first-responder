# Application Deployment Guide

This directory contains the frontend and backend applications for the first-responder project.

## Architecture

- **Frontend**: Next.js application (in `frontend/my-app`)
- **Backend**: Python FastAPI application (in `backend`)

## Local Development

### Frontend
```bash
cd application/frontend/my-app
npm install
npm run dev
```

The frontend will run on `http://localhost:3000` and connect to the backend at `http://localhost:8000` by default.

### Backend
```bash
cd application/backend
# Install dependencies and run
python -m uvicorn main:app --reload --port 8000
```

The backend will run on `http://localhost:8000`.

## Kubernetes Deployment

### Backend URL Configuration

The frontend uses **runtime configuration** via ConfigMaps to connect to the backend. This means you can change the backend URL without rebuilding Docker images!

#### How It Works
1. Frontend fetches `/api/config` on page load
2. API route reads `BACKEND_URL` from environment variables (server-side)
3. Environment variable is populated from a ConfigMap
4. ConfigMap can be edited anytime → restart pods → new config!

**Key benefit**: Same Docker image works in all environments (local, staging, production)

#### Configuration Per Environment

- **Local Development** (npm run dev): Defaults to `http://localhost:8000`
- **Kind Cluster**: Configured via ConfigMap to `http://local-backend:8000`
- **Other environments**: Edit the ConfigMap overlay for that environment

For detailed information, see [RUNTIME_CONFIG.md](./RUNTIME_CONFIG.md)

### Building Images

To build and load the Docker images into your Kind cluster:

```bash
cd infra
make build-images
```

This script:
1. Builds the backend Docker image as `backend:test`
2. Builds the frontend Docker image as `frontend:test`
3. Loads both images into the Kind cluster

**Note**: Images are environment-agnostic. Backend URL is configured via ConfigMap at runtime.

### Deploying to Kubernetes

The applications are deployed using Kustomize and managed by ArgoCD:

```bash
# Deploy via ArgoCD (automatic if ArgoCD is watching the repo)
# Or manually apply:
kubectl apply -k application/frontend/my-app/k8s/overlays/local
kubectl apply -k application/backend/k8s/overlays/local
```

### Accessing the Applications

After deployment, you can access the applications via port-forwarding:

```bash
# Frontend
make port-forward-load-tester-frontend
# Access at http://localhost:3001

# Backend
make port-forward-load-tester-backend
# Access at http://localhost:8000
# API docs at http://localhost:8000/docs
```

## Troubleshooting

### Frontend can't connect to backend in Kubernetes

**Symptom**: Frontend shows errors like "TypeError: Load failed" when trying to reach the backend.

**Solution 1: Check ConfigMap**
```bash
kubectl get configmap local-frontend-config -n load-tester -o yaml
```
Ensure `BACKEND_URL` is set correctly (e.g., `http://local-backend:8000`)

**Solution 2: Restart pods**
After changing the ConfigMap:
```bash
kubectl rollout restart deployment/local-frontend -n load-tester
```

**Solution 3: Verify environment variable in pod**
```bash
kubectl exec -it <frontend-pod-name> -n load-tester -- env | grep BACKEND_URL
```

### Changing the Backend URL

Simply edit the ConfigMap:
```bash
kubectl edit configmap local-frontend-config -n load-tester
```

Change the `BACKEND_URL` value, save, then restart the pods:
```bash
kubectl rollout restart deployment/local-frontend -n load-tester
```

**No rebuild needed!** 🎉

### Verifying the backend URL

You can verify what backend URL the frontend is using by:

1. Port-forward to the frontend
2. Open the browser console
3. Check the "Backend URL" input field - it should show `http://backend:8000`

### Environment Variables

The frontend uses the `NEXT_PUBLIC_BACKEND_URL` environment variable:
- **Build time**: Set via Docker build arg (for Kubernetes deployment)
- **Runtime**: Can be overridden in the UI for testing

The backend uses:
- `PORT`: The port to listen on (default: 8000)

## Directory Structure

```
application/
├── backend/
│   ├── Dockerfile
│   ├── k8s/
│   │   ├── base/
│   │   │   ├── deployment.yaml
│   │   │   ├── service.yaml
│   │   │   └── kustomization.yaml
│   │   └── overlays/
│   │       └── local/
│   │           └── kustomization.yaml
│   └── [backend source code]
└── frontend/
    └── my-app/
        ├── Dockerfile
        ├── k8s/
        │   ├── base/
        │   │   ├── deployment.yaml
        │   │   ├── service.yaml
        │   │   ├── httproute.yaml
        │   │   └── kustomization.yaml
        │   └── overlays/
        │       └── local/
        │           └── kustomization.yaml
        └── [frontend source code]
```

## Next Steps

1. **Build images**: `make build-images`
2. **Deploy**: ArgoCD will automatically sync, or manually apply the kustomize configs
3. **Access**: Use `make port-forward-load-tester-frontend` and `make port-forward-load-tester-backend`
4. **Monitor**: Check ArgoCD UI for deployment status
