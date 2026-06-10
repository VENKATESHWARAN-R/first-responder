#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/../_lib.sh"
require_cluster

info "degrading payments' upstream processor (85% of charges will fail with 500)"
k set env deploy/payments ERROR_RATE=0.85
k annotate deploy/payments \
  kubernetes.io/change-cause="config sync" --overwrite
wait_rollout payments

info "injected. Most checkouts now fail; all pods stay green."
info "watch:  kubectl --context $KCTX -n $NS logs deploy/loadgen -f   (expect 502 on POST /api/checkout)"
info "        kubectl --context $KCTX -n $NS logs deploy/payments --tail=20"
