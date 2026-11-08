# The Adaptive Harness

*An autonomous engineering system should not decide on model reasoning alone. It should also weigh
what the organization has learned, how the systems are behaving now, and what deterministic tools
measure in the code. It does this inside the same gates it enforces, and never authorizes itself.*

**Status: proposed.** This standard codifies an architectural hypothesis so that future
implementations have something to conform to. Nothing here is built. The contracts it names exist
as schemas with examples; their conformance cases, and every implementation, come after the
standard is approved (§12). It extends `08_Telemetry_Driven_Dynamics.md` (bounded steering),
`07_Agent_Notepad.md` §7 (memory), `00_UniversalStandards/17_Quality_Policy_Engine.md` (quality
decisions) and `01_Agent_Standards.md` §6–7 (routing, budgets). Where they and this page disagree,
they win and this page is the bug.

---

## 1️⃣ The Hypothesis

The **harness** is the loop that runs an agent's work: it decides the next bounded step of a task.
It weighs four kinds of input, never one alone:

1. **Organizational knowledge:** what has worked and failed before, from the retrieval index (§3).
2. **Operational state:** how the target service and the harness itself are behaving now (§5).
3. **Deterministic quality evidence:** the Evaluator's metrics and the Policy Engine's decision (§6).
4. **Governance state:** the task, its stage, its budget, its permissions and the policy in force.

It is context-aware without being self-authorizing. It is an engineering citizen of the platform:
observable, measured, bounded, auditable, and held to the standards it applies to others (§11).

## 2️⃣ Where It Sits

The harness is part of an **actor**: it holds the loop and its decisions (`01_Agent_Standards.md`
§1a). The Evaluator, the Policy Engine and the index are tools it calls. It replaces none of them.

