# Agentic Scrum: How the Owner and the Agents Run the Work

*Status: adopted 2026-11-25; the first formal Sprint is December 2026. Each capability below is marked
implemented or proposed, and nothing proposed counts until it is merged and verified.*

The factory has one person, who is its stakeholder, Product Owner and approver, and two AI agents
that do the engineering work (Claude and Codex). Agentic Scrum is how that work is planned,
inspected and improved each month. It is **Scrum-informed, not Scrum-compliant**: it keeps Scrum's
empiricism (transparency, inspection, adaptation) and its events, and it says plainly where it
differs from the Scrum Guide (§5).

---

## 1️⃣ Accountabilities

| Who | Holds |
| :--- | :--- |
| **The owner** | The Product Goal and every Sprint Goal; the backlog's order; every merge and every approval; Scrum Master accountability |
| **The agents** | Execution: they build, verify, report and record. They make claims; CI makes evidence (`AGENTS.md`, Agent Rules) |

Agents never approve, merge, deploy or change their evaluator. They work in staging (QA) or prod
and change things only through DEV (`01_Software_Factory.md` §5).

---

## 2️⃣ Artifacts

| Scrum artifact | In the factory |
| :--- | :--- |
| **Product Goal** | The MVP and its gates in the factory roadmap |
| **Product Backlog** | The board: one workflow for development work and CAPA findings (`01_Software_Factory.md` §3) |
| **Sprint Goal** | Set and approved by the owner at Planning, with pass/fail acceptance criteria; a weighted score is reported but never offsets a failed mandatory criterion |
| **Sprint Backlog** | The ticket keys listed in the Sprint's planning record |
| **Increment and Definition of Done** | Done means merged and verified on the default branch, with evidence maturity from EXISTS to OPERATIONALLY VERIFIED |

---

## 3️⃣ Events

| Event | When | Who | Record |
| :--- | :--- | :--- | :--- |
| **Sprint** | One calendar month | Everyone | The Sprint's folder in the shared-intelligence repository |
| **Sprint Planning** | First weekday | The owner, with an agent | `planning.md`: Sprint Goal and criteria, backlog keys, environment assignments, observation objectives |
| **Daily Standup Summary** | Every day, by an existing scheduled task | An agent | `daily/YYYY-MM-DD.md`: progress, Sprint Goal criteria, verified work, blockers, owner decisions, evidence |
| **Backlog refinement** | Continuous | The owner and the agents | Refinement candidates in each daily record; changes on the board |
| **Sprint Review** | Last weekday | The owner, with an agent | `review.md`: each criterion met or not, a written re-grade, roadmap adaptation |
| **Sprint Retrospective** | Last weekday, after the Review | The owner, with an agent | `retrospective.md`: systemic improvements and candidate actions |

- **Agent reports are not records until approved.** A daily record is an agent report until the
  owner merges it to the default branch; until then it is cited as pending.
- **The Daily is a report, not a meeting.** It reconciles the board, the repositories, CI and the
  CAPA register, and notifies the owner only when a human decision is needed.
- **Retrospectives read evidence.** For the Sprint's dates, they read the CAPA register, the
  board's history, pull requests and CI runs, and the agents' handoffs, and look for systemic
  causes: recurring defect fingerprints, blocked chains, rework. Actions go to existing tickets or
  to the `capa-issue` process, and stay candidates until the next Planning.
- **Outcomes are labelled.** Every retrospective claim is marked as an actual result (with its
  evidence), an owner decision, agent execution, or an inferred conclusion.

---

## 4️⃣ Continuous Improvement and Shared Intelligence

- **CAPA is the corrective memory.** Every finding is journaled, ranked and tracked to closure in
  the register (`AGENTS.md`, Observability Rules); the retrospective reads it rather than copying it.
- **Shared intelligence is one environment with many producers.** Handoffs, daily and Sprint records
  live in one private repository both agents read, next to the standards and the register they
  link to. A memory provider may cache them for an agent, but the repositories stay the record.
- **The factory improves itself under governance.** New versions of factory capabilities follow the
  lifecycle in `01_Software_Factory.md` §5: built through DEV, observed in QA, approved for PROD.

---

## 5️⃣ Where It Differs from the Scrum Guide

| Scrum Guide | Agentic Scrum | Why |
| :--- | :--- | :--- |
| Product Owner and Scrum Master are separate accountabilities, usually different people | One person holds both, and approves every merge | There is one human |
| Developers are people | The Developers are two AI agents, directed by the owner | Execution is delegated; judgment and approval are not |
| The Daily Scrum is a 15-minute event of the Developers | An asynchronous, evidence-linked report | The agents work in sessions, not in shared time |
| Sprint Goals are commitments the Scrum Team crafts | The owner sets them, with measurable criteria; when a full goal is not realistic, a Sprint-level step toward it is chosen instead | Honest forecasting over arbitrary deadlines |
| Teams commonly track Sprints on a Scrum board | A Kanban board, with the Sprint Backlog listed in the planning record | One workflow for development and CAPA work |

---

## 6️⃣ Implemented and Proposed

| Capability | State |
| :--- | :--- |
| The board, one workflow, evidence maturity | Implemented |
| The CAPA journal and register | Implemented |
| Shared handoffs between the agents | Implemented |
| Agents opening pull requests under their own GitHub App identity | Implemented and verified |
| The daily reconciliation task | Implemented; its standup output and records are proposed |
| Monthly Planning, Review and Retrospective records | Proposed; first Sprint December 2026 |
| A dedicated Scrum calendar | Proposed; not connected |
| Environment enforcement by Genesis | Proposed (§5 of `01_Software_Factory.md`) |

Results are added here only after a Sprint Review, and only with their evidence.

---

## Principle

Scrum's events are kept because they make the work inspectable, not because the Guide requires
them. Where one person and two agents differ from a Scrum Team, the difference is written down.
