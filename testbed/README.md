# Testbed — fault-injection environment for First Responder

## What this is

A fully local, disposable Kubernetes environment that can be broken **on purpose, in
known ways**. It is the ground-truth machine for the whole project: every fault
scenario here has a documented root cause, so an investigation agent's diagnosis can
be *scored*, not just eyeballed.

It exists to make the project's kill condition testable (see `.ai/IDEA.md`):

> "In a controlled fault-injection test bed, the system cannot reach the correct root
> cause in at least ~60% of common app-level scenarios → the diagnosis-quality bet fails."

## What's inside

| Path | What it is | Read its README for |
|---|---|---|
| `cluster/` | [kind](https://kind.sigs.k8s.io/) cluster definition + setup/teardown scripts | node layout, port mapping, metrics-server |
| `apps/` | The "shop" demo stack: 4 microservices + Redis + a load generator | architecture, fault knobs, logging/metrics conventions |
| `scenarios/` | One folder per injectable fault, each with `inject.sh`, `revert.sh`, `ground-truth.yaml`, `README.md` | the scenario contract and ground-truth schema |
| `Makefile` | Single entry point for everything below | — |

## Prerequisites

- **Docker** (running)
- **kind** ≥ 0.20 — `brew install kind`
- **kubectl** — `brew install kubectl`

No cloud account, no registry: images are built locally and side-loaded into kind.

## Usage

```sh
make up                       # create cluster, install metrics-server, build + deploy everything
make status                   # pods, deployments, recent events
make smoke                    # curl the gateway from the host (http://localhost:8080)
make scenarios                # list fault scenarios
make inject S=01-bad-deploy   # inject a fault
make revert S=01-bad-deploy   # undo it
make build                    # rebuild app images after code changes and restart deployments
make down                     # delete the whole cluster
```

The gateway is reachable from the host at **http://localhost:8080** (kind maps host
port 8080 to the gateway's NodePort). A `loadgen` pod inside the cluster generates
continuous browse + checkout traffic, so faults produce *observable symptoms* (error
rates, latency, restarts) within seconds to minutes — there is always something for
an investigator to find in logs and metrics.

## Design decisions

- **kind, not minikube/cloud** — multi-node, runs in CI later, free, and `kind load`
  avoids needing an image registry.
- **Our own services, not a public demo app** — fault behavior must be controllable
  and the *application code must live in this repo*, because the future Codebase
  Agent investigates recent commits and deploy diffs. Off-the-shelf demo apps
  (Sock Shop, Online Boutique) give neither.
- **Faults are env-var toggles applied via `kubectl`** — every injection is a regular
  Kubernetes rollout or config change, which is exactly what real bad changes look
  like: they show up in `kubectl rollout history`, events, and pod restarts. No
  chaos-mesh dependency for the five MVP scenario classes.
- **Everything is a file** — cluster config, manifests, scenario definitions, and
  ground truth are all declarative files in git. No state lives anywhere else.

## Relationship to the rest of the project

The future eval harness will iterate over `scenarios/*/ground-truth.yaml`: inject the
fault, let symptoms develop, run the investigation agent, and compare its dossier
against the ground truth (correct root cause? evidence actually supports the claims?).
The agent itself must **never** read the `scenarios/` directory — that would be
cheating. See `scenarios/README.md`.