![The adaptive harness among the factory's parts: the Builder, the Evaluator, the Policy Engine and the independent authorization layer, with the two feedback loops](../docs/architecture/sheet-4-adaptive-harness.svg)

| Part | Decides | Authoritative for |
| :--- | :--- | :--- |
| Builder | What code and tests to write | Nothing beyond its own change |
| Evaluator | Nothing: it measures and normalizes | The evidence (`quality_metrics.v1`) |
| Policy Engine | PASS, BLOCK or QUARANTINE | Quality decisions (`policy_decision.v1`) |
| Authorization | Merge and release | Release permissions: branch protection, the person's review, the compliance authority |
| **Harness** | The next bounded step of the task | Only how execution proceeds inside its granted scope |

**The harness cannot:** override a BLOCK; turn a QUARANTINE into a PASS; change a policy threshold;
treat missing evidence as passing evidence; authorize its own merge or deployment; widen its
capabilities, scope or rate ceilings because signals look healthy; or relax a human approval.
These are left out of its action vocabulary by construction (§8), not merely forbidden.

## 3️⃣ Two Memory Systems

The playbook already has one memory model (`07_Agent_Notepad.md` §7). The hypothesis's two memory
systems map onto it; there is no new store (proofing C1).

| | Short-term memory: live operational state | Long-term memory: organizational knowledge |
| :--- | :--- | :--- |
| Is | The context window, the task's notepad work in progress, and the live telemetry read-back (`08` §2) | The retrieval index: pointers to sealed records, each with its evidence tier |
| Holds | Logs, metrics, traces, stack traces, tool failures, retries, latency, resource use, tokens and context used, progress, current SLO and error-budget state, the current Evaluator and Policy Engine results | Validated practices; finding resolutions; architecture decisions; verified remediation outcomes; incident and defect records; sealed reliability records (incident records, CAPA entries, sealed SLO reports); validated execution outcomes |
| Lifetime | The task | As long as its source, which the index points to |
| Written by | Agents, tools and telemetry, during the task | Only the indexing pipeline, from sealed objects |
| Used for | The next step of this task (Loop A, §9) | Context for future tasks (Loop B, §9) |

- **Raw metrics are not knowledge.** Metric series stay in the telemetry store. Long-term memory
  indexes *sealed reliability records* about them (proofing C2).
- **Retrieved content is data, never instructions.** It is delimited in the prompt
  (`01_Agent_Standards.md` §5), fetched with the caller's identity, and digest-verified before use
  (proofing G4).
- **Weights are not a memory path.** Neither loop changes model weights. Retrieval ordering is not
  weight modification. Fine-tuning, if ever introduced, is a separate, protected, human-approved
  process (`07` §7).

### Memory promotion

Short-term evidence becomes long-term knowledge only when it is validated, relevant and attributed
(proofing G3).

| Kind of record | Promoted when | Evidence tier |
| :--- | :--- | :--- |
| Finding resolution | The change that resolved or waived it merges (existing notepad rule) | That of its evidence |
| Remediation outcome | The fix has merged and one full measurement `period` of its process class (`autonomy_policy.v1`) has passed with no defect traced to it (`10_Autonomy_by_Evidence.md` §7) | `VERIFIED` |
| Incident or reliability record | Its incident record is closed with checkable evidence pointers | `VERIFIED` |
| Validated execution outcome | A harness decision record is sealed with its task's outcome | `OBSERVED` |
| **Engineering practice** | A person approves it in a reviewed playbook change, citing its verified outcomes | `VERIFIED`, and `approved_in` names the pull request |

- **Transient events are never promoted.** Tool failures, retries, timeouts, and build failures
  classified `infra`, `flaky` or `unknown` (`build_failure.v1`) inform this task only. They may
  raise a platform incident about the tool; they never lower confidence in a practice.
- **Knowledge ages out, it is not deleted.** A record past its `review_by` date is retrieved as
  UNKNOWN until re-verified. A record contradicted by a later verified outcome is superseded and
  links its successor.

## 4️⃣ Reliability-Aware Retrieval

**Semantic similarity finds candidates; it never establishes trust.** A document can be highly
relevant and still wrong. Retrieval runs in three steps.

1. **Candidates:** semantic search, filtered by applicability (repository, language, component,
   rule or finding fingerprint).
2. **Eligibility:** the record is active, the caller may read its source, and its digest verifies.
3. **Order:** lexicographic, with no numeric coefficients:
   1. the precedence of `07` §7: playbook rules, then a person's decision, then `VERIFIED` and
      `OBSERVED` records, then claims;
   2. within a tier, practice standing (§5): GREEN before UNKNOWN;
   3. applicability: an exact rule or fingerprint match, then the same component, the same
      repository, the same language;
   4. evidence of outcomes: more verified outcomes first;
   5. freshness: the most recently sealed first.

A practice in RED standing is still returned, labelled as a caution with its attributed defects,
never as guidance. Nothing is hidden because it failed.

### Weighting dimensions

The dimensions are: reliability history, evidence strength (tier), applicability, freshness,
historical outcomes, causal attribution, and the current operational health of the subject. The
order above uses each one, in that precedence.

**Numeric weights are not allowed until calibrated** (proofing F3). Introducing one requires:

1. a labelled calibration set of past tasks, recording which retrieved records were used and
   whether the change was accepted without a defect (`10_Autonomy_by_Evidence.md` §7);
2. a held-out evaluation showing the weighted order beats the lexicographic order on that measure;
3. the weights in a versioned policy file with its calibration report;
4. a change to them treated as a behavioral change: golden tasks run before it ships
   (`01_Agent_Standards.md` §10);
5. recalibration when the measure drifts out of control (p-chart, `10_Autonomy_by_Evidence.md` §6).

## 5️⃣ Reliability States

Red/Green logic (`05_Metadata/RedGreen_Logic.md`) applied to reliability, with a third state for
evidence that is not good enough to decide. A state always names its **subject** (proofing B2, C7):

| Subject | Is | Its state reads |
| :--- | :--- | :--- |
| `service` | The service a change targets, or one the harness depends on | That service's SLOs |
| `harness` | The harness itself, as a service with its own design record and SLOs (§11) | Its own SLOs and Governor signals |
| `practice` | A long-term knowledge record | Its outcome history |

**For a service, or the harness.** These reuse the existing SLO and burn-rate definitions
(`04_OperationalRunbooks/02_Monitoring_Alert_Thresholds.md` §2) and add no threshold:

- **GREEN:** the subject has SLOs in its design record. Every burn-rate alert pair was evaluated
  within its own short window (5 minutes for the page pair, 30 minutes for the ticket pair), none is
  firing, and no open incident names the subject.
- **RED:** a burn-rate alert for one of its SLOs is firing at page or ticket severity, its error
  budget for the window is spent, a saturation alert (knee − 1σ) is firing, or an open incident
  names it.
- **UNKNOWN:** anything else. That includes no SLOs, an evaluation older than its short window, a
  missing signal, sources that contradict each other, and an empty set of states (proofing G2, G6).

**For a practice:**

- **GREEN:** tier `VERIFIED`, at least one verified outcome, and no attributed defect that a later
  verified fix has not superseded.
- **RED:** at least one attributed defect not yet superseded.
- **UNKNOWN:** anything else, including only claimed or observed evidence, no outcomes, or a passed
  `review_by` date.

**Causal attribution** (proofing G1): a defect counts against a practice only through a recorded
chain. The knowledge record was cited by a harness decision record; that decision led to a change;
and a defect or incident record names that change. Use in the same component, similar wording, or
a co-occurring RED service state is never attribution.

### How states act

| State | On retrieval | On execution (§7) |
| :--- | :--- | :--- |
| Service RED | Adds the subject's failure evidence (incidents, CAPA entries, remediation outcomes for that failure mode) at the top, labelled. Other practices keep their standing. | No advance; preserve evidence and route |
| Service or harness UNKNOWN | Results are labelled "operating state unknown" | No advance and no increase; request the missing evidence, pause or escalate to a person |
| Harness RED | No change | Slow down: lower concurrency, longer backoff, fewer parallel tool calls; pause if it persists |
| Practice RED | Returned as a caution with its defects; lowered within its tier | May be cited only as a caution; a decision citing it cannot advance |
| Practice UNKNOWN | Returned, labelled unproven | Cannot be the only basis for an action |

**The guardrails:**

- UNKNOWN never silently becomes GREEN.
- RED raises relevant failure evidence; it does not penalize practices that merely look similar.
- Confidence falls only on attributed evidence.
- No reliability state changes a Policy Engine decision.
- Missing telemetry never justifies more autonomy or looser controls.

## 6️⃣ Deterministic Quality Evidence

The harness reads the Evaluator's `quality_metrics.v1` and the Policy Engine's `policy_decision.v1`
as they are. It uses their definitions and redefines nothing (proofing G5):

- CRAP = CC² × (1 − Cov)³ + CC per function; a module's mutation score is (killed + timed out) ÷
  (killed + timed out + survived + uncovered); a module with no mutants has no score.
- Ratchets, zones and the new-function limits (CRAP ≤ 15, coverage ≥ 80%) are the Policy Engine's,
  as published in `schemas/quality_policy.v1.json`.

The terms the decision table uses are defined from that evidence:

| Term | Means |
| :--- | :--- |
| High CRAP | A finding of QP-011, QP-025 or QP-030 on a function in the change |
| Surviving mutants | A changed module with survivors in the metrics, or a finding of QP-013, QP-021 or QP-031 |
| Strong mutation | A changed module at or above `mutation_green_min` with no survivors on changed lines |
| Missing or inconclusive | No decision, a decision whose digest does not verify, or an evidence finding (QP-001 to QP-006) |

## 7️⃣ The Decision Table

**Rules decide the action class; a model never does** (proofing C6). The table gives the set of
allowed actions. Where it allows several, policy code picks by rule. A model may only propose one of
them, and code rejects any proposal outside the set. The rows are checked in this order, and the
first that applies decides:

| # | When | Allowed actions |
| :--- | :--- | :--- |
| 1 | The ticket's budget is spent | `stop`, `escalate_to_human` |
| 2 | Policy decision QUARANTINE | `stop`, `escalate_to_human` |
| 3 | Quality evidence missing or inconclusive | `request_evaluation`, `pause`, `stop`, `escalate_to_human` |
| 4 | Policy decision BLOCK, with a target service RED or the harness RED | `stop`, `route_remediation`, `escalate_to_human`; preserve evidence |
| 5 | Policy decision BLOCK, high CRAP and surviving mutants | `route_remediation`, choosing for each fixer task a deeper analysis order or a higher rung at the task boundary |
| 6 | Policy decision BLOCK, high CRAP with strong mutation | `route_remediation` to the CRAP fixer; analyze complexity, do not assume weak tests |
| 7 | Policy decision BLOCK, any other finding | `route_remediation` by the rule's fixer (`17` §7) |
| 8 | PASS, but a target service RED | `pause`, `escalate_to_human`; preserve evidence |
| 9 | PASS, harness RED | `pace_down`, `reduce_concurrency`, `retry`, `switch_tool`, `pause` |
| 10 | PASS, any state UNKNOWN | `request_evidence`, `pause`, `escalate_to_human` |
| 11 | PASS, low CRAP but surviving mutants | `request_evaluation` for the survivors, or `advance` with the survivors recorded for the mutation fixer |
| 12 | PASS, every state GREEN | `advance` to the next stage, which ends at the independent authorization layer |

- **Within a row, the harness may also** reorder its own work, change pacing, and choose a tool or
  a ladder rung for the next task. These change where it looks and how gently it acts, never
  whether an action is permitted (`08` §3).
- **No row authorizes anything.** `advance` moves work to the next stage. The last stage before
  release is the person's approval and the compliance authority, which the harness cannot reach
  around.

## 8️⃣ What Adapts, and What Never Does

| The harness adapts, inside its bounds | Needs deterministic evaluation first | Needs human authorization |
| :--- | :--- | :--- |
| Test and analysis order | Any claim that quality improved or regressed (the Evaluator, then the Policy Engine) | Merging, deploying, releasing |
| Pacing, and backoff under stress | Advancing past a BLOCK (only a new PASS) | Lifting a QUARANTINE (the owner) |
| Concurrency: down freely; back up toward the approved ceiling only on a fresh GREEN, never above it | Any change to the evidence it acts on | Raising a ticket's budget (the owner) |
| Retries, within the attempt limit and the budget | | A new or changed policy threshold (a reviewed playbook change) |
| Model rung, at a task boundary, within the ladder and the budget (proofing C5) | | Promoting a practice (§3) |
| Tool choice among the tools it is granted | | Any change to scope, capabilities, rate ceilings or the autonomy level (proofing C9) |
| Remediation order | | |

**The action vocabulary** in `harness_decision.v1` is closed: `advance`, `reorder_work`,
`pace_down`, `reduce_concurrency`, `restore_concurrency`, `retry`, `switch_tool`,
`change_model_rung`, `request_evaluation`, `request_evidence`, `route_remediation`, `pause`,
`stop`, `escalate_to_human`. There is no action that approves, merges, deploys, grants, raises a
ceiling or edits policy, so no reading of the evidence can produce one.

## 9️⃣ Two Connected Loops

**Loop A, runtime adaptation (within one task):** current telemetry and quality evidence → the
decision table → one bounded action → new execution → new telemetry and evidence. It uses
short-term memory only. Its purpose is to execute better inside fixed limits.

**Loop B, organizational learning (across tasks):** sealed decision records and outcomes →
validation and causal attribution → reliability standing → promotion into the index → retrieval for
future tasks. It uses only validated history.

The loops connect through **sealed decision records**: every Loop A decision is recorded
(`harness_decision.v1`) and sealed with the task, and Loop B reads only those records and their
verified outcomes. Neither loop changes model weights. Loop A never writes long-term memory
directly, and Loop B never acts on a running task.

## 🔟 Failing Conservatively

- **Missing, stale or contradictory signals** make a state UNKNOWN. UNKNOWN allows no advance and
  no increase.
- **A stale healthy signal authorizes nothing.** Freshness is checked against the alert's own short
  window before GREEN is used.
- **An empty input is not a healthy input.** A decision with no reliability states cannot advance.
- **Missing quality evidence is never a pass.** Row 3 of §7 applies before any row that could
  advance.
- **A failed tool lowers confidence in the tool run, not in a practice** (§3, transient events).
- **When the table cannot decide,** the harness pauses and escalates to a person.

## 1️⃣1️⃣ The Harness Is Held to Its Own Standards

- **It has a design record** (`16_Service_Design_Record.md`) with SLOs for its own decision latency
  and availability, so its own state is defined like any service's (§5).
- **Every decision is evidence.** Each is a `harness.decide` span. The span carries the action, its
  rule, the reliability states and their subjects, the policy decision's digest, and the knowledge
  records cited, plus the steering attributes `agent.steer.reason`, `agent.steer.from` and
  `agent.steer.to` from `08` §4. It also produces a structured log line with `trace_id`, and the
  metrics in `metrics/promql/MASTER_INDEX.md` §10.
- **It draws from the ticket's one budget,** and its token records follow `token_record.v1`.
- **Its own quality is measured** like any code: the Policy Engine gates the harness's code.
- **Its decision table is versioned,** and changing it is a behavioral change behind golden tasks,
  including designed-to-fail ones (§12).
- **Its autonomy is per process class** and protected classes stay at L2 or below; an incident
  traced to a harness decision demotes the class (`10` §6).

## 1️⃣2️⃣ Status and Next Stages

| Stage | State |
| :--- | :--- |
| 1. Hypothesis | Done: the white paper |
| 2. Codification | This standard; the contracts `harness_decision.v1` and `knowledge_record.v1` (schemas and examples) |
| 3. Review and proofing | The proofing report (Software Factory project, `claude/harness-whitepaper-proof.md`); owner review of this standard |
| 4. Test design | Not started: conformance cases for every decision-table row and contract constraint; designed-to-fail cases (a forged stale GREEN, a QUARANTINE input, an empty reliability set, a spent budget, an attributed defect without its chain); the retrieval calibration protocol |
| 5. Implementation | Not started; after the standard and the test design are approved |
| 6. Validation | Not started |

Today every service's state would be UNKNOWN: no factory service has SLOs yet (SD-07). A harness
built now would therefore escalate to a person before every advance. That is the intended
conservative behavior, not a defect.

---

## Principle

Let the harness see everything (history, health and measured quality), let it choose only how to
proceed, and keep whether anything ships with the gates and the people who own them.
