# Rotor: Cyclic Tri-Pass Reading

*Rotor orders what every agent reads. For a long input its main pattern reads the same material
three times, each in a different rotation, so every part has a turn at the start, in the middle and
at the end. A stage's reading changes only if a benchmark shows the change finds more than the
simpler ways of reading.*

**Status: PROPOSED** (the playbook's *Design*: agreed target, not implemented). **Rotor** is the
factory step that orders what an agent reads. It sits in front of **every** agent's input, inside the
harness boundary (`09_Adaptive_Harness.md`, KAN-47), so no input reaches a model without passing it:
the orchestrator's, the Builder's, triage's, and the session agent's, whose prompts enter through its
ingress hook (KAN-91). Rotor may change how a stage reads only after that stage wins its benchmark
(§7) and is promoted by a reviewed change (§8). Until then it passes the input through unchanged
(arm A) and records, in shadow, the plan it would have used. Every input is in its path from the
first day, and none is changed before the evidence allows it. The
benchmark also tests two alternatives on equal terms, end-focused windows (arm E) and a size-routed
hybrid (arm F), so tri-pass is adopted only where nothing cheaper finds as much. The tri-pass
ordering, the windows and the routing rule are specified exactly and tested
(`tests/contracts/context_order_reference.py`); the contracts they name are specified at the
test-design stage (§10), not before.

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

## 2️⃣ Where It Sits, and Where It May Change the Reading

**Rotor sits in front of every agent's input.** Its size routing (arm F's rule, §7) sends a short
input straight through, so an agent with bounded inputs pays nothing for it. A stage's reading
changes only on promotion, and stages are benchmarked in this order:

| Stage | Input | What a miss costs |
| :--- | :--- | :--- |
| **Session agent (first)** | The owner's prompts and the documents a session reads or updates (READMEs, standards, handoffs) | A section is skipped and the update or answer is incomplete. The first golden task is the README update of 2026-11-16 that missed a large section until the owner pointed at it |
| Spec-to-plan intake (`03_Software_Factory_Intake.md`) | A long spec and the material it cites | A requirement left out of the plan, so the ticket is built without it |
| Incident and log triage | Build, CI and service logs, traces, an incident's timeline | The causal line is in the middle of the log, and the triage names a symptom |
| SecOps investigation context (`07_SoftwareFactory/02_Platform_Patterns.md`) | The events, findings and asset context of one security event | A signal that changes the decision is skipped. The pattern only reads: remediation stays a protected class, approved by a person |

**The Builder** is in Rotor's path like every agent. Its inputs are bounded slices (its notepad
page, a slice of the reuse map, retrieved records), so routing sends them through unchanged, and it
stays the latency-sensitive path. A long Builder input is benchmarked like any other stage before
its reading changes.

**Never in scope:**

- **The Policy Engine.** It is pure and deterministic, with no model calls
  (`00_UniversalStandards/17_Quality_Policy_Engine.md`). There is nothing to read.
- **The Reviewer.** Retired: deterministic CI and per-ticket acceptance tests evaluate every change.
  Its rule of at most 2 model calls per review unit stands for any review unit that remains.

Promoting a stage, or adding one to the table, is a reviewed change to this standard, and the stage
needs its own benchmark.

**Rotor reads; it never decides.** It is a tool (`AGENTS.md` → Agent Rules): typed input, typed
output, no loop, no judgment. It reorders the input it was given, adds and removes nothing, and
every pass draws from the ticket's one budget with its own token records. Whether an *action* may
run is a different check at the same harness boundary, the EEP action gate (KAN-47), which is
deterministic and fails closed.

**When Rotor is unavailable,** the input passes through unchanged with a visible warning on the
session and a `rotor.unavailable` error metric, because reading mutates nothing and stopping every
agent would gain nothing. The action gate never falls back this way: when it is unavailable or
cannot decide, no action runs.

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
| E. Chunk-aligned, end-focused windows | Windows of whole chunks in true order, each ending on its focus group and the restated task, in parallel, then the same synthesis as D (below) |
| F. Size-routed hybrid | Arm A, C, or a long arm (D or E), chosen by the input's length against the stage's thresholds (below) |

