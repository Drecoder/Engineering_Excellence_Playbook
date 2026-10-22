# Anti-Pattern Catalog

*One versioned catalog of anti-patterns, read the same way by rig and the Reviewer, measured
before it is trusted, and never a new source of blocking.*

The catalog is `schemas/antipatterns.v1.json`, validated by `schemas/antipatterns.v1.schema.json`.
Its findings use `schemas/antipattern_finding.v1.schema.json`. The enforceable subset is in
`AGENTS.md` → **Anti-Pattern Rules**.

---

## 1️⃣ What a Rule Is

Each rule maps **one detector rule** to a stable ID, `AP-<STACK>-<NNN>`:

| Field | Meaning |
| :--- | :--- |
| `id`, `revision`, `added_in` | The ID never changes; `revision` increments when the meaning or mapping changes; `added_in` is the catalog version |
| `stack`, `framework` | Go, TypeScript (Node.js, React, Angular), Python (Django, FastAPI), HCL (Terraform, Terragrunt), Docker, CI (GitHub Actions) |
| `severity`, `confidence` | The catalog's own impact scale and expected hit quality, not the tool's |
| `detector` | The tool, its own rule ID exactly as reported, whether it is a custom rig check, and the mapping status |
| `remediation`, `references`, `related` | The fix, the tool's documentation, and the `ARCH-*`/`SEC-*`/`GOV-*` rules it also violates |
| `test_cases` | At least one positive case (must be reported) and one negative case (the fixed form, must not be) |
| `enforcement` | `planned`, `advisory`, or `retired`; `blocks` is the constant `false` in v1 |
| `benchmark` | `unmeasured`, or the measured counts and precision (§4) |

**Existing tools first.** A rule points at an existing tool's rule (go vet, staticcheck, ESLint and
its plugins, Ruff, Bandit, Semgrep, Checkov, Trivy, tflint, hadolint, actionlint, zizmor) and never
re-implements it.
A **custom rig check** (`tool: rig`, `custom: true`) exists only where no tool covers the pattern,
such as the Terragrunt rules and dependency conflicts.

## 2️⃣ Implemented, Mapped, or Planned

`detector.mapping.status` says how much is proven:

| Status | Meaning |
| :--- | :--- |
| `verified` | The tool, at the recorded version, was run on every positive and negative case inside the pinned toolchain image and reported the rule ID exactly on the positives. The image digest and `verified_in` (`local` or `ci`) are recorded |
| `mapped` | Taken from the tool's documentation; not yet run (for example, no runner for that tool in the toolchain) |
| `planned` | No detector exists yet: a custom rig check that is not built. Its rule is `planned` and produces no findings |

Verification runs only in the toolchain image (`tests/antipatterns/toolchain/`,
`tests/antipatterns/verify_detectors.py`), never with host-installed tools
(`00_UniversalStandards/12_Containers.md`). A `local` verification is provisional until the CI job
repeats it in the same image.

## 3️⃣ The Contract for rig and the Reviewer

Both consumers read the same catalog and must produce identical findings:

1. **Reject an invalid catalog**: schema errors, a duplicate ID, or two live rules on the same
   `(tool, rule_id)`. Never repair it.
2. **Look up each detector hit** by `(tool, rule_id)`. Only `advisory` rules produce findings; a hit
   with no rule, or on a `planned` or `retired` rule, is counted as unmapped and produces nothing.
3. **Normalize**: forward-slash, repository-relative paths; severity and confidence from the
   catalog; `blocking: false`; `reported_by` is `rig` or `reviewer`.
4. **Fingerprint**: the first 16 hex characters of SHA-256 over
   `rule_id|file|start_line|detector rule_id`, identical for both consumers, so the Reviewer and
   rig deduplicate the same finding.
5. **Share vectors, not code.** `schemas/examples/antipatterns/finding_vectors.json` holds hits and
   the exact findings expected. rig (Python) and the Reviewer (TypeScript) each pass them;
   `tests/antipatterns/reference.py` is the reference implementation.

## 4️⃣ Advisory, Always, in v1

- **No catalog rule blocks.** `enforcement.blocks` is the constant `false`, and the finding schema
  makes `blocking` the constant `false`. A finding never fails a build, never starts a review round
  on its own, and severity (even `critical`) does not change that.
- **The CI gate is unchanged.** The gate's own thresholds still apply to the underlying tools
  (`00_UniversalStandards/07_Security_In_Depth.md`). The catalog neither adds to that list nor
  removes from it.
- **Below the gate, findings are counted, not shown**, like every other below-threshold finding.

## 5️⃣ Measuring Detection Quality

A rule is measured on a labelled corpus. Each source contributes a different kind of truth:

| Source | Labels | Used for |
| :--- | :--- | :--- |
| **Seeded positive cases** | The rule's positive test cases and the benchmark's defect operators, with the defect's line range | True positives and false negatives |
| **Clean cases** | Negative test cases, and merged code with no finding confirmed and no incident on it for 90 days | False positives |
| **Historical pull requests** | Findings a person confirmed (fixed in the same or a later change) or dismissed (with a reason) | True and false positives on real code |
| **Known incidents** | Incident records (`docs/incidents/`) whose root cause is the anti-pattern, with the commit that introduced it | True positives the detector should have caught (recall) |

**Scoring:** a hit inside a labelled defect's line range is a true positive; a hit on a clean case
is a false positive; a labelled defect with no hit is a false negative. Precision is
TP / (TP + FP), reported with its **Wilson lower bound** at the catalog's confidence level; recall
is TP / (TP + FN). Results are recorded in the rule's `benchmark` block with the corpus hash and
date, and a held-out part of the corpus is never used while a rule is being tuned.

## 6️⃣ Promotion Criteria

Promotion is evidence, not opinion. A rule is **eligible** only when all of these hold
(`promotion` in the catalog):

- Its mapping is `verified` in CI, not only locally.
- At least **20 true positives** and **50 clean cases**.
- The precision **lower bound is at least 0.90** at 95% confidence.
- The measurement is at most **90 days** old.

Eligible means a reviewed change may **propose** adding the detector rule to the CI gate's own list,
through the gate's workstream. It never makes the catalog block. Changing that would need a new
schema version, not an edit to v1. A rule whose precision falls below the criteria in a later
measurement is reported, and a rule that stays noisy is `retired`.

## 7️⃣ Changing the Catalog

- Every change bumps `catalog_version`: patch for wording, minor for new or changed rules, major for
  removed rules or changed IDs.
- A new rule comes with positive and negative cases; a mapped rule moves to `verified` only through
  `verify_detectors.py` in the toolchain image.
- Candidates come from incident records, confirmed review findings, and benchmark misses; the loop
  is: candidate → rule with cases → verified mapping → measured → eligible.

---

## Principle

One versioned catalog, two consumers that read it identically, quality measured before anyone
relies on it, and no new way to block a change.
