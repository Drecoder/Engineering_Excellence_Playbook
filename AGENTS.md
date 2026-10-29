# AGENTS.md — Engineering Standards

The canonical, enforceable rule set of the **Engineering Excellence Playbook**
(`github.com/Drecoder/Engineering_Excellence_Playbook`). It applies to **everything that writes,
reviews, or runs code on the platform**:

- **Engineers**
- **Coding assistants** — Claude, Gemini, or any other; each tool reads this file directly or
  through a thin shim (e.g. `CLAUDE.md` imports it)
- **The platform's own agents and services** — Builder, Reviewer, rig, and anything added later.
  For these, the rules are enforced by platform controls (schemas, tool allow-lists, identities,
  `SEC-*` and gate policies), not by the agent reading this file

The rules are model- and vendor-neutral. This file is vendored into consumer repos as
`.playbook/AGENTS.md` by the playbook's GitHub Action, pinned per repo (see
`00_UniversalStandards/05_Standards_Distribution.md`), so **keep every rule repo-agnostic**.
All doc paths below refer to the playbook repo.

See `README.md` for the full principles/philosophy and `00_UniversalStandards/` →
`06_AgentZone/` for the detailed zone docs. The rules below are the enforceable, mechanical
subset (IaC and Node/TypeScript). They narrow the general philosophy in
`03_InfrastructureZone/01_IaC_Standards.md` (plus `01a_GCP_Specifics.md` /
`01b_AWS_Specifics.md`) and `02_BackendZone/` to concrete gates.

## IaC Rules

- Use **Terragrunt** (HCL) to orchestrate Terraform — do not call bare `terraform` directly
  in new work. This includes bootstrap units (`live/_bootstrap/…`).
- Every Deployment Unit declares a class: `persistent` or `ephemeral`. Ephemeral units carry a
  TTL label, are destroyed only through the apply pipeline, and are swept by a scheduled cleanup.
- Keep state configuration DRY: define backend/provider config once in a root `root.hcl`
  and have child `terragrunt.hcl` files `include` it rather than repeating backend blocks.
- Keep modules isolated — a module must not reach into another module's state or resources
  directly; pass values across modules via `dependency` blocks / outputs only.
- Never mix a **structural** change (moving/renaming resources, splitting modules, changing
  state layout) with a **behavioral** change (changing resource arguments/behavior) in the
  same refactor step. Split them into separate commits/PRs so `terragrunt plan` stays easy to
  read and diff. Sequence refactors per `00_UniversalStandards/06_Module_Refactor_Framework.md`.

## TypeScript / Node Rules

- Enforce strict type checking: `tsc --noEmit` must pass with `strict: true` in `tsconfig.json`
  before work is considered done.
- Exported interfaces are a platform contract (see `02_BackendZone/01_API_Architecture.md`) —
  never change their shape without updating all consumers in the same change, and never
  silently widen/narrow an exported type.

## Application Architecture Rules

How services are shaped (rationale in `02_BackendZone/05_Application_Architecture.md`).

- **Start as a modular monolith.** Split a module into its own service only for a measured reason
  (independent scaling, failure isolation, ownership, a different runtime or security boundary),
  recorded in the change that splits it.
- **Each service owns its data.** No other service reads or writes its store; data crosses
  boundaries only through versioned APIs or events.
- **No network call inside a database transaction.** Connection pools are sized with Little's Law
  and bounded like any Governor.
- **Schemas change by expand, then contract**, one reversible step per change; dropping the old
  shape is irreversible and always human-approved.
- **Events are published through a transactional outbox**; consumers record processed event IDs
  (inbox) and are safe to replay. Multi-service workflows are sagas with compensating actions, never
  distributed transactions.
- **Every queue states its ordering and DLQ policy**, and carries trace context in message headers.
- **Large payloads travel by claim check:** messages carry an object reference and its SHA-256;
  consumers verify the digest before use and dead-letter a mismatch.
- **Every remote call has a timeout**; retries only for idempotent operations, with backoff, jitter,
  and idempotency keys for writes.
