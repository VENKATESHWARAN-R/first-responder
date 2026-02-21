# How to Add a New Dashboard Card

This guide walks through adding a new summary card or data section to the Namespace Observatory dashboards.

## Overview

Dashboard cards follow a consistent pattern:

1. **Backend**: Add a data-fetching function in the K8s service
2. **Backend**: Expose it via an API endpoint (or extend an existing one)
3. **Frontend**: Create a component to display the data
4. **Frontend**: Add it to the appropriate page

## Example: Adding a "Top 5 Pods by Restart Count" Card

### Step 1: Backend — Add Data Logic

Edit `backend/app/services/k8s.py` to add a function that computes the data:

```python
def get_top_restart_pods(ns: str, limit: int = 5) -> list[dict[str, Any]]:
    """Return the top N pods by restart count in a namespace."""
    key = f"ns:top_restarts:{ns}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    pods = _list_pods(ns)
    sorted_pods = sorted(pods, key=lambda p: p.get("restart_count", 0), reverse=True)
    result = sorted_pods[:limit]
    cache.set(key, result)
    return result
```

The function:
- Uses the cache layer (cache key prefixed by namespace)
- Calls internal `_list_pods()` (which already handles K8s API errors)
- Returns a simple list of dicts

### Step 2: Backend — Add or Extend an API Endpoint

**Option A: Extend the existing namespace summary**

Edit `backend/app/services/k8s.py` `get_namespace_summary()` to include the new field:

```python
def get_namespace_summary(ns: str) -> dict[str, Any]:
    # ... existing code ...
    top_restart_pods = get_top_restart_pods(ns)

    summary = {
        # ... existing fields ...
        "top_restart_pods": top_restart_pods,
    }
```

**Option B: Create a new endpoint**

Edit `backend/app/routers/kubernetes.py`:

```python
@router.get("/namespaces/{ns}/top-restarts")
def get_top_restarts(
    ns: str,
    user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    _check_ns_access(user, ns)
    return get_top_restart_pods(ns)
```

### Step 3: Frontend — Add TypeScript Types

If you created a new endpoint, add the type and fetch function to `frontend/src/lib/api.ts`:

```typescript
export interface TopRestartPod {
  name: string;
  namespace: string;
  restart_count: number;
  phase: string;
}

export function getTopRestarts(ns: string) {
  return request<TopRestartPod[]>(`/api/namespaces/${ns}/top-restarts`);
}
```

### Step 4: Frontend — Create the Card Component

Create a card component or add it inline on the namespace detail page. The project uses plain CSS classes from `globals.css`:

```tsx
function TopRestartsCard({ ns }: { ns: string }) {
  const { data, loading, error } = useFetch(() => getTopRestarts(ns), [ns]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorBox message={error} />;
  if (!data || data.length === 0) {
    return (
      <div className="card">
        <div className="card-title">Top Restarts</div>
        <EmptyState title="No restarts" description="All pods are stable." />
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-title">Top 5 Pods by Restart Count</div>
      <SortableTable
        columns={[
          { key: "name", label: "Pod" },
          {
            key: "restart_count",
            label: "Restarts",
            sortValue: (p: TopRestartPod) => p.restart_count,
          },
          {
            key: "phase",
            label: "Phase",
            render: (p: TopRestartPod) => <HealthBadge status={p.phase} />,
          },
        ]}
        data={data as unknown as Record<string, unknown>[]}
      />
    </div>
  );
}
```

### Step 5: Frontend — Add to the Page

Edit `frontend/src/app/namespace/[ns]/page.tsx` and place the card:

```tsx
{/* After the stat-grid, before the tabs */}
<TopRestartsCard ns={ns} />
```

## Design Guidelines

### CSS Classes Available

| Class | Purpose |
|-------|---------|
| `card` | Container with border, shadow, padding |
| `card-title` | Bold section heading inside a card |
| `stat-card` | Compact card for single metric display |
| `stat-value` | Large monospace number |
| `stat-label` | Small uppercase label |
| `badge badge-healthy` | Green status badge |
| `badge badge-degraded` | Yellow/orange status badge |
| `badge badge-critical` | Red status badge |
| `error-box` | Error message container |
| `empty-state` | Centered placeholder for no-data states |

### Theme Compatibility

All styling uses CSS custom properties (defined in `globals.css`). As long as you use the existing CSS classes and variables, your card will automatically work with both themes:

- `var(--bg-card)` — Card background
- `var(--border-color)` — Border color
- `var(--text-primary)` — Primary text
- `var(--text-secondary)` — Secondary text
- `var(--accent)` — Accent/link color
- `var(--danger)` — Error/critical color
- `var(--warning)` — Warning color
- `var(--shadow)` — Card shadow

### State Handling

Every card should handle three states:

1. **Loading** — Show `<LoadingSpinner />`
2. **Error** — Show `<ErrorBox message={error} />`
3. **Empty** — Show `<EmptyState title="..." />`
4. **Data** — Render the actual content

### Caching

Backend functions should use the TTL cache:

```python
from app.services.cache import cache

def my_function(ns: str):
    key = f"ns:my_data:{ns}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    # ... fetch from K8s API ...
    cache.set(key, result)
    return result
```

## Adding a Diagnostic Rule

To add a new pod diagnostic rule, edit `backend/app/services/diagnostics.py` and add an entry to the `RULES` list:

```python
{
    "id": "my_new_rule",
    "match_reasons": ["SomeK8sReason"],
    "source": "container_state",  # or "event"
    "severity": "critical",       # or "warning"
    "title": "Human-Readable Title",
    "description": "What this means and why it happens.",
    "remediation": "1. Step one.\n2. Step two.\n3. Step three.",
},
```

The diagnostics engine will automatically pick it up — no other changes needed. Add a test case in `backend/tests/test_diagnostics.py` to verify.
