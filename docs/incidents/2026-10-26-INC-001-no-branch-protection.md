# INC-001: No Branch Protection on Any Platform Repository

## 1️⃣ Incident Summary

- **ID / Severity:** `INC-001`; High
- **Date / Time:** Found 2026-10-26 at about 19:20 UTC. The start is not determined; the gap has
  most likely existed since each repository was created. It is still open.
- **Service / System Affected:** All six platform repositories.
  - **Private, cannot be protected on the current GitHub plan:** `sovereign-vpc-gcp`, `rig`,
    `gcp-reviewer-agent`, `aws-builder-agent`.
  - **Public, can be protected but are not:** `Engineering_Excellence_Playbook`, `Genesis`.
- **Impact:** two controls the playbook relies on exist only on paper.
  - **Human approval of merges is not enforced** (`AGENTS.md` → Security Rules: staging and prod
    merges need human approval, enforced by branch protection, no bypass). Nothing stops a direct
    push to `main`, a force-push, or a merge without review, by a person or an agent with write
    access. A merge to `main` in `sovereign-vpc-gcp` triggers an apply.
  - **The code-owner review of `.ci/exceptions.v1.json` is not enforced**
    (`00_UniversalStandards/15_Central_CI.md` §9). CODEOWNERS files exist in `sovereign-vpc-gcp`
    and `gcp-reviewer-agent`, but without branch protection they only request a review; they
    cannot require one.
  - **No misuse is known.** Whether every change to `main` came through a pull request has not been
    checked. The 54 merged pull requests in the baseline window (`docs/BASELINE_2026-10-26.md`)
    were merged by the owner, but a direct push would not appear in that count. Any control that
    held, held by habit, not by enforcement.
- **Detection Method:** **manual investigation.** It was found while checking which status checks
  `main` requires, before the `single-job` change renamed the gate checks. The API refused to
  return branch protection for a private repository. Manual detection is itself a finding: no signal
  watches for this.
- **Time to detect / Time to resolve:** not determined / open.

## 2️⃣ Timeline of Events

| Time (UTC) | Action / Observation | Responsible |
| :--- | :--- | :--- |
| 2026-10-26 ~19:20 | Before renaming gate checks (sovereign-vpc-gcp#24), the required checks on `main` are queried; the API returns "Upgrade to GitHub Pro or make this repository public to enable this feature." | Claude Code |
| 2026-10-26 20:08 | All six repositories checked. The four private ones return the same 403 for branch protection and rulesets; the two public ones return "Branch not protected" and an empty ruleset list. | Claude Code |
| 2026-10-26 | Recorded here; `15_Central_CI.md` §9 marks the code-owner review as a gap. | Claude Code |

## 3️⃣ Root Cause Analysis

- **Trigger:** none. The gap was found before anything exploited it.
- **Systemic issue:**
  - **The plan does not offer it.** GitHub's plan for this account offers no branch protection or
    rulesets on private repositories.
  - **Nothing was set where it could have been.** The public repositories, which can have both,
    were never configured.
  - **The standard assumed it.** The playbook states the control as if it were in place, and
    nothing verifies that it is.
- **Contributing factors:**
  - **No signal.** No check, metric, or alert reports a repository without protection, and the
    governance baseline (`schemas/governance_baseline.v1.json`) covers cloud guardrails, not GitHub
    repository settings.
  - **One maintainer.** With a single maintainer, "require an approving review" cannot be met:
    GitHub forbids self-approval. So the protection that fits today is different from the protection
    the standard describes.

## 4️⃣ Resolution & Mitigation

- **Documentation corrected:** `15_Central_CI.md` §9 marks the code-owner review as a gap and
  points here.
- **No settings changed.** Repository settings are the owner's to change.
- **Lessons:**
  - A control written in a standard is a claim, not a fact, until something checks it.
  - On the current plan, making the private repositories public, which the portfolio already
    intends, is also what makes branch protection available to them.

## 5️⃣ Preventive Actions

| Action Item | Owner | Target Date | Status |
| :--- | :--- | :--- | :--- |
| Protect `main` on the two public repositories: require a pull request, block force-pushes and deletion, and require the gate checks, with no bypass | Drecoder | 2026-11-02 | Open |
| Make the four private repositories public, after the git-history audit for secrets and identifiers; or move to a plan that offers protection on private repositories | Drecoder | 2026-11-25 | Open |
| Decide how human approval works with one maintainer (a second approver, or a recorded rule for who may merge what) before requiring reviews | Drecoder | 2026-11-25 | Open |
| **Add the missing signal:** a scheduled check that every platform repository's `main` is protected as the standard requires, opening an incident issue when one is not | Drecoder | after the repositories are public | Open |

## 6️⃣ Evidence

- **Commands, run 2026-10-26 20:08 UTC, for each of the six repositories:**

  ```bash
  gh api repos/Drecoder/<repo>/branches/main/protection
  gh api repos/Drecoder/<repo>/rulesets
  ```

- **Results:**
  - **Private repositories:** HTTP 403, "Upgrade to GitHub Pro or make this repository public to
    enable this feature."
  - **Public repositories:** "Branch not protected", and `[]`.
- **Context:** sovereign-vpc-gcp#24 (the change that prompted the check);
  `docs/BASELINE_2026-10-26.md` (merge history in the window).
