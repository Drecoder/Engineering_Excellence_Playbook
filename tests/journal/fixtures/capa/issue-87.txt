### Journal heading

Dependabot cannot read the private central CI, so its run on main fails

### Category

ci

### Severity

low

### Detected by

person

### Found

2026-11-16

### Rules

AGENTS.md#CI Rules

### Components

coqui-tts
aws-builder-agent
sovereign-vpc-gcp

### Fingerprints

dependabot-private-reusable-workflow
checklist-only-triage

### Recurs

_No response_

### Rule

read every red check's log; callers pin the central workflow to a full commit SHA and repin through a reviewed pull request (`AGENTS.md` → CI Rules).

### Problem

on coqui-tts `main` (`ae43a6a`, the #18 merge), one of three Dependabot runs failed (check 133146961219). The github-actions updater could not fetch `Drecoder/sovereign-vpc-gcp` to check the caller's pins on `gates.yml` and `dependabot-auto-merge.yml`: `git_dependencies_not_reachable`. The other ecosystems succeeded. The same error has failed every
weekly github-actions run on aws-builder-agent since 2026-10-28 (runs 40612975761, 41751671110,
42936417351, 43078055981), on `gates.yml`. On 2026-11-11 it was triaged in the red-check survey as
"Dependabot can't reach a private repo (an owner setting)" and went on a checklist as "turn on
Dependabot private-repo access": no journal entry, no register row, no due date, so it was never
closed and is now seen on a second repository.

### Detection

a person: the agent, reading every check on each `main` before re-scoring the roadmap.

### Root cause

the central CI is a private repository, and Dependabot has no access to the owner's other private repositories. Its pins are meant to move only through reviewed repin PRs, so Dependabot has nothing to update there anyway. The 2026-11-11 triage treated it as a setting to
toggle, without a finding, so nothing tracked it.

### Correction

in each consumer's `.github/dependabot.yml`, the github-actions entry ignores `Drecoder/sovereign-vpc-gcp/*`, with the reason written in (repins are reviewed PRs). Alternative for the owner: grant Dependabot access to the private repository.

### Preventive action

the central caller template carries the ignore, so every new consumer starts with it.

### Verification

the next Dependabot run on each consumer's `main` succeeds for github-actions.

### Evidence

aws-builder-agent Dependabot runs 40612975761 and 43078055981 (`Handled error whilst
updating Drecoder/sovereign-vpc-gcp/.github/workflows/gates.yml: git_dependencies_not_reachable`);
coqui-tts check run 133146961219, job log line `Handled error whilst updating Drecoder/sovereign-vpc-gcp/.github/workflows/dependabot-auto-merge.yml: git_dependencies_not_reachable`.

### Drafts for the owner

- [X] Root cause
- [X] Correction
- [X] Preventive action
- [X] Verification
