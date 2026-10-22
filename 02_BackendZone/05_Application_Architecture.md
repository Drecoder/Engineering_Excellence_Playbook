# Application Architecture

*Where business logic is split, where state lives, and how data moves between components, decided
once here so that people and agents stop improvising it per service.*

The rest of the playbook governs the platform every service runs on: identity, guardrails,
pipelines, telemetry. This document governs the services themselves. It matters most for AI agents:
a Builder asked to "add a service with a queue" fills any gap in the rules with its own guess, and
guesses differ every time. The enforceable subset is in `AGENTS.md` → **Application Architecture
Rules**, and every rule carries an `ARCH-*` ID that `schemas/architecture_rules.v1.json` makes
checkable (§10).

---

## 1️⃣ Start as a Modular Monolith

A new system starts as **one deployable with internal module boundaries**, not as a set of services.

- Modules inside the monolith follow the same boundary rules as repositories
  (`00_UniversalStandards/09_Reuse_and_DRY.md`): each module has an internal scope and a declared
  public interface, and modules do not import each other's internals (`ARCH-001`).
- **A module becomes its own service only for a measured reason**, recorded in the change that
  splits it (`ARCH-002`):

| Reason to split | Evidence |
| :--- | :--- |
| Independent scaling | The module's load profile differs from the rest, shown by its RED and USE metrics |
| Failure isolation | A failure in the module has degraded unrelated features (an incident record) |
| Ownership | A separate team owns it and is blocked by the shared release cycle |
| Different runtime or security boundary | It needs another language, hardware, or a stricter identity boundary |

"It might need to scale someday" is not a reason. Each extra service adds a network hop, a failure
mode, a deployment pipeline, and an identity to govern.

---

## 2️⃣ Each Service Owns Its Data

- **One owner per data store.** A database, bucket, or table belongs to exactly one service. No
  other service reads or writes it directly, including "just for reporting" (`ARCH-003`).
- **Data crosses boundaries only through contracts**: an API or an event, each versioned. Contracts
  shared across repositories live once in the playbook's `schemas/` and are vendored
  (`00_UniversalStandards/09_Reuse_and_DRY.md` §6; `ARCH-004`).
- Reporting and analytics read from events or a derived store the owner publishes, never from the
  owner's tables.
- The owning service's identity is the only one granted write access to its store
  (`03_InfrastructureZone/02_Security_IAM_Policies.md`).

---

## 3️⃣ Transactions and Connections

- **Keep transactions short.** No network call (another service, a queue publish, an external API)
  happens inside a database transaction; a slow remote call holding a transaction open is how
  connection pools and locks run out (`ARCH-005`).
- **Choose the isolation level deliberately** for each workflow that reads and then writes, and
  record why. The database default is a decision too, not a neutral choice (`ARCH-006`).
- **Size connection pools with Little's Law**: concurrent connections needed is roughly the query
  arrival rate times P99 query duration, the same reasoning as a Governor
  (`docs/PHYSICS_OF_FLOW.md`). The pool is a Governor: bounded, with a wait timeout, observable
  (`ARCH-007`).

---

## 4️⃣ Schema Changes: Expand, Then Contract

Database schemas change with the same sequencing as module refactors
(`00_UniversalStandards/06_Module_Refactor_Framework.md`): never break readers and writers in one
step.

| Step | Change | Safe because |
| :--- | :--- | :--- |
| **1. Expand** | Add the new column, table, or index; nullable or with a default | Old code ignores it |
| **2. Dual write** | Code writes both the old and the new shape | Either shape is complete |
| **3. Backfill** | Fill the new shape for existing rows, in bounded batches (`ARCH-010`) | Batches respect the Governor; resumable |
| **4. Switch reads** | Code reads the new shape | The old shape still exists for rollback |
| **5. Contract** | Stop writing, then drop the old shape | Only after the previous step has run cleanly in production |

- Each step is its own change, deployable and reversible on its own (`ARCH-008`).
- **Step 5 is irreversible**: it is the `irreversible` protected class in
  `00_UniversalStandards/10_Autonomy_by_Evidence.md`, so a person approves it at every autonomy
  level, after confirming a backup exists (`ARCH-009`).
- Migrations run through the pipeline, never by hand against a live database.

---

## 5️⃣ Reliable Events: the Transactional Outbox

"Write to the database, then publish the event" loses events when the process dies between the two,
and "publish, then write" announces things that never happened.

- **Outbox:** the service writes the business change **and** the event into an outbox table in the
  **same transaction**. A relay publishes outbox rows to the queue and marks them sent (`ARCH-011`).
- **Inbox:** consumers record the IDs of events they have processed, in the same transaction as
  their own write, so a redelivered event changes nothing (the idempotency rule in
  `02_BackendZone/02_Async_Processing.md`; `ARCH-012`).
- **Multi-service workflows use sagas**, not distributed transactions: each step commits locally and
  publishes an event; each step has a defined **compensating action** that undoes it if a later step
  fails. Two-phase commit across services is not used (`ARCH-013`).

---

