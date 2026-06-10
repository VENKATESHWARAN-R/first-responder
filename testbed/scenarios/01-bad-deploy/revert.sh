#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/../_lib.sh"
require_cluster

info "rolling orders back to v1.3.0 (restoring the real payments endpoint)"
k patch deploy/orders --type=strategic -p '{
  "metadata": {"labels": {"app.kubernetes.io/version": "1.3.0"}},
  "spec": {"template": {
    "metadata": {"labels": {"app.kubernetes.io/version": "1.3.0"}},
    "spec": {"containers": [{
      "name": "orders",
      "env": [{"name": "PAYMENTS_URL", "value": "http://payments.shop.svc.cluster.local:8000"}]
    }]}
  }}
}'
k annotate deploy/orders \
  kubernetes.io/change-cause="rollback orders to v1.3.0" --overwrite
wait_rollout orders

info "reverted. Checkouts should be succeeding again."
