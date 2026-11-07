# Service Design Record

*A service declares its numbers, its promises, and its data rules before it is built, in one record
that people, the Builder, the Reviewer and the gate can all check the same way.*

The Design stage of the lifecycle (`01_Deliverable_Lifecycle.md`) asks for contracts and SLOs. This
standard says what that means in data: the capacity a service is designed for, how its reliability
is measured and promised, how much data it may lose and how long it may be down, and what each of
its stores must guarantee. The record is `schemas/service_design_record.v1.schema.json`; an example
for the orchestrator is `schemas/examples/service_design_record.v1.example.json`.

**Status: specified.** The schemas, the class table, the versioned rule set and its vectors exist
and are tested. Nothing consumes them yet: the Design exit gate check, the Builder's intake check and
the architecture lens's use of the record are still to be built. Until then a record is reviewed by a
person against §6.

---

## 1️⃣ One Record, Separate Definitions

The record defines nothing itself. It references separate, versioned definitions and binds them to
one service:

| Definition | Schema | What it holds |
| :--- | :--- | :--- |
| Capacity estimate | `capacity_estimate.v1` | Arrival rate, P99 target, in-flight load, payload size, round trips, fan-out, read/write ratio, latency or bandwidth bound, serial point, hottest key, monthly cost and egress (§4) |
| Service level indicators | `sli.v1` | Good events over valid events, and every way an event counts as bad (§2) |
| Service level objectives | `slo.v1` | A target and window for one SLI, and its burn-rate alerts (§2) |
| Recovery objectives | `recovery_objectives.v1` | RTO, RPO, the failover path, and the failure scenarios the service must survive (§3) |
| Data classes | `data_class.v1`, table in `schemas/data_classes.v1.json` | What each class of data requires of the store that holds it (§5) |

Each definition carries its own `schema_version` and can be validated alone, so a later version of
one does not force a new version of the others. The record adds only what ties them together: the
service, its owner, its stores and the class each one uses, and its concurrency limit. What JSON
Schema cannot check across definitions is checked by the relationship rules (§6).

## 2️⃣ SLIs and SLOs

- **An SLI is good events over valid events.** Both are queries over the service's own metrics.
- **Name every way an event is bad,** not only server errors: a response slower than a threshold, a
  wrong or empty result, missing data. Counting only 5xx makes slow or silently wrong answers look
  like successes. A latency SLI must name its threshold.
- **Every service has an availability SLO and a latency SLO** (DR-004), each with a paging and a
  ticketing burn-rate alert, as the alerting policy requires
  (`04_OperationalRunbooks/02_Monitoring_Alert_Thresholds.md` §2).
- **An SLO is stricter than any promise made outside the team** (DR-005), so the team hears about a
  problem before a customer contract is broken.

## 3️⃣ Recovery Objectives

- **RPO** is the most recent window of acknowledged writes the service may lose; **RTO** is the
  longest it may be unavailable.
- **Replication is not a backup.** It copies a bad write or a delete to every replica, so every store
  whose class requires a backup declares one (DR-009).
- **The RPO is checked against the worst-case recovery point** (DR-010): the backup interval plus the
  time until a backup is restorable, and the lag of any asynchronous replica a failover could
  promote. An RPO of 0 needs continuous backup and synchronous replication. The rule checks the design;
  whether backups complete on time and restores work is shown by backup monitoring and restore tests.
- **The failover scope sets placement.** A service that must survive losing a region keeps its
  backed-up stores in more than one region (DR-011).
- **Availability is checked against failure scenarios, not the RTO alone.** The record lists the
  failures the service is designed to survive (zone or region loss, a dependency outage, a bad change,
  data corruption, overload), how often each is expected, and how long each takes it down. No scenario
  may take longer than the RTO (DR-019), and their expected downtime must fit every availability SLO's
  error budget (DR-020). The rates are estimates; correct them from the incident history.
- **One outage must fit the error budget** (DR-006). This is a floor: a target that cannot survive
  one recovery is not a real target, but passing it says nothing about how often recovery is needed.

## 4️⃣ Capacity Estimate

The estimate is the input to the playbook's physics (`docs/PHYSICS_OF_FLOW.md`), written before the
service exists instead of measured after it fails:

