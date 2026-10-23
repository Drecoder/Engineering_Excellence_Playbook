# Autonomy by Evidence

*A human leaves a process step only when the data shows the step is stable, capable, and better
without them, and never when the step carries security, ethical, or irreversible consequences.*

This standard applies Six Sigma and Lean thinking to the platform's change process: how changes
are built, reviewed, merged, and applied. It decides, process class by process class, how much of
that work runs without a person, and how that autonomy is earned, measured, and taken back. The
enforceable subset is in `AGENTS.md` → **Autonomy Rules**; the machine-readable policy is
`schemas/autonomy_policy.v1.json`.

---

## 1️⃣ The Objective, and an Honest Constraint

**The long-term objective is Six Sigma quality** for every process class: no more than **3.4
defects per million opportunities** (99.99966% defect-free). The working hypothesis behind this
standard is that the largest remaining source of variation in a stable, well-instrumented change
process is the human step, and that removing it, where it is safe and ethical to do so, moves the
process toward Six Sigma.

**Current demand cannot demonstrate Six Sigma, and this standard does not pretend it can.** Proving
a defect rate of 3.4 per million with 95% confidence needs on the order of 900,000 consecutive
defect-free events; proving five nines (99.999%) needs about 300,000. A platform that merges dozens
of changes a week would need decades to reach either by counting defects.

So the standard holds two things at once:

- **The target is Six Sigma.** Every measurement, chart, and promotion rule is the one a Six Sigma
  program would use, so the evidence accumulates toward it.
- **The current gates are interim and explicit.** Each autonomy level states the defect rate it
  can actually demonstrate at today's volume, with its confidence. Targets tighten as volume grows,
  through a reviewed change to the policy, never by assumption.

A process that has not reached its interim target is not declared Six Sigma, and a process that
has reached it is not declared Six Sigma either. The policy records what has been shown.

---

## 2️⃣ DMAIC Applied to the Change Process

| Phase | On this platform |
| :--- | :--- |
| **Define** | A **process class**: a kind of change with one definition of done and one definition of a defect (e.g. "documentation-only change", "dev IaC change outside protected resources") |
| **Measure** | Telemetry the platform already emits: gate results, review rounds, fix success by rung, lead time, post-merge apply results, reverts, incidents (`02_BackendZone/04_Telemetry_Standards.md`) |
| **Analyze** | Which step contributes the most defects, variation, or waiting. The human step is a candidate, not a presumption: it is measured like every other step (§4) |
| **Improve** | Move that step one level up the autonomy ladder (§3), and only that step |
| **Control** | Control charts on the class's metrics; an out-of-control signal demotes the class automatically (§6) |

**Never automate a broken process.** A class whose metrics are not in statistical control is fixed
first, by people, at its current level. Autonomy amplifies whatever process it is applied to,
including a bad one.

---

## 3️⃣ The Autonomy Ladder (Jidoka)

Jidoka, from the Toyota Production System, removes people in stages: the machine first learns to
detect a problem and stop itself, and only then works unattended.

| Level | Jidoka stage | What runs without a person | The human's role |
| :--- | :--- | :--- | :--- |
| **L0** | Manual | Nothing | Writes, reviews, merges, applies |
| **L1** | Human and machine | Agents propose changes | Reviews and merges every change |
| **L2** | Machine detects and stops | Deterministic gates block; agents fix what they block | Approves every merge |
| **L3** | Human on exception | Merge, when every gate is green and the class is in control | Answers the andon: anomalies, demotions, out-of-control signals |
| **L4** | Unattended | Merge, apply, and automatic rollback | Reviews the control charts and the incident records |

- Autonomy is granted **per process class**, never globally, and moves **one level at a time**.
- At L3 and above, the machine must be able to **stop the line by itself**: block, revert, or roll
  back without a person. That capability is tested by drills, the way guardrails are tested by
  conformance tests (`08_Governance_Guardrails.md` §5a), before the level is granted.
- Branch protection still enforces every gate at every level. Removing the human approval from a
  class removes a person, not a control.

---

## 4️⃣ Measure the Human Before Removing the Human

That the human is the greatest source of variation is a hypothesis to test, not an assumption to
act on. Before a class is promoted past a human step, the evidence must show at least one of:

| Trigger | Measured by | Six Sigma analogue |
| :--- | :--- | :--- |
| **The human is an unreliable gauge** | Reviewer agreement: the same changes reviewed by different people, or by the same person twice, scored against seeded ground truth (the Reviewer benchmark harness) | Gage R&R: repeatability and reproducibility |
| **The human adds no detection** | On the class's defect types, deterministic gates and the AI reviewer already catch what human review catches | Measurement system adds no information |
| **The human is the bottleneck** | Human wait time as a share of lead time, against the class's required delivery rate | Takt time versus cycle time |
| **The human introduces defects** | Defects traced to manual steps (approvals given on red gates, manual edits, skipped steps) in incident records | Root cause in the Analyze phase |

