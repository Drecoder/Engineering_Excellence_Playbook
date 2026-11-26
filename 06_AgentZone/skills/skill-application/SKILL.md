---
name: "skill-application"
description: "Apply at the start of every task: how an agent selects, loads, composes and applies the skills in this set, and reassesses them as the task changes."
---

# Skill Application

The one procedure for using the playbook's shared agent skills. It adds no authority: the playbook's standards, your identity and permission authority and the owner's current authorization govern, as every skill states.

## Skills

| Applies | Skill |
| --- | --- |
| Every task, throughout | [Prevent Drift](../prevent-drift/SKILL.md), [Communication Efficiency](../communication-efficiency/SKILL.md) |
| When its description matches the task | [Session Handoff](../session-handoff/SKILL.md), [PR Hygiene](../pr-hygiene/SKILL.md), [Documentation Reconciliation](../documentation-reconciliation/SKILL.md), [Owner Summary](../owner-summary/SKILL.md) |

## Bindings

The skills stay environment-neutral. One private bindings document per environment fills these slots and names the playbook commit SHA its skills are read at:

| Slot | What it names |
| --- | --- |
| Identity and permission authority | Who grants and enforces agent access |
| Work tracker | Where tickets and finding IDs live |
| Change route | How agent changes land: branch, bot identity, human merge |
| Findings record | The corrective-action register |
| Handoff store | Where handoffs live, per-agent folders, any manifest, the fallback location |
| Standing authorized operations | What agents do without asking each time |
| Context provider (optional) | Where shared context is hydrated from |
| Status inventory (optional) | A reference map of work |
| Priority rule (optional) | What leads "Next" and which scope stays out |

A binding may add environment-specific requirements; it never weakens a skill. The playbook's standards prevail over both.

## Procedure

1. **Intake:** identify the objective, scope and constraints from the prompt, its ticket and the relevant shared context. Hydrate that context from your configured context provider where one exists; otherwise read the sources directly.
2. **Select:** the always-on skills plus each conditional skill whose description matches.
3. **Load:** read the selected skills at the version your bindings pin, never from an unpinned, local or synced copy. Then read your bindings.
4. **Compose:** apply every selected skill. Skills hold no rank among themselves. When two conflict and neither text settles it, escalate through the existing route (Owner Summary's Decision needed, or Session Handoff's Owner decisions open); don't resolve it yourself.
5. **Apply:** keep the selected skills active through reasoning, planning, execution, verification and reporting.
6. **Reassess:** when the task or its context changes (a new PR, a failed check, a handoff, new shared context, a document to reconcile), repeat steps 1 and 2.
7. **Validate:** check adherence before delivery. An agent's self-check is a claim, not independent evidence. Existing CI gates and the owner-controlled merge stay mandatory. Review by another agent is advisory by default. It blocks only when existing authoritative governance explicitly requires it, or when an unresolved material discrepancy prevents approval. Existing requirements for shared contracts, protected changes and risk escalation are unchanged. Unless a cross-agent review is mandatory, describe a PR as "ready for owner review after required checks", and share review findings through the handoff and the findings record.
8. **Feedback:** preserve material findings through the existing shared context (the handoff store, and the findings record for findings), and route a material deviation through your existing corrective-action procedure.

## Known limitation

Loading is manual: an agent reads the skills because its starter prompt says to. This set does not claim automatic loading; that depends on your harness.
