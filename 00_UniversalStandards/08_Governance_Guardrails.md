# Governance Guardrails

*Governance comes before everything. The cloud's control plane enforces the platform's limits, so
no service, agent, or person can step outside them, whatever path a change takes.*

This standard defines the guardrails every cloud account and project lives under. The playbook
owns **what** the guardrails are. Genesis owns **how** each cloud enforces them. Services are built
**inside** them. The enforceable subset is in `AGENTS.md` → **Governance Rules**, and the
machine-readable baseline is `schemas/governance_baseline.v1.json`.

---

## 1️⃣ Where Governance Sits

```text
Engineering Excellence Playbook   what the guardrails are   (GOV-* controls, this doc + baseline contract)
        │  vendored as .playbook/schemas/governance_baseline.v1.json
        ▼
Genesis                           how each cloud enforces them   (GCP org policies, AWS SCPs, hierarchy, vending)
        │  every account and project is created under the guardrails
        ▼
Services and platform stacks      built inside them   (sovereign-vpc, inference, agents, apps)
```

- **The playbook never implements a cloud control**, and Genesis never invents one. A guardrail
  that is not in the baseline is not enforced. A control in the baseline that Genesis does not
  implement for a cloud is a visible gap, not a silent one.
- **Services never manage guardrails.** A service repo cannot create, change, or except an org
  policy or SCP. It asks for an exception through Genesis (§6).

---

## 2️⃣ Guardrails vs `SEC-*` Policies

Two layers, both required. Each assumes the other can fail.

| | `SEC-*` policies | `GOV-*` guardrails |
| :--- | :--- | :--- |
| Enforced by | rig-scan and CI gates, on the plan | The cloud control plane (GCP Organization Policy, AWS SCPs) |
| When | Before merge | On every API call, forever |
| Catches | Bad code in a pull request | Anything that skips the pull request: console clicks, a third-party agent, a stolen credential, a misconfigured pipeline |
| Fails | Closed: the change is blocked | Closed: the API call is denied |
| Lives in | `07_Security_In_Depth.md` §10 | This doc and `schemas/governance_baseline.v1.json` |

Where a control exists in both layers, the baseline names the matching `SEC-*` id, so a finding in
CI and a denial in the cloud point at the same rule.

---

## 3️⃣ Resource Hierarchy

Guardrails attach to the hierarchy, never to individual projects or accounts, so everything created
later inherits them without anyone remembering to.

| Node | GCP | AWS | Holds |
| :--- | :--- | :--- | :--- |
| Root | Organization | Organization root | The baseline guardrails |
| `governance` | Folder | OU | Genesis's own project or account, the central audit log sink |
| `platform` | Folder | OU | Shared platform stacks (VPC shell, CI runners, inference, observability) |
| `dev` / `staging` / `prod` | Folders | OUs | Service projects or accounts, one per service per environment |

- **No project or account lives outside the hierarchy.** A standalone project inherits no
  guardrails, so it is a finding, not a configuration.
- Environment nodes may tighten the baseline (e.g. `prod` enforces controls that `dev` runs in dry
  run), never loosen it.

---

## 4️⃣ The Baseline Controls

Each control states the intent once, then how each cloud enforces it. The contract
(`schemas/governance_baseline.v1.json`) carries the exact constraint names and SCP statements.

