# 01-bad-deploy — orders v1.4.0 ships a broken payments endpoint

## The story

The orders team releases v1.4.0, which migrates to a new `payments-v2` endpoint as
part of a planned payments split. The new service name doesn't resolve — `payments-v2`
was never deployed. Pods roll out green (the bug only triggers on checkout requests,
which probes don't exercise), so the deploy *looks* successful while every checkout
fails.

This is the classic bad deploy: healthy-looking rollout, broken behavior, and the
fix is a rollback — not a restart, not scaling.

## What inject.sh does

Patches `deployment/orders`: sets `PAYMENTS_URL` to
`http://payments-v2.shop.svc.cluster.local:8000` (nonexistent service), bumps the
version label to `1.4.0`, and records a plausible `change-cause`. This creates a
normal rollout — new ReplicaSet, fresh pods, an entry in `kubectl rollout history`.

## What an investigator should find

- `loadgen` logs: `POST /api/checkout -> 502` starting immediately after injection;
  browse traffic still 200.
- `orders` logs: `ERROR payments unreachable at http://payments-v2...` with
  `ConnectError` — the bad hostname is right there in the log line.
- `kubectl rollout history deploy/orders -n shop`: a fresh revision,
  change-cause "release orders v1.4.0: migrate to payments-v2 endpoint",
  minutes before symptoms began.
- `payments` itself: healthy, ready, receiving **no** traffic — exonerating it.
- Pods all Running/Ready — nothing wrong at the infrastructure level.

The tell connecting symptom to cause is *temporal*: errors start at the same moment
as the rollout, and the erroring hostname matches the deploy's change.

## Revert

`revert.sh` patches `PAYMENTS_URL` and the version label back to the manifest
values and records a rollback change-cause — equivalent to `kubectl rollout undo`,
but deterministic regardless of revision history.