- **Never cache an authorization decision** longer than the credential it rests on.
- **The rules are checked from one file.** Each rule has an `ARCH-*` ID in
  `schemas/architecture_rules.v1.json`. rig runs its static checks on the diff and its trace checks
  on the targeted test run's traces; the Reviewer's `architecture` lens rubric is generated from the
  same file, only for the rules matching what the unit touches. A span missing an attribute a check
  needs is unverifiable, never compliant.

## Container Rules

How work runs and how images are built (rationale in `00_UniversalStandards/12_Containers.md`).

- **Everything runs in a pinned container.** Builds, tests, linters, scanners, benchmarks, and
  verification run in a container image pinned by digest, the same image locally and in CI. A
  result names the image it ran in; a result from host-installed tools is provisional.
- **Pin completely:** base images by digest, packages by exact version with a lockfile, downloaded
  binaries by checksum. Tools with conflicting dependencies get separate environments.
- **Images are multi-stage, minimal, stateless, and non-root**, run one process in exec form, take
  configuration from the environment, and are built once and promoted by digest.
- **No secrets in images** (`ENV`, `ARG`, or layers); use build secrets and a secret manager.

## CI Rules

One factory for every repository's gates (rationale in `00_UniversalStandards/15_Central_CI.md`).

- **CI lives in one reusable workflow:** `Drecoder/sovereign-vpc-gcp/.github/workflows/gates.yml`.
  A consumer has one caller file that calls it and passes inputs. No per-repo or per-module CI, no
  copied setup steps, no caller-local actions (`./.github/actions/...`).
- **Callers pin it to a full commit SHA,** never a tag or a branch, and repin through a reviewed
  pull request. After a squash merge, callers repin to the merge commit.
- **The factory is self-contained:** it installs its own pinned, checksum-verified toolchain, keeps
  gate tools and project dependencies in separate environments, and reads nothing from the caller
  but its code and configuration files.
- **Inputs are a contract** (`runs-on`, `fixture-paths`, `exclude-paths`, `run-tests`,
  `install-bubblewrap`, `single-job`): never renamed, removed, or repurposed without updating every
  caller. A caller that needs more asks for an input.
- **Every vulnerability scanner goes through one severity gate** (CRITICAL or CISA KEV, failing
  closed).
- **Scanners see all code.** Frozen copies and fixtures skip only the build gates (format, lint,
  type check, tests) through `fixture-paths`. Every scanner still scans them, and a real finding
  there blocks like any other. `exclude-paths` hides code from every gate except secret scanning,
  so it needs a reviewed reason.
- **Every job is bounded** by `timeout-minutes`. A job's timeout does not cover time waiting in the
  queue, so queued-job age needs its own alert.
- **Write each gate's script once.** A gate's script is shared by every job shape. On a runner pool
  that starts a fresh VM per job, the gates run as one job (`single-job`); on hosted runners they
  run as parallel jobs per stack.
- **Fix CI failures in the factory,** and test a factory change through each consumer's repin
  pull request before it merges.

## Supply Chain Rules

Know what goes into every artifact and prove where it came from (rationale in
`00_UniversalStandards/13_Supply_Chain.md`).

- **Pin every input:** packages by exact version in a committed lockfile, base images by digest,
  downloads by checksum or signature, actions by commit SHA. Update pins through gated pull
  requests, never through floating ranges.
- **Every released artifact has an SBOM** and a keyless signature from the pipeline's identity,
  with provenance; deploys admit only artifacts whose signature verifies.
- **Licenses are checked against a reviewed policy** (`schemas/license_policy.v1.json`); a denied
  license blocks, and a review-required or unknown one goes to a person.

## Test Quality Rules

A passing suite counts only if its tests could fail (rationale in
`00_UniversalStandards/14_Test_Quality.md`).

- **No committed `.only` or `.skip`, and every test asserts**; expected failures are asserted
  precisely.
