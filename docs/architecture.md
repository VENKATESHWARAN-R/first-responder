# Architecture Overview

- **Frontend (Next.js App Router)**: UI pages for overview, namespace detail, workload/pod detail, settings, and admin user management.
- **Backend (FastAPI)**: Authentication, RBAC checks, namespace-scoped Kubernetes reads, diagnostics rules, and user/admin APIs.
- **Persistence**: SQLite via SQLModel for users and preferences.
- **Caching**: In-memory TTL cache wraps namespace listing and detail queries.
- **Cluster Access**: Kubernetes Python client uses in-cluster config first, then falls back to local kubeconfig.

## Data flow
1. User logs in via `/api/auth/login`; JWT stored in HttpOnly cookie.
2. Each API request resolves user from cookie and enforces namespace visibility.
3. Backend queries Kubernetes APIs with short timeout/retry and caches read results.
4. Frontend renders dashboard tables/cards with empty/loading/error states.
