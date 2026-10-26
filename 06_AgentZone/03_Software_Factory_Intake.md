# Software Factory Intake

*Work enters the factory as an approved spec, carried by events, never by a person handing a file
to an agent.*

Intake is the factory's **ingress**: how a requirement becomes an approved spec and reaches the
Builder. **Egress** is the other direction: the domain events the factory publishes for consuming
domains (finance, cost management, operations, governance, analytics). Both run on the same event
backbone; this document covers ingress. The message contract is `schemas/spec_event.v1.schema.json`;
the infrastructure is `03_InfrastructureZone/06_Messaging_Building_Blocks.md`.

---

## 1️⃣ The Flow

| Step | Who | What happens |
| :--- | :--- | :--- |
| **1. Questionnaire** | The architect, through the intake wizard | Answers a structured questionnaire. The questions come from the criteria the work must satisfy (the compliance registry and the `ARCH-*` rules that apply to what the work touches), never from a hand-written list |
| **2. Deep dives** | An agent with read-only tools (the Builder's model ladder) | Researches what the answers leave open: existing code (rig's symbol index), constraints, cost, risk. Every finding is attached as evidence with its source |
| **3. Grooming** | The intake pipeline | Raw answers become a complete spec through the stages in §2; gaps go back to the architect as new questions |
| **4. Review** | People, on the Jira board | The spec is published (`spec.submitted`) and reviewed; it is approved or rejected with a reason |
| **5. Approval** | The approval service | A verified approval becomes a `spec.approved` event on the backbone |
| **6. Build** | The Builder | Receives the event from its queue, fetches the spec object, verifies its digest, and only then starts work |

## 2️⃣ Grooming Stages

Grooming follows the platform's medallion layering:

| Layer | Contents | Leaves the layer when |
| :--- | :--- | :--- |
| **Bronze** | Raw wizard answers and deep-dive notes, kept as written, with author and time | Always kept; never edited |
| **Silver** | Answers normalized against the spec schema, deduplicated, and enriched: cost estimate (infrastructure and model tokens), existing-system context, the criteria and evidence tiers each requirement needs | Every mandatory question is answered and the estimate is within budget |
| **Gold** | The assembled spec document: versioned, complete against the registry, ready for review | It is published for review |

**Evidence from a model is a claim.** A deep-dive finding enters at tier `CLAIMED`; the architect
confirming it raises it to `OBSERVED`; only a measurement or a signed tool result reaches `VERIFIED`
(`06_AgentZone/02_Compliance_Engine.md`). Model output never counts as proof on its own.

## 3️⃣ Claim Check: Objects Travel by Reference

- **The spec is an object, stored once.** Each spec version is written to the spec object store
  (S3 or its equivalent) under its spec ID and version: versioned, write-once after approval (object
  lock), encrypted with a customer-managed key, public access blocked, access-logged. Only the intake
  service writes; the Builder reads.
- **Events carry the reference, not the document:** the spec ID and version, the object URI, the
  object's SHA-256, the event ID (the idempotency key), and for approvals the review reference and
  approver (`spec_event.v1`). Queues have size limits and replay copies every byte; a reference does
  not.
- **Consumers verify before use.** A consumer fetches the object and checks its digest against the
  event; a mismatch, a missing object, or an unreadable one is refused, sent to the dead-letter queue,
  and recorded as an incident (`ARCH-024`).

## 4️⃣ The Event Path

1. The producing service writes the event through its **outbox** (`ARCH-011`); the relay publishes
   to the **event stream** (Kafka), the durable, replayable source of truth.
2. A **bridge** forwards the stream's events to a **fan-out topic** (SNS or equivalent).
3. Each consumer has its own **work queue** (SQS or equivalent), subscribed with a filter for the
   event types it needs, a dead-letter queue, and an **inbox** so a redelivered event changes nothing
   (`ARCH-012`, `ARCH-014`).
4. Trace context travels in message headers, so one trace follows a spec from questionnaire to build
   (`ARCH-015`).

| Event | Produced by | Consumed by |
| :--- | :--- | :--- |
| `spec.submitted` | Intake service, when a Gold spec is ready | Jira sync (creates or updates the review issue), audit |
| `spec.approved` | Approval service, after a verified approval | Builder intake, audit, cost (estimate baseline) |
| `spec.rejected` | Approval service | Intake (reopens the questionnaire with the reason), audit |

## 5️⃣ Approval Is Bound to the Spec

- **The event log is the system of record;** Jira is where people review. A Jira webhook is
  signature-verified before the approval service acts on it (`00_UniversalStandards/07_Security_In_Depth.md`).
- **An approval names one exact spec version and its digest.** The Builder starts work only from a
  `spec.approved` event whose object digest verifies; a spec changed after approval is a new version
  that needs its own approval. The same binding protects releases: the compliance authority's token
  names the exact artifact that passed.
- **Only the approval service's identity may publish `spec.approved`;** the Builder can read the spec
  store and its queue, and nothing else on this path.

## 6️⃣ Open Decisions

Recorded here until decided, each by a reviewed change to this document:

- Whether deep dives stay a read-only mode of the Builder or become a separate analyst role.
- Whether the reviewer must be a different person from the architect (a two-person rule).
- Where an approved spec is decomposed into Builder tasks (`builder.spec.v1`): before review, so
  reviewers approve the breakdown, or after.

---

## Principle

Let the architect decide, let agents research and assemble, let people approve one exact version,
and move work through the factory as events that point to verified objects.
