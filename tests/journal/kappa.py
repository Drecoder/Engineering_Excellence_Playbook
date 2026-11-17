"""
Kappa-first learning (KAN-60 slice 3, the read side): before the Builder diagnoses or builds
anything, it reads what its own journal and register already know about the work.

Two commands, one retrieval:

- `slice` is the retrieval. From the register and the journal, it selects every finding that
  applies to a query (the component worked on, plus the rules and fingerprints the work touches)
  and prints each one's root cause, correction, preventive action and verification. That output
  is the context the next prompt (diagnosis) receives.
- `check` is the gate. It recomputes the same slice from Kappa as it stands on the base branch
  and refuses a learning record (schemas/kappa_learning.v1.schema.json) that omits an applicable
  finding, was made against other Kappa, reuses an earlier correction without re-checking it,
  says Kappa was unavailable (fail closed), or was committed after the implementation began.

The selection is deterministic and lexicographic, with no numeric weights
(06_AgentZone/09_Adaptive_Harness.md §4). A finding applies when it is:

- open in the queried component; or
- in the queried component and shares a queried rule; or
- shares a queried fingerprint, in any component; or
- related to one of those: a finding it recurs, a finding that recurs it, or a finding its journal
  entry cites by ID.

Closed findings count: a correction that was made before is exactly what the Builder must
re-check before it reuses it.

    python tests/journal/kappa.py slice --component playbook --fingerprint rule-without-control
    python tests/journal/kappa.py check RECORD --commits COMMITS.tsv --record-path .kappa/KAN-60.json

Standard library only: it runs in the same pinned python image as the journal checks.
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capa_project import entry_fields  # noqa: E402
from journal_append_only import entries  # noqa: E402

SCHEMA_VERSION = "kappa_learning.v1"
RECORD_DIR = ".kappa/"
FINDING_ID = re.compile(r"\bF-\d{4}\b")
# Entries written before the bold-list form (2026-11-08) use plain `Field: text` lines.
PLAIN_FIELD = re.compile(r"^(Rule|Problem|Detection|Root cause|Correction|Preventive action[^:]*|"
                         r"Verification|Evidence|Status|Residual): ?(.*)$")
CONTEXT_FIELDS = ("Problem", "Root cause", "Correction", "Preventive action", "Verification", "Status")
RELATIONS = ("same", "recurring", "related", "caused_by_prior_correction", "not_applicable")
CLASSIFICATIONS = ("new", "recurring", "related", "regression_of_prior_correction")
MIN_REASON = 10  # characters: "n/a" or "ok" is not a disposition


class KappaError(ValueError):
    pass


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fields_of(block):
    """{field: text} for an entry in either the bold-list form or the older plain form."""
    found = entry_fields(block)
    if found:
        return found
    out, current = {}, None
    for line in block.splitlines()[1:]:
        m = PLAIN_FIELD.match(line)
        if m:
            current = re.sub(r" \(.*\)$", "", m.group(1))
            out[current] = m.group(2)
        elif current and line.strip():
            out[current] += "\n" + line.strip()
    return out


def causal_text(heading, block):
    """Where an entry names the findings it is causally tied to: its heading, its root cause, its
    preventive action, and the "Related:" note of its evidence. A finding listed only as an example
    in a problem statement (F-0099 lists fourteen) is not a relation."""
    fields = fields_of(block)
    parts = [heading]
    parts += [v for k, v in fields.items() if k.startswith(("Root cause", "Preventive action"))]
    evidence = next((v for k, v in fields.items() if k.startswith("Evidence")), "")
    parts += [evidence.split("Related:", 1)[1]] if "Related:" in evidence else []
    return "\n".join(parts)


def retrieve(register, journal, component, rule_ids=(), fingerprints=()):
    """The applicable findings, in ID order: [{id, why, row, fields}]. Raises on an unknown component."""
    known = {c["id"] for c in register["components"]}
    if component not in known:
        raise KappaError(f"component {component!r} is not in the register's component registry")
    rows = {r["id"]: r for r in register["findings"]}
    blocks = {heading: block for heading, block in entries(journal)}
    rule_ids, fingerprints = set(rule_ids), set(fingerprints)

    why = {}
    for fid, row in rows.items():
        refs = row["refs"]
        here = component in refs["components"]
        reasons = []
        if here and row["status"] == "open":
            reasons.append(f"open in {component}")
        if here and rule_ids & set(refs["rule_ids"]):
            reasons.append("rule: " + ", ".join(sorted(rule_ids & set(refs["rule_ids"]))))
        if fingerprints & set(refs["fingerprints"]):
            reasons.append("fingerprint: " + ", ".join(sorted(fingerprints & set(refs["fingerprints"]))))
        if reasons:
            why[fid] = reasons

    related = {}
    for fid in list(why):
        row = rows[fid]
        links = set(row["refs"].get("recurs", []))
        links |= {o for o, r in rows.items() if fid in r["refs"].get("recurs", [])}
        links |= set(FINDING_ID.findall(causal_text(row["journal"], blocks.get(row["journal"], "")))) - {fid}
        for other in sorted(links):
            if other in rows and other not in why:
                related.setdefault(other, []).append(f"related to {fid}")
    why.update(related)

    out = []
    for fid in sorted(why):
        row = rows[fid]
        block = blocks.get(row["journal"])
        if block is None:
            raise KappaError(f"{fid}: its journal entry {row['journal']!r} is not in the journal")
        out.append({"id": fid, "why": why[fid], "row": row, "fields": fields_of(block)})
    return out


def render(found, query):
    """The slice as Markdown: the historical context handed to the diagnosis prompt."""
    q = ", ".join(f"{k}={v}" for k, v in query.items() if v)
    if not found:
        return f"# Kappa slice ({q})\n\nNo applicable prior findings. Record `result: none_found`.\n"
    lines = [f"# Kappa slice ({q})", "",
             f"{len(found)} applicable finding(s). Each needs a disposition in the learning record. "
             "History informs the diagnosis; it never overrides a gate or current evidence, and a "
             "prior correction is re-checked against today's code before it is reused.", ""]
    for f in found:
        row = f["row"]
        lines += [f"## {f['id']}: {row['journal'][15:]}", "",
                  f"- **Status:** {row['status']}, {row['severity']} {row['category']}; why: {'; '.join(f['why'])}",
                  f"- **Fingerprints:** {', '.join(row['refs']['fingerprints'])}"]
        if row["refs"].get("recurs"):
            lines.append(f"- **Recurs:** {', '.join(row['refs']['recurs'])}")
        if row.get("verification"):
            lines.append(f"- **Register verification:** {row['verification']}")
        for name in CONTEXT_FIELDS:
            text = next((v for k, v in f["fields"].items() if k.startswith(name)), None)
            if text:
                lines.append(f"- **{name}:** " + text.replace("\n", " "))
        lines.append("")
    return "\n".join(lines)


def parse_commits(tsv):
    """`sha<TAB>path` lines, first-parent order, a commit with no path on a line of its own."""
    commits = []
    for line in tsv.splitlines():
        if not line.strip():
            continue
        sha, _, path = line.partition("\t")
        if not commits or commits[-1][0] != sha:
            commits.append((sha, set()))
        if path:
            commits[-1][1].add(path)
    return commits


def check_order(commits, record_path):
    """Errors unless the record was committed before the first commit that changes anything else."""
    added_at = next((i for i, (_, paths) in enumerate(commits) if record_path in paths), None)
    first_work = next((i for i, (_, paths) in enumerate(commits) if paths - {record_path}), None)
    if added_at is None:
        return [f"{record_path} is not committed in this change"]
    if first_work is not None and first_work <= added_at:
        sha = commits[first_work][0][:12]
        return [f"the learning record was committed after the work began: {sha} changes "
                f"{', '.join(sorted(commits[first_work][1] - {record_path}))} before or with {record_path}. "
                "Kappa is consulted before diagnosis, so the record comes first, in its own commit"]
    return []


def record_paths(commits):
    return sorted({p for _, paths in commits for p in paths
                   if p.startswith(RECORD_DIR) and p.endswith(".json")})


def check_record(record, register, journal, register_text, journal_text):
    """Every way the record fails to show that applicable history was considered."""
    errors = []
    if record.get("schema_version") != SCHEMA_VERSION:
        return [f"schema_version is {record.get('schema_version')!r}, not {SCHEMA_VERSION}"]
    if record.get("agent") != register.get("agent"):
        errors.append(f"agent {record.get('agent')!r} is not this register's agent {register.get('agent')!r}: "
                      "an agent reads only its own journal")
    kappa = record.get("kappa", {})
    if kappa.get("status") != "consulted":
        return errors + [f"Kappa was not consulted ({kappa.get('status')!r}: {kappa.get('error', 'no reason')}). "
                         "The stage fails closed: retry the slice, or the owner records an exception"]
    if kappa.get("register_sha256") != sha256(register_text):
        errors.append("register_sha256 does not match the register on the base branch: re-run the slice "
                      "against current Kappa and update the record")
    if kappa.get("journal_sha256") != sha256(journal_text):
        errors.append("journal_sha256 does not match the journal on the base branch: re-run the slice "
                      "against current Kappa and update the record")
    q = record.get("query", {})
    try:
        required = {f["id"] for f in retrieve(register, journal, q.get("component"),
                                              q.get("rule_ids", []), q.get("fingerprints", []))}
    except KappaError as exc:
        return errors + [str(exc)]
    given = {}
    for f in record.get("findings", []):
        fid = f.get("id")
        if fid in given:
            errors.append(f"{fid} has two dispositions")
        given[fid] = f
    known = {r["id"] for r in register["findings"]}
    for fid in sorted(set(given) - known):
        errors.append(f"{fid} is not a finding in the register")
    for fid in sorted(required - set(given)):
        errors.append(f"{fid} applies to this work (the slice selects it) and has no disposition")
    result = record.get("result")
    if result == "none_found" and (required or given):
        errors.append("result is none_found, but the slice selects "
                      f"{len(required)} finding(s) and the record lists {len(given)}")
    if result == "matches" and not given:
        errors.append("result is matches, but no finding is listed")
    if result not in ("matches", "none_found"):
        errors.append(f"result {result!r} is neither matches nor none_found")
    for fid, f in sorted(given.items()):
        if f.get("relation") not in RELATIONS:
            errors.append(f"{fid}: relation {f.get('relation')!r} is not one of {', '.join(RELATIONS)}")
        if len((f.get("reason") or "").strip()) < MIN_REASON:
            errors.append(f"{fid}: the reason is missing or too short to be a disposition")
        if f.get("reuses_correction") and len((f.get("revalidation") or "").strip()) < MIN_REASON:
            errors.append(f"{fid}: reuses a prior correction without saying how it was re-checked "
                          "against the current code")
    cls = record.get("classification")
    if cls not in CLASSIFICATIONS:
        errors.append(f"classification {cls!r} is not one of {', '.join(CLASSIFICATIONS)}")
    elif cls == "new" and any(f.get("relation") in ("same", "recurring") for f in given.values()):
        errors.append("classification is new, but a finding is marked same or recurring")
    elif cls == "regression_of_prior_correction" and not any(
            f.get("relation") == "caused_by_prior_correction" for f in given.values()):
        errors.append("classification is regression_of_prior_correction, but no finding is marked "
                      "caused_by_prior_correction")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("slice", help="print the applicable findings")
    s.add_argument("--component", required=True)
    s.add_argument("--rule", action="append", default=[])
    s.add_argument("--fingerprint", action="append", default=[])
    s.add_argument("--format", choices=("md", "json"), default="md")
    c = sub.add_parser("check", help="check a learning record against the base branch's Kappa")
    c.add_argument("--commits", required=True, help="sha<TAB>path lines, first-parent order")
    c.add_argument("--head", default=".", help="the checkout holding the change's records")
    for p in (s, c):
        p.add_argument("--journal", default="docs/POC_JOURNAL.md")
        p.add_argument("--register", default="docs/FINDINGS_REGISTER.json")
    args = parser.parse_args(argv)

    journal_text = Path(args.journal).read_text(encoding="utf-8")
    register_text = Path(args.register).read_text(encoding="utf-8")
    register = json.loads(register_text)

    if args.cmd == "slice":
        found = retrieve(register, journal_text, args.component, args.rule, args.fingerprint)
        query = {"component": args.component, "rule_ids": args.rule, "fingerprints": args.fingerprint}
        if args.format == "json":
            print(json.dumps({"query": query, "register_sha256": sha256(register_text),
                              "journal_sha256": sha256(journal_text),
                              "findings": [{"id": f["id"], "why": f["why"]} for f in found]}, indent=2))
        else:
            print(render(found, query))
        return 0

    commits = parse_commits(Path(args.commits).read_text(encoding="utf-8"))
    paths = record_paths(commits)
    if len(paths) != 1:
        print(f"kappa: expected one learning record under {RECORD_DIR} in this change, found "
              f"{len(paths)}{': ' + ', '.join(paths) if paths else ''}. Run `kappa.py slice` before "
              "diagnosing and commit the record first (AGENTS.md -> Agent Rules)")
        return 1
    errors = check_order(commits, paths[0])
    record = json.loads((Path(args.head) / paths[0]).read_text(encoding="utf-8"))
    errors += check_record(record, register, journal_text, register_text, journal_text)
    for e in errors:
        print(f"kappa: {paths[0]}: {e}")
    if not errors:
        print(f"kappa: {paths[0]}: {len(record.get('findings', []))} finding(s) considered, "
              "committed before the work; Kappa digests match the base branch")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
