# Platform Architecture

*A software factory that governs itself: requirements enter as approved specs, agents build and
review inside guardrails, an independent authority decides what ships, and every step is evidence.*

This is the map. It shows how the pieces fit and what state each one is in; the rules for each
piece live in the standard it links to, and `AGENTS.md` is the enforceable subset. Where this page
and a standard disagree, the standard wins and this page is the bug.

**Status legend:** **Built** runs today. **Partial** runs, with named gaps. **Design** is the
agreed target, not implemented. **Open** is an undecided question.
In the drawings (`docs/architecture/`), a solid outline is built, a corner tick is partial, a
dashed outline is design, and red is refused.

---

## 1️⃣ Layers

![System map: the playbook's rules and contracts are vendored into every repo at a full commit SHA; Genesis enforces guardrails in the cloud hierarchy and vends projects; the platform runs network, runners, observability, inference and the CI factory; the factory's agents run on the platform and build services.](docs/architecture/sheet-1-system-map.svg)

- **The playbook defines; nothing below it invents rules.** Genesis implements the guardrails the
  baseline names (`00_UniversalStandards/08_Governance_Guardrails.md`); services never create,
  change, or except an org policy or SCP.
- **Contracts have one home** (`schemas/`), vendored byte-identical; across languages the platform
  shares the spec and test vectors, not code (`00_UniversalStandards/09_Reuse_and_DRY.md`,
  `05_Standards_Distribution.md`).

## 2️⃣ Components

| Component | Repo | Role | Status |
| :--- | :--- | :--- | :--- |
| Engineering Excellence Playbook | `Engineering_Excellence_Playbook` | Standards, `AGENTS.md`, contracts, anti-pattern catalog, textbook | **Built** |
| Genesis | `Genesis` | Governance hierarchy, `GOV-*` enforcement per cloud, vending | **Partial**: GCP conformance plan (M1) in review; built by the agent loop, never by hand |
| Platform network, state, identity | `sovereign-vpc-gcp` (`modules/network`, `state`, `identity`) | Shell VPC, encrypted versioned state, federated identities | **Built** (dev) |
| CI runners | `sovereign-vpc-gcp` (`modules/runners`) | Self-hosted runners for plan jobs | **Built** (dev) |
| Observability | `sovereign-vpc-gcp` (`modules/observability`) | OTLP collector, metrics, alerts | **Built** (dev) |
| Inference | `sovereign-vpc-gcp` (`modules/inference`) | Self-hosted models (Ollama) for the model ladder, including spot GPU benchmarks | **Partial** |
| Central CI factory | `sovereign-vpc-gcp` (`.github/workflows/gates.yml`) | One reusable workflow running every repo's gates | **Partial**: rework and scanners in review; runner image not digest-pinned |
| rig | `rig` | Deterministic tool: lifts code into evaluation units, static and trace `ARCH-*` checks, features | **Built**; trace checks in review |
| Builder | `aws-builder-agent` | Actor: turns an approved task into a pull request | **Built** (PR-driven); compliance scoping skill **Design** |
| Reviewer | `gcp-reviewer-agent` | Actor: reviews a pull request through lenses | **Built** (PR-driven); Vertex inference in review |
| Intake (wizard, deep dives, grooming) | — | Requirement → approved spec | **Design** |
| Compliance authority and deployment guard | — | Decide and sign releases; consume tokens at deploy | **Design** |
| Messaging backbone | Genesis modules (AWS first) | Object store, event stream, bridge, fan-out, work queues | **Design**: module specs pending for the agent loop |

## 3️⃣ The Path of a Change

![Path of a change: intake to Builder, CI gates and Reviewer (looping for fix rounds), a person approves the merge, then the apply pipeline; the spec lives in an object store fetched by digest; signed CI evidence goes to an independent compliance authority whose single-use token the deployment guard consumes. Every box is its own identity.](docs/architecture/sheet-2-path-of-a-change.svg)

| Stage | Standard | Status |
| :--- | :--- | :--- |
| Questionnaire, deep dives, grooming, approval | `06_AgentZone/03_Software_Factory_Intake.md` | **Design** |
| Build loop, pre-PR gates, failure classification, budgets | `06_AgentZone/01_Agent_Standards.md` §7 | **Built** (PR-driven) |
| CI gates | `00_UniversalStandards/15_Central_CI.md` | **Partial** |
| Review lenses | `06_AgentZone/04_Review_Lenses.md` | **Built**; architecture lens in review |
| Review over events | `06_AgentZone/05_Review_Loop.md` | **Design**: today Builder and Reviewer exchange work through the pull request |
| Merge conflicts: detect, route, resolve, check | `06_AgentZone/06_Merge_Conflicts.md` | **Design**: today a person resolves them, or asks a coding agent to |
| Merge | `AGENTS.md` → Agent Rules, Security Rules | **Built**: human approval via branch protection |
| Evaluation, release token, deploy | `06_AgentZone/02_Compliance_Engine.md` | **Design** |
| Apply | `03_InfrastructureZone/01_IaC_Standards.md` | **Built**: post-merge pipeline with its own identity; agents only plan |

## 4️⃣ Trust Boundaries

Each boundary is its own identity, so no component can approve its own work.

