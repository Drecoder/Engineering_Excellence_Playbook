# Reuse and DRY

*Say each thing once, in the right place. When agents write most of the code, finding what already
exists has to be engineered, not hoped for.*

Agents optimize locally: without a map of what exists, a Builder regenerates a helper rather than
finding the existing one. The cost is real, not aesthetic. On 2026-10-21 a retry fix landed in the
CI runners' startup script and missed the inference pool's copy of the same bootstrap
(sovereign-vpc-gcp `docs/incidents/INC-001`). This standard defines where shared things live, how
agents find them, and how duplication is caught. The enforceable subset is in `AGENTS.md` →
**Reuse Rules**.

---

## 1️⃣ When to Abstract, and When Not To

DRY has two failure modes: copies that drift, and abstractions nobody can follow ("indirection
hell"). The rule balances both:

| Situation | Rule |
| :--- | :--- |
| Security code (redaction, auth, input sanitization) or a contract (schemas, string contracts) | Extract on the **second** copy. A drifted copy of these is a vulnerability or a broken interface |
| Everything else | Extract on the **third** copy. Two copies are often coincidence |
| An abstraction that needs flags or special cases to fit its callers | Leave the duplication. **Duplication is cheaper than the wrong abstraction** |
| The same behavior in two languages | Do not share code across runtimes. Share the **spec and its test vectors** (§5) |

---

## 2️⃣ Scope: Internal and Shared

Every definition has exactly one of two scopes:

| Scope | What | Who may use it |
| :--- | :--- | :--- |
| `internal` | Everything inside one declared boundary | Only code inside that boundary |
| `shared` | Exported symbols in `packages/` or `schemas/`, or explicitly marked `@shared` | Anyone, across boundaries and repos |

- **Boundaries are declared** per repo, one per language unit: a TypeScript package, a Go module, a
  Python package, a Terraform module. Anything undeclared or ambiguous is `internal` (fail closed).
- **Exported is not shared.** A symbol exported by accident does not join the shared scope;
  membership is the explicit set above, so nothing becomes a platform dependency without a decision.
- **Importing another boundary's `internal` symbol is a violation**, caught by language-native
  enforcement where it exists (Go `internal/`, TypeScript `exports` maps, Terraform module
  isolation) and by rig's boundary rule everywhere else.
- **Promotion** (moving code into `packages/` or marking it `@shared`) is a reviewed change of its
  own, never a side effect of another task.

---

## 3️⃣ The Reuse Map

The reuse map is the platform's index of what exists: rig's symbol index (`schemas/symbol_index.v1.json`),
one entry per definition.

- **Generated, never hand-written.** rig builds it deterministically from the source (tree-sitter
  parsers for TypeScript, Python, Go, HCL) and regenerates it on every merge. A hand-kept map goes
  stale, and a stale map is worse than none: agents trust it.
- **Definitions only:** exported code symbols, IaC module inputs and outputs, contracts by
  `schema_version`, and **string contracts** (metric, span, environment variable, and PR label
  names). Locals and loop variables are noise; repeated IaC inputs like `project_id` are expected,
  not duplication.
- **Each entry carries** a signature, location and revision, purpose, scope and boundary, tags
  (`security`, `contract`, `telemetry`, ...), fan-in and fan-out, a normalized body hash, and per
  function cognitive complexity.

### How the Builder uses it

- The Builder's task carries a **slice** of the map, never the whole index: required primitives for
  its stack, contracts it touches, its own boundary's symbols, and a few shared candidates. One line
  per symbol, no bodies.
- It reads a body only when it decides to use that symbol, and searches the map through a read-only
  tool when the slice is not enough.
- It never sees another boundary's `internal` symbols, so it cannot be tempted to import them.

---

## 4️⃣ Catching Duplication

Code decides what code can decide; a model judges only the rest.

| Check | Decided by | Blocks? |
| :--- | :--- | :--- |
| Exact or near clone (same normalized body hash, or a close near-miss signature) | rig, deterministic | Advisory, except copies of security code |
| Copy of a contract (a `schema_version` or data shape outside `.playbook/`) | rig, deterministic | **Blocks** |
| String-contract collision (an existing metric, span, env var, or label name reused or nearly reused) | rig, deterministic | **Blocks** for exact reuse; advisory for near matches |
| Illegal cross-boundary import | rig and language tooling | **Blocks** |
| Rule-of-three count | rig, from the index | Informs the two rows above |
| "Same thing, different name" (similar purpose and signature, different body) | The Reviewer's `reuse` lens | Advisory |

- **Fixed in the same PR.** DRY findings are fixed inside the change that introduced them, within
  the change's bounded review loop (`AGENTS.md` → Agent Rules). Only **deterministic** DRY findings
  (a clone, a hash or signature match against a reuse-map entry) start a fix round; a model's "this
  looks similar" stays advisory, because a fix based on a guess is how refactor ping-pong starts.
- A DRY fix may only touch files already in the change, and never promotes code to `shared`.

---

## 5️⃣ Across Languages: Share the Spec, Not the Code

A Go function and a TypeScript function never hash alike, and sharing code across runtimes is not
possible anyway. The duplication that matters across languages is contracts and names:

| Duplicated across languages | How it stays single-sourced |
| :--- | :--- |
| **Data shapes** | The contract lives once in the playbook's `schemas/`. Types in each language are generated from it or validated against it; a hand-written type matching a contract's shape is a finding |
| **String contracts** | Indexed by exact value, whatever the language. `governor_max_limit` in TypeScript, Python, and PromQL is one entry |
| **Behavior** (e.g. secret redaction in Python and TypeScript) | The rules live once as data (patterns, cases), and every implementation is tested against the same test vectors |

---

## 6️⃣ Contracts Have One Home

- Every contract crossing a repo boundary lives in the playbook's `schemas/` and is vendored into
  consumers as `.playbook/schemas/` (`05_Standards_Distribution.md`).
- A consumer never hand-copies a contract. A copy outside `.playbook/` is the contract-copy finding
  in §4, and it blocks.
- Changing a contract's shape follows the exported-interface rule: all consumers change in the same
  change, or the contract gets a new version.

---

## 7️⃣ Measured

| Metric | Meaning |
| :--- | :--- |
| `code_duplication_ratio{repo}` | Share of indexed definitions that are clones of another |
| `pr_new_clones_total{repo,kind}` | Clones introduced per change, by kind (exact, near, contract, string) |
| `reuse_hits_total` / `builder_tasks_total` | Share of Builder tasks that used a reuse-map entry they were shown |

A rising duplication ratio while agents write more of the code means the reuse map or the Builder's
slice is failing, not that the rules are too strict.

---

## Principle

Shared things live in one place, agents are shown that place before they write, and code catches
the copies a person or a model misses.
