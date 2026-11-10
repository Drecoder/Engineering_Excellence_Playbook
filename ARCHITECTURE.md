# Platform Architecture

*A software factory that governs itself: requirements enter as approved specs, the Builder builds
inside guardrails, CI evaluates every change, the owner approves the merge, an independent authority
decides what ships, and every step is evidence.*

This is the map. It shows how the pieces fit and what state each one is in; the rules for each
piece live in the standard it links to, and `AGENTS.md` is the enforceable subset. Where this page
and a standard disagree, the standard wins and this page is the bug. The factory's repositories and
how they work with one another are the playbook's capstone,
`07_SoftwareFactory/01_Software_Factory.md`.

**Status legend:** **Built** runs today. **Partial** runs, with named gaps. **Design** is the
agreed target, not implemented. **Open** is an undecided question.
In the drawings (`docs/architecture/`), a solid outline is built, a corner tick is partial, a
dashed outline is design, and red is refused.

---

## 1️⃣ Layers

![System map: the playbook's rules and contracts are vendored into every repo at a full commit SHA; Genesis enforces guardrails in the cloud hierarchy and vends projects; the platform runs network, runners, observability, inference and the CI factory, which holds the acceptance tests, the Evaluator and the Policy Engine; in the factory a thin orchestrator hands one ticket to the Builder, CI evaluates its change, and the owner approves the merge.](docs/architecture/sheet-1-system-map.svg)

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
| Central CI factory | `sovereign-vpc-gcp` (`.github/workflows/gates.yml`) | One reusable workflow running every repo's gates, including the acceptance tests and the Policy Engine | **Partial**: rework and scanners in review; runner image not digest-pinned; the Policy Engine is not wired in (KAN-43) |
| rig | `rig` | Deterministic tool: static and trace `ARCH-*` checks and features for the Builder's pre-PR scan | **Built**; trace checks in review |
| Builder | `aws-builder-agent` | Actor: turns an approved task into a pull request | **Built** (PR-driven); compliance scoping skill **Design** |
| Orchestrator | `factory-orchestrator` | Leases one ticket, hands the Builder the spec, reads the CI result, bounces up to the attempt limit, stops at the budget | **Partial** (KAN-14): decision logic and fenced lease pass on in-memory fakes (#2 merged; fence fix in review, #3); no Jira, DynamoDB or GitHub adapters, no telemetry, not deployed |
| Quality evaluator and Policy Engine | — | Run in CI: normalize tool output to `quality_metrics.v1`, then decide PASS, BLOCK or QUARANTINE (`00_UniversalStandards/17_Quality_Policy_Engine.md`) | **Design**: reference engine and 54 vectors specified; service not built (KAN-18, KAN-41) |
| Intake (wizard, deep dives, grooming) | — | Requirement → approved spec | **Design** |
| Compliance authority and deployment guard | `compliance-authority` | Decide and sign releases; consume tokens at deploy | **Partial**: CLI with local stores and keys; no network API, not in the deploy path |
| Agent notepad | `agent-notepad` | Working memory for every agent and task | **Partial**: library with in-memory and local file backends |
| Adaptive harness | — | Picks an agent's next bounded step from knowledge, reliability states, quality evidence and governance state (`06_AgentZone/09_Adaptive_Harness.md`) | **Design**: proposed standard; contracts specified |
| CAPA graph and risk-weighted learning | — | Projects the proof journal and CAPA register into a graph, computes risk weights W(N), and (after a protected decision) fine-tunes an agent on its own verified corrections (`06_AgentZone/10_CAPA_Graph_and_Risk_Weighted_Learning.md`) | **Design**: proposed standard; fine-tuning closed |
| Messaging backbone | Genesis modules (AWS first) | Object store, event stream, bridge, fan-out, work queues | **Design**: SNS and SQS with claim checks, in the MVP (KAN-36); module specs pending |

## 3️⃣ The Path of a Change

![Path of a change: the orchestrator hands one ticket's spec to the Builder; CI runs the tests, scanners, acceptance tests and Policy Engine, and a failing report goes back to the Builder (up to 3 attempts within $2.00, then Blocked); on a pass the owner approves the merge, then the apply pipeline; the spec lives in an object store fetched by digest; signed CI evidence goes to an independent compliance authority whose single-use token the deployment guard consumes. Every box is its own identity. Learning loop (design): every attempt goes to a run record; the factory drafts Proof journal and CAPA register entries from QUARANTINE, Blocked, budget, dead-letter and fence refusals for the owner to merge; and the Builder gets prior findings with its spec.](docs/architecture/sheet-2-path-of-a-change.svg)

| Stage | Standard | Status |
| :--- | :--- | :--- |
| Questionnaire, deep dives, grooming, approval | `06_AgentZone/03_Software_Factory_Intake.md` | **Design** |
| Build loop, pre-PR gates, failure classification, budgets | `06_AgentZone/01_Agent_Standards.md` §7 | **Built** (PR-driven) |
| CI gates | `00_UniversalStandards/15_Central_CI.md` | **Partial** |
| Acceptance tests: written before the build, shown to fail first, run in CI | `07_SoftwareFactory/01_Software_Factory.md` §3 | **Design** |
| Policy Engine in CI: PASS, BLOCK or QUARANTINE | `00_UniversalStandards/17_Quality_Policy_Engine.md` | **Design** (KAN-18, KAN-43) |
| Fix loop: the CI report goes back to the Builder, which fixes its own change; 3 attempts, $2.00 per ticket | `07_SoftwareFactory/01_Software_Factory.md` §3 | **Design** (KAN-14, KAN-19); today the Builder fixes through the pull request |
| Merge conflicts: detect, route, resolve, check | `06_AgentZone/06_Merge_Conflicts.md` | **Design**: today a person resolves them, or asks a coding agent to |
| Agent notepad: a folder per agent and task, sealed at each push | `06_AgentZone/07_Agent_Notepad.md` | **Partial**: the service core is built as a library; agents do not use it yet |
| Merge | `AGENTS.md` → Agent Rules, Security Rules | **Gap**: no platform repository's `main` is protected, so human approval holds by habit, not enforcement (`docs/incidents/2026-10-26-INC-001-no-branch-protection.md`) |
| Evaluation, release token, deploy | `06_AgentZone/02_Compliance_Engine.md` | **Partial**: authority and guard built as a CLI; not yet in the deploy path |
| Apply | `03_InfrastructureZone/01_IaC_Standards.md` | **Built**: post-merge pipeline with its own identity; agents only plan |
| Run record: every Builder attempt (spec, transcript, diff, attested CI result, cost), keyed by ticket and lease token | `07_SoftwareFactory/01_Software_Factory.md` §3 | **Design** (KAN-62) |
| Learning loop: the factory drafts Proof journal and CAPA register entries from loop outcomes, the owner merges them, and the Builder reads matching prior findings | `docs/POC_JOURNAL.md`; `07_SoftwareFactory/01_Software_Factory.md` §3 | **Design** (KAN-60): the journal and register are enforced in CI; the factory does not write or read them yet |

**Owner decision, 2026-11-07 (KAN-14):** the Builder and CI loop is the factory, and the owner's
merge approval is its only judgment step. The Reviewer agent, the CRAP and mutation fixers, and
finding sub-tickets are removed. Standards that still describe them (`AGENTS.md` → Agent Rules,
`06_AgentZone/04_Review_Lenses.md`, `06_AgentZone/05_Review_Loop.md`) are pending alignment; until
then, this page and `07_SoftwareFactory/01_Software_Factory.md` record the decision.

## 4️⃣ Trust Boundaries

Each boundary is its own identity, so no component can approve its own work.

| Boundary | May | May not |
| :--- | :--- | :--- |
| Builder | Read the approved spec and its CI report, plan, open pull requests, fix its own change, submit evidence, dry-run its compliance scope | Approve a spec, approve its own change, merge, apply, read the authority's signing key, authorize its release |
| Orchestrator | Lease one approved `factory` ticket, hand the Builder the spec, read the CI result, bounce up to the attempt limit, stop at the budget, move tickets | Edit or judge code, pick up a ticket without the `factory` label, raise a budget, lift a quarantine, merge |
| rig and other tools | Return typed results for typed input | Hold a loop, decide what to do next, apply |
| Policy Engine | Read the request and the files it names by digest; return one decision | Reach the network, a model or git; read raw tool output; apply an exception; merge |
| CI (attester) | Run the gates, sign evidence records | Sign release tokens |
| Pull-request gate runners | Run a pull request's checks on agent-written code, ephemeral and unprivileged | Hold deploy, apply or secret access; share the apply pipeline's identity |
| CI webhook ingress | Verify GitHub's signature, re-read the check result from GitHub, store the report as a claim check | Treat a received payload as evidence before re-reading it; call the execution plane |
| Compliance authority | Verify evidence, evaluate criteria, sign single-use tokens | Deploy, accept a decision or status from the Builder |
| Deployment guard | Consume a valid token once, deploy the pinned digest | Deploy anything else |
| Apply pipeline | Apply a merged, approved plan | Run on an agent's request |
| People | Approve specs, approve every factory merge, approve exceptions, lift a quarantine | Bypass branch protection (admins included) |

- **Workloads and agents use short-lived federated identity only**, pinned to repo, branch, and
  environment; cloud credentials live one hour (`00_UniversalStandards/07_Security_In_Depth.md`).
- **Agents are roles, never users.** People sign in through the workforce directory with MFA;
  agents assume roles bounded so they cannot change IAM or networks or delete resources. The Builder
  calls models and plans but cannot apply; publishing and applying belong to their own pipeline
  identities.
- **Agents never notify people;** they set labels, and a notification service routes them.

## 4️⃣a Separation of Cognition from Execution Authority

The factory separates the ability to reason about, propose, and build a change from the authority
to evaluate, certify, approve, and execute it. Agents never hold the second kind, so they cannot
redefine the standards, certify their own work, or grant themselves deployment rights. **Design**:
owner decision, 2026-11-08.

| Plane | Where | Holds | Never holds |
| :--- | :--- | :--- | :--- |
| Cognitive (agentic) | AWS | The orchestrator, the Builder and its models, retrieval, the claim-check store, the event bus | Any identity in the execution plane; authority to evaluate, approve, apply, or deploy |
| Execution (service) | GCP (`sovereign-vpc-gcp`) | CI with its Policy Engine and attester, the compliance authority and deployment guard, apply, the services | Agent identities |
| Seam | GitHub | Pull requests, required checks, branch protection, CODEOWNERS | — |
| Human | The owner | Approval of every merge and every protected change | — |

Genesis governs both planes.

### Four flows

| Flow | Path | Carries | Authority it carries |
| :--- | :--- | :--- | :--- |
| Change | Agentic plane → GitHub → execution plane | A pull request | None: a proposal, run by CI in isolation |
| Verification | GitHub → the agentic plane's webhook ingress | A check result | None until the signature is verified and the result is re-read from GitHub |
| Observability | Agentic plane → the execution plane's collector | Traces, metrics, logs | None: send-only |
| Coordination | Agentic plane ↔ Jira | Ticket status and specs | None: moving a ticket starts work and approves nothing; ticket text is untrusted input, and work enters only as an approved spec fetched by digest |

### Three controls on the seam

GitHub is part of the trusted computing boundary, not only a transport. So is every account that
can change its settings, held to the same standard as a cloud admin role, and a change to a
protection rule is itself a protected change.

| Path an agent could use | Control | Status |
| :--- | :--- | :--- |
| Change its evaluator: workflows, the `gates.yml` pin, `.ci/quality.v1.json`, `.ci/exceptions.v1.json` | Agent GitHub Apps have no `workflows` permission; CODEOWNERS requires a human code owner on those paths | **Design**: CODEOWNERS exist in two repositories but are not enforced (INC-001); App permissions not yet audited (KAN-30) |
| Run its code with execution authority | Pull-request gate runners are ephemeral and unprivileged, run tests with no network, and hold an identity with no deploy, apply, or secret access, separate from the apply pipeline's | **Partial**: runners are ephemeral per job; the factory still runs on the runner image (§7); identity separation not yet verified |
| Merge around the gates | Protected `main`: a pull request, the gate checks, and the owner's code-owner review are required, with no bypass for admins | **Gap**: no platform repository's `main` is protected (INC-001, open; the playbook's `main` checked unprotected on 2026-11-08) |

### One evidence rule

**Authoritative evidence is signed by the CI attester's identity.** Everything else, including any
report an agent makes about its own work, stays at tier `CLAIMED` (§6); repeating, forwarding, or
receiving a claim never promotes it. The rule rests on the signing identity, not on which cloud
produced the result.

### The human gate

The owner approves on the diff and the signed CI evidence, never on the agent's summary: a pull
request's description is a claim like any other.

## 5️⃣ Data and Messaging

- **Claim check.** Specs, CI reports, and artifacts are objects in a versioned,
  write-locked, encrypted object store. Events carry only the ID, URI, and SHA-256, and every
  consumer verifies the digest before use (`ARCH-024`, `schemas/claim_check.v1.schema.json`).
- **The object store is the history; the event stream only delivers.** The stream keeps events for
  days; the store keeps every version for at least the triage window. Older deployments move to one
  sealed bundle each in archive storage (**Design**, `03_InfrastructureZone/06_Messaging_Building_Blocks.md` §3a).
- **The path.** Producer outbox → event stream (Kafka) → bridge → fan-out topic → one work queue per
  consumer, with a dead-letter queue; consumers are idempotent by `event_id`
  (`02_BackendZone/05_Application_Architecture.md`).
- **Ingress, internal, egress** share the backbone: `spec.*` events bring work in, factory events
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

![CI factory: consumer repos call one gates.yml at a full commit SHA with inputs; it detects stacks, runs per-stack jobs and scanners, and routes every scanner report through a severity gate that blocks only CRITICAL or CISA KEV and fails closed, reading OSV, KEV and the caller's reviewed exceptions; then the factory loop's gate, the ticket's acceptance tests and the Policy Engine on the Evaluator's metrics for the change and its merge base (design). Genesis cannot call it: public cannot call private.](docs/architecture/sheet-3-ci-factory.svg)

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
- **Triage walks back from the deployed digest:** token → evaluation → commit → CI attempts → spec
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
