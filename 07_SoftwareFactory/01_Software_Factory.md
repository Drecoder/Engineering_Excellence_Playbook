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
| `01_FrontendZone`, `02_BackendZone` | What the Builder writes and what the Reviewer's lenses and rig's `ARCH-*` checks hold it to |
| `03_InfrastructureZone` | How Genesis and the platform are built, and the Builder's IaC stack |
| `04_OperationalRunbooks` | Incidents, rollbacks, and alerts for the factory and for what it ships |
| `05_Metadata` | Red/Green decisions, which the gates turn into pass or block |
| `06_AgentZone` | The Builder, the Reviewer, intake, the compliance authority, and the notepad |

## 2️⃣ The Benches

All repositories are under `Drecoder`. The playbook is public: it is the public face of the work.
Every factory repository is private, and one private repository can call another's reusable
workflow, so all of them can call the private central gate.

| Repository | Bench | Kind | Takes in | Puts out |
| :--- | :--- | :--- | :--- | :--- |
| `Engineering_Excellence_Playbook` | The rulebook: standards, `AGENTS.md`, contracts in `schemas/` | Rules | Reviewed changes to the standards | `.playbook/`, vendored into every other repository at a pinned commit |
| `Genesis` | Guardrails and vending: the governance hierarchy, `GOV-*` per cloud, new projects, messaging and storage modules | Infrastructure | The governance baseline | Governed cloud projects and the shared infrastructure the services run on |
| `sovereign-vpc-gcp` | The shop floor: private network, state, federated identity, runners, observability, inference, and the central CI factory (`gates.yml`) | Infrastructure | Every repository's pull requests | Gate results, runner capacity, the OTLP collector, self-hosted models |
| `aws-builder-agent` | The Builder | Actor | `builder.spec.v1`, an approved task | Code or infrastructure built in a sandbox, `builder.result.v1`, a pull request |
| `gcp-reviewer-agent` | The Reviewer | Actor | rig's `evaluation_unit.v1` and `features.v1` | Advisory `review_findings.v1`, through lenses |
| `rig` | Measurement: deterministic lift, `ARCH-*` static and trace checks, features, the symbol index | Tool | A repository and a test run's traces | `evaluation_unit.v1`, `features.v1`, `symbol_index.v1` |
| `compliance-authority` | Final inspection: evidence verification, evaluation, release tokens, and the deployment guard | Service | `compliance_submission.v6` with CI-signed evidence | An append-only evaluation record and a single-use `release_token.v1` |
| `agent-notepad` | Working memory: a folder per agent and task, a sealed, hash-chained page at each push | Service | `notepad_op.v1` operations | `notepad_manifest.v1`, named in each commit's `Notepad-Manifest` trailer |
| `jira-orchestrator` | The dispatcher: moves one approved ticket at a time from the board through build, gates, and review | Service | Tickets the owner moved to Ready | A validated `builder.spec.v1` for the Builder, ticket transitions, Reviewer findings attached to the ticket |
| CRAP service | Measurement: scores each changed method for complexity against coverage | Tool | A change and its coverage report | A finding for each method over the threshold, in its own journal |
| Mutation service | Measurement: mutates the changed code to show whether the tests notice | Tool | A change and its tests | A finding for each surviving mutant, in its own journal |
| CRAP fixer | Fixes one CRAP finding at a time, in production code only | Actor | One finding ticket and the sealed notepad page | A commit on the pull request's branch |
| Mutation fixer | Kills one surviving mutant at a time by strengthening tests, in tests only | Actor | One finding ticket and the sealed notepad page | A commit on the pull request's branch |

