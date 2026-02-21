# Namespace Observatory

Read-only Kubernetes namespace monitoring SaaS. Provides login-based RBAC, namespace health dashboards, pod crash/restart diagnostics, and a dual-theme UI — all without any cluster management capabilities.

## Features

- **Authentication & RBAC** — App-managed users with JWT sessions. Admin assigns namespace access per user. All API requests enforce server-side filtering.
- **Namespace Overview** — Grid of namespaces with health indicators (Healthy/Degraded/Critical), deployment readiness, pod counts, restart counts, and warning events.
- **Namespace Detail** — Summary cards + tabbed views for Workloads, Pods, Events, and Config (ConfigMap/Secret names only).
- **Workload Detail** — Replica status, container images, rollout conditions, and associated pods.
- **Pod Diagnostics** — Container states, restart counts, events, and rule-based "Likely Cause" analysis (ImagePullBackOff, OOMKilled, CrashLoopBackOff, etc.).
- **Two Themes** — Minimal (clean, light) and Neo-Brutal (bold borders, thick shadows). Persisted per user.
- **Least-Privilege RBAC** — Helm chart creates a ServiceAccount with only get/list/watch permissions.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15 (App Router) + TypeScript |
| Backend | Python FastAPI |
| Auth | JWT in HttpOnly cookies |
| Storage | SQLite (users, audit log) |
| K8s Client | `kubernetes` Python library |
| Cache | In-memory TTL (configurable) |
| Deploy | Helm chart |

## Quick Start (Local)

```bash
# 1. Start the backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 2. Start the frontend (separate terminal)
cd frontend
npm install
npm run dev

# 3. Open http://localhost:3000
# Login: admin@namespace-observatory.local / admin
```

The backend reads your local `~/.kube/config` by default. Make sure you have a cluster context configured.

## Deploy to Kubernetes

```bash
# Build images
docker build -t namespace-observatory/backend:latest ./backend
docker build -t namespace-observatory/frontend:latest ./frontend

# Deploy with Helm
helm install nso ./helm/namespace-observatory \
  --set backend.env.NSO_SECRET_KEY="$(openssl rand -hex 32)" \
  --set backend.env.NSO_ADMIN_PASSWORD="your-secure-password"
```

## Tests

```bash
cd backend
python -m pytest tests/ -v
```

42 tests covering: diagnostics engine, RBAC filtering, TTL cache, and API contract tests (auth, admin, theme endpoints).

## Documentation

- [Quickstart Guide](docs/quickstart.md)
- [Architecture Overview](docs/architecture.md)
- [RBAC Model & Permissions](docs/rbac.md)
- [How to Add a Dashboard Card](docs/adding-dashboard-cards.md)

## Project Structure

```
backend/
  app/
    main.py              # FastAPI app entry point
    config.py            # Settings via env vars (NSO_ prefix)
    database.py          # SQLite setup + admin seed
    dependencies.py      # Auth guards
    routers/
      auth.py            # Login/logout/me/theme
      admin.py           # User CRUD
      kubernetes.py      # All K8s read endpoints
    services/
      auth.py            # JWT + password hashing + RBAC filter
      cache.py           # In-memory TTL cache
      k8s.py             # Kubernetes API client
      diagnostics.py     # Rule-based pod diagnostics
    models/
      schemas.py         # Pydantic request/response models
  tests/                 # pytest test suite
  Dockerfile

frontend/
  src/
    app/                 # Next.js App Router pages
      page.tsx           # Overview (namespace grid)
      namespace/[ns]/    # Namespace detail (tabs)
      workload/[kind]/[ns]/[name]/  # Workload detail
      pod/[ns]/[name]/   # Pod detail + diagnostics
      settings/          # Theme switcher
      admin/             # User management
      globals.css        # Theme tokens (CSS variables)
    components/          # Reusable components
    lib/                 # API client + hooks
  Dockerfile

helm/namespace-observatory/
  Chart.yaml
  values.yaml
  templates/             # K8s manifests (RBAC, Deployments, Services)
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NSO_SECRET_KEY` | `change-me-...` | JWT signing key |
| `NSO_ADMIN_EMAIL` | `admin@namespace-observatory.local` | Initial admin email |
| `NSO_ADMIN_PASSWORD` | `admin` | Initial admin password |
| `NSO_K8S_IN_CLUSTER` | `false` | Set `true` when running inside K8s |
| `NSO_CACHE_TTL_SECONDS` | `15` | Cache TTL for K8s API responses |
| `NSO_DB_PATH` | `data/users.db` | SQLite database file path |
| `NSO_CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins |

## Non-Goals (Phase 1)

- No editing/scaling/restarting workloads
- No viewing secret/configmap contents (names only)
- No multi-cluster support
- No alerting engine
- No OpenTelemetry integration
