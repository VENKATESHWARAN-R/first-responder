#!/usr/bin/env bash
# Deletes the testbed cluster and everything running in it.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTBED_DIR="$(dirname "$SCRIPT_DIR")"

# Keep this local kind cluster out of the user's default/corporate kubeconfig(s).
export KUBECONFIG="${TESTBED_KUBECONFIG:-$TESTBED_DIR/.kubeconfig}"

CLUSTER_NAME="first-responder"

if kind get clusters 2>/dev/null | grep -qx "$CLUSTER_NAME"; then
  kind delete cluster --name "$CLUSTER_NAME"
else
  echo "kind cluster '$CLUSTER_NAME' does not exist — nothing to do"
fi
