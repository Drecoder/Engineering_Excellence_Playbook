# Messaging Building Blocks

*Five reusable modules carry every event in the factory: an object store, an event stream, a
bridge, a fan-out topic, and a work queue.*

Genesis provides these as modules, built by the platform's agent loop, so no service hand-builds
its own messaging. Services wire them together through Terragrunt `dependency` blocks. The flow they
serve is `06_AgentZone/03_Software_Factory_Intake.md`; the queue rules they enforce are `ARCH-014` to
`ARCH-016` and `ARCH-024` (`02_BackendZone/05_Application_Architecture.md`).

---

## 1️⃣ The Blocks

| Block | AWS | GCP | Azure | Role |
| :--- | :--- | :--- | :--- | :--- |
| **Object store** | S3 | Cloud Storage | Blob Storage | Holds claim-check objects (specs, artifacts, reports) by ID and version |
| **Event stream** | Amazon MSK (Kafka) | Managed Service for Apache Kafka | Event Hubs (Kafka API) | Durable, replayable source of truth for domain events |
| **Bridge** | EventBridge Pipes | Kafka Connect / Pub/Sub connector | Event Grid or a connector | Forwards stream events to the fan-out topic without custom code |
| **Fan-out topic** | SNS | Pub/Sub topic | Service Bus topic | Delivers each event to every subscribed consumer |
| **Work queue** | SQS with a dead-letter queue | Pub/Sub subscription with a dead-letter topic | Service Bus subscription with dead-lettering | One per consumer; where work is pulled from |

AWS is built first; the GCP and Azure modules follow the same inputs and outputs, so a service
moves between clouds without changing how it wires its messaging.

## 2️⃣ What Every Block Must Do

| Requirement | Why |
| :--- | :--- |
| **Encrypted** with a customer-managed key, at rest and in transit (TLS 1.2+) | `07_Security_In_Depth.md` |
| **Private**: no public endpoint; Kafka in private subnets from the networking module | Least exposure |
| **Identity-based access only**: IAM or workload identity per producer and consumer, no static credentials; topic and queue policies name exactly who may publish | Only the approval service may publish `spec.approved`, for example |
| **Labelled** `owner`, `service`, `unit_class` | Cost allocation and sweeping (`AP-COST-001`) |
| **Observable**: dead-letter depth, age of the oldest message, consumer lag, and publish errors as metrics with alerts | A stuck queue is found by an alert, not by a person looking |

## 3️⃣ Block-Specific Rules

- **Object store:** versioning on; object lock (write-once) for objects that are approved or
  audited, such as specs, review requests, and findings; public access blocked; access logging on.
  It is the factory's long-term history, not a cache: the history is kept for at least the triage
  window, hot or archived (§3a), and lifecycle rules delete only drafts and originals already
  sealed into a verified bundle. Consumers verify an object's SHA-256 against the event that
  referenced it (`ARCH-024`).
- **Event stream:** retention long enough to replay a fixed consumer (at least 7 days); topics
  per domain (`spec.events`, `workflow.events` for the review loop, `delivery.events`, and the
  others); IAM authentication and TLS only. Topic creation is part of the module, not done by hand.
- **Fan-out topic:** subscriptions use filter policies so each queue receives only the event types
  it consumes; per-key ordering (FIFO) only where a consumer needs it, keyed by the entity ID.
- **Work queue:** a dead-letter queue after a bounded number of receives; a visibility timeout
  longer than the consumer's processing time; the queue policy accepts messages only from its
  fan-out topic (`ARCH-014`).

## 3️⃣a Object Store Tiering

**Status: design.** Most stored objects are read again only during triage, so only recent
deployments stay in standard storage.

| Tier | Holds | Storage | Read back |
| :--- | :--- | :--- | :--- |
| **Hot** | Every object of a service's last *N* deployments (the rollback targets) | Standard | Milliseconds |
| **Archive** | One sealed bundle per older deployment | An archive class (AWS Glacier Deep Archive or Glacier Instant Retrieval; GCP Archive; Azure Archive) | Hours for the deepest classes; restore before triage |

- **The hot set is counted in deployments, not days.** Lifecycle rules only see object age, so the
  deploy pipeline does the counting: when a deployment becomes current, the step marks the
  deployment that fell out of the last *N* (for example by tagging its objects), and a lifecycle
  rule on that mark moves it. A rollback target is therefore always hot.
- **Bundle before archiving.** Specs, review requests, and findings are a few kilobytes each, and
  archive classes charge per object (minimum billable sizes, per-object overhead, transition
  requests); archiving them one by one can cost more than leaving them in standard storage. When
  a deployment leaves the hot set, its objects are packed into one bundle with a manifest listing
  every object's key, version, and SHA-256, and the bundle's own digest is recorded as an event.
  Triage restores one bundle and still verifies every object in it.
- **Lock the bundle for the triage window; lock originals only while hot.** Originals are
  write-locked for the hot period, so they can be removed once their bundle is verified; the bundle
  is write-locked for the full triage window. The manifest pins every original digest, so the
  history stays tamper-evident while moving to cheaper storage.
- **Transitions are not deletions.** Moving to an archive class keeps the object and its lock;
  respect each class's minimum billed duration so nothing is moved twice inside it.

**Open decisions:**

- *N*, the hot count (2 or 3 deployments per service).
- The triage window, which compliance may set (for example 1 or 7 years).
- The archive class for bundles: the cheapest with a restore of hours, or a costlier one readable
  at once.

## 4️⃣ Cost

A managed Kafka cluster has a fixed monthly floor whether or not events flow, unlike topics and
queues, which cost per use. Estimate it on the plan before choosing a cluster type
(`03_InfrastructureZone/05_Cost.md`), and in development consider whether replay is needed yet or
the fan-out topic and queues are enough until it is.

---

## Principle

Build messaging once, as modules with security, observability, and dead-lettering already in place,
so every service gets reliable events by wiring blocks together rather than reinventing them.
