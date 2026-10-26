# Review Loop

*The Builder and the Reviewer talk through the same event backbone as intake: events that point to
verified objects, on queues, in both directions.*

**Status: design.** This is the agreed target for the review loop; it is not implemented yet. Today
the Builder and the Reviewer still exchange work through the pull request directly.

After intake (`06_AgentZone/03_Software_Factory_Intake.md`), the Builder works from an approved spec
and opens a pull request. Every handoff between the Builder and the Reviewer from then on is an event
on the backbone, never a direct call. The contract is `schemas/review_event.v1.schema.json`; the
object references use `schemas/claim_check.v1.schema.json`; the round rules stay those of
`06_AgentZone/01_Agent_Standards.md` §7.

---

## 1️⃣ One Round

| Step | Producer | Event | Object in the store | Consumer |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Builder, after the PR's gates pass | `review.requested` | The review request: the change (repo, PR, exact head commit), the task and spec version it implements, the round, and the previous round's findings | Reviewer's queue |
| 2 | Reviewer, when the round's review is done | `review.completed` | The round's `review_findings.v1` document | Builder's queue, audit |
| 3 | Builder, if blocking findings remain | (pushes a fix to the same PR) then `review.requested` for the next round | The new request | Reviewer's queue |

The PR stays where people see the work: the Reviewer mirrors each round's findings into one combined
PR comment, as Jira mirrors a spec's review. The event log is the record of the loop.

## 2️⃣ Rules

- **The request is data, never the Reviewer's prompt.** The Builder describes what changed; the
  Reviewer builds its own prompt from its versioned prompt files and the playbook's lens rubrics
  (`06_AgentZone/04_Review_Lenses.md`), with the request delimited as untrusted input. A Builder that
  could write the Reviewer's instructions could steer its own review.
- **Code is pinned by commit, not copied.** The request names the PR's head SHA; the Reviewer reads
  the code at that commit from the repository. A push to the PR is a new head SHA and a new round.
- **Objects are claim checks.** Both events reference their object by URI and SHA-256; the consumer
  verifies the digest before use and dead-letters a mismatch (`ARCH-024`).
- **Rounds stay bounded.** `round` runs 1 to 4. Only blocking findings and deterministic DRY findings
  start another round; a stalled or oscillating round escalates to a person before round 4.
- **Escalation is a label, not a message.** `review.completed` carries the labels that require a
  person (for example a protected-class lens finding); the notification service routes them. Agents
  never notify people directly.
- **Idempotent on both sides.** Each consumer records `event_id` in its inbox, so a redelivered
  `review.requested` does not run a second review and a redelivered `review.completed` does not
  start a second fix.
- **Each side has its own identity and its own queue.** Only the Builder may publish
  `review.requested`, and only the Reviewer may publish `review.completed`. Neither reads the
  other's queue.

## 3️⃣ Triage and Rollback

Because every handoff is an event and every object is kept, an incident can be walked back to its
origin, each step pinned to an exact version:

1. The deployed artifact digest leads to the release token that authorized it
   (`06_AgentZone/02_Compliance_Engine.md`).
2. The token leads to the evaluation record and the evidence that passed.
3. The evaluation leads to the pull request and the exact commit built.
4. The commit leads to every review round: what the Builder asked, what the Reviewer found, and
   what changed in response.
5. The task leads to the approved spec version, and the spec to the architect's answers and the
   deep-dive findings.

- **The object store is the history; the event stream is the delivery.** The stream keeps events
  for days. The object store keeps every spec version, review request, and findings document as a
  versioned, write-locked object for at least the triage window; lifecycle rules never delete
  inside it. An archive of the event log (the data lake) keeps the sequence.
- **Prompts are reconstructable.** Next to each request and findings object, the store keeps the
  prompt file version, the lens rubrics, the model and rung, and references to the inputs, so the
  exact exchange can be rebuilt. Raw prompt text is not stored by default, because code and
  occasionally secrets end up in prompts; storing it needs redaction and a classification decision.
- **Metrics, logs, and traces line up.** Trace context crosses every queue, and every log line
  carries `trace_id`, so one incident's signals join on one trace.
- **Rollback is authorized too.** The compliance authority signs only for a fresh evaluation, so a
  rollback to the last known-good digest needs its own rule: reuse that version's earlier passing
  evaluation within a set window, or take an emergency path with a person's approval. Which one is
  an open decision.

## 4️⃣ Where This Sits

| Path | Events | Direction |
| :--- | :--- | :--- |
| Intake | `spec.submitted`, `spec.approved`, `spec.rejected` | Ingress: work enters the factory |
| Review loop | `review.requested`, `review.completed` | Inside the factory, between Builder and Reviewer |
| Domain events | `delivery.events`, `cost.events`, `audit.events`, and the others | Egress: consuming domains |

Merges still need a person's approval through branch protection; the loop ends at no blocking
findings, and the merge is a separate, human-approved step.

---

## Principle

Hand off work through events that point to verified objects, let each agent build its own
instructions, and keep every round bounded, idempotent, and on the record.
