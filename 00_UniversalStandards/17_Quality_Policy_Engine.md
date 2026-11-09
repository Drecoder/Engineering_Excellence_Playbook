# Quality Policy Engine

*Standard tools measure the code; one small, pure program decides. The same evidence always gets
the same answer: PASS, BLOCK or QUARANTINE.*

Coverage, complexity, mutation and dependency scans each produce a number. This standard says how
those numbers become one decision on a pull request: which tools produce them, how they are
normalized, what they are compared against, and which result wins. The decision is made by the
**Policy Engine** (version 2.2, MVP scope), a stateless Python program with no network, database or
model calls.

**Status: specified.** The contracts, the playbook's policy, a reference engine and its conformance
vectors exist and are tested (`tests/contracts/test_policy_engine_contracts.py`). The normalizers,
the engine service and its wiring into the central gate are still to be built. Until then
`.ci/quality.v1.json` floors (`14_Test_Quality.md`) are the only quality gate that runs.

---

## 1️⃣ Four Parts, Kept Apart

| Part | Does | Must not |
| :--- | :--- | :--- |
| **Builder** | Writes the change and its tests | Measure its own change, or see the decision before the gate does |
| **Evaluator** | Runs the pinned tools in the toolchain image and normalizes their outputs into `quality_metrics.v1` (§2, §3) | Decide anything, or drop a changed path without an exclusion reason |
| **Policy Engine** | Reads the request, the policy and two metrics files; writes `policy_decision.v1` (§5, §6) | Reach the network, a database, a model, the clock or git; read raw tool output |
| **Authorization** | GitHub branch protection and the person's code-owner review; the compliance authority for releases | Merge on the engine's PASS alone: PASS only clears this gate |

The parts meet only through files named by SHA-256. The MVP deliberately leaves out a custom call-graph
reachability engine, a REST quarantine service, a custom signature ledger and automated
remediation loops; standard git, standard scanners and protected branches cover those needs.

## 2️⃣ Toolchain Manifest

Every tool runs in the pinned toolchain image (`12_Containers.md`); a result from host-installed
tools is refused (`quality_metrics.v1` requires the image digest).

| Language | Complexity | Coverage | Mutation | Dependencies | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| TypeScript / JavaScript | ESLint `complexity` rule, set to report every function | istanbul (Jest or c8) `coverage-final.json` | StrykerJS | `npm audit --json` | To build |
| Python | Radon `cc --json` | coverage.py `json` | mutmut | `pip-audit --format json` | To build |
| Go | `gocyclo` | `go test -coverprofile` | `go-mutesting` | `govulncheck -json` | Contracts only; built when a factory repository uses Go |

- **`crap-score` is a developer report, not evidence.** It is in the TypeScript image so people can
  see scores locally; the engine never reads a tool's CRAP score and recomputes every score from
  raw counts (§5).
- **Severity comes from the shared severity gate.** `pip-audit` and `govulncheck` report no
  severity of their own; the normalizer takes it from the gate's OSV mapping (`07_Security_In_Depth.md`),
  and a vulnerability still without one is `unknown`, which blocks when new. The KEV flag comes from
  a pinned catalog snapshot listed in `sources`.
- **Go's mutation tool is moving.** The maintained `go-mutesting` fork is being superseded by a new
  project; choose and pin one when the Go normalizer is built.

## 3️⃣ Normalized Evidence

A normalizer turns one language's raw outputs at one commit into `quality_metrics.v1`
(`schemas/quality_metrics.v1.schema.json`):

- **A module is a source file; a function is named by its qualified name** within the module
  (`Class.method`, `outer.inner`). Anonymous functions are `<anonymous>@<container>#<ordinal>`; an
  ordinal is not stable, so a moved anonymous function is treated as new and must meet the
  new-function limits.
- **Counts, never ratios.** Each function carries its complexity, instrumented lines and lines hit;
  each module its killed, timed-out, survived and uncovered mutants. The engine computes every
  ratio itself, exactly.
- **Nothing changed goes unaccounted.** Every changed path is either a measured module or listed in
  `excluded` with a reason (`not_source`, `test`, `generated`, `vendored`, `deleted`).
- **Every raw output is listed by digest** in `sources`, so the normalized numbers can be traced and
  recomputed.

## 4️⃣ The Baseline

