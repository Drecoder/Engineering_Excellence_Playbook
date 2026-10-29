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
| Release pipeline: SBOM, signature, provenance (CD-1 to CD-4, §7) | Know what is in every image and prove where it came from | Every build of `main` publishes a signed image with its SBOM and provenance |
| Bootstrap apply for the platform's identity unit | A factory whose apply fails cannot ship | `apply` green on `main`; the incident issue closes |
| Live telemetry backend and dashboards | Metrics no one sees are not observability | Every service's RED metrics and SLOs visible; one alert fired in a drill |
| Delivery metrics (CD-9, CD-10) | Extends the baseline's lead time and change failure rate with deployment frequency and time to restore | All four measured from CI events, on a dashboard |
| The notepad's seal check in central CI | Makes the record trustworthy | A push without a valid `Notepad-Manifest` trailer fails |

**Target by area:** standards 96, CI 93, merge 90, supply chain 80, tests 82, observability 85,
IaC 65, agent loop 82, containers 85.

## 5️⃣ PI-3: Production (85 → 91)

**Goal:** the 90 bar, met on production infrastructure.

| Feature | Why | Exit criterion |
| :--- | :--- | :--- |
| Genesis on Terragrunt, green | The IaC rules require it, and it proves the loop delivers real infrastructure | `plan` and `apply` green; no bare `terraform` |
| Signatures verified at deploy (CD-5 to CD-8, §7) | Signing matters only if unsigned images are refused | An unsigned image is rejected in a drill |
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

## 7️⃣ Continuous Delivery

Every service runs in the cloud as a container, so every service ships an image: the central gate
builds it, tests in it, and scans it on every pull request, and fails a repository that neither
names its image nor declares why it has none. Delivery takes that image from a merge to a running
service without ever trusting anything it cannot verify:

1. **Publish.** A merge to `main` builds the image once, pushes it by digest, and attaches its SBOM,
   keyless signature, and SLSA provenance. Nothing is deployed by tag.
2. **Promote.** Each environment's digest lives in an environment repository. Development follows
   every publish; staging and production change only by a human-approved merge there, enforced by
   branch protection, never by a deploy button. Rollback promotes the previous digest.
3. **Admit.** The deployment guard verifies the signature, the provenance, and a single-use release
   token from the compliance authority, consumes the token, and attests the digest with a key only
   it holds; Cloud Run's Binary Authorization runs only attested digests, so a direct
   `gcloud run deploy` is refused too.

Every handoff is an event on the bus (`image.published`, `deploy.requested`, `deploy.completed`),
built on the bus interface with its local adapter until the backbone lands. Release tokens never
ride the bus: the event names the evaluation, and the token reaches the guard on its own
authenticated path.

