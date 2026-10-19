# Agent Standards
*Agents are services. They follow the same lifecycle, contracts, and observability rules — plus
guardrails for the fact that their decisions come from a model.*

The enforceable subset lives in `CLAUDE.md` → **Agent Rules**. This doc explains the why and the
shape of each rule.

---

## 1️⃣ Philosophy

- An agent is a **flow participant**: bounded, observable, and recoverable like any worker.
- **Deterministic gates first, models second.** A model may propose; only CLI gates and
  schemas decide.
- **Least privilege applies to tools.** An agent can only do what its tools allow, so the tool
  list is the agent's IAM policy.
- **Build one agent at a time.** Each agent must pass its own golden tasks standalone before it
  is wired into a multi-agent loop.

---

## 2️⃣ Agent Anatomy

| Part | Standard |
| :--- | :--- |
| **Input contract** | Versioned JSON Schema (`<agent>.spec.v<N>`), validated on receipt; invalid input is rejected |
| **Tools** | Small, allow-listed set; each tool has its own argument schema and guardrail |
| **Loop** | A Governor: max attempts, per-call timeout / `AbortSignal`, terminal `gave_up` status |
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
| Network | Egress limited to the endpoints the agent needs |

Secrets never enter prompts, tool outputs, logs, or span attributes.

---

## 4️⃣ Risk Routing

Review work is routed by risk, not by habit:

| Tier | Handles | Examples |
| :--- | :--- | :--- |
| **TIER_0 — Deterministic** | Zero-diff or low-risk changes | `tflint`, `checkov`, plan no-destroy gate |
| **TIER_1 — Private SLM** | Utility work with no state or IAM impact | Docs, formatting, simple non-state edits |
| **TIER_2 — Frontier LLM** | IAM, state, multi-file or high-complexity changes | `moved` blocks, replacements, policy changes |

Routing rules:

1. **Hard overrides first.** IAM or state impact (taken from the plan JSON) → TIER_2.
2. **Fail closed.** Unknown, malformed, or low-confidence classification → TIER_2.
3. A model verdict never overrides a failing TIER_0 gate.

---

## 5️⃣ Loops and Escalation

- **Inner loop** (inside one agent, e.g. fixing its own plan errors): bounded by the agent's
  max attempts; ends in `plan_ok`, `plan_failed`, or `gave_up`.
- **Outer loop** (between agents, e.g. Reviewer → Builder): capped at **3 iterations**, then
  escalates to a human with the full trace link.
- Loop counts are metrics, so runaway behavior shows up on dashboards before it shows up in cost.

---

## 6️⃣ Golden Tasks and Change Control

Every agent keeps a fixed suite of golden tasks:

- 3–5 representative tasks that must succeed
- At least one task designed to fail, which must end in a clean `gave_up` / rejection
- A telemetry assertion: the expected spans and attributes are emitted

Changing an agent's **prompt, tools, model, or routing thresholds** is a behavioral change:
it ships only after the golden suite passes, in its own PR, with before/after results attached.

---

## 7️⃣ Principle

An agent earns autonomy by being **bounded, typed, and observable** — not by being clever.
