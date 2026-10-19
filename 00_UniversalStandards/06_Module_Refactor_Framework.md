# Module Refactor Framework

*How to sequence a module refactor safely and what to test at each stage — for Terraform /
Terragrunt modules and TypeScript modules alike.*

---

## Core Principle: The Isolation Rule

> **Each step changes either structure or behavior, never both.** Every intermediate step leaves
> the system fully deployable, so you can pause or roll back at any point.

This is the long form of the structural-vs-behavioral rule in `CLAUDE.md`.

---

## Stage 0: Baseline & Freeze the Contract

**Do**

1. Document the public surface:
   - **Terraform / Terragrunt:** `variables.tf`, `outputs.tf`, provider requirements, and resource
     addresses that callers or other units depend on.
   - **TypeScript:** exported types and functions, and emitted OTel span / metric names and
     attributes.
2. Snapshot current behavior with characterization tests (pin today's behavior, bugs included).
3. Tag the commit: `git tag pre-refactor/<module>`.

**Test — this becomes the oracle for every later stage**

```bash
terragrunt run-all plan -out=baseline.tfplan
terragrunt run-all show -json baseline.tfplan > baseline.plan.json
```

```ts
it("routes high-variance diff to TIER_2", () => {
  expect(route(fixtures.multiFileDiff)).toMatchSnapshot();
});
```

- Contract tests validate JSON schemas against recorded real payloads.
- Record span and metric names — dashboards break silently when they are renamed.

**Exit gate:** characterization tests pass; baseline artifacts stored.

---

## Stage 1: Create Seams (No Behavior Change)

**Do**

- Insert an interface or adapter between the module and its callers — an injected interface in
  TypeScript, a wrapper module or `locals` input-isolation block in HCL.
- Add unit tests covering the exact paths you are about to isolate.

**Test**

- All Stage 0 tests pass unchanged.
- `terragrunt plan` shows **zero diff**.
- `tsc --noEmit` passes with no new `any` or casts at the seam.

**Exit gate:** zero plan diff; identical snapshots.

---

## Stage 2: Expand (Build the New Path Next to the Old)

**Do**

- Implement the new version behind the seam; the old path stays the default
  (e.g. `modules/vpc/v2` alongside `v1`, or a handler behind `ROUTER_IMPL=v2`).

**Test**

- Unit tests for the new path in isolation.
- **Differential tests:** run a corpus through both paths and assert parity.

  ```ts
  for (const f of corpus) {
    expect(v2.route(f)).toEqual(v1.route(f));
  }
  ```

- Point a scratch stack at `v2` and compare its plan to `baseline.plan.json`: the resource set
  and attributes must match; only addresses may differ.
- `tflint` and `checkov -d modules/<module>/v2`.

**Exit gate:** differential suite green, or every variance documented and approved.

---

## Stage 3: Migrate Callers (One at a Time)

**Do**

- Migrate in batches ordered by blast radius: **sandbox → dev → staging → prod**.
- Preserve state; never destroy and recreate.
- **One PR per caller or environment**, each individually revertible.

**State moves — pick the right tool**

| Situation | Tool |
| :--- | :--- |
| Address changes **within one state** (same Terragrunt unit) | `moved {}` block |
| Resource moves **between states** (different Terragrunt units) | `removed {}` (with `lifecycle { destroy = false }`) in the old unit + `import {}` in the new unit |

`moved` blocks cannot cross state files. In Terragrunt every unit has its own state, so moving a
resource between units always needs the remove/import pair — plan both units in the same PR.

**Test (per PR)**

- Hard CI gate: no `delete` actions (this also catches replacements, which include `delete`):

  ```bash
  jq -e '[.resource_changes[] | select(.change.actions | index("delete"))] | length == 0' plan.json
  ```

- Integration or smoke tests against the migrated environment.
- Telemetry: expected spans emitted; latency and error rate within baseline.

**Exit gate:** all callers migrated. For TypeScript, live telemetry proves the old path receives
zero traffic; for IaC, no unit references the old module version.

---

## Stage 4: Contract (Delete the Old Path)

**Do**

- Remove the `v1` code, flags, and obsolete adapters.
- Keep `moved {}` blocks for at least one release cycle before removing them.

**Test**

- Full suite, including Stage 0 characterization tests (update snapshots only for approved
  behavior changes).
- `terragrunt plan` shows **zero changes** in every environment.
- Dead-code detection (`knip` / `ts-prune`, plus a grep for retired flag names).

**Exit gate:** legacy path removed; no drift in any environment.

---

## Stage 5: Fix Bugs & Change Behavior

- Behavioral fixes found during the refactor (the bugs the characterization tests pinned) ship
  as **separate PRs**.
- Each fix starts with a test that fails before the fix.

---

## Test Matrix

| Stage | Unit | Differential | Plan zero-diff | No delete / replace | `tflint` / `checkov` | Integration | Telemetry |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **0 Baseline** | ✅ | — | Record | — | ✅ | ✅ | Record |
| **1 Seams** | ✅ | — | ✅ | ✅ | ✅ | — | — |
| **2 Expand** | ✅ | ✅ | Scratch stack | ✅ | ✅ | — | — |
| **3 Migrate** | ✅ | — | Per env | ✅ | ✅ | ✅ | ✅ |
| **4 Contract** | ✅ | — | ✅ | ✅ | ✅ | ✅ | ✅ |
| **5 Fix** | ✅ new failing test | — | Expected diff only | Reviewed | ✅ | ✅ | ✅ |

---

## Agent Loop Guardrails

These apply when the Builder / Reviewer agents perform a refactor (see
`06_AgentZone/01_Agent_Standards.md`).

1. **One PR = one stage step.** A diff mixing structural and behavioral changes is rejected.
2. **Risk routing:**
   - Zero-diff steps (Stages 1 and 4) → **TIER_0** deterministic checks.
   - State-touching steps (Stage 3 `moved` / `removed` / `import`) → **TIER_2**, always.
3. **Remediation cap:** the Builder fixes deterministic findings (no-delete gate, scanners) in its
   own bounded loop before opening a PR. PR review rounds follow the change-loop rules in the
   agent standards: they end at no blocking findings, round 3, or a stalled round, then escalate
   to a human. The loop never "fixes" a plan by accepting a replacement.
4. **Human approval:** every refactor PR that reaches staging or prod is approved by a human.

---

## Rollback

| When | How |
| :--- | :--- |
| **Before Stage 4** | Revert the caller's PR — the old path still exists. |
| **After Stage 4** | Revert to `pre-refactor/<module>` and add `moved {}` blocks in the reverse direction (or the reverse `removed` / `import` pair across units). Follow `04_OperationalRunbooks/01_Emergency_Rollbacks.md`. |

---

## Principle

A refactor is a sequence of boring, reversible steps. If a step is exciting, it is two steps.