## 6️⃣ Queue Topology

Every queue or topic documents, next to its schema (`ARCH-014`; tracing `ARCH-015`; backpressure
`ARCH-016`):

| Property | Rule |
| :--- | :--- |
| **Delivery** | At-least-once, always; consumers are idempotent |
| **Ordering** | Stated explicitly: none, or per key. When per key, the partition or ordering key is named and justified |
| **Poison messages** | After a bounded number of retries with backoff, the message goes to a dead-letter queue; DLQ growth is a ticket (`04_OperationalRunbooks/02_Monitoring_Alert_Thresholds.md`) |
| **Replay** | Consumers are safe to replay from any point; replay is how a fixed consumer catches up |
| **Backpressure** | Consumers pull through a Governor; a slow consumer lags, it does not fall over |
| **Tracing** | Producers put the trace context in the message headers, so a trace continues across the queue |

---

## 7️⃣ Calls Between Services

- **Timeouts on every call**, shorter than the caller's own deadline, so a slow dependency cannot
  hold the caller (`ARCH-017`).
- **Retries only for idempotent operations**, with exponential backoff and jitter and a retry
  budget; non-idempotent writes carry an **idempotency key** so a retried request is applied once
  (`ARCH-018`).
- **Pagination** on every list endpoint; no unbounded responses (`ARCH-019`).
- **Synchronous call chains stay shallow and acyclic**: a request that hops through more than three
  services synchronously, or reaches the same service twice, is a distributed monolith; part of the
  chain becomes an event, or the services become one module (`ARCH-020`).
- APIs are versioned contracts (`02_BackendZone/01_API_Architecture.md`); a breaking change ships a
  new version next to the old one, the expand-then-contract pattern again.

---

## 8️⃣ Caching

- **Cache-aside by default**, with an explicit TTL and an invalidation path for every cached item
  (`ARCH-021`).
- **Never cache an authorization decision** longer than the credential it was based on (one hour at
  most, `00_UniversalStandards/07_Security_In_Depth.md`), and never share one user's cached
  authorization with another (`ARCH-022`).
- Protect hot keys against stampedes (request coalescing or early refresh), and keep the service
  correct, if slower, when the cache is empty or down: a cache is an optimization (`ARCH-023`).

---

## 9️⃣ What Vended Services Get

Services vended by Genesis (`00_UniversalStandards/08_Governance_Guardrails.md` §8) start from a
template that already contains these decisions: a module layout with declared boundaries, its own
data store and identity, the outbox and inbox tables, a Governor-bounded consumer, trace propagation
in message headers, and timeouts and retries on its HTTP client. The Builder extends the template;
it does not design these from scratch.

---

## 🔟 How the Rules Are Checked

The rules exist once, in `schemas/architecture_rules.v1.json` (validated by its `.schema.json`), and
everything that enforces them reads that file, so the reviewer's prompt and the deterministic checks
cannot drift apart. Each rule can have up to three checks:

| Check | Run by | Sees | Outcome |
| :--- | :--- | :--- | :--- |
| **Static** | rig, on the diff | Code and IaC as written: a client call inside a transaction callback, a migration that adds and drops | A `features.v1` rule finding with `path:line`; blocks when the rule is blocking |
| **Trace** | rig, on the traces of the targeted test run | What actually executed, through helpers, libraries, and injection: a `CLIENT` span under a `db.transaction` span, an orphaned consumer trace | A rule finding with the `trace_id` and `span_id` as evidence; blocks when the rule is blocking |
| **Lens** | The Reviewer's `architecture` lens | What neither check can decide: whether a split's evidence holds, whether a saga's compensation is correct | An advisory finding, or an escalation for a protected class; never a block |

- **Only the rules that apply reach the prompt.** rig records what a unit touches
  (`features.v1` `structure.touches`: a transaction, a migration, a queue publish); the lens rubric
  is generated from the `lens.ask` of the matching rules, never hand-written. Rule hits rig already
  reported go in as known findings, so the model spends tokens only on what the checks leave.
- **Trace checks need the conventions.** They read OpenTelemetry semantic-convention attributes and
  the platform spans and attributes listed in the rules file (`db.transaction`, `outbox.relay`,
  `app.timeout_ms`, and the others), which the shared `traced()` wrapper emits. These names are
  telemetry contracts. A span missing an attribute a check needs is reported as **unverifiable**,
  never counted as compliant.
- **A trace shows only what ran.** Review runs record every span (no sampling), and a path no test
  reached has no trace evidence, so trace checks add to static checks and never replace them. Run
  against sampled staging traces, the same checks report drift findings and "not observed", never
  "compliant".
- **A check counts once it is proven.** Each check moves from `specified` to `implemented` to
  `golden_tested`: it passes fixtures that must pass and fixtures designed to fail, the same
  evidence rule as any verification (`AGENTS.md` → Observability Rules).

---

## Principle

Decide the shape of a service once, write it down, and give it to every builder, human or agent.
Split only on evidence, let each service own its data, and never change a contract, a schema, or a
message in one step that breaks whoever is on the other side.
