# Adaptive Harness: Test Design

Stage 4 of `06_AgentZone/09_Adaptive_Harness.md` (KAN-47). These are the tests a harness implementation
must later pass. Writing them is not implementation: nothing here runs in the factory, and a passing
contract test is not proof that a runtime capability exists.

| Part | File |
| :--- | :--- |
| Conformance vectors (104 cases, 72 designed to fail) | `schemas/examples/harness/vectors.json` |
| Reference checker (the oracle) | `tests/contracts/harness_reference.py` |
| Tests | `tests/contracts/test_harness_conformance.py` |
| The agent-ddi-harness pin | `tests/contracts/harness_conformance/ddi_pin.json` |

## 1️⃣ Contracts: No New Schema

Inputs and decisions are checked against the playbook's locked contracts, which already carry the
reliability states, `QUARANTINE`, the budget and the attribution chain:

- `harness_decision.v1`: one decision, its inputs and its action;
- `knowledge_record.v1`: one long-term memory record, its standing and its attributions.

Every violation is emitted as two documents from `Drecoder/agent-ddi-harness`:

- a `ddi.event.v1` with `kind: "error"`, named `harness.block.<check>`;
- a `ddi.capa_draft.v1` (status `draft`, trust `unverified_claim`) whose fingerprint is the check plus
  the subject, so a recurrence updates the same draft.

Both cite `eep-rule` IDs. Those schemas and catalogs are read from a checkout of the commit in
`ddi_pin.json`, each file verified by SHA-256. They are never copied into this repository, and no
locked contract is edited. CI checks the commit out at `.ddi-harness`; a missing or changed file fails
the tests rather than skipping them.

| Violation class | `eep-rule` IDs cited |
| :--- | :--- |
| Every violation | `CAPA-001` (every block is a CAPA signal), `CAPA-003` (a draft is a claim) |
| Evidence: missing or unverified evidence, a stale or unproven GREEN, an attribution without its chain, a broken Loop A or Loop B link, a transient event promoted | `HAB-005` (prove with evidence) |
| Scope: an action outside its row, concurrency, the ladder, the attempt limit, the capability boundary, oscillation, an unavailable gate | `HAB-004` (keep to what the intent asks) |
| Recurrence | `CAPA-002` (one draft per fingerprint), through the stable fingerprint |

The EEP catalogs were written for pushes, so this mapping is by analogy. It is the owner's to confirm.

## 2️⃣ The Matrix

| Area | Standard | Cases | What is proven |
| :--- | :--- | :--- | :--- |
| Decision table | §7 | `HD-001`–`HD-057` | One case per row (0–12), the first matching row decides, each row's allowed set, and a designed-to-fail case for every way a row can be broken |
| Contract constraints | schemas | `HD-*`, `KR-*` with `schema_constraints` | Every `allOf` rule of both schemas, the action rules and the quality `if`/`then` are tripped by a named case |
| Cross-file checks | §8; schema description | `HD-028`–`HD-041` | Concurrency down only, within the ceiling (O1 still open); a rung on `model_ladder.v1`, at a task boundary; a retry within the attempt limit |
| Reliability states | §5 | `RS-001`–`RS-013` | GREEN, RED and UNKNOWN from burn-rate fixtures, stale and future evaluations, contradictory sources, no SLOs, no sources |
| Practice standing and attribution | §3, §5 | `KR-001`–`KR-017` | Standing is recomputed, never reported; only a resolving chain counts; `review_by` ages a record to UNKNOWN; transient events are never promoted |
| Retrieval | §4 | `RT-001`–`RT-006` | Precedence, standing, applicability, outcomes, freshness; ineligible records dropped; RED returned as a caution |
| Retrieved content is data | §3 | `RD-001` | A record carrying instructions stays inside the data block |
| Inbound boundary (Rotor) | owner decision, 2026-11-16 | `BD-001`–`BD-003` | Pass-through is unchanged; Rotor down still passes, with a visible warning; the README-miss golden task |
| Outbound boundary (action gate) | owner decision, 2026-11-16 | `BD-004`–`BD-007` | Deterministic; denies when down or unable to decide |
| Golden tasks | §11 | `GT-001`–`GT-003` | Whole runs through the gate, two of them designed to fail |

