# Definition of Done (DoD)

*Establishing clear, cross-layer criteria for completing work.*

---

## 🟢 The Flow Audit (Technical Gate)

A task is not "Done" until it passes the **Flow Audit**. This ensures the technical "physics" of the change are sound:

* [ ] **Standardized Semantics:** Code is idiomatic (Go/Python/Node) and maintainable by any industry professional.
* [ ] **Rate Limited:** Entry points have arrival gates to protect the service substrate.
* [ ] **Concurrency Controlled:** All workers/tasks are managed by a **Governor** (No "naked" goroutines, unbounded async loops, or unmanaged worker threads).
* [ ] **RED Validated:** Throughput, Errors, and P99 Latency are visible in PromQL.
* [ ] **USE Validated:** The service operates within the **-1σ buffer** of the substrate capacity.

---

## 1️⃣ Philosophy

I define “done” not as code pushed, but as **work that is complete, observable, tested, and aligned across layers**:

* Fully implemented and peer-reviewed.
* Observable and monitored in production.
* Documented in code and operational standards.
* Tested at unit, integration, and contract levels.
* Cross-layer impact considered (frontend, backend, infra, async, DB).

---

## 2️⃣ Criteria Checklist

| Layer | DoD Criteria |
| :--- | :--- |
| **Code** | Code meets style, linting, and coverage standards; passes all automated tests. |
| **Infrastructure** | Resources managed as code; deployed via CI/CD; drift minimized. |
| **Backend** | APIs meet contract, async flows validated, database interactions safe. |
| **Frontend** | UI/UX matches design; interacts correctly with APIs; error states handled. |
| **Observability** | Logs, metrics, alerts in place; dashboards updated. |
| **Documentation** | Markdown or Confluence updated with clear instructions, diagrams, references. |
| **Operational Readiness** | Rollback procedures confirmed; failover or retry flows tested. |
| **Security** | Every layer of `07_Security_In_Depth.md` holds: SSO + MFA, federated identity, least privilege, TLS 1.2+ with authenticated service traffic, encryption at rest, no public access; all `SEC-*` policies pass. |
| **Telemetry** | Traces, metrics, and correlated logs emitted from the first version (`02_BackendZone/04_Telemetry_Standards.md`); dashboard JSON committed. |
| **Agents** | Input/output schemas validated; tools sandboxed; loops bounded; golden tasks (incl. one designed-to-fail) pass; no `apply` capability (`06_AgentZone/01_Agent_Standards.md`). |

---

## 3️⃣ Principle

Work is **only done when it can be reliably operated, observed, and extended**.

Pushing code is **not enough** — completeness requires cross-layer verification, technical flow auditing, and operational readiness.
