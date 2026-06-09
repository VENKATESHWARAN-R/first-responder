# First Responder — Autonomous K8s Incident First Responder (Multi-Agent)

> **Status:** Draft — 2026-06-10

---

## Problem Statement

When a production microservice on Kubernetes breaks at 2 AM, the alert that fires (Prometheus/Alertmanager → PagerDuty/Slack) reaches a human stripped of all context. The on-call SRE wakes up to a one-line notification and spends the first 20–40 minutes of the incident manually assembling state: Grafana dashboards, `kubectl` output, recent deploy diffs, runbook wikis, and Slack scrollback — before they can form even a first hypothesis. Diagnosis, not repair, dominates MTTR, and this context-gathering is the least-leveraged, most-miserable work in engineering: high-stakes, repetitive, and performed at the worst possible hour by a degraded human.

## Target User

The SRE / platform engineer carrying the pager at a mid-size SaaS company (50–500 engineers) running microservices on Kubernetes. They have a real on-call rotation but no follow-the-sun coverage, so night pages land on people with day jobs. They care about sleep, MTTR, and not being paged for noise — and they extend trust only to tools that show their evidence. They can adopt new tooling without enterprise procurement, which makes them the sharpest first wedge.

## Current Workaround

Alertmanager routes to PagerDuty/Slack; a human wakes and runs the investigation by hand: dashboards, `kubectl describe/logs`, the deploy pipeline history, a wiki search for the relevant runbook, and questions in Slack. Some teams bolt on single-shot AI explainers (K8sGPT-style) that summarize one resource's state, but nothing investigates *across* telemetry, code changes, and documentation, and nothing proposes or executes a mitigation. The workaround is tolerated because incidents are episodic — but every minute of it sits on the critical path of MTTR, and the toil is a known driver of on-call burnout and attrition.

## Proposed Solution

An autonomous multi-agent "First Responder" that intercepts the alert before the human. A **Coordinator Agent** (incident commander) receives the alert payload, plans the investigation, and dispatches specialist sub-agents in parallel:

- **Telemetry Agent** — live logs, metrics, and distributed traces from the cluster
- **Codebase Agent** — recent commits, diffs, and manifest changes in the application repos
- **Docs/RAG Agent** — internal runbooks, SOPs, and architecture guides

The Coordinator synthesizes their findings into a **verdict**, a **proposed mitigation**, and an **evidence-linked dossier**, then pages the human with all three. The human approves the mitigation with one click; the system executes it and produces a comprehensive incident report.

**Does:**
- Intercept Prometheus/Alertmanager alerts before any human is paged
- Run a parallel multi-agent investigation across telemetry, codebase, and documentation
- Issue a verdict for every alert: false alarm / self-healed / mitigation proposed / needs human now
- Propose safelisted mitigations (rollback last deploy, scale replicas, restart pods) — executed only on one-click human approval
- Link every claim in the dossier to raw evidence (the log lines, the diff, the metric query) with explicit confidence levels
- Page the human *with* the dossier when human judgment is required
- Produce a comprehensive incident report after every investigation, action taken or not

**Does NOT:**
- Act autonomously without human approval (the autonomy dial exists in the vision; the MVP ships at approve-gated)
- Handle DDoS or security incidents (roadmap: dedicated Security Agent — different toolset, different trust conversation)
- Cover infra/cluster-level incidents (node pressure, disk, networking) in the MVP
- Replace the alerting stack — it sits behind Alertmanager, it doesn't redefine alert rules
- Write code or open PRs to fix bugs — it recommends; humans fix

## MVP Definition (3-Month Target)

An on-call SRE receives a page that already contains a verdict, an evidence-linked root-cause hypothesis, and a proposed mitigation they can approve with one click — within minutes of the alert firing — for application-level incidents: 5xx/error spikes, latency regressions, crash loops, OOM kills, and bad deploys. The full loop (investigate → verdict → propose → approve → execute → report) works end-to-end; read-only "report only" mode falls out for free by hiding the approve button.

## Success Metric

- **Time-to-context:** alert fired → dossier delivered in under 5 minutes.
- **Diagnosis quality (pre-deployment):** in a fault-injected test bed, the system identifies the true root cause in ≥70% of the covered scenario classes.
- **Trust transfer (with design partners):** in ≥70% of real incidents, the human's first action matches the agent's top recommendation.
- **Noise suppression:** non-actionable alerts correctly closed with a false-alarm/self-healed verdict instead of a page.

## Riskiest Assumption

**Diagnosis quality is good enough to be trusted.** The bet: the dossier is right — and honest about its uncertainty — often enough that the on-call treats it as their starting point instead of re-deriving everything from scratch. A confident-but-wrong narrative at 2 AM is *worse* than no narrative; it sends a degraded human down the wrong path. Design consequences baked in from day one: every claim cites raw evidence, confidence is explicit, and "I don't know — here's what I ruled out" is a first-class output.

## Why Now / Why You

- **Why now:** Agentic orchestration frameworks and standardized tool access (MCP-style) became practical only in the last ~2 years, and Kubernetes provides a rare uniform API surface — an investigation agent generalizes across companies in a way bespoke enterprise tooling never could.
- **Why me:** I carry the pager myself — built-in user empathy and a live test environment. The project doubles as deep multi-agent architecture practice and a venture-wedge test, so it's worth building even before market validation completes.

## Parking Lot

- Security/DDoS Agent (traffic-attack classification, WAF/rate-limit response)
- Infra-level incidents: node pressure, disk, networking, cluster components
- Autonomy dial beyond approval: safelisted auto-mitigation, blast-radius-bounded autonomy per team / per alert type
- Historian Agent — incident memory ("we've seen this before; last time it was the node pool")
- Runbook flywheel — every investigation becomes a draft runbook; the system writes the documentation it later retrieves
- Comms Agent — drafts status-page updates and stakeholder Slack threads during incidents
- Morning-after blameless postmortem draft generation
- Learning loop from human approve/reject/correction signals on dossiers and mitigations
- Multi-cluster / fleet-wide view
- Per-investigation cost and latency budgets as a product surface

## Kill Conditions

- In a controlled fault-injection test bed, the system cannot reach the correct root cause in at least ~60% of common app-level scenarios after sustained iteration → the diagnosis-quality bet fails; rethink the core approach.
- Design-partner SREs read the dossiers but consistently re-derive the investigation from scratch anyway → trust never transfers; the core value proposition fails.
- After ~10 serious conversations, no mid-size team will grant even read-only cluster + repo + telemetry access → the access/trust posture blocks the wedge; re-evaluate as self-hosted/internal-first.
