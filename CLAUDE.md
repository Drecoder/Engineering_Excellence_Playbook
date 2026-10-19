# CLAUDE.md

Instructions for Claude Code (and, via `AGENTS.md`, other agents) when writing or reviewing code.

This file is the canonical rule set of the **Engineering Excellence Playbook**
(`github.com/Drecoder/Engineering_Excellence_Playbook`). It is vendored into consumer repos as
`.playbook/CLAUDE.md` and `.playbook/AGENTS.md` by CI (see
`00_UniversalStandards/05_Standards_Distribution.md`), so **keep every rule repo-agnostic**.
All doc paths below refer to the playbook repo.

See `README.md` for the full principles/philosophy and `00_UniversalStandards/` →
`06_AgentZone/` for the detailed zone docs. The rules below are the enforceable, mechanical
subset (IaC and Node/TypeScript). They narrow the general philosophy in
`03_InfrastructureZone/01_IaC_Standards.md` (plus `01a_GCP_Specifics.md` /
`01b_AWS_Specifics.md`) and `02_BackendZone/` to concrete gates.

## IaC Rules

- Use **Terragrunt** (HCL) to orchestrate Terraform — do not call bare `terraform` directly
  in new work.
- Keep state configuration DRY: define backend/provider config once in a root `terragrunt.hcl`
  and have child `terragrunt.hcl` files `include` it rather than repeating backend blocks.
- Keep modules isolated — a module must not reach into another module's state or resources
  directly; pass values across modules via `dependency` blocks / outputs only.
- Never mix a **structural** change (moving/renaming resources, splitting modules, changing
  state layout) with a **behavioral** change (changing resource arguments/behavior) in the
  same refactor step. Split them into separate commits/PRs so `terragrunt plan` stays easy to
  read and diff.

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

## Agent Rules

Rules for the Builder / Reviewer agents and any future agent in the control plane (rationale in
`06_AgentZone/01_Agent_Standards.md`).

- **Plan, never apply.** Agents may run `terragrunt plan` / `validate` only. `apply` runs in a
  separate post-merge pipeline with its own scoped identity and is never exposed as an agent tool.
- **Schemas at every boundary.** Agent inputs, outputs, and tool arguments are defined as
  versioned JSON Schemas (`<name>.v<N>`) and validated at runtime; invalid payloads are rejected,
  not repaired.
- **Sandboxed tools.** File tools resolve paths inside a sandbox root and reject traversal;
  write tools restrict file extensions (e.g. `.hcl`, `.tf`). Shell tools are allow-listed commands,
  never free-form.
- **Bounded loops.** Every agent loop is a Governor: a configurable max attempt count, a timeout /
  `AbortSignal` per tool and model call, and a terminal `gave_up` status. The cross-agent
  self-correction loop is capped at **3 iterations**, then escalates to a human.
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
| `terragrunt hclfmt` | Format all HCL files |
| `terragrunt validate` | Validate HCL syntax and module wiring |
| `tflint` | Lint Terraform for provider-specific errors and conventions |
| `terragrunt plan` | Verify the intended infrastructure diff |
| `terragrunt show -json <planfile> \| jq ...` | No-destroy / no-replace gate on the plan JSON |
| `checkov` | Static security/compliance scan of IaC |
| `tsc --noEmit` | Strict type check |
| `npm test` | Run the Node/TypeScript test suite (incl. telemetry and golden-task tests) |
| `markdownlint "**/*.md"` | Lint playbook docs (mirrors the CI workflow) |
