# Infrastructure-as-Code Standards

*Infrastructure must be reproducible, observable, and secure by default — on every cloud.*

This is the cloud-agnostic core. Cloud-specific rules live in:

- `01a_GCP_Specifics.md` — GCS backend, Workload Identity Federation, labels
- `01b_AWS_Specifics.md` — S3 backend, IAM roles via OIDC, tags

If a cloud-specific doc conflicts with this one, this one wins.

---

## Philosophy

I manage infrastructure to ensure it is reproducible, observable, and version controlled.

All changes flow through the platform lifecycle:

1. Design & define in Terraform modules, orchestrated by Terragrunt
2. Peer review via Pull Request
3. Plan & validate against current state
4. Deploy through CI/CD pipeline
5. Observe metrics and logs
6. Improve iteratively based on feedback

The focus is on **deterministic outcomes**, cross-layer consistency, and operational visibility.

---

## 🔴 Red Light Conditions

Infrastructure must not ship if:

- Resources are created manually in a cloud console
- IAM roles are overly permissive (e.g., GCP `Editor` / `Owner`, AWS `AdministratorAccess` or `*:*`)
- Secrets are hardcoded or committed
- Long-lived static credentials are used where federated identity is available
- No remote state with locking exists
- No naming convention enforced
- No tagging/labeling strategy
- No monitoring enabled
- No environment separation
- The plan contains an unexplained `delete` or replace action

---

## 🟢 Green Light Conditions

Infrastructure is production-ready when:

- All resources are defined in code and applied through Terragrunt
- Remote backend configured once in the root `root.hcl`, with locking
- IAM follows least privilege
- Variables used for environment abstraction
- Modules used for reusable patterns, isolated from each other's state
- Outputs defined intentionally
- `tflint` and `checkov` pass
- Cost impact reviewed
- Rollback path understood

---

## Required Components (Every Cloud)

- Network with subnet isolation (GCP VPC / AWS VPC)
- Workload identities with scoped permissions (GCP service accounts / AWS IAM roles)
- Centralized logging enabled
- Monitoring alerts configured (see `04_OperationalRunbooks/02_Monitoring_Alert_Thresholds.md`)
- Separate environments (dev/stage/prod), each with its own state and identity
- State stored remotely with locking

---

## Repository Layout

```text
<repo>/
├── root.hcl                    # root: remote_state + provider generation, defined once
├── modules/<module>/           # reusable Terraform modules
└── live/
    ├── _bootstrap/<cloud>/identity/   # OIDC trust, plan + apply identities (applied once by a human)
    └── <env>/<cloud>/<unit>/
        └── terragrunt.hcl      # include root, set inputs, declare dependency blocks
```

Bootstrap is Terragrunt too: the remote-state backend creates its own bucket, and the identity
units are the only ones a human applies by hand. Everything after them runs through CI.

---

## Deployment Unit Lifecycle

A **Deployment Unit (DU)** is the atomic thing the platform launches: its own state, identity,
and blast radius. DUs never read each other's state; they share values only through outputs.

| Class | Lifetime | Rules |
| :--- | :--- | :--- |
| `persistent` | Long-lived (bootstrap, state, telemetry storage) | Deletes and replacements are blocked by the no-delete gate |
| `ephemeral` | Created on demand, destroyed after use | Requires a `ttl` label; destroyed only by the apply pipeline; swept by a scheduled cleanup when expired or orphaned |

- Agents and people **request** a DU with a spec (type, size, TTL). The apply pipeline validates it
  against policy (budget, max TTL, allowed instance types) and applies it. Agents never create
  infrastructure directly.
- Build order for a platform: **bootstrap → observability → networking → workloads**, so
  everything after bootstrap reports telemetry from its first run.
- DU creation time and teardown success are tracked as metrics.

---

## Cost Defaults

Spin up only what is used, and make idle cost visible:

- **Prove the loop in dev first.** Staging and prod may exist from day one, each with its own
  state and identity, but keep their fixed-cost resources minimal or scaled to zero until the
  dev loop works.
- **Avoid fixed hourly costs in dev:** no NAT gateways, managed Kubernetes clusters, or idle load
  balancers unless the unit truly needs them.
- **GPUs are on demand.** Prefer a scale-to-zero service (e.g. Cloud Run with a GPU) over a
  long-lived VM; a GPU VM must be an `ephemeral` DU with a TTL.
- **Budget alerts in every account and project** as the backstop for the TTL cleanup.
- Request GPU quota early; give GPU units an ordered list of allowed zones or regions.

---

## Pull Request Requirements

Every IaC PR must include:

- `terragrunt plan` output (attach the plan JSON summary)
- Risk summary
- IAM diff explanation (if changed)
- Rollback consideration
- Cross-layer impact notes
- Structural vs behavioral classification — never both in one PR (see `AGENTS.md`)

---

## Observability Rule

If infrastructure changes but monitoring does not reflect it,
the change is incomplete.

---

## Final Principle

Infrastructure is not configuration.

It is code.

And code must follow lifecycle discipline.
