# Compliance Engine

*The builder may submit artifacts and evidence; it never authorizes its own release.*

The compliance engine decides whether an artifact may be released, from evidence the builder
submits. It is split across components with separate identities, because the component that wants
a release cannot be the one that grants it. Contracts: `schemas/compliance_submission.v6.schema.json`
(the submission), `schemas/compliance_registry.v1.json` (the criteria), and
`schemas/examples/compliance/canonical_identity_vectors.json` and
`attestation_payload_vectors.json` (the artifact identity and the signed evidence bytes every
implementation must reproduce; checked by `tests/contracts/test_compliance_contracts.py`).

---

## 1️⃣ Components and Trust Boundaries

| Component | Lives in | Does | Never does |
| :--- | :--- | :--- | :--- |
| **Scoping skill** (`scope_compliance`) | The Builder, at the scoping stage | Reads the registry for the target stage, returns the criteria and minimum evidence tiers the work must satisfy, checks a draft submission against the contract, and runs an advisory dry run of the structural rules | Verify attestations, judge freshness, decide a gate, or issue a token. Its output says `authoritative: false` |
| **Compliance authority**: contract validator, evidence verifier, policy evaluator, authorization service | A separate service with its own identity | Verifies each evidence attestation against the attester's public key, checks freshness and path invalidation, evaluates every mandatory criterion, stores the immutable evaluation record, and signs a short-lived, single-use release token bound to the artifact digest | Accept a decision, status, freshness flag, or authorization claim from the builder |
| **Deployment guard** | The deploy boundary (the apply pipeline or deploy workers) | Verifies the token, checks the target artifact and environment match it, consumes the token atomically, and deploys the pinned digest | Deploy without a valid, unconsumed token, or deploy anything other than the authorized digest |

Each boundary is its own identity: the builder cannot read the authority's signing key, and the
authority cannot deploy. The keys that sign evidence (the attester, typically CI) and tokens (the
authority) are different keys.

## 2️⃣ Lifecycle

1. **Scoping.** Before work starts, the builder calls its scoping skill for the target lifecycle
   stage and plans the evidence each criterion needs. The same criteria drive the intake wizard's
   questions (`06_AgentZone/03_Software_Factory_Intake.md`).
2. **Building.** The builder produces the artifact; CI runs the checks and signs each evidence
   record over its canonical attestation payload.
3. **Evaluation.** The builder submits the artifact and evidence to the authority. The authority
   evaluates every mandatory criterion exactly once: missing evidence is `BLOCKED`; present evidence
   that fails verification, freshness, or attestation, or is below the required tier, is
   `REMEDIATE`; the gate follows `BLOCKED > REMEDIATE > PASS`.
4. **Authorization.** Only for a stored `PASS` record, and only for the artifact that record names,
   the authority issues a token (RS256, unique `jti`, `iat`, `nbf`, `exp`).
5. **Deployment.** The guard claims the token once and deploys the pinned digest; a replayed or
   raced token is refused.

## 3️⃣ Shared Rules

- **One contract, many implementations.** The Builder (TypeScript) and the authority (Python)
  read the same vendored schemas and registry and pass the same canonical-identity vectors: the
  playbook shares the spec and test vectors, not code (`00_UniversalStandards/09_Reuse_and_DRY.md`).
- **Canonical identity** is the compact, key-sorted, ASCII JSON of every artifact field; tokens
  carry its SHA-256 as `artifact_digest`.
- **Attestation payload** is the same canonical JSON over the 11 evidence fields other than
  `attestation_signature`, with `monitored_paths` sorted and `timestamp_utc` exactly as submitted
  (UTC with a literal `Z`, at most microseconds), never parsed and re-serialized. Implementations
  reproduce `schemas/examples/compliance/attestation_payload_vectors.json`.
- **Freshness** is judged against the authority's clock at evaluation (`evaluated_at`), never the
  builder's: evidence is fresh when its `timestamp_utc` is at most 24 hours old and at most 5
  minutes in the future (clock skew). Anything outside that window is stale, and its criterion is
  `REMEDIATE`.
- **Patterns are full matches.** Python's `jsonschema` lets `$` match before a trailing newline, so a
  Python consumer also validates into typed models that match whole strings; the schema alone is
  not enough there.
- **Fail closed** on a missing key, an unknown criterion, a duplicate criterion, a non-UTC clock, an
  invalid registry, or any verification error.

---

## Principle

Let the builder plan and submit, let an independent authority decide and sign, and let the deploy
boundary accept nothing but a valid, unused token for the exact artifact that passed.
