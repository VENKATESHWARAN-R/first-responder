# apps/ — the "shop" demo stack

## What this is

A small but realistic e-commerce microservice stack — the *victim system* that fault
scenarios break and the investigation agent diagnoses. Four Python/FastAPI services,
a Redis datastore, and an in-cluster load generator, all in the `shop` namespace.

```
                       ┌───────────┐
   loadgen ──HTTP────▶ │  gateway  │ ◀── host: http://localhost:8080
   (constant traffic)  └─────┬─────┘     (NodePort 30080)
                 browse      │      checkout
              ┌──────────────┴──────────────┐
              ▼                             ▼
        ┌──────────┐                  ┌──────────┐
        │ catalog  │                  │  orders  │
        └────┬─────┘                  └─┬──────┬─┘
             │ products                 │      │ charge
             ▼                 orders   │      ▼
        ┌─────────┐ ◀───────────────────┘ ┌──────────┐
        │  redis  │                       │ payments │
        └─────────┘                       └──────────┘
```

| Service | Role | Depends on | Notable behavior |
|---|---|---|---|
| `gateway` | Public API; routes browse → catalog, checkout → orders | catalog, orders | Propagates `X-Request-ID`; maps upstream 5xx → 502 |
| `catalog` | Product listing, backed by Redis | redis | **Fails fast at startup** if Redis is unreachable (→ CrashLoopBackOff on bad config) |
| `orders` | Creates orders, charges via payments, persists to Redis | payments, redis | Optional in-memory "order cache" (`ENABLE_ORDER_CACHE`) that grows without bound |
| `payments` | Simulated third-party payment processor | — | ~5% of charges decline with 402 (normal business noise) |
| `loadgen` | curl loop: browse + a checkout every ~3s | gateway | Exists so faults produce live symptoms in logs/metrics |
| `redis` | Shared datastore | — | Single replica, plain `redis:7-alpine` |

## Layout

```
services/<name>/    main.py, requirements.txt, Dockerfile   (one self-contained image per service)
manifests/          one YAML file per component (Deployment + Service), plus namespace.yaml
```

Each service duplicates its ~40 lines of logging/metrics boilerplate instead of
importing a shared package — deliberate, so every image builds from a single
directory with no build context tricks, and each service reads as one file.

## Conventions (what an investigator can rely on)

- **Structured logs:** every service writes JSON lines to stdout —
  `{"ts", "level", "service", "msg", "request_id", "status", "latency_ms", ...}`.
  Errors and 5xx responses log at `WARNING`/`ERROR`.
- **Request tracing:** `X-Request-ID` is generated at the gateway and propagated to
  every downstream call, so one user request can be followed across all service logs.
- **Prometheus metrics:** every service exposes `/metrics`
  (`http_requests_total{service,method,path,status}` and
  `http_request_duration_seconds`). No Prometheus server is installed yet — the
  endpoints exist so one can be pointed at them later without touching app code.
- **Probes:** `/healthz` (liveness) and `/readyz` (readiness; checks the service's
  own hard dependency, e.g. catalog → Redis ping).
- **Versioned deploys:** deployments carry `app.kubernetes.io/version` labels and
  `kubernetes.io/change-cause` annotations, so `kubectl rollout history` tells a
  story. Fault injections update both — like real bad deploys do.

## Fault knobs

Every service understands two environment variables, read at startup; scenarios flip
them via `kubectl set env` / `kubectl patch` (which triggers a normal rollout):

| Env var | Effect |
|---|---|
| `ERROR_RATE` | Fraction (0–1) of non-health requests answered with a 500 |
| `EXTRA_LATENCY_MS` | Milliseconds of artificial delay added to every request |

Service-specific knobs:

| Env var | Service | Effect |
|---|---|---|
| `ENABLE_ORDER_CACHE` | orders | Caches every order **plus an ~8 MB invoice blob** in process memory, unbounded — a deliberate memory-leak bug |
| `REDIS_URL` | catalog, orders | Catalog exits at startup if it can't connect (orders degrades gracefully) |
| `DECLINE_RATE` | payments | Fraction of charges declined with 402 (default 0.05 — normal noise, not a fault) |

These knobs are the *mechanism* of fault injection; the *stories* (what supposedly
happened, what's observable, what the correct diagnosis is) live in `../scenarios/`.

## Local development

```sh
# rebuild + redeploy all services after editing code (from testbed/):
make build

# run one service directly on the host (no cluster) for quick iteration:
cd services/catalog && pip install -r requirements.txt
REDIS_URL=redis://localhost:6379/0 uvicorn main:app --port 8000
```
