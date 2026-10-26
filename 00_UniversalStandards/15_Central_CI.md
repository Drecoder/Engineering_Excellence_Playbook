# Central CI

*One factory, called by SHA, configured through inputs.*

Every repository on the platform runs the same deterministic gates. They live once, in one reusable
workflow; a repository calls it and says only what is different about itself. A gate that lives in
two places drifts, and a fix made in one repo is a workaround everywhere else. Security rules for
the workflow itself (permissions, access scope, secrets) are in `07_Security_In_Depth.md` §5; pins
are in `13_Supply_Chain.md`.

---

## 1️⃣ One Factory

- **The gates live in one reusable workflow:** `.github/workflows/gates.yml` in
  `Drecoder/sovereign-vpc-gcp`. It is the only place build, lint, type, test, and scan logic is
  written.
- **A consumer has one caller file** that triggers on pull requests and does nothing but call the
  factory and pass inputs:

  ```yaml
  jobs:
    gates:
      uses: Drecoder/sovereign-vpc-gcp/.github/workflows/gates.yml@<full commit SHA>
      with:
        exclude-paths: bench/corpus
  ```

- **No per-repo or per-module CI,** no copied setup steps, and no caller-local actions. A local
  action (`uses: ./.github/actions/...`) inside a reusable workflow resolves against the *caller's*
  checkout, where it does not exist, so it fails in every consumer.
- **Failures are fixed in the factory,** not worked around in the caller: missing setup, lint scope,
  frozen fixtures, audits, and pins are all central changes.
- Workflows that are not gates are allowed per repo when they do something only that repo needs,
  such as the playbook's rule sync (`05_Standards_Distribution.md`) or the anti-pattern catalog's
  re-verification (`11_Anti_Pattern_Catalog.md`). They never repeat a gate.

## 2️⃣ Self-Contained

- No step reads a path from the caller's checkout except the code under test and the caller's own
  configuration files (`.tflint.hcl`, `mypy.ini`, `tsconfig.json`, `package.json`, …).
- The factory installs its own toolchain: tools at exact versions, downloaded binaries verified
  against pinned SHA-256 sums.
- Gate tools and the project's dependencies live in **separate environments**, so a dependency scan
  audits the project and never the gate's own tools, and the type checker sees the project's
  packages.
- A caller without an optional file (no `.tflint.hcl`, no `modules/`, no `*.hcl`) gets the tool's
  defaults rather than a failure.

## 3️⃣ Inputs Are a Contract

The inputs are the factory's interface. Like an exported type (`02_BackendZone/01_API_Architecture.md`),
an input is never renamed, removed, or given a new meaning without updating every caller in the
same change.

| Input | Default | Meaning |
| :--- | :--- | :--- |
| `runs-on` | `"ubuntu-latest"` | JSON `runs-on` value, e.g. a self-hosted runner label |
| `exclude-paths` | empty | Space-separated directories holding frozen corpora or fixtures; skipped by every gate except secret scanning (§6) |
| `run-tests` | `true` | Run each stack's tests (`npm test --if-present`, pytest, `go test`); tests block |

A caller that needs something the inputs cannot express asks for a new input in the factory; it
does not add a step of its own.

## 4️⃣ Pinning

- **Callers pin the factory to a full commit SHA,** never a tag or a branch. A tag can move; a
  branch always does. Repinning is a reviewed pull request in the caller.
- The SHA must stay reachable from the factory's `main`. A caller pinned to a pull request's head
  stays valid only if that pull request is merged with a merge commit; after a squash merge, every
  caller is repinned to the merge commit.
- Inside the factory, third-party actions are pinned to commit SHAs and tools to exact versions
  (`13_Supply_Chain.md`).
- Agent instruction files (`.github/copilot-instructions.md`, `CLAUDE.md`, …) state the same rule
  in the same words: full commit SHA, never a tag or a branch.
- **Status: gap.** Jobs run on the `ubuntu-latest` runner image, not in a container pinned by digest,
  and Node, Python, and Go are pinned to a minor version, not an exact one. Both fall short of
  `12_Containers.md`; moving the jobs into the pinned toolchain image closes it.

## 5️⃣ What Runs

