# Security & IAM Policies
*Guidelines for managing identities, access, and privileges across the platform.*

---

## 1️⃣ Philosophy

I manage security **as part of the platform flow**:

- Access is granted **based on role and function**, not convenience  
- Policies are version-controlled and auditable  
- Observability and monitoring of IAM changes is mandatory  
- Least privilege is the default approach  
- Security controls are **integrated into CI/CD**  

---

## 2️⃣ Policy Principles

| Principle | Implementation |
|-----------|----------------|
| **Least Privilege** | Grant only the permissions required to perform the role. See `Least_Privilege_Checklist.md` |
| **Separation of Duties** | Avoid combining high-risk roles (e.g., admin + deploy) |
| **Auditability** | Enable logging of IAM changes, policy updates, and access events |
| **Temporal Access** | Use time-bound or session-limited credentials where possible |
| **Version Control** | Manage IAM policies as code; changes via PRs for review |
| **Automated Enforcement** | Use policy-as-code tools (Terraform, GCP IAM, AWS IAM, OPA, etc.) |

---

## 3️⃣ Lifecycle Flow

1. **Define Role / Access Need**  
   - Map user/service to minimum required actions  
2. **Implement Policy as Code**  
   - Terraform modules orchestrated by Terragrunt  
   - PR review required for all changes  
3. **Deploy & Monitor**  
   - Observe IAM changes, failed access attempts  
   - Alert on drift or privilege escalation  
4. **Review & Refine**  
   - Periodic audits and rotations  
   - Apply lessons from incidents or policy drift  

---

## 4️⃣ Principle

IAM is **flow-managed access**, not static permissions. I enforce policies consistently across all layers — infrastructure, backend, frontend — while remaining auditable and reproducible.