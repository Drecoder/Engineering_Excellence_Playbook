# Standards Distribution

*The playbook is the single source of truth. Consumer repos receive a vendored copy through CI.*

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

## 2️⃣ What Is Distributed

| Source (playbook) | Destination (consumer repo) |
| :--- | :--- |
| `CLAUDE.md` | `.playbook/CLAUDE.md` |
| `CLAUDE.md` | `.playbook/AGENTS.md` |
| `schemas/**` (when present) | `.playbook/schemas/**` |
| — | `.playbook/README.md` (source commit + do-not-edit notice) |

The zone docs are **not** vendored: they explain the rules, and the rules link back to them.

---

## 3️⃣ How It Flows

1. A change to `CLAUDE.md` or `schemas/` merges to `main` in the playbook (reviewed like any PR).
2. `.github/workflows/sync-playbook-rules.yml` runs once per consumer repo.
3. It replaces the consumer's `.playbook/` directory and opens (or updates) a PR on the
   `chore/playbook-sync` branch.
4. The consumer repo's own CI and review gate the PR. Merging it is how a repo **adopts** a new
   rule version — rules never change underneath a repo silently.

---

## 4️⃣ Consumer Repo Setup

Each consumer keeps its own root `CLAUDE.md` for repo-specific rules and imports the shared ones:

```markdown
# CLAUDE.md

@.playbook/CLAUDE.md

## Repo-specific rules
- ...
```

- Add `.playbook/ @<owner>` to `CODEOWNERS` so vendored files only change through the sync PR.
- Repo-specific rules may **narrow** playbook rules, never loosen them. A needed exception is a
  playbook PR, not a local edit.

---

## 5️⃣ Identity & Security

- The workflow authenticates as a **GitHub App** installed only on the consumer repos, with
  `contents: write` and `pull_requests: write`. No personal access tokens.
- App ID lives in the repo variable `PLAYBOOK_SYNC_APP_ID`; the private key in the secret
  `PLAYBOOK_SYNC_APP_PRIVATE_KEY`.
- Tokens are minted per run and scoped to the single consumer repo being synced.

---

## 6️⃣ Adding a Consumer

1. Install the GitHub App on the new repo.
2. Add the repo name to the `matrix.repo` list in `sync-playbook-rules.yml`.
3. Run the workflow manually (`workflow_dispatch`) to open the first sync PR.
4. Add the `@.playbook/CLAUDE.md` import and the `CODEOWNERS` entry in the consumer.

---

## 7️⃣ Principle

A standard that does not reach the place where work happens is a suggestion. Distribution makes
the playbook **enforceable everywhere**, while each repo still chooses *when* to adopt a change.
