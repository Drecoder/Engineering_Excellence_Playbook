---
name: "owner-summary"
description: "Use before changing the work tracker, the code host, cloud resources, the status inventory or any permission, and when a task finishes: a short executive summary for the owner."
---

# Owner summary

The owner reviews intent first and inspects supporting evidence or diffs when risk, policy or uncertainty requires it. Produce this summary at two points:

1. **Before an external mutation or a permission expansion** (about 70% of the way through a task): what is about to change, so the owner can redirect before anything is written. Such changes keep whatever approval they already require; the summary does not replace that approval. For standing authorized operations, the summary gives visibility, not permission: send it and proceed without waiting.
2. **At the end of the task**: what changed and what the evidence is.

Read-only work (reading tickets, runs, logs or code; running checks that change nothing) proceeds under existing authorization with no summary first.

## Governed autonomy

The operations your bindings list as standing authorized are done without asking each time. Escalate (Decision needed) only when an operation exceeds existing authorization, needs a governance exception, hits a blocker or needs a human decision. Merging, expanding permissions and deleting records stay human. This changes behaviour, not access: no new permissions.

Keep it short enough to read on a phone. Never recap the steps taken.

## Format

**Heading:** `Owner summary: <task>` plus `(before execution)` or `(done)`.

1. **Outcome** - one or two sentences: what this delivers or changes, and whether anything has been written yet.
2. **Changes** - a table: item (ticket key, PR, repo, status-inventory row ID as a link) | what changes | notes. One row per item touched.
3. **Evidence** - for each claim, say which it is: *verified* (with the link: CI run, PR, register row), *claimed but not verified* (and why not), or *blocked* (and what would unblock it). Never present a claim as verified because it passed locally or because an agent reported it. Link the diff or evidence so the owner can inspect it when risk or uncertainty calls for it.
4. **Decision needed** - the one question the owner must answer, or "none".
5. **Risks** - only if something is irreversible or widens permissions; otherwise omit.

## Rules

- Every PR as a hyperlink, never a bare number. Ticket keys link to the work tracker.
- Reference the work tracker's and status inventory's IDs wherever an item has one.
- Use the evidence maturity terms where they apply: EXISTS, IMPLEMENTED, INTEGRATED, VERIFIED (CI-signed), OPERATIONALLY VERIFIED.
- Hold to your priority rule: if a change expands a frozen definition of done, flag it under Decision needed instead of folding it in.
- Prefer amending an existing ticket to proposing a new one; say which.
- Things the agent could not do (refused tool, missing access) go under Evidence as blocked, stated plainly, with the unblock step.
- No new frameworks, services or tickets appear in a summary unless the owner already approved them.
