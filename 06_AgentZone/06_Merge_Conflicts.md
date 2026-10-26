# Merge Conflicts

*A tool finds the conflict, the Builder resolves it, the Reviewer checks that nothing was lost, and a
person approves the merge.*

**Status: design.** This is the agreed target; it is not implemented yet. Today a person resolves
conflicts, or asks a coding agent to, and the result goes through the normal gates and review.

A pull request conflicts with `main` when another change merged first and touched the same lines. The
work is split by the platform's actor and tool rule (`01_Agent_Standards.md` §1a): detecting a
conflict is a deterministic tool's job, resolving it means writing a commit, which is the Builder's
job, and judging the resolution is the Reviewer's. The Reviewer never writes the resolution. The
contract is `schemas/merge_conflict.v1.schema.json`.

---

## 1️⃣ The Flow

| Step | Who | What happens |
| :--- | :--- | :--- |
| **1. Detect** | rig (tool) | `git merge-tree --write-tree` against the base branch finds the conflicts without touching any branch. rig writes a `merge_conflict.v1` report: every conflicted file and hunk, the base, ours and theirs lines, the commits on each side, and the route for each hunk |
| **2. Route** | Code, from the report | Each hunk's `route` decides who resolves it (§2). Routing is decided by rules, never by a model |
| **3. Resolve** | The Builder | A `rule` hunk is resolved deterministically; a `model` hunk goes to the Builder's model, which proposes a resolution with its reasoning. A `person` hunk stops the Builder |
| **4. Commit** | The Builder | The resolution is a merge commit on the pull request's branch: never a rebase, never a force-push, so the history a reviewer saw stays intact |
| **5. Gate** | The central CI | The merge commit runs the same gates as any other commit (`00_UniversalStandards/15_Central_CI.md`) |
| **6. Review** | The Reviewer, merge-resolution lens | Checks that nothing either side added was dropped, and flags semantic collisions (§3). Advisory, like every lens |
| **7. Merge** | A person | Approves the merge through branch protection, as for every change |

## 2️⃣ Routing

| Route | When | Resolved by |
| :--- | :--- | :--- |
| `rule` | The hunk is **mechanical**: both sides only added lines where the base had none (`disjoint_additions`), as when two changes each add a row to the same table or a key to the same block | Keep both sides, ours then theirs, with no model. The result must contain every added line |
| `model` | The hunk is **semantic**: both sides changed the same line, one side deleted what the other changed, or a rename collides | The Builder's model, at the ladder rung the change's difficulty selects |
| `person` | The file is in a **protected path** (IAM, state, governance, the CI factory itself), the conflict is binary, or the Builder gave up within its budget | A person, with the report attached. Protected paths never get an automatic resolution, mechanical or not |

- **Classification fails closed.** rig marks a hunk mechanical only when it can prove the base side is
  empty and both sides added lines. Anything it cannot classify is semantic. Whether a file is
  protected is decided by rules on its path; if the protected patterns cannot be read, every file
  counts as protected.
- **Mechanical is not the same as safe.** A protected file goes to a person even when its hunk is a
  plain pair of additions. The contract's example is a real case: sovereign-vpc-gcp#17 and #14 each
  added pinned versions to the same `env` block of the CI factory's `gates.yml`. Disjoint additions,
  so the rule would keep both, but the file is the CI factory, so a person decides.
- **One resolver at a time.** A branch has at most one resolution in progress. A second agent, or a
  person, waits for it or cancels it; two resolvers pushing to the same branch race and lose work.
- **Budgets are the Builder's.** Resolution attempts count against the Builder's loop budget
  (`01_Agent_Standards.md` §7); a stalled or oscillating resolution escalates like a stalled review
  round.

## 3️⃣ The Merge-Resolution Lens

The Reviewer reads the `merge_conflict.v1` report and the merge commit, and asks two questions:

1. **Was anything dropped?** Every line that ours or theirs added in a conflicted hunk is either present
   in the resolved file or listed as deliberately removed in the resolution's message, with a reason.
   A line missing without a reason is a finding.
2. **Is there a semantic collision the text merge cannot see?** Both sides setting the same key to
   different values, a renamed function still called by its old name, two migrations with the same
   number, a duplicated table row. These are findings even where git reported no conflict.

The first question is mechanical and runs as code before the model, from the report; only the second
needs judgment. Findings follow the lens rules (`04_Review_Lenses.md`): advisory, never blocking by
themselves. A dropped line or a protected-path change escalates to a person.

## 4️⃣ Rules

- Detection and routing are deterministic; a model sees a conflict only after rig has classified it.
- The resolution is always a merge commit. Rewriting a branch someone may have reviewed is never the
  fix for a conflict.
- Every resolution goes through the gates and the human merge like any other commit. An agent outside
  the platform (a coding assistant asked to resolve conflicts) is held to the same rules: it may
  propose, and its push is reviewed and gated like the Builder's.
- Every resolution leaves evidence: the report, the merge commit, and the lens findings, linked from the
  pull request.

---

## Principle

Let a tool find the conflict, rules route it, the Builder resolve it, the Reviewer prove nothing was
lost, and a person decide the merge.
