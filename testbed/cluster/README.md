# cluster/ — kind cluster lifecycle

## What this is

Definition and lifecycle scripts for the local Kubernetes cluster the testbed runs on.
[kind](https://kind.sigs.k8s.io/) runs each Kubernetes node as a Docker container.

| File | Purpose |
|---|---|
| `kind-config.yaml` | Cluster shape: 1 control-plane + 2 workers, host port mapping |
| `setup.sh` | Idempotent bring-up: cluster → metrics-server → build/load images → deploy apps |
| `teardown.sh` | Deletes the cluster (and everything in it) |

## Why this shape

- **Three nodes, not one** — pod scheduling spreads across workers, so node-level
  context (`kubectl get pods -o wide`, per-node events) looks like a real cluster.
  An investigator that assumes "everything is on one node" should fail here.
- **Host port mapping 8080 → NodePort 30080** — the gateway service is reachable from
  your laptop at `http://localhost:8080` without `kubectl port-forward` juggling.
  NodePorts are open on every node, so mapping through the control-plane node works.
- **metrics-server** — installed by `setup.sh` (with `--kubelet-insecure-tls`, required
  on kind's self-signed kubelets) so that `kubectl top pods/nodes` works. Memory
  pressure is a first-class signal in the OOM scenario.

## Usage

Normally driven via the testbed `Makefile` (`make up` / `make down`), but the scripts
run standalone too:

```sh
./setup.sh      # safe to re-run; skips the cluster if it already exists
./teardown.sh
```

The cluster is named `first-responder`; its kubectl context is `kind-first-responder`.

## Kubeconfig isolation

The cluster's credentials live in `testbed/.kubeconfig` (gitignored), **not** in
`~/.kube/config` — all scripts and the Makefile export
`KUBECONFIG=testbed/.kubeconfig` (overridable via `TESTBED_KUBECONFIG`). This keeps
the testbed completely separate from any default/corporate kubeconfig and vice versa.

To run `kubectl` against the testbed manually:

```sh
export KUBECONFIG=/path/to/first-responder/testbed/.kubeconfig
kubectl -n shop get pods
```