| Boundary | May | May not |
| :--- | :--- | :--- |
| Builder | Read the approved spec, plan, open pull requests, submit evidence, dry-run its compliance scope | Approve a spec, review itself, merge, apply, read the authority's signing key, authorize its release |
| Reviewer | Read the code at the requested commit, publish findings and labels | Take instructions from the review request, push code, merge |
| rig and other tools | Return typed results for typed input | Hold a loop, decide what to do next, apply |
| CI (attester) | Run the gates, sign evidence records | Sign release tokens |
| Compliance authority | Verify evidence, evaluate criteria, sign single-use tokens | Deploy, accept a decision or status from the Builder |
| Deployment guard | Consume a valid token once, deploy the pinned digest | Deploy anything else |
| Apply pipeline | Apply a merged, approved plan | Run on an agent's request |
| People | Approve specs, approve merges to staging and prod, approve exceptions | Bypass branch protection (admins included) |

- **Workloads and agents use short-lived federated identity only**, pinned to repo, branch, and
  environment; cloud credentials live one hour (`00_UniversalStandards/07_Security_In_Depth.md`).
- **Agents never notify people;** they set labels, and a notification service routes them.

## 5️⃣ Data and Messaging

- **Claim check.** Specs, review requests, findings, and artifacts are objects in a versioned,
  write-locked, encrypted object store. Events carry only the ID, URI, and SHA-256, and every
  consumer verifies the digest before use (`ARCH-024`, `schemas/claim_check.v1.schema.json`).
- **The object store is the history; the event stream only delivers.** The stream keeps events for
  days; the store keeps every version for at least the triage window. Older deployments move to one
  sealed bundle each in archive storage (**Design**, `03_InfrastructureZone/06_Messaging_Building_Blocks.md` §3a).
- **The path.** Producer outbox → event stream (Kafka) → bridge → fan-out topic → one work queue per
  consumer, with a dead-letter queue; consumers are idempotent by `event_id`
  (`02_BackendZone/05_Application_Architecture.md`).
- **Ingress, internal, egress** share the backbone: `spec.*` events bring work in, `review.*` events
  run the loop, and domain events (delivery, cost, audit) go out to consuming domains.
- **AWS first** (S3, MSK, EventBridge Pipes, SNS, SQS); GCP and Azure modules keep the same inputs
  and outputs.

## 6️⃣ Models

- **A ladder, not a tier.** Rules and a complexity assessor produce a difficulty score that selects
  the cheapest model rung that fits; unknown or low-confidence routing takes the top rung
  (`06_AgentZone/01_Agent_Standards.md` §6, `schemas/model_ladder.v1.json`).
- **Providers are injected.** Local models run on the platform's inference stack; managed models
  (Vertex on GCP) are a configuration choice. **Partial:** the shared ladder lists local model IDs
  only, so a managed provider needs its own rung IDs.
- **Model output is a claim.** It enters evidence at tier `CLAIMED`; only a measurement or a signed
  tool result is `VERIFIED`. A model's verdict never overrides a failing deterministic gate.
- **No secrets in context;** prompts are versioned files, and untrusted input is delimited as data.

## 7️⃣ CI and Supply Chain

![CI factory: consumer repos call one gates.yml at a full commit SHA with inputs; it detects stacks, runs per-stack jobs and scanners, and routes every scanner report through a severity gate that blocks only CRITICAL or CISA KEV and fails closed, reading OSV, KEV and the caller's reviewed exceptions. Genesis cannot call it: public cannot call private.](docs/architecture/sheet-3-ci-factory.svg)

- **One factory:** every repo's gates run in one reusable workflow, called by full commit SHA and
  configured through inputs; vulnerability scanners block only on CRITICAL or CISA KEV through one
  shared gate that fails closed (`00_UniversalStandards/15_Central_CI.md`).
- **Pin everything:** packages by lockfile, images by digest, downloads by checksum, actions by SHA;
  released artifacts carry an SBOM and a keyless pipeline signature (`13_Supply_Chain.md`).
- **Everything runs in a pinned container,** the same locally and in CI (`12_Containers.md`).
  **Gap:** the CI factory still runs on the runner image.

## 8️⃣ Observability and Evidence

- Every service and agent emits traces, metrics, and logs over OTLP from the first line of code;
  logs carry `trace_id`, and trace context crosses every queue
  (`02_BackendZone/04_Telemetry_Standards.md`).
- **Evidence is telemetry:** a verification result counts only as a span, a structured log line,
  and a metric, never only as a file.
- **Triage walks back from the deployed digest:** token → evaluation → commit → review rounds → spec
  version → the architect's answers (`06_AgentZone/05_Review_Loop.md` §3).
- Every failure and near miss gets an incident record in the affected repo.

## 9️⃣ Autonomy

People leave a process step only on evidence: a process class moves one level at a time (L0 manual
to L4 unattended) when it is in statistical control and meets its defect-rate target. Security,
ethics, irreversible changes, and merges to staging and production are protected classes and never
pass L2 (`00_UniversalStandards/10_Autonomy_by_Evidence.md`).

## 🔟 Open Decisions

| Decision | Where it is tracked |
| :--- | :--- |
| Deep dives as a Builder mode or a separate analyst role | `06_AgentZone/03_Software_Factory_Intake.md` §6 |
| Two-person rule (architect ≠ reviewer) | `06_AgentZone/03_Software_Factory_Intake.md` §6 |
| Where a spec is decomposed into Builder tasks | `06_AgentZone/03_Software_Factory_Intake.md` §6 |
| How a rollback is authorized | `06_AgentZone/05_Review_Loop.md` §3 |
| Hot window N, triage window, and archive class | `03_InfrastructureZone/06_Messaging_Building_Blocks.md` §3a |
| Event stream cost in development | `03_InfrastructureZone/06_Messaging_Building_Blocks.md` §4 |
| Public repos and the private CI factory | `00_UniversalStandards/15_Central_CI.md` §8 |

---

## Principle

Define once in the playbook, enforce in the cloud, build inside the guardrails, let no component
approve its own work, and keep every step as evidence someone can walk back.
