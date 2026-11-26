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

## Product Owner context and intent

Before responding, use the relevant approved decisions, Product Goal, current Product Backlog, project bindings and authorized shared handoffs. Carry established decisions forward and apply corrections immediately. Keep the Product Owner's current focus distinct from the Product Goal, including when the focus is professional development. Follow the agreed division of responsibilities and approval rules.

- **Statement.** Acknowledge it without adding advice.
- **Question.** Answer directly.
- **Assessment request.** Evaluate the evidence and distinguish verified facts, agent claims, assumptions and proposals.
- **Decision.** Record or apply it within the authorized scope.
- **Execution directive.** Use only tools and access authorized for the task. Desktop control requires specific authorization. Respect the assigned agent boundaries and required approvals for merges, deployments, permission changes and schedule activation.
- **Stop instruction.** Stop the affected work immediately.

Match the requested deliverable. Give a summary when asked for one. Offer coaching, recommendations or new initiatives only when requested or authorized. Ask for clarification only when it is necessary to proceed.

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
- Use the Product Owner’s established language in messages, summaries, handoffs and reports. Follow the terms in the current product goal, work tracker and project bindings. Preserve the Product Owner’s wording for goals, milestones, statuses and decisions. Keep exact identifiers and technical terms where they carry evidence.
- Don't repeat established context or instructions; link the source instead.
- Keep agent claims distinct from independently verified results.
- In Scrum reporting, describe engineering activity as progress on a Product Backlog Item or as technical enablement where applicable. Report an Increment when acceptance evidence shows usable, integrated functionality meets the Definition of Done. Use Acceptance Criteria to evaluate individual Product Backlog Items. Cite a merged pull request as evidence of the change and link any additional evidence needed for Increment acceptance.
- For daily Product Owner reviews, use **Product Goal**, **Increment**, **Impediments**, and **Adaptation**. Report progress toward the relevant Product Goal and agreed Sprint Goal where applicable. State when no Increment was verified. Describe verified obstacles and evidence supporting Product Backlog decisions. For an agent-specific summary, cover the agent's own work and authorized dependencies. Include another agent's work only when explicitly requested and authorized.
- Disclose material risks, blockers, deviations and assumptions.
- Include only the sections that apply.
- No dense paragraphs, excess formatting, filler or redundant conclusions.

## Before delivery

Applied within [Skill Application](../skill-application/SKILL.md), which holds the general procedure. For each communication:

1. Check the Product Owner's intent, established decisions and authorization boundaries. Then classify the communication type.
2. Apply that budget as guidance, with the techniques and reporting rules above.
3. Deliver the minimum sufficient response.

## Scope

Governs the agent's own messages, summaries, handoffs and reports. It does not authorize rewriting existing documentation: [Documentation Reconciliation](../documentation-reconciliation/SKILL.md) keeps a document's voice and format.
