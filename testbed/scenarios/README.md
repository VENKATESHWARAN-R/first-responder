# scenarios/ — fault-injection scenarios with ground truth

## What this is

One directory per injectable fault. Each scenario is a reproducible, revertible
incident with a **documented root cause**, covering the five app-level incident
classes from the MVP definition in `.ai/IDEA.md`.

| Scenario | Class | What breaks |
|---|---|---|
| `01-bad-deploy` | bad-deploy | orders v1.4.0 points at a payments endpoint that doesn't exist → checkout 502s |
| `02-crash-loop` | crash-loop | catalog reconfigured to an unreachable Redis → CrashLoopBackOff → browse 502s |
| `03-oom-kill` | oom-kill | orders v1.3.1 enables an unbounded in-memory cache → OOMKilled every few minutes |
| `04-error-spike` | error-spike | payments' upstream processor "degrades" → ~85% of charges 500 → checkout 502s |
| `05-latency-regression` | latency-regression | catalog gains ~900 ms per request → browse latency ~20x, no errors |

## The scenario contract

Every scenario directory contains exactly four files:

| File | Contract |
|---|---|
| `inject.sh` | Applies the fault via plain `kubectl` against the `shop` namespace. Idempotent — running it twice is safe. Prints what to watch for. |
| `revert.sh` | Restores the exact healthy state from the manifests (deterministic — it does not rely on rollout history). Idempotent. |
| `ground-truth.yaml` | Machine-readable answer key, consumed by the future eval harness. Schema below. |
| `README.md` | The human story: what "happened", what is observable where, and why the ground truth is what it is. |

Injections are deliberately *ordinary Kubernetes changes* (`kubectl set env`,
`kubectl patch`): they create real rollouts with `change-cause` annotations, so the
trail an investigator finds (rollout history, fresh ReplicaSets, events) is the same
trail a real bad change leaves.

## Ground-truth schema

```yaml
id:               directory name
title:            one line, no colons (the Makefile parses it)
fault_class:      bad-deploy | crash-loop | oom-kill | error-spike | latency-regression
faulty_component: the k8s object at fault, e.g. deployment/orders
namespace:        shop
injection:
  mechanism:      the literal change inject.sh makes
  artifact_note:  how the injection differs from the real-world cause it simulates
root_cause:       prose answer key — what a correct diagnosis must identify
observable_signals:  list of evidence a good investigation should surface
blast_radius:     list of affected components / user-facing paths
time_to_symptom:  how long after injection symptoms appear
expected_verdict: what the agent should conclude (mitigation-proposed for all five)
expected_mitigation: the correct safe remediation
```

Scoring intent: a diagnosis counts as correct when it identifies the
`faulty_component` **and** the substance of `root_cause`, with cited evidence that
actually appears in `observable_signals` territory. "Checkout is returning 502s"
(the symptom) is not a root cause.

## Rules

- **The investigation agent must never read this directory.** The ground truth is
  the exam answer key. The agent sees only what it could see in production: the
  cluster API, logs, metrics, events, and the app repo (`apps/`).
- Symptoms need traffic — the in-cluster `loadgen` provides it. Verify it's running
  (`make status`) before injecting.
- Run one scenario at a time, and `revert` before injecting the next: overlapping
  faults invalidate each other's ground truth.

## Usage

```sh
make scenarios                   # list
make inject S=04-error-spike
export KUBECONFIG=../testbed/.kubeconfig   # testbed credentials live here, not in ~/.kube
kubectl -n shop logs deploy/loadgen -f     # watch symptoms
make revert S=04-error-spike
```

## Adding a scenario

Copy an existing directory, keep the four-file contract, give it the next number,
and make sure `revert.sh` restores the manifest state byte-for-byte (check with
`kubectl diff -f ../apps/manifests/`). If the fault needs a new knob in a service,
document it in `../apps/README.md`.