The baseline is `quality_metrics.v1` for the pull request's **merge base**, measured in the same
toolchain image with the same tool versions.

- **Immutable by construction.** It describes a commit that was already reviewed and merged, so a
  pull request cannot edit it. The gate may reuse the main branch's stored metrics for that exact
  commit; otherwise it measures the merge base itself. Mutation runs at the merge base only for the
  modules the change touches.
- **Bound by digest, not by signature.** The request (`policy_evaluation_request.v1`) names the
  candidate, the baseline and the policy by SHA-256; the engine refuses any mismatch (QP-002), a
  baseline from another commit (QP-003) and one measured in another toolchain (QP-006).
- **Anti-laundering.** Every module that is not new must have a baseline record, and a changed
  module must have baseline mutation counts. A missing baseline blocks (QP-004); it never passes as
  "nothing to compare".

## 5️⃣ What Is Measured

For a function *f* with complexity *CC(f)* and coverage *Cov(f)* = lines hit ÷ lines instrumented:

$$CRAP(f) = CC(f)^2 \cdot (1 - Cov(f))^3 + CC(f)$$

A module's **mutation score** is (killed + timed out) ÷ (killed + timed out + survived + uncovered);
a module with no mutants has no score. Compile and runtime errors are not mutants.

Every function in the candidate is one of three kinds, from the change's diff hunks:

| Kind | Means |
| :--- | :--- |
| **New** | Its name is not in the baseline module (or the module is new) |
| **Changed** | It exists in the baseline and a changed line falls inside it |
| **Unchanged** | It exists in the baseline and no changed line falls inside it |

All values are compared exactly (fractions), never after rounding: a CRAP of 15.00006 is above 15.
Values are rounded to 4 decimal places, half-even, only in the output.

## 6️⃣ The Rules

The thresholds and rule set are `schemas/quality_policy.v1.json`, version 2.2.0. Changing a
threshold is a new `policy_version` through a reviewed pull request.

| Stage | Rule | Checks | Decision |
| :--- | :--- | :--- | :--- |
| Evidence | QP-001 | Request, policy, candidate and baseline validate; the policy's rule set is the engine's | BLOCK, stops |
| Evidence | QP-002 | File digests and the policy version match the request | BLOCK, stops |
| Evidence | QP-003 | Candidate is the request's commit; baseline is its merge base, same language | BLOCK, stops |
| Evidence | QP-004 | Every module that is not new has a baseline; changed modules have baseline mutation counts | BLOCK |
| Evidence | QP-005 | Every changed path is measured or excluded; each module's evidence is complete and consistent | BLOCK |
| Evidence | QP-006 | Candidate and baseline used the same toolchain image and tool versions | BLOCK, stops |
| Red | QP-010 | No critical vulnerability and none on the CISA KEV list | QUARANTINE |
| Red | QP-011 | No new or changed function has CRAP > 30 | QUARANTINE |
| Red | QP-012 | No new or changed function has complexity > 20 | QUARANTINE |
| Red | QP-013 | Mutation score not below 50% (new module, or a score that falls below 50% in this change) | QUARANTINE |
| Ratchet | QP-020 | No existing function's CRAP rises above its baseline | BLOCK |
| Ratchet | QP-021 | No module's mutation score falls below its baseline | BLOCK |
| Ratchet | QP-022 | A module's complexity, summed over its existing functions, does not rise | BLOCK |
| Ratchet | QP-023 | A module's line coverage, over its existing functions, does not fall | BLOCK |
| Ratchet | QP-024 | No new vulnerability of moderate, high or unknown severity | BLOCK |
| Ratchet | QP-025 | Every new function has CRAP ≤ 15 | BLOCK |
| Ratchet | QP-026 | Every new function has coverage ≥ 80% | BLOCK |
| Yellow | QP-030 | No changed function has CRAP > 15 | BLOCK |
| Yellow | QP-031 | Mutation score at least 80% (new module, or a score that falls below 80% in this change) | BLOCK |

- **Zones apply to new and changed code; ratchets hold the rest.** An unchanged legacy function with
  a CRAP of 30 passes as long as it gets no worse. Touching it brings it into the zones, so the
  change must bring it to green: whoever edits a function owns its score. A legacy module whose
  mutation score is already below a boundary is held by its ratchet, not quarantined on every touch.
