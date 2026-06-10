#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/../_lib.sh"
require_cluster

info "pointing catalog at a shared redis that does not exist (botched infra migration)"
k set env deploy/catalog \
  REDIS_URL=redis://redis-primary.infra.svc.cluster.local:6379/0
k annotate deploy/catalog \
  kubernetes.io/change-cause="config change: point catalog at shared redis (infra migration)" --overwrite

info "injected. New catalog pods will crash at startup; expect CrashLoopBackOff within ~1 minute."
info "watch:  kubectl --context $KCTX -n $NS get pods -w"
info "        kubectl --context $KCTX -n $NS logs deploy/catalog --tail=20"
