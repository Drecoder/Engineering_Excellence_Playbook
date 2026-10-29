# Engineering Excellence Playbook

_High-level overview of Principles & Philosophies guiding platform flow._

---

## 🚀 Purpose

This playbook consolidates my **consultant-first approach** to engineering across:

- Frontend, Backend, and Infrastructure
- Async flows and operational processes
- Observability, security, and platform governance

It provides **repeatable, auditable, flow-oriented guidance** for building, operating, and improving systems.

---

## 📓 Proof Journal

A standard counts only when it is enforced and running. The **[proof journal](docs/POC_JOURNAL.md)**
records what applying this playbook actually found while building the software factory, each
finding written up as a compact post-mortem in CAPA form (Corrective and Preventive Action): the
rule, the problem, how it was found, the root cause, the correction, the preventive action, and the
verification, including the findings still open.

It is one living document with three roles, all feeding the same loop from standard to evidence and
back:

- **Engineering artifact:** the evidence-linked history of findings, fixes, and open work, so the
  project's actual state is readable without reconstructing it from Git.
- **Learning resource:** causal knowledge (what failed, why, how it was caught, how the fix was
  verified) that a learning system can teach from.
- **Feedback mechanism:** prior experience the factory's agents and future decisions weigh
  against the playbook's standards and current evidence.

The first role is in use today; the other two are designed and not yet wired.

- **Append-only, enforced:** CI refuses any change that edits, deletes, or reorders an entry.
- **Ranked and timed:** the **[CAPA register](docs/FINDINGS_REGISTER.json)** gives every finding a
  severity on a written rubric and a mandatory deadline (critical 7 days, high 30, medium 90, low
  180); an overdue finding fails the daily run.
- **Measured:** every run reports how many control classes are proven to fail on their defect and
  how many findings a control caught rather than a person.
- **Governance before production:** production readiness stays false while any critical or high
  security or governance finding is open.

The **[incident records](docs/incidents/README.md)** hold the full post-mortems, and
**[program increments](docs/PROGRAM_INCREMENTS.md)** show the plan they feed.

---

## 1️⃣ Core Principles

1. **I manage flow** – every action, workflow, and process is observed, traceable, and recoverable.
2. **Operational continuity first** – service reliability is prioritized over immediate fixes.
3. **Work is only done when cross-layer ready** – code, infrastructure, and operational flows must align.
4. **Rollbacks are repeatable flows** – reversible deployments are designed and tested, not improvised.
5. **Observability is integral** – metrics, logs, and alerts are embedded into every layer.
6. **Decisions are signal-driven** – Red/Green logic guides safe progression across all systems.
7. **Least privilege everywhere** – access is granted based on role and necessity, minimizing risk.
8. **Continuous learning** – post-mortems and audits turn incidents into actionable insights.
9. **Cross-layer alignment** – frontend, backend, infrastructure, and async systems flow cohesively.
10. **Consistency and reproducibility** – all standards, policies, and flows are version-controlled and auditable.

---

## 2️⃣ Core Philosophies

- **Treat components as flow participants** – everything from React components to workers emits and consumes observability signals.
- **Preventive design over reactive fixes** – workflows are designed to minimize emergency interventions.
- **Documentation is code** – living standards, templates, and checklists are versioned and shareable.
- **Trade-offs are evaluated holistically** – the “Two Sides of the Coin” balances immediate impact vs long-term resilience.
- **Automation is a baseline expectation** – CI/CD, Terraform, and policy-as-code minimize human error.
- **Metrics drive decisions** – thresholds, queue depths, and latency inform operational actions.
- **Guidance, not prohibition** – frameworks like Red/Green or Least Privilege guide actions rather than restrict them arbitrarily.
- **Cross-layer visibility** – all alerts, metrics, and logs must be meaningful across infra, backend, frontend, and async flows.
- **Standardization enables agility** – consistent patterns allow faster decisions without sacrificing reliability.
- **Platform is a living system** – standards evolve, post-mortems inform improvements, and learning loops are continuous.

---

## 📂 Repo Structure Overview

```text
Engineering_Excellence_Playbook/
├── AGENTS.md                # Enforceable standards for engineers, assistants, and agents
├── CLAUDE.md                # Shim: imports AGENTS.md for Claude Code
├── 00_UniversalStandards/   # Lifecycle, DoD, security in depth, governors, distribution, refactors, central CI
├── 01_FrontendZone/         # React patterns, clean code, performance
├── 02_BackendZone/          # API architecture, async processing, database health, telemetry
├── 03_InfrastructureZone/   # IaC core + GCP/AWS specifics, security & IAM, Kubernetes
├── 04_OperationalRunbooks/  # Rollbacks, incident response, alert thresholds
├── 05_Metadata/             # Red/Green logic, trade-offs, least privilege
├── 06_AgentZone/            # Agent contracts, tool guardrails, risk routing, golden tasks
├── 07_SoftwareFactory/      # Capstone: the factory's repositories and how they work together
├── ARCHITECTURE.md          # Platform map: layers, path of a change, trust boundaries, status
├── docs/                    # Deep dives: USL, Little's Law, RED/USE methods
├── metrics/promql/          # Master Metric Index (PromQL constants)
├── templates/consumer/      # Files a consumer repo copies to depend on the playbook
└── action.yml               # GitHub Action that vendors AGENTS.md / schemas into a consumer
```

> Each folder contains templates, standards, and reference guides to manage platform flow effectively.

---

## 🔗 How to Use

1. Start with **00_UniversalStandards** — align on deliverables, definition of done, and post-mortem process.
2. **Consult the Master Metric Index** — Use the `/metrics/promql/` folder for standardized monitoring constants.
3. Use **FrontendZone**, **BackendZone**, and **InfrastructureZone** for implementation guidelines and operational standards.
4. Reference **OperationalRunbooks** for reactive flows (rollbacks, monitoring).
5. Consult **Metadata** for high-level decision frameworks (Red/Green logic, Two Sides of the Coin, least privilege).
6. Use **AgentZone** when building or changing an AI agent (contracts, guardrails, risk routing).
7. Finish with **SoftwareFactory**, the capstone — the workshop where every zone's rules are used together.
8. Keep all updates in GitHub — changes are version-controlled, auditable, and syncable to Confluence if needed.
