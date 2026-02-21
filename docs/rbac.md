# RBAC Model & Permissions

## Two Layers of RBAC

Namespace Observatory has two independent RBAC systems:

1. **Application RBAC** — Controls which users can see which namespaces
2. **Kubernetes RBAC** — Controls what the app's ServiceAccount can read from the cluster

Both must allow access for data to be visible.

---

## Application RBAC

### User Roles

| Role | Capabilities |
|------|-------------|
| `admin` | View all assigned namespaces, manage users, assign namespace access |
| `viewer` | View only assigned namespaces |

### Namespace Access

Each user has an `allowed_namespaces` list stored in SQLite:

- `["*"]` — Access to all namespaces (typically for admins)
- `["default", "production", "staging"]` — Access to specific namespaces only
- `[]` — No access (UI shows "no namespaces available" state)

### Enforcement

RBAC is enforced **server-side** in every API endpoint. The filtering logic is in `backend/app/services/auth.py:filter_namespaces()`:

```python
def filter_namespaces(user_namespaces: list[str], available: list[str]) -> list[str]:
    if "*" in user_namespaces:
        return available
    return [ns for ns in available if ns in user_namespaces]
```

Every Kubernetes endpoint in `routers/kubernetes.py` calls `_check_ns_access()` which:

1. Lists all cluster namespaces
2. Intersects with the user's allowed namespaces
3. Returns 403 if the requested namespace is not in the intersection

### Admin User Management

Admins can manage users via `POST/GET/PATCH/DELETE /api/admin/users`:

- Create users with specific namespace access
- Update namespace assignments
- Change roles
- Reset passwords

The initial admin is seeded from environment variables (`NSO_ADMIN_EMAIL`, `NSO_ADMIN_PASSWORD`).

---

## Kubernetes RBAC

### ClusterRole

The Helm chart creates a ClusterRole with **read-only** permissions:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: <release>-readonly
rules:
  - apiGroups: [""]
    resources: ["namespaces"]
    verbs: ["get", "list", "watch"]

  - apiGroups: [""]
    resources: ["pods", "events", "configmaps", "secrets", "services"]
    verbs: ["get", "list", "watch"]

  - apiGroups: ["apps"]
    resources: ["deployments", "statefulsets", "daemonsets", "replicasets"]
    verbs: ["get", "list", "watch"]

  - apiGroups: ["batch"]
    resources: ["jobs", "cronjobs"]
    verbs: ["get", "list", "watch"]
```

### Why These Permissions

| Resource | Why Needed |
|----------|-----------|
| `namespaces` | List available namespaces for the overview page |
| `pods` | Show pod status, container states, restart counts |
| `events` | Display warning/normal events, used for diagnostics |
| `configmaps` | Show names only (contents never exposed) |
| `secrets` | Show names only (contents never exposed) |
| `deployments` | Show deployment status, replica counts, conditions |
| `statefulsets` | Show statefulset status and replicas |
| `daemonsets` | Show daemonset status |
| `replicasets` | Used internally for pod-to-deployment matching |
| `jobs`, `cronjobs` | Show job status and schedules |

### What's NOT Permitted

The ClusterRole explicitly excludes:

- `create`, `update`, `patch`, `delete` — No write operations
- `exec`, `attach`, `portforward` — No pod access
- `proxy` — No API proxying
- Secret/ConfigMap `data` — While get/list is granted (needed for names), the application code never reads or returns the `data` field

### ServiceAccount & Binding

```yaml
# ServiceAccount — identity for the app pod
apiVersion: v1
kind: ServiceAccount
metadata:
  name: namespace-observatory

# ClusterRoleBinding — connects ServiceAccount to ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: <release>-readonly
roleRef:
  kind: ClusterRole
  name: <release>-readonly
subjects:
  - kind: ServiceAccount
    name: namespace-observatory
    namespace: <release-namespace>
```

### Namespace-Scoped Alternative

For tighter security, you can replace the ClusterRole with per-namespace Roles and RoleBindings. This limits the app to only specific namespaces at the Kubernetes level (in addition to the application-level filtering):

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: nso-readonly
  namespace: production
rules:
  - apiGroups: ["", "apps", "batch"]
    resources: ["pods", "events", "deployments", ...]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: nso-readonly
  namespace: production
roleRef:
  kind: Role
  name: nso-readonly
subjects:
  - kind: ServiceAccount
    name: namespace-observatory
    namespace: default
```

Note: With namespace-scoped Roles, the app will need a ClusterRole for `namespaces` list access or you must pre-configure the namespace list.

---

## Audit Logging

All authentication events and namespace page accesses are logged to the `audit_log` SQLite table:

| Event | Detail |
|-------|--------|
| `login` | User email |
| `logout` | — |
| `view_namespaces` | Count of namespaces returned |
| `view_namespace` | Namespace name |
| `view_pod` | Namespace + pod name |
| `create_user` | Created user email |
| `update_user` | Updated user ID |
| `delete_user` | Deleted user ID |
