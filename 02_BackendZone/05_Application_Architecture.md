# Application Architecture

*Where business logic is split, where state lives, and how data moves between components, decided
once here so that people and agents stop improvising it per service.*

The rest of the playbook governs the platform every service runs on: identity, guardrails,
pipelines, telemetry. This document governs the services themselves. It matters most for AI agents:
a Builder asked to "add a service with a queue" fills any gap in the rules with its own guess, and
guesses differ every time. The enforceable subset is in `AGENTS.md` → **Application Architecture
Rules**.

---

## 1️⃣ Start as a Modular Monolith

A new system starts as **one deployable with internal module boundaries**, not as a set of services.

- Modules inside the monolith follow the same boundary rules as repositories
  (`00_UniversalStandards/09_Reuse_and_DRY.md`): each module has an internal scope and a declared
  public interface, and modules do not import each other's internals.
- **A module becomes its own service only for a measured reason**, recorded in the change that
  splits it:

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
  other service reads or writes it directly, including "just for reporting".
- **Data crosses boundaries only through contracts**: an API or an event, each versioned. Contracts
  shared across repositories live once in the playbook's `schemas/` and are vendored
  (`00_UniversalStandards/09_Reuse_and_DRY.md` §6).
- Reporting and analytics read from events or a derived store the owner publishes, never from the
  owner's tables.
- The owning service's identity is the only one granted write access to its store
  (`03_InfrastructureZone/02_Security_IAM_Policies.md`).

---

## 3️⃣ Transactions and Connections

- **Keep transactions short.** No network call (another service, a queue publish, an external API)
  happens inside a database transaction; a slow remote call holding a transaction open is how
  connection pools and locks run out.
- **Choose the isolation level deliberately** for each workflow that reads and then writes, and
  record why. The database default is a decision too, not a neutral choice.
- **Size connection pools with Little's Law**: concurrent connections needed is roughly the query
  arrival rate times P99 query duration, the same reasoning as a Governor
  (`docs/PHYSICS_OF_FLOW.md`). The pool is a Governor: bounded, with a wait timeout, observable.

---

## 4️⃣ Schema Changes: Expand, Then Contract

Database schemas change with the same sequencing as module refactors
(`00_UniversalStandards/06_Module_Refactor_Framework.md`): never break readers and writers in one
step.

| Step | Change | Safe because |
| :--- | :--- | :--- |
| **1. Expand** | Add the new column, table, or index; nullable or with a default | Old code ignores it |
| **2. Dual write** | Code writes both the old and the new shape | Either shape is complete |
| **3. Backfill** | Fill the new shape for existing rows, in bounded batches | Batches respect the Governor; resumable |
| **4. Switch reads** | Code reads the new shape | The old shape still exists for rollback |
| **5. Contract** | Stop writing, then drop the old shape | Only after the previous step has run cleanly in production |

- Each step is its own change, deployable and reversible on its own.
- **Step 5 is irreversible**: it is the `irreversible` protected class in
  `00_UniversalStandards/10_Autonomy_by_Evidence.md`, so a person approves it at every autonomy
  level, after confirming a backup exists.
- Migrations run through the pipeline, never by hand against a live database.

---

## 5️⃣ Reliable Events: the Transactional Outbox

"Write to the database, then publish the event" loses events when the process dies between the two,
and "publish, then write" announces things that never happened.

- **Outbox:** the service writes the business change **and** the event into an outbox table in the
  **same transaction**. A relay publishes outbox rows to the queue and marks them sent.
- **Inbox:** consumers record the IDs of events they have processed, in the same transaction as
  their own write, so a redelivered event changes nothing (the idempotency rule in
  `02_BackendZone/02_Async_Processing.md`).
- **Multi-service workflows use sagas**, not distributed transactions: each step commits locally and
  publishes an event; each step has a defined **compensating action** that undoes it if a later step
  fails. Two-phase commit across services is not used.

---

## 6️⃣ Queue Topology

Every queue or topic documents, next to its schema:

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
  hold the caller.
- **Retries only for idempotent operations**, with exponential backoff and jitter and a retry
  budget; non-idempotent writes carry an **idempotency key** so a retried request is applied once.
- **Pagination** on every list endpoint; no unbounded responses.
- APIs are versioned contracts (`02_BackendZone/01_API_Architecture.md`); a breaking change ships a
  new version next to the old one, the expand-then-contract pattern again.

---

## 8️⃣ Caching

- **Cache-aside by default**, with an explicit TTL and an invalidation path for every cached item.
- **Never cache an authorization decision** longer than the credential it was based on (one hour at
  most, `00_UniversalStandards/07_Security_In_Depth.md`), and never share one user's cached
  authorization with another.
- Protect hot keys against stampedes (request coalescing or early refresh).
- A cache is an optimization: the service stays correct, if slower, when the cache is empty or down.

---

## 9️⃣ What Vended Services Get

Services vended by Genesis (`00_UniversalStandards/08_Governance_Guardrails.md` §8) start from a
template that already contains these decisions: a module layout with declared boundaries, its own
data store and identity, the outbox and inbox tables, a Governor-bounded consumer, trace propagation
in message headers, and timeouts and retries on its HTTP client. The Builder extends the template;
it does not design these from scratch.

---

## Principle

Decide the shape of a service once, write it down, and give it to every builder, human or agent.
Split only on evidence, let each service own its data, and never change a contract, a schema, or a
message in one step that breaks whoever is on the other side.
