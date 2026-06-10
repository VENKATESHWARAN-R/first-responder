#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/../_lib.sh"
require_cluster

info "restoring payments' upstream processor to healthy"
k set env deploy/payments ERROR_RATE-
k annotate deploy/payments \
  kubernetes.io/change-cause="remove ERROR_RATE override on payments" --overwrite
wait_rollout payments

info "reverted. Checkouts should succeed again (apart from the normal ~5% declines)."
