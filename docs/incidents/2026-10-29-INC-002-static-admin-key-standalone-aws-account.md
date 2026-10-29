# INC-002: Long-Lived Administrator Access Key on a Standalone AWS Account

## 1️⃣ Incident Summary

- **ID / Severity:** `INC-002`; High
- **Date / Time:** Found 2026-10-29 during proof-of-concept testing. The key was created on
  2025-11-19 and last used on 2026-10-26. Still open.
- **Service / System Affected:** The AWS account the factory uses (the Builder's model provider,
  Bedrock, runs there), and every workstation tool that reads the local AWS profile.
- **Impact:** The local AWS profile authenticates as an IAM user, not through single sign-on:
  - **One active access key, about eleven months old,** a long-lived static credential, which
    `AGENTS.md` → Security Rules forbids ("SSO with MFA; … never static keys").
  - **No MFA device** on the user.
  - **Administrator access** through the `admin` group (`AdministratorAccess`).
  - **The account is in no AWS Organization,** so no service control policy applies to it. The
    playbook treats a standalone account as a governance finding (`AGENTS.md` → Governance Rules).
  - No misuse is known. Anyone holding the key file has administrator access until the key is
    deactivated.
- **Detection Method:** A coding assistant applying the playbook's identity rule to what was
  actually running (`aws sts get-caller-identity` before a live-agent test). No control, scanner,
  or alert reported it.

## 2️⃣ Timeline of Events

| Time (UTC) | Action / Observation | Responsible |
| :--- | :--- | :--- |
| 2025-11-19 | Access key created for the IAM user | Owner |
| 2026-10-22 | AWS single sign-on set-up started: a new organization management account was planned and this account was to be invited | Owner, assistant |
| 2026-10-26 | Key last used (CloudFormation) | Owner |
| 2026-10-29 | Found while checking the toolchain before the first live-agent run; read-only checks: key age, MFA, group policies, organization membership | Assistant |

## 3️⃣ Root Cause Analysis

- **Trigger:** The workstation was set up with an IAM user's access key before the single sign-on
  rule existed, and the move to IAM Identity Center was started but not finished.
- **Systemic issue:** Nothing checks identities against the rule. The governance baseline is
  enforced through an organization's service control policies, and this account is in no
  organization, so it inherits none of them.
- **Contributing factors:**
  - A static key keeps working silently; nothing expires it.
  - The account's second IAM user has not been inspected.

## 4️⃣ Resolution & Mitigation

- **None yet.** Identity and account settings are the owner's to change.
- **Evidence recorded:** read-only IAM and Organizations calls only. No key material, key ID, or
  account number appears in this public record.

## 5️⃣ Preventive Actions

| Action Item | Owner | Target Date | Status |
| :--- | :--- | :--- | :--- |
| Finish the organization: a management account, this account invited, IAM Identity Center with MFA; switch the CLI to `aws sso login` | Drecoder | 2026-11-05 | Open |
| Deactivate the access key, confirm nothing breaks (its last use was CloudFormation), then delete it and the user's `admin` group membership | Drecoder | After SSO works | Open |
| Inspect the account's second IAM user the same way | Drecoder | 2026-11-05 | Open |
| **Add the missing signal:** AWS Config rules `access-keys-rotated`, `iam-user-mfa-enabled`, and `iam-user-unused-credentials-check`, with findings routed as alerts | platform | With the organization | Open |
| Apply the governance baseline's service control policies to the account once it is in the organization (Genesis) | platform | With the organization | Open |
