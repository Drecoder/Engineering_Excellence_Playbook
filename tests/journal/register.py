"""
The CAPA register check (docs/FINDINGS_REGISTER.json, contract schemas/findings_register.v1).

The contract test validates the register's shape; this checks what the schema cannot:

- every journal entry has exactly one register row, and every row names a journal entry;
- a due date is at most the found date plus its severity's days: critical 7, high 30, medium 90,
  low 180;
- a closed finding was closed on or after it was found;
- an open finding past its due date is overdue: a warning on pull requests, a failure on the daily
  run (--mode scheduled), so a deadline cannot pass silently.

It also computes the control-effectiveness metrics and production readiness: not ready while any
critical or high finding in the security or governance category is open.

    python tests/journal/register.py JOURNAL REGISTER [--mode pr|scheduled] [--today YYYY-MM-DD]

Prints the metrics as Markdown (also appended to $GITHUB_STEP_SUMMARY when set). Exits 1 on an
error, or on an overdue finding in scheduled mode.
"""

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from journal_append_only import entries  # noqa: E402

SLA_DAYS = {"critical": 7, "high": 30, "medium": 90, "low": 180}
SEVERITIES = ["critical", "high", "medium", "low"]
GOVERNED = {"security", "governance"}
BLOCKING = {"critical", "high"}


def check(journal_text: str, register: dict, today: date) -> dict:
    errors, overdue = [], []
    headings = [h for h, _ in entries(journal_text)]
    findings = register["findings"]
    rows = {}
    for f in findings:
        if f["journal"] in rows:
            errors.append(f"{f['id']}: a second row for {f['journal']}")
        rows[f["journal"]] = f
    ids = [f["id"] for f in findings]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        errors.append(f"{dup}: id used more than once")
    for h in headings:
        if h not in rows:
            errors.append(f"no register row for journal entry: {h}")
    for j, f in rows.items():
        if j not in headings:
            errors.append(f"{f['id']}: names no journal entry: {j}")

    closed_days = []
    for f in findings:
        found, due = date.fromisoformat(f["found"]), date.fromisoformat(f["due"])
        limit = found + timedelta(days=SLA_DAYS[f["severity"]])
        if due > limit:
            errors.append(f"{f['id']}: due {due} is past the {f['severity']} deadline {limit}")
        if f["status"] == "open":
            if due < today:
                overdue.append(f"{f['id']} ({f['severity']}, due {due}): {f['journal'][3:]}")
        else:
            closed = date.fromisoformat(f["closed"])
            if closed < found:
                errors.append(f"{f['id']}: closed {closed} before it was found {found}")
            closed_days.append((closed - found).days)

    open_rows = [f for f in findings if f["status"] == "open"]
    blockers = [f for f in open_rows if f["severity"] in BLOCKING and f["category"] in GOVERNED]
    controls = register.get("controls", [])
    proven = sum(1 for c in controls if c["proven"])
    by_control = sum(1 for f in findings if f["detected_by"] == "control")
    return {
        "errors": errors,
        "overdue": overdue,
        "metrics": {
            "findings": len(findings),
            "open": len(open_rows),
            "open_by_severity": {s: sum(1 for f in open_rows if f["severity"] == s) for s in SEVERITIES},
            "controls_proven": proven,
            "controls_total": len(controls),
            "detected_by_control": by_control,
            "mean_days_to_close": round(sum(closed_days) / len(closed_days), 1) if closed_days else None,
            "overdue": len(overdue),
        },
        "production_ready": not blockers,
        "blockers": [f"{f['id']} ({f['severity']} {f['category']}): {f['journal'][3:]}" for f in blockers],
    }


def summary(result: dict) -> str:
    m = result["metrics"]
    pct = lambda a, b: f"{100 * a / b:.0f}%" if b else "n/a"  # noqa: E731
    sev = ", ".join(f"{s} {n}" for s, n in m["open_by_severity"].items())
    lines = [
        "### CAPA register",
        "",
        "| Metric | Value |",
        "| :--- | :--- |",
        f"| Findings | {m['findings']} ({m['open']} open: {sev}) |",
        f"| Control classes proven to fail on their defect | {m['controls_proven']} of {m['controls_total']} ({pct(m['controls_proven'], m['controls_total'])}) |",
        f"| Findings caught by a control, not a person | {m['detected_by_control']} of {m['findings']} ({pct(m['detected_by_control'], m['findings'])}) |",
        f"| Mean days from found to closed | {m['mean_days_to_close']} |",
        f"| Overdue | {m['overdue']} |",
        f"| Production ready | {'yes' if result['production_ready'] else 'no'} |",
    ]
    for b in result["blockers"]:
        lines.append(f"\nBlocks production: {b}")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    args = argv[1:]
    mode, today = "pr", date.today()
    if "--mode" in args:
        mode = args[args.index("--mode") + 1]
    if "--today" in args:
        today = date.fromisoformat(args[args.index("--today") + 1])
    if mode not in ("pr", "scheduled") or len(args) < 2:
        print("usage: register.py JOURNAL REGISTER [--mode pr|scheduled] [--today YYYY-MM-DD]", file=sys.stderr)
        return 2
    journal = Path(args[0]).read_text(encoding="utf-8")
    register = json.loads(Path(args[1]).read_text(encoding="utf-8"))
    result = check(journal, register, today)
    text = summary(result)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write(text)
    for e in result["errors"]:
        print(f"::error::CAPA register: {e}")
    level = "error" if mode == "scheduled" else "warning"
    for o in result["overdue"]:
        print(f"::{level}::CAPA register: overdue: {o}")
    if result["errors"] or (mode == "scheduled" and result["overdue"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
