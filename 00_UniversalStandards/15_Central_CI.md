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
        fixture-paths: bench/corpus
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
| `fixture-paths` | empty | Space-separated directories of frozen code not meant to build here (copies of other repos, test corpora). Every scanner scans them; build gates skip them (§6) |
| `exclude-paths` | empty | Space-separated directories hidden from every gate, scanners included, except secret scanning. Needs a reviewed reason; prefer `fixture-paths` (§6) |
| `run-tests` | `true` | Run each stack's tests (`npm test --if-present`, pytest, `go test`); tests block |
| `install-bubblewrap` | `false` | Install pinned bubblewrap before the TypeScript tests, for repos whose tests exercise a bubblewrap sandbox |
| `single-job` | `false` | Run every gate as steps of one job instead of one job per stack, for runner pools that start a fresh VM per job (§5) |

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

A `detect` step lists tracked files outside `exclude-paths`, and each stack's gates run only when
that stack is present. Fixture code counts: a stack found only under `fixture-paths` still starts
its job, so its scanners run, while its build steps report there is nothing to build.

| Job | Runs when | Checks |
| :--- | :--- | :--- |
| HCL | `*.tf` or `*.hcl` | `terraform fmt`, `terragrunt hcl fmt` (per file), TFLint (per directory), `terraform validate` per module, Checkov `SEC-*` (blocking) and the rest (counted) |
| TypeScript | `*.ts`, `*.tsx`, or `package.json` | `npm ci`, `tsc --noEmit`, tests, `npm audit` |
| Python | `*.py`, `pyproject.toml`, or `requirements*.txt` | Ruff, `compileall`, mypy (against the project's environment), Bandit, tests, `pip-audit` (of `requirements.txt`, else `pyproject.toml`) |
| Go | `*.go` or `go.mod` | `go vet`, `go build`, tests, `govulncheck` |
| Secrets | Always | Gitleaks (`SEC-010`) |
| Trivy | Always | `trivy fs`: vulnerabilities and misconfigurations |
| Semgrep | TypeScript or Python present | python, typescript, javascript, secrets, and security-audit rulesets |

### Job shape and runner pools

- **Each gate's script is written once.** Every multi-line step body lives in one named script in
  the workflow's `env` (`GATE_HCL_LINT`, `GATE_TRIVY`, …), and steps run it with
  `eval "$GATE_…"`. Both job shapes below run the same scripts and the same pinned actions, so
  neither can drift from the other.
- **Per-stack jobs (the default)** run the gates in parallel, one job per stack. This suits
  GitHub-hosted runners, where a job starts in seconds.
- **One job (`single-job: true`)** runs every gate as steps of a single job. This suits a pool that
  recycles a VM after every job, where each job pays a full recycle.
  - **Every gate still runs:** each step runs under `!cancelled()`, so a failed gate does not hide
    the rest, and any failed step fails the job.
  - **Ordering:** HCL runs before `setup-python`, so Checkov gets the runner's own `python3`.
  - **The cost is coupling.** The gates share one machine's `PATH` and `$RUNNER_TEMP`, so a gate
    must never depend on another gate's tools or files.
  - Callers on the private pool set it from the pool variable, e.g.
    `single-job: ${{ vars.PLAN_RUNS_ON != '' }}`.
- **Measured** on sovereign-vpc-gcp's one-VM plan pool, 2026-10-26:

  | Shape | First job to plan done | VM recycles |
  | :--- | :--- | :--- |
  | Per-stack jobs (#18) | 55 min, for about 6 min of work | 5 |
  | One job (#24) | 11.5 min (gates 5.6, recycle 3.6, plan 2.3) | 2 |

  A recycle is about 3.6 min: about 1.5 min for the instance group to recreate the VM, about 1 min
  to boot, and 68 s of startup script. The one-job shape costs nothing extra.
- **The next steps cost money**, and are taken only when the wait justifies them:
  - **A prebuilt runner image** (OS packages and the pinned runner baked in, no secrets, no
    registration) saves about 1 min per recycle, for cents a month of image storage.
  - **A second always-on plan VM** removes the wait when the queue is idle, for about $15 a month
    on demand (an estimate from list prices).

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
- **Scanners see fixture code; only build gates skip it.** Under `fixture-paths`:
  - **Skipped:** format, lint, validate, type checks, compile, and tests, because the code builds
    in its own repo.
  - **Still scanned:** Gitleaks, Trivy, Semgrep, Checkov, and Bandit.
  - **A real finding in fixture code blocks** like any other, and gets fixed or a reviewed
    exception. Example: a corpus copy of a firewall with a waived finding needs its own mirrored
    exception, with the same owner and expiry.
- **`exclude-paths` hides code from every gate except secret scanning,** so it needs a reviewed
  reason in the caller. Gitleaks ignores it: a secret committed into a frozen corpus is still a
  leaked secret.
- **Every job is bounded.** Each factory job sets `timeout-minutes` at 3 to 5 times its longest
  measured run, and the single job is bounded at 45 minutes. A hung tool fails the gate in minutes,
  not after GitHub's 6-hour default.
- **A timeout does not bound the queue.** `timeout-minutes` starts when a job starts. A job waiting
  for a runner can stay queued for up to 24 hours. Queued-job age therefore needs its own alert
  (AGENTS.md → Observability: the platform instruments itself).
  - **Status: gap.** No queue alert exists yet. It is deferred until the repositories are public,
    when the scheduled check runs on free GitHub-hosted minutes.
- **A presence check must not read "nothing" by mistake.** Never test for files with
  `cmd | grep -q .` under `set -o pipefail`. When `grep` exits early, it can kill `cmd` with
  SIGPIPE, and the failed pipeline reads as "no files", which silently skips the gate. Use a
  command substitution instead: `[ -z "$(cmd)" ]`.

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
  - **Status: gap.** No platform repository has branch protection today, so the code-owner review
    is not enforced (`docs/incidents/2026-10-26-INC-001-no-branch-protection.md`).
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
