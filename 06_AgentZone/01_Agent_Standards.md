# Agent Standards

*Agents are services. They follow the same lifecycle, contracts, and observability rules — plus
guardrails for the fact that their decisions come from a model.*

The enforceable subset lives in `AGENTS.md` → **Agent Rules**. This doc explains the why and the
shape of each rule.

---

## 1️⃣ Philosophy

- An agent is a **flow participant**: bounded, observable, and recoverable like any worker.
- **Deterministic gates first, models second.** A model may propose; only CLI gates and
  schemas decide.
- **Spend tokens only where code cannot decide.** Anything a linter, scanner, parser, policy, or
  template can do is TIER_0 and costs zero tokens. A model step must earn its place with a metric.
- **AI review advises; humans approve.** Deterministic gates block, AI review recommends, and a
  human approves every merge to staging and prod.
- **Least privilege applies to tools.** An agent can only do what its tools allow, so the tool
  list is the agent's IAM policy.
- **Build one agent at a time.** Each agent must pass its own golden tasks standalone before it
  is wired into a multi-agent loop.

---

## 1️⃣a Actors and Tools

The platform separates **actors**, which hold judgment, from **tools**, which hold capability.
The split repeats at every layer: an agent is an actor and its scanners are tools; the platform
is an actor and its infrastructure engine is a tool.

| | Actor | Tool |
| :--- | :--- | :--- |
| Holds | The loop, the decision of what to do next, model-backed judgment | One capability, called and returned |
| Examples | Builder, Reviewer, the platform (agents + approval + pipeline) | rig (scan, reason), the IaC engine (plan) |
| Must not contain | Raw mechanism it could call a tool for | A loop, a decision about what to do, any `apply` / write of record |
| Surface | Versioned input/output contracts; golden tasks | A versioned callable: typed input → typed output |

Three rules:

1. **Tools hold no judgment.** A tool is called, runs its one capability, and returns a typed
   result. It never decides what to work on next, and it never applies.
2. **Actors hold no raw mechanism.** An actor calls a tool rather than embedding the capability,
   so judgment and capability stay independently testable.
3. **Dependencies point one way: actor → tool, never the reverse.** A tool never imports its
   caller (the IaC engine never imports the agents; a scanner never imports the platform).

**Demoting an actor to a tool is a sanctioned refactor.** Capabilities built as agents during an
earlier design (their own loop, their own autonomy) are expected to become tools as the system
matures. When actor logic is found inside a tool, the standard is to **move it up** into the
calling actor — not to leave it — following `00_UniversalStandards/06_Module_Refactor_Framework.md`.
The result is a smaller, deterministic, testable callable.

---

## 2️⃣ Agent Anatomy

| Part | Standard |
| :--- | :--- |
| **Input contract** | Versioned JSON Schema (`<agent>.spec.v<N>`), validated on receipt; invalid input is rejected |
| **Tools** | Small, allow-listed set; each tool has its own argument schema and guardrail |
| **Model** | Injected behind a provider-agnostic interface; chosen by configuration, never hard-coded |
| **Loop** | A Governor: max attempts, max turns, token budget, per-call timeout / `AbortSignal`, terminal `gave_up` status |
| **Output contract** | Versioned JSON Schema (`<agent>.result.v<N>`), validated before it leaves the agent |
| **Telemetry** | One trace per task; spans per model and tool call; metrics per `02_BackendZone/04_Telemetry_Standards.md` |
| **Identity** | Short-lived federated credentials scoped to the agent's tools only |

---

## 3️⃣ Tool Guardrails

| Tool type | Guardrail |
| :--- | :--- |
| File read / write | Paths resolved inside a sandbox root; traversal rejected; write extensions allow-listed |
| Shell / CLI | Fixed allow-listed commands with typed arguments — never free-form shell |
| IaC | `plan` and `validate` only. `apply` is not an agent tool; it runs in the post-merge pipeline |
| Analysis (e.g. rig-scan) | Read-only; returns normalized `findings.v1`; never writes code |
| Network | Egress limited to the endpoints the agent needs |

Secrets never enter prompts, tool outputs, logs, or span attributes. Only the Builder writes
code; analysis tools and reviewers return findings, never patches.

---

## 4️⃣ Models and Providers

- Agents depend on a **model interface**, not a vendor SDK. Each provider (Claude on Bedrock,
  Bedrock Converse, Ollama, Vertex) is an adapter with its own contract tests; a factory picks one
  from configuration (`MODEL_PROVIDER`, `MODEL_ID`).
- Adapters must not bake in one model's assumptions (default model, effort, fallback chain).
  Model-specific settings are configuration.
