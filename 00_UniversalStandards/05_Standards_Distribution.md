# Standards Distribution

*The playbook is the single source of truth. Consumer repos depend on it — the playbook never
depends on them.*

---

## 1️⃣ Why Distribution Is Needed

Claude Code only loads the `CLAUDE.md` of the repo it is working in (plus the user-level
`~/.claude/CLAUDE.md`). Rules written here do nothing for a session — or a containerized agent —
running in another repo unless they are delivered there.

| Consumer | Where it runs | How it gets the rules |
| :--- | :--- | :--- |
| Local Claude Code sessions | Your machine | Vendored `.playbook/` (preferred) or an `@` import of a local playbook checkout |
| AWS Builder agent | ECS Fargate / AgentCore container | Vendored `.playbook/` in the repo it clones |
| GCP Reviewer agent | Cloud Run container | Vendored `.playbook/` in the repo under review |
| Non-Claude agents (Gemini, SLMs) | Any | `.playbook/AGENTS.md` — same content as `CLAUDE.md` |

Containers have no access to your local disk, so **vendoring is the standard**; local `@` imports
of an absolute path are a convenience only.

---

## 2️⃣ Design: Dependency Inversion

The playbook **publishes**; consumers **declare a dependency**. Nothing in the playbook lists
consumer repos.

| Concern | Owned by |
| :--- | :--- |
| What the rules are | Playbook (`CLAUDE.md`, `schemas/`) |
| How rules are vendored | Playbook (`action.yml` — a composite GitHub Action) |
| Which repos use the rules | Each consumer (its own workflow) |
| Which version a repo uses | Each consumer (the pinned `@vX.Y.Z` ref) |
| When a repo adopts a new version | Each consumer (merging the Dependabot bump and the sync PR) |

Adding a consumer never requires a playbook change, and the playbook needs no credentials for
any other repo.

---

## 3️⃣ What Is Vendored

| Source (playbook, at the pinned ref) | Destination (consumer repo) |
| :--- | :--- |
| `CLAUDE.md` | `.playbook/CLAUDE.md` |
| `CLAUDE.md` | `.playbook/AGENTS.md` |
| `schemas/**` (when present) | `.playbook/schemas/**` |
| — | `.playbook/README.md` (source ref + do-not-edit notice) |

The zone docs are **not** vendored: they explain the rules, and the rules link back to them.

---

## 4️⃣ How It Flows

1. A rule change merges to `main` in the playbook and is released as a tag (`vX.Y.Z`).
2. Dependabot in each consumer opens a PR bumping `Drecoder/Engineering_Excellence_Playbook@vX.Y.Z`.
3. Merging that bump triggers the consumer's sync workflow, which runs the playbook action.
4. The action replaces `.playbook/` with the files from that exact ref and opens a sync PR.
5. The consumer's own CI and review gate the sync PR. Merging it **adopts** the new rules.

Rules never change underneath a repo silently, and every repo's rule version is visible in its
workflow file.

---

## 5️⃣ Consumer Repo Setup

Copy the templates from `templates/consumer/`:

| Template | Destination in the consumer |
| :--- | :--- |
| `.github/workflows/sync-playbook-rules.yml` | Same path |
| `.github/dependabot.yml` | Same path (merge if one exists) |

Then:

1. Enable **Settings → Actions → General → Allow GitHub Actions to create and approve pull
   requests** (the action uses the workflow's `GITHUB_TOKEN`).
2. Run the workflow once manually (`workflow_dispatch`) to open the first sync PR.
3. Import the shared rules from the repo's own root `CLAUDE.md`:

   ```markdown
   # CLAUDE.md

   @.playbook/CLAUDE.md

   ## Repo-specific rules
   - ...
   ```

4. Add `.playbook/ @<owner>` to `CODEOWNERS` so vendored files only change through the sync PR.

Repo-specific rules may **narrow** playbook rules, never loosen them. A needed exception is a
playbook PR, not a local edit.

---

## 6️⃣ Releasing the Playbook

- Tag releases on `main` as `vX.Y.Z`. Consumers pin exact versions, so a tag is a contract:
  never move or delete a published tag.
- Version bumps follow the change type: **major** for a rule that can fail existing code,
  **minor** for new rules or schemas, **patch** for wording that changes no behavior.

---

## 7️⃣ Constraints

- **Private playbook:** if the playbook repo is private, enable **Settings → Actions → General →
  Access** so repositories owned by the same account can use its action.
- **CI on sync PRs:** PRs opened with `GITHUB_TOKEN` do not trigger other workflows. A consumer
  that needs CI on the sync PR passes a GitHub App token via the action's `token` input.
- **Destination safety:** the action refuses an empty, root, absolute, or `..` destination,
  because it replaces that directory on every sync.

---

## 8️⃣ Principle

A standard that does not reach the place where work happens is a suggestion. Distribution makes
the playbook **enforceable everywhere**, while each repo decides *which* version it runs and
*when* to adopt a change.
