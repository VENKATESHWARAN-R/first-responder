# 03-oom-kill — orders v1.3.1 enables an unbounded in-memory cache

## The story

The orders team ships v1.3.1, enabling an in-memory order cache "for faster
lookups". The cache stores every confirmed order *including its rendered ~8 MB
invoice blob* and never evicts anything. Under normal checkout traffic, each pod's
memory climbs until it hits the container's 192 Mi limit and the kernel OOM-kills
it. The pod restarts with empty memory, works fine for a couple of minutes, and
the cycle repeats.

This is a memory leak as it actually presents in production: not a crash at
startup, but a *sawtooth* — periodic OOMKills, restart counts climbing, short
bursts of failed requests at each kill, otherwise healthy-looking service.

## What inject.sh does

Patches `deployment/orders`: sets `ENABLE_ORDER_CACHE=true`, bumps the version
label to `1.3.1`, records change-cause "release orders v1.3.1: enable in-memory
order cache for faster lookups". The leak itself is real application code — see
`_order_cache` in `apps/services/orders/main.py`.

## What an investigator should find

- `kubectl get pods -n shop`: orders pods with `OOMKilled` in last state
  (`kubectl describe pod` → `Last State: Terminated, Reason: OOMKilled`),
  restart counts climbing every few minutes.
- `kubectl top pods -n shop` (needs metrics-server): orders memory ratcheting
  up toward 192 Mi between restarts — catching the sawtooth mid-climb.
- Events: liveness/readiness blips and restarts on orders pods.
- `loadgen` logs: intermittent 502 bursts on `POST /api/checkout` coinciding with
  each kill; browse traffic unaffected.
- Rollout history: "release orders v1.3.1: enable in-memory order cache" shortly
  before the first OOMKill.
- The app code in this repo: the cache write in `orders/main.py` stores an 8 MB
  blob per order with no eviction — a future Codebase Agent can find the bug itself.

The trap: a restart "fixes" it for a few minutes, which tempts a *restart the pods*
mitigation. The correct call is rolling back the v1.3.1 change — restarts just
reset the sawtooth.

## Timing

With loadgen's ~1 checkout per 3s spread across 2 replicas, each pod leaks roughly
8 MB every 6 seconds → first OOMKill typically within **2–3 minutes** of injection.
Give it at least that long before investigating.

## Revert

Sets `ENABLE_ORDER_CACHE=false`, restores the 1.3.0 version label, records a
rollback change-cause.
