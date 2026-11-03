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

## 3️⃣a Low-Volume Services Scale to Zero

A platform service that runs a few times a day must not carry a fixed monthly charge.

- **Idle costs nothing.** Choose components billed per request or per unit stored, with no hourly
  charge while idle; a component with a standing charge needs a reason in its design.
- **Design against permanent free allowances, never trials.** A trial allowance ends on a date the
  design does not control. Where a service's permanent allowance applies only to one capacity mode,
  choose that mode at a capacity that stays inside it.
- **Prefer the thinnest entry point.** A function's own authenticated endpoint before a managed
  gateway, unless the gateway's features are needed.
- **Prove it on the bill.** The service's budget alarm is set before it ships, and its first 30
  days of billing are checked for any fixed charge.

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

### The cost ledger

Model spend is recorded per call and computed in one place, so cost per ticket and cost per
accepted change come from records, not estimates.

- **One record per call.** Every model call inside a factory run emits a `token_record.v1`
  (`schemas/token_record.v1.schema.json`) through the shared telemetry package: ticket, run, call,
  agent, attempt, model, provider, start time, and prompt, cached and completion tokens. The record
  carries counts, never a cost.
- **Cost is computed by the ledger,** from the record and a versioned price table kept in version
  control. Each computed cost names the price-table version it used, so a price change never
  rewrites history.
- **The ledger is append-only and idempotent.** A record is keyed by `run_id` and `call_id`; a
  resent record changes nothing, and a correction is a new record, never an edit.
- **Writes are authenticated.** Only the agents' own roles can write; a record that fails its
  schema is refused before it is stored (`09_Reuse_and_DRY.md` §6).
- **One source for cost.** Dashboards read the ledger; no second pipeline computes cost. Latency and
  errors stay in the observability stack.
- **Spend data is private.** Reading the ledger requires a signed-in owner; nothing is public.
- **Only factory work is metered.** Budgets and their alerts per ticket are in
  `06_AgentZone/01_Agent_Standards.md` §7.

---

## Principle

Show the cost before the merge, give every resource an owner and a budget, pay for expensive
capacity only while it is doing work, and price every model call from the record, not the claim.