- **In-flight load follows Little's Law:** at least peak arrival rate times P99 latency, rounded up
  (DR-014), and the declared concurrency holds it (DR-015). For a serverless consumer the concurrency
  is the platform's cap on the trigger, not a per-instance Governor.
- **Round trips and fan-out are counted,** because each remote call costs distance and each parallel
  call adds its tail to the caller's.
- **The workload is latency-bound or bandwidth-bound,** with the lever the design relies on; the two
  need opposite fixes.
- **The serial point is named:** the single leader, lock or hot row every request passes through.
- **Cost includes egress** (DR-017 checks the total covers its parts).

## 5️⃣ Data Classes

`schemas/data_classes.v1.json` is the playbook-wide table. A store names one class, and the class
sets the minimum the store must meet:

| Class | Losing it means | Write acknowledged | Copies, placement | Backup | Consistency | Caching |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ephemeral` | Nothing | Not waited on | 1, one zone | No | Eventual | Any |
| `rebuildable` | A rebuild from the source | In memory | 1, one zone | No | Eventual, ≤ 300 s stale | Any |
| `business_record` | A customer-visible defect | On disk | 2, two zones, synchronous | Yes | Read your writes, ≤ 5 s stale | Cache-aside only |
| `audit_ledger` | A broken guarantee: money, approvals, evidence | On a quorum | 3, two zones, synchronous | Yes | Strong | Never |
| `coordination` | Two holders acting at once | On a quorum | 3, two zones, synchronous | No | Strong | Never |

- **Value data needs a strong class.** A store holding records that break a guarantee if lost or
  misread (money, approvals, release tokens, leases, ledgers) uses `audit_ledger` or `coordination`
  (DR-012).
- **A cache inherits the rules of what it caches:** only the modes that class allows, and a TTL no
  longer than its staleness bound (DR-013). Write-back caching is allowed only for classes that can
  lose recent writes.
- **When a buffer fills,** `ephemeral` and `rebuildable` producers may drop; the others reject with a
  retry signal. Blocking a user's request is never allowed.
- **The table changes by review,** like any contract. Adding a class is additive; tightening a class
  is a breaking change for every store that uses it.

## 6️⃣ Relationship Rules

The rules are a versioned rule set, `schemas/design_record_rules.v1.json`, and a record names the set
it is checked against (`rules_version`). A consumer refuses a record naming a set it does not
implement, so the gate, the Builder and the Reviewer can never apply different readings of the same
record. Changing what a rule checks is a new rule set version, never an edit. Each rule states what it
checks and, where it matters, what it cannot establish.

The reference behavior is `tests/contracts/design_record_reference.py`, and every consumer must
reproduce `schemas/examples/design_record/relationship_vectors.json`, which has at least one vector
that fails each rule alone.

| Rule | Checks |
| :--- | :--- |
| `DR-001` | Every component names the record's service |
| `DR-002` | SLI ids are unique and SLO ids are unique |
| `DR-003` | Every SLO names an SLI in the record |
| `DR-004` | There is an availability SLO and a latency SLO |
| `DR-005` | An SLO target is strictly higher than its external commitment |
| `DR-006` | One outage lasting the RTO fits inside every SLO's error budget (a floor, not proof the target is achievable) |
| `DR-007` | Every store, and every cache's cached class, names a class in the table |
| `DR-008` | Every store meets its class's minimum copies, placement and replication |
| `DR-009` | A store whose class requires backup declares its backup |
| `DR-010` | Every backed-up store's worst-case recovery point is no longer than the RPO |
| `DR-011` | A region-scoped failover places every backed-up store in more than one region |
| `DR-012` | A store holding value data uses a strongly consistent class |
| `DR-013` | A cache uses a mode its cached class allows and a TTL within its staleness bound |
| `DR-014` | In-flight load at peak covers Little's Law |
| `DR-015` | Declared concurrency holds the in-flight load at peak |
| `DR-016` | Mean arrival rate does not exceed peak |
| `DR-017` | Total monthly cost is at least the sum of its parts |
| `DR-018` | Class ids in the table are unique |
| `DR-019` | No failure scenario's downtime is longer than the RTO |
| `DR-020` | Expected downtime from the failure scenarios fits every availability SLO's error budget |

---

## Principle

Decide the numbers, the promises and the data rules before building, write them where a machine can
check them, and check them the same way everywhere.