Every arm uses the same chunks, the same prompt file and the same citation rule. Arms A and B are
one call on the synthesis rung: the strongest model, reading once. Arms C, D and E run their
extraction on the extraction rung and their synthesis on the synthesis rung. So tri-pass has to beat
the strongest model reading the material straight through, and the cost of doing so is measured.

#### Arm E: chunk-aligned, end-focused windows

"Lost in the middle" makes the middle of a read the weakest position, so a window puts what it is
for at its end, next to the task, never in its centre.

- **Windows slide over whole chunks** (§3: symbols, headings, event windows), never fixed character
  or token spans.
- **Focus groups:** the rotating chunks, in true order, are tiled into contiguous groups whose
  weight is at most the stage's focus budget. A group closes when the next chunk would overflow it;
  a chunk heavier than the budget is a group of its own.
- **Window i reads,** in order: the table of contents and the pinned chunks (the same cacheable
  prefix as every other arm), then its **context** (the whole chunks just before focus group i,
  nearest first, as many as fit in the context budget, shown in true order), then **focus group i**,
  marked as the focus, then the restated task.
- **The guarantee:** every rotating chunk is in the focus slot, the end of a window just before the
  task, exactly once; windows are in true order and have no seam; pinned chunks lead every window and
  never rotate. The reference tests check this for every chunk count up to 300. A defect that crosses
  a group boundary is read whole in the later window only when the context budget holds the chunk
  before the boundary, so D4 sets the context budget at least as large as the stage's largest
  rotating chunk, or records which boundaries it leaves uncovered.
- **Citations:** a window's finding must cite a chunk in that window (its context or its focus); one
  that cites any other chunk is **rejected, not repaired**, and counted, like any unresolved
  citation (§5). The deterministic merge then deduplicates across windows as it does across passes.
- **Cost:** about N × (focus + context) ÷ focus input tokens for N tokens of rotating chunks, plus
  one prefix per window, of which the shared prefix is cached. The context budget is the overlap, so
  it is the cost lever.

#### Arm F: size-routed hybrid

Short inputs have no real middle; long ones do. Arm F reads each input the cheapest way its length
calls for, and the routing rule itself has to win the benchmark.

- **The rule,** on the rotating chunks' total weight L and the stage's two thresholds (D3):
  `L <= t_short` reads as arm A (one linear pass, prefix cached); `t_short < L <= t_long` as arm C
  (per-unit map-reduce); `L > t_long` as the long arm. A length exactly on a threshold takes the
  shorter band. A missing or malformed length **fails closed** to the long arm, the highest-scrutiny
  reading (`AGENTS.md` → Agent Rules).
- **Two variants, both reported:** F-D (the long arm is tri-pass) and F-E (the long arm is the
  windows).
- **Scored by replay, at no extra model cost.** Routing is deterministic, so on every task F's
  result is exactly the result of the arm it routes to, already measured. F makes no calls of its
  own; it needs only tasks in every length band (below).
- **The thresholds are fixed in the benchmark policy file before the first run.** Choosing them after
  seeing results would fit the rule to the data, so the replay refuses a policy file changed after
  the first run's timestamp. New thresholds are a new candidate rule and need a new run on fresh
  tasks.

### Tasks

- **A corpus per stage**, from the factory's own sealed material: the session agent's own prompts
  and the documents it read or updated, with each owner correction of a missed section as a planted
  defect (the README miss of 2026-11-16 first); specs for intake; `docs/incidents/` and CI logs for
  triage; recorded security events for SecOps. The stage benchmarked first is
  decision D1.
- **Three length bands per stage,** short (`L <= t_short`), medium and long (`L > t_long`), with the
  thresholds of D3. The long band is where the middle is real. Every arm runs on every band, so each
  arm's recall is known per band and arm F can be scored by replay.
- **Planted defects at 11 positions**, at 0%, 10%, 20% and so on up to 100% of the input's
  true-order token offset, each a known, fingerprinted defect of the stage's kind: a missing
  requirement, the causal log line, the signal that changes the decision. Each position is covered
  by several tasks and defect types.
