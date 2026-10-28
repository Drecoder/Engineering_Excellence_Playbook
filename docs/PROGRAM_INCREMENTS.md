# Program Increments: From 61 to 90 Against the Playbook

*Where the factory stands against its own standard, the score each stage has to reach, and what
earns it.*

The bar is **90 out of 100** against the playbook's enforceable rules (`AGENTS.md`). A rule counts
only when it is enforced and running on `main`: designed, documented, or open in a pull request
scores nothing. Each program increment (PI) ends with a re-grade from evidence (repository state,
CI runs, and branch settings) and is accepted only when its exit criteria are met.

---

## 1️⃣ How the Score Is Computed

Each area is scored 0 to 100 from evidence, then weighted:

| Area | Weight | What earns points |
| :--- | :--- | :--- |
| Standards and contracts | 15 | Versioned contracts with vectors and contract tests in CI |
| CI gates | 15 | The central gates on every repository, green |
| Human-approved merge | 15 | Branch protection on every factory repository, admins included |
| Supply chain | 10 | Exact pins, licenses checked, SBOM, signature, and provenance on every release, verified at deploy |
| Test quality | 10 | Coverage floors held, changed-line coverage reported, mutation floors, golden tasks |
| Observability | 10 | Traces, metrics, and logs everywhere; indexed metrics; SLOs, burn-rate alerts, delivery metrics |
| IaC and governance | 10 | Terragrunt, green plan and apply, guardrails enforced from the baseline |
| Agent loop | 10 | Notepad, event handoff, compliance authority, and release tokens running |
| Containers | 5 | Every image pinned by digest, non-root, read-only root |

## 2️⃣ The Path

| Stage | PI | Target | Main sources of points | Unblocked by |
| :--- | :--- | :--- | :--- | :--- |
| Baseline (2026-10-28) | — | 61 | — | — |
| Proof of concept complete | PI-1 | **70** | Working memory, every gate live on every repository, SLOs, golden tasks | Hand-built work |
| Pilot | PI-2 | **85** | Branch protection, signed releases, live telemetry, delivery metrics, green bootstrap | Owner decisions and the bootstrap apply |
| Production | PI-3 | **91** | Genesis on Terragrunt and green, verified deploys, cloud backends, burn-rate paging | The agent loop and Genesis infrastructure |
| Scale | PI-4 | **≥ 93, held** | Autonomy promoted on evidence, the loop replacing hand-built services, client projects | Evidence |

The proof-of-concept ceiling is about 70: the human-approved merge (weight 15), infrastructure (10),
and most of the supply chain need the pilot and production stages. Without branch protection the
ceiling in every stage is about 75.

## 3️⃣ PI-1: Proof of Concept Complete (61 → 70)

**Goal:** every rule that needs no new infrastructure is enforced on every repository, and the work
has a memory.

The notepad comes first. It is the factory's **working memory** (`06_AgentZone/07_Agent_Notepad.md`):
decisions, questions with their reasons, tool evidence, and each PI's grade live in sealed records
instead of pasted handoffs and chat history. Every later feature is cheaper to build and better
recorded once it exists, so by weighted shortest job first it leads the increment.

| # | Feature | Why | Exit criterion |
| :--- | :--- | :--- | :--- |
| 1 | Notepad service core, local backends | The working memory every later step records into | The Builder seals before a push; the commit carries `Notepad-Manifest`; a sealed version refuses writes |
| 2 | Event handoff on a local bus | The loop cannot run without it | One review round runs `review.requested` → `review.completed` with outbox, inbox, and dead-letter queue |
| 3 | Merge the open contract, gate, and service changes | Points count only on `main` | Merged, CI green |
| 4 | Consumer rollout: repin, `.ci/quality.v1.json`, coverage reporters | A floor nobody runs is not a floor | Every consumer passes the coverage and license gates at its measured floor |
| 5 | Exact versions in every `package.json` | Floating ranges break the supply-chain rule even with a lockfile | No `^` or `~` in any factory repository |
| 6 | Telemetry in rig | The one service with none | Spans, RED metrics, and JSON logs, indexed in `metrics/promql/MASTER_INDEX.md` |
| 7 | Reviewer golden tasks | Prompt and model changes are blocked without them | At least one designed-to-fail task; the suite runs in CI |
| 8 | Nightly mutation testing | Coverage shows code ran; mutation shows the tests would notice it being wrong | A measured score and a floor per repository, critical paths first |
| 9 | SLOs and burn-rate rules | No SLO means no error budget, no burn-rate page, and no autonomy evidence | `slo.v1` contract; SLOs for the compliance authority, Builder, and Reviewer; generated rules pass `pint` |