| Control | Intent | GCP | AWS | `SEC-*` |
| :--- | :--- | :--- | :--- | :--- |
| `GOV-001` | No default networks; every network is declared in IaC | `compute.skipDefaultNetworkCreation` | Default VPCs deleted at account vending | — |
| `GOV-002` | No long-lived workload keys | `iam.disableServiceAccountKeyCreation`, `iam.disableServiceAccountKeyUpload` | SCP denies `iam:CreateAccessKey` | `SEC-004` |
| `GOV-003` | No VM directly reachable from the internet | `compute.vmExternalIpAccess` (deny all) | SCPs deny public IPs at launch, Elastic IP association, and internet gateways outside the platform network role | — |
| `GOV-004` | Storage is never public | `storage.publicAccessPrevention` | S3 account Block Public Access; SCP denies changing it | `SEC-002` |
| `GOV-005` | Access to storage is IAM-only, no ACLs | `storage.uniformBucketLevelAccess` | S3 Object Ownership `BucketOwnerEnforced` at vending | `SEC-002` |
| `GOV-006` | Resources only in approved regions | `gcp.resourceLocations` | SCP denies `aws:RequestedRegion` outside the list; global-service exclusions come from AWS's maintained reference SCP, not a hand-kept list | — |
| `GOV-007` | Access only for identities in the platform's own directory | `iam.allowedPolicyMemberDomains` | SCP denies RAM shares to external principals; `aws:PrincipalOrgID` checked at plan time | — |
| `GOV-008` | VMs cannot act as routers | `compute.vmCanIpForward` (deny all) | SCP denies disabling `SourceDestCheck` | — |
| `GOV-009` | No network side channels between projects | `compute.restrictVpcPeering` (deny all) | SCP denies `ec2:CreateVpcPeeringConnection` | — |
| `GOV-010` | Audit logging cannot be disabled | Org-level audit config + org log sink | SCP denies `cloudtrail:StopLogging` / `DeleteTrail` | `SEC-009` |
| `GOV-011` | No automatic Editor grants to default service accounts | `iam.automaticIamGrantsForDefaultServiceAccounts` | — (no equivalent) | `SEC-005` |
| `GOV-012` | Interactive VM access goes through IAM | `compute.requireOsLogin` | SSM Session Manager only; SCP denies EC2 key pairs and `ec2-instance-connect:SendSSHPublicKey` | — |
| `GOV-013` | Guardrails cannot be changed or escaped from inside | Only the governance identity holds Org Policy Administrator | SCP denies `organizations:LeaveOrganization` and changes to governance roles | — |

Controls marked `—` for a cloud are recorded as `not_applicable` in the contract, with the reason.

### What a control guarantees, and what it does not

A control enforces one narrow invariant. Reading it as a broader security outcome is how a false
sense of security starts. For example, `GOV-003` keeps VMs off the internet, but a load balancer can
still be public. `GOV-004` keeps buckets from being public, but an authorized identity with
over-broad access can still leak the data.

So every control in the contract states both:

- `guarantees`: the exact invariant the cloud enforces.
- `does_not_guarantee`: the outcome it is most often mistaken for, and which other control or
  practice covers it.

When a control's description and its `guarantees` disagree, `guarantees` wins and the description
is the bug.

---

## 5️⃣ Rollout: Dry Run, Then Enforce

A guardrail that breaks running stacks on day one gets disabled on day two. The contract's `mode`
is each control's **target**, and Genesis reaches it in two steps:

1. **Stage in dry run.** Every new or changed control is first applied in dry run: violations are
   logged (GCP Organization Policy dry run; AWS SCP attached to a test OU first) and nothing is
   blocked.
2. **Promote to the target.** Once the dry-run log shows no violations, or every violation has an
   approved exception, **and** the control's conformance test passes for that cloud (§5a), a
   reviewed Genesis change promotes the control to its target mode.

- A target of `enforce` means the control blocks once staged. A target of `dry_run` means the
  control stays in dry run until a prerequisite is met (a parameter, an exception), which the
  contract notes.
- The target per control lives in the contract, so changing it is a reviewed change in the
  playbook, not a click in a console.
- New projects and accounts get every `enforce` control from their first API call.
- A control never moves back from `enforce` to `dry_run` to unblock a change. That is what
  exceptions are for.

### 5a. Conformance tests: proof the cloud enforces it

A policy that looks right but does not match the cloud's authorization semantics is worse than no
policy, because everyone believes it holds. A plan, a lint, or a review cannot prove enforcement;
only the cloud API can.

