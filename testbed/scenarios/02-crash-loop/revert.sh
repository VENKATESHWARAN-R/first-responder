#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/../_lib.sh"
require_cluster

info "restoring catalog's redis config to the in-namespace redis"
k set env deploy/catalog \
  REDIS_URL=redis://redis.shop.svc.cluster.local:6379/0
k annotate deploy/catalog \
  kubernetes.io/change-cause="revert redis config change on catalog" --overwrite
wait_rollout catalog

info "reverted. Catalog pods should be Running and Ready."
