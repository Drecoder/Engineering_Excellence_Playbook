# Agent Notepad

*One place for every piece of work: each agent gets a notebook, each task a folder, and every push
saves a read-only page.*

**Status: design.** This is the agreed target; it is not implemented yet. Today agents run as
command-line tools that take a spec in and return a result, and working notes live in chat
transcripts, open tabs, and loose files that are never saved or cataloged.

The notepad is a service that gives every agent on the platform its own folder, through the same
injected interface (`Notepad`), the way the model is injected (`01_Agent_Standards.md` §4). It
replaces the command line as the way to work with an agent: a person or an event writes into the
agent's folder, and the agent answers there. The first goal is plain: keep work on track, so every
question, decision, and result has one cataloged place instead of hundreds of unsaved notes.

Code never lives in the notepad. Agents change code the way a coding assistant does: edit files in a
checkout, commit, and push to the repository. The notepad holds everything around the code: the
questions, the reasoning, the tool results, the findings, and the decisions.

---

## 1️⃣ Layout

```text
<project>/<agent>/<spec_id>/<task_id>/
    wip/        the working copy
    v1/ v2/ …   sealed versions, one per push
```

| Level | Is | Why it is a level |
| :--- | :--- | :--- |
| `project` | The software factory itself, or a service the factory builds that lives outside it | The strongest boundary: its own key, its own RAG namespace, its own retention (§8) |
| `agent` | An agent type: Builder, Reviewer, and any added later | The isolation boundary between agents (§6) |
| `spec_id` | One feature: an approved spec (`03_Software_Factory_Intake.md`) | Groups the tasks a spec was decomposed into |
| `task_id` | One `builder.spec.v1` task | Where work in progress, seals, leases, and round counts live |

Every level is a platform ID, never a free-text name, so paths are deterministic, validated, and
cannot carry traversal. The same IDs appear in every agent's folder, so one task's history joins
across agents by path.

## 2️⃣ Two States: Work in Progress and Sealed

| | WIP | Sealed |
| :--- | :--- | :--- |
| Is | The working copy before a push | A snapshot taken at a push, bound to that commit |
| Writable | Yes, region by region (§3) | Never, by anyone |
| Stored | The service's working store | The object store, under `v<n>/`, with object lock |
| Counts as | Work in progress | Record |
| Indexed for retrieval | Never | Yes, as pointers (§7) |

- **Each push seals a version; the folder never freezes.** Review continues after a pull request
  opens, so each push seals `v<n>` and the working copy carries on as the next version. A sealed
  version is never edited; a change is a new version, the same rule as for specs.
- **Seal before push.** The agent calls `seal()`; the service snapshots the task folder and returns
  the digest of its manifest (each file's SHA-256, the task, the version, the writer's identity, and
  the digest of the previous version). The agent commits with a `Notepad-Manifest: sha256:…`
  trailer and pushes. Sealing after the push would let the working copy change in between.
- **The gate checks the seal.** Central CI fails a push whose trailer is missing or names no sealed
  manifest. The claim check for the push (`review.requested`, `05_Review_Loop.md`) carries both the
  head SHA and the manifest digest, so code and notes point at each other.
- **Read-only three times.** The service refuses writes to a sealed version; IAM denies put and
  delete on sealed prefixes, even to the service's own role; object lock refuses overwrite and
  deletion until retention ends, whatever IAM says.
- **A hash chain.** Each manifest names the one before it and the inputs it answered, so a missing or
  altered version is visible.
- **Failed pushes are sealed too**, marked `gates: failed`, for triage. They are never indexed, so a
  failed attempt is never retrieved as an example.

## 3️⃣ Ownership by Region

Each file in a task folder belongs to a **channel type** that declares who owns which region. The
service enforces the declaration at write time; central CI checks the same declaration on any change
a person pushes. One declaration feeds both, from `schemas/`.

| Region | Owner | Example |
| :--- | :--- | :--- |
| Human-owned | People only, by role | Answers, acceptances, review dispositions |
| Agent append-only | The folder's agent, adding only | New questions, thought-log entries, findings |
| Tool output | Written by the service from the tool result; read-only to everyone | A scan, a plan, a conflict report |
| Inputs | Placed by the service, verified by digest; read-only | The approved spec, the other side's sealed findings |

- **The spec wizard is the first channel type**: question blocks the agent may append and, while a
  block is open, reword; answers and the transitions to answered, accepted, and deferred belong to
  people. Promotion needs every blocking question accepted by its human owner, not just answered.
