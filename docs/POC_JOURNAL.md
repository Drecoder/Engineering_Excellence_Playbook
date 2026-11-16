# Proof-of-Concept Journal

*What applying the playbook actually found, in the order it was found, each written up as a
compact post-mortem.*

This journal is the factory's working record of proof. Each entry is a finding the playbook's rules
surfaced in real work: a defect, a gap between a written rule and what runs, or a check shown to
work. It feeds each program increment's re-grade (`docs/PROGRAM_INCREMENTS.md`) and the case study.

## Three Roles, One Document

The journal is one living document with three functions. Each is for a different reader, and all
three feed the same loop: the playbook sets a standard, work tests it, the journal records what
happened, and what it records changes the standard, the controls, and the next piece of work.

| Role | Status | For | What it gives them | How they read it |
| :--- | :--- | :--- | :--- | :--- |
| **Engineering artifact** | **In use** | Engineers and reviewers | The chronological, evidence-linked history of findings, corrections, verification, and unresolved work, so the project's actual state does not have to be rebuilt from Git history | The entries in order; the [CAPA register](FINDINGS_REGISTER.json) for what is open, its severity, and its deadline |
| **Learning resource** | Designed, not yet wired | People learning the craft, through a learning system | Engineering experience turned into causal knowledge: what failed, why, how it was detected, how the fix was verified, and what now prevents it | Each entry's CAPA fields as a lesson; the register's category and severity to group and order lessons |
| **Feedback mechanism** | Designed, not yet wired | The factory's agents and future engineering decisions | Prior experience to weigh against the playbook's standards and the current evidence, so the variance between what a rule says, what happened before, and what is happening now is visible | The register as structured data (category, severity, status, residual); the entries it points to, as the reasoning behind each row |

**Status, honestly:** the engineering artifact is in use. The learning resource and the feedback
mechanism are designed but not yet wired: no learning system reads the journal yet, and no agent
is given it yet. When agents are, they will receive a slice relevant to their task, never the whole
journal, as with every other piece of context (`AGENTS.md` → Reuse Rules). The structure is already
ready for all three, though only the first is served: CAPA fields in every entry, and a register
with the same rows as machine-readable data.

## Format: CAPA

Every entry follows **CAPA** (Corrective and Preventive Action), the quality-management form of a
post-mortem: fixing the instance is not enough; the cause is found and the recurrence prevented.

| Field | Answers |
| :--- | :--- |
| **Rule** | Which playbook rule applied |
| **Problem** | What was wrong, and its impact |
| **Detection** | How it was found, and whether a control or a person found it |
| **Root cause** | Why it happened, not just what broke |
| **Correction** | The immediate fix to this instance |
| **Preventive action** | What stops it happening again: a check, a signal, or a rule |
| **Verification** | Proof that the correction and the preventive action work |
| **Evidence** | Pull requests, commits, workflow runs, reports, incident records |
| **Status** | Open, fixed, or proven |

A failure also gets a full post-mortem in the affected repository's `docs/incidents/`
(`00_UniversalStandards/03_Post_Mortem_Template.md`); its entry here is the compact CAPA that points
to it. Entries are added, never rewritten; a later entry corrects an earlier one. (On 2026-10-29
the first seven entries were restated in this format; their facts did not change.)

This file is the journal until the notepad runs (`06_AgentZone/07_Agent_Notepad.md`); then the
journal moves into the notepad's filing system, where each entry is a sealed, hash-chained record.

## The CAPA register: risk, deadlines, and closure

The journal is the immutable record; the **[CAPA register](FINDINGS_REGISTER.json)** is each
finding's living status: one row per entry, with its category, severity, due date, status, closure
date, verification, and the references the CAPA graph reads: rules, components, fingerprints,
and recurrences (contract `schemas/findings_register.v2.schema.json`). CI checks both on
every pull request and every day.

| Severity | Means | Deadline |
| :--- | :--- | :--- |
| **Critical** | An exploitable security exposure, or a control that admits what it must refuse | 7 days |
| **High** | A control that silently does not run or checks nothing, or a governance gap that removes a guardrail | 30 days |
| **Medium** | A defect or a missing proof, with a working control around it | 90 days |
| **Low** | Maintainability or reuse | 180 days |

- **Deadlines are mandatory.** A due date past its severity's deadline is refused, and an open
  finding past its due date fails the daily run.
