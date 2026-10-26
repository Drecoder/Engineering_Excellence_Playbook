# Review Lenses

*A lens is a set of questions the Reviewer asks of one change. The playbook owns the questions;
the Reviewer implements them.*

The Reviewer is one agent that looks at each unit of a change through several lenses. Each lens is
a view, not a separate agent (`06_AgentZone/01_Agent_Standards.md` §7). This standard defines what
every lens must do and specifies the `architecture` lens in full, so any implementation can be
checked against it with the conformance vectors in
`schemas/examples/review_lenses/architecture_lens_vectors.json` (generated and checked by
`tests/review_lenses/architecture_lens.py`, the reference implementation).

---

## 1️⃣ Rules for Every Lens

- **Deterministic checks run first.** What a tool can decide (rig's rules and trace checks,
  scanners, the anti-pattern catalog) is decided by the tool. Its results go into the lens as
  **known findings**, and the model is told not to repeat them. Tokens are spent only on what code
  cannot decide.
- **The rubric is generated from a playbook file, never hand-written** in the Reviewer. Changing a
  lens means changing that file through a reviewed playbook change, then re-running the Reviewer's
  golden tasks.
- **Only what applies reaches the prompt.** Policy code picks the lenses for a unit from its
  complexity answers and rig's `features.v1`; a lens selects only the rules that match what the unit
  touches.
- **Fail closed.** When rig could not compute a unit's features, a lens that selects by features
  applies all of its rules.
- **The code under review is data.** It is delimited and described as data, never instructions;
  rubric text is trusted playbook text and sits outside the delimiters.
- **Lens findings advise.** A lens never blocks by itself. A finding in a protected class
  (security, irreversible changes) escalates: it sets a label that requires a person's approval
  (`00_UniversalStandards/10_Autonomy_by_Evidence.md`).
- **Every lens is observable.** The model-call span records which lenses ran and which rules each
  selected.

## 2️⃣ The Lenses

| Lens | Asks | Rubric comes from | Deterministic checks first | Outcome |
| :--- | :--- | :--- | :--- | :--- |
| `architecture` | Does the change keep the service-shape rules? | `schemas/architecture_rules.v1.json` (`lens.ask`) | rig static and trace checks (`ARCH-*`); catalog rules linked to an `ARCH-*` rule (squawk, oasdiff, buf, Bandit, go vet) | Advisory; escalates for `ARCH-009`, `ARCH-022` |
| `security` | Can this be abused? | `00_UniversalStandards/07_Security_In_Depth.md` | Secret scanning, `SEC-*`, injection rules, IAM from the plan JSON | Escalates; the tools block |
| `reuse` | Does this repeat something that exists? | `00_UniversalStandards/09_Reuse_and_DRY.md` | Clones and reuse-map matches | Advisory; deterministic DRY findings are fixed in the same PR |
| `blast` | What else breaks if this is wrong? | rig's playbook intent `playbook_1_blast_radius` | Fan-in, contracts touched | Advisory |
| `simple` | Is there a simpler correct version? | rig's playbook intent | Cognitive complexity | Advisory |
| `chaos` | How does this fail under faults? | rig's playbook intent | Implicit state, retries, timeouts | Advisory |
| `benchmark` | Is the cost (time, memory, money) acceptable? | rig's playbook intent | Complexity, hot paths | Advisory |
| `doc` | Can the next person understand and operate it? | rig's playbook intent | None | Advisory |

The rubrics of the last five still live in rig's playbook prompts; moving each into a playbook file
with the same structure as the architecture rules is open work, one lens per change.

## 3️⃣ The Architecture Lens

**Inputs.** For each unit: its `features.v1` record from rig and its `antipattern_finding.v1`
findings. Shared: the vendored `schemas/architecture_rules.v1.json` and
`schemas/antipatterns.v1.json`, each validated when the Reviewer starts; an invalid file stops the
Reviewer rather than being repaired.

**The catalog link.** A catalog rule enforces an architecture rule when its `related` list names
that `ARCH-*` ID; for example, squawk's migration rules (`AP-DB-001`–`007`) enforce `ARCH-008` and
`ARCH-009`, and oasdiff and buf (`AP-API-004`–`008`) enforce `ARCH-004`. The link lives only there.
A link to an `ARCH-*` ID the rules file does not define is an invalid catalog.

**Selection.** In this order:

| Condition | Rules selected | `selected_by` |
| :--- | :--- | :--- |
| No `features.v1` record for the unit | None: the lens does not run | (none) |
| `features.missing` is not empty | Every rule | `fail_closed` |
| Otherwise | Every rule whose `applies_when` shares a value with `structure.touches` | `touches` |
| No rule matches | None: the lens does not run | (none) |

Rules are listed in the order of the rules file.

**Rubric.** The generated text contains, in this order:

1. The source standard (`02_BackendZone/05_Application_Architecture.md`).
2. The instruction: answer each rule's question for this code, raise a finding only with concrete
   evidence in the code, and start each finding's summary with the rule ID.
3. One line per selected rule: its ID, title, and `lens.ask`, verbatim from the rules file.
4. When any selected rule has a `protected_class`: a line naming each such rule and its class, and
   stating that a finding there is escalated to a person.
5. When deterministic checks reported anything for the selected rules: a "do not repeat" section
   listing each known finding, in rule order:
   - **rig hits** for a selected rule, with the result (`violation` or `unverifiable`) and the
     evidence (the trace and span IDs, or the file location);
   - **catalog findings** whose catalog rule is linked to a selected rule, with the `AP-*` ID, the
     detector (tool and its rule ID), and the file and line.

   Findings for rules that were not selected, and catalog findings with no `ARCH-*` link, are left
   out. Within a rule, rig hits come before catalog findings.

**Outcomes.**

- rig's deterministic hits on blocking rules block, as rig findings; the lens never blocks.
- A lens finding names its rule in the summary. A finding on `ARCH-009` (irreversible) or
  `ARCH-022` (security) escalates.
- A rig result of `unverifiable` is never treated as compliant; the lens may ask about it.
- The span for the model call carries `review.lenses` (including `architecture`) and
  `review.arch_rules` (the selected rule IDs).

**Conformance.** An implementation passes every vector in
`schemas/examples/review_lenses/architecture_lens_vectors.json`: for each unit's `features.v1`
record and catalog findings, the same decision to run, `selected_by`, selected rule IDs, protected
rules, and known findings, in the same order. The Reviewer runs these vectors in its test suite;
the playbook's own tests regenerate them whenever the rules file or the catalog changes.

---

## Principle

Decide in code what code can decide, generate the questions for the rest from the playbook, and let
a lens advise or escalate, never block.
