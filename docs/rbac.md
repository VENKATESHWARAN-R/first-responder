# RBAC Model

## Application RBAC
- Roles: `admin`, `viewer`.
- `admin` can manage users and access all namespaces.
- `viewer` can only access explicitly assigned namespaces.
- Namespace checks are enforced server-side for every namespace-scoped endpoint.

## Kubernetes RBAC (least privilege)
The chart installs a read-only ClusterRole with only `get/list/watch` for:
- core: namespaces, pods, events, configmaps, secrets
- apps: deployments, statefulsets, daemonsets
- batch: jobs, cronjobs

No mutation verbs (`create/update/patch/delete`) are granted.
