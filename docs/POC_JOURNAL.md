# Proof-of-Concept Journal

*What applying the playbook actually found, in the order it was found, each written up as a
compact post-mortem.*

This journal is the factory's working record of proof. Each entry is a finding the playbook's rules
surfaced in real work: a defect, a gap between a written rule and what runs, or a check shown to
work. It feeds each program increment's re-grade (`docs/PROGRAM_INCREMENTS.md`) and the case study.

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
date, and verification (contract `schemas/findings_register.v1.schema.json`). CI checks both on
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
  proven to fail on their defect, the share of findings caught by a control rather than a person,
  open findings by severity, and days to close.
- **Governance closes before production.** Production readiness is false while any critical or
  high security or governance finding is open; no production operation until it is true.

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
- **Verification:** pending this change's own runs.
- **Evidence:** `docs/FINDINGS_REGISTER.json`, `tests/journal/register.py`,
  `schemas/findings_register.v1.schema.json`.
- **Status:** open until its runs are recorded.
