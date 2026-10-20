# Emergency Rollbacks

*Step-by-step procedures for rolling back deployments safely and quickly.*

---

## 1️⃣ Philosophy

I treat rollbacks as **managed flows, not panic actions**:

- Every deployment is reversible by design  
- Rollbacks are tested in staging before production  
- Observability and logging are mandatory during rollback  
- Root cause analysis follows, but rollback always restores service first  

---

## 2️⃣ Rollback Workflow

1. **Detection**  
   - Monitor alerts, logs, and metrics  
   - Identify failed or degraded deployment  

2. **Decision**  
   - Confirm rollback necessity  
   - Communicate to stakeholders  

3. **Execution**  
   - Trigger rollback via CI/CD or Terraform  
   - Validate infra and backend services restored  

4. **Validation**  
   - Check application logs, health endpoints, and dashboards  
   - Confirm metrics returned to normal thresholds  

5. **Post-Rollback Analysis**  
   - Document root cause  
   - Update deployment checklist to prevent recurrence  

---

## 3️⃣ Key Guidelines

- Always **back up DB or stateful resources** before rollback  
- Use **feature flags** where possible to isolate failures  
- Keep **rollback scripts version-controlled**  
- Automate as much as possible to reduce human error  

---

## 4️⃣ Infrastructure (IaC) Rollbacks

Infrastructure rolls **forward to a known-good commit**; nobody edits state or the console by hand.

1. **Revert the change in Git** — `git revert` the merge commit; never force-push over history.
2. **Plan the revert** — `terragrunt plan` against the reverted commit and review it like any PR.
   Pay extra attention to `delete` / replace actions: reverting a create destroys a resource.
3. **Structural changes need the reverse `moved` blocks.** If the original change moved or
   renamed resources, the revert must include `moved` blocks in the opposite direction, or the
   plan will destroy and recreate them.
4. **Stateful resources** — confirm backups / snapshots exist and `prevent_destroy` holds before
   applying any plan that touches databases, buckets, or disks.
5. **Apply through the pipeline** — the post-merge pipeline applies the revert with its scoped
   identity. Manual `apply` only during a declared incident, and it is recorded in the post-mortem.
6. **State recovery (last resort)** — restore the previous state version from the versioned
   backend (GCS / S3) only when state itself is corrupted, then run `plan` to confirm no drift.

---

## 5️⃣ Principle

I manage rollbacks as a **repeatable, observable flow** — ensuring service continuity first, learning second.