- **Instructions are separate from state.** An agent's system prompt is a versioned, read-only file
  pinned by digest, never part of its folder, so an agent cannot edit its own guardrails.
- **Human text is data.** What a person writes is a decision, and it still enters a prompt delimited
  as data, like any input.

## 4️⃣ Tools Act for the Agent

An agent's tool calls are the agent's actions (`01_Agent_Standards.md` §1a). The result lands in the
**calling agent's** folder, attributed to the agent, in a tool-output region the agent cannot edit.

- The tool runs with the agent's permissions and no more; a tool is never a path to more privilege.
- Each record names the tool and version, the image digest it ran in, and its exact inputs, so anyone
  can rerun it and get the same result. A reproducible tool result can reach evidence tier
  `VERIFIED`; a model's claim enters at `CLAIMED` (`02_Compliance_Engine.md`).
- Any agent added later, for example a security agent, follows the same pattern. Adding an agent is
  still a rule change that needs a measured reason: security today is a Reviewer lens, not an agent.

## 5️⃣ A Review Round, and a Merge Conflict

| Step | Who | Notepad |
| :--- | :--- | :--- |
| 1 | Builder | Seals `v1` and pushes; once the gates pass, `review.requested` claim-checks the push |
| 2 | Reviewer | Works in its own folder; seals its findings (`review_findings.v1`) when it publishes `review.completed`. The pull request comments are rendered from that object, each carrying its fingerprint |
| 3 | A person | Records a disposition for each fingerprint (agree, disagree with a reason, or a comment) and adds suggestions, in the human-owned region; sealed on submit (`review_disposition.v1`, to be defined) |
| 4 | Service | Opens the Builder's `v2` working copy with the sealed findings and dispositions as read-only inputs. The Builder never reads the Reviewer's folder |
| 5 | Builder | Answers each fingerprint (fixed, or disputed with a reason), seals `v2`, and pushes; the next round starts |

- **Dispositions steer the loop.** Disagreeing waives a fingerprint: it starts no further round and
  is not raised again. A person's suggestion enters the next round as a finding labelled
  human-sourced. Merge approval stays with branch protection; nothing in the notepad approves a
  merge.
- **Round counting reads only seals.** Stalled and oscillating rounds are computed by code from
  sealed manifests, never from a working copy or a model's account.
- **Merge conflicts use the same path** (`06_Merge_Conflicts.md`). Conflict detection is the
  Builder's tool call, so the `merge_conflict.v1` report lands in the Builder's folder as tool
  output. The resolution is a sealed version whose manifest records each hunk's route, the lines
  kept, and any line deliberately removed with its reason, so the merge-resolution lens checks for
  dropped lines in code. **One resolver at a time** is a lease on the branch, held by the service,
  with an expiry. A conflict resolution counts against the Builder's budget, not as a review round.

## 6️⃣ Least Privilege, in Depth

Each layer assumes the one before it can fail (`00_UniversalStandards/07_Security_In_Depth.md`).

| Layer | Notepad control |
| :--- | :--- |
| Human authentication | SSO with MFA |
| Human authorization | A role map; only a block's owner accepts it; no self-acceptance |
| Agent identity | Short-lived workload identity. The service takes the project, agent, and task from the token's claims, never from a path the agent passes |
| Agent authorization | The service resolves paths inside the scoped root, rejects traversal and symlinks, allow-lists extensions, and enforces regions; storage IAM allows only the session's project, agent, and task prefix; the key's encryption context binds the same IDs, so a misrouted read fails to decrypt |
| In transit | mTLS between agents and the service |
| At rest | A key per project, no public access, versioning, object lock on sealed versions |
| Model context | Secret scanning on every write; untrusted text stays delimited |
| Detection | Every operation is a span, a log line with `trace_id`, and a metric; a denied operation alerts and gets an incident record |

- **No reads across agents.** Handoffs are events with claim checks; otherwise the notepad becomes a
  side channel around the event backbone.
- **On the code side**, each agent pushes as its own GitHub App with installation tokens of an hour
  at most, installed only on its project's repositories, without the workflows permission, limited
  by rulesets to its own branch pattern, with signed commits; merges need human approval.
- **The service owns its storage.** Nothing reads or writes the store except through the service.
- **Notes never authorize work.** Work still enters as an approved spec; a note can ask, record,
  and request read-only research.

## 7️⃣ Memory

Four memory states, each with its own writer, lifetime, and trust:

