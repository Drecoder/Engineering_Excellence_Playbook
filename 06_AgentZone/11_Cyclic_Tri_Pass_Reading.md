# Cyclic Tri-Pass Reading

*A reading pattern for long inputs: the model reads the same material three times, each time in a
different rotation, so every part of it has a turn at the start, in the middle and at the end. It is
adopted for a stage only if a benchmark shows it finds more than the simpler ways of reading.*

**Status: PROPOSED** (the playbook's *Design*: agreed target, not implemented). Nothing here is used
by any agent. The pattern may run in a stage only after it wins that stage's benchmark (§7) and is
promoted by a reviewed change (§8). Until then, every stage reads the way it does today. The
ordering is specified exactly and tested (`tests/contracts/context_order_reference.py`); the
contracts it names are specified at the test-design stage (§10), not before.

---

## 1️⃣ The Problem

Models attend less to the middle of a long input than to its start and end ("lost in the middle").
A defect, a log line or a spec clause that sits in the middle of a long read is the one most likely
to be missed.

Two obvious fixes do not work well enough:

- **Reading from the middle outwards** (middle, then up, then down; or middle, then down, then up)
  puts the centre first, but buries other chunks in the middle of two passes out of three, repeats
  the same opening chunk, and gives identical passes for two chunks.
- **Rotating the chunk list** by thirds cannot guarantee each chunk one turn in each third when the
  chunk count is not a multiple of 3. The reference tests prove this for 4 chunks.

What does work is to cut the input into **three segments** and rotate the segments (§3).

## 2️⃣ Where It Applies, and Where It Never Does

**In scope**, because the input is long and unstructured, missing something is costly, and no
deterministic tool reads it for us:

| Stage | Input | What a miss costs |
| :--- | :--- | :--- |
| Spec-to-plan intake (`03_Software_Factory_Intake.md`) | A long spec and the material it cites | A requirement left out of the plan, so the ticket is built without it |
| Incident and log triage | Build, CI and service logs, traces, an incident's timeline | The causal line is in the middle of the log, and the triage names a symptom |
| SecOps investigation context (`07_SoftwareFactory/02_Platform_Patterns.md`) | The events, findings and asset context of one security event | A signal that changes the decision is skipped. The pattern only reads: remediation stays a protected class, approved by a person |

**Excluded, always:**

- **The Policy Engine.** It is pure and deterministic, with no model calls
  (`00_UniversalStandards/17_Quality_Policy_Engine.md`). There is nothing to read.
- **The Builder's slices.** The Builder already gets bounded slices (its notepad page, a slice of the
  reuse map, retrieved records), so there is no long middle, and it is the latency-sensitive path.
  Three reads would multiply its cost and time for no measured gain.
- **The Reviewer.** Retired: deterministic CI and per-ticket acceptance tests evaluate every change.
  Its rule of at most 2 model calls per review unit stands for any review unit that remains.

Adding a stage to the scope is a reviewed change to this standard, and the stage needs its own
benchmark.

## 3️⃣ The Ordering

**Chunks follow the material's own boundaries**, never fixed character or token windows:

- code: symbols from rig's symbol index (function, class, module), and a diff hunk is never split;
- specs: sections by heading;
- logs: one event window or one trace per chunk.

**Pinned chunks** carry what everything else depends on: a file's imports, exports and interfaces,
or a spec's goals and definitions. They are not rotated. They come first in every pass, after the
table of contents.

**The rotating chunks**, in true order, are cut into three contiguous segments S0, S1 and S2 of
near-equal token weight. Each cut is the chunk boundary nearest a third of the total; a tie takes the
earlier boundary. Every segment keeps its true internal order. The three passes are:

```text
pass 1:  S0 S1 S2     true order, identical to a linear read
pass 2:  S1 S2 S0     one seam, between S2 and S0
pass 3:  S2 S0 S1     one seam, between S2 and S0
```

**The guarantee:** every rotating chunk is in the first segment of exactly one pass, the middle
segment of exactly one pass, and the last segment of exactly one pass. No chunk is in the middle
twice, and no pass repeats another. With 2 rotating chunks there are 2 passes (each chunk first once
and last once); with 0 or 1 there is one. The reference tests check this for every chunk count up to
300, with equal, random and skewed weights, with and without pinned chunks.

**Caching:** all three passes share one prefix, the instructions, the table of contents and the
pinned chunks, and pass 1 shares its whole prompt with a linear read. Passes 2 and 3 pay their
rotated segments uncached, so the cost is close to three reads, not less. That is measured, not
assumed (§7).

## 4️⃣ The Prompt

Every pass uses the same versioned prompt file, with untrusted input delimited as data:

1. **The table of contents, in true order:** every chunk's ID, symbol or heading, and line range. It
   is the same in every pass and tells the model the real order whatever order it reads in.
2. **Each chunk wrapped with its anchor:** `[Chunk i of N | <symbol or heading> | lines a–b]`.
3. **A seam marker** where a rotated pass jumps back: "the next chunk comes earlier in true order".
4. **An extraction task, not an understanding task:** "list findings, each citing one chunk ID and a
   line range inside it." The model is never asked to reconstruct execution order from the reading
   order.
5. **The instructions restated at the end**, so the task itself is in the strongest positions.

## 5️⃣ Findings, Citations and Synthesis

