# Proof-of-Concept Journal

*What applying the playbook actually found, in the order it was found, with the evidence for each.*

This journal is the factory's working record of proof. Each entry is a finding the playbook's rules
surfaced in real work: a defect, a gap between a written rule and what runs, or a check shown to
work. It feeds each program increment's re-grade (`docs/PROGRAM_INCREMENTS.md`) and the case study.
Entries are added, never rewritten; a later entry corrects an earlier one. This file is the journal
until the notepad runs (`06_AgentZone/07_Agent_Notepad.md`); then the journal moves into the
notepad's filing system, where each entry is a sealed, hash-chained record.

Each entry gives: the date, the playbook rule that applied, how it was found, the evidence (pull
requests, workflow runs, incident records), what changed, and its status.

---

## 2026-10-28: An image scan that ran out of disk passed for the expected CVE block

- **Rule:** read every red check's log (`AGENTS.md` → CI Rules).
- **Found by:** reading the log of a check everyone expected to be red, 16 hours later.
- **Evidence:** coqui-tts INC-001; runs 40656484883 (the failure) and 40808933067 (measured: 13 GB
  free at start, an 11 GB peak).
- **Changed:** a need-based disk preflight and a low-point report in every central gate job
  (sovereign-vpc-gcp #35).
- **Status:** fixed and measured.

## 2026-10-28: The central gate type-checked tests before installing pytest

- **Rule:** the factory tests itself; a skipped job is not a pass (`AGENTS.md` → CI Rules).
- **Found by:** a consumer's red gate (coqui-tts #1). The fix (sovereign-vpc-gcp #32) merged before
  its code path had run anywhere.
- **Evidence:** sovereign-vpc-gcp INC-007; the fixture fails on the old gate (run 40808542665) and
  passes on the fixed one (run 40808502279).
- **Changed:** a Python fixture and a self-test on every gate change (sovereign-vpc-gcp #33).
- **Status:** fixed; the fixture proves it.

## 2026-10-29: A CRITICAL CVE removed at its source, not excepted

- **Rule:** an image finding is fixed at its source, never excepted (`AGENTS.md` → Container Rules).
- **Found by:** the image scan blocking on CVE-2026-6653 (libxml2). A time-boxed exception was
  written, then rejected as a workaround.
- **Evidence:** coqui-tts #1 and #2; the equivalence report shows all 16 MP3s byte-identical.
- **Changed:** a minimal ffmpeg build; image findings 749 → 214 (CRITICAL 1 → 0); a daily check
  that the source build keeps up with Debian's security releases.
- **Status:** fixed.

## 2026-10-29: The central gate's checks proven to fail

- **Rule:** each check is shown to fail on the defect it guards against before it counts.
- **Evidence:** a throwaway pull request with the pre-fix gate fails the Python fixture
  (sovereign-vpc-gcp #34); one with a CRITICAL base image fails the image scan (#37); the disk
  preflight's cases, including an unmeetable need, run on a real runner (#35).
- **Status:** proven.

## 2026-10-29: A public repository could not call the private gate

- **Rule:** every repository calls the central gate by full commit SHA (`AGENTS.md` → CI Rules).
- **Found by:** Genesis's gate run failing to start; its caller also pinned `@main`.
- **Evidence:** Genesis #3.
- **Changed:** Genesis made private; one visibility for the factory, the playbook public. The
  caller pinned to a full SHA.
- **Status:** fixed. The gate now runs on Genesis and is red on legacy code; taking it to green
  through the agent loop is the first real workload.

## 2026-10-29: A cloud project outside the organization

- **Rule:** every cloud project lives in the governance hierarchy; a standalone project is a
  finding (`AGENTS.md` → Governance Rules).
- **Found by:** checking where the registry could live (`gcloud projects list`).
- **Evidence:** the project that holds the CI runners and their state has no parent organization.
- **Changed:** nothing yet; the registry goes into a project Genesis vends inside the organization.
- **Status:** open.

## 2026-10-29: A long-lived administrator key on a standalone AWS account

- **Rule:** SSO with MFA, never static keys (`AGENTS.md` → Security Rules); every account lives in
  the governance hierarchy.
- **Found by:** checking the toolchain's identity before the first live-agent run.
- **Evidence:** INC-002.
- **Changed:** nothing yet; the actions are the owner's.
- **Status:** open.
