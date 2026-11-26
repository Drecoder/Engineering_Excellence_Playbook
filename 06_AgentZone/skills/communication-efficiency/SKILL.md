---
name: "communication-efficiency"
description: "Apply silently throughout every task to minimize reading volume, cognitive load and tokens without reducing accuracy, reasoning, verification or governance."
---

# Communication Efficiency

The single source of truth for how agents communicate. Apply it silently from context intake through reasoning, planning, execution and reporting. It shapes how work is reported, never how much reasoning or verification is done. It does not override the playbook's standards, your identity and permission authority, other skills' required formats or the owner's authorization.

Compress communication, not intelligence.

## Techniques

- **DRY:** say each thing once.
- **KISS:** use the simplest accurate explanation.
- **Lean:** cut anything that adds no value.
- **Chunking:** group related information into meaningful units.
- **Plain language:** aim for ninth-grade readability; keep technical precision.
- **Visual hierarchy:** descriptive headings, selective bold, left-aligned text, whitespace.
- **Progressive disclosure:** essentials first; expand only when needed.
- **Dual coding:** use a table or diagram when clearer than prose.
- **Schema formation:** keep reporting structures predictable.
- **Fewer context switches:** group related findings and decisions.

## Response budget

Classify each response by what it actually communicates, not by the task phase, and compose only the sections that apply. Budgets cover the whole response, including table headings and cells.

| Communication type | Words |
| --- | ---: |
| Status update | 25–50 |
| Task completion | 50–100 |
| Owner approval | 100–150 |
| Architectural decision | 150–250 |
| Incident analysis | 250–500 |

Budgets are flexible guidance, not minimums. Use fewer words when they suffice. Required evidence, material disclosures and required handoff or summary fields take precedence: keep them even when they take the response over budget. Exceed it otherwise only for correctness or safety.

## Reporting rules

- Report the delta, not the whole system state.
- Lead with outcomes and required decisions.
- Don't repeat established context or instructions; link the source instead.
- Keep agent claims distinct from independently verified results.
- Disclose material risks, blockers, deviations and assumptions.
- Include only the sections that apply.
- No dense paragraphs, excess formatting, filler or redundant conclusions.

## Before delivery

Applied within [Skill Application](../skill-application/SKILL.md), which holds the general procedure. For each communication:

1. Classify its communication type.
2. Apply that budget as guidance, with the techniques and reporting rules above.
3. Deliver the minimum sufficient response.

## Scope

Governs the agent's own messages, summaries, handoffs and reports. It does not authorize rewriting existing documentation: [Documentation Reconciliation](../documentation-reconciliation/SKILL.md) keeps a document's voice and format.