- Genesis keeps a **conformance test per control per cloud**, run against a dedicated test project
  or account in the test folder or OU. It attempts the forbidden action through every known path
  (e.g. `GOV-003` on AWS: launch with and without a launch template, attach an Elastic IP to a
  network interface, launch into a subnet that maps public IPs) and asserts the API **denies** it.
- Each test also performs one **allowed** action nearby, so a control that blocks too much fails
  too.
- The contract records the result per cloud in `verified`. Genesis sets it to `true` only from a
  passing test run, and a control is not promoted to `enforce` on a cloud where `verified` is
  `false`.
- Conformance tests rerun on every Genesis change and on a schedule, because cloud authorization
  semantics change underneath policies.
- The contract is validated against `schemas/governance_baseline.v1.schema.json` in the playbook's
  CI and again by Genesis before it reads the baseline. An invalid baseline is rejected, not
  repaired.

---

## 6️⃣ Exceptions

Some workloads need what a guardrail denies, e.g. peering for a managed database's private IP
(`GOV-009`).

- Exceptions live in Genesis, in a reviewed exceptions file, never in a service repo.
- Every exception names the control, the **narrowest scope** that works (one project or account,
  never a folder or OU unless every project in it needs it), an **owner**, a **reason**, and an
  **expiry date**.
- An expired exception is removed by the next Genesis plan. Renewing it is a new review.
- Exceptions are listed on the governance dashboard, so the size of the exception list is visible.

---

## 7️⃣ The Governance Identity

Changing guardrails is the most powerful action on the platform, so it gets its own identity.

- **One identity, used only by Genesis's apply pipeline**, holds Organization Policy Administrator
  (GCP) or the SCP management permissions (AWS). No other pipeline, service, agent, or person holds
  them day to day.
- It is federated and short-lived like every workload identity (`07_Security_In_Depth.md` §4), and
  its trust policy pins the Genesis repo, `main`, and the `governance` environment.
- Every Genesis change merges with **human approval**. Agents may propose governance changes; they
  never apply them (`06_AgentZone/01_Agent_Standards.md`).
- Break-glass access to the organization exists, is alerted on (`07_Security_In_Depth.md` §9), and
  is reviewed after every use.

---

## 8️⃣ Vending: Spinning Up Services Inside the Guardrails

Governance is what makes new services fast and safe. A new service does not design its own
security; it is **vended** into a place where the security already exists.

Genesis vends a project (GCP) or account (AWS) for a service from a short, reviewed request:

| Input | Example |
| :--- | :--- |
| Service name | `scan-engine` |
| Environment | `dev` |
| Owner | `platform` |
| APIs or services it needs | `run.googleapis.com`, `secretmanager.googleapis.com` |

What the service gets, with no extra work:

- A project or account in the right environment folder or OU, inheriting every `GOV-*` guardrail.
- Required labels or tags (`env`, `owner`, `service`, `managed_by=terragrunt`), billing, and only
  the requested APIs enabled.
- Its CI identity: federated, pinned to the service's repo, plan and apply split
  (`07_Security_In_Depth.md` §4).
- Attachment to the platform network and telemetry (the shell VPC, the observability stack), not a
  network of its own.

The service repo then holds only the service's own Deployment Units.

---

## 9️⃣ Audit and Drift

- Genesis runs a scheduled plan against the live organization. Any drift (a policy changed outside
  Genesis, a project outside the hierarchy, a default network) is a finding routed like any other.
- Policy changes, exception use, and dry-run violations are logged centrally and alerted on
  (`07_Security_In_Depth.md` §9).
- Metrics: `governance_controls_total{mode}`, `governance_dry_run_violations_total{control}`,
  `governance_exceptions_active{control}`, `governance_drift_findings_total`.

---

## Principle

Guardrails are set once, at the top, and inherited by everything below. A service is fast to build
because it never has to rebuild the guardrails, and safe because it cannot step outside them.
