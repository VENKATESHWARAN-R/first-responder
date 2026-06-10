#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/../_lib.sh"
require_cluster

info "enabling the 'price rules engine' on catalog (+~900ms per request, no errors)"
k set env deploy/catalog EXTRA_LATENCY_MS=900
k annotate deploy/catalog \
  kubernetes.io/change-cause="enable price rules engine on catalog" --overwrite
wait_rollout catalog

info "injected. Browse latency is now ~20x baseline with zero errors."
info "watch:  kubectl --context $KCTX -n $NS logs deploy/loadgen -f   (expect 200s taking ~1s)"
info "        time curl -s http://localhost:8080/api/products >/dev/null"
