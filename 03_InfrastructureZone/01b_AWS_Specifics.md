# AWS Specifics

*Only what differs on AWS. Everything else follows `01_IaC_Standards.md`.*

---

## Remote State

- Backend: **S3** bucket per environment with versioning, default encryption (SSE-KMS), and
  public access blocked.
- Locking: use S3 native locking (`use_lockfile = true`, Terraform ≥ 1.10). DynamoDB locking
  is deprecated — use it only on older Terraform versions.
- The bucket lives in a dedicated state/admin account, not in the workload account.

```hcl
# root terragrunt.hcl
remote_state {
  backend = "s3"
  config = {
    bucket       = "tfstate-${local.env}-<org>"
    key          = "${path_relative_to_include()}/terraform.tfstate"
    region       = "<region>"
    encrypt      = true
    use_lockfile = true
  }
  generate = { path = "backend.tf", if_exists = "overwrite_terragrunt" }
}
```

---

## Identity

- CI and agents authenticate via **OIDC federation** (e.g., GitHub OIDC provider →
  `sts:AssumeRoleWithWebIdentity`). **No IAM users with access keys** for workloads.
- Role trust policies pin the OIDC `sub` claim to the exact repo / branch / environment.
- One role per workload per environment. Separate roles for `plan` (read-only) and `apply`
  (post-merge pipeline only), matching the Agent Rules in `AGENTS.md`.
- Never attach `AdministratorAccess` or `*` actions on `*` resources to workloads; guard
  accounts with SCPs.

---

## Tags

- Required tags on every taggable resource: `env`, `owner`, `service`, `managed_by=terragrunt`.
- Set them once with the provider's `default_tags` in the generated provider block; add
  per-unit tags in inputs.

---

## Required Services

- CloudTrail (organization trail) and CloudWatch Logs enabled per account
- One account per environment under AWS Organizations
- AWS Config or equivalent drift detection for security-relevant resources