Every one of the 24 acceptance criteria (§14) and the eight adversarial cases have a tagged case, and
the tests fail if one goes missing.

## 3️⃣ How a Designed-to-Fail Case Counts

A case designed to fail counts only once it is shown to fail:

1. it is caught: the checker reports exactly the checks the case expects;
2. it gets through when those checks are switched off: the same input then reports nothing, so the
   case depends on the check and on nothing else;
3. every check, and every schema constraint, has at least one such case.

Reliability, retrieval and rendering cases are proven against a naive implementation instead. Each
designed-to-fail fixture gives a different answer from a reader that treats "not firing" as GREEN, from
ordering by similarity, or from concatenating summaries into the prompt.

The reference checker was also mutation-tested by hand: 25 seeded defects (a wider freshness window, a
dropped row, the wrong default row, extra actions allowed in row 0, unverified digests, attribution
without the cited record, a flattened precedence, an unescaped render, a gate that never denies, and
others), all 25 caught. The two that first survived exposed real gaps, now closed by `HD-057` and
`RT-006`.

## 4️⃣ Retrieval Calibration Protocol

Numeric retrieval weights stay forbidden until this protocol is run and its result reviewed (§4,
O4). The lexicographic order of §4, conformed to by `RT-*`, is the baseline any weighting must beat.

1. **Labelled set.** Take past tasks with sealed `harness_decision.v1` records. For each, record which
   knowledge records were retrieved and cited, and the outcome measure of `10_Autonomy_by_Evidence.md`
   §7: the change was accepted with no defect traced to it within one full measurement `period` of its
   process class. Transient failures (§3) are excluded from the labels.
2. **Holdout.** Split by time, never at random: the most recent 30% of tasks, by `recorded_at`, is the
   holdout. Fix the split and the measure before any weight is fitted, and record both in the report.
3. **Compare.** On the holdout, score the weighted order against the lexicographic order with the same
   measure: the rate of accepted, defect-free changes among tasks whose top-cited record came from each
   order. The weighted order must win at 95% confidence. A tie keeps the lexicographic order.
4. **Versioned weights.** Weights live in a versioned policy file beside its calibration report (data,
   split, measure, result, the commit of the reference that produced it). Changing them is a
   behavioral change: the golden tasks run before it ships.
5. **Recalibration trigger.** The outcome measure is tracked on a p-chart
   (`10_Autonomy_by_Evidence.md` §6). An out-of-control point reverts retrieval to the lexicographic
   order at once and reopens calibration. The weights are not tuned in place.

## 5️⃣ Readings the Owner Should Confirm

The standard leaves these open. The cases encode the most conservative reading, and changing one is a
change to the vectors.

| # | Reading | Where |
| :--- | :--- | :--- |
| T1 | When no row applies (for example a PASS that carries a high-CRAP finding), the table "cannot decide": only `pause` or `escalate_to_human` (§10), recorded as row 0 | `HD-054`, `HD-055`, `HD-057` |
| T2 | "Within a row" adaptations (`reorder_work`, `pace_down`, `switch_tool`, `change_model_rung`) are allowed in rows 4–12 only. Rows 1–3 are closed by the schema, and row 0 escalates | `HD-036`, `HD-057` |
| T3 | A recorded GREEN carries one evaluation time, so it must fall within the stricter page window (5 minutes) | `HD-013`, `HD-014` |
| T4 | "Strong mutation" is read as no surviving signal, because `harness_decision.v1` does not carry `mutation_green_min` | `HD-022` |
| T5 | Sources that contradict each other make a subject UNKNOWN, even when one of them says RED | `HD-015`, `RS-013` |
| T6 | The `eep-rule` mapping in §1 | `Emission` tests |

## 6️⃣ Running It

```bash
git clone https://github.com/Drecoder/agent-ddi-harness .ddi-harness
git -C .ddi-harness checkout <commit in ddi_pin.json>
docker run --rm -v "$PWD:/work:ro" playbook-antipattern-toolchain \
    python -m unittest discover -s tests/contracts -v
```