The **architect** is a role, not a repository: it turns the owner's plan into a spec and posts it to
the board's Backlog. It may be a person or an agent; either way it never builds, reviews the code,
or approves.

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
| `reviewer/` | `gcp-reviewer-agent` |
| `rig/` | `rig` |
| `notepad/` | `agent-notepad` |
| `compliance/` | `compliance-authority` |
| `orchestrator/` | `jira-orchestrator` |
| `measurement/` | The CRAP and mutation services |
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
| Playbook | Every repository | `.playbook/`, synced by the playbook's action and checked byte-for-byte in CI | **Partial**: the Builder, notepad, and authority sync; the Reviewer and rig vendor without the sync workflow; Genesis and `sovereign-vpc-gcp` do not vendor |
| Every repository | `sovereign-vpc-gcp` | `gates.yml`, called by full commit SHA | **Partial**: every factory repository calls it; Genesis since 2026-10-29, red on its legacy code |
| Genesis | Platform and services | Governed projects, guardrails, messaging and storage modules | **Partial**: the bootstrap slice and modules are pending for the agent loop |
| Intake | Builder | `spec.approved` on the Builder's queue; the spec is fetched by digest | **Design** |
| Board | Builder (MVP path) | The orchestrator polls the Ready column, leases one ticket, and hands the Builder a validated `builder.spec.v1` | **Design** |
| Orchestrator | Reviewer | After the gates pass, the orchestrator requests review and attaches the findings to the ticket | **Design** |
| CRAP and mutation services | Fixers | Each finding becomes its own ticket under the change's ticket (below) | **Design** |
| Builder | Notepad | The injected `Notepad` interface; a seal at each push | **Partial**: a library with local backends, no network boundary |
| Builder | rig | The rig-scan gate and `features.v1`, before the pull request opens | **Built** |
| Builder | Reviewer | The pull request today; `review.requested` and `review.completed` as the target | **Built** (PR-driven); events **Design** |
| rig | Reviewer | `evaluation_unit.v1` and `features.v1` | **Built** (file-based) |
| Builder | Compliance authority | The scoping skill reads the registry; the submission carries CI-signed evidence | **Partial**: the authority runs as a CLI; the scoping skill is in progress |
| Compliance authority | Deployment guard | `release_token.v1`, on its own authenticated path | **Partial**: the guard is built, not wired into the apply pipeline |
| People | Merge, then apply | Branch protection; the apply pipeline with its own identity | **Built** |

### Findings become tickets

A CRAP or mutation finding is work like any other: visible on the board, leased, and counted.

- **One ticket per finding,** under the change's ticket, naming the method or mutant and its journal
  entry. A rerun never opens a duplicate.
- **CRAP before mutation.** Fixing production code changes the mutants, so mutation findings wait
  until the CRAP findings on the same change are closed.
- **Scopes are enforced, not trusted.** CI fails a CRAP fixer's change outside production code and
  a mutation fixer's change outside tests.
- **Only the quick check reruns** after a fix: that method's score, or that one mutant.
- **Loops end.** A finding gets 3 attempts, counted by the board's automation, never by an agent.
  The third failure sends it to the Builder; if the Builder fails too, the ticket moves to Blocked
  with its history. It never moves to the Reviewer's column, which is for finished work.
- **Retries carry the delta.** From the second attempt, an agent receives only what failed (the
  method, the mutant, the gate's lines) and the sealed notepad page, not the whole ticket again.
- **Equivalence is a person's call.** A fixer may propose that a mutant cannot be killed; only the
  owner rules on it.
- **The Reviewer runs once,** on the final diff, after every finding is closed.

## 4️⃣ Rules of the Workshop

- **The playbook depends on no bench.** It describes the factory's repositories here; each one
  depends on the playbook, never the reverse (`00_UniversalStandards/05_Standards_Distribution.md`).
- **Contracts live only in the playbook's `schemas/`.** A bench vendors them; it never copies or
  redefines one.
- **No bench approves its own work.** Each is its own identity (`ARCHITECTURE.md` §4).
- **No model provider checks its own output.** The models that write a change, review it, and test
  it come from different providers, and the architect's provider does not review the code built
  from its spec.
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
