# Terraform GCP Standards
*Infrastructure must be reproducible, observable, and secure by default.*

---

## Philosophy

I manage infrastructure to ensure it is reproducible, observable, and version controlled.

All changes flow through the platform lifecycle:

1. Design & define in Terraform
2. Peer review via Pull Request
3. Plan & validate against current state
4. Deploy through CI/CD pipeline
5. Observe metrics and logs
6. Improve iteratively based on feedback

The focus is on **deterministic outcomes**, cross-layer consistency, and operational visibility.
---

# 🔴 Red Light Conditions

Infrastructure must not ship if:

- Resources are created manually in GCP console
- IAM roles are overly permissive (e.g., Editor)
- Secrets are hardcoded
- No remote state management exists
- No naming convention enforced
- No tagging/labeling strategy
- No monitoring enabled
- No environment separation

---

# 🟢 Green Light Conditions

Infrastructure is production-ready when:

- All resources are defined in Terraform
- Remote backend configured (GCS)
- IAM follows least privilege
- Variables used for environment abstraction
- Modules used for reusable patterns
- Outputs defined intentionally
- Cost impact reviewed
- Rollback path understood

---

## Required Components for GCP Projects

- VPC with subnet isolation
- Service accounts with scoped IAM
- Cloud Logging enabled
- Monitoring alerts configured
- Separate environments (dev/stage/prod)
- State stored remotely with locking

---

## Pull Request Requirements

Every Terraform PR must include:

- `terragrunt plan` output (attach the plan JSON summary)
- Risk summary
- IAM diff explanation (if changed)
- Rollback consideration
- Cross-layer impact notes

---

## Observability Rule

If infrastructure changes but monitoring does not reflect it,
the change is incomplete.

---

## Final Principle

Infrastructure is not configuration.

It is code.

And code must follow lifecycle discipline.