- **Every finding cites a chunk ID and a line range inside it.** Code resolves each citation against
  the chunk map. One that does not resolve (an unknown chunk, or a line range outside its chunk) is **rejected, not repaired**, and counted.
- **Deterministic merge first:** code deduplicates findings across passes by chunk, line range and
  fingerprint, and records which passes found each one.
- **Then synthesis,** over the surviving findings in true order. It may issue one declarative
  `evidence_request.v1` (`symbol_context`) to re-read a chunk it doubts; it never fetches anything
  itself. Its own findings follow the same citation rule.
- Findings are claims (`AGENTS.md` → Agent Rules). Reading more carefully never turns a claim into
  evidence.

## 6️⃣ Models and Budget

- The three passes are independent and run in parallel, on the rung the model ladder selects for
  extraction. Synthesis may run on a higher rung (`01_Agent_Standards.md` §6).
- Synthesis sees only findings, so it cannot recover what every pass missed; its evidence request
  is the only way back into the material.
- Every pass draws from the ticket's one budget, computed from token records, never reported.

## 7️⃣ The Benchmark (Golden Tasks)

A stage adopts the pattern only by winning this benchmark. It runs per stage, in the pinned
toolchain image, and every result is telemetry: a span, a structured log line with `trace_id`, and a
metric (`AGENTS.md` → Observability Rules).

### Arms

| Arm | How the input is read |
| :--- | :--- |
| A. Single linear | One pass, true order |
| B. Linear with restated instructions | One pass, true order, the task restated at the end |
| C. Parallel per-unit map-reduce | One small extraction call per rotating chunk, each also given the table of contents and the pinned chunks, in parallel, then the same synthesis as D |
| D. Cyclic tri-pass | §3 to §5 |

Every arm uses the same chunks, the same prompt file and the same citation rule. Arms A and B are
one call on the synthesis rung: the strongest model, reading once. Arms C and D run their extraction
on the extraction rung and their synthesis on the synthesis rung. So tri-pass has to beat the
strongest model reading the material straight through, and the cost of doing so is measured.

### Tasks

- **A corpus per stage**, from the factory's own sealed material: specs for intake, `docs/incidents/`
  and CI logs for triage, recorded security events for SecOps. Inputs are long enough that the
  middle is real (the length is fixed per stage at test design).
- **Planted defects at 11 positions**, at 0%, 10%, 20% and so on up to 100% of the input's
  true-order token offset, each a known, fingerprinted defect of the stage's kind: a missing
  requirement, the causal log line, the signal that changes the decision. Each position is covered
  by several tasks and defect types.
- **Designed-to-fail tasks:** a finding citing a chunk that does not exist must be rejected; a defect
  that spans the seam must still be found; a defect planted in a pinned chunk must be found by every
  arm. A task with no planted defect checks false positives.

### Measures

| Measure | How |
| :--- | :--- |
| Recall by position | Planted defects found, per decile position, with a 95% interval |
| Worst-decile recall | The lowest of the 11. The headline measure: lost in the middle shows up here |
| Precision | Findings that match a planted defect, out of all accepted findings |
| Uncached token cost | Input and output tokens, uncached input counted separately, computed from `token_record.v1` |
| Latency | Wall clock from the first call to the synthesis result, p50 and p90 |
| Citation-rejection rate | Findings rejected by the deterministic citation check, out of all findings |

## 8️⃣ Promotion

For each stage, an arm replaces today's reading only when, against arm A:

1. worst-decile recall is higher, with non-overlapping 95% intervals;
2. precision is not lower;
3. the citation-rejection rate is not higher;
4. its cost and latency fit the stage's budget.

If several arms pass, the cheapest one whose worst-decile recall is not significantly below the
best passing arm's wins. So arm B or arm C can win, and tri-pass is adopted only where it finds
measurably more than every cheaper way of reading.
The numbers each condition needs (sample sizes, the cost and latency ceilings) are fixed in a
versioned policy file before the first run, never after seeing results, following the calibration
rule for numeric weights (`09_Adaptive_Harness.md` §4). Promotion is a reviewed, human-approved
change. A later fall in worst-decile recall, or a rise in the rejection rate, on the stage's golden
tasks demotes it.

## 9️⃣ Open Decisions

| # | Question | Until decided |
| :--- | :--- | :--- |
| D1 | **Intake's reader.** Specs are drafted by an architect, a person or an agent, and approved by the owner. The pattern helps an agent architect; whether one reads long specs today decides if the intake benchmark runs first | Intake waits; triage can run first |
| D2 | **The SecOps corpus.** SecOps is Run 3, so recorded security events may not exist yet | SecOps benchmark waits for its corpus |
| D3 | **Input length per stage** at which the middle is real | Fixed at test design, before any run |

## 🔟 Status

| Stage | State |
| :--- | :--- |
| 1. Hypothesis | Done (2026-11-16) |
| 2. Codification | This standard, and the reference ordering with its tests |
| 3. Review | Owner review of this standard |
| 4. Test design | Not started: contracts `context_pass_plan.v1` and `context_finding.v1`, the benchmark policy file, the per-stage corpora, and the golden tasks |
| 5. Implementation | Not started; triage first |
| 6. Validation | Not started: the benchmark of §7, per stage |

---

## Principle

Read long material so that no part of it is always in the middle, cite every finding to where it
was found, and adopt a way of reading only when it measurably finds more than a simpler one.
