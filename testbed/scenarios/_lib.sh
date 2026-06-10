# Shared helpers for scenario inject/revert scripts. Source, don't execute.
set -euo pipefail

_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTBED_DIR="$(dirname "$_LIB_DIR")"

# Keep this local kind cluster out of the user's default/corporate kubeconfig(s).
export KUBECONFIG="${TESTBED_KUBECONFIG:-$TESTBED_DIR/.kubeconfig}"

NS="shop"
KCTX="kind-first-responder"

k() { kubectl --context "$KCTX" -n "$NS" "$@"; }

info() { printf '\033[1;34m[scenario]\033[0m %s\n' "$*"; }

require_cluster() {
  kubectl --context "$KCTX" get ns "$NS" >/dev/null 2>&1 || {
    echo "error: namespace '$NS' not found on context '$KCTX' — run 'make up' first" >&2
    exit 1
  }
}

wait_rollout() {
  k rollout status "deploy/$1" --timeout=120s
}
