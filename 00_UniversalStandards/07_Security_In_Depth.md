# Security in Depth

*No single control is trusted to hold. Every layer assumes the one before it can fail.*

This is the central security standard for every project that follows the playbook. Detailed
guidance lives in `03_InfrastructureZone/02_Security_IAM_Policies.md` (identity and access) and
`05_Metadata/Least_Privilege_Checklist.md`. The enforceable subset is in `AGENTS.md` →
**Security Rules**.

---

## 1️⃣ The Layers

| # | Layer | Protects | Core controls |
| :--- | :--- | :--- | :--- |
| 1 | **Human authentication** | Who a person is | SSO with MFA everywhere |
| 2 | **Human authorization** | What a person can do | Roles per environment, required approvals |
| 3 | **Workload and agent identity** | Who a service or agent is | Short-lived federated credentials |
| 4 | **Workload and agent authorization** | What a service or agent can do | Least privilege, allow-listed tools |
| 5 | **Data in transit** | Data moving between systems | TLS everywhere, authenticated service-to-service traffic |
| 6 | **Data at rest** | Stored data | Encryption with managed keys, no public access |
| 7 | **Data in model context** | Data sent to models | No secrets in prompts, logs, or spans |
| 8 | **Detection and audit** | Knowing a layer failed | Central audit logs and alerts |

---

## 2️⃣ Human Authentication

- **SSO with MFA** for source control, cloud consoles, observability, and notification channels.
  Phishing-resistant MFA (security keys / passkeys) for anyone with prod or admin access.
- **No shared accounts.** Every action traces to one named person.
- **No long-lived personal cloud credentials.** People reach clouds through SSO-issued, short-lived
  sessions.
- Offboarding removes access in one place (the identity provider), not in each tool.

---

## 3️⃣ Human Authorization

- Access is granted by **role and environment**, never individually where a group will do.
- **Branch protection** on every default branch: required reviews, required status checks, no
  force-push. Merges to staging and prod require human approval.
- **The merge is the gate.** Human approval is enforced by the forge on the merge itself (protected
  branches with required reviewers and checks, no bypass — admins included). A deploy that runs
  automatically after an approved merge is fine; a manual deploy button without merge approval
  does not satisfy this rule.
- **Separation of duties:** the person who writes a change is not its only approver for prod.
- **Break-glass access** is time-limited, requires a reason, alerts on use, and is reviewed in
  the post-mortem.
- Access is reviewed periodically; unused roles are removed.

---

## 4️⃣ Workload and Agent Identity

- CI, agents, and services authenticate with **federated, short-lived credentials** (GitHub OIDC,
  AWS IAM roles, GCP Workload Identity Federation). **No static keys.**
- Trust policies pin the token's subject to the exact repository, branch, and environment.
- **Separate identities per purpose:** a read-only plan identity and a post-merge apply identity;
  one identity per Deployment Unit per environment.

---

## 5️⃣ Workload and Agent Authorization

- **Least privilege** at the lowest resource level; no basic/admin roles on workloads; permissions
  boundaries (AWS) and org policies (GCP) as ceilings.
- Agents are limited by their **tool allow-list** and sandbox; they never apply infrastructure and
  never write outside their sandbox (`06_AgentZone/01_Agent_Standards.md`).
- Deployment Units never read each other's state; they share values only through outputs.

---

## 6️⃣ Data in Transit

- **TLS 1.2 or higher on every connection**; TLS 1.3 preferred. Plain HTTP only for local
  development on loopback.
- **Service-to-service traffic is authenticated**, not just encrypted: mTLS or signed short-lived
  tokens. Telemetry pushed from a Deployment Unit carries that unit's own identity.
- **Private connectivity** (private endpoints, VPC endpoints, Private Service Connect) where the
  provider offers it for the service in use.