A `detect` job lists tracked files outside `exclude-paths`, and each stack's job runs only when
that stack is present.

| Job | Runs when | Checks |
| :--- | :--- | :--- |
| HCL | `*.tf` or `*.hcl` | `terraform fmt`, `terragrunt hcl fmt` (per file), TFLint (per directory), `terraform validate` per module, Checkov `SEC-*` (blocking) and the rest (counted) |
| TypeScript | `*.ts`, `*.tsx`, or `package.json` | `npm ci`, `tsc --noEmit`, tests, `npm audit` |
| Python | `*.py`, `pyproject.toml`, or `requirements*.txt` | Ruff, `compileall`, mypy (against the project's environment), Bandit, tests, `pip-audit` (of `requirements.txt`, else `pyproject.toml`) |
| Go | `*.go` or `go.mod` | `go vet`, `go build`, tests, `govulncheck` |
| Secrets | Always | Gitleaks (`SEC-010`) |
| Trivy | Always | `trivy fs`: vulnerabilities and misconfigurations |
| Semgrep | TypeScript or Python present | python, typescript, javascript, secrets, and security-audit rulesets |

## 6️⃣ Thresholds and Failure Behavior

- Pass/fail checks (format, lint, type check, compile, validate, tests) and `SEC-*` always block.
- **Vulnerability scanners share one severity gate.** Trivy, `npm audit`, `pip-audit`, and
  `govulncheck` write a full report; one script in the factory reads it and blocks only on
  **CRITICAL** severity or any alias on the **CISA KEV** list. Where a scanner reports no severity,
  or reports advisory IDs that KEV does not use, the gate looks the ID up in OSV for its aliases and
  GitHub advisory severity. Everything below the line is counted, never shown in the pull request.
  The full table is `07_Security_In_Depth.md` → Gate thresholds.
- `govulncheck` counts only vulnerabilities in code the module actually calls, then applies the same
  CRITICAL-or-KEV line.
- **The gate fails closed:** a scanner error, an empty or truncated report, or an unreachable OSV or
  KEV feed fails the check. A finding the gate could not classify never passes as clean.
- **Exclusions skip frozen code, never secrets.** `exclude-paths` applies to detection, format,
  lint, validate, Checkov, type checks, Trivy, Semgrep, Bandit, tests, and dependency discovery.
  Gitleaks ignores it: a secret committed into a frozen corpus is still a leaked secret.

## 7️⃣ Changing the Factory

1. Change `gates.yml` in a pull request on the factory repo. Its own run covers the stacks the
   factory repo has.
2. In each consumer, open a pull request that repins to the new head SHA. **That run is the real
   test** of the change for that consumer's stacks; a finding it surfaces in the consumer's code is
   fixed in that same repin pull request.
3. Merge the factory change (merge commit), then the repins. Open pull requests that still call an
   older pin pick up the change when they are updated from `main`.
4. A change that adds a blocking check lists, in its description, which consumers it is expected
   to turn red and why, from a dry run.
5. **Stacked factory changes run no gates** until they target `main`. Retarget a stacked pull
   request to `main` *before* its base branch is deleted: GitHub retargets automatically only when
   the base is deleted by the merge itself, and a manual delete closes the stacked pull request
   (sovereign-vpc-gcp INC-005).

## 8️⃣ Who Can Call It

- The factory repo's Actions access is set to the owning user or organization, never public
  (`07_Security_In_Depth.md` §5).
- **GitHub does not let a public repository call a reusable workflow in a private one.** A public
  consumer (today: Genesis) cannot use the factory until the two visibilities line up.
- **Status: open decision.** Either move the factory to a dedicated, public repo that holds only
  shared workflows (the option `07_Security_In_Depth.md` prefers, since it exposes nothing else), or
  make the public consumers private.

## 9️⃣ Policy-Driven Gates

**Status: design.** The contracts below are agreed; the factory does not read them yet. Today the
checks and their thresholds are written into `gates.yml` (§5, §6).

The factory becomes an engine that reads the CI policy as data and computes the gates for each
change, instead of a workflow with the checks written into it.

| Contract | Owned by | Holds |
| :--- | :--- | :--- |
| `schemas/ci_policy.v1.json` (schema `ci_policy.v1.schema.json`) | The playbook | Every check: tool and exact pin, category, when it applies, scope, what blocks, whether exclusions and exceptions apply, and the `SEC-*` policies it enforces |
| `.ci/exceptions.v1.json` in each caller (schema `ci_exceptions.v1.schema.json`) | The caller, through reviewed pull requests | Need-based exceptions to blocking findings |
| `gate_plan.v1` (schema `gate_plan.v1.schema.json`) | Written by the factory per change | The checks run and why, the scope, and the exceptions applied or rejected |

- **Policy is data.** Adding a scanner, changing a pin, or moving a threshold is a reviewed change to
  `ci_policy.v1.json`. The schema itself rejects policies that weaken the playbook's thresholds:
  - pass/fail checks always block and can't be excepted;
  - dependency scanners block on CRITICAL or KEV over the whole repository;
  - secret scanning covers the whole repository, ignores `exclude-paths`, and can't be excepted;
  - every factory tool has an exact version;
  - the high-risk and fail-closed floors can't be turned off.
- **One gate plan per change.** Before any check runs, the engine reads the policy, the changed
  files and units, rig's `features.v1`, the plan JSON, and the caller's exceptions, then writes
  `gate_plan.v1`. The plan is evidence: a span, a log line with `trace_id`, and an object kept with
  the run, recording the policy version and its canonical-JSON digest.
- **Only the factory writes the plan.** A caller never supplies one. Checks run from the plan the
  factory just wrote, and a plan that is missing, or names a different head commit or factory pin
  than the run, fails the run.
- **One digest rule for every language:** SHA-256 over the policy's canonical JSON, meaning keys
  sorted at every level, no whitespace (`,` and `:` separators), and non-ASCII characters escaped as
  `\uXXXX`. File formatting and line endings never change the digest.
- **Scoped by need, with floors.**
  - Pass/fail checks may run only on the changed units.
  - Security categories (`SEC-*` policy, dependency vulnerabilities, misconfiguration, SAST,
    secrets) always scan the whole repository.
  - A high-risk change (IAM, state layout, `moved`, delete, replace, governance, or the CI factory
    itself), decided by code from the plan JSON and paths, runs everything at full scope.
- **Fails closed.** An unreadable policy or exceptions file, unavailable features or diff, or an
  unclassifiable risk puts the plan in `full` mode. Dynamic gates can add checks; they never drop
  one silently.
- **Exceptions exist only while the need does.**
  - **Raised only by a block:** an entry is added only after a check blocks on a specific finding.
  - **Narrow:** it names one check, one finding, one file and one resource, plus the issue or pull
    request that removes the need.
  - **Time-boxed:** it expires within `exceptions.max_days` (30). Renewal is a new pull request,
    never an edit in place.
  - **Validated:** the engine applies an entry only to the exact finding and resource it names. An
    expired, over-long, mismatched, or non-exceptable entry is rejected and recorded in the plan.
  - **Never excepted:** pass/fail checks and secret scanning. Active exceptions are a metric.
  - **No self-exemption:** in every caller, `.ci/exceptions.v1.json` belongs in CODEOWNERS to the
    platform team, not the caller's team, and branch protection requires a code-owner review.
    Each entry names its approver (`approved_by`), and the engine checks through the API that this
    login approved the `approved_in` pull request and is a code owner of the file.
  - **Excepting a finding is not weakening a rule.** No exception changes a threshold. An exception
    covers one known finding on one resource until it expires, and only in the categories the
    playbook already lets a reviewed exception cover (`SEC-*` policy, dependency vulnerabilities,
    misconfiguration, SAST).
- **Callers don't change.** The engine keeps the factory's inputs (§3) and is still called by full
  commit SHA. The contracts have one home, the playbook's `schemas/`, and reach the factory
  vendored byte-identical as `.playbook/schemas/`, like every playbook contract.
- **Reference behavior** for what a schema cannot express (exception eligibility, exact-resource
  matching, plan provenance, the digest) is `tests/contracts/ci_reference.py`. Every engine
  implementation must agree with it on the contract tests' vectors.

---

## Principle

Write each gate once, call it by SHA, change it only through inputs, and fix every CI failure where
the gate lives.
