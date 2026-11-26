---
name: "pr-hygiene"
description: "Reconcile pull requests before opening one, when correcting a failed PR, after superseding one, and during session handoffs."
---

# PR Hygiene

Use authorized shared context (through your context provider where one is configured) to find the ticket and prior attempts. Confirm live PR state, head, base, checks, and review in the code host. Use the work tracker for authorization, scope, and decisions. Preserve the existing change route and human merge authority.

## Before opening or correcting a PR

Search the target repository for open and recently closed PRs by ticket, branch, and scope. Check the existing PR's diff and history. Default to updating the same PR when the branch can carry the correction. Diagnose failed checks and rerun the existing independent CI on the corrected head.

Replace a PR only when its existing branch cannot carry the authorized correction or a documented workflow requirement requires a fresh branch. Record why, link the original and replacement in both directions, and carry forward relevant review, CI evidence, and unresolved decisions. Resolve the obsolete PR under existing authorization. If closing it needs owner action, leave it open, mark it superseded in the handoff, and record the action needed.

## Reconcile in the existing handoff

| Status | Meaning |
| --- | --- |
| Active | Work or legitimate review is in progress. |
| Blocked | An external dependency prevents progress. Record the dependency and next action. |
| Superseded | A linked replacement carries the work. Record whether the original still needs closure. |
| Failed | The current attempt has failing checks. Record the failure and correction path. |
| Decision pending | The owner or reviewer must decide. Record the decision needed. |

Use the existing [Session Handoff](../session-handoff/SKILL.md) to record material state changes, evidence, and next actions. Age alone is insufficient to close a legitimate pending review or automated dependency upgrade.