**Target by area:** standards 96, CI 92, merge 20, supply chain 62, tests 78, observability 78,
IaC 50, agent loop 78, containers 82.

## 4️⃣ PI-2: Pilot (70 → 85)

**Goal:** real work through the factory, under controls no one can bypass.

| Feature | Why | Exit criterion |
| :--- | :--- | :--- |
| Branch protection on every factory repository | Turns "humans approve merges" from a habit into a control | A merge without approval is refused, admins included |
| Release pipeline: SBOM, signature, provenance | Know what is in every image and prove where it came from | Every build of `main` publishes a signed image with its SBOM and provenance |
| Bootstrap apply for the platform's identity unit | A factory whose apply fails cannot ship | `apply` green on `main`; the incident issue closes |
| Live telemetry backend and dashboards | Metrics no one sees are not observability | Every service's RED metrics and SLOs visible; one alert fired in a drill |
| Delivery metrics | Extends the baseline's lead time and change failure rate with deployment frequency and time to restore | All four measured from CI events, on a dashboard |
| The notepad's seal check in central CI | Makes the record trustworthy | A push without a valid `Notepad-Manifest` trailer fails |

**Target by area:** standards 96, CI 93, merge 90, supply chain 80, tests 82, observability 85,
IaC 65, agent loop 82, containers 85.

## 5️⃣ PI-3: Production (85 → 91)

**Goal:** the 90 bar, met on production infrastructure.

| Feature | Why | Exit criterion |
| :--- | :--- | :--- |
| Genesis on Terragrunt, green | The IaC rules require it, and it proves the loop delivers real infrastructure | `plan` and `apply` green; no bare `terraform` |
| Signatures verified at deploy | Signing matters only if unsigned images are refused | An unsigned image is rejected in a drill |
| Cloud backends for the notepad and the compliance authority | Local files cannot resist tampering | Object-locked storage, KMS keys, and the event backbone in use |
| The compliance authority as a service | It is a command-line tool today | The Builder submits, and the deployment guard consumes tokens, in the real pipeline |
| Burn-rate paging and incident records | Pages fire on symptoms, and every failure leaves a record | First real incident handled end to end with evidence pointers |

**Target by area:** standards 97, CI 94, merge 90, supply chain 92, tests 86, observability 90,
IaC 90, agent loop 90, containers 90.

## 6️⃣ PI-4: Scale (hold ≥ 93)

- Promote non-protected process classes one level at a time on evidence
  (`00_UniversalStandards/10_Autonomy_by_Evidence.md`); demotion stays automatic.
- The agent loop rebuilds the hand-built services against the same contracts and replaces them.
- Client projects run on their own buckets and keys (`project.v1`).
- Exit: 90 or more held for a whole PI, with every demotion handled.

## 7️⃣ Risks

- **Branch protection is the swing factor:** without it, no stage passes about 75.
- **Genesis depends on the agent loop,** and the Builder cannot yet write workflow YAML or Markdown.
  That capability is a PI-2 prerequisite for PI-3.
- **Cost:** a live telemetry backend and cloud backends add monthly spend; each rule is met with
  the cheapest option that meets it.

## Open Decisions

Recorded here until decided, each by a reviewed change to this document:

- **PI length:** two weeks while most work is hand-built, or four to six weeks once the agent loop
  and pilot users take part.
- **Branch protection route:** a paid plan that keeps the repositories private, or public
  repositories after the history audit.
- **Release signing:** keyless signing, which publishes the repository and workflow identity in
  public transparency logs, or a cloud KMS key, which waits on Genesis.

---

## Principle

Score only what runs, set each stage a number, and build first what makes everything after it
cheaper.