- **Ratchets cover every module in both commits,** not only changed ones, so deleting tests that an
  unchanged module relied on is caught (QP-020, QP-023).
- **Module complexity and coverage count existing functions only.** New functions are held by their
  own limits (QP-025, QP-026), so adding a well-tested function never fails a module ratchet.
- **Vulnerabilities are repository-wide.** A critical or KEV vulnerability quarantines whether or not
  this change introduced it, since it must be fixed either way. Below that, only a vulnerability the
  baseline did not have blocks; existing ones stay on the dashboard (`07_Security_In_Depth.md`).

### Precedence

The engine applies every rule and reports every failure. The decision is **QUARANTINE** if any
finding is a quarantine, else **BLOCK** if there is any finding, else **PASS**. A "stops" rule
means the evidence cannot be trusted, so no metric is read at all: the engine never reports a
red-zone reading from evidence it could not verify. In the v2.2 priority table this is priority 1
(red zone, critical vulnerabilities), then 2 (bad evidence), 3 (ratchets, new functions), 4 (yellow
zone, moderate vulnerabilities) and 5 (PASS).

## 7️⃣ Output, Exit Codes and What Follows

`policy_decision.v1` is canonical JSON (sorted keys, no timestamp, no host), byte-identical for the
same inputs. It lists the digest of every input and every finding with its rule, module, function,
value, limit and baseline.

| Decision | Exit code | What follows |
| :--- | :--- | :--- |
| PASS | 0 | The change goes on to branch protection and code-owner review |
| BLOCK | 1 | The gate fails. Function and module findings become fixer sub-tickets (below); evidence findings (QP-001 to QP-006) are `infra` or `config` build failures, routed by `build_failure.v1` |
| QUARANTINE | 2 | The gate fails, the pull request gets the `quality-quarantine` label and the ticket moves to the owner. It leaves quarantine only by a fix or by an owner-approved exception |
| No decision | 3 | The engine could not run; the gate treats it as BLOCK |

- **Findings go to the fixer whose scope can fix them.** CRAP and complexity findings (QP-011,
  QP-012, QP-020, QP-022, QP-025, QP-030) go to the CRAP fixer, which changes production code only.
  Coverage and mutation findings (QP-013, QP-021, QP-023, QP-026, QP-031) go to the mutation fixer,
  which changes tests only. Vulnerability findings go to the Builder as a dependency change. The
  ticket rules are in `07_SoftwareFactory/01_Software_Factory.md` §3.
- **An override is an exception, never a flag.** Only the owner may approve one, as a
  `ci_exceptions.v1` entry for the check `quality-policy` that names one rule and one module or
  function, links the work that removes the need, and expires. The gate applies it after the
  engine decides; the engine itself knows nothing of exceptions. Evidence rules (QP-001 to QP-006)
  are never excepted, and no agent may write an exception.
- **Evidence is telemetry.** The engine has no network, so the gate job emits the evidence: a
  `policy_engine.evaluate` span with the decision, policy version and input digests; a structured
  log line with `trace_id` carrying the decision document's digest; and the metrics
  `policy_engine_decisions_total{decision}` and `policy_engine_findings_total{rule}`
  (`metrics/promql/MASTER_INDEX.md` §9).

## 8️⃣ How This Fits What Exists

- **Repository floors stay.** `.ci/quality.v1.json` still holds a total-coverage floor on every pull
  request and a mutation floor in the nightly run (`14_Test_Quality.md`). The engine adds what the
  floors cannot see: per-module ratchets, new-function limits and zones on the code a change touches.
- **The CRAP Analysis Service spec v1 is superseded for measurement.** Off-the-shelf tools replace its
  adapters and core for the MVP. Its ideas that the MVP leaves out (a body fingerprint to follow
  renamed functions, branch coverage, a hash-chained journal) are candidates for a later policy
  version, on evidence that the simpler identity misses real cases.
- **Determinism is tested, not assumed.** Every implementation of the engine must reproduce the
  vectors in `schemas/examples/policy_engine/vectors.json`. Each rule has at least one case designed
  to make it fail, and the reference engine is mutation-tested against them.

---

## Principle

Measure with standard tools, decide with one pure program, compare against the reviewed past, and
let nothing pass on evidence that cannot be checked.
