#!/usr/bin/env bash
# Idempotent testbed bring-up: kind cluster -> metrics-server -> images -> shop stack.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTBED_DIR="$(dirname "$SCRIPT_DIR")"

# Keep this local kind cluster out of the user's default/corporate kubeconfig(s).
export KUBECONFIG="${TESTBED_KUBECONFIG:-$TESTBED_DIR/.kubeconfig}"

CLUSTER_NAME="first-responder"
KCTX="kind-${CLUSTER_NAME}"
NS="shop"
VERSION="1.3.0"
SERVICES=(gateway catalog orders payments)

info() { printf '\033[1;34m[setup]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[setup]\033[0m %s\n' "$*"; }

need() {
  command -v "$1" >/dev/null 2>&1 || { echo "error: '$1' is required but not installed" >&2; exit 1; }
}
need docker
need kind
need kubectl

# --- 1. Cluster -------------------------------------------------------------
if kind get clusters 2>/dev/null | grep -qx "$CLUSTER_NAME"; then
  info "kind cluster '$CLUSTER_NAME' already exists, skipping creation"
else
  info "creating kind cluster '$CLUSTER_NAME' (1 control-plane + 2 workers)"
  kind create cluster --config "$SCRIPT_DIR/kind-config.yaml"
fi

# --- 2. metrics-server (for 'kubectl top') ----------------------------------
if kubectl --context "$KCTX" -n kube-system get deploy metrics-server >/dev/null 2>&1; then
  info "metrics-server already installed"
else
  info "installing metrics-server"
  if kubectl --context "$KCTX" apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml; then
    # kind kubelets use self-signed certs; metrics-server must be told to accept them.
    kubectl --context "$KCTX" -n kube-system patch deploy metrics-server --type=json \
      -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
  else
    warn "metrics-server install failed (offline?) — 'kubectl top' won't work; everything else will"
  fi
fi

# --- 3. Build app images and side-load into kind ----------------------------
for svc in "${SERVICES[@]}"; do
  info "building shop/${svc}:${VERSION}"
  docker build -q -t "shop/${svc}:${VERSION}" "$TESTBED_DIR/apps/services/${svc}"
  info "loading shop/${svc}:${VERSION} into the cluster"
  kind load docker-image "shop/${svc}:${VERSION}" --name "$CLUSTER_NAME"
done

# --- 4. Deploy the shop stack ------------------------------------------------
info "applying namespace"
kubectl --context "$KCTX" apply -f "$TESTBED_DIR/apps/manifests/namespace.yaml"
kubectl --context "$KCTX" wait --for=jsonpath='{.status.phase}'=Active "namespace/$NS" --timeout=60s

info "applying app manifests"
for manifest in redis payments orders catalog gateway loadgen; do
  kubectl --context "$KCTX" apply -f "$TESTBED_DIR/apps/manifests/${manifest}.yaml"
done

info "waiting for rollouts"
for deploy in redis "${SERVICES[@]}"; do
  kubectl --context "$KCTX" -n "$NS" rollout status "deploy/${deploy}" --timeout=180s
done

# --- 5. Smoke ----------------------------------------------------------------
info "smoke-testing the gateway via http://localhost:8080"
for attempt in 1 2 3 4 5; do
  if curl -fsS --max-time 5 http://localhost:8080/api/products >/dev/null 2>&1; then
    info "gateway is serving traffic"
    break
  fi
  [ "$attempt" -eq 5 ] && { warn "gateway not reachable on localhost:8080 yet — check 'make status'"; break; }
  sleep 3
done

info "done. Try:  curl http://localhost:8080/api/products | jq"
info "      then: make scenarios   (from the testbed/ directory)"
