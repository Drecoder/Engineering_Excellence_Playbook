"""
The CAPA register check (docs/FINDINGS_REGISTER.json, contract schemas/findings_register.v2;
findings_register.v1 is still accepted until V1_ACCEPTED_UNTIL).

The contract test validates the register's shape; this checks what the schema cannot:

- every journal entry has exactly one register row, and every row names a journal entry;
- a due date is at most the found date plus its severity's days: critical 7, high 30, medium 90,
  low 180;
- a closed finding was closed on or after it was found;
- an open finding past its due date is overdue: a warning on pull requests, a failure on the daily
  run (--mode scheduled), so a deadline cannot pass silently.

For findings_register.v2 it also resolves every reference the CAPA graph will read
(06_AgentZone/10_CAPA_Graph_and_Risk_Weighted_Learning.md §4), and rejects one that does not:

- a rule ID names a rule that exists: ARCH-NNN in schemas/architecture_rules.v1.json, SEC-NNN in
  00_UniversalStandards/07_Security_In_Depth.md, GOV-NNN in schemas/governance_baseline.v1.json;
  PATH#HEADING names a playbook Markdown file and one of its headings (a leading emoji number
  may be left out);
- components, and their dependencies, are in the register's component registry;
- anti-pattern IDs are in schemas/antipatterns.v1.json;
- a finding recurs only an earlier finding: one closed before it was found, sharing a fingerprint
  and a rule.

It also computes the control-effectiveness metrics and production readiness: not ready while any
critical or high finding in the security or governance category is open.

    python tests/journal/register.py JOURNAL REGISTER [--mode pr|scheduled] [--today YYYY-MM-DD]

Prints the metrics as Markdown (also appended to $GITHUB_STEP_SUMMARY when set). Exits 1 on an
error, or on an overdue finding in scheduled mode.
"""

import json
import os
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from journal_append_only import entries  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
V1, V2 = "findings_register.v1", "findings_register.v2"
V1_ACCEPTED_UNTIL = date(2027, 2, 8)  # 90 days after v2; then v1 is refused (AGENTS.md -> Reuse Rules)

SLA_DAYS = {"critical": 7, "high": 30, "medium": 90, "low": 180}
SEVERITIES = ["critical", "high", "medium", "low"]
GOVERNED = {"security", "governance"}
BLOCKING = {"critical", "high"}


FENCE = re.compile(r"^(```|~~~)")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
NUMBER = re.compile(r"^[^A-Za-z\s]*[^A-Za-z\s][a-z]?$")  # "3️⃣", "3️⃣a", "1.", "🔟"


def headings(path: Path) -> set[str]:
    """Every heading of a Markdown file outside code fences, also without a leading number."""
    out, fenced = set(), False
    for line in path.read_text(encoding="utf-8").splitlines():
        if FENCE.match(line.strip()):
            fenced = not fenced
            continue
        m = None if fenced else HEADING.match(line)
        if m:
            text = m.group(1).strip()
            out.add(text)
            first, _, rest = text.partition(" ")
            if rest and NUMBER.match(first):
                out.add(rest.strip())
    return out


def catalogs(root: Path) -> dict:
    load = lambda rel: json.loads((root / rel).read_text(encoding="utf-8"))  # noqa: E731
    sec = (root / "00_UniversalStandards/07_Security_In_Depth.md").read_text(encoding="utf-8")
    return {
        "ARCH": {r["id"] for r in load("schemas/architecture_rules.v1.json")["rules"]},
        "GOV": {c["id"] for c in load("schemas/governance_baseline.v1.json")["controls"]},
        "SEC": set(re.findall(r"`(SEC-[0-9]{3})`", sec)),
        "AP": {r["id"] for r in load("schemas/antipatterns.v1.json")["rules"]},
    }


def check_refs(register: dict, root: Path = ROOT) -> list[str]:
    """Resolve every findings_register.v2 reference against its source; one error per miss."""
    errors, cat, docs = [], catalogs(root), {}
    comps = [c["id"] for c in register["components"]]
    for dup in sorted({c for c in comps if comps.count(c) > 1}):
        errors.append(f"component {dup}: id used more than once")
    for c in register["components"]:
        for d in c["depends_on"]:
            if d["component"] not in comps:
                errors.append(f"component {c['id']}: depends on unknown component {d['component']}")
            elif d["component"] == c["id"]:
                errors.append(f"component {c['id']}: depends on itself")
    by_id = {f["id"]: f for f in register["findings"]}
    for f in register["findings"]:
        refs, fid = f["refs"], f["id"]
        for rule in refs["rule_ids"]:
            if "#" in rule:
                rel, _, head = rule.partition("#")
                path = (root / rel).resolve()
                if root.resolve() not in path.parents or not path.is_file():
                    errors.append(f"{fid}: rule {rule}: no playbook file {rel}")
                    continue
                if rel not in docs:
                    docs[rel] = headings(path)
                if head not in docs[rel]:
                    errors.append(f"{fid}: rule {rule}: {rel} has no heading {head!r}")
            elif rule not in cat[rule.split("-")[0]]:
                errors.append(f"{fid}: rule {rule} is not in its catalog")
        for c in refs["components"]:
            if c not in comps:
                errors.append(f"{fid}: unknown component {c}")
        for ap in refs.get("antipattern_ids", []):
            if ap not in cat["AP"]:
                errors.append(f"{fid}: {ap} is not in the anti-pattern catalog")
        for prior_id in refs.get("recurs", []):
            prior = by_id.get(prior_id)
            if prior is None or prior_id == fid:
                errors.append(f"{fid}: recurs {prior_id}, which is not another finding in this register")
                continue
            if prior["status"] == "open" or date.fromisoformat(prior["closed"]) >= date.fromisoformat(f["found"]):
                errors.append(f"{fid}: recurs {prior_id}, which was not closed before {fid} was found")
            if not set(prior["refs"]["fingerprints"]) & set(refs["fingerprints"]):
                errors.append(f"{fid}: recurs {prior_id} but shares no fingerprint with it")
            if not set(prior["refs"]["rule_ids"]) & set(refs["rule_ids"]):
                errors.append(f"{fid}: recurs {prior_id} but shares no rule with it")
    return errors


def check(journal_text: str, register: dict, today: date, root: Path = ROOT) -> dict:
    errors, overdue = [], []
    version = register.get("schema_version")
    if version == V2:
        errors.extend(check_refs(register, root))
    elif version == V1:
        if today > V1_ACCEPTED_UNTIL:
            errors.append(f"{V1} was accepted until {V1_ACCEPTED_UNTIL}; migrate the register to {V2}")
    else:
        errors.append(f"unsupported register version {version!r}; expected {V2} (or {V1} until {V1_ACCEPTED_UNTIL})")
        return {"errors": errors, "overdue": [], "metrics": {}, "production_ready": False, "blockers": []}
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
    if not result["metrics"]:
        return "### CAPA register\n\nNot checked: the register's version is not supported.\n"
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
        f"| Findings recorded as caught by a control (attribution set by hand, not verified) | {m['detected_by_control']} of {m['findings']} ({pct(m['detected_by_control'], m['findings'])}) |",
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
