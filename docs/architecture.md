# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Browser                           │
│  Next.js Frontend (React, TypeScript)               │
│  Port 3000                                          │
└──────────────────┬──────────────────────────────────┘
                   │  /api/* (proxied via next.config.ts rewrite)
                   ▼
┌─────────────────────────────────────────────────────┐
│            FastAPI Backend (Python)                  │
│            Port 8000                                 │
│                                                     │
│  ┌──────────┐ ┌──────────┐ ┌────────────────────┐  │
│  │  Auth    │ │  Admin   │ │  Kubernetes Router  │  │
│  │  Router  │ │  Router  │ │                     │  │
│  └────┬─────┘ └────┬─────┘ └────────┬───────────┘  │
│       │             │                │               │
│  ┌────▼─────────────▼────────────────▼───────────┐  │
│  │              Services Layer                    │  │
│  │  auth.py  │  k8s.py  │  cache.py  │ diag.py   │  │
│  └────┬──────────┬───────────┬───────────────────┘  │
│       │          │           │                       │
│  ┌────▼────┐ ┌───▼──────┐ ┌─▼──────────┐           │
│  │ SQLite  │ │ K8s API  │ │ TTL Cache  │           │
│  │ (users) │ │ Client   │ │ (in-mem)   │           │
│  └─────────┘ └──────────┘ └────────────┘           │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  Kubernetes API  │
              │  (read-only)     │
              └──────────────────┘
```

## Module Breakdown

### Backend (`backend/app/`)

| Module | File | Purpose |
|--------|------|---------|
| **Entry Point** | `main.py` | FastAPI app, CORS, lifespan (init DB + K8s client) |
| **Config** | `config.py` | Pydantic Settings from env vars (NSO_ prefix) |
| **Database** | `database.py` | SQLite schema, connection manager, admin seed |
| **Dependencies** | `dependencies.py` | `get_current_user` and `require_admin` guards |
| **Auth Router** | `routers/auth.py` | Login, logout, /me, theme update |
| **Admin Router** | `routers/admin.py` | User CRUD (create, list, update, delete) |
| **K8s Router** | `routers/kubernetes.py` | All read-only K8s endpoints with RBAC filtering |
| **Auth Service** | `services/auth.py` | Password hashing, JWT encode/decode, user queries, namespace filter |
| **K8s Service** | `services/k8s.py` | Kubernetes API calls, data extraction, caching |
| **Cache** | `services/cache.py` | In-memory TTL cache (per-key expiry) |
| **Diagnostics** | `services/diagnostics.py` | Rule-based pod issue detection |
| **Schemas** | `models/schemas.py` | Pydantic request/response models |

### Frontend (`frontend/src/`)

| Module | Path | Purpose |
|--------|------|---------|
| **Layout** | `app/layout.tsx` | Root layout, HTML shell, theme attribute |
| **App Shell** | `app/AppShell.tsx` | Auth check, theme application, login gate |
| **Login** | `app/LoginPage.tsx` | Login form (rendered when unauthenticated) |
| **Overview** | `app/page.tsx` | Namespace grid with search/filter |
| **NS Detail** | `app/namespace/[ns]/page.tsx` | Summary cards + tabs (workloads/pods/events/config) |
| **Workload** | `app/workload/[kind]/[ns]/[name]/page.tsx` | Replica info, images, conditions, pod list |
| **Pod** | `app/pod/[ns]/[name]/page.tsx` | Container states, events, diagnostics |
| **Settings** | `app/settings/page.tsx` | Theme switcher, profile info |
| **Admin** | `app/admin/page.tsx` | User management (create, edit, delete) |
| **API Client** | `lib/api.ts` | Typed fetch wrappers for all endpoints |
| **Hooks** | `lib/hooks.ts` | `useFetch` (data/loading/error) and `useUser` |
| **Components** | `components/` | Header, HealthBadge, SortableTable, StatusStates |
| **Themes** | `app/globals.css` | CSS custom properties for Minimal + Neo-Brutal |

## Data Flow

### Authentication Flow

1. User submits email/password → `POST /api/auth/login`
2. Backend verifies credentials against SQLite
3. Backend creates JWT token → sets `session_token` HttpOnly cookie
4. All subsequent requests include the cookie automatically
5. `get_current_user` dependency decodes JWT, loads user from DB
6. Namespace-scoped endpoints call `filter_namespaces()` to enforce RBAC

### Kubernetes Data Flow

1. Frontend calls `/api/namespaces` (or any K8s endpoint)
2. Backend checks auth → extracts user's `allowed_namespaces`
3. Cache layer checked first (TTL: 15s default)
4. On cache miss: K8s Python client calls cluster API
5. Response is cached and returned
6. Frontend renders data with appropriate components

### Diagnostics Flow

1. Frontend requests `GET /api/pods/{ns}/{name}`
2. Backend fetches pod details + pod events from K8s API
3. `diagnose_pod()` runs all rules against container states and events
4. Each rule checks for specific `reason` strings (e.g., `OOMKilled`, `ImagePullBackOff`)
5. Matching rules produce findings with: severity, title, description, remediation, signal
6. Findings are deduplicated by rule ID and returned with the pod detail

## Caching Strategy

The backend uses an in-memory TTL cache (`services/cache.py`) to reduce Kubernetes API load:

- **Default TTL**: 15 seconds (configurable via `NSO_CACHE_TTL_SECONDS`)
- **Cache keys**: Namespaced by resource type (e.g., `ns:pods:default`, `workload:Deployment:default:nginx`)
- **Invalidation**: Can invalidate by prefix (e.g., `ns:` clears all namespace caches)
- **No persistence**: Cache is lost on restart (acceptable for short TTL)

## Security Model

- **No cluster writes**: The app only uses get/list/watch verbs
- **Secret/ConfigMap contents**: Never exposed — only names are returned
- **JWT tokens**: Stored in HttpOnly cookies (not accessible to JavaScript)
- **Password hashing**: SHA-256 with per-user random salt
- **RBAC**: Enforced server-side on every request (not just UI filtering)
- **Kubernetes RBAC**: ServiceAccount has minimal ClusterRole permissions
