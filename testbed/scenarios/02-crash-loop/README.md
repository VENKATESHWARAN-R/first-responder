# 02-crash-loop — catalog reconfigured to an unreachable Redis

## The story

As part of an "infra migration", someone points the catalog at a new shared Redis —
`redis-primary.infra.svc.cluster.local` — which doesn't exist (the migration was
never completed in this cluster). Catalog fails fast at startup when it can't reach
its datastore, so new pods retry the connection for ~10 seconds, exit, and enter
**CrashLoopBackOff**.

The wrinkle that makes this realistic: the deployment's rolling update gets stuck.
New pods never become Ready, so depending on timing one or both old healthy pods may
linger — the symptom can be *intermittent* browse failures rather than a full outage,
which is a more honest test of an investigator than a clean binary failure.

## What inject.sh does

`kubectl set env deploy/catalog REDIS_URL=redis://redis-primary.infra.svc.cluster.local:6379/0`
plus a change-cause annotation telling the migration story. The rollout starts and
never completes.

## What an investigator should find

- `kubectl get pods -n shop`: catalog pods in `CrashLoopBackOff` / `0/1 Ready`,
  restart count climbing; rollout stuck (`kubectl rollout status` hangs).
- `catalog` logs (current or previous container):
  `WARNING cannot reach redis at redis://redis-primary.infra... (attempt 1/5)` …
  then `CRITICAL giving up after 5 attempts` — the bad hostname is in the logs.
- Events: `Back-off restarting failed container`, readiness probe failures.
- `redis` (the real one) is Running and Ready — the datastore is fine; the *config*
  pointing at it is wrong.
- `kubectl rollout history deploy/catalog`: fresh revision with change-cause
  "config change: point catalog at shared redis (infra migration)".

A correct diagnosis names the config change as the cause, not "catalog is crashing"
(symptom) and not "redis is down" (false — and the trap a sloppy investigation
falls into).

## Revert

Sets `REDIS_URL` back to the in-namespace Redis from the manifests and waits for
the rollout to complete.
