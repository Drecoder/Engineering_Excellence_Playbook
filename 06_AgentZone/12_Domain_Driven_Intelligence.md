# Domain-Driven Intelligence (DDI)

*DDI governs how intelligent agents understand, execute, verify and improve engineering work by
the same domain rules that govern the people doing it. Intelligence works inside the domain's
boundaries; it does not get to redefine them.*

**Status: PROPOSED** (the playbook's *Design*: agreed target, not implemented in the factory).
This document names the discipline the factory's agent standards add up to, states its principles,
and points at its open-source reference implementation, `Drecoder/agent-ddi-harness`. It changes
no rule in `AGENTS.md`: every rule it relies on is already there or proposed elsewhere in this
playbook. What it adds is the frame that ties them into one loop.

---

## 1️⃣ The Proposition

Agents can be autonomous in execution while staying constrained by domain rules and accountable to
verifiable evidence. Three conditions make that true at once:

1. the boundaries (bounded contexts, invariants, engineering rules) are written by people and
   enforced deterministically, outside the agent's reach;
2. everything an agent produces about its own work is a claim until an independent, signed
   process proves it;
3. what the agent learns comes only from verified failures, through changes a person approves.

DDI is not "AI applied to software development". It applies domain-driven governance to the
agents themselves.

## 2️⃣ What DDI Aggregates

| Discipline | Contributes | In the factory |
| :--- | :--- | :--- |
| **DDD**, Domain-Driven Design | what the system must respect: bounded contexts, ubiquitous language, invariants | bounded contexts and invariants per repository; rules in `AGENTS.md` |
| **TDD**, Test-Driven Development | how behaviour is specified and checked: a failing test first, then the change | acceptance tests first (`AGENTS.md`); the CRAP → mutation → TDD-pyramid gates |
| **EDD**, event-, error- and evidence-driven development | what must be demonstrated, and what moves work forward: state events advance it, error events (a broken premise, a tripped gate, a conflict) are first-class signals, and progress counts only with evidence | the CAPA journal and register; CI-signed results as the only evidence |

DDD defines what must be respected, TDD how behaviour is tested, EDD what must be shown. DDI
applies all three to the agent's own decisions, actions, corrections and learning.

> **Open question for the owner:** "EDD" is used here in its combined sense, events and errors
> as the signals and evidence as the bar, which is how the reference implementation works. If
> the playbook should define EDD as evidence-driven only, §2 and §3 narrow accordingly.

## 3️⃣ The Five Elements

| Element | What it means | Where it lives in this playbook |
| :--- | :--- | :--- |
| **Domain governance** | engineering rules, bounded contexts and invariants, written and owned by people | `AGENTS.md`; the anti-pattern catalog; the governance baseline |
| **Intelligent orchestration** | agents interpret the task and select the context and rules that apply to it | Rotor (`11_Cyclic_Tri_Pass_Reading.md`); intake (`03_Software_Factory_Intake.md`) |
| **Deterministic enforcement** | a harness governs actions and blocks violations; rules come from catalogs no agent can write; it fails closed | the harness boundary (`09_Adaptive_Harness.md`); the Policy Engine |
| **Evidence-based verification** | tests, CI provenance, and CAPA closure on verifiable evidence | the gates; the compliance authority; the CAPA register |
| **Controlled learning** | verified failures inform rules, thresholds and agent behaviour, through reviewed changes | the CAPA graph and risk-weighted learning (`10_CAPA_Graph_and_Risk_Weighted_Learning.md`) |

## 4️⃣ The Loop

One continuous loop, every phase reading the same rule catalogs:

1. **Scope and slice.** Read the change (diff, intent, conflicts); classify its bounded contexts
   and risks; rank the rules that apply: domain invariants, the five inner-loop habits (Scope &
   Premise Check, Investigate & Blast Radius, TDD & Root Cause, Minimal Diff & Architecture,
   Prove With Evidence), CAPA rules and merge-conflict rules (`06_Merge_Conflicts.md`).
2. **Rule-gated execution.** Enforce the machine-checkable rules before any gate runs.
3. **Capture.** Every error event opens or updates a structured CAPA or conflict draft with its
   evidence, so nothing is copied into an issue, a PR or a chat by hand.
4. **Gauntlet.** CRAP, then mutation, then the TDD pyramid, on exactly what is pushed; stop at
   the first failure.
5. **Feedback.** The verification artifact, the drafts and the events feed the next attempt.

What is automatic and what is not:

- **Automatic:** identifying failures, writing and updating drafts, the agent's own correction
  attempts, assembling the evidence a closure needs.
- **Never automatic:** closing a CAPA (it closes on CI-signed evidence and the owner's promotion),
  changing a rule or threshold (a reviewed change), merging (the owner approves every merge).

## 5️⃣ Where It Runs

- **Inside the factory:** in the Builder's pass, before it opens a pull request. A block sends
  the draft back into the Builder's next attempt; a pass sends the artifact and drafts with the
  PR as claim checks. The Builder gains no identity in the execution plane; CI and the compliance
  authority remain the only evidence. Failure signals from the factory's own plumbing (DLQs,
  failed webhooks, PR conflicts) use the same draft schema. It belongs under the harness boundary
  (KAN-47): its test design is approved before it is built into the Builder.
- **Standalone:** a `pre-push` hook for any repository, person or agent, from the same source
  pinned to a commit.

## 6️⃣ Reference Implementation

[`Drecoder/agent-ddi-harness`](https://github.com/Drecoder/agent-ddi-harness), MIT, first commit
`67d5500`. Level 1 is a complete local pre-push harness (Python and git only, no cloud, no
credentials); Level 2 (vectorized CAPA graph lookup) and Level 3 (CAPA graph export for a tuner)
are disabled seams. As measured at that commit, on its own runs:

- three local demos, each a real `git push` through the hook: a clean change passes all three
  gates; a weak test is blocked by mutation testing with a CAPA draft that a retry updates rather
  than duplicates; a merge conflict left half-resolved is blocked, and the finished resolution
  passes with a conflict draft that identifies the paths both sides changed;
- 61 tests, including a designed-to-fail case per enforced rule and gate, and seven negative
  fixtures in which drafts and events forge CI certification and are rejected;
- it gates its own pushes. Its first runs on itself blocked on real defects (an undeclared
  bounded-context crossing, a coverage bug that ran zero tests, five CRAP violations, 20
  surviving mutants), each fixed at the root; its first push to GitHub passed its own gate at
  CRAP worst 30.0, mutation 80% on a 40-of-528 sample, pyramid 41 unit / 20 integration.

Its three mutation results come from three different populations and are never added together:

- **targeted replay**, 17 of 17 killed: the surviving mutants of the first self-run that still
  applied after the fixes, re-applied one by one. It shows those weaknesses are closed and says
  nothing about any other mutant;
- **sampled gate run**, 8 survived of 40 (80%): an evenly spaced sample of the 528 mutants of the
  changed code, drawn by the pre-push gate. It estimates the whole population;
- **full population**, every mutant with no sampling, from CI's sharded `mutation` job, whose merge
  refuses a partial count. Pending its first run in the pinned image; only this one is a complete
  survivor count.

Those are claims of a local run, recorded in the repository. They were measured with host-installed
Python, not in a container pinned by digest, so under the Container Rules they are provisional until
re-run in a pinned image; they become evidence when CI re-runs them and signs the result.

## 7️⃣ What Would Make It a Field

Naming a discipline is not establishing one. DDI would need, in this order:

1. a formal definition (this document, once accepted);
2. a reference architecture (§4–§5, and the factory's architecture with the loop placed in it);
3. repeatable benchmarks: the reference implementation's demos are a start; comparative ones
   (agents with and without the loop, on the same tasks, scored by defects that reach CI) are
   the next step;
4. independent adoption: others using the reference implementation, or building their own, and
   reporting results.

Until then this playbook treats DDI as a proposed design, like any other.
