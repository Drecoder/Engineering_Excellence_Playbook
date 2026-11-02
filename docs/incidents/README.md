# Incidents

Failures and near misses that affect the platform as a whole, rather than one repository, in the
format of `00_UniversalStandards/03_Post_Mortem_Template.md`. Incidents in one repository live in
that repository's `docs/incidents/`.

| ID | Date | Title | Severity | Detection | Time to detect | Time to resolve | Fix |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| [INC-001](2026-10-26-INC-001-no-branch-protection.md) | 2026-10-26 | No branch protection on any platform repository | High | Manual investigation | Not determined | Open | Owner's settings change; see preventive actions |
| [INC-002](2026-10-29-INC-002-static-admin-key-standalone-aws-account.md) | 2026-10-29 | Long-lived administrator access key on a standalone AWS account | High | A coding assistant applying the identity rule | About 11 months after the key was created | Open | Owner's identity changes; see preventive actions |
