#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/../_lib.sh"
require_cluster

info "deploying orders v1.4.0 (migrates to a payments-v2 endpoint that does not exist)"
k patch deploy/orders --type=strategic -p '{
  "metadata": {"labels": {"app.kubernetes.io/version": "1.4.0"}},
  "spec": {"template": {
    "metadata": {"labels": {"app.kubernetes.io/version": "1.4.0"}},
    "spec": {"containers": [{
      "name": "orders",
      "env": [{"name": "PAYMENTS_URL", "value": "http://payments-v2.shop.svc.cluster.local:8000"}]
    }]}
  }}
}'
k annotate deploy/orders \
  kubernetes.io/change-cause="release orders v1.4.0: migrate to payments-v2 endpoint" --overwrite
wait_rollout orders

info "injected. The rollout is green, but every checkout now fails."
info "watch:  kubectl --context $KCTX -n $NS logs deploy/loadgen -f   (expect 502 on POST /api/checkout)"
info "        kubectl --context $KCTX -n $NS logs deploy/orders --tail=20"