- **Designed-to-fail tasks:** a finding citing a chunk that does not exist must be rejected; a defect
  that spans the seam must still be found; a defect planted in a pinned chunk must be found by every
  arm. A task with no planted defect checks false positives.
- **For arms E and F:** a window's finding citing a chunk outside its window must be rejected; a
  defect spanning two focus groups must still be found; a task whose length sits exactly on a
  threshold must route to the shorter band; a task with its length withheld must route to the long
  arm.

### Measures

| Measure | How |
| :--- | :--- |
| Recall by position | Planted defects found, per decile position and per length band, with a 95% interval |
| Worst-decile recall | The lowest of the 11, per band, and the lowest over all bands. The headline measure: lost in the middle shows up here |
| Precision | Findings that match a planted defect, out of all accepted findings |
| Uncached token cost | Input and output tokens, uncached input counted separately, computed from `token_record.v1` |
| Latency | Wall clock from the first call to the synthesis result, p50 and p90, per band |
| Routing (arm F) | The arm each task was routed to, and per band whether that arm was the cheapest passing one |
| Citation-rejection rate | Findings rejected by the deterministic citation check, out of all findings |

## 8️⃣ Promotion

Promotion is decided per stage, starting with the stage chosen in D1, on that stage's corpus over
all its length bands. An arm replaces today's reading only when, against arm A:

1. worst-decile recall, over all bands, is higher with non-overlapping 95% intervals, and is not
   lower in any band;
2. precision is not lower;
3. the citation-rejection rate is not higher;
4. its cost and latency fit the stage's budget.

If several arms pass, the cheapest one whose worst-decile recall is not significantly below the
best passing arm's wins. So arm B, C, E or F can win, and tri-pass is adopted only where it finds
measurably more than every cheaper way of reading. Arm F is promoted only with the thresholds frozen
before the run, and only as the variant (F-D or F-E) that passed; it never wins on latency alone.
The numbers each condition needs (sample sizes, the cost and latency ceilings) are fixed in a
versioned policy file before the first run, never after seeing results, following the calibration
rule for numeric weights (`09_Adaptive_Harness.md` §4). Promotion is a reviewed, human-approved
change. A later fall in worst-decile recall, or a rise in the rejection rate, on the stage's golden
tasks demotes it.

## 9️⃣ Open Decisions

| # | Question | Until decided |
| :--- | :--- | :--- |
| D1 | **The first stage benchmarked.** Decided 2026-11-16 by the owner: the session agent, which is already missing sections in practice. Triage next; intake when an agent architect reads long specs; SecOps when its corpus exists (D2) | Decided |
| D2 | **The SecOps corpus.** SecOps is Run 3, so recorded security events may not exist yet | SecOps benchmark waits for its corpus |
| D3 | **Length bands per stage:** `t_short` and `t_long` in tokens of rotating chunks. `t_long` is where the middle is real; both are arm F's routing thresholds | Fixed in the benchmark policy file at test design, before any run; arm F cannot run without them |
| D4 | **Arm E's budgets per stage:** the focus budget and the context budget, in tokens. The context budget is at least the largest rotating chunk in the stage's corpus, or the uncovered boundaries are recorded | Fixed in the same policy file, before any run |

## 🔟 Status

| Stage | State |
| :--- | :--- |
| 1. Hypothesis | Done (2026-11-16) |
| 2. Codification | This standard, and the reference ordering with its tests |
| 3. Review | Owner review of this standard |
| 4. Test design | Not started: contracts `context_pass_plan.v1` (passes, windows and the routing decision) and `context_finding.v1`, the benchmark policy file (D1, D3, D4 and the promotion numbers), the per-stage corpora in three length bands, and the golden tasks |
| 5. Implementation | Not started: Rotor in the harness boundary (KAN-92), the session ingress hook (KAN-91); the session agent first |
| 6. Validation | Not started: the benchmark of §7, per stage |

---

## Principle

Every input passes Rotor. Read long material so that no part of it is always in the middle, cite
every finding to where it was found, and change a way of reading only when it measurably finds more
than a simpler one.
