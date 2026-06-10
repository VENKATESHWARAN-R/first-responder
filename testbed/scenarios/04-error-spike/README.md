# 04-error-spike — payments' upstream processor degrades

## The story

The third-party payment processor behind the payments service starts timing out.
~85% of charge attempts fail with 500s. Nothing was deployed, nothing crashed, no
pod is unhealthy — every pod in the namespace is Running and Ready while the
checkout success rate collapses.

This scenario tests whether an investigation can localize a fault *by following the
error chain through service logs* rather than by spotting an unhealthy pod or a
recent deploy, and whether it correctly reports that the fault is **external** —
the right mitigation is *not* a rollback or restart.

## What inject.sh does

`kubectl set env deploy/payments ERROR_RATE=0.85`. The env change does create a
rollout (see `artifact_note` in the ground truth — a real upstream outage wouldn't),
with a deliberately mundane change-cause so the rollout trail isn't a giveaway.

## What an investigator should find

- `loadgen` logs: most `POST /api/checkout -> 502`, browse traffic 100% healthy.
- The error chain in logs, hop by hop, joined by shared `request_id`s:
  - gateway: `upstream orders returned 500` → 502
  - orders: `charge failed for order X: payments returned 500`
  - payments: `500` on `POST /charge`, message
    `"charge failed: upstream payment processor timed out"`
- All pods Running/Ready, zero restarts — infrastructure is exonerated.
- ~15% of checkouts still succeed — a partial failure, not an outage.

A correct diagnosis bottoms out at payments' upstream processor, citing the
payments log line. A sloppy one stops at "orders is failing" — one hop short.

## Revert

Removes the `ERROR_RATE` override; payments returns to its normal ~5% business
declines (402s), which are noise, not faults.
