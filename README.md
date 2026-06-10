# First Responder

An autonomous multi-agent **Kubernetes incident first responder**. When a production
alert fires, First Responder investigates *before* a human is paged — pulling live
telemetry, recent deploy history, and runbooks — and pages the on-call with a verdict,
an evidence-linked root-cause hypothesis, and a one-click mitigation proposal.

The full concept, scope, success metrics, and kill conditions live in
[`.ai/IDEA.md`](.ai/IDEA.md). Read that first.

## Status

**Pre-MVP.** The riskiest assumption of the whole project is *diagnosis quality* —
can an agent reach the correct root cause often enough to be trusted at 2 AM? Nothing
else (multi-agent orchestration, Slack paging, mitigation execution) matters until
that question has a number attached to it.

So the build order is deliberately:

1. **`testbed/`** ← *current* — a local Kubernetes cluster with a realistic
   microservice stack and reproducible fault-injection scenarios, each with
   machine-readable ground truth.
2. **Investigation agent** — a single agent with read-only cluster tools that
   produces an evidence-linked dossier.
3. **Eval harness** — runs the agent against every testbed scenario and scores
   root-cause accuracy and evidence fidelity against the ground truth.

Only after the eval number clears the bar (≥60–70% per the kill conditions) does the
architecture grow toward the multi-agent design in the idea doc.

## Repository layout

| Path | What it is |
|---|---|
| `.ai/IDEA.md` | The idea document — problem, MVP definition, success metrics, kill conditions |
| `testbed/` | Local k8s fault-injection testbed: cluster setup, demo app stack, failure scenarios |

Every module carries its own `README.md` explaining what is in it and why it exists.

## Quickstart

```sh
cd testbed
make up                      # create kind cluster, build & deploy the shop stack
make smoke                   # verify the stack serves traffic
make scenarios               # list available fault scenarios
make inject S=03-oom-kill    # break something on purpose
make revert S=03-oom-kill    # heal it
make down                    # delete the cluster
```

Prerequisites and details: [`testbed/README.md`](testbed/README.md).