- **Changed-line coverage is reported** on every pull request and each repository holds its
  coverage floor; **mutation score** is tracked with a floor. The floors live in each repository's
  `.ci/quality.v1.json` (`schemas/quality.v1.schema.json`); a missing file fails the gate closed.
- **A flaky test is a defect:** rerun once at most, then fixed or quarantined with an owner.

## Anti-Pattern Rules

One catalog, two consumers (rationale in `00_UniversalStandards/11_Anti_Pattern_Catalog.md`;
catalog in `schemas/antipatterns.v1.json`).

- **rig and the Reviewer read the same catalog** and normalize detector hits to
  `antipattern_finding.v1` identically, proven by the shared conformance vectors.
- **Map existing tools before writing checks.** A custom rig check exists only where no tool covers
  the pattern, and is marked `custom`.
- **Anti-pattern findings are advisory and never block** in v1. The CI gate's own thresholds are
  unchanged by the catalog.
- **Verified means run:** a mapping is `verified` only when the tool ran on the rule's positive and
  negative cases in the pinned toolchain image. Promotion needs measured precision, never an
  assumption.

## Observability Rules

Telemetry ships with the first line of code, not after the feature works (see
`02_BackendZone/04_Telemetry_Standards.md`, `docs/RED_METHOD.md`, `docs/USE_METHOD.md`,
`metrics/promql/MASTER_INDEX.md`).

- Every new service or agent emits **traces, metrics, and logs** through the OpenTelemetry SDK
  (`@opentelemetry/sdk-node`) over OTLP. Telemetry setup loads before any application code.
- Never hard-code collector endpoints or credentials — configure via `OTEL_SERVICE_NAME`,
  `OTEL_EXPORTER_OTLP_ENDPOINT`, and `OTEL_EXPORTER_OTLP_HEADERS` only.
- Logs are structured JSON and carry `trace_id` / `span_id` so every log line links to its trace.
- Every service exposes RED metrics (rate, errors, duration histogram). Every Governor exposes
  `governor_active_tasks`, `governor_max_limit`, and `governor_wait_duration_seconds` per
  `00_UniversalStandards/04_CONCURRENCY_GOVERNORS.md`.
- LLM calls are spans using the OTel GenAI conventions (`gen_ai.request.model`,
  `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`) and increment a token/cost counter.
- Instrument through a shared wrapper (e.g. `traced(name, attrs, fn)`) — do not hand-roll spans
  inside business logic.
- A metric or span name is a contract like an exported interface: renaming one requires updating
  its dashboards and alerts in the same change.
- New metrics are added to `metrics/promql/MASTER_INDEX.md`.
- **The platform instruments itself.** CI and its runners are services too: runner bootstrap
  failures, queued-job age, and failed applies are metrics with alerts. A failure found by a person
  looking is a finding in itself: its record adds the missing signal.
- **Evidence is telemetry.** A verification result (conformance test, chaos experiment, golden
  task) counts only when it exists as a span, a structured log line with `trace_id`, and a metric,
  not only as a file or a screenshot.
- **Every failure and near miss gets an incident record** in the affected repo's `docs/incidents/`,
  in the post-mortem format (`00_UniversalStandards/03_Post_Mortem_Template.md`), with checkable
  evidence pointers (run IDs, log queries, trace IDs, PRs).

## Governance Rules

Governance comes before everything: the playbook defines the guardrails, Genesis enforces them per
cloud, and services are built inside them (rationale in
`00_UniversalStandards/08_Governance_Guardrails.md`; baseline in
`schemas/governance_baseline.v1.json`).

- Every cloud project and account lives in the governance hierarchy (Organization → folder or OU).
  A standalone project inherits no guardrails and is a finding.
- `GOV-*` guardrails are enforced by the cloud control plane (GCP org policies, AWS SCPs) and
  implemented **only** in Genesis, from the vendored baseline. A service repo never creates,
  changes, or excepts an org policy or SCP.
