# INC-002: Long-Lived Administrator Access Key on a Standalone AWS Account

## 1️⃣ Incident Summary

- **ID / Severity:** `INC-002`; High
- **Date / Time:** Found 2026-10-29 during proof-of-concept testing. The key was created on
  2025-11-19 and last used on 2026-10-26. Resolved for people on 2026-11-03: single sign-on with
  MFA, key deactivated, long-lived credentials denied (F-0013 fixed). Enforcement for workload
  accounts is still open (F-0016).
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
| 2026-11-03 | IAM Identity Center turned on as an organization instance, making this account the organization's management account; the owner signs in through it with MFA, and the CLI uses `aws sso login` | Owner |
| 2026-11-03 | Access key deactivated; a fresh credential report shows no active access keys on any user and root with MFA | Owner |
| 2026-11-03 | The owner's permission set denies creating users, access keys and console passwords, and re-activating a key; shown to fail (`iam:CreateUser` returned `AccessDenied`) | Owner, assistant |
| 2026-11-03 | Found that service control policies never apply to a management account, so the planned enforcement would have denied nothing here (F-0020) | Assistant |

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

- **People sign in through single sign-on with MFA.** IAM Identity Center is the only way in for
  the owner; the IAM user is no longer used.
- **The key is inactive,** and the credential report shows no active access keys. It is deleted,
  with the old user, after seven days with nothing broken.
- **Long-lived credentials are denied.** The owner's permission set carries an explicit deny on
  creating users, access keys and console passwords, and on re-activating a key, shown to fail.
  Root, with MFA, is the break-glass path.
- **The second IAM user was inspected:** never signed in, no password, no keys; it is being deleted.
- **Evidence recorded:** read-only IAM and Organizations calls only. No key material, key ID, or
  account number appears in this public record.

## 5️⃣ Preventive Actions

| Action Item | Owner | Target Date | Status |
| :--- | :--- | :--- | :--- |
| Finish the organization: a management account, this account invited, IAM Identity Center with MFA; switch the CLI to `aws sso login` | Drecoder | 2026-11-05 | **Done 2026-11-03**, changed: this account became the management account instead of being invited; MFA on the directory user to confirm |
| Deactivate the access key, confirm nothing breaks (its last use was CloudFormation), then delete it and the user's `admin` group membership | Drecoder | After SSO works | **Deactivated 2026-11-03**; deletion after a seven-day soak |
| Inspect the account's second IAM user the same way | Drecoder | 2026-11-05 | **Done 2026-11-03**: unused, no password, no keys; being deleted |
| **Prevent, management account:** every permission set denies creating users, access keys and console passwords, and re-activating a key (added 2026-11-03; service control policies never apply to a management account, F-0020) | Drecoder | 2026-11-05 | **Done 2026-11-03**, shown to fail |
| **Prevent (enforcement), workload accounts:** a service control policy on the workload OU that denies creating IAM users and access keys, with one documented break-glass path; applied by Genesis from the governance baseline, once a member account is vended | platform | With the first member account | Open (F-0016) |
| **Detect (the missing signal):** AWS Config rules `access-keys-rotated`, `iam-user-mfa-enabled`, and `iam-user-unused-credentials-check`, with findings routed as alerts. Detection only: an alert neither removes a key nor limits it | platform | With the organization | Open |