A class where human review demonstrably catches what the machines miss **keeps the human**, even if
the human is slow. Speed never buys removal of a working control.

---

## 5️⃣ Protected Classes: Where the Human Stays

In manufacturing, a severe hazard *removes* the human, because the human is the one who gets hurt.
In software, the harm lands on systems, data, and the people they serve, and the human is the
**accountability and ethics check**. The severity rule therefore runs the other way: high severity
keeps a person in the loop.

These classes never go above **L2**, whatever their metrics show:

| Protected class | Examples |
| :--- | :--- |
| **Security** | IAM and identity, governance guardrails and their exceptions, secrets, network exposure, CI permissions |
| **Ethics** | Changes affecting how user data is collected, used, retained, or shared; decisions that affect people rather than systems |
| **Irreversible** | Deletes, state moves and replacements, data destruction or migration, anything a rollback cannot undo |
| **Staging and production** | Merges to staging and production (for now; see below) |

- Membership is decided **deterministically** (from the plan JSON, the changed paths, the touched
  resources, the target environment), never from model output, and fails closed: a change that might
  be protected is treated as protected.
- Staging and production are protected today because the platform requires human approval for those
  merges (`07_Security_In_Depth.md` §3). Raising either above L2 is a reviewed change to this
  standard, made only with evidence, never as a side effect of promoting another class.

---

## 6️⃣ Promotion, Control, and Demotion

### Promotion

A class moves up one level when **all** of these hold:

1. **In control:** its control charts show no out-of-control signal for the required number of
   consecutive periods.
2. **Capable:** its demonstrated defect rate is at or below the level's interim target, at 95%
   confidence. With *n* consecutive defect-free events, the 95% upper bound on the defect rate is
   about *3/n* (the rule of three); with defects observed, the exact Clopper-Pearson bound is used.
   Continuous metrics (lead time, review rounds) use **Cpk ≥ 1.33** against their specification
   limits.
3. **Self-stopping** (L3 and above): drills show the machine detects a seeded failure and stops,
   reverts, or rolls back without a person.
4. **Not protected** (§5).
5. **Reviewed:** the promotion is a reviewed change to `schemas/autonomy_policy.v1.json`.

| Target | Interim (demonstrable today) | Events needed with zero defects, 95% confidence | Long-term target |
| :--- | :--- | :--- | :--- |
| L3 | ≤ 1% defects | ≈ 300 | 3.4 per million |
| L4 | ≤ 0.1% defects | ≈ 3,000 | 3.4 per million |

### Control

- **p-charts** on each class's defect proportion per period; **individuals and moving-range
  charts** on lead time and review rounds.
- Out-of-control signals follow the standard Western Electric rules (a point beyond three sigma,
  runs on one side of the center line, sustained trends).

### Demotion

- **Automatic and immediate:** any out-of-control signal, any incident traced to the class, or any
  failed self-stop drill drops the class one level. That is "stop the line", applied to autonomy
  itself.
- Re-promotion starts the evidence over: the class must meet §6 promotion again from the point of
  demotion.
- Every demotion gets an incident record (`03_Post_Mortem_Template.md`).

---

## 7️⃣ What Counts as a Defect

Each class defines its defects in the policy; the defaults are:

- a change reverted, or rolled back, after merge
- a post-merge apply that failed or left partial state
- an incident traced to the change
- a defect found later in code the change introduced (an escaped defect)
- a gate bypassed or overridden for the change

A change that is blocked by a gate and fixed before merge is **not** a defect: the line stopped
itself, which is the process working.

---

## 8️⃣ Measured

| Metric | Meaning |
| :--- | :--- |
| `autonomy_level{process_class}` | Current level per class |
| `process_events_total{process_class,outcome}` | Changes per class, by outcome (`ok`, `defect`) |
| `process_defect_rate_upper_bound{process_class}` | Demonstrated 95% upper bound on the defect rate |
| `process_dpmo_estimate{process_class}` | Defects per million opportunities, the Six Sigma figure, tracked toward 3.4 |
| `process_out_of_control_total{process_class,rule}` | Control-chart signals |
| `autonomy_demotions_total{process_class,reason}` | Demotions |
| `change_lead_time_seconds{process_class}` | Time from change proposed to merged (histogram) |
| `human_wait_seconds{process_class}` | Time changes wait on a person (histogram) |
| `reviewer_agreement_ratio{process_class}` | Agreement between reviewers on the same changes (the Gage R&R analogue) |

---

## Principle

Remove the human where the human is the variation, keep the human where the human is the
conscience, and let the data decide which is which. Six Sigma is the destination; every level on
the way is earned with evidence and taken back the moment the evidence stops.
