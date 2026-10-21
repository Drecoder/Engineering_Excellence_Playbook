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
  baseline through a reviewed change, and only on a cloud where its conformance test (a real
  denied attempt through every known path, plus one allowed action) passes.
- The baseline is validated against `schemas/governance_baseline.v1.schema.json`; an invalid
  baseline is rejected, not repaired.
- Exceptions live in Genesis's reviewed exceptions file, at the narrowest scope, with an owner, a
  reason, and an expiry.
- Only Genesis's apply identity can change guardrails; Genesis merges need human approval.
- New services are vended by Genesis into the hierarchy, not hand-built.

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
  secrets explicitly (never `secrets: inherit`), and are pinned by callers to a tag or SHA.
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
  status. PR review rounds end at no blocking findings, **round 3**, or a **stalled** round (no
  finding fingerprints resolved), then escalate to a human. Only blocking findings start a round.
- **Gates before PRs.** The Builder opens a PR only after the no-op, scope, duplicate, and
  rig-scan gates pass (plus self-review when enabled).
- **AI review advises; humans approve.** Merges to staging and prod require human approval.
  Auto-merge is limited to explicitly allow-listed low-risk paths.
- **Third-party coding agents are allowed only behind the same invariant.** A platform-external
  agent (e.g. GitHub Copilot) may **propose** — open a PR, push to a PR branch — but its output
  passes the same deterministic gates and the same human-approved merge, and never bypasses them.
  Branch protection is what enforces this for every agent, ours and theirs alike.
- **Model weight is a ladder, not a tier.** Rules/Jev emit a continuous difficulty score that
  selects the cheapest model that fits (config-driven rungs); the fail-closed ceiling forces the
  top rung. Spend compute proportional to difficulty (`06_AgentZone/01_Agent_Standards.md` §6).
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
