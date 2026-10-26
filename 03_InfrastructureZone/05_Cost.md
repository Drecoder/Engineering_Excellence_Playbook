# Cost

*Every change shows what it costs before it merges, every resource has an owner, and the most
expensive capacity is borrowed, not kept.*

Cost anti-patterns visible in Terraform are the `AP-COST-*` rules in `schemas/antipatterns.v1.json`.

---

## 1️⃣ Cost Is Visible Before Merge

- **A cost diff on every plan.** The pipeline runs a cost estimator (Infracost) on the Terraform
  plan and posts the monthly delta. A delta above the repository's threshold needs a person's
  approval, like any other high-scrutiny change.
- Infracost needs an API key for its pricing service. The key is a CI secret, passed explicitly to
  the job that needs it and never to agents; until it exists, the cost diff is a documented gap.

## 2️⃣ Every Resource Has an Owner

- Every billable resource carries `owner`, `service`, and `unit_class` labels, applied once as
  default labels in the root configuration (`AP-COST-001`).
- Spend is reported per service and per owner; a resource nobody owns is a finding.

## 3️⃣ Budgets and Alerts

- Every project or account is vended with a **budget and alerts** at 50%, 90%, and 100% of its
  monthly amount (`AP-COST-003`). Genesis does this for every project it vends
  (`00_UniversalStandards/08_Governance_Guardrails.md`).
- A budget alert is routed like any other alert, with an owner and a runbook.

## 4️⃣ Expensive Capacity Is Borrowed

- **GPUs and large instances run on spot or preemptible capacity with a maximum run duration**,
  and the work they do checkpoints, so a preemption costs minutes, not the run (`AP-COST-002`).
  On-demand capacity for them is a reviewed exception.
- **Ephemeral units carry a TTL** and are swept (`AGENTS.md` → IaC Rules; `AP-TG-004`).
- **Right-size from measurements**: requests and machine types follow USE metrics
  (`docs/USE_METHOD.md`), not guesses.

## 4️⃣a Storage Is Tiered

- History that is read only during triage does not stay in standard storage: only the last few
  deployments are hot, and older ones are bundled and moved to archive storage
  (`03_InfrastructureZone/06_Messaging_Building_Blocks.md` §3a).
- Small objects are bundled before archiving; archiving them one by one can cost more than it saves.

## 5️⃣ Model Cost

- Every model call increments a token and cost counter (`AGENTS.md` → Observability Rules); the
  model ladder picks the cheapest model that fits the task, and every model step must show that it
  improves outcomes (`06_AgentZone/01_Agent_Standards.md`).

---

## Principle

Show the cost before the merge, give every resource an owner and a budget, and pay for expensive
capacity only while it is doing work.
