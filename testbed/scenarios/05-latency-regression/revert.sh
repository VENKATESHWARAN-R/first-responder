#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/../_lib.sh"
require_cluster

info "disabling the 'price rules engine' on catalog"
k set env deploy/catalog EXTRA_LATENCY_MS-
k annotate deploy/catalog \
  kubernetes.io/change-cause="revert price rules engine on catalog (latency regression)" --overwrite
wait_rollout catalog

info "reverted. Browse latency should be back to ~tens of milliseconds."
