"""
The CAPA projector (KAN-60 slice 1): a `capa` issue, written through
.github/ISSUE_TEMPLATE/capa.yml, becomes its journal entry (docs/POC_JOURNAL.md) and its register
row (docs/FINDINGS_REGISTER.json). Nothing in either is written by hand, so the two cannot drift
from the issue, and a field is never cut (F-0089).

The issue number is the finding's ID (F-NNNN), and each row names its issue (`issue`,
owner/repo#N). Projection only appends: an issue whose ID is already in the register, or that a
row names (KAN-114: #103 was journaled by hand as F-0100), is left alone, so running it twice adds
nothing. Input that does not fit
the form (a missing required section, an unknown choice, a malformed date) is refused, never
repaired.

    gh api 'repos/OWNER/REPO/issues?labels=capa&state=all&per_page=100' > issues.json
    python tests/journal/capa_project.py issues.json            # writes both files
    python tests/journal/capa_project.py issues.json --check    # exits 1 if anything is unprojected

Standard library only: it runs in the same pinned python image as the journal checks.
"""

import argparse
import json
import re
import sys
import textwrap
from datetime import date, timedelta
from pathlib import Path


class ProjectionError(ValueError):
    pass


# The form's section labels, in form order: the projector's input contract. A renamed label in
# capa.yml fails test_every_form_label_is_known_to_the_projector.
FORM_LABELS = (
    "Journal heading", "Category", "Severity", "Detected by", "Found", "Rules", "Components",
    "Fingerprints", "Recurs", "Rule", "Problem", "Detection", "Root cause", "Correction",
    "Preventive action", "Verification", "Evidence", "Drafts for the owner",
)
OPTIONAL = {"Recurs", "Drafts for the owner"}

# The journal entry's CAPA fields, in entry order. "Status" follows them, set by the projector.
ENTRY_FIELDS = ("Rule", "Problem", "Detection", "Root cause", "Correction", "Preventive action",
                "Verification", "Evidence")
DRAFTABLE = ("Root cause", "Correction", "Preventive action", "Verification")

CHOICES = {
    "Category": ("security", "governance", "supply-chain", "ci", "reliability", "quality", "reuse"),
    "Severity": ("critical", "high", "medium", "low"),
    "Detected by": ("control", "person"),
}
# AGENTS.md -> Observability Rules: critical 7 days, high 30, medium 90, low 180.
DUE_DAYS = {"critical": 7, "high": 30, "medium": 90, "low": 180}

NO_RESPONSE = "_No response_"
WIDTH = 100
SECTION = re.compile(r"^### (.+?)\s*$", re.M)
FINDING_ID = re.compile(r"^F-\d{4}$")
ISSUE_URL = re.compile(r"^https://github\.com/([^/]+/[^/]+)/issues/(\d+)$")


def parse_form(body):
    """{label: text} for every `### Label` section of the form's output; "" for no response."""
    body = (body or "").replace("\r\n", "\n")
    marks = list(SECTION.finditer(body))
    form = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        text = body[m.end():end].strip("\n").strip()
        form[m.group(1)] = "" if text == NO_RESPONSE else text
    return form


def _form(issue):
    form = parse_form(issue.get("body"))
    for label in FORM_LABELS:
        if label in OPTIONAL:
            continue
        if not form.get(label, "").strip():
            raise ProjectionError(f"#{issue.get('number')}: the required section {label!r} is missing or empty")
    for label, options in CHOICES.items():
        if form[label] not in options:
            raise ProjectionError(f"#{issue.get('number')}: {label} {form[label]!r} is not one of {', '.join(options)}")
    try:
        date.fromisoformat(form["Found"])
    except ValueError:
        raise ProjectionError(f"#{issue.get('number')}: Found {form['Found']!r} is not a YYYY-MM-DD date") from None
    if "\n" in form["Journal heading"]:
        raise ProjectionError(f"#{issue.get('number')}: the Journal heading must be one line")
    return form


def _lines(text):
    return [line.strip() for line in text.splitlines() if line.strip()]


def _drafts(form):
    marked = set()
    for line in _lines(form.get("Drafts for the owner", "")):
        m = re.match(r"^- \[[xX]\] (.+)$", line)
        if m:
            marked.add(m.group(1).strip())
    return marked


def _blocks(text):
    """A field's text as ("p", paragraph) and ("li", item) blocks: hard-wrapped lines join into one
    paragraph, and a line starting with "- " or "* " starts a list item."""
    blocks = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            if blocks:
                blocks.append(("break", ""))
            continue
        item = re.match(r"^[-*] (.*)$", line)
        if item:
            blocks.append(("li", item.group(1)))
        elif blocks and blocks[-1][0] in ("p", "li"):
            blocks[-1] = (blocks[-1][0], f"{blocks[-1][1]} {line}")
        else:
            blocks.append(("p", line))
    return [b for b in blocks if b[0] != "break"]


def _wrap(text, first, rest):
    # Long tokens (URLs) go on a line of their own rather than being broken.
    return textwrap.wrap(text, width=WIDTH, initial_indent=first, subsequent_indent=rest,
                         break_long_words=False, break_on_hyphens=False)