- Every new or changed guardrail is staged in dry run, then promoted to the target mode in the
  baseline through a reviewed change, and only on a cloud where it has reached
  `adversarially_verified` (real denied attempts through every known bypass path, the exception
  path, and the authorization boundary). Verified is not enforced: enforcement is live state Genesis
  observes, never a claim in the contract.
- The baseline is validated against `schemas/governance_baseline.v1.schema.json`; an invalid
  baseline is rejected, not repaired.
- A verification stage advances only on evidence with every signal the baseline's `evidence` block
  requires (span, log, metric). Governance incidents (a control that failed to deny, a drift event,
  an exception misused) get incident records like any other failure.
- Exceptions live in Genesis's reviewed exceptions file, at the narrowest scope, with an owner, a
  reason, and an expiry.
- Only Genesis's apply identity can change guardrails; Genesis merges need human approval.
- New services are vended by Genesis into the hierarchy, not hand-built.

## Reuse Rules

Say each thing once, in the right place (rationale in `00_UniversalStandards/09_Reuse_and_DRY.md`;
the reuse map is rig's `schemas/symbol_index.v1.json`).

- **Extract on the third copy, or the second for security code and contracts.** Prefer duplication
  over an abstraction that needs flags and special cases to fit its callers.
- **Two scopes.** `internal` = inside one declared boundary (TS package, Go module, Python package,
  Terraform module); `shared` = exported symbols in `packages/` or `schemas/`, or marked `@shared`.
  Undeclared or ambiguous is `internal`. Exported is not shared.
- **Never import another boundary's `internal` symbol.** Promotion to `shared` is its own reviewed
  change.
- **The reuse map is generated, never hand-written,** by rig on every merge. Agents get a slice of
  it, never the whole index, and never see another boundary's internals.
- **Contracts have one home:** the playbook's `schemas/`, vendored as `.playbook/schemas/`. A copy
  of a contract or an exact reuse of a string contract (metric, span, env var, label name) blocks.
- **Across languages, share the spec and test vectors, not code.**
- **DRY findings are fixed in the same PR** when deterministic (a clone, or a hash or signature
  match against the reuse map); the fix stays inside the PR's files.

## Autonomy Rules

A person leaves a process step only when the evidence shows the step is stable, capable, and better
without them (rationale in `00_UniversalStandards/10_Autonomy_by_Evidence.md`; policy in
`schemas/autonomy_policy.v1.json`). The long-term target is Six Sigma (3.4 defects per million);
current volume cannot demonstrate it, so promotion uses explicit interim targets that tighten as
volume grows.

- Autonomy is granted per process class, one level at a time (L0 manual to L4 unattended), through
  a reviewed change to the policy. It is never granted globally or by assumption.
- **Never automate a broken process:** a class must be in statistical control, meet its interim
  defect-rate target at 95% confidence, and (L3 and above) pass self-stop drills before promotion.
- **Measure the human before removing the human:** promotion past a human step needs evidence that
  the step is an unreliable gauge, adds no detection, is the bottleneck, or introduces defects. A
  human step that catches what machines miss stays.
- **Protected classes never exceed L2:** security, ethics, irreversible changes, and merges to
  staging and production. Membership is decided deterministically and fails closed.
- **Demotion is automatic:** an out-of-control signal, an incident traced to the class, or a failed
  self-stop drill drops the class one level, with an incident record.

## Security Rules

Security in depth: every layer assumes the one before it can fail (rationale and the `SEC-*`
policy list in `00_UniversalStandards/07_Security_In_Depth.md`).

- **Session lifetimes:** cloud credentials (human and workload) live 1 hour by default and at most;
  longer needs a reviewed exception. Sign-in sessions re-authenticate within 24 hours (AAL2; 8 hours
  by default), and within 12 hours for prod/admin access (AAL3, phishing-resistant MFA).
- **People:** SSO with MFA; no shared accounts; staging and prod merges need human approval,
  enforced by branch protection on the merge (no bypass, admins included) — not by a manual
  deploy button.
- **Workloads and agents:** short-lived federated identity only — never static keys or service
  account keys; trust policies pin repo, branch, and environment.
- **CI least privilege:** workflows default to `permissions: contents: read` and grant more per
  job. Shared reusable workflows are reachable only by the owning user/org (never public), receive
  secrets explicitly (never `secrets: inherit`), and are pinned by callers to a full commit SHA.
- **In transit:** TLS 1.2+ on every connection; service-to-service traffic (including telemetry)
  is authenticated with mTLS or signed tokens; webhooks are signature-verified.
- **At rest:** storage is encrypted (customer-managed keys where classification requires) and
  public access is blocked by default; state buckets are encrypted, versioned, and access-logged.
- **Enforced as code:** `SEC-*` policies run on every plan; a failing policy blocks the change.
  Exceptions live in a reviewed policy file with an owner and an expiry.
- **Gates block on critical only:** scanners block on CRITICAL severity or any CISA KEV entry;
  pass/fail checks (format, lint, type check) and `SEC-*` always block. Below-critical findings
  are counted on a dashboard, never shown in the pull request (see
  `00_UniversalStandards/07_Security_In_Depth.md`).

## Agent Rules

Rules for the Builder / Reviewer agents and any future agent in the control plane (rationale in
`06_AgentZone/01_Agent_Standards.md`).

- **Actors hold judgment; tools hold capability.** An agent (actor) holds the loop and the
  decisions; the things it calls (scanners, analysis, the IaC engine) are tools that take typed
  input and return typed output. A tool holds no loop, decides nothing about what to do next, and
  never applies. Dependencies point one way — actor → tool, never the reverse. Actor logic found
  inside a tool is moved up into the caller (a sanctioned refactor), not left in place.
- **The builder never authorizes its own release.** At scoping it may read the compliance criteria
  and dry-run its submission (advisory only); evaluation and release tokens come from the independent
  compliance authority, and the deploy boundary consumes each token once
  (`06_AgentZone/02_Compliance_Engine.md`).
- **Target design: the Builder and the Reviewer hand off through events.** `review.requested` and
  `review.completed` on the event backbone, with claim-checked objects kept as the triage history;
  the request is data, never the Reviewer's prompt. Not implemented yet; today the handoff is the
  pull request (`06_AgentZone/05_Review_Loop.md`).
- **Target design: every agent works through an injected notepad.** Each agent gets a folder per
  task; agents write only their own regions, tool results land read-only in the caller's folder,
  each push seals a read-only version named in the commit, and agents never read another agent's
  folder. Code stays in the repository. Not implemented yet (`06_AgentZone/07_Agent_Notepad.md`).
- **Work enters only as an approved spec.** The Builder starts from a `spec.approved` event on its
  queue, fetches the spec object, and verifies its digest; the approval names one exact spec
  version (`06_AgentZone/03_Software_Factory_Intake.md`).
- **Plan, never apply.** Agents may run `terragrunt plan` / `validate` only. `apply` runs in a
  separate post-merge pipeline with its own scoped identity and is never exposed as an agent tool.
- **Schemas at every boundary.** Agent inputs, outputs, and tool arguments are defined as
  versioned JSON Schemas (`<name>.v<N>`) and validated at runtime; invalid payloads are rejected,
  not repaired.
- **Sandboxed tools.** File tools resolve paths inside a sandbox root and reject traversal;
  write tools restrict file extensions (e.g. `.hcl`, `.tf`). Shell tools are allow-listed commands,
  never free-form.
- **Bounded loops.** Every agent loop is a Governor: a configurable max attempt count, a **token
  budget per change**, a timeout / `AbortSignal` per tool and model call, and a terminal `gave_up`
  status. PR review rounds end at no blocking findings, **round 4**, or a **stalled** round (no
  finding fingerprints resolved) or **oscillating** round (a resolved fingerprint reintroduced),
  then escalate to a human. Only blocking findings and deterministic DRY findings start a round.
  Round 4 is headroom: the expected outcome is 3 rounds or fewer (`review_loop_rounds` p90 ≤ 3).
- **Classify build failures before fixing.** rig classifies each failure
  (`build_failure.v1`); only `code` and `config` failures reach the Builder. `infra` and `unknown`
  go to a human, `flaky` gets one rerun, `mechanical` gets a deterministic auto-fix.
- **Evidence is requested, never fetched by the model.** Models emit declarative
  `evidence_request.v1` (`symbol_context`, or `run_tests` on symbols, never commands); code
  validates and fulfils them. At most 2 model calls and 1 evidence round per review unit.
- **Lenses, not extra agents.** Reuse, security, and architecture are Reviewer lenses. Deterministic security
  tools block; the security lens escalates to required human approval and never blocks by itself.
- **Gates before PRs.** The Builder opens a PR only after the no-op, scope, duplicate, and
  rig-scan gates pass (plus self-review when enabled).
- **AI review advises; humans approve.** Merges to staging and prod require human approval.
  Auto-merge is limited to process classes promoted to L3 or above under Autonomy Rules, never to
  a protected class.
- **Third-party coding agents are allowed only behind the same invariant.** A platform-external
  agent (e.g. GitHub Copilot) may **propose** — open a PR, push to a PR branch — but its output
  passes the same deterministic gates and the same human-approved merge, and never bypasses them.
  Branch protection is what enforces this for every agent, ours and theirs alike.
- **Model weight is a ladder, not a tier.** Rules, then a complexity assessor, produce a continuous
  difficulty score that selects the cheapest model that fits (config-driven rungs); the fail-closed
  ceiling forces the top rung. Spend compute proportional to difficulty
  (`06_AgentZone/01_Agent_Standards.md` §6).
- **The complexity assessor answers complexity, never routing.** It reads rig's `features.v1` (never
  raw code) and judges the change; policy code maps its answers to the rung, the lenses, and whether
  evidence may be fetched.
