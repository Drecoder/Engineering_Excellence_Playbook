# The CAPA Graph and Risk-Weighted Learning

*The proof journal records what went wrong and why. This standard turns that record into a graph the
factory can reason over, a risk weight for every rule and pattern it has broken, and, only after a
protected decision, training signal that teaches an agent to avoid its own past mistakes.*

**Status: PROPOSED** (the playbook's *Design*: agreed target, not implemented). This standard
codifies the design so implementations have something to conform to. Nothing here is built. The
contracts it names are specified at the test-design stage (§11), not before. It extends
`docs/POC_JOURNAL.md` (its *feedback mechanism* role), `09_Adaptive_Harness.md` §3–4 (long-term
memory and the calibration protocol for numeric weights) and `07_Agent_Notepad.md` §7. Where they and
this page disagree, they win and this page is the bug.

**Fine-tuning stays closed.** `07_Agent_Notepad.md` §7 keeps fine-tuning from the record closed
unless decided as a protected change. §6–§8 of this standard describe how it would work *if* that
decision is made (§10, D1). Until then, only §2–§5 (the graph and the risk weights, advisory) may be
built.

---

## 1️⃣ Why a Graph

The journal is chronological and the register is a flat table. Neither answers the questions the
factory now needs answered:

- Which rules are broken *repeatedly*, and do their preventive actions actually stop recurrence?
- Which defects sit on components that many others depend on, so one mistake costs more?
- Which agent, model and prompt version authored each defect, so learning stays with its owner?
- Which preventive actions are proven controls, and which are only alerts or habits?

These are path questions (finding → defect → root cause → prevention → verification → control), so
the record is modeled as a property graph. **The graph is a projection, never a source of truth.**
It is rebuilt deterministically from the journal, the register and repository state; it is never
edited; and a correction is a new journal entry, exactly as today.

## 2️⃣ The Data Model

### Nodes

Every node carries `id`, `schema_version`, `source` (the journal heading or register row it came
from, with the commit SHA it was read at) and `content_sha256`.

| Node | Key properties | Comes from |
| :--- | :--- | :--- |
| `Finding` | `register_id` (`F-0001`), `found`, `due`, `closed`, `status` (open, fixed, proven), `severity`, `category`, `detected_by` (control, person) | One journal entry plus its register row |
| `Rule` | `rule_id` (`ARCH-*`, `SEC-*`, `GOV-*`, or an `AGENTS.md` section anchor), `zone`, `blocking` (true, false) | The entry's **Rule** field, resolved (§4 step 2) |
| `Defect` | `fingerprint` (stable hash of the pattern, the path class and the rule), `antipattern_id` (from `schemas/antipatterns.v1.json`, when one matches) | The entry's **Problem** field |
| `RootCause` | `class` (missing control, wrong control, gap in a rule, unverified assumption, process), `summary` | **Root cause** |
| `Correction` | `commits`, `pull_requests`, `changed_paths` | **Correction** and **Evidence** |
| `PreventiveAction` | `kind` (check, signal, rule, contract), `implements_control` | **Preventive action** |
| `Verification` | `kind` (designed-to-fail case, test run, drill, review), `evidence_tier` (`VERIFIED`, `OBSERVED`, `CLAIMED`), `run_ids` | **Verification** and **Evidence** |
| `Component` | `repository`, `boundary` (package, module or Terragrunt unit), `data_class` | Evidence paths and the service design record |
| `Control` | `gate`, `proven` (has a designed-to-fail case) | The register's `controls` block |
| `Agent` | `agent` (Builder, Reviewer, …), `model`, `prompt_version`, `adapter_digest` (null until §8) | Run records and commit trailers |

### Relationships

The six core relationships, plus the ones that capture architectural dependency, attribution and the
append-only history:

| Relationship | From → To | Meaning |
| :--- | :--- | :--- |
| `VIOLATES` | Finding → Rule | The finding is a breach of this rule |
| `EXHIBITS` | Finding → Defect | The finding is an instance of this defect pattern |
| `CAUSED_BY` | Defect → RootCause | Why it happened |
| `REMEDIATED_BY` | Finding → Correction | The fix to this instance |
| `PREVENTED_BY` | RootCause → PreventiveAction | What stops recurrence |
| `VALIDATED_BY` | Correction or PreventiveAction → Verification | Proof the fix or prevention works |
| `AFFECTS` | Finding → Component | Where the defect lived |
| `DEPENDS_ON` | Component → Component, `kind` (runtime, build, contract, data) | The architectural dependency graph |
| `ENFORCED_BY` | Rule → Control | Which gate enforces the rule, if any |
| `IMPLEMENTS` | PreventiveAction → Control | The prevention became a control |
| `DETECTED_BY` | Finding → Control | A control caught it (absent when a person did) |
| `RECURS` | Finding → Finding | Same rule and fingerprint, found after the earlier one closed |
| `CORRECTS` | Finding → Finding | A later entry corrects an earlier one (entries are never rewritten) |
| `AUTHORED_BY` | Defect → Agent | Who wrote the defective change, with model and prompt version |

**Invariants**, checked on every rebuild; a snapshot that breaks one is rejected, not repaired:

1. Every `Finding` has exactly one register row, at least one `VIOLATES` and one `EXHIBITS`.
2. A `Finding` with status `proven` has a `Verification` of tier `VERIFIED` on its correction *and*
   on its preventive action. "Fixed" without that is `fixed`, never `proven`.
3. A `Rule` with no `ENFORCED_BY` is reported as **unenforced**: a written rule with no control.
4. `RECURS` and `CORRECTS` point backwards in time only.
5. Unresolved references become an `Unresolved` node, flagged in the report, never guessed (§4).

## 3️⃣ The Risk Weight W(N)

A risk weight in [0, 1] for every `Rule`, `Defect` pattern and `Component` node, recomputed on every
rebuild. It answers: *how much should the factory care about this node right now?*

For a node `N` at time `t`, over the findings `f` connected to it:

```text
Temporal decay
  d(f,t) = 1                                   if f is open
         = 2^(−(t − closed_f) / h) · (1 − ρ·P_f)  otherwise
    h    = half-life in days
    P_f  = 1 if f's preventive action IMPLEMENTS a proven Control, else 0
    ρ    = credit for a proven control (residual risk falls, never to zero)

Severity (noisy-OR: many mediums approach a high, never exceed 1)
  S(N,t) = 1 − Π_f ( 1 − s(f) · d(f,t) )
    s(f) from the register's written rubric: critical, high, medium, low

Recurrence (log-damped, so one noisy component cannot dominate)
  R(N,t) = min(1, log(1 + Σ_{f has RECURS} d(f,t)) / log(1 + R_max))

Centrality (risk is costlier where much depends on it)
  C(N)   = percentile rank of PageRank on the DEPENDS_ON projection,
           edges pointing from dependent to dependency;
           for a Rule or Defect node, the max over the Components its findings AFFECT

Weight (multiplicative: no evidence of a defect, no risk, however central)
  W(N,t) = S(N,t) · (1 + β·R(N,t)) · (1 + γ·C(N)) / ((1 + β)(1 + γ))
```

**Why this shape.** Severity is the base, so a central component that has never been defective
carries no weight; centrality and recurrence only amplify evidence. Open findings never decay. A
closed finding decays, and faster when its prevention became a proven control, which rewards
preventive action over correction alone. Percentile rank keeps centrality stable as the graph grows.

**The parameters are not set.** `h`, `ρ`, `β`, `γ`, `R_max` and the severity map follow the
calibration protocol for numeric weights (`09_Adaptive_Harness.md` §4): a labelled set, a held-out
evaluation, a versioned policy file with its calibration report, golden tasks before a change ships,
and recalibration when the measure drifts. The measure is **recurrence prediction**: on a held-out
later window, W ranks the nodes that went on to recur above those that did not, and beats severity
alone. Until then, W is computed and reported, and **steers nothing**: not retrieval, not routing,
not training. Proposed starting points for the first calibration run only: `h` 90 days, `ρ` 0.5,
`β` 1, `γ` 0.5, `R_max` 5, severity 1.0 / 0.6 / 0.3 / 0.1.

## 4️⃣ The Pipeline: Ingestion to Graph

Each step is a tool (`01_Agent_Standards.md` §1a): typed input, typed output, no loop, never applies.

1. **Extract.** Parse `docs/POC_JOURNAL.md` by its fixed `## YYYY-MM-DD: title` headings and bold
   CAPA fields, and `docs/FINDINGS_REGISTER.json` by its contract. Join each entry to its row by the
   row's `journal` heading. Emit one CAPA record per entry, validated against its schema. A missing
   field or an entry with no row is rejected, not repaired.
2. **Resolve.** Map the free-text **Rule** field to rule IDs, evidence paths to `Component` nodes,
   problems to defect fingerprints and catalog anti-patterns. Deterministic matching first (IDs,
   paths, the catalog). A model may *propose* a link; it is recorded `CLAIMED` and becomes an edge
   only when a person confirms it. Anything else becomes an `Unresolved` node.
3. **Project.** Build nodes and edges in one deterministic pass, keyed by content hash, so the same
   inputs always give the same snapshot. Check the §2 invariants.
4. **Score.** Compute W(N) (§3) under the versioned parameters, or the provisional ones, labelled.
5. **Seal and report.** Write the snapshot (nodes and edges as JSON Lines, digest-named) with its
   source commit SHA and parameter version, then emit a span, a structured log line and the metrics
   `capa_graph_nodes`, `capa_graph_unresolved_refs`, `capa_rules_unenforced` and `capa_risk_weight`
   (the last per node, advisory). Evidence is telemetry (`AGENTS.md` → Observability Rules).

**Storage follows the scale.** At tens of entries the graph is built in memory by a job that runs
only when called, and its snapshot lives in the object store. A graph database is added only for a
measured reason (query latency, size, concurrent readers), recorded in the change that adds it.

**Gap this exposes:** the register's **Rule** column is prose today, so step 2 has to guess. The
register's next contract version carries `rule_ids`, `components`, `fingerprints` and `recurs`, and
the 29 existing rows are backfilled through a reviewed change (§11, LL-2).

## 5️⃣ What the Graph Is For Before Any Training

These need no protected decision and are the first value it delivers, all advisory:

- **Unenforced rules:** every `Rule` without `ENFORCED_BY` is a written rule no control checks.
- **Prevention that did not prevent:** a `RECURS` edge after a `proven` finding means the control
  does not cover the pattern. That is a new finding.
- **Control coverage, measured:** the register's control-catch share, recomputed from `DETECTED_BY`
  edges with evidence, instead of the hand-set attribution it reports today.
- **Retrieval candidates:** `knowledge_record.v1` pointers for the harness (`09` §3), each finding a
  sealed source. Ordering stays lexicographic until W is calibrated (`09` §4).

## 6️⃣ Training Data: Preference Pairs

*Applies only once D1 (§10) opens fine-tuning.*

**Pairs come from corrections, not from prose.** The journal supplies the rule taxonomy and the
weights; the training examples come from the factory's own run records, where a change was refused
and then corrected:

| Field | Source |
| :--- | :--- |
| `x`: prompt | The approved spec, the task's sealed notepad page, and the retrieved context the agent actually had |
| `y⁻`: rejected | The agent's diff that a deterministic gate refused (Policy Engine BLOCK or QUARANTINE, a rig anti-pattern hit, a `SEC-*` policy) or that a Reviewer blocking finding sent back |
| `y⁺`: chosen | The corrected diff that passed every gate and merged with human approval |
| `W` | The max W(N) over the `Rule` and `Defect` nodes the refusal names |
| Provenance | Run IDs, gate decision digest, commit SHAs, `Agent` node of `y⁻` |

**A pair is admitted only when all hold:**

- The correction's `Verification` is `VERIFIED`. Agent claims (`CLAIMED`) are never training data.
- **The agent learns only from its own mistakes:** `y⁻` is `AUTHORED_BY` the agent being trained.
  Each agent's journal and pairs are its own; the Builder never trains on the Reviewer's record.
- The failure was classified `code` or `config` (`build_failure.v1`). Transient failures (`infra`,
  `flaky`, `unknown`) never become training data, as they never become knowledge (`09` §3).
- `y⁺` was not later corrected (`CORRECTS`) or implicated in a `RECURS`.
- No secret, credential or redacted span appears in `x`, `y⁻` or `y⁺`.

**Volume is the gating fact.** The journal holds 29 entries today; that is a taxonomy, not a training
set. Fine-tuning is not attempted below an initial floor of **500 admitted pairs spanning at least 10
rules**, revisited at test design.

## 7️⃣ The Training Objective

The model being tuned is an open-weight Builder candidate (LoRA adapters), with the current
production rung frozen as the reference policy `π_ref`.

### Token masks and weights

For each token `t` of a completion:

```text
m_t = 1  for tokens of the diff the agent wrote
      0  for the prompt, the spec and retrieved context (the model learns to act, not to recite)
      0  for any path the agent may not change: .github/, the gate pin, .ci/quality.v1.json,
         .ci/exceptions.v1.json (agents cannot change their evaluator, so they are never
         trained to write it)
h_t = 1  for tokens in hunks that differ between y⁺ and y⁻, else 0
w_t = W of the rule or pattern the hunk containing t was refused for (0 outside refused hunks)
λ_t = (1 + η·w_t), normalized so its batch mean is 1 (keeps the effective learning rate stable)
```

### Risk-weighted SFT on the chosen diff

```text
L_SFT = − Σ_t m_t · λ_t · log π_θ(y⁺_t | x, y⁺_<t)  /  Σ_t m_t · λ_t
```

### Risk-margin, hunk-masked DPO

```text
Δ_θ(y)  = Σ_t m_t · h_t · [ log π_θ(y_t | x, y_<t) − log π_ref(y_t | x, y_<t) ]

L_DPO   = − E_(x, y⁺, y⁻) [ log σ( β · (Δ_θ(y⁺) − Δ_θ(y⁻)) − δ · W ) ]
```

- **Hunk masking (`h_t`)** puts the preference on the lines that differ. Shared context cancels in
  principle; masking it removes length bias and noise in practice.
- **The margin `δ · W`** is the risk weighting: a pair refused for a high-risk rule must separate
  further before its loss vanishes. It is preferred to scaling the loss by W, which amplifies label
  noise on exactly the rare, severe pairs.
- **Unlikelihood on the rejected tokens is not used.** Pushing token probabilities toward zero
  degrades fluency and teaches the model to dodge a detector's surface form, not the defect.

### The combined loss

```text
L = L_DPO + λ_sft · L_SFT
```

The SFT term guards against a known DPO failure: the likelihood of the chosen output falling along
with the rejected one. `β`, `δ`, `η` and `λ_sft` are tuned on held-out pairs and recorded with the
adapter; none is fixed by this standard.

## 8️⃣ Evaluation, Promotion and Rollback

**Split by time, not at random:** train on older pairs, evaluate on newer ones, so the evaluation
measures generalization to mistakes not yet seen. Golden tasks and the evaluation set are excluded
from training by content hash, and the check is part of the dataset's report.

**A tuned adapter is promoted only when, against the current rung, on held-out specs run through
the real central gate:**

1. every golden task passes, including the designed-to-fail tasks (`01_Agent_Standards.md` §10);
2. the first-attempt pass rate rises, and the Policy Engine's BLOCK and QUARANTINE rates fall;
3. anti-pattern hits and refusals for the trained rules fall, **and** the mutation score of the
   agent's own tests does not, and review rounds (p90) do not rise;
4. defects that escape the gate do not rise (an adapter that learned to evade a detector shows up
   here, not in the detector);
5. a general coding suite shows no regression.

**Goodhart is designed for.** The detectors that label pairs are not the only judge: mutation, the
Reviewer, escaped defects and human review all score the adapter. At least one golden task is an
*evasive* variant, the same defect in a shape the detector misses, which the adapter must not
produce.

**Promotion is a model change** on the ladder (`schemas/model_ladder.v1.json`): a reviewed,
human-approved change, golden tasks first. Every defect the adapter later authors carries its
`adapter_digest` on `AUTHORED_BY`, so the graph measures the adapter like any other control.
Rollback restores the previous adapter digest. A rise in findings attributed to an adapter, or an
incident traced to it, demotes it automatically, as with any process class
(`00_UniversalStandards/10_Autonomy_by_Evidence.md`).

## 9️⃣ The Loop

```text
work ──► gate refuses ──► journal entry + register row ──► graph rebuild ──► W(N)
  ▲                                                                            │
  │                                    (advisory) unenforced rules, recurrence │
  │                                    after "proven", control coverage ◄──────┤
  │                                                                            ▼
  └── promoted adapter ◄── evaluation ◄── training ◄── admitted pairs  (only after D1)
```

The first loop changes **rules and controls**, through people, in reviewed playbook changes. The
second changes **one agent's weights**, through the same gates and the same human approval. Neither
loop can change the gates, the register's deadlines or this standard.

## 🔟 Conflicts and Open Decisions

Recorded here, not resolved by editing other standards.

| # | Question | Until decided |
| :--- | :--- | :--- |
| D1 | **Opening fine-tuning from the record.** `07` §7 keeps it closed unless decided as a protected change. This standard proposes the conditions under which it opens: Policy Engine enforcing in CI, the notepad sealing run records, W calibrated, and the pair floor met. | Closed. §6–§8 are design only |
| D2 | **Numeric parameters of W.** | Computed and reported, steering nothing, until calibrated (`09` §4) |
| D3 | **The register's machine-readable references** (`rule_ids`, `components`, `fingerprints`, `recurs`). | Resolution is deterministic where IDs exist; the rest is `Unresolved` |
| D4 | **Graph store.** | In-memory build and object-store snapshots; a graph database only for a measured reason |
| D5 | **Training compute.** Spot GPU, scale to zero, under one budget per training run. | Not provisioned |

## 1️⃣1️⃣ Status

| Capability | Status | What exists |
| :--- | :--- | :--- |
| CAPA graph data model | PROPOSED | This standard |
| Risk weight W(N) | PROPOSED | This standard; parameters uncalibrated |
| Ingestion pipeline | PROPOSED | The journal and register it reads, and their CI checks |
| Preference pairs and risk-weighted fine-tuning | PROPOSED, closed by D1 | This standard |

| Stage | State |
| :--- | :--- |
| 1. Hypothesis | Done (2026-11-09) |
| 2. Codification | This standard |
| 3. Review | Owner review of this standard |
| 4. Test design | Not started: contracts `capa_record.v1`, `capa_graph_snapshot.v1`, `risk_weight_policy.v1`, `preference_pair.v1`, the register's next version, conformance vectors for every §2 invariant and for W, and the calibration protocol |
| 5. Implementation | Not started; the graph and W first (roadmap LL-2 to LL-4), training only after D1 |
| 6. Validation | Not started |

---

## Principle

Learn from every mistake the record can prove, weigh it by what it cost and how often it returns,
and change rules through people and weights through the same gates as any other change.