- Provider-specific state the provider requires verbatim (e.g. thinking blocks) is carried as
  opaque content and replayed untouched by the adapter that produced it.
- **Small models do single-shot work** — summarize, explain, classify, check intent. Multi-step
  tool loops use frontier models.
- Every setting in config must reach the model call. Config that is declared but not wired
  (temperature, context window, output format) is a defect.

---

## 5️⃣ Prompts

- **Single-source, versioned, change-gated.** Every prompt has one home, no duplicate copies, is
  versioned (a change is a behavioral change per §9 and re-runs the golden suite). **Reusable
  "skill" prompts** — standalone, shared, or non-engineer-edited — live in files with ids
  (`explain_failure.v1`); a registry is required there. **Structural prompts** an agent owns in
  code — a builder's system prompt and per-stack scope/spec guidance — may stay centralized code
  constants, as long as they meet the same single-source and change-gated bar.
- **System vs user.** Stable rules go in the system prompt, phrased positively. The user turn
  carries only inputs.
- **Untrusted input is data.** Code, diffs, logs, and findings are wrapped in explicit delimiters
  (e.g. `<source_code>…</source_code>`) and described as data, never instructions.
- **Structured output.** Answers that code consumes are JSON validated against a schema (use the
  provider's structured-output / `format` option); code output is checked by a parser or compiler
  before it is used.
- **Context budget.** Set the context window explicitly and measure prompt size before sending;
  trim or fail loudly — never let the runtime silently truncate the instructions.
- **Few-shot from known-good outputs.** Use one short example per task where it helps; keep
  golden expected outputs as the eval set.
- **Checked by rig.** The violations of these rules are catalogued as `AP-AI-*` in
  `schemas/antipatterns.v1.json`: a prompt written at the call site, a model call without a context
  window, output cap, or timeout, undelimited untrusted input, unvalidated model output, and a model
  hard-coded at the call site. No existing linter knows these rules, so they are custom rig checks,
  planned until rig implements them.

---

## 6️⃣ Risk Routing

**Rules before routers.** Deterministic rules decide first; a **complexity assessor** handles only
what the rules leave. It reads rig's deterministic feature record (`schemas/features.v1.json`),
never raw code, and answers questions about **the change's complexity only**: conceptual
difficulty, hidden coupling, intent clarity, specialized knowledge, implicit state, and for build
failures, error interpretability and fix locality. It never answers routing questions (which rung,
which lens, whether to fetch evidence); the platform's **policy code** maps complexity to those, so
the mapping stays readable, versioned, and calibrated against outcomes.

- **Today:** a deterministic assessor. Conceptual difficulty is per-function **cognitive
  complexity** computed by rig with Sonar's published rules (validated by matching Sonar's file
  totals; Sonar stays the gate), combined with fan-in, scope, tags, and implicit-state constructs.
  Weights start hand-set and are later fitted to outcomes.
- **Later:** a decision model (e.g. TypeSafe's Jev, which returns typed values with calibrated
  probabilities) can sit behind the same interface, with the deterministic assessor as its
  fallback, once access exists and the benchmark shows it routes better.
- Its confidence feeds the fail-closed threshold below, and a non-empty `missing` list in the
  feature record fails closed.

Routing has **two axes**, kept separate: a coarse **scrutiny tier** (safety, rule-driven) and a
continuous **model weight** (cost, score-driven). Conflating them wastes money — a two-rung switch
throws away most of the router's signal.

### Scrutiny tier — safety, decided by rules

| Tier | Handles |
| :--- | :--- |
| **TIER_0 — Deterministic** | Gates, zero-diff, docs, policy (`tflint`, `checkov`, OPA, no-delete gate) — no model is called |
| **TIER_1 — Judgment** | A unit that needs a model's opinion, without IAM or state impact |
| **TIER_2 — Highest scrutiny / ceiling** | IAM, state, or any fail-closed case — always takes the top of the ladder |

1. **Gates first.** A failing TIER_0 gate returns to the Builder; no model is called.
2. **Hard overrides.** IAM or state impact (from the plan JSON, never model output) → TIER_2.
3. **Fail closed.** Unknown, malformed, or low-confidence classification → TIER_2.
4. A model verdict never overrides a failing TIER_0 gate.

### Model weight — a ladder, not a tier

Within the judgment path, the router emits a **continuous score** (rules first, then the complexity
assessor for what rules leave, mapped to a score by policy code). The score selects the **cheapest model on an ordered ladder** that fits the
difficulty; easy, high-confidence units take a small local SLM, and only hard units climb. The
fail-closed ceiling (TIER_2) forces the top rung. This is where cost is controlled — **compute
proportional to difficulty, not a frontier model for everything.**

