# Least Privilege Checklist

*Stand-alone reference for ensuring minimal necessary access across the platform.*

---

## 1. General Principles

- Grant only the permissions required to perform a task
- Avoid broad roles like `Editor` or `Owner` unless strictly necessary
- Apply separation of duties (different roles for deployment, monitoring, admin)
- Review permissions periodically
- Prefer groups/service accounts over individual users

---

## 2. Infrastructure (Terraform / GCP)

- Use scoped service accounts per environment
- Avoid hardcoding credentials
- Assign roles at the minimum resource level
- Document any exceptions in the PR
- Validate with `terragrunt plan` that permissions changes do not overreach

---

## 3. Backend Services

- API keys / secrets scoped per service
- No database superuser credentials in app configs
- Apply role-based access control (RBAC) for microservices
- Rotate secrets regularly

---

## 4. Frontend / Client-Side

- Do not expose sensitive API keys
- Only request data a user is authorized to see
- Validate tokens and session scopes on backend

---

## 5. Audit & Validation

- Periodically list users and service accounts
- Confirm least privilege with `gcloud iam roles describe` or equivalent
- Document findings in the PR or post-mortem if drift occurs

---

## 6. Philosophy

I grant **only the permissions required to perform a task**, minimizing risk while maintaining operational flow.

---

## 7. Checklist

| Resource / Role | Required Actions Only | Notes |
|-----------------|---------------------|-------|
| IAM Users | Assign to roles with minimal permissions | Avoid attaching full admin rights |
| Service Accounts | Limit scopes to needed APIs | Rotate keys regularly |
| Databases | Grant read/write per service | Avoid wildcard grants |
| Queues / Async Systems | Limit enqueue/dequeue to needed services | Dead-letter queues monitored |
| Storage / S3 / GCS | Restrict bucket access to required paths | Audit logs enabled |
| CI/CD Pipelines | Limit deploy access per environment | PR approval required |
| CI Workflows | `permissions: contents: read` default; grant per job | Shared workflows: owner/org access only, explicit secrets, pinned by tag/SHA (`07_Security_In_Depth.md` §5) |
| Kubernetes RBAC | RoleBindings follow least privilege | Avoid cluster-admin unless unavoidable |

---

## 8. Lifecycle Flow

1. **Define Access Need** → Identify required actions  
2. **Implement Policy** → Apply as code with review  
3. **Observe & Audit** → Monitor logs, failed access attempts  
4. **Refine & Rotate** → Remove unused roles, rotate keys, adjust privileges  

---

## 9. Principle

Least privilege is **not a restriction**, it’s **managed operational flow**: minimal risk, maximum visibility, and consistent governance across all layers.