| | Context window | Notepad | Retrieval index | Model weights |
| :--- | :--- | :--- | :--- | :--- |
| Holds | One call | One task's working memory and its sealed record | Pointers to decisions and their reasons | General knowledge |
| Written by | The context assembler | Agents and people, by region | Only the indexing pipeline, from sealed objects | The model provider; changed only by configuration |
| Trust | What was loaded into it | People's regions are decisions; agents' regions are claims | Each entry carries its evidence tier | Never evidence |

- **Code builds the context, not the model.** A deterministic assembler builds each call from seals
  within an explicit context budget. Each round starts fresh from sealed inputs instead of a growing
  history, which keeps calls small and runs reproducible. The saving is visible in the GenAI token
  attributes on every span; it needs no separate benchmark, and the agent's golden tasks still run
  before the assembler ships.
- **The index holds pointers, not content.** An entry is an embedding plus tags: the sealed
  manifest's address and digest, the repository and commit of the change, the fingerprint, rule,
  lens, disposition, evidence tier, IDs, and embedding model version. Retrieval fetches from the
  object store and the repository **with the caller's identity**, verifies the digest, and loads the
  content as data. Access control stays where the data lives, retention follows the source, and the
  index can be rebuilt from the store at any time.
- **What is indexed:** one resolution record per fingerprint (finding, disposition, and the change
  that resolved it, or the reason it was waived), at merge, pointing at the merge commit. Waivers are
  indexed so a rejected finding is not raised again. Not indexed: events, working copies, failed
  pushes, abandoned pull requests, mechanical conflict hunks.
- **When memories disagree:** playbook rules first, then a person's decision, then `VERIFIED` and
  `OBSERVED` entries, then claims, then the model's general knowledge.
- **Weights are not a memory path.** Nothing an agent does at runtime changes model weights;
  fine-tuning from the record stays closed unless decided as a protected change.

## 8️⃣ Projects Are Injected

The factory core is generic. A project is a set of bindings, read from its configuration
(`project.v1`, to be defined) by a composition root that validates it and hands each agent its
scoped handles:

| Interface | Bound per project |
| :--- | :--- |
| `Notepad`, `ObjectStore` | The folder root and storage: shared bucket, dedicated bucket, or the owner's own account |
| `KeyProvider` | The project's key |
| `RepoHost` | The project's repositories and the app installations scoped to them |
| `VectorIndex` | The project's retrieval namespace; no retrieval across projects by default |
| `Model` | The model ladder, which an owner's terms may constrain |

- **The configuration is a boundary.** It carries the owner, classification, residency, retention,
  whether lessons may feed shared knowledge, and the storage isolation. An invalid configuration is
  rejected, not repaired; at startup the root checks that each binding belongs to the project and
  fails closed; weakening isolation, allowing shared learning, or changing the owner needs human
  approval.
- **Built for one owner, ready for more.** A key per project and the project ID on every path, tag,
  index entry, span, and claim check from the start; a dedicated bucket or account only when an
  owner's terms require it, vended through Genesis.
- **The notepad stays inside the factory**, even for a service that lives outside it, and the sealed
  history of a project can be exported to its owner.

## 9️⃣ What the Record Is For

Every agent, tool result, handoff, and decision lands in the same sealed, chained record, so each
task carries the story of its whole life cycle: the spec questions, the build, every review round and
disposition, conflict resolutions, the merge, the release token, and any incident.

- **Staying on track:** one place per task, nothing lost in an open tab.
- **Evidence for autonomy:** human dispositions against findings show whether a human step catches
  what machines miss (`00_UniversalStandards/10_Autonomy_by_Evidence.md`).
- **Provenance:** an artifact's provenance can lead back to the story that produced it.
- **Incidents** start from the chain instead of screenshots.
- **Teaching material:** the story of a public project can be narrated, through text-to-speech, into
  educational video. Private and client projects are never used.

## 🔟 First Slice

Build the notebook first; the rest grows on it.

1. The notepad service with one storage backend, serving the Builder, with the layout of §1 and the
   project ID and key from day one.
2. Seal before push, the trailer, and the central CI check.
3. The review round of §5: sealed findings, dispositions, and the Builder's next working copy.

Then the retrieval index, project configurations beyond the key, the export bundle, and the spec
wizard channel.

## Open Decisions

Recorded here until decided, each by a reviewed change to this document:

- Whether any command-line entry point survives, for local runs or golden tasks, or both go through
  the notepad with an in-memory backend.
- How people reach their side: through the service only, or also by pull request with CI as the
  check.
- Where the working copy is stored before a seal, and how long an idle working copy lives.

---

## Principle

Give every piece of work one place, let each party write only its own part, seal what was pushed, and
remember by pointing at the record instead of copying it.