| ID | PI | Story | Done when | Depends on |
| :--- | :--- | :--- | :--- | :--- |
| CD-1 | PI-2 | Artifact Registry and the publish identity, in Genesis's bootstrap slice | A registry per environment; a federated publish identity pinned to repository, `main`, and environment, one-hour credentials, no keys | Genesis bootstrap |
| CD-2 | PI-2 | Central publish stage on merge to `main` | Builds once, pushes by digest, scans that digest through the shared severity gate, emits `image.published` | CD-1; the image job in the central gate |
| CD-3 | PI-2 | SBOM attestation | A syft SBOM (pinned in the gate) attached to the digest | CD-2 |
| CD-4 | PI-2 | Keyless signature and SLSA provenance | The digest is signed by the pipeline's identity; provenance names repository, commit, workflow, and builder | CD-2 |
| CD-5 | PI-3 | Cloud Run services as Terragrunt units | One unit per service: its own least-privilege service account, ingress, scaling limits; Checkov passes | CD-1 |
| CD-6 | PI-3 | Promotion by digest through the environment repository | Development deploys on publish; staging and production on approved merges; rollback promotes the previous digest | CD-2, CD-5, branch protection |
| CD-7 | PI-3 | Deployment guard and Binary Authorization | The guard checks the signature's issuer (GitHub's OIDC issuer) and identity (the central gate's publish workflow, at an allowed ref), the digest, the provenance (repository, commit, builder), the policy version, and the token's binding to that digest and environment. A valid signature alone is not trusted provenance. It consumes the token in one atomic step, attests with its KMS key, and fails closed when the authority or its state store is unavailable; Cloud Run admits only attested digests | CD-4, CD-6, the compliance authority as a service, the guard's KMS key |
| CD-8 | PI-3 | Negative tests (drills) | Each is refused, with evidence: a merge without approval; a direct push; a tampered artifact (digest mismatch); an unsigned image; a signature from another workflow or identity; an expired, mis-scoped, or replayed token; two concurrent consumers of one token (exactly one wins); an unattested `gcloud run deploy`; a deploy while the authority is down. Paths not yet tested are listed in the drill record, not implied covered | CD-7 |
| CD-9 | PI-2 | Delivery metrics | Deployment frequency, lead time, change failure rate, and time to restore computed from bus events, on a dashboard | CD-2, CD-6 |
| CD-10 | PI-2 | Delivery telemetry | Every publish and deploy emits a span, a log line, and a metric; a failed deploy alerts and opens an incident record | CD-2 |
| CD-11 | PI-2, PI-3 | Onboard every service | Each service repository sets its image target, publishes, and has its Cloud Run unit | CD-2, CD-5 |

The first slice is CD-1 to CD-4, which meets PI-2's release exit criterion.

### P0: one complete, verifiable lifecycle

The milestone is not a larger factory but a smaller, complete one. **P0 is met by one reproducible
run:** an approved spec, the Builder's change and pull request, the Reviewer's findings, the central
gate, a human-approved merge, the published digest with its SBOM, signature, and provenance, the
compliance decision bound to that commit, gate run, digest, and policy version, and an admitted
deploy, with no alternate release path. The same run's record shows the CD-8 refusals. Its evidence
(run IDs, digests, the decision, the notepad's sealed record) becomes the factory's case study.

**The first real workload is Genesis itself, from red to green.** Its central gate is red on legacy
code (CRITICAL dependency CVEs, HCL parse errors, failing Go and Python checks). Those failures are
not worked around, excepted, or archived: the agent loop takes them as its work queue and turns the
gate green through the same specs, pull requests, and human-approved merges as any change. The
bootstrap slice's pull requests merge once that gate is green.

### P1: the economics, measured

The objective is the cost of a safely accepted change, not token usage. On comparable tasks with the
same acceptance criteria, factory-assisted delivery is compared with a documented manual baseline:
time from approved requirement to accepted release, human intervention and correction time, defects
escaping the gate, total cost per accepted change, and recovery time after a failed run. Golden-task
and dogfood runs are reused rather than paying for new ones. The result is published with its
method, sample size, and limits.

## 8️⃣ Risks

- **Branch protection is the swing factor:** without it, no stage passes about 75. The plan now
  allows it on private repositories; it waits on the approver identity (Open Decisions).
- **Genesis depends on the agent loop,** and the Builder cannot yet write workflow YAML or Markdown.
  That capability is a PI-2 prerequisite for PI-3.
- **Cost:** a live telemetry backend and cloud backends add monthly spend; each rule is met with
  the cheapest option that meets it.

## Open Decisions

Recorded here until decided, each by a reviewed change to this document:

- **PI length:** two weeks while most work is hand-built, or four to six weeks once the agent loop
  and pilot users take part.
- **Approver identity:** GitHub forbids approving your own pull request, and with one maintainer
  every change is authored by that maintainer, so "require an approving review" cannot be met
  (`docs/incidents/2026-10-26-INC-001-no-branch-protection.md`). The factory's developers are its
  agents; the person is the approver. Recommended: each agent authors under its own identity (a
  GitHub App, free: the Builder, and the coding assistant for hand-built work), and the person
  approves and merges, as the factory's design intends. Until then, protection requires a pull request,
  the gate checks, and no force-push or deletion, without a review count.

## Decided

Each was decided by the reviewed change that moved it here.

- **Branch protection route (2026-10-29): a paid plan.** GitHub Pro; every factory repository
  stays private, and only the playbook is public.
- **Genesis's red gate (2026-10-29): dogfooded, not worked around.** The agent loop takes Genesis
  from red to green as the factory's first real workload (P0, §7). The legacy code stays.

- **Release signing (2026-10-29): keyless.** Images are signed with the pipeline's OIDC identity
  (Sigstore), so no signing key exists to leak. Accepted: repository and workflow names appear in
  the public transparency log, including before the repositories go public.
- **Registry (2026-10-29): in Genesis's bootstrap slice.** Nothing ships without it, so it is
  built with the rest of the bootstrap, as IaC, rather than waiting for the agent loop.
- **Deploy enforcement (2026-10-29): the deployment guard and Cloud Run Binary Authorization.**
  A pipeline check alone leaves `gcloud run deploy` as a bypass. Binary Authorization on Cloud Run
  verifies attestations signed with a key, not keyless signatures, so the guard verifies the keyless
  signature, provenance, and token, then attests with a Cloud KMS key only its identity can use.
  That key joins the registry in the bootstrap slice.
- **Promotion (2026-10-29): an environment repository.** Each promotion is a pull request; staging
  and production merges are human-approved and branch-protected. No deploy button.
- **Event bus (2026-10-29): build on the interface now.** Delivery stages hand off through the bus
  interface with its local adapter, so nothing is rewired when the backbone lands.

---

## Principle

Score only what runs, set each stage a number, and build first what makes everything after it
cheaper.
