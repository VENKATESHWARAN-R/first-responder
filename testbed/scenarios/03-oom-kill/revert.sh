#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/../_lib.sh"
require_cluster

info "rolling orders back to v1.3.0 (disabling the order cache)"
k patch deploy/orders --type=strategic -p '{
  "metadata": {"labels": {"app.kubernetes.io/version": "1.3.0"}},
  "spec": {"template": {
    "metadata": {"labels": {"app.kubernetes.io/version": "1.3.0"}},
    "spec": {"containers": [{
      "name": "orders",
      "env": [{"name": "ENABLE_ORDER_CACHE", "value": "false"}]
    }]}
  }}
}'
k annotate deploy/orders \
  kubernetes.io/change-cause="rollback orders to v1.3.0 (order cache leaks memory)" --overwrite
wait_rollout orders

info "reverted. Orders memory should hold steady; restart counts stop climbing."
