# 05-latency-regression — catalog gains ~900 ms per request

## The story

A config change enables a "price rules engine" on catalog. Every catalog request now
takes ~900 ms longer. Nothing errors: every request succeeds, every pod is green,
probes pass (health endpoints are exempt from the slowdown — realistic, since probe
paths rarely exercise the slow code path). The only symptom is that browsing the
shop went from ~50 ms to ~1 s.

This is the hardest of the five scenarios for an investigator, and deliberately so:
there are **no errors to grep for**. Latency regressions only show up if the
investigation actually *measures* — timing requests against each service to isolate
which hop added the delay.

## What inject.sh does

`kubectl set env deploy/catalog EXTRA_LATENCY_MS=900` with change-cause
"enable price rules engine on catalog".

## What an investigator should find

- `loadgen` logs: `GET /api/products -> 200 in 0.9xx s` (previously `0.0xx s`) —
  status codes unchanged, timing ~20x worse. Checkout latency unaffected.
- Timing requests per hop isolates the regression to catalog: gateway adds
  milliseconds; catalog answers in ~900 ms+ on its own.
- All pods Running/Ready, no restarts, no error logs, CPU/memory flat — every
  "look for what's broken" heuristic comes back clean.
- Rollout history of catalog: "enable price rules engine on catalog" at exactly
  the moment loadgen response times jumped.
- `http_request_duration_seconds` on catalog's `/metrics` corroborates, for an
  investigator that reads Prometheus histograms directly.

A correct diagnosis localizes the latency to catalog and ties it to the config
change. Wrong-but-tempting answers: "redis is slow" (it isn't), "the gateway is
slow" (it's just summing its upstream).

## Revert

Removes the `EXTRA_LATENCY_MS` override; browse latency returns to baseline.
