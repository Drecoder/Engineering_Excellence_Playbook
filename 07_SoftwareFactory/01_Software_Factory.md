# The Software Factory

*The capstone of the playbook: the workshop where the craft of software engineering is practiced,
by every rule the playbook teaches.*

The zones before this one say how we build. The software factory is where that is done: a workshop
of repositories, each a bench with one job, that turns an approved requirement into a released
artifact. It builds anything; it is not tied to one product. And it is held to the same rules as
the work that comes out of it, so the factory is also the playbook's proof that its rules work
together.

This page describes the factory's own repositories and how they work with one another. The
platform map, trust boundaries, and status of every stage are in `ARCHITECTURE.md`; the rules for
each bench are in the standard it links to.

---

## 1️⃣ Why It Is the Capstone

Every zone of the playbook lands on a bench in the factory.

| Zone | Where it shows up in the factory |
| :--- | :--- |
| `00_UniversalStandards` | The lifecycle, Definition of Done, security, governance, reuse, autonomy, containers, supply chain, test quality, and central CI that every bench follows, and that the central CI, Genesis, and the compliance authority enforce |
| `01_FrontendZone`, `02_BackendZone` | What the Builder writes and what CI's gates, rig's `ARCH-*` checks and the Policy Engine hold it to |
| `03_InfrastructureZone` | How Genesis and the platform are built, and the Builder's IaC stack |
| `04_OperationalRunbooks` | Incidents, rollbacks, and alerts for the factory and for what it ships |
| `05_Metadata` | Red/Green decisions, which the gates turn into pass or block |
| `06_AgentZone` | The Builder, the orchestrator, intake, the compliance authority, and the notepad |

## 2️⃣ The Benches

All repositories are under `Drecoder`. The playbook is public: it is the public face of the work.
Every factory repository is private, and one private repository can call another's reusable
workflow, so all of them can call the private central gate.

| Repository | Bench | Kind | Takes in | Puts out |
| :--- | :--- | :--- | :--- | :--- |
| `Engineering_Excellence_Playbook` | The rulebook: standards, `AGENTS.md`, contracts in `schemas/` | Rules | Reviewed changes to the standards | `.playbook/`, vendored into every other repository at a pinned commit |
| `Genesis` | Guardrails and vending: the governance hierarchy, `GOV-*` per cloud, new projects, messaging and storage modules | Infrastructure | The governance baseline | Governed cloud projects and the shared infrastructure the services run on |
| `sovereign-vpc-gcp` | The shop floor: private network, state, federated identity, runners, observability, inference, and the central CI factory (`gates.yml`) | Infrastructure | Every repository's pull requests | Gate results, runner capacity, the OTLP collector, self-hosted models |
| `aws-builder-agent` | The Builder | Actor | `builder.spec.v1`, an approved task, and from the second attempt the CI report | Code or infrastructure built in a sandbox, `builder.result.v1`, a pull request, and fixes to its own change |
| `rig` | Measurement: deterministic lift, `ARCH-*` static and trace checks, features, the symbol index | Tool | A repository and a test run's traces | `evaluation_unit.v1`, `features.v1`, `symbol_index.v1` |
| `compliance-authority` | Final inspection: evidence verification, evaluation, release tokens, and the deployment guard | Service | `compliance_submission.v6` with CI-signed evidence | An append-only evaluation record and a single-use `release_token.v1` |
| `agent-notepad` | Working memory: a folder per agent and task, a sealed, hash-chained page at each push | Service | `notepad_op.v1` operations | `notepad_manifest.v1`, named in each commit's `Notepad-Manifest` trailer |
| `factory-orchestrator` | The dispatcher: a thin orchestrator that leases one approved ticket at a time, hands it to the Builder, reads the CI result, and bounces it back up to the attempt limit and the budget | Service | Tickets the owner moved to Ready, and CI results | A validated `builder.spec.v1` for the Builder, and ticket transitions |
| Quality evaluator | Measurement, inside CI: runs the pinned complexity, coverage, mutation and audit tools and normalizes their output (`00_UniversalStandards/17_Quality_Policy_Engine.md` §2–3) | Tool | A commit, its tests and its dependency manifests | `quality_metrics.v1` for the change and for its merge base |
| Policy Engine | Decision, inside CI: applies `quality_policy.v1` to the two metrics files, with no network, database or model | Tool | `policy_evaluation_request.v1` and the files it names by digest | `policy_decision.v1`: PASS, BLOCK or QUARANTINE, with one finding per failed rule |