def _field(label, text):
    out, first = [], True
    for kind, content in _blocks(text):
        if kind == "li":
            if first:
                out += _wrap(f"- **{label}:**", "", "  ")
                first = False
            out += _wrap(f"- {content}", "  ", "    ")
        else:
            out += _wrap(f"- **{label}:** {content}" if first else content, "" if first else "  ", "  ")
            first = False
    return out


def issue_ref(issue):
    """owner/repo#N for an issue, from its html_url: the register's `issue` field (KAN-114)."""
    m = ISSUE_URL.match(issue.get("html_url", ""))
    if not m:
        raise ProjectionError(f"#{issue.get('number')}: html_url {issue.get('html_url')!r} is not an issue URL")
    return f"{m.group(1)}#{m.group(2)}"


def _link(issue):
    m = ISSUE_URL.match(issue.get("html_url", ""))
    if not m:
        raise ProjectionError(f"#{issue.get('number')}: html_url {issue.get('html_url')!r} is not an issue URL")
    return f"[{m.group(1)}#{m.group(2)}]({issue['html_url']}) (the finding)"


def project_entry(issue):
    """The issue's journal entry: heading, the CAPA fields in order (DRAFT where the form marks
    it), and the status."""
    form = _form(issue)
    drafts = _drafts(form)
    lines = [f"## {form['Found']}: {form['Journal heading']}", ""]
    for name in ENTRY_FIELDS:
        label = f"{name} (DRAFT)" if name in drafts and name in DRAFTABLE else name
        text = form[name]
        if name == "Evidence":
            text = f"{_link(issue)}; {text}"
        lines += _field(label, text)
    lines.append("- **Status:** open.")
    return "\n".join(lines)


def entry_fields(entry):
    """{field name: text} read back from an entry; "(DRAFT)" is not part of the name."""
    fields, current = {}, None
    for line in entry.splitlines():
        m = re.match(r"^- \*\*(.+?):\*\* ?(.*)$", line)
        if m:
            current = re.sub(r" \(DRAFT\)$", "", m.group(1))
            fields[current] = m.group(2)
        elif current and line.startswith("  "):
            fields[current] += "\n" + line.strip()
    return fields


def _split(text):
    return _lines(text)


def project_row(issue):
    """The issue's register row (findings_register.v2)."""
    form = _form(issue)
    found = date.fromisoformat(form["Found"])
    refs = {"rule_ids": _split(form["Rules"]), "components": _split(form["Components"]),
            "fingerprints": _split(form["Fingerprints"])}
    recurs = _split(form.get("Recurs", ""))
    if recurs:
        bad = [r for r in recurs if not FINDING_ID.match(r)]
        if bad:
            raise ProjectionError(f"#{issue.get('number')}: Recurs {', '.join(bad)} is not a finding ID (F-NNNN)")
        refs["recurs"] = recurs
    return {
        "id": f"F-{int(issue['number']):04d}",
        "journal": f"## {form['Found']}: {form['Journal heading']}",
        "category": form["Category"],
        "severity": form["Severity"],
        "detected_by": form["Detected by"],
        "found": form["Found"],
        "due": (found + timedelta(days=DUE_DAYS[form["Severity"]])).isoformat(),
        "status": "open",
        "refs": refs,
        "issue": issue_ref(issue),
    }


def _is_capa(issue):
    return "pull_request" not in issue and any(
        (label.get("name") if isinstance(label, dict) else label) == "capa" for label in issue.get("labels", []))


def project(issues, journal, register):
    """Append every capa issue not yet in the register, in issue order. Returns the new journal
    text, the register (changed in place), and the IDs added."""
    known = {row["id"] for row in register["findings"]}
    # An issue a row names is journaled, whatever that row's ID (KAN-114: #103 is F-0100).
    named = {row["issue"] for row in register["findings"] if "issue" in row}
    added = []
    for issue in sorted((i for i in issues if _is_capa(i)), key=lambda i: int(i["number"])):
        if f"F-{int(issue['number']):04d}" in known or issue_ref(issue) in named:
            continue  # already projected; an issue from before the form is never parsed
        row = project_row(issue)
        entry = project_entry(issue)
        journal = journal.rstrip("\n") + "\n\n" + entry + "\n"
        register["findings"].append(row)
        known.add(row["id"])
        added.append(row["id"])
    return journal, register, added


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("issues", help="JSON list of issues, as the GitHub REST API returns them")
    parser.add_argument("--journal", default="docs/POC_JOURNAL.md")
    parser.add_argument("--register", default="docs/FINDINGS_REGISTER.json")
    parser.add_argument("--check", action="store_true", help="change nothing; exit 1 if a capa issue is unprojected")
    args = parser.parse_args(argv)
    issues = json.loads(Path(args.issues).read_text(encoding="utf-8"))
    journal_path, register_path = Path(args.journal), Path(args.register)
    journal = journal_path.read_text(encoding="utf-8")
    register = json.loads(register_path.read_text(encoding="utf-8"))
    try:
        journal, register, added = project(issues, journal, register)
    except ProjectionError as e:
        print(f"::error::{e}")
        return 1
    if args.check:
        if added:
            print(f"::error::unprojected capa issue(s): {', '.join(added)}")
            return 1
        print("every capa issue is projected")
        return 0
    if added:
        journal_path.write_text(journal, encoding="utf-8")
        register_path.write_text(json.dumps(register, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"projected {', '.join(added)}" if added else "nothing to project")
    return 0


if __name__ == "__main__":
    sys.exit(main())