- **Control effectiveness is measured.** Every run's summary reports the share of control classes
  proven to fail on their defect, the share of findings recorded as caught by a control rather than
  a person (the register's `detected_by`, set by hand for each finding, not derived from evidence),
  open findings by severity, and days to close.
- **Governance closes before production.** Production readiness is false while any critical or
  high security or governance finding is open; no production operation until it is true.

The register was introduced on 2026-10-29. Findings F-0001 to F-0016 were ranked then,
retroactively: each deadline counts from the day the finding was originally recorded, and their
journal entries are unchanged.

---

## 2026-10-28: The prototype never produced any audio

- **Rule:** a refactor proves it changed no behavior before it changes any (the narration job's
  Phase 1 exit check: same audio).
- **Problem:** the text-to-speech prototype had never written an MP3 for any slide, and nothing
  said so.
- **Detection:** the equivalence check, run on the prototype and the refactored pipeline: both
  failed every slide in the same way.
- **Root cause:** the `vctk/vits` model is multi-speaker and refuses a request without a speaker.
  Each failure was caught per slide and the job still exited 0, so a run that produced nothing
  looked like a success.
- **Correction:** a default speaker.
- **Preventive action:** exit codes are now the contract (1 when any slide fails, 2 when the job
  cannot start), and the equivalence check compares decoded audio and MP3 bytes for every slide,
  applying the same one-line fix to a copy of the verbatim prototype.
- **Verification:** the Phase 1 exit check passes; 7 unit tests at the time, 25 later.
- **Evidence:** coqui-tts `fd4d39c`, `57e51ba`; `reports/phase1-equivalence-20261028T061544Z.json`.
- **Status:** fixed.

## 2026-10-28: A model loader that writes broke on a read-only root

- **Rule:** containers are stateless with a read-only root filesystem (`AGENTS.md` → Container
  Rules).
- **Problem:** the job crashed when run as the cloud will run it.
- **Detection:** the hardened run script: read-only root, no network, no capabilities.
- **Root cause:** loading the model by name goes through a manager that rewrites `config.json` on
  every load. The job had only ever run with a writable filesystem.
- **Correction:** the model loads by path from the image.
- **Preventive action:** the job is always run hardened (`scripts/run.sh`), the same way locally and
  in the cloud.
- **Verification:** hardened run: 4 of 4 slides saved, exit 0; a rerun skips all 4.
- **Evidence:** coqui-tts `57e51ba`.
- **Status:** fixed.

## 2026-10-28: A CRITICAL CVE in the speech engine's runtime

- **Rule:** CRITICAL or CISA KEV blocks (`AGENTS.md` → Security Rules).
- **Problem:** CVE-2025-32434, code execution through `torch.load`, in the shipped torch 2.4.1.
- **Detection:** Trivy on the runtime image.
- **Root cause:** the pin predated the fix, and the central gate scanned only the repository's
  files, not the built image, where the engine actually lives.
- **Correction:** torch 2.6.0.
- **Preventive action:** the image is scanned on every pull request (first in the repository's own
  CI, now in the central gate's image job).
- **Verification:** Trivy no longer reports it. The new numerics change the audio bytes, so
  equivalence is held where it matters: the prototype and the pipeline on the same torch still
  match exactly.
- **Evidence:** coqui-tts `4ce148f`; `reports/phase1-equivalence-20261028T080820Z.json`.
- **Status:** fixed.

## 2026-10-28: The license gate found no licenses

- **Rule:** licenses are checked against a reviewed policy (`AGENTS.md` → Supply Chain Rules);
  verified means run.
- **Problem:** the new license gate would have passed every repository while checking nothing:
  against a TypeScript repository it found 19 "packages", none of them the npm dependencies.
- **Detection:** running the gate against a real repository before merging it.
- **Root cause:** a directory scan reads lockfiles and manifests by default, and they carry no
  license metadata; the 19 were GitHub Actions and Go modules vendored inside `node_modules`.
- **Correction:** each stack scans what it actually installed (an installed-package cataloger per
  stack).
- **Preventive action:** a gate check counts only after it has run on real repositories and on a
  designed-to-fail case (a denied-license fixture).
- **Verification:** agent-notepad: 130 packages, every one with a license; compliance-authority: 33,
  with no vendored noise.
- **Evidence:** sovereign-vpc-gcp #31, `e323a06`.
- **Status:** fixed.

## 2026-10-28: The license gate carried a copy of the contract

- **Rule:** contracts have one home; a second copy of contract logic is forbidden (`AGENTS.md` →
  Reuse Rules).
- **Problem:** the gate re-implemented the playbook's reference license evaluator inline, so two
  implementations could drift apart.
- **Detection:** review of the new gate.
- **Root cause:** copying was the quick way to get the evaluator into the gate; nothing flagged it.
- **Correction:** the gate fetches the playbook's evaluator at a pinned commit and imports it.
- **Preventive action:** the contract's test vectors are replayed on every run before any verdict
  counts, so an evaluator that disagrees with its own contract stops the gate.
- **Verification:** the same verdicts on agent-notepad; the denied-license fixture still blocks.
- **Evidence:** sovereign-vpc-gcp #31, `8a6a506`.
- **Status:** fixed.

## 2026-10-28: Telemetry code copied across services

- **Rule:** extract on the third copy (`AGENTS.md` → Reuse Rules).
- **Problem:** the TypeScript telemetry setup exists in three services (Builder, Reviewer,
  notepad); the Python setup is in two, and a third would follow.
- **Detection:** review.
- **Root cause:** each service set up telemetry before there was a home for shared packages.
- **Correction:** none yet.
- **Preventive action:** decide where shared packages live, then extract.
- **Verification:** pending.
- **Status:** open.

## 2026-10-28: An image scan that ran out of disk passed for the expected CVE block

- **Rule:** read every red check's log (`AGENTS.md` → CI Rules).
- **Problem:** for 16 hours the image was not scanned at all, and nobody knew.
- **Detection:** a person reading the log of a check everyone expected to be red.
- **Root cause:** the job needs about 11 GB at its peak and a hosted runner starts with 13 GB free,
  with the test image and build cache still on disk. The failed check carried no reason, and the
  pull request had predicted a red check, so the real failure looked like the expected one.
- **Correction:** delete unused toolchains and prune before the scan.
- **Preventive action:** every central gate job starts with a need-based disk preflight and reports
  its low point, warning under 5 GB; every red check's log is read.
- **Verification:** run 40808933067 measured the need (low point 21 GB); the preflight's cases pass
  on a real runner, including one that must fail.
- **Evidence:** coqui-tts INC-001; runs 40656484883, 40808933067; sovereign-vpc-gcp #35.
- **Status:** fixed and measured.

## 2026-10-28: The central gate type-checked tests before installing pytest

- **Rule:** the factory tests itself; a skipped job is not a pass (`AGENTS.md` → CI Rules).
- **Problem:** any Python repository whose pytest is not a runtime dependency failed the gate; the
  fix then merged before its code path had run anywhere.
- **Detection:** a consumer's red gate (coqui-tts #1).
- **Root cause:** step order: mypy ran before the test step installed pytest. The two other Python
  repositories listed pytest as a runtime dependency, which hid it. The factory repository has no
  Python, so its own gate skipped the changed job, and a skipped job looked like a pass.
- **Correction:** pytest is installed before lint (sovereign-vpc-gcp #32).
- **Preventive action:** a Python fixture, run by a self-test in both job layouts on every gate
  change (sovereign-vpc-gcp #33).
- **Verification:** the fixture fails on the old gate (run 40808542665) and passes on the fixed one
  (run 40808502279).
- **Evidence:** sovereign-vpc-gcp INC-007.
- **Status:** fixed; the fixture proves it.

## 2026-10-29: A CRITICAL CVE removed at its source, not excepted

- **Rule:** an image finding is fixed at its source, never excepted (`AGENTS.md` → Container Rules).
- **Problem:** CVE-2026-6653 (libxml2, CRITICAL, no Debian fix) blocked the image.
- **Detection:** the image scan. A time-boxed exception was written first, then rejected as a
  workaround.
- **Root cause:** Debian's ffmpeg links about 60 optional libraries, libxml2 among them; the job
  uses only WAV, MP3, and LAME.
- **Correction:** a minimal ffmpeg built from the pinned upstream source.
- **Preventive action:** a daily check that fails when Debian's security release moves past the
  version the source build matches (scanners cannot see a source build); image findings take no
  exceptions.
- **Verification:** all 16 MP3s byte-identical to the Debian build; image findings 749 → 214,
  CRITICAL 1 → 0.
- **Evidence:** coqui-tts #1, #2; `reports/phase1-equivalence-20261029T022705Z.json`.
- **Status:** fixed.

## 2026-10-29: The central gate's checks proven to fail

- **Rule:** each check is shown to fail on the defect it guards against before it counts.
- **Problem:** a check that has never failed may not be checking anything.
- **Detection:** the INC-007 review.
- **Root cause:** checks were shown to pass, never to fail.
- **Correction:** throwaway pull requests that reintroduce each defect.
- **Preventive action:** the rule above, in `AGENTS.md` → CI Rules, and the self-test on every gate
  change.
- **Verification:** the pre-fix gate fails the Python fixture (sovereign-vpc-gcp #34); a CRITICAL
  base image fails the image scan (#37); the disk preflight's unmeetable need fails on a real
  runner (#35).
- **Status:** proven.

## 2026-10-29: A public repository could not call the private gate

- **Rule:** every repository calls the central gate by full commit SHA (`AGENTS.md` → CI Rules).
- **Problem:** Genesis had no gate at all: its gate run failed to start.
- **Detection:** the run's "workflow file issue" on Genesis #3.
- **Root cause:** a public repository cannot call a private reusable workflow, and the factory's
  repositories had mixed visibility. The caller also pinned `@main`, and nothing checked pins.
- **Correction:** Genesis made private; its caller pinned to a full SHA.
- **Preventive action:** one visibility for the whole factory (private), the playbook alone public.
- **Verification:** the gate now runs on Genesis. It is red on legacy code, which the agent loop
  takes to green as the first real workload.
- **Evidence:** Genesis #3.
- **Status:** fixed.

## 2026-10-29: A cloud project outside the organization

- **Rule:** every cloud project lives in the governance hierarchy; a standalone project is a
  finding (`AGENTS.md` → Governance Rules).
- **Problem:** the project that holds the CI runners and their state has no parent organization,
  so no organization policy applies to it.
- **Detection:** checking where the registry could live.
- **Root cause:** the project predates the organization, and nothing lists projects outside it.
- **Correction:** none yet.
- **Preventive action:** new infrastructure goes into projects Genesis vends inside the
  organization; a check that lists projects without a parent.
- **Verification:** pending.
- **Status:** open.

## 2026-10-29: A long-lived administrator key on a standalone AWS account

- **Rule:** SSO with MFA, never static keys (`AGENTS.md` → Security Rules); every account lives in
  the governance hierarchy.
- **Problem:** the workstation's AWS profile used an IAM user's access key, about eleven months
  old, with administrator access and no MFA, on an account in no organization.
- **Detection:** a coding assistant checking the toolchain's identity before the first live-agent
  run; no control reported it.
- **Root cause:** the move to single sign-on was started but not finished, and nothing checks
  identities against the rule.
- **Correction:** none yet; the actions are the owner's.
- **Preventive action:** AWS Config rules for key age, MFA, and unused credentials, routed as
  alerts; the governance baseline once the account is in the organization.
- **Verification:** pending.
- **Evidence:** INC-002.
- **Status:** open.

## 2026-10-29: The journal's append-only rule was not enforced

- **Rule:** every finding is journaled, and entries are added, never rewritten (`AGENTS.md` →
  Observability Rules).
- **Problem:** the rule was a sentence. Any pull request could edit, delete, or reorder entries, and
  nothing would notice.
- **Detection:** an external review of the journal.
- **Root cause:** the rule was written before any check for it existed, and the notepad's sealed
  records, which would enforce it, are not running yet.
- **Correction:** a check that compares the journal before and after every change: base entries
  must stay byte for byte, in order, and new ones may only follow them
  (`tests/journal/journal_append_only.py`).
- **Preventive action:** it runs on every pull request and every push to `main`, in a Python image
  pinned by digest (`.github/workflows/journal.yml`), with a fixture for each allowed and each
  forbidden change.
- **Verification:** 14 tests pass; a checker broken to allow everything fails 6 of them; the real
  journal passes against itself and this entry's own pull request passes it (run 40904223442),
  while a pull request that edits an existing entry fails with `entry edited` (#43, run
  40904315387).
- **Limitation:** this enforces the rule for changes that go through pull requests. It does not make
  the journal immutable: anyone who can bypass branch protection or edit the workflow can still
  rewrite history, and until branch protection is on, a direct push is only detected (the run on
  `main` turns red), not prevented. Immutability waits for the notepad's hash-chained records.
- **Evidence:** `.github/workflows/journal.yml`, `tests/journal/`.
- **Status:** enforced on pull requests; immutability open.

## 2026-10-29: The source-built ffmpeg is watched by version only

- **Rule:** a component built from source is invisible to scanners, so it is pinned by checksum and
  tracked against its upstream security channel (`AGENTS.md` → Supply Chain Rules).
- **Problem:** the daily check compares the version with Debian's security release, and nothing
  else. It would miss an advisory against FFmpeg 7.1.5 that Debian has not shipped, a change in our
  build configuration, and the built binary itself. The 16 byte-identical MP3s prove the output is
  equivalent for those inputs, not that the build is equally secure.
- **Detection:** an external review.
- **Root cause:** the check was designed to replace Debian's package tracking, and Debian's version
  is only one signal of it.
- **Correction:** none yet.
- **Preventive action:** the daily run also looks up advisories for FFmpeg at the pinned version,
  and CI records and verifies the build's configure flags and the binary's checksum.
- **Verification:** pending.
- **Evidence:** coqui-tts `.github/workflows/ffmpeg-current.yml`, `749889f`.
- **Status:** open.

## 2026-10-29: INC-002's prevention was only an alert

- **Rule:** a preventive action prevents; detection alone is not prevention (CAPA). Never static
  keys (`AGENTS.md` → Security Rules).
- **Problem:** INC-002's preventive action was a set of AWS Config rules. They report a long-lived
  key; they neither remove it nor limit what it can do.
- **Detection:** an external review.
- **Root cause:** the prevention was written as detection.
- **Correction:** INC-002 now names enforcement: once the account is in an organization, a service
  control policy that denies creating IAM users and access keys, with one documented break-glass
  path; the Config rules stay, as detection.
- **Preventive action:** each preventive action in an incident record states whether it prevents
  or detects.
- **Verification:** pending; the organization does not exist yet.
- **Evidence:** INC-002.
- **Status:** open.

## 2026-10-29: Findings had no risk ranking or deadline

- **Rule:** a finding is closed by verified correction and prevention (CAPA); regulated quality
  systems also require risk ranking, remediation timelines, measured control effectiveness, and
  governance closure before production.
- **Problem:** six findings were open with no severity and no deadline, nothing measured whether
  the controls work, and nothing stopped production operation with a critical finding open.
- **Detection:** an external review placing the journal against regulated-industry practice.
- **Root cause:** the CAPA format recorded each finding's content but not its risk or its time, and
  the journal, being append-only, cannot carry a status that changes.
- **Correction:** the CAPA register (`docs/FINDINGS_REGISTER.json`, contract
  `findings_register.v1`): one row per journal entry, with a category, a severity on a written
  rubric, a due date, status, closure, and verification, plus the gate's control classes and
  whether each is proven.
- **Preventive action:** CI checks that every journal entry has a row and every due date is within
  its severity's deadline (critical 7 days, high 30, medium 90, low 180); an overdue open finding
  warns on pull requests and fails the daily run; every run reports the control-effectiveness
  metrics and production readiness, which is false while any critical or high security or
  governance finding is open.
- **Verification:** 29 tests pass, and four broken versions of the rules (no deadline check,
  always ready, overdue never fails, no row check) each fail them; the contract tests pass with
  the toolchain's pins. CI run 40905982806 reports 17 findings, 6 open, 5 of 13 control classes
  proven, 6 of 17 findings caught by a control, and production ready: no (the AWS key, the cloud
  project, INC-002's prevention). The daily failure on an overdue finding is proven by test, not
  yet by a real overdue run.
- **Evidence:** `docs/FINDINGS_REGISTER.json`, `tests/journal/register.py`,
  `schemas/findings_register.v1.schema.json`.
- **Status:** fixed.

## 2026-10-29: The journal's controls run on main, and earlier findings were ranked

- **Rule:** a control counts only when it is enforced and running on `main` (`docs/PROGRAM_INCREMENTS.md`).
- **Problem:** the append-only check and the CAPA register had passed only on their own pull
  requests, and the 16 findings recorded before the register existed had no severity or deadline.
- **Detection:** merging them (#42, #44) and checking the runs on `main`.
- **Root cause:** a control proven on a pull request is not yet a control on `main`, and the
  register postdated the findings it tracks.
- **Correction:** #42, #44, and #38 merged; findings F-0001 to F-0016 ranked retroactively in the
  register, each deadline counted from the day the finding was originally recorded. Their journal
  entries are unchanged, as the append-only rule requires.
- **Preventive action:** every push to `main` runs the journal check and the register check, and
  the register check runs daily.
- **Verification:** on `main`, the journal check passed at `f2d8897` (run 40906894231); the journal
  and register checks at `c256d28` (run 40907358453) and the contract tests (run 40907358223);
  and at `4c7d901` (run 40907978656): 17 entries kept, 5 findings open, 5 of 13 control classes
  proven, production ready: no.
- **Evidence:** #42, #44, #38; the runs above.
- **Status:** proven.

## 2026-10-29: The control-catch metric measures a recorded attribution

- **Rule:** a claim counts only as far as its evidence goes: the playbook's principle that a rule
  counts only when it is enforced and running (`docs/PROGRAM_INCREMENTS.md`), applied to a metric.
- **Problem:** the register reports the share of findings "caught by a control rather than a
  person" (6 of 18 on `main`). That number counts the register's `detected_by` field, which is set
  by hand for each finding; nothing checks it against the entry's detection evidence. It measures
  recorded attribution, not verified detection effectiveness.
- **Detection:** review of PR #46's wording before merge.
- **Root cause:** the metric was defined from a field that is easy to record and hard to verify,
  and the wording described what the field means rather than how it is set.
- **Correction:** the README and the journal's preamble now say the share is "recorded as caught by
  a control", an attribution recorded by hand (#46, `f7f9410`); the run summary's label says the
  same; F-0017's register row carries the limitation as a residual. F-0017's own entry keeps its original wording, as the append-only rule
  requires.
- **Preventive action (planned, not implemented):** a finding attributed to a control will have to
  name the control (its id in the register's control list), the run that reported it, and the line
  in that run's output that reports this defect. The register check will look the run up and refuse
  the attribution unless that run failed in that control's job and its output contains the line.
  Even then, it shows that the control reported this defect in that run, not that the control
  catches every instance; that is what each control's designed-to-fail proof is for. Until this is
  implemented and tested, the share stays labelled as an unverified attribution.
- **Verification:** pending: the preventive action, once implemented, needs a case that must fail
  (a control attribution with no run, or with a run that did not fail) and one that must pass.
- **Evidence:** #46; the register check's output on `main`.
- **Status:** open until the preventive action is implemented and that verification passes.

## 2026-11-03: The planned key guardrail would not have reached the account it guards

- **Rule:** a preventive action prevents (CAPA), and a guardrail counts only when it is shown to
  fail on its defect (`AGENTS.md` → CI Rules); every account lives in the governance hierarchy.
- **Problem:** INC-002's enforcement was planned as a service control policy denying IAM users and
  access keys. Turning on the sign-in directory made the only AWS account the organization's
  management account, and service control policies never apply to a management account. The
  planned guardrail would have been attached, looked right, and denied nothing.
- **Detection:** reviewing the plan while closing F-0013, before the policy was written.
- **Root cause:** the plan assumed the guarded account would be a member account; the playbook's
  hierarchy did not say where the management account sits or what guards it.
- **Correction:** the owner's permission set now carries an explicit deny on creating users, access
  keys and console passwords, and on re-activating a key. Shown to fail: creating a user returned
  `AccessDenied` (explicit deny in an identity-based policy).
- **Preventive action:** the governance standard now says the management account runs nothing and,
  until a member account is vended, is guarded by permission sets
  (`00_UniversalStandards/08_Governance_Guardrails.md` §3); people sign in through the directory and
  never have IAM users (`03_InfrastructureZone/01b_AWS_Specifics.md`). Workloads move to a vended
  member account, where the service control policy does apply (F-0016).
- **Verification:** the `AccessDenied` result above, 2026-11-03; the service control policy itself
  is proven when the member account exists.
- **Evidence:** the permission set's inline policy; the denied `iam:CreateUser` call; this branch.
- **Status:** fixed for the management account; the member-account guardrail is tracked by F-0016.

## 2026-11-08: The orchestrator's fence survived dropping its token check

- **Rule:** a passing suite counts only if its tests could fail, and a surviving mutant on a
  critical path is a finding (`00_UniversalStandards/14_Test_Quality.md` §3); leases decide who may
  act, so the fence is a critical path.
- **Problem:** a hand mutant that fences board writes and pushes on the lease owner alone, without
  the token, passed all 30 tests on factory-orchestrator #2 (`e0ff447`). The fence's correctness
  then rests on owner IDs never repeating across runs, an invariant no test states.
- **Detection:** a hand-made mutant during the build session; a person, because no mutation gate
  runs in CI yet.
- **Root cause:** the stale-run tests (acceptance tests 6 and 7) change the token and the owner
  together, so no case holds the owner fixed and varies only the token; and the central factory
  has no mutation gate (StrykerJS is listed as To build in `17_Quality_Policy_Engine.md`).
- **Correction (planned):** a contract test where a lease held with token T2 and owner O refuses a
  write carrying the stale token T1 and the same owner O (KAN-14 item 9). Killing the mutant
  removes the need for an equivalence ruling.
- **Preventive action (planned):** a StrykerJS gate in the central factory (KAN-58), so a surviving
  mutant on a changed module is reported by a control, not found by a person.
- **Verification:** pending: the new test must fail against the owner-only mutant and pass against
  the real fence; KAN-58's fixture must fail on a surviving mutant.
- **Evidence:** factory-orchestrator #2 at `e0ff447`; KAN-14; KAN-58.
- **Status:** open.

## 2026-11-08: The board ticket's format had no contract

- **Rule:** contracts have one home, the playbook (`AGENTS.md` → Reuse Rules); work enters only as
  an approved spec (`AGENTS.md` → Agent Rules).
- **Problem:** the orchestrator's board port expects structured fields (title, task, acceptance
  criteria, scope, repository and base branch, approval), but nothing said how a Jira issue
  carries them. The Jira adapter, not yet built, would have invented the format, and a ticket
  written to a guessed format would be rejected or, worse, read wrongly.
- **Detection:** preparing the dry-run ticket (KAN-59); a person.
- **Root cause:** the MVP board path describes the trigger (the owner's move to Ready) but not the
  ticket's body (`06_AgentZone/03_Software_Factory_Intake.md`, `07_SoftwareFactory/01_Software_Factory.md`).
- **Correction:** the format is now written down: fixed `##` sections parsed strictly, with no
  custom fields, in `07_SoftwareFactory/01_Software_Factory.md` §3 (this change) and KAN-14.
- **Preventive action (planned):** the Jira adapter's contract tests: one rejection case per
  missing, empty, duplicated or malformed section, and KAN-59's real body as the valid case.
- **Verification:** pending until the adapter and its tests exist.
- **Evidence:** factory-orchestrator `src/ports.ts` (`BoardTicket`); KAN-14; KAN-59; this change.
- **Status:** open.

## 2026-11-09: The orchestrator's SLIs query metrics its code never emits

- **Rule:** telemetry ships with the first line of code, and evidence is telemetry (`AGENTS.md` →
  Observability Rules); the Build stage implements with telemetry from the first commit
  (`00_UniversalStandards/01_Deliverable_Lifecycle.md`).
- **Problem:** the orchestrator's design record defines its SLIs and SLO burn-rate alerts on
  metrics such as `orchestrator_dispatch_total`, but slice 1's code has no OpenTelemetry SDK and
  emits no metric, trace or log. Wired as it is, every alert would read an empty input.
- **Detection:** checking the build against the playbook before the real adapters; a person.
- **Root cause:** slice 1's acceptance tests cover the business rules only; nothing ties the metric
  names in a design record to what the code emits, so a record can promise signals the code never
  produces and every gate still passes.
- **Correction (planned):** telemetry before the real adapters: a shared `traced` wrapper, the RED
  metrics the design record names, and the Governor metrics (KAN-14 slice 2).
- **Preventive action (planned):** a test that a run of the acceptance suite emits every metric an
  SLI in the design record queries, so the record and the code cannot drift apart.
- **Verification:** pending: the test must fail on the code at `e0ff447` and pass once telemetry
  lands.
- **Evidence:** factory-orchestrator `design/service_design_record.v1.json`; `package.json` (no
  OpenTelemetry dependency) at `e0ff447`.
- **Status:** open.

## 2026-11-09: AWS infrastructure has no Terragrunt root or state backend to land in

- **Rule:** use Terragrunt to orchestrate Terraform, including bootstrap units (`AGENTS.md` → IaC
  Rules); AWS state lives in an S3 backend in a dedicated account
  (`03_InfrastructureZone/01b_AWS_Specifics.md`).
- **Problem:** Genesis's `bootstrap/aws` is bare Terraform (a VPC and the GitHub OIDC provider)
  with no remote state; its `environments/*/aws` files are empty; no `root.hcl` exists. The
  orchestrator's stores (lease and run tables, its role) and the messaging backbone (KAN-36) have
  nowhere to apply, so the dry run cannot reach real AWS.
- **Detection:** placing the orchestrator's stores unit; a person.
- **Root cause:** an ordering gap. Genesis's bootstrap slice is pending for the agent loop
  (`07_SoftwareFactory/01_Software_Factory.md` §3), and the agent loop's own AWS stores need that
  bootstrap first. No step in the plan runs first.
- **Correction:** none yet. The stores unit is drafted as a portable module and a staging unit that
  includes `root.hcl`; nothing is applied.
- **Preventive action (planned):** the owner decides whether the AWS bootstrap slice (state bucket,
  `root.hcl`, plan and apply identities) is built by hand as an MVP bench, later rebuilt by the
  agent loop as the workshop rules allow, and records the decision in this playbook.
- **Verification:** pending: a `terragrunt plan` of the bootstrap and of the stores unit in CI.
- **Evidence:** Genesis at `667eb1b` (`bootstrap/aws/main.tf`, empty `environments/staging/aws/`);
  KAN-14.
- **Status:** open.

## 2026-11-08: The branch-protection incident was never journaled

Rule: a merge to a protected branch needs a pull request and a human, enforced by branch protection with no bypass (AGENTS.md → Security Rules; INC-001).
Problem: the three repositories that hold the factory's main branches had no protection, so a direct push or an unreviewed merge was possible. INC-001 was recorded on 2026-10-26 and stayed open for thirteen days with no journal entry and no register row, so the production-readiness check did not see it.
Detection: a person, reviewing the build kickoff against the register.
Root cause: the incident record and the journal are written separately, and nothing requires one to name the other. The register check counts journal entries, not incident records.
Correction: an active ruleset "Protect Main Branch" with no bypass actors on the playbook (26828664), Genesis (26828926) and factory-orchestrator (26829160): a pull request is required, deletion and force pushes are blocked, and the gate checks are required.
Preventive action (planned, not implemented): an incident record names its journal entry, and the register check refuses an incident record that no entry names.
Verification: the three rulesets read back active, with an empty bypass list, on 2026-11-08. A direct push refused by the ruleset has not yet been shown, so this is fixed, not proven.
Evidence: docs/incidents/2026-10-26-INC-001-no-branch-protection.md; rulesets 26828664, 26828926, 26829160; factory-orchestrator PR #1.
Status: fixed.
Residual: approvals are 0 until agents act under their own identities; the designed-to-fail direct push is not yet run.

## 2026-11-08: A required check could be met by any app

Rule: a gate counts only as the required check from the central factory, and an agent cannot change its evaluator (AGENTS.md → Security Rules).
Problem: the six required checks on Genesis were created with source "Any source". A status with the same name, posted by any app installed on the repository, would have satisfied the check.
Detection: a person, reviewing the ruleset page before saving it.
Root cause: the ruleset page offered no GitHub Actions source for these checks, so the default was kept, and nothing checks the source of a required check.
Correction: all six checks set to integration_id 15368 (GitHub Actions) through the API. The read-back on 2026-11-08 shows 15368 on every one of them.
Preventive action (planned, not implemented): a check that reads each protected branch's ruleset and refuses any required check without integration_id 15368.
Verification: the ruleset read-back on 2026-11-08 (Genesis, 26828926). A designed-to-fail case has not been run, so this is fixed, not proven.
Evidence: rulesets 26828926, 26828664, 26829160.
Status: fixed.
Residual: a later edit in the ruleset page can reset the source, and Genesis's page cannot select GitHub Actions.

## 2026-11-08: The design record had no gate

Rule: every service has a design record, valid against service_design_record.v1 and passing design_record_rules.v1 (AGENTS.md → Application Architecture Rules).
Problem: the central gates do not validate a repository's design record. The orchestrator's record was checked by hand: valid against the schema, 0 of 20 rules failing, and DR-012 failing on a designed-to-fail case. A record that breaks a rule would merge.
Detection: a person, while adding the record.
Root cause: the rules and the reference checker (tests/contracts/design_record_reference.py) exist in the playbook, but the central gate has no step that calls them.
Correction: the orchestrator's record was validated locally; nothing validates it on CI yet.
Preventive action (planned): KAN-55, a central gate step that applies the rules at the playbook's pinned commit and fails closed.
Verification: pending.
Evidence: factory-orchestrator PR #1 (design/service_design_record.v1.json); tests/contracts/design_record_reference.py.
Status: open.

## 2026-11-08: The Genesis gate pin recorded as fixed on 2026-10-29 is @main on main

Rule: every repository calls the central gate by full commit SHA, never a tag or a branch (AGENTS.md → CI Rules).
Problem: Genesis's gate caller on main (commit 667eb1b) names sovereign-vpc-gcp's gates.yml at @main. Any change merged to that repository's main changes Genesis's evaluator without a review in Genesis. The 2026-10-29 entry records this pin as corrected to a full SHA (Genesis #3).
Detection: a person, reading the caller while building the orchestrator's CI.
Root cause: not established from a shallow clone. The 2026-10-29 correction had no check behind it: its preventive action was repository visibility, and no check reads caller pins, so a regression raised no signal. Genesis's own instructions (added in its PR #2) say "not even @main", so the rule is written but not enforced.
Correction: none yet.
Preventive action (planned): KAN-54, a pin check in the central gates, or a playbook contract test, that fails a caller pinned to a branch or tag, shown failing on a fixture; then Genesis's caller is repinned by a reviewed pull request.
Verification: pending.
Evidence: Genesis main 667eb1b; Genesis PR #2 (.github/copilot-instructions.md); the 2026-10-29 entry above; KAN-54.
Status: open.

## 2026-11-08: builder.spec.v1 and the price table have no contract

Rule: contracts have one home, and every agent input and output is a versioned schema validated at runtime (AGENTS.md → Reuse Rules and Agent Rules).
Problem: the Builder's input, builder.spec.v1, is named in the factory's docs but has no schema in the playbook's schemas/. The price table that turns token records into spend has none either. The orchestrator's dispatch and budget tests cannot be written against a contract.
Detection: a person, while drafting KAN-14 slice 1's acceptance tests.
Root cause: the boundary was described in the docs before its contract was written, and no check lists contracts that are named but undefined.
Correction: none yet.
Preventive action (planned): a playbook pull request that adds both schemas, an example of each, and contract tests, each with a case that must fail.
Verification: pending.
Evidence: 07_SoftwareFactory/01_Software_Factory.md; 06_AgentZone/03_Software_Factory_Intake.md; KAN-14.
Status: open.

## 2026-11-10: The journal's CAPA fields are not checked

- **Rule:** every finding is journaled in CAPA form: rule, problem, detection, root cause,
  correction, preventive action, verification, evidence, and status (`AGENTS.md` → Observability
  Rules; this journal's Format: CAPA).
- **Problem:** 8 of 29 entries do not carry the fields in the documented form. The five entries of
  2026-11-08 use plain `Rule:` lines instead of the bold list fields, and three entries (2026-10-28
  telemetry copies, 2026-10-29 checks proven to fail, 2026-10-29 cloud project outside the
  organization) have no Evidence field. A reader can follow them; the CAPA graph's extract step,
  which parses the fields strictly and rejects an entry it cannot read
  (`06_AgentZone/10_CAPA_Graph_and_Risk_Weighted_Learning.md` §4), would reject all eight.
- **Detection:** a person, while backfilling the register's references for `findings_register.v2`.
- **Root cause:** the format is written in this preamble, but the journal's checks test only that
  entries are appended and that each has a register row. Nothing reads an entry's fields. This
  recurs the 2026-10-29 finding that the append-only rule was not enforced: the same kind of
  journal rule with no check behind it; that preventive action covered only appending.
- **Correction:** none yet. Entries are never rewritten, so the eight stay as they are.
- **Preventive action (planned):** a field check in `tests/journal/` that fails a new entry missing
  any CAPA field in the bold list form, shown failing on a fixture first, with the existing eight
  entries listed as known exceptions rather than edited.
- **Verification:** pending.
- **Evidence:** the field count run against this journal on 2026-11-10; the register's
  `findings_register.v2` references for this entry (`recurs` F-0014).
- **Status:** open.

## 2026-11-11: Hosted gate runners float on ubuntu-latest

- **Rule:** pin completely, and everything runs in a pinned container (`AGENTS.md` → Container
  Rules); the factory installs its own pinned toolchain (`AGENTS.md` → CI Rules).
- **Problem:** the central gates and their callers default to `ubuntu-latest`. When that label moved
  to Ubuntu 26.04, the pinned `bubblewrap` version the gates install was no longer available, and
  aws-builder-agent's TypeScript sandbox tests failed (aws-builder-agent #21 and #22). The gates'
  result changed with no change to the gates or the caller.
- **Detection:** a person, reading the red checks' logs during the 2026-11-11 factory CI survey.
- **Root cause:** the runner OS is an input to every gate result but was left floating. The rule to
  pin completely is applied to images, packages and actions, and nothing checks the runner label.
- **Correction (interim containment):** sovereign-vpc-gcp pins the gates' default `runs-on` and
  every hosted fallback in `gates.yml`, `gates-selftest.yml`, `plan.yml` and `apply.yml` to
  `ubuntu-24.04`; aws-builder-agent then repins the gates to that merge commit.
- **Preventive action (planned):** KAN-66, the gates run inside a container image pinned by digest,
  so the hosted runner's OS no longer reaches the result.
- **Verification:** pending: the pin merged on sovereign-vpc-gcp `main`, then aws-builder-agent's
  gates green on its `main` after the repin.
- **Evidence:** aws-builder-agent #21 and #22 gate logs; sovereign-vpc-gcp branch
  `fix/pin-hosted-runner-ubuntu-24.04`; KAN-66.
- **Status:** open.

## 2026-11-11: The self-hosted runner pool sat at zero with nothing to scale it up

- **Rule:** compute runs only when called: runners are at zero when no work is queued (`AGENTS.md`
  → IaC Rules); queued-job age needs its own alert, and runner failures are metrics with alerts
  (`AGENTS.md` → CI Rules and Observability Rules).
- **Problem:** the managed groups `ci-runner-plan` and `ci-runner-apply` in `sovereign-vpc-488522`
  were resized to zero by hand to stop idle cost. Nothing scales them up when a job is queued, so
  sovereign-vpc-gcp #41 and #42 queued with no runner and no signal. The Terraform still declares
  `size = 1`, so the code and the live state disagree.
- **Detection:** a person, asking why #41 and #42 never started.
- **Root cause:** scale-to-zero was applied by hand without the scale-from-zero half: there is no
  trigger on a queued job, and no queued-job-age alert that would have shown the stall.
- **Correction (interim containment):** the owner resized `ci-runner-plan` to 1 at about 15:47 UTC
  so #41 and #42 could run, to be resized back to 0 when they finish.
- **Preventive action (planned):** KAN-67, a signature-verified `workflow_job` webhook received by
  Cloud Run at zero minimum instances creates one ephemeral VM per queued job, which deletes itself
  after its job; a sweep removes stale VMs, the Terraform declares no always-on capacity, and
  queued-job age gets an alert.
- **Verification:** pending: a job queued against an empty pool runs, and the pool returns to zero.
- **Evidence:** sovereign-vpc-gcp #41 and #42 runs; the managed-group resize on 2026-11-11; KAN-67.
- **Status:** open.

## 2026-11-11: Playbook pin bumps cannot pass the vendored-contracts check

- **Rule:** contracts have one home and are vendored as `.playbook/`, checked byte-for-byte against
  the pin (`AGENTS.md` → Reuse Rules); pins are updated through gated pull requests (`AGENTS.md` →
  Supply Chain Rules).
- **Problem:** in the consumer repositories, Dependabot bumps the playbook action's pin in
  `sync-playbook-rules.yml` without changing `.playbook/`. The consumer's "Vendored contracts match
  the pin" check fails on that pull request, because the vendored files are only regenerated after
  the bump merges, when the sync workflow runs on the push to `main`. Every playbook bump must
  therefore merge red, and `main` is out of sync until a second pull request merges.
  compliance-authority #10 fails this way, missing every contract added since `37853f5`.
- **Detection:** a person, reading the failing check's log on compliance-authority #10 during the
  2026-11-11 factory CI survey.
- **Root cause:** the sync was designed as a post-merge reaction to the pin, while the check that
  enforces it runs before the merge. Nothing produces the pin and the vendored files in the same
  change.
- **Correction:** none yet. compliance-authority #10 stays open until the corrected sync can
  replace it.
- **Preventive action (planned):** in agent-notepad, aws-builder-agent, compliance-authority and
  coqui-tts, Dependabot ignores the playbook action, and the sync workflow takes a `ref` input on
  `workflow_dispatch` so one pull request changes the pin and `.playbook/` together; the push
  trigger stays as a backstop.
- **Verification:** pending: a dispatched sync opens a pull request that passes the vendored-contracts
  check before it merges, in each of the four repositories.
- **Evidence:** compliance-authority #10, run 42997795613; each repository's
  `.github/workflows/sync-playbook-rules.yml` and `.github/dependabot.yml`.
- **Status:** open.

## 2026-11-11: aws-builder-agent declares its npm dependencies as caret ranges

- **Rule:** pin every input: packages by exact version in a committed lockfile, updated through
  gated pull requests, never through floating ranges (`AGENTS.md` → Supply Chain Rules).
- **Problem:** every dependency in aws-builder-agent's `package.json` is a `^` range (for example
  `"@opentelemetry/api": "^1.9.1"`). The lockfile fixes what is installed today, but any
  regeneration of it can move every package within its range without a reviewed change to the
  declared versions.
- **Detection:** a person, reading the manifest while preparing the repository's grouped
  Dependabot configuration on 2026-11-11.
- **Root cause:** not established. The other TypeScript repository, agent-notepad, declares exact
  versions; nothing in the central gates checks the manifest for ranges.
- **Correction:** none. The owner decided on 2026-11-11 to keep the ranges for now rather than
  convert them in the Dependabot change.
- **Preventive action (planned):** convert the manifest to exact versions in its own pull request,
  and a central gate check that fails a manifest declaring a range, shown failing on a fixture.
- **Verification:** pending.
- **Evidence:** aws-builder-agent `package.json` at `48edcd8`.
- **Status:** open.

## 2026-11-11: The playbook sync PR names the wrong source

- **Rule:** know what goes into every artifact and prove where it came from (`AGENTS.md` → Supply
  Chain Rules); contracts are vendored from the pinned playbook (`AGENTS.md` → Reuse Rules).
- **Problem:** the sync pull request's title, commit message and body name
  `peter-evans/create-pull-request@22a9089…` as the source of the vendored rules, not the
  playbook. A reviewer cannot tell from the pull request which playbook version it adopts.
  aws-builder-agent #9 shows it; the vendored `.playbook/README.md` in the same pull request
  names the playbook correctly (`590f09f`, the consumer's pin).
- **Detection:** a person, reading aws-builder-agent #9 on 2026-11-11.
- **Root cause:** `action.yml` reads `github.action_ref` and `github.action_repository` in the
  `with:` inputs of its nested `peter-evans/create-pull-request` step. There they name the nested
  action, not the playbook. Only the action's own `run` step reads them correctly. No test covered
  the action.
- **Correction:** none yet. aws-builder-agent #9 is held unmerged.
- **Preventive action (planned):** the vendor step publishes the playbook's ref and repository as
  outputs, the pull-request step reads those, and a contract test fails any nested-action step that
  reads `github.action_*`, shown failing on the action as it was. The contract tests run on changes
  to `action.yml`.
- **Verification:** pending: the test fails on the old action and passes on the fixed one, and the
  next sync pull request in a consumer names the playbook commit.
- **Evidence:** aws-builder-agent #9 (title and body, `.playbook/README.md`); `action.yml` at
  `af9d918`.
- **Status:** open.

## 2026-11-11: Six repositories have no protection on main

- **Rule:** staging and prod merges need human approval, enforced by branch protection with no
  bypass; agents cannot change their evaluator, and `main` requires the person's code-owner review
  (`AGENTS.md` → Security Rules and Agent Rules).
- **Problem:** sovereign-vpc-gcp, aws-builder-agent, agent-notepad, compliance-authority, coqui-tts
  and gcp-reviewer-agent have no ruleset and no branch protection on `main`. Anyone with write
  access can push directly, including to the central gates in sovereign-vpc-gcp, which every
  repository runs; the CODEOWNERS files merged on 2026-11-11 are not enforced there. The Playbook,
  Genesis and factory-orchestrator do have rulesets.
- **Detection:** a person, checking each repository's rules on `main` (`GET
  /repos/{repo}/rules/branches/main`) while triaging red runs on 2026-11-11.
- **Root cause:** rulesets were added repository by repository as each was set up; nothing lists
  which repositories lack one, and the playbook names no check for it.
- **Correction:** none yet. The owner applies the factory-orchestrator ruleset (no deletion, no
  force-push, pull request with code-owner review, required status checks) to the six repositories,
  sovereign-vpc-gcp first.
- **Preventive action (planned):** a scheduled check that fails when any factory repository's `main`
  lacks those rules, shown failing on one that does.
- **Verification:** pending: each of the six returns the four rule types on `main`.
- **Evidence:** `GET /repos/Drecoder/{repo}/rules/branches/main` for each repository on 2026-11-11;
  F-0025.
- **Status:** open.

## 2026-11-11: The sovereign-vpc-gcp apply has failed on every push since October

- **Rule:** read every red check's log; failed applies are metrics with alerts (`AGENTS.md` → CI
  Rules and Observability Rules).
- **Problem:** every apply on `main` has failed since October (#11 through #38), so "Apply (dev)"
  never ran: #38 merged but never reached GCP, and #39's plan fails on the missing output
  `inference_bench_sa_email`. Live state and `main` diverged for weeks (issue #26).
- **Detection:** a person, surveying the factory's red checks on 2026-11-11; no alert fired.
- **Root cause:** two defects in the apply's gates call: it omits `no-image-reason`, so the image
  rule fails closed, and the Debian 12 self-hosted runner has no Python 3.12 for `setup-python`,
  which also causes the exit-127, missing-coverage and license-scan errors. Nothing alerts on a
  failed apply.
- **Correction:** sovereign-vpc-gcp #44 adds `no-image-reason` to `apply.yml`; a runner image on an
  exact Ubuntu 24.04 image (Python 3.12 available) replaces `debian-cloud/debian-12`. Then an apply
  lands #38, and #39 can plan.
- **Preventive action (planned):** a failed-apply metric with an alert (the observability rule
  above), tracked with KAN-67's runner work.
- **Verification:** pending: an apply on `main` succeeds and #39's plan passes.
- **Evidence:** sovereign-vpc-gcp run 41755822228 (log lines 3143 and 12818); run 41755407595 (#39);
  issue #26; #44.
- **Status:** open.

## 2026-11-11: Genesis applies on every push to main

- **Rule:** plan, never apply outside the separate post-merge pipeline with its own scoped identity;
  Terragrunt, never bare `terraform`; Genesis merges need human approval (`AGENTS.md` → Agent, IaC
  and Governance Rules).
- **Problem:** `.github/workflows/terraform-apply.yml` runs `terraform apply -auto-approve` on every
  push to `main`, with bare `terraform` and a hard-coded mock token. Today it targets a placeholder
  endpoint and fails, but any merge triggers it, and Genesis is the repository that owns the
  guardrails.
- **Detection:** a person, reading Genesis's workflows while triaging its four red pull requests on
  2026-11-11.
- **Root cause:** the workflow predates the playbook's apply rules and was never brought under them;
  no check lists workflows that apply on push.
- **Correction:** planned as Genesis PR 1: the apply runs on `workflow_dispatch` only, merged before
  any other Genesis change.
- **Preventive action (planned):** the Terragrunt and pinned OpenTofu layout decided for Genesis,
  with apply in its own pipeline and identity.
- **Verification:** pending: a push to Genesis `main` starts no apply.
- **Evidence:** Genesis `.github/workflows/terraform-apply.yml` at `main`; Terraform Apply runs on
  `main`, latest failure at `667eb1b`.
- **Status:** open.

## 2026-11-11: A Genesis governance module file holds only a file path

- **Rule:** `terragrunt hcl fmt` and `validate` pass before IaC work is done (`AGENTS.md` → IaC
  Rules and Local Validation Commands).
- **Problem:** `modules/governance/gcp/org_policy_identity_controls.tf` contains only the Windows
  path `C:\WS\genesis\modules\governance\gcp\org_policy_identity_controls.tf`. The HCL gate stops on
  it with "Invalid character", and the identity org-policy controls it should hold are missing.
- **Detection:** a person, reading the HCL gate's log on Genesis #3 on 2026-11-11.
- **Root cause:** not established; the path looks pasted or redirected into the file in place of its
  contents.
- **Correction:** none yet. The owner restores the file from the local copy, or removes it if it was
  never meant to be committed.
- **Preventive action (planned):** the HCL gate already fails closed on it; no new control.
- **Verification:** pending: the HCL gate passes on Genesis.
- **Evidence:** Genesis #3, HCL gates log.
- **Status:** open.

## 2026-11-11: Genesis CI cannot pass: no OpenTofu, no quality file, no image declaration

- **Rule:** the factory installs its own pinned toolchain; each repository holds
  `.ci/quality.v1.json`; every service ships an image or declares why not (`AGENTS.md` → CI, Test
  Quality and Container Rules).
- **Problem:** no Genesis pull request can pass: Terratest fails with `exec: "tofu": executable file
  not found in $PATH`, the quality gate fails closed on the missing `.ci/quality.v1.json`, and the
  image rule fails because the caller sets neither `image-target` nor `no-image-reason`. Genesis #1,
  #3, #4 and #5 are all red for these reasons, besides F-0041 and F-0043.
- **Detection:** a person, reading each red check's log on Genesis #1, #3, #4 and #5 on 2026-11-11.
- **Root cause:** the central gates gained these requirements after Genesis's caller was written,
  and Genesis moved to OpenTofu without the gates installing it.
- **Correction:** planned: Genesis's caller adds `no-image-reason` and is repinned from `@main` to a
  commit SHA (KAN-54); the central gates install pinned, checksum-verified OpenTofu; Genesis adds
  `.ci/quality.v1.json`.
- **Preventive action (planned):** consumer repins remain the test of each consumer (`AGENTS.md` →
  CI Rules); the repin carries the new requirements in the same pull request, as aws-builder-agent
  #23 does.
- **Verification:** pending: Genesis #4's gates pass.
- **Evidence:** Genesis #1, #3, #4 and #5 check logs, 2026-11-11.
- **Status:** open.

## 2026-11-11: Genesis's test dependencies carry two critical CVEs

- **Rule:** every vulnerability scanner goes through one severity gate, and pins are updated through
  gated pull requests (`AGENTS.md` → CI and Supply Chain Rules).
- **Problem:** Trivy blocks every Genesis pull request on `github.com/hashicorp/go-getter` 1.7.1
  (CVE-2024-3817) and `google.golang.org/grpc` 1.56.3 (CVE-2026-33186), both CRITICAL. Both are
  indirect, pulled in only by Terratest 0.46.3, so they are in test code and never in what Genesis
  deploys.
- **Detection:** the Trivy gate, on Genesis pull requests; traced to Terratest by a person on
  2026-11-11.
- **Root cause:** Genesis had no Dependabot configuration, so the indirect modules were never bumped
  (Genesis #5 adds one).
- **Correction:** planned: bump Terratest so both modules update, or the owner turns on Dependabot
  security updates for Genesis; Genesis #5 stays unmerged until Genesis CI is green.
- **Preventive action (planned):** Genesis #5's Dependabot configuration (go_modules with a
  Terratest, `golang.org/x` and grpc group).
- **Verification:** pending: Trivy passes on Genesis.
- **Evidence:** Genesis #4 and #5 Trivy logs; Genesis #5.
- **Status:** open.

## 2026-11-11: The aws-builder-agent runtime image carries six critical CVEs

- **Rule:** an image finding is fixed at its source, never excepted; base images pinned by digest,
  downloads by checksum, packages by exact version (`AGENTS.md` → Container and Supply Chain Rules).
- **Problem:** the first scan of the Builder's runtime image blocks on six CRITICAL findings: Go
  `stdlib` 1.22.7 and `grpc` 1.59.0 in the `terraform` 1.9.8 binary; `stdlib` 1.23.1, `grpc` 1.66.0
  and `labstack/echo` 4.11.4 in the `terragrunt` 0.67.16 binary; and `zlib1g` 1.2.13
  (CVE-2023-45853) in the `node:22-bookworm-slim` base. The same Dockerfile pins the base by tag,
  downloads both tools without checksums, installs apt packages unversioned, and installs
  `terraform` though the factory chose OpenTofu.
- **Detection:** the image gate, on aws-builder-agent #23, the first pull request to set
  `image-target`.
- **Root cause:** the image was never scanned: the repository's gate pin predated the image rule, so
  its toolchain versions aged without a signal.
- **Correction:** pending the owner's choice, inside #23: OpenTofu and a current terragrunt (option
  A) or current terraform and terragrunt (option B), each checksum-verified, with the base pinned by
  digest.
- **Preventive action (planned):** the image gate now runs on every pull request; Dependabot's
  docker ecosystem watches the base digest.
- **Verification:** pending: the image gate passes on #23 and on `main` after merge.
- **Evidence:** aws-builder-agent #23, job 130694386871.
- **Status:** open.

## 2026-11-11: Image builds download external files with no retry

- **Rule:** every remote call has a timeout and retries with backoff where idempotent (`AGENTS.md` →
  Application Architecture Rules); read every red check's log (`AGENTS.md` → CI Rules).
- **Problem:** two image builds fail on one transient network error: the Playbook's anti-pattern
  toolchain image got a 504 downloading Trivy 0.71.1 from GitHub releases (red on `main` since
  2026-11-09, because the workflow reruns only when its paths change), and coqui-tts #3 hit a
  connection reset downloading the ffmpeg source tarball (#4, #7 and #8 fail at the same step,
  unconfirmed).
- **Detection:** a person, reading the red runs on 2026-11-11.
- **Root cause:** the downloads use `curl -sSf` with no `--retry`, and nothing reruns a workflow
  that failed on an infrastructure error.
- **Correction:** rerun the anti-pattern catalog workflow; add `--retry 5 --retry-all-errors` with a
  connect timeout to both downloads, keeping the checksum verification.
- **Preventive action (planned):** the same retry on every external download in a Dockerfile; rig
  classifies such failures as `infra`, which go to a person (`AGENTS.md` → Agent Rules).
- **Verification:** pending: the anti-pattern catalog is green on `main`, and coqui-tts's image
  builds.
- **Evidence:** Playbook run 42569537837 (`curl: (22) ... 504`); coqui-tts #3 build log;
  `tests/antipatterns/toolchain/Dockerfile`.
- **Status:** open.

## 2026-11-11: Agent pull requests are authored as the owner

- **Rule:** agents author changes under their own App identities, never the person's, and `main`
  requires the person's code-owner review (`AGENTS.md` → Agent Rules and Security Rules).
- **Problem:** every pull request the coding agent opened on 2026-11-11 (for example
  sovereign-vpc-gcp #43 and #44, aws-builder-agent #23 and #24, Playbook #72 to #75) is authored
  by the owner's account, because the agent acts through the owner's GitHub connection. GitHub
  never requests a review from a pull request's author, so none reaches the owner's "Needs your
  review", and the owner cannot approve them; a ruleset that required code-owner review would
  block every merge. Bot-authored pull requests (Dependabot, github-actions) are routed and
  approvable correctly.
- **Detection:** a person, comparing the inbox's "Needs your review" and "Waiting for review or
  checks" sections on 2026-11-11.
- **Root cause:** the per-agent GitHub App identity the rule requires does not exist yet, and the
  agent's session has only the owner's credentials.
- **Correction (interim containment):** the agent opens pull requests only on the owner's explicit
  go-ahead, never merges, and states in each pull request that it is agent-authored; sovereign-vpc-gcp's
  ruleset requires checks with 0 approvals until this is fixed.
- **Preventive action (planned):** KAN-69, a GitHub App per agent with no `workflows` permission,
  its key non-exportable in Cloud KMS; then every factory ruleset requires code-owner review.
- **Verification:** pending: an agent pull request authored by the App appears in the owner's
  "Needs your review" and merges only after the owner's approval.
- **Evidence:** the authors of the pull requests above; sovereign-vpc-gcp ruleset 27052237;
  KAN-69.
- **Status:** open.

## 2026-11-11: dependency_patch promoted to L3 below its interim evidence target

- **Rule:** autonomy is granted per process class through a reviewed change, one level at a time,
  and L3 needs at least 300 defect-free events at 95% confidence (`AGENTS.md` → Autonomy Rules;
  `schemas/autonomy_policy.v1.json` interim targets).
- **Problem:** the owner promoted `dependency_patch` from L1 to L3 on the evidence of a run of
  Dependabot pull requests approved without a change, about a dozen, not 300, and skipping L2.
  The promotion is real, so the policy now differs from the evidence its own target requires.
- **Detection:** the agent, checking the interim targets while drafting the promotion.
- **Root cause:** human review of these pull requests was the factory's bottleneck. The owner was
  approving single-package updates the deterministic gates already fully cover, and the review
  added no detection (`10_Autonomy_by_Evidence.md`: the human adds no detection).
- **Correction:** the promotion is narrowed instead of withheld. Only Dependabot pull requests that
  change only manifests and lockfiles, with patch or minor updates, merge without a person, and
  only after every required check on `main` is green, including CRAP and mutation
  (sovereign-vpc-gcp `dependabot-auto-merge.yml`, 9 cases, 5 of 5 condition mutants killed). A
  repository without required checks never auto-merges.
- **Preventive action (planned):** count each auto-merged update as an event and each defect
  traced to one (a revert, an incident) as a defect. Demotion is automatic on a defect or an
  out-of-control signal, as for any class.
- **Verification:** pending: 300 defect-free auto-merged events at 95% confidence, which closes this
  entry; any traced defect demotes the class.
- **Evidence:** sovereign-vpc-gcp #47; this pull request's policy change.
- **Status:** open.

## 2026-11-11: A skipped required check counted as passed

- **Rule:** a skipped job is not a pass (`AGENTS.md` → CI Rules: "the factory tests itself").
- **Problem:** GitHub treats a skipped required check as passed. When "Detect stacks" failed on
  Genesis #6, every stack job was skipped, so the pull request showed as mergeable with HCL and
  Semgrep never having run; only secret scanning had passed.
- **Detection:** the owner, reading the check list before a merge and refusing to merge a build
  whose gates had skipped.
- **Root cause:** the rulesets required individual gate jobs by name, and GitHub's merge rules
  cannot tell a legitimate skip (a stack the repository does not have) from a gate that did not
  run because an earlier job failed.
- **Correction:** a Gates verdict job in the shared gates (sovereign-vpc-gcp #48). It always runs,
  works out from the detected stacks and the inputs which jobs had to run, and fails unless every
  one of them succeeded; a failed Detect stacks fails it outright.
- **Preventive action:** each repository requires the one check, `gates / Gates verdict`, in place
  of a list of job names, once it repins.
- **Verification:** self-test `verdict`, 11 cases: every skipped or failed gate that applies fails
  the verdict, including the failed-Detect case, and legitimate skips pass; all 6 mutants of its
  logic killed. Live: `plan / gates / Gates verdict` passed on #48's own plan run.
- **Evidence:** sovereign-vpc-gcp #48 (merge 74be340); Genesis #6's check list.
- **Status:** proven. Residual: the rulesets still name the old checks until each repository
  repins.

## 2026-11-11: Genesis's ruleset required checks that never report

- **Rule:** required checks must match check-run names exactly, or nothing can merge
  (`AGENTS.md` → CI Rules; F-0038).
- **Problem:** the ruleset applied to Genesis's `main` required status contexts that no Genesis
  workflow reports, so every pull request would wait forever for them.
- **Detection:** the owner, reading back the ruleset after applying it.
- **Root cause:** the required contexts were written from the job names in the shared workflow,
  not read from the check runs Genesis's caller actually produces (`gates / gates / …`).
- **Correction:** the owner reapplied the ruleset with the three contexts Genesis reports.
- **Preventive action:** rulesets require the single `gates / Gates verdict` context after each
  repin (F-0048), so there is one name to get right instead of a list.
- **Verification:** the owner's read-back shows the three reporting contexts.
- **Evidence:** the owner's `gh api` ruleset read-backs, 2026-11-11.
- **Status:** fixed.

## 2026-11-11: Mutation testing crashed on every TypeScript repository

- **Rule:** mutation score is tracked with a floor in CI, and each check is shown to fail on the
  defect it guards against before it counts (`AGENTS.md` → Test Quality Rules, CI Rules).
- **Problem:** Stryker rewrites `tsconfig.json` and loads `typescript` from its own install folder,
  which the gate keeps apart from the repository. Every consumer has a `tsconfig.json`, so the
  mutation gate crashed on all of them with "Cannot find package 'typescript'". It failed closed:
  it would have blocked every TypeScript repository, never let one through.
- **Detection:** the agent, running the gate's exact Stryker configuration on factory-orchestrator
  and aws-builder-agent to measure their mutation floors before they repinned.
- **Root cause:** the self-test fixture had no `tsconfig.json`, so it never exercised the path every
  real consumer takes.
- **Correction:** the gate installs the repository's exact `typescript` version, read from its
  `node_modules` after `npm ci`, beside Stryker (sovereign-vpc-gcp #49).
- **Preventive action:** a self-test case with a `tsconfig.json` and a pinned `typescript`.
- **Verification:** the case was committed first and failed with the exact error the real
  repositories hit; after the fix, 12 of 12 mutation cases pass.
- **Evidence:** sovereign-vpc-gcp #49 (merge 6d595f1).
- **Status:** proven.

## 2026-11-11: An orchestrator takeover of a retried attempt is rejected to Blocked

- **Rule:** invalid payloads are rejected, never repaired, so the orchestrator must build a valid
  one (`AGENTS.md` → Agent Rules: schemas at every boundary).
- **Problem:** when a lease expires with no CI result, the orchestrator takes it over and
  re-dispatches the same attempt. For attempt 2 or 3, `builder.spec.v1` requires a
  `failure_delta`, but the takeover sent none, so the spec was rejected and the ticket went to
  Blocked instead of being re-dispatched.
- **Detection:** a control: a test written to kill a surviving mutant of the FI-01b bound
  ("answered attempts do not use up the takeover budget") failed with `rejected`.
- **Root cause:** the takeover path reused the first-pickup dispatch, which sends no failure delta;
  no test covered a takeover after a bounce.
- **Correction:** a takeover of attempt 2 or later re-sends the failure that started the attempt,
  read from the runs store. Fixed with FI-01b (silent takeovers bounded by unanswered dispatches)
  and FI-04b (a bounce raises the fencing token) on factory-orchestrator branch
  `fix/fi-01b-fi-04b-bounded-takeover`.
- **Preventive action:** acceptance tests for each takeover path, committed failing first.
- **Verification:** pending merge: 60 of 60 tests pass with every line of `orchestrator.ts`
  covered; all 9 mutants of the new controls are killed; the AFDF baseline's FI-01b and FI-04b
  injection cases now pass.
- **Evidence:** factory-orchestrator commits 664e94f (tests) and 5f3e0e7 (fix), not yet in a
  pull request.
- **Status:** open.

## 2026-11-11: CI jobs wait minutes for every runner to install its tools

- **Rule:** compute runs only when called and scales to zero (`AGENTS.md` → IaC Rules), and the
  owner's time is the factory's bottleneck.
- **Problem:** the private runner pool gives each job a fresh VM, which installs its packages,
  downloads the GitHub runner, and installs its dependencies before the job starts. Each pull
  request's plan workflow needs two such cycles on the one VM, so three queued pull requests waited
  about six cycles, most of it setup.
- **Detection:** the owner, waiting on a `Plan (dev)` check that sat queued with the VM running.
- **Root cause:** the runner image is stock Debian; everything a job needs is installed at boot,
  every boot.
- **Correction (planned):** bake the runner image once (packages and the checksum-verified runner)
  and boot it by name; the startup script skips the installs when the image carries the pinned
  runner version and installs as before on any other image. Built on sovereign-vpc-gcp branch
  `feat/baked-runner-image`, not yet pushed.
- **Preventive action:** the image name is the pin; a new bake changes nothing until a reviewed
  pull request points the pool at it.
- **Verification:** pending: a job's start time after a VM boots, before and after.
- **Evidence:** sovereign-vpc-gcp plan runs for #46, #47 and #48 (queued 2026-11-11).
- **Status:** open.

## 2026-11-16: Mutation testing crashed on every repository on typescript 7

- **Rule:** every repository tracks its mutation score with a floor (`AGENTS.md` → Test Quality
  Rules), and the factory fixes its own CI failures (`AGENTS.md` → CI Rules).
- **Problem:** typescript 7, the native compiler, ships no JavaScript compiler API. Stryker parses
  `tsconfig.json` through that API, and since F-0050 the gate installs the repository's own
  typescript beside Stryker, so on aws-builder-agent (typescript 7.0.2) mutation crashed with
  "ts.parseConfigFileTextToJson is not a function" before the first mutant. It failed closed, so
  nothing passed, but the Builder could not get a mutation floor.
- **Detection:** the agent, running the gate's exact Stryker configuration on aws-builder-agent to
  measure its floor before the MVP repin.
- **Root cause:** the F-0050 fix assumed every typescript release has the JavaScript API; the
  self-test covered typescript 6 only.
- **Correction:** for a repository on typescript 7 or later the gate puts a pinned typescript 6.0.3
  (`STRYKER_TYPESCRIPT_API`) beside Stryker for its tsconfig parse; the repository's own typescript
  still runs its tests (sovereign-vpc-gcp #50).
- **Preventive action:** a self-test case for a typescript 7 repository.
- **Verification:** pending merge: the case was committed first and failed with the exact error;
  after the fix 13 of 13 mutation cases pass, and aws-builder-agent measured 945 of 986 mutants
  killed (host run, provisional).
- **Evidence:** sovereign-vpc-gcp #50 (commits f32264e, 7195458).
- **Status:** open.

## 2026-11-16: Genesis has never implemented GOV-002 (no service-account keys)

- **Rule:** every `GOV-*` guardrail is implemented in Genesis from the vendored baseline, staged in
  dry run, then enforced (`AGENTS.md` → Governance Rules); GOV-002's baseline mode is `enforce`.
- **Problem:** `modules/governance/gcp/org_policy_identity_controls.tf`, the file meant for the
  identity controls, was empty from Genesis's first commit and since 2026-05-09 has held only a
  pasted Windows path. `constraints.tf` names `iam.disableServiceAccountKeyCreation` and
  `iam.disableServiceAccountKeyUpload`, but no policy applies them. Service-account key creation
  and upload, which the Security Rules forbid, are not denied by any org policy from Genesis.
- **Detection:** the agent, reading the red `HCL gates` log on Genesis #7 ("Invalid character" on
  line 1 of that file) and tracing the file's history.
- **Root cause:** the governance module was written by hand rather than generated from the
  baseline, and nothing compares the policies Genesis applies with the baseline's controls; until
  Genesis #7 no gate ran on Genesis's HCL at all.
- **Correction (planned):** Genesis #7 removes the corrupt line, so the file is valid and says what
  is missing (containment, not a fix). A separate governance pull request implements GOV-002 from
  the baseline in dry run, on the highest-scrutiny path with the owner's approval, then enforces it,
  and audits which other baseline controls Genesis lacks.
- **Preventive action:** generate Genesis's org policies from `governance_baseline.v1.json` and
  check in CI that every control with a GCP org-policy status is applied.
- **Verification:** pending: GOV-002 in dry run, then `adversarially_verified` (a denied key
  creation and a denied upload), then enforced.
- **Evidence:** Genesis #7, job 130898665766; Genesis commit b32f454.
- **Status:** open.

## 2026-11-16: The Go gate installed a hard-coded Go version

- **Rule:** the factory is self-contained and installs a pinned toolchain (`AGENTS.md` → CI Rules).
- **Problem:** both Go job shapes installed Go 1.23. Genesis's `go.mod` requires 1.26.3, so its
  Go gate stopped at "go.mod requires go >= 1.26.3 (running go 1.23.12; GOTOOLCHAIN=local)". The
  local toolchain setting correctly refused to download another Go; the gate never ran Genesis's
  vet, build, tests or vulnerability scan.
- **Detection:** the gate itself, failing closed on Genesis #7.
- **Root cause:** the Go version was written into the workflow instead of read from the repository
  it gates; the gate had no Go self-test.
- **Correction:** `GATE_GO_VERSION` resolves the highest version any built `go.mod` requires (its
  toolchain directive, else its go directive, `X.Y` meaning `X.Y.0`), and both job shapes install
  exactly that version (sovereign-vpc-gcp #52).
- **Preventive action:** `tests/gates/go/cases.sh` and a `go-version` self-test job.
- **Verification:** pending merge: the 10 cases were committed first and all failed on 6d595f1;
  with the fix 10 of 10 pass, and on Genesis the resolver gives 1.26.3.
- **Evidence:** sovereign-vpc-gcp #52 (commits 73adfef, 820fb07); Genesis #7, job 130898665696.
- **Status:** open.

## 2026-11-16: Genesis runs its own plan and apply workflows outside the central CI

- **Rule:** CI lives in one reusable workflow, with no per-repository CI; anything that touches a
  cloud runs from the central pool (`AGENTS.md` → CI Rules).
- **Problem:** Genesis keeps `terraform-plan.yml` and `terraform-apply.yml`. The plan workflow pins
  actions by tag, installs `terraform` instead of the pinned OpenTofu, runs Terratest a second time
  without OpenTofu (so its "Build and Plan" check fails on every pull request), and plans against a
  mock token, which proves nothing.
- **Detection:** the agent, reading the red "Build and Plan" log on Genesis #7.
- **Root cause:** the workflows predate the central CI and were never retired when the gates came
  in.
- **Correction (planned):** Genesis #7 retires both; Terratest already runs in the central Go gate
  with `install-opentofu`, and Genesis's plan and apply move to the central `iac.yml` (KAN-72,
  KAN-73). No apply runs from Genesis until then.
- **Preventive action:** a central check that a consumer's `.github/workflows` holds only its
  gates caller and the shared callers.
- **Verification:** pending: Genesis #7 green with no per-repository workflow.
- **Evidence:** Genesis #7, job 130898607600.
- **Status:** open.

## 2026-11-16: Two factory repositories have no Dependabot security updates

- **Rule:** every factory repository has vulnerability alerts and Dependabot security updates on
  (`AGENTS.md` → Security Rules).
- **Problem:** `setup-auto-merge-security.sh` turned them on for the repositories it lists; Genesis
  and gcp-reviewer-agent are not among them. Genesis carries two CRITICAL vulnerabilities in
  Terratest's indirect dependencies (`hashicorp/go-getter` 1.7.1, CVE-2024-3817;
  `google.golang.org/grpc` 1.56.3, CVE-2026-33186) and no pull request was ever opened to fix them.
- **Detection:** the Trivy gate blocked both on Genesis #7; the agent then compared the script's
  repository list, as the owner ran it, with the factory repositories.
- **Root cause:** the script's repository list was written by hand and missed two repositories.
- **Correction (planned):** add both repositories to the script and run it; bump both dependencies
  in Genesis #7 (go-getter 1.7.4 or later, grpc 1.79.3 or later).
- **Preventive action:** derive the script's list from the findings register's component registry.
- **Verification:** pending: both settings read back on, and Genesis #7's Trivy gate green.
- **Evidence:** Genesis #7, job 130898610397 (`trivy: 71 finding(s), 2 blocking`).
- **Status:** open.

## 2026-11-16: The CRAP gate blocked the agent's own regression

- **Rule:** ratchet the past: no existing function's CRAP, and no module's mutation score or
  complexity, gets worse than its baseline (`AGENTS.md` → Test Quality Rules).
- **Problem:** the agent's FI-01b fix put the takeover bound inside `#pickUp`, raising its
  complexity from 5 to 8 and the module's existing-function total from 101 to 104, and its new
  code left orchestrator.ts's mutation score at 84.2% against a base of 84.9%.
- **Detection:** the CRAP gate (Policy Engine 2.2.0) blocked factory-orchestrator #8 on QP-020,
  QP-021 and QP-022 on its first run. A check shown to work on a real change, not a fixture.
- **Root cause:** the fix added branches to an existing function instead of a new one, and its
  tests did not pin which previous result a takeover re-sends.
- **Correction:** the takeover and dispatch tail moved into a new `#start` (existing total 100,
  `#pickUp` 4), and four tests aimed at the surviving mutants raised orchestrator.ts to 87.2%.
- **Preventive action:** the agent measures complexity with the gate's own script and the base's
  mutation score before pushing a change to an existing module.
- **Verification:** pending: the re-run of #8's CRAP and Mutation gates.
- **Evidence:** factory-orchestrator #8 (commits 928697c, 5231e2e).
- **Status:** open.

## 2026-11-16: Dependabot bumps merged a manifest without its lockfile

- **Rule:** auto-merge is limited to a class promoted to L3 (`AGENTS.md` → Autonomy Rules); pin
  every input in a committed lockfile (`AGENTS.md` → Supply Chain Rules).
- **Problem:** coqui-tts merged three Dependabot bumps that changed `pyproject.toml` alone (#12
  OpenTelemetry, #14 torchaudio, #16 pytest). The image installs from the hashed lockfiles, so it
  kept the old versions while every gate stayed green, and `torchaudio==2.11.1` beside
  `torch==2.6.0+cpu` cannot be resolved. compliance-authority has the same drift (pydantic,
  pytest). Replayed against coqui-tts #13 (`torch==2.15.0`, dropping `+cpu`), the auto-merge
  eligibility check answered "Eligible: every condition holds": a control admitting what it must
  refuse. Nothing has auto-merged; the gap is open until sovereign-vpc-gcp #53 merges.
- **Detection:** the owner, reviewing coqui-tts #13; the agent replayed the eligibility check and
  compared every manifest pin with both lockfiles.
- **Root cause:** the eligibility rule accepted any change confined to manifests and lockfiles, not
  a manifest that moves with its lockfile; and no gate compared a manifest with the locks built from
  it, because the build reads only the locks.
- **Correction:** containment by the owner: #13 closed, auto-merge off on coqui-tts. coqui-tts #18
  reverts the three manifest-only bumps and stops version updates of torch and torchaudio (security
  updates still open). sovereign-vpc-gcp #53: eligibility refuses a manifest changed without the
  lockfile beside it, and `GATE_LOCK_MATCH` fails a manifest pin the locks do not have.
- **Preventive action:** both checks run in the central factory with self-tests committed failing
  first; the same class of gap is related to F-0047 (`dependency_patch` promoted below its evidence
  target).
- **Verification:** pending merge: auto-merge cases 16 of 16, lockfile cases 11 of 11; on real
  repositories coqui-tts `main` fails (9 pins), coqui-tts #18 passes, compliance-authority `main`
  fails (3 pins).
- **Evidence:** coqui-tts #12, #13, #14, #16, #18; sovereign-vpc-gcp #53 (commits f887418,
  69baf77).
- **Status:** open. This is the last hand-written entry: from here findings are opened by controls
  as issue-backed records and projected into this journal (KAN-60, owner decision 2026-11-16).

## 2026-11-16: The governance baseline stages guardrails that cannot run in dry run

- **Rule:** every new or changed guardrail is staged in dry run before it is enforced
  (`AGENTS.md` → Governance Rules).
- **Problem:** Google Org Policy accepts a dry-run policy only for custom constraints, managed
  constraints and four legacy ones (service usage, endpoint usage, TLS versions, TLS cipher
  suites). The baseline's GCP controls name legacy constraints (GOV-002
  `iam.disableServiceAccountKeyCreation` and `…Upload`; GOV-006, 007, 009, 011 and 012 likewise),
  so the baseline's own staging rule cannot be met for them.
- **Detection:** the agent, preparing KAN-76 slice 1 (GOV-002 in dry run), from Google's "Test
  organization policies" limitations.
- **Root cause:** the baseline was written against legacy constraint names without checking each
  constraint's dry-run support.
- **Correction (planned):** the baseline names the managed equivalents (for example
  `iam.managed.disableServiceAccountKeyCreation`), each checked against Google's per-constraint
  dry-run flag, and marks any control without one as a custom constraint or a documented
  exception; owner-reviewed.
- **Preventive action:** a contract test that refuses a baseline control whose constraint cannot be
  dry-run.
- **Verification:** pending: the baseline change and its contract test, then GOV-002 in dry run.
- **Evidence:** KAN-76 comments of 2026-11-16; Genesis #8.
- **Status:** open.

## 2026-11-16: The plan pool sat at zero again, and four PR gates queued over three hours with no alert

- **Rule:** queued-job age needs its own alert, and runner failures are metrics with alerts
  (`AGENTS.md` → CI Rules, Observability Rules); compute runs only when called (`AGENTS.md` → IaC
  Rules).
- **Problem:** `ci-runner-plan` was at target size 0 from after 2026-11-12 01:18:32 UTC (the last
  plan job, `ci-runner-plan-8hcr-2e5f5f`) until about 07:55 UTC on 2026-11-16. The required `gates /
  Gates (single job)` jobs of sovereign-vpc-gcp #50, #51, #52 and #53 queued with no runner; #50's
  waited 3 h 17 min 39 s (04:39:30 to 07:57:09 UTC). Nothing alerted.
- **Detection:** a person: the agent reading the queued checks at session start, then the owner
  reading the group's live size.
- **Root cause (DRAFT):** F-0034's containment, resizing by hand, is the only way the pool scales,
  and its preventive action (KAN-67 plus a queued-job-age alert) is not built. A pool at zero and a
  broken pool look the same from GitHub.
- **Correction:** the owner resized `ci-runner-plan` to 1 at about 07:55 UTC;
  `ci-runner-plan-rbs4-f87bed` picked up #50's job at 07:57:09.
- **Preventive action (DRAFT):** a queued-job-age metric with an alert for every `sovereign-*`
  label, built first, then the elastic plan pool (0 idle, burst to 3–4 Spot VMs on queue depth;
  design record before build; KAN-67). The alert is also a KAN-60 trigger ("a queued job past its
  age threshold").
- **Verification (DRAFT):** a job queued against an empty pool raises the alert within its threshold
  (designed-to-fail case), and the pool returns to zero after the job.
- **Evidence:**
  [Drecoder/Engineering_Excellence_Playbook#84](https://github.com/Drecoder/Engineering_Excellence_Playbook/issues/84)
  (the finding); runs 43805413928, 43805524210, 43818233175, 43821351066; Plan (dev) for #49
  completed 2026-11-12T01:18:32Z; sovereign-vpc-gcp
  `docs/incidents/2026-11-16-INC-008-plan-pool-left-at-zero.md`.
- **Status:** open.

## 2026-11-16: The apply workflow has been disabled for twelve days with no signal

- **Rule:** failed applies are metrics with alerts; a failure found by a person looking is a finding
  in itself (`AGENTS.md` → Observability Rules).
- **Problem:** sovereign-vpc-gcp's `apply.yml` is `disabled_manually`, last changed
  2026-11-03T19:59:17-06:00, after its last run (41755822228, 2026-11-04, failed). #47, #48 and #49
  merged on 2026-11-12 and started no apply. INC-006's report job, which opens the "Apply failing on
  main" issue, lives in the same workflow, so disabling it also silenced its alarm. Hand resizes of
  the runner groups stay in place, because nothing reconciles the declared state.
- **Detection:** a person: the agent, listing the repository's workflows while looking for the
  runner outage.
- **Root cause (DRAFT):** the signal for a broken apply is emitted from inside the workflow it
  watches, so the containment for a failing apply (disabling it) also removes the signal.
- **Correction:** none yet. Re-enabling waits on the two apply blockers (sovereign-vpc-gcp #44 and
  the runner image). Interim (owner, 2026-11-16): `ci-runner-apply` resized to 0 by hand, recorded
  as drift.
- **Preventive action (DRAFT):** a scheduled check outside `apply.yml` that fails, and opens a
  KAN-60 finding, when the apply workflow is disabled or `main`'s head has no successful apply
  within a stated age.
- **Verification (DRAFT):** the check fails on a fixture with the workflow disabled and on one with
  an unapplied head, and passes once apply runs on `main`.
- **Evidence:**
  [Drecoder/Engineering_Excellence_Playbook#85](https://github.com/Drecoder/Engineering_Excellence_Playbook/issues/85)
  (the finding); `GET /repos/Drecoder/sovereign-vpc-gcp/actions/workflows` (`apply.yml`
  `disabled_manually`); apply runs 41755822228 (last), none since; sovereign-vpc-gcp #47–#49 merge
  commits.
- **Status:** open.

## 2026-11-16: The agent diagnosed the runner outage from the code, not the live state

- **Rule:** read every red check's log; a failure that looks like the expected one is still read,
  because an assumed cause hides the real one (`AGENTS.md` → CI Rules).
- **Problem:** the handoff `claude/handoff-2026-11-16-b.md` said the plan runner "ran every other
  job of #50 and #51 until ~04:42Z" and that the outage "isn't a sizing problem", because the unit
  declares `size = 1`. No run supports the timeline: the last plan job finished 2026-11-12 01:18:32
  UTC, and every job of #50 and #51 that ran went to GitHub-hosted runners. The group was at 0. The
  owner's first queued action pointed at a VM serial log for a VM that did not exist.
- **Detection:** a person: the agent, in the next session, listing the runner name of every
  `sovereign-plan` job since 2026-11-01.
- **Root cause (DRAFT):** the diagnosis read declared state and inferred the timeline from which
  checks were green, without reading which runner ran each job or the group's live size.
- **Correction:** the next session corrected it with the owner (2026-11-16 ~07:55 UTC) before any
  change was made.
- **Preventive action (DRAFT):** a runner diagnosis cites the last job each runner ran (job history,
  `runner_name`) and the group's live target size; the queued-job-age metric (sibling finding) makes
  the state visible without inference.
- **Verification (DRAFT):** the next runner incident's record carries both citations.
- **Evidence:**
  [Drecoder/Engineering_Excellence_Playbook#86](https://github.com/Drecoder/Engineering_Excellence_Playbook/issues/86)
  (the finding); job history for runs since 2026-11-01 (all `sovereign-plan` jobs with a
  `runner_name`); sovereign-vpc-gcp INC-008 timeline.
- **Status:** open.

## 2026-11-16: Dependabot cannot read the private central CI, so its run on main fails

- **Rule:** read every red check's log; callers pin the central workflow to a full commit SHA and
  repin through a reviewed pull request (`AGENTS.md` → CI Rules).
- **Problem:** on coqui-tts `main` (`ae43a6a`, the #18 merge), one of three Dependabot runs failed
  (check 133146961219). The github-actions updater could not fetch `Drecoder/sovereign-vpc-gcp` to
  check the caller's pins on `gates.yml` and `dependabot-auto-merge.yml`:
  `git_dependencies_not_reachable`. The other ecosystems succeeded. The same error has failed every
- **Detection:** a person: the agent, reading every check on each `main` before re-scoring the
  roadmap.
- **Root cause (DRAFT):** the central CI is a private repository, and Dependabot has no access to
  the owner's other private repositories. Its pins are meant to move only through reviewed repin
  PRs, so Dependabot has nothing to update there anyway. The 2026-11-11 triage treated it as a
  setting to
- **Correction (DRAFT):** in each consumer's `.github/dependabot.yml`, the github-actions entry
  ignores `Drecoder/sovereign-vpc-gcp/*`, with the reason written in (repins are reviewed PRs).
  Alternative for the owner: grant Dependabot access to the private repository.
- **Preventive action (DRAFT):** the central caller template carries the ignore, so every new
  consumer starts with it.
- **Verification (DRAFT):** the next Dependabot run on each consumer's `main` succeeds for
  github-actions.
- **Evidence:**
  [Drecoder/Engineering_Excellence_Playbook#87](https://github.com/Drecoder/Engineering_Excellence_Playbook/issues/87)
  (the finding); aws-builder-agent Dependabot runs 40612975761 and 43078055981 (`Handled error
  whilst
- **Status:** open.

## 2026-11-16: The hand projection cut three sentences from F-0087's journal entry

- **Rule:** every finding is journaled as a compact post-mortem, and entries are added, never
  rewritten (`AGENTS.md` → Observability Rules).
- **Problem:** the journal entry for F-0087, merged in #88 (`f2985d4`), stops mid-sentence in three
  fields. **Problem** ends at "The same error has failed every", **Root cause** at "treated it as a
  setting to", and **Evidence** at "(`Handled error whilst". In the issue body of #87, each of those
  bullets goes on in indented continuation lines; the hand projection kept only each bullet's first
  line. The register row and the entries for F-0084, F-0085 and F-0086 are complete. #87 itself is
  intact.
- **Detection:** a person: the agent, reading the merged journal at the start of the next session,
  before building the projector.
- **Root cause (DRAFT):** the projection was a one-off script run by hand, with no test, and nothing
  compared the projected entry with its issue. The append-only check, the register check and
  markdownlint all passed, because a cut sentence is still valid Markdown and the heading still
  matches its row.
- **Correction:** this finding's journal entry restates F-0087's three cut fields in full, from #87;
  the F-0087 entry stays as merged, because entries are never rewritten. The register row of F-0087
  is unchanged. The three fields in full, from #87:
  - **Problem (F-0087):** on coqui-tts `main` (`ae43a6a`, the #18 merge), one of three Dependabot
    runs failed (check 133146961219). The github-actions updater could not fetch
    `Drecoder/sovereign-vpc-gcp` to check the caller's pins on `gates.yml` and
    `dependabot-auto-merge.yml`: `git_dependencies_not_reachable`. The other ecosystems succeeded.
    The same error has failed every weekly github-actions run on aws-builder-agent since 2026-10-28
    (runs 40612975761, 41751671110, 42936417351, 43078055981), on `gates.yml`. On 2026-11-11 it was
    triaged in the red-check survey as "Dependabot can't reach a private repo (an owner setting)"
    and went on a checklist as "turn on Dependabot private-repo access": no journal entry, no
    register row, no due date, so it was never closed and is now seen on a second repository.
  - **Root cause (F-0087, DRAFT):** the central CI is a private repository, and Dependabot has no
    access to the owner's other private repositories. Its pins are meant to move only through
    reviewed repin PRs, so Dependabot has nothing to update there anyway. The 2026-11-11 triage
    treated it as a setting to toggle, without a finding, so nothing tracked it.
  - **Evidence (F-0087):** aws-builder-agent Dependabot runs 40612975761 and 43078055981 (`Handled
    error whilst updating Drecoder/sovereign-vpc-gcp/.github/workflows/gates.yml:
    git_dependencies_not_reachable`); coqui-tts check run 133146961219, job log line `Handled error
    whilst updating Drecoder/sovereign-vpc-gcp/.github/workflows/dependabot-auto-merge.yml:
    git_dependencies_not_reachable`.
- **Preventive action (DRAFT):** KAN-60 slice 1's projector is built test first, with #87's body as
  a fixture: a bullet with continuation lines projects whole. A check refuses a projected entry
  whose text, with whitespace normalized, differs from its issue's bullets.
- **Verification (DRAFT):** the projector's test fails on the one-line-per-bullet behaviour and
  passes on the fix; re-projecting #87 reproduces the three full fields given below.
- **Evidence:**
  [Drecoder/Engineering_Excellence_Playbook#89](https://github.com/Drecoder/Engineering_Excellence_Playbook/issues/89)
  (the finding); `docs/POC_JOURNAL.md` at `f2985d4`, the F-0087 entry; issue #87's body; PR #88.
- **Status:** open.

## 2026-11-16: A hand scale-in to zero killed four running CI jobs

- **Rule:** compute runs only when called, and CI failures are signals, not noise (`AGENTS.md` → IaC
  Rules, CI Rules).
- **Problem:** at about 09:02 UTC on 2026-11-16, `ci-runner-plan` was resized by hand to 0 while
  four runners held jobs. All four jobs failed within 42 s (09:02:07 to 09:02:49 UTC) when their VMs
  were deleted: the gates job of #55 (`ci-runner-plan-x994-d27f22`) and of #54
  (`ci-runner-plan-bnfq-9fba23`), and `Plan (dev)` of #53 (`ci-runner-plan-rbs4-205e3b`) and of run
  43818233175 (`ci-runner-plan-r533-7c9ccf`). Required checks went red for a reason unrelated to the
  code.
- **Detection:** a person: the agent, reading the red checks; GitHub reported the runners as lost.
- **Root cause (DRAFT):** hand resizing is the only way the pool scales (F-0034's containment), and
  a managed instance group deletes VMs without knowing whether a runner holds a job. Nothing checks
  that the pool is idle before scaling in.
- **Correction:** the four runs were re-run (attempt 2) and passed.
- **Preventive action (DRAFT):** #55's scaler never shrinks a pool while any of its runners is busy.
  Until #55 is live, a hand scale-in to 0 happens only after the `sovereign-plan` queued and
  in-progress counts both read 0.
- **Verification (DRAFT):** a designed-to-fail test in #55: a scale-in requested while a runner is
  busy leaves the target size unchanged.
- **Evidence:**
  [Drecoder/Engineering_Excellence_Playbook#91](https://github.com/Drecoder/Engineering_Excellence_Playbook/issues/91)
  (the finding); sovereign-vpc-gcp runs 43834264138, 43828521071, 43821351066 and 43818233175
  (attempt 1 failed 09:02:07–09:02:49 UTC; attempt 2 passed); handoff
  `claude/handoff-2026-11-16-e.md`. Related: F-0034 and F-0084 (open; hand resizing is their
  containment), sovereign-vpc-gcp #55 (KAN-67).
- **Status:** open.

## 2026-11-16: The bake workflow merged three times without its real path running, and each run found the next defect

- **Rule:** a control counts only when its real path has run; read every red log (`AGENTS.md` → CI
  Rules).
- **Problem:** `bake-runner-image.yml` is started only by hand (`workflow_dispatch`), so no PR runs
  it. #51 merged without a run, and read the serial port after the VM stopped, so it could never
  succeed (runs 43836324036, 43838274590: `resource ... is not ready`). #56 polled while the VM ran
  but kept only the last read; checked by `bash -n` and a YAML parse, it failed with an empty copy
  and no reason (run 43840809177). #57 printed the read errors; its run (43879267488) had no read
  errors and still kept one blank line, because an empty last read replaced everything read before
  it. Four bakes, no image; the cause of the bake VM's power-off about 3 min after boot is still
  unknown.
- **Detection:** a person: the agent, reading each failed bake log.
- **Root cause (DRAFT):** a dispatch-only workflow has no PR-time execution, and the gates check its
  syntax only. Each fix was merged with "the real test is the next run", so production was the only
  test of the step's logic.
- **Correction:** sovereign-vpc-gcp #59 reads the serial port from the previous response's `next`
  offset and appends, so a late empty read loses nothing, and logs every read's size. Its step was
  run locally against a stub `gcloud` (success: image created; `BAKE_RESULT=failed`: no image,
  result shown).
- **Preventive action (DRAFT):** the bake's polling logic moves into a script with tests run by the
  gates on any PR that touches it: designed-to-fail cases for an empty final read, a missing
  `BAKE_RESULT=ok`, and a VM that never stops. A dispatch-only workflow merges only with such a test
  or a linked successful run.
- **Verification (DRAFT):** the test fails on #56's last-copy logic and passes on #59's; then a bake
  on `main` produces an image.
- **Evidence:**
  [Drecoder/Engineering_Excellence_Playbook#92](https://github.com/Drecoder/Engineering_Excellence_Playbook/issues/92)
  (the finding); sovereign-vpc-gcp runs 43836324036, 43838274590, 43840809177, 43879267488; PRs #51,
  #56, #57, #59. Related: F-0052 (open; the baked image is its correction), F-0010 (proven; the fail
  side of the same class), sovereign-vpc-gcp #51, #56, #57, #59.
- **Status:** open.

## 2026-11-16: The central gate's Python path never ran on the Debian self-hosted pool

- **Rule:** every gate that applies runs and passes, and a skip is never a pass (`AGENTS.md` → CI
  Rules).
- **Problem:** `actions/setup-python` supports GitHub's Ubuntu images, not Debian 12. #55 was the
  first Python-touching PR whose gates ran on `ci-runner-plan`; its single gates job failed at
  `setup-python` and every Python step after it (run 43837740795). F-0039 named this cause on
  2026-11-11; its correction (an Ubuntu 24.04 runner image) was never made. Other gate steps may
  assume Ubuntu too: the bubblewrap pin is an Ubuntu package version. Not yet checked.
- **Detection:** a person: the agent, reading #55's red gates log.
- **Root cause (DRAFT):** the gates self-test runs only on hosted Ubuntu runners, so no change to
  the gates is exercised on the self-hosted pool. F-0039's correction had no ticket and no owner.
- **Correction:** sovereign-vpc-gcp #58 installs Python with a pinned uv 0.13.5 (sha256 from the
  owner) on self-hosted runners; its `python-self-hosted` self-test passed on the pool (run
  43842299596).
- **Preventive action (DRAFT):** the full single-job self-test runs on every self-hosted label in
  each gates PR, or hosted and self-hosted runners share one OS image.
- **Verification (DRAFT):** the self-hosted self-test fails on an Ubuntu-only step before its fix
  (designed to fail), then passes.
- **Evidence:**
  [Drecoder/Engineering_Excellence_Playbook#93](https://github.com/Drecoder/Engineering_Excellence_Playbook/issues/93)
  (the finding); sovereign-vpc-gcp run 43837740795 (#55); run 43842299596 (#58); F-0039's journal
  entry. Related: F-0039 (open; recorded on 2026-11-11 that the Debian 12 runner has no Python 3.12
  for `setup-python`), sovereign-vpc-gcp #55, #58.
- **Status:** open.

## 2026-11-16: The agent pushed a workflow with a trigger GitHub Actions does not have

- **Rule:** check behaviour against the platform's documentation before relying on it (`AGENTS.md` →
  CI Rules).
- **Problem:** #55's first push of `.github/workflows/runner-scaler.yml` used `on: workflow_job`, a
  webhook event that is not a GitHub Actions trigger. GitHub rejected the file (run 43834216309
  failed in 0 s). The push was corrected to `workflow_run`.
- **Detection:** a control: GitHub's workflow parser.
- **Root cause (DRAFT):** the agent wrote the trigger from memory, without the GitHub docs or a
  workflow linter. Nothing lints workflow files before push or in the gates.
- **Correction:** #55 uses `workflow_run` on plan and apply plus a 5-minute schedule.
- **Preventive action (DRAFT):** a pinned actionlint runs in the gates on every change under
  `.github/workflows/`, and in the agent's pre-push.
- **Verification (DRAFT):** actionlint rejects a fixture workflow with `on: workflow_job` (designed
  to fail) and passes the corrected file.
- **Evidence:**
  [Drecoder/Engineering_Excellence_Playbook#94](https://github.com/Drecoder/Engineering_Excellence_Playbook/issues/94)
  (the finding); sovereign-vpc-gcp run 43834216309; PR #55's commit history. Related: F-0086 (open;
  also acted on an assumption instead of checking), sovereign-vpc-gcp #55.
- **Status:** open.

## 2026-11-16: An agent's local test ran a download the owner had stopped

- **Rule:** an agent acts only within what the owner approves (`AGENTS.md` → Agent Rules).
- **Problem:** while #58 was being built, the owner stopped the uv download, and a local test step
  then ran uv anyway. The step ran inside an `if ( … )` condition, where bash ignores `set -e`, so
  the failed step did not stop the script. The session did not record the commands or times, only
  the outcome (handoff `claude/handoff-2026-11-16-e.md`, item 5).
- **Detection:** a person: the owner.
- **Root cause (DRAFT):** `set -e` does not apply to commands in a condition (`if`, `&&`, `||`), so
  an earlier failure, here the stopped download, does not stop the script. The test had no explicit
  check that the download had succeeded before running the binary.
- **Correction:** the step runs in `bash -c`, so `set -e` applies inside it.
- **Preventive action (DRAFT):** scripts the agent writes check each prerequisite explicitly (exit
  status and checksum) before using what it produced, and never rely on `set -e` inside a condition;
  a ShellCheck rule or test case covers `set -e` under `if`.
- **Verification (DRAFT):** a test where the download step fails shows the script stops before
  running the binary (designed to fail).
- **Evidence:**
  [Drecoder/Engineering_Excellence_Playbook#95](https://github.com/Drecoder/Engineering_Excellence_Playbook/issues/95)
  (the finding); handoff `claude/handoff-2026-11-16-e.md`, item 5; PR #58. The session kept no
  command log; this gap is part of the finding. Related: F-0046 (open; the agent acts through the
  owner's credentials), sovereign-vpc-gcp #58.
- **Status:** open.

## 2026-11-16: An agent commit was authored as the owner because the agent copied the last commit's author

- **Rule:** agents author changes under their own identity, never the person's (`AGENTS.md` → Agent
  Rules, Security Rules).
- **Problem:** the agent created sovereign-vpc-gcp commit `cd8f210` with `-c user.name/user.email`
  taken from `git log -1`, the owner's merge commit, so it was authored as the owner, though the
  clone's configured identity is `Claude <noreply@anthropic.com>`. It was pushed and #59 opened on
  it at 13:54 UTC; the agent noticed, re-authored it (`abb6e15`) and force-pushed within about a
  minute. Plan run 43880298759 started on the wrong commit and was cancelled.
- **Detection:** a person: the agent, comparing the author with earlier agent commits.
- **Root cause (DRAFT):** the agent overrode the configured identity with a value read from history
  instead of trusting the configuration. Nothing checks commit authors on agent pull requests.
- **Correction:** #59 now has one commit, authored as Claude.
- **Preventive action (DRAFT):** the agent never sets `user.name`/`user.email` on the command line.
  Until KAN-69, a gate on pull requests marked agent-authored refuses any commit whose author is not
  the agent identity.
- **Verification (DRAFT):** the gate fails on `cd8f210` (designed to fail) and passes on `abb6e15`.
- **Evidence:**
  [Drecoder/Engineering_Excellence_Playbook#96](https://github.com/Drecoder/Engineering_Excellence_Playbook/issues/96)
  (the finding); sovereign-vpc-gcp commits `cd8f210` and `abb6e15`; runs 43880298759 (cancelled) and
  43880340573; PR #59. Related: F-0046 (open, same fingerprint, so not a `recurs`; this is a new
  path to it), KAN-69, sovereign-vpc-gcp #59.
- **Status:** open.

## 2026-11-16: F-0039's root cause explained only the last three of sixteen failed applies

- **Rule:** read every red check's log (`AGENTS.md` → CI Rules).
- **Problem:** F-0039 gives the cause of every failed apply since October as two defects in the
  apply's gates call, read from run 41755822228 (#38). That holds for applies #22–#24 only (#35,
  #36, #38: the gates job failed). The earlier failures had passing gates and failed in `Apply
  (dev)` itself, with two other causes: (1) applies #9–#13 (#4, #12, #10, #11, #14; 2026-10-23 to
  10-26): `Error creating RegionBackendService ... Balancing mode must be CONNECTION for an INTERNAL
  backend service`, fixed by #16; (2) applies #14–#21 (#16 to #32; 2026-10-26 to 10-29): `Permission
  'iam.serviceAccounts.create' denied` creating `ollama-gpu-bench` on `sovereign-vpc-488522`. #38
  moved that account into the human-applied identity unit and #39 (open) points the bench unit at
  it; whether the identity unit has been applied is not known. The first apply after `apply.yml` is
  re-enabled will roll out every change merged since 2026-10-23.
- **Detection:** a person: the agent, reading every failed apply on 2026-11-16 after the owner
  shared the `dev` deployments page.
- **Root cause (DRAFT):** the 2026-11-11 diagnosis read the newest failed run only; the failure
  streak's first run and the points where the error changed were not read.
- **Correction:** this finding records the two missing causes; F-0039's entry stays as written.
- **Preventive action (DRAFT):** a repeated failure is diagnosed from the first run of the streak
  and every run where the error changes, not the latest only. Before `apply.yml` is re-enabled: the
  identity unit is applied by hand, #39 is merged, and a plan on `main` shows no service-account
  creation by `ci-apply`.
- **Verification (DRAFT):** the first apply after re-enabling succeeds; the failed-apply alert
  planned in F-0039 fires on a designed-to-fail apply.
- **Evidence:**
  [Drecoder/Engineering_Excellence_Playbook#97](https://github.com/Drecoder/Engineering_Excellence_Playbook/issues/97)
  (the finding); sovereign-vpc-gcp apply runs 40003137967, 40284222436, 40284655716, 40286088966,
  40364496131 (balancing mode); 40370266410 to 40801232217 (eight runs, IAM denied); 40875507651,
  40875694344, 41755822228 (gates); PRs #16, #38, #39. Related: F-0039 (open; the entry this
  corrects), F-0085 (apply disabled), F-0086 (same class: diagnosis without full evidence),
  sovereign-vpc-gcp #38, #39.
- **Status:** open.