The **architect** is a role, not a repository: it turns the owner's plan into a spec and posts it to
the board's Backlog. It may be a person or an agent; either way it never builds or approves.

## 2️⃣a The Workspace

Checked out on a machine, the factory is laid out the same way it is designed: one folder per
bench, and every repository and worktree of that bench inside it. Anyone, person or agent, can tell
from a path which bench they are in.

```text
<workspace>/
  <bench>/
    <repository>/            the main checkout
    worktrees/<short-name>/  one per branch in progress, named for the work
```

| Bench folder | Holds |
| :--- | :--- |
| `builder/` | `aws-builder-agent` |
| `rig/` | `rig` |
| `notepad/` | `agent-notepad` |
| `compliance/` | `compliance-authority` |
| `orchestrator/` | `factory-orchestrator` |
| `measurement/` | The quality evaluator and the Policy Engine |
| `platform/gcp/`, `platform/genesis/` | `sovereign-vpc-gcp`, `Genesis` |
| `playbook/` | Worktrees of `Engineering_Excellence_Playbook` |
| `specs/` | The factory's specs |

- **New repositories are cloned straight into their bench folder,** never at the workspace root.
  A repository that fits no bench gets its bench first: a row in §2 and a folder here.
- **New worktrees go in the bench's `worktrees/`:** `git worktree add <bench>/worktrees/<name> <branch>`,
  named for the work (`scanners`, `cost-ledger`), not for the repository.
- **Checkouts move only through git.** A worktree moves with `git worktree move`; a moved main
  checkout is relinked with `git worktree repair`. A plain file move breaks git's links between
  them.
- The playbook's own main checkout stays where it is; only its worktrees live under `playbook/`.

## 3️⃣ How the Benches Work Together

A change moves through the factory in this order (`ARCHITECTURE.md` §3 draws it). Today most
handoffs are a pull request, a file, or an in-process call. The target is that every handoff is an
event on the backbone carrying a claim check (`ARCHITECTURE.md` §5); release tokens never ride it.

| From | To | Through | Status |
| :--- | :--- | :--- | :--- |
| Playbook | Every repository | `.playbook/`, synced by the playbook's action and checked byte-for-byte in CI | **Partial**: the Builder, notepad, and authority sync; rig vendors without the sync workflow; Genesis and `sovereign-vpc-gcp` do not vendor |
| Every repository | `sovereign-vpc-gcp` | `gates.yml`, called by full commit SHA | **Partial**: every factory repository calls it; Genesis since 2026-10-29, red on its legacy code |
| Genesis | Platform and services | Governed projects, guardrails, messaging and storage modules | **Partial**: the bootstrap slice and modules are pending for the agent loop |
| Intake | Builder | `spec.approved` on the Builder's queue; the spec is fetched by digest | **Design** |
| Board | Builder (MVP path) | The orchestrator polls the Ready column, leases one ticket, and hands the Builder a validated `builder.spec.v1` | **Design**: decision logic built on in-memory fakes; no Jira adapter yet |
| Builder | CI | The pull request calls `gates.yml`: tests, scanners, the ticket's acceptance tests, and the Policy Engine | **Partial**: the Policy Engine is not wired in |
| CI | Builder | A failing CI report, bounced back by the orchestrator (below) | **Design** |
| CI | Board | PASS moves the ticket to Awaiting Approval; QUARANTINE to Human; a failure at the limit to Blocked | **Design** |
| Builder | Notepad | The injected `Notepad` interface; a seal at each push | **Partial**: a library with local backends, no network boundary |
| Builder | rig | The rig-scan gate and `features.v1`, before the pull request opens | **Built** |
| Builder | Compliance authority | The scoping skill reads the registry; the submission carries CI-signed evidence | **Partial**: the authority runs as a CLI; the scoping skill is in progress |
| Compliance authority | Deployment guard | `release_token.v1`, on its own authenticated path | **Partial**: the guard is built, not wired into the apply pipeline |
| People | Merge, then apply | Branch protection; the apply pipeline with its own identity | **Built** |

