# Post-Mortem Template

*Structured approach for analyzing incidents and improving platform flow.*

Every failure **and every near miss** gets a record, not only outages. A near miss caught in review
(a change that would have broken the pipeline that applies it) teaches as much as an outage and
costs nothing to write down while the evidence is fresh.

Records live in the affected repo under `docs/incidents/`, one file per incident
(`YYYY-MM-DD-INC-NNN-<slug>.md`), with an index (`docs/incidents/README.md`) listing ID, date,
title, severity, detection method, time to detect, time to resolve, and the fixing change. Every
record points at evidence that can be checked: workflow run IDs, log queries, trace IDs, metric
queries, and PRs. A record whose claims cannot be traced to evidence says so explicitly ("not
determined") rather than guessing.

---

## 1️⃣ Incident Summary

- **ID / Severity:** `INC-NNN`; Low, Medium, High, Critical, or Near miss
- **Date / Time:** Start and end, UTC
- **Service / System Affected:**
- **Impact:** (Users, data, SLAs, delayed or partial changes)
- **Detection Method:** Alert (name it), failing gate or job, code review, or **manual
  investigation**. Manual detection is itself a finding: it means a signal was missing.
- **Time to detect / Time to resolve:**

---

## 2️⃣ Timeline of Events

| Time (UTC) | Action / Observation | Responsible |
| :--------- | :------------------- | :---------- |
|            |                      |             |
|            |                      |             |

---

## 3️⃣ Root Cause Analysis

- **Trigger:** what started it
- **Systemic issue:** why the system let it happen
- **Contributing factors:** including missing signals (why it was not detected sooner)

---

## 4️⃣ Resolution & Mitigation

- Steps taken to resolve the incident
- Immediate fixes applied (link the change)
- Lessons learned for future prevention

---

## 5️⃣ Preventive Actions

Each action has an owner and a target. When detection was manual, at least one action adds the
missing signal (a metric, an alert, or a test).

| Action Item | Owner | Target Date | Status |
| :---------- | :---- | :---------- | :----- |
|             |       |             |        |
|             |       |             |        |

---

## 6️⃣ Evidence

- Workflow / job runs:
- Log queries (exact text, so anyone can rerun them):
- Trace IDs / metric queries:
- Changes (PRs) that fixed it:

---

## 7️⃣ Principle

I treat post-mortems as **flow learning sessions**: not blame, but structured insight into **how
systems, processes, and humans interact**.

The goal is **continuous improvement**, operational clarity, and reducing repeat incidents. An
incident history kept as structured records with evidence is part of the platform's proof that it
works, not a diary.
