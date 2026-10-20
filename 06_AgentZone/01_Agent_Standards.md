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

- **One versioned registry per agent.** Prompts live in files with ids (`explain_failure.v1`);
  no duplicate inline copies. Changing a prompt is a behavioral change (see §9).
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

---

## 6️⃣ Risk Routing

**Rules before routers.** Deterministic rules decide first; a learned router (e.g. Jev) only
handles what the rules leave, and only once metrics show the rules route badly.

| Tier | Handles | Examples |
| :--- | :--- | :--- |
| **TIER_0 — Deterministic** | Gates, zero-diff, docs, policy | `tflint`, `checkov`, OPA, no-delete gate, `terraform-docs` |
| **TIER_1 — Private SLM** | Single-shot judgment without IAM or state impact | Intent check, plan summary, failure triage |
| **TIER_2 — Frontier LLM** | IAM, state, multi-file or high-complexity changes | `moved` blocks, replacements, policy changes |

Routing rules:

1. **Gates first.** A failing TIER_0 gate returns to the Builder; no model is called.
2. **Hard overrides.** IAM or state impact (taken from the plan JSON) → TIER_2.
3. **Fail closed.** Unknown, malformed, or low-confidence classification → TIER_2.
4. A model verdict never overrides a failing TIER_0 gate.

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

### PR review rounds

1. Each round, the Reviewer re-runs rig-scan independently, rig-reason checks intent, and TIER_2
   joins only for IAM or state. They post **one combined `review.findings.v1` comment** per round.
2. The Builder answers by pushing to the **same PR**.
3. **Only blocking findings start another round.** Advisory comments go to the human.
4. The loop ends when there are **no blocking findings**, after **round 3**, or when a round is
   **stalled** — it resolved none of the previous round's finding fingerprints.

### Budgets

Revise and review rounds count toward the agent's attempt and **token budget per change**;
exhausting either ends the task as `gave_up` and escalates.

---

## 8️⃣ Human in the Loop

- **Humans approve merges to staging and prod.** Auto-merge is allowed only on narrow, low-risk
  paths (e.g. dev, docs-only) and widened only when metrics justify it.
- **Agents never message people.** They set a PR label (`ready-for-human`, `needs-decision`);
  one notification service fans out:

| Situation | Channel |
| :--- | :--- |
| Clean and ready for approval | Pinned review-channel message + email (ticket level, no page) |
| Round 3 reached or stalled with findings left | Same, marked **needs decision**, findings listed |
| Prod, IAM, or state change; loop broken; budget exceeded | Also an **alert** |
| Approved or closed | Unpin; record the outcome in the thread |

The human sees one PR with the plan summary, remaining findings, rounds run and why the loop
stopped, token cost, and a trace link.

---

## 9️⃣ Golden Tasks and Change Control

Every agent keeps a fixed suite of golden tasks:

- 3–5 representative tasks that must succeed
- At least one task designed to fail, which must end in a clean `gave_up` / rejection
- A telemetry assertion: the expected spans and attributes are emitted

Changing an agent's **prompt, tools, model, routing rules, or budgets** is a behavioral change:
it ships only after the golden suite passes, in its own PR, with before/after results attached.

---

## 🔟 Measure Before Adding Model Steps

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
