#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/../_lib.sh"
require_cluster

info "deploying orders v1.3.1 (enables the unbounded in-memory order cache)"
k patch deploy/orders --type=strategic -p '{
  "metadata": {"labels": {"app.kubernetes.io/version": "1.3.1"}},
  "spec": {"template": {
    "metadata": {"labels": {"app.kubernetes.io/version": "1.3.1"}},
    "spec": {"containers": [{
      "name": "orders",
      "env": [{"name": "ENABLE_ORDER_CACHE", "value": "true"}]
    }]}
  }}
}'
k annotate deploy/orders \
  kubernetes.io/change-cause="release orders v1.3.1: enable in-memory order cache for faster lookups" --overwrite
wait_rollout orders

info "injected. Memory now leaks ~8MB per checkout; expect the first OOMKill in ~2-3 minutes."
info "watch:  kubectl --context $KCTX -n $NS get pods -w"
info "        kubectl --context $KCTX -n $NS top pods"