- **Webhooks are verified** (signature checks such as GitHub's HMAC) before any processing.
- Certificates are issued and rotated automatically; no hand-managed certificates.

---

## 7️⃣ Data at Rest

- **Everything is encrypted at rest** with provider-managed KMS keys by default, and
  **customer-managed keys** where data classification or regulation requires it.
- **Public access is blocked by default** on buckets, disks, snapshots, and databases.
- **State is protected:** state buckets are encrypted, versioned, access-logged, and readable only
  by plan/apply identities.
- **Backups are encrypted** and restore-tested.
- Data is classified (public, internal, confidential, restricted); the class decides key type,
  retention, and residency.

---

## 8️⃣ Data in Model Context

- Credentials and secrets never enter prompts, tool outputs, logs, or span attributes.
- Telemetry collectors **redact** known secret patterns before export.
- Untrusted input (code, diffs, logs) is delimited and treated as data, never as instructions.
- Restricted data does not leave its boundary to reach a model; use a private model inside the
  boundary or do not send it.

---

## 9️⃣ Detection and Audit

- Cloud audit logs (AWS CloudTrail, GCP Cloud Audit Logs) and identity-provider logs flow into the
  independent observability stack, where they cannot be altered by the workloads they describe.
- Alerts on: IAM and policy changes, break-glass use, repeated failed sign-ins, public-access or
  encryption settings being disabled.
- Secret scanning runs on every commit and PR.

---

## 🔟 Enforced as Code

Each layer that can be checked automatically is a **TIER_0 policy** run by rig-scan on every plan
and PR — no model, no tokens, no reliance on memory. Policy ids appear in findings as `rule_id`.

| Policy | Rule |
| :--- | :--- |
| `SEC-001` | Storage (buckets, disks, databases, snapshots) has encryption at rest enabled |
| `SEC-002` | Public access is blocked on storage unless the unit is explicitly allow-listed |
| `SEC-003` | Load balancers and endpoints enforce TLS 1.2 or higher; no plain-HTTP listeners |
| `SEC-004` | No IAM users with access keys; no service account keys |
| `SEC-005` | No `*` actions on `*` resources; no basic/admin roles on workloads |
| `SEC-006` | OIDC trust policies pin repository, branch, and environment |
| `SEC-007` | State buckets are encrypted, versioned, and access-logged |
| `SEC-008` | Every Deployment Unit configures an authenticated telemetry collector |
| `SEC-009` | Audit logging is enabled in every account and project |
| `SEC-010` | No secrets in code or config (secret scanning) |

A failing `SEC-*` policy blocks the change. Exceptions are granted per unit in a reviewed policy
file, with an owner and an expiry date.

### Gate thresholds — block on critical, report nothing else

Pipeline gates stay quiet: a change is blocked, and the pull request shows a finding, only when
it is critical. No noise below that line.

| Check type | Blocks on | Pull request shows |
| :--- | :--- | :--- |
| Format, lint errors, type check, compile (`terragrunt hcl fmt`, `tflint`, `tsc --noEmit`, `go vet`, Python compile) | Any failure (pass/fail, no severity) | The failure |
| Dependency and image scanners (`npm audit`, `pip-audit`, `trivy`) | **CRITICAL** severity, or any vulnerability on the **CISA KEV** list regardless of severity | Only the blocking findings |
| `govulncheck` | Any finding (it reports only vulnerabilities the code actually calls) | Only the blocking findings |
| IaC scanners (`checkov`) | The `SEC-*` check list (hard-fail); all other checks soft-fail | Only the blocking findings |
| `SEC-*` policies | Always, whatever the severity | The failing policy |

- **KEV overrides severity.** A vulnerability that is being exploited in the wild blocks even when
  it is rated below critical. The gate reads a pinned, regularly refreshed copy of the KEV
  catalog, not a live call.
- **Below-critical findings are counted, not shown.** They go to a dashboard metric
  (`gate_findings_total{severity}`), never to the pull request, so a growing backlog is visible
  without adding noise.
- Tools without a severity filter (`pip-audit`) run through a thin wrapper that maps findings to
  severity (OSV data) and applies this table. Open-source `checkov` has no severities, so it
  gates on check IDs instead.
- Exceptions follow the same reviewed policy file (owner and expiry); a KEV finding cannot be
  excepted past its CISA due date.

---

## Principle

Security is not a gate at the end; it is a property of every layer, checked on every change.
