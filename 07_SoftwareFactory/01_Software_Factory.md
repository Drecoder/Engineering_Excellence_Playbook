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

All repositories are under `Drecoder`. The playbook and Genesis are public; the others are private.

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

## 3️⃣ How the Benches Work Together

A change moves through the factory in this order (`ARCHITECTURE.md` §3 draws it). Today most
handoffs are a pull request, a file, or an in-process call. The target is that every handoff is an
event on the backbone carrying a claim check (`ARCHITECTURE.md` §5); release tokens never ride it.

| From | To | Through | Status |
| :--- | :--- | :--- | :--- |
| Playbook | Every repository | `.playbook/`, synced by the playbook's action and checked byte-for-byte in CI | **Partial**: the Builder, notepad, and authority sync; the Reviewer and rig vendor without the sync workflow; Genesis and `sovereign-vpc-gcp` do not vendor |
| Every repository | `sovereign-vpc-gcp` | `gates.yml`, called by full commit SHA | **Partial**: Genesis is public and cannot call the private factory |
| Genesis | Platform and services | Governed projects, guardrails, messaging and storage modules | **Partial**: the bootstrap slice and modules are pending for the agent loop |
| Intake | Builder | `spec.approved` on the Builder's queue; the spec is fetched by digest | **Design** |
| Builder | Notepad | The injected `Notepad` interface; a seal at each push | **Partial**: a library with local backends, no network boundary |
| Builder | rig | The rig-scan gate and `features.v1`, before the pull request opens | **Built** |
| Builder | Reviewer | The pull request today; `review.requested` and `review.completed` as the target | **Built** (PR-driven); events **Design** |
| rig | Reviewer | `evaluation_unit.v1` and `features.v1` | **Built** (file-based) |
| Builder | Compliance authority | The scoping skill reads the registry; the submission carries CI-signed evidence | **Partial**: the authority runs as a CLI; the scoping skill is in progress |
| Compliance authority | Deployment guard | `release_token.v1`, on its own authenticated path | **Partial**: the guard is built, not wired into the apply pipeline |
| People | Merge, then apply | Branch protection; the apply pipeline with its own identity | **Built** |

## 4️⃣ Rules of the Workshop

- **The playbook depends on no bench.** It describes the factory's repositories here; each one
  depends on the playbook, never the reverse (`00_UniversalStandards/05_Standards_Distribution.md`).
- **Contracts live only in the playbook's `schemas/`.** A bench vendors them; it never copies or
  redefines one.
- **No bench approves its own work.** Each is its own identity (`ARCHITECTURE.md` §4).
- **The factory is built by its own rules.** A bench that cannot meet the playbook is not built.
- **Benches built by hand are replaced by the factory.** MVP benches built by hand, on local
  backends behind injected interfaces, are later rebuilt by the agent loop.

---

## Principle

The playbook teaches the craft; the factory is the workshop where every rule is used at once, on
every piece of work, including the factory itself.
