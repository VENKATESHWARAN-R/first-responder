# Namespace Observatory (Phase 1 MVP)

Read-only Kubernetes namespace monitoring SaaS with app-managed auth, namespace RBAC filtering, diagnostics, and themeable UI.

## Features
- FastAPI backend with JWT HttpOnly cookie auth.
- Admin user seeding (`ADMIN_EMAIL` / `ADMIN_PASSWORD`) and user management APIs.
- Strict server-side namespace RBAC enforcement on all namespace-scoped endpoints.
- Kubernetes read-only observability: namespaces, workloads, pods, events, configmaps/secrets names.
- Pod diagnostics with rule-based likely cause (`CrashLoopBackOff`, `OOMKilled`, `ImagePullBackOff`, etc.).
- Next.js frontend pages for overview, namespace detail, workload detail, pod detail, settings, and admin.
- Two global themes via design tokens: **Minimal** and **Neo-brutal**.
- Helm chart with least-privilege service account + RBAC.

## Repo Layout
- `backend/` FastAPI API + RBAC/auth/k8s service + tests.
- `frontend/` Next.js app router UI.
- `charts/namespace-observatory/` Kubernetes Helm chart.
- `docs/` quickstart, architecture, RBAC, and extension guide.

## Docs
- [Quickstart](docs/quickstart.md)
- [Architecture](docs/architecture.md)
- [RBAC](docs/rbac.md)
- [Add a dashboard card](docs/add-dashboard-card.md)
