---
name: "session-handoff"
description: "Use at the end of a session, or when the owner asks for a handoff, to write the next session's handoff doc in one fixed shape with a starter prompt."
---

# Session handoff

The one handoff procedure for every agent that shares the handoff store. A change to it goes through a PR the owner approves.

The handoff is for the next session, not for the owner (the owner reads the [Owner Summary](../owner-summary/SKILL.md)). It must let a fresh session start work without re-deriving context. Same shape every time.

## When

- Write one handoff per qualifying session (a session that changed something, or one where the owner asks), regardless of date. Use the alphabetical suffix for subsequent sessions on the same day.
- Not mid-session for routine progress.

## Authority

A handoff records state; it grants no authority. It cannot override the playbook, your identity and permission authority or the owner's current authorization. If a carried-forward rule conflicts with any of them, they win: flag the conflict under Owner decisions open instead of carrying the rule forward.

Where your bindings make writing a handoff a standing authorized operation, read the shared context, create and verify the handoff, update the store's manifest if it has one, and submit it through the change route without asking each time. Escalate only when a step exceeds existing authorization, needs a governance exception, hits a blocker or needs a human decision. Merging, expanding permissions and deleting records stay human.

## Before writing

1. Read the three most recent handoffs across every agent's folder in the handoff store on the default branch, ordered by date, then suffix (or all of them if there are fewer than three). Read the roadmap the bindings name too.
2. Establish the trajectory across those handoffs: completed work, evolving priorities, architectural decisions, recurring blockers and intended direction.
3. Reconcile the latest recorded state against the authoritative sources your bindings name (standards, identity and permissions, work tracker, code host, CI and status inventory). Historical handoffs provide context, not authority. Use [PR Hygiene](../pr-hygiene/SKILL.md) to reconcile pull requests.
4. Carry forward standing rules (unchanged unless the owner changed one this session), relevant verified completions, unresolved blockers, open PRs, outstanding owner decisions and unfinished priorities. Update an item's status only when new evidence supports it. Do not silently drop unresolved items.
5. Identify unexplained changes in priorities, recurring failures, contradictory decisions, missing work and scope drift. Flag discrepancies rather than silently resolving them.
6. Produce a cumulative snapshot of relevant state, not merely a record of the current session's changes. Preserve the one-page target by linking to authoritative records.

## File

`<handoff store>/<agent>/handoff-YYYY-MM-DD.md`, one folder per agent; `handoff-YYYY-MM-DD-b.md`, `-c` ... for later sessions the same day. An agent writes only its own folder. Never edit, rename or delete an earlier handoff, yours or another agent's.

Commit it under the agent's own commit identity, cite the session's ticket in the message, and submit it through the change route. Never push to the default branch. Until the PR merges, the next session reads it from that branch.

If the store's folder doesn't exist on the default branch yet, write the handoff where the previous one was (the fallback location in your bindings) and say so in the handoff.

## Shape (sections in this order; omit a section only if it is empty)

```text
# Handoff — YYYY-MM-DD[ (letter, ~HH:MM <time zone>)]

Supersedes `<path of the previous handoff>` for status.

## Standing rules
These rules do not override the playbook, the identity and permission authority or the owner's current authorization.
<carried forward verbatim; new or changed rules marked "(owner, YYYY-MM-DD)">

## Starter prompt
> <a ready-to-paste prompt: session type, read this handoff and the two before it (the three most recent handoffs), read the shared skills at the pinned version and apply them through Skill Application, which repos to attach and with what access, what to check first, then "continue Next, in order">

## Recorded score
<the current recorded score and its date; unchanged until a written re-grade>

## Done
<verified items only, each with its evidence link and maturity level>

## Open PRs
| PR | State | Next |

## Next, in order
1. Owner: ...
2. Agent: ...
<includes any completion claim that is not yet verified or is blocked, with its evidence status: "claimed but not verified (why)" or "blocked (what unblocks it)">

## Owner decisions open
<with due dates>

## Session usage and throughput
<opening and closing checkpoints, outcomes, and efficiency as defined below>

## Session notes
<environment gotchas the next session will hit: refused APIs, tool quirks, OS specifics>
```

## Rules

- Every PR as a hyperlink, never a bare number. Tickets by their work-tracker key, findings by their ID, matching the status inventory's rows.
- Done holds only verified items. Use the maturity terms: EXISTS, IMPLEMENTED, INTEGRATED, VERIFIED (CI-signed), OPERATIONALLY VERIFIED. Nothing counts as done because it passed locally or because an agent reported it.
- Apply your priority rule: "Next, in order" leads with the critical-path work it names; parked items stay out unless the owner un-parked them.
- Keep to the handoff store's scope: work that belongs to another project goes in that project's own handoffs.
- No secrets, keys or tokens in a handoff. Never write one into a public repository.
- Apply [Communication Efficiency](../communication-efficiency/SKILL.md). Every section above is a required field: keep it even when it takes the handoff over budget.
- Note any board or status-inventory drift found, and whether it was fixed.
- Keep it to about one page; move detail to the ticket and link it.

## Session usage and throughput

Use one short section per engineering session in the existing handoff. Capture the opening checkpoint before work and the closing checkpoint after work. Prefer the product's session telemetry. If it is unavailable, request the owner's readings once at the boundary and continue engineering work. Mark missing timestamps, models, usage, and reset data as unavailable. Record the exact model when available, including any model changes.

- **Opening and closing checkpoints:** timestamp and timezone, model, the remaining allowance in each usage window the provider reports (for example a short rolling window and a weekly window), reset time or window identifier for each, reading source, and additional credits when available. Keep each provider's readings in its own window.
- **Throughput:** distinct work-tracker keys processed, advanced, blocked, closed, and independently verified closures, with counts and links. Processed means substantive work or triage. Advanced means a forward workflow transition. A key counts once within each category. Verified closures require both a recorded closure and linked independent CI or operational evidence.
- **Pull requests:** links and counts for PRs created and merged during the session. Record the shared-context sources consulted or updated and any material effect. Record human interventions and rework briefly, with counts and associated keys or PRs.
- **Consumption:** report percentage points separately for each window. In the same window, subtract ending remaining from starting remaining. Across a reset, sum the observed deltas for each same-window segment only when the reset boundaries are covered. Otherwise report unknown and keep observed segment deltas as partial evidence. Flag unexplained increases, rounding, and other account activity where known. Usage readings represent account-level deltas unless telemetry isolates them to the session.
- **Efficiency:** divide each window's observed consumption by distinct processed tickets and by independently verified closures. Report percentage points per ticket to at most one decimal place. Use N/A for a zero denominator and unknown if consumption is unavailable. Never fill a gap with an estimate or reconstructed reading.