- The ladder is **configuration** (ordered rungs with score bands and a model id per rung), not
  code; adding or reordering a rung is a config change.
- **Hosting follows the ladder** (`03_InfrastructureZone/01_IaC_Standards.md`): the low rungs stay
  **warm and cheap** (they serve most traffic); the top rungs run on **cold / spot GPU**, as an
  ephemeral DU with a TTL, since their latency tax is paid rarely.
- Each finding records the **actual model** that produced it; the score and rung are span
  attributes.

### How each agent consumes the ladder (they differ)

The picker is shared; the two agents use it differently, by design:

- **Builder — the edge model is home.** Its default is the **edge/frontier model**, because novel
  generation is cutting-edge and quality matters most. A build error, though, is often *not*
  cutting-edge, so a **fix task** is scored and gets a **ladder-assigned model proportional to the
  error** (cheap for a trivial fix). When the fix task finishes, the Builder **reverts to the edge
  model** — the downgrade is transient and per-task; the Builder never *stays* downgraded.
- **Reviewer — no home model.** It holds no default; **every unit is assigned a model** by the
  rig → Jev → ladder outcome. Pure ladder, model-per-unit.

Model selection happens at the **task boundary**, never mid-loop (a provider's opaque state, e.g.
thinking blocks, cannot move between models). A new generation task defaults to edge; a fix task
picks its rung from the score.

---

## 7️⃣ The Change Loop

### Pre-PR gates (Builder side)

The Builder opens a PR only after its change passes, in order:

| Gate | Blocks when | Cost |
| :--- | :--- | :--- |
| **No-op** | The plan has zero changes | Free |
| **Scope** | Files or resources fall outside the spec's `module_path` / Deployment Unit | Free |
| **Duplicate** | An open PR already has the same spec and plan fingerprint | Free |
| **rig-scan** | Blocking findings remain | Free |
| **Self-review** (feature-flagged) | rig-reason returns `revise`: the plan does not match the intent | TIER_1 |

Self-review returns `{verdict: pass | revise, reasons[]}`; `revise` reasons go back to the Builder
as tool feedback. It can only send work back — a `pass` never skips a later gate or the human.

### Build failures: classify before fixing

A failed build reaches the Builder only when it is the change's fault. rig parses the failure into
`schemas/build_failure.v1.json` and classifies it; the class decides routing before any model sees
it:

| Class | Route |
| :--- | :--- |
| `code`, `config` | Builder fix task (ladder rung from the assessor's complexity answers) |
| `mechanical` (formatting, lockfiles) | Deterministic auto-fix (`terragrunt hcl fmt`, `gofmt`); no model |
| `flaky` (a known transient pattern) | One automatic rerun, never more |
| `infra` (runner, permissions, provider, network) | A human, with an incident record; never the Builder |
| `unknown` | A human (fail closed) |

A recurring failure fingerprint marks a stalled fix; the next fix task reverts to the edge model.

### Review lenses and evidence

- The Reviewer reviews each unit through **lenses** (`blast`, `simple`, `chaos`, `benchmark`,
  `doc`, and the `reuse`, `security`, and `architecture` lenses); policy code picks which lenses
  apply from the complexity answers. Lenses are views of one Reviewer, not separate agents.
- **Security:** deterministic tools (secret scanning, `SEC-*`, injection rules, IAM from the plan
  JSON) **block**. The `security` lens **escalates**: a high-confidence finding sets a label that
  requires human approval, and never blocks by itself.
- **Reuse:** see `00_UniversalStandards/09_Reuse_and_DRY.md`. Deterministic DRY findings (a clone,
  or a hash or signature match against the reuse map) are fixed in the same PR; the lens's
  "looks similar" findings stay advisory.
- **Architecture:** the lens rubric is generated from `schemas/architecture_rules.v1.json`, only
  for the `ARCH-*` rules whose `applies_when` matches the unit's `features.v1` `structure.touches`;
  rig's static and trace hits for those rules, and catalog findings linked to them, go in as known
  findings (`06_AgentZone/04_Review_Lenses.md`, which specifies the lens). Deterministic hits on
  blocking rules block; the lens's findings are advisory, except a protected class (`ARCH-009`
  irreversible, `ARCH-022` security), which escalates
  (`02_BackendZone/05_Application_Architecture.md` §10).
