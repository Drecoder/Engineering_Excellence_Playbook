# GCP Specifics
*Only what differs on GCP. Everything else follows `01_IaC_Standards.md`.*

---

## Remote State

- Backend: **GCS** bucket per environment, with object versioning enabled. GCS provides
  state locking natively.
- The bucket lives in a dedicated state/admin project, not in the workload project.

```hcl
# root terragrunt.hcl
remote_state {
  backend = "gcs"
  config = {
    bucket   = "tfstate-${local.env}-<org>"
    prefix   = path_relative_to_include()
    project  = "<state-project>"
    location = "<region>"
  }
  generate = { path = "backend.tf", if_exists = "overwrite_terragrunt" }
}
```

---

## Identity

- CI and agents authenticate with **Workload Identity Federation** (e.g., GitHub OIDC →
  workload identity pool → service account impersonation). **No service account keys.**
- One service account per workload per environment; grant roles at the lowest resource level
  (project → folder → org only when unavoidable).
- Never grant basic roles (`roles/owner`, `roles/editor`, `roles/viewer`) to workloads.

---

## Labels

- Required labels on every labelable resource: `env`, `owner`, `service`, `managed_by=terragrunt`.
- Label keys and values: lowercase letters, digits, `_` and `-` only, ≤ 63 characters.
- Set shared labels once in the root config and merge per-unit labels in inputs.

---

## Required Services

- Cloud Logging and Cloud Monitoring enabled per project
- Audit logs (Admin Activity is always on; enable Data Access logs for sensitive services)
- Organization policies for: no external SA keys, restricted resource locations