- **Spend tokens only where code cannot decide.** Rules run before any router or model; a model
  step stays only if its metrics show it improves outcomes.
- **Models are injected.** Agents depend on a provider-agnostic model interface; the provider and
  model come from configuration. Every configured model setting must reach the call.
- **Prompts are versioned files.** Untrusted input is delimited and treated as data; outputs that
  code consumes are schema-validated; the context window is set explicitly.
- **Agents never notify people directly.** They set PR labels; a notification service routes them
  (`06_AgentZone/01_Agent_Standards.md` §8).
- **Fail closed.** Routing or risk classification that is unknown, malformed, or below the
  confidence threshold resolves to the highest-scrutiny path. Changes touching IAM or state
  (`moved` blocks, replacements, deletes) always take the highest-scrutiny path, decided from the
  `plan` JSON — not from model output.
- **No secrets in context.** Credentials never enter prompts, tool outputs, logs, or span
  attributes. Cloud access uses short-lived federated identity (OIDC / Workload Identity
  Federation), never static keys.
- **Deterministic gates first.** A model's verdict never overrides a failing CLI gate
  (`tflint`, `checkov`, no-destroy check).
- **Golden tasks.** Each agent keeps a fixed set of golden tasks (including at least one
  designed-to-fail task) that must pass before a change to its prompt, tools, or model ships.

## Local Validation Commands

Run the relevant commands before calling IaC or Node/TypeScript work complete:

| Command | Purpose |
| :--- | :--- |
| `terragrunt hcl fmt` | Format all HCL files |
| `terragrunt validate` | Validate HCL syntax and module wiring |
| `tflint` | Lint Terraform for provider-specific errors and conventions |
| `terragrunt plan` | Verify the intended infrastructure diff |
| `terragrunt show -json <planfile> \| jq ...` | No-destroy / no-replace gate on the plan JSON |
| `checkov` | Static security/compliance scan of IaC |
| `tsc --noEmit` | Strict type check |
| `npm test` | Run the Node/TypeScript test suite (incl. telemetry and golden-task tests) |
| `markdownlint "**/*.md"` | Lint playbook docs (mirrors the CI workflow) |