- **Evidence, declaratively.** The model never calls tools. It emits `evidence_request.v1`
  (`symbol_context`, or `run_tests` on symbols, never commands); the orchestrator validates and
  fulfils it and appends `evidence_response.v1` (with provenance, limits, and uncertainty) to the
  unit's `review_context.v1`. At most **2 model calls and 1 evidence round per unit**. Runtime
  evidence is targeted test results; raw traces and state snapshots are added to the model's context
  only when the benchmark shows they pay for themselves. rig's deterministic trace checks are
  separate: they read the test run's traces in code and cost no tokens.

### PR review rounds

1. Each round, the Reviewer re-runs rig-scan independently, rig-reason checks intent, and TIER_2
   joins only for IAM or state. They post **one combined `review.findings.v1` comment** per round.
   The target design moves each round's request and findings onto the event backbone, with the
   objects kept as the triage history (`06_AgentZone/05_Review_Loop.md`, not implemented yet).
2. The Builder answers by pushing to the **same PR**.
3. **Only blocking findings and deterministic DRY findings start another round.** Other advisory
   comments go to the human. A DRY fix may only touch files already in the PR.
4. The loop ends when there are **no blocking findings**, after **round 4**, or when a round is
   **stalled** (it resolved none of the previous round's finding fingerprints) or **oscillating**
   (it reintroduced a fingerprint resolved in an earlier round). Stalls and oscillations escalate
   immediately, before round 4.
5. **Round 4 is headroom, not the plan:** the expected outcome is 3 rounds or fewer
   (`review_loop_rounds` p90 ≤ 3). A growing share of changes reaching round 4 points upstream:
   lens precision, the Builder's rung, or DRY churn. It is investigated, never answered by raising
   the cap.

### Budgets

Revise and review rounds count toward the agent's attempt and **token budget per change**;
exhausting either ends the task as `gave_up` and escalates.

---

## 8️⃣ Human in the Loop

- **Humans approve merges to staging and prod.** Auto-merge is allowed only on narrow, low-risk
  paths (e.g. dev, docs-only) and widened only when metrics justify it. "Metrics justify it" is
  defined in `00_UniversalStandards/10_Autonomy_by_Evidence.md`: per-class promotion on statistical
  control and demonstrated defect rates, with protected classes held at L2.
- **Agents never message people.** They set a PR label (`ready-for-human`, `needs-decision`);
  one notification service fans out:

| Situation | Channel |
| :--- | :--- |
| Clean and ready for approval | Pinned review-channel message + email (ticket level, no page) |
| Round 4 reached, stalled, or oscillating with findings left | Same, marked **needs decision**, findings listed |
| Prod, IAM, or state change; loop broken; budget exceeded | Also an **alert** |
| Approved or closed | Unpin; record the outcome in the thread |

The human sees one PR with the plan summary, remaining findings, rounds run and why the loop
stopped, token cost, and a trace link.

---

## 9️⃣ Supported Stacks

Agents build and verify in four languages — one **stack** each, matching the playbook zones:

| Stack | Writes | Verifies with (never deploys) |
| :--- | :--- | :--- |
| `iac` | HCL / Terraform | `terragrunt validate`, `terragrunt plan` (no delete/replace) |
| `typescript` | `.ts` / `.tsx` | `tsc --noEmit`, the test suite |
| `python` | `.py` | `mypy`, `pytest` |
| `go` | `.go` | `go vet`, `go build`, `go test` |

A new language is a new stack (its write allow-list, tools, terminal verify tool, and prompt
guidance) — never a change to the agent loop. Verification stops at plan / static-check + tests;
applying and deploying stay in the post-merge pipeline.

---

## 🔟 Golden Tasks and Change Control

Every agent keeps a fixed suite of golden tasks, **covering each stack it builds in**:

- 3–5 representative tasks per stack that must succeed
- At least one task per stack designed to fail, ending in a clean `gave_up` / rejection
- A telemetry assertion: the expected spans and attributes are emitted

Changing an agent's **prompt, tools, stacks, model, routing rules, or budgets** is a behavioral
change: it ships only after the golden suite passes, in its own PR, with before/after results.

---

## 1️⃣1️⃣ Measure Before Adding Model Steps

Every model-backed step reports whether it pays for itself:

| Metric | Answers |
| :--- | :--- |
| Cost (tokens, $) per merged change | Is the loop affordable? |
| Rounds per change; stalled-loop rate | Does the loop converge? |
| Findings resolved per round (by fingerprint) | Is each round making progress? |
| Self-review pass later rejected in PR | Does the self-review miss problems? |
| Self-review `revise` a human would have accepted | Does it block good work? |
| Human override rate of AI review | Is the advice trusted? |

A step whose metrics do not improve outcomes is removed.

---

## Principle

An agent earns autonomy by being **bounded, typed, and observable** — not by being clever.