### The fix loop

The Builder and CI loop is the factory (owner decision, 2026-11-07, KAN-14). The Builder writes the
change; CI evaluates it; the owner approves the merge.

- **Acceptance tests come first.** Every ticket has acceptance tests written before the build. They
  carry spec conformance, run in CI, and must be shown to fail before the change that passes them.
- **CI is the only evaluator.** It runs the tests, the scanners, the acceptance tests, and the
  Policy Engine (PASS, BLOCK or QUARANTINE). There is no Reviewer agent and no separate fixer agent.
- **A failing report goes straight back to the Builder,** which fixes its own change. Retries carry
  the delta: what failed and the sealed notepad page, not the whole ticket again. Findings stay in
  the report; they do not become sub-tickets.
- **Loops end.** A ticket gets 3 attempts, counted by the board's automation, never by an agent,
  and stops at its $2.00 budget. A failure at either limit moves the ticket to Blocked with its
  history.
- **A pass waits for the owner.** The ticket moves to Awaiting Approval; the owner's merge approval
  is the only judgment step.
- **A quarantine is the owner's.** The ticket moves to Human with the `quality-quarantine` label,
  and nothing bounces it until the owner decides.

### The board ticket's format (MVP path)

On the MVP path a factory ticket is the task. The Jira adapter reads it with no custom fields:
fixed `##` sections in the description, parsed strictly (owner decision, 2026-11-08, KAN-14).

| Source | Becomes in `builder.spec.v1` | Rule |
| :--- | :--- | :--- |
| Issue summary | `task.title` | 1–200 characters |
| `## Repository` | `repository.full_name`, `repository.base_branch` | One line: `owner/name @ branch` |
| `## Task` | `task.description` | Non-empty Markdown |
| `## Acceptance criteria` | `task.acceptance_criteria` | Bullet list, at least 1 item |
| `## Acceptance tests` (optional) | `task.acceptance_tests` | Bullet list of repository paths |
| `## Scope` | `task.scope.paths` | Bullet list of repository paths, at least 1 |
| The changelog entry for the move to Ready | `source` (who approved, when) | Read from Jira, never from the body |

- **Strict, never repaired.** A missing, empty, duplicated or malformed required section rejects
  the ticket before any lease or Builder call. Headings match exactly, in any order; text outside
  them is ignored; bullets are read in the style Jira returns.
- **The attempt counter is not in the body.** It is the issue property `factory.attempt`, written
  only by the orchestrator.
- **Decisions are named rules.** Every move the orchestrator makes is a named rule in code, never a
  model's judgment.

## 4️⃣ Rules of the Workshop

- **The playbook depends on no bench.** It describes the factory's repositories here; each one
  depends on the playbook, never the reverse (`00_UniversalStandards/05_Standards_Distribution.md`).
- **Contracts live only in the playbook's `schemas/`.** A bench vendors them; it never copies or
  redefines one.
- **No bench approves its own work.** Each is its own identity (`ARCHITECTURE.md` §4).
- **No model provider checks its own output.** The models that write a change and its acceptance
  tests come from different providers, and the architect's provider does not build from its own
  spec.
- **Only the owner starts work.** A spec enters the board in Backlog; moving it to Ready is the one
  trigger, and the orchestrator never picks up anything else.
- **Agents take only factory work.** Ready also holds the owner's hand-done work, so the
  orchestrator picks up only tickets labeled `factory`; a ticket without the label is never touched.
- **The factory is built by its own rules.** A bench that cannot meet the playbook is not built.
- **Benches built by hand are replaced by the factory.** MVP benches built by hand, on local
  backends behind injected interfaces, are later rebuilt by the agent loop.

---

## Principle

The playbook teaches the craft; the factory is the workshop where every rule is used at once, on
every piece of work, including the factory itself.
