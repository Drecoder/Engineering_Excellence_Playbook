"""
Tests for the CAPA projector (tests/journal/capa_project.py, KAN-60 slice 1): a `capa` issue,
written through .github/ISSUE_TEMPLATE/capa.yml, becomes its journal entry and its register row,
and nothing in either is written by hand.

The first case is F-0089's: the hand projection of 2026-11-16 kept only the first line of each
bullet and cut three of F-0087's fields mid-sentence. fixtures/capa/issue-87.txt is #87's content in
the form's output, and its Problem, Root cause and Evidence span several lines.

    python -m unittest discover -s tests/journal -v
"""

import copy
import json
import re
import sys
import unittest
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
from capa_project import (  # noqa: E402
    ENTRY_FIELDS,
    FORM_LABELS,
    ProjectionError,
    entry_fields,
    parse_form,
    project,
    project_entry,
    project_row,
)
from journal_append_only import violations as append_only_check  # noqa: E402
from register import check as register_check  # noqa: E402

FIXTURES = HERE / "fixtures" / "capa"
ISSUE_87 = (FIXTURES / "issue-87.txt").read_text()
URL = "https://github.com/Drecoder/Engineering_Excellence_Playbook/issues/"


def words(text: str) -> str:
    return " ".join(text.split())


def issue(number: int, body: str, labels=("capa",), state="open") -> dict:
    return {"number": number, "body": body, "labels": [{"name": n} for n in labels],
            "state": state, "html_url": f"{URL}{number}"}


class ParseForm(unittest.TestCase):
    def test_reads_every_section(self):
        form = parse_form(ISSUE_87)
        self.assertEqual(form["Journal heading"],
                         "Dependabot cannot read the private central CI, so its run on main fails")
        self.assertEqual(form["Components"], "coqui-tts\naws-builder-agent\nsovereign-vpc-gcp")
        self.assertEqual(form["Recurs"], "")

    def test_a_missing_required_section_is_refused_not_repaired(self):
        body = re.sub(r"### Detection\n\n.*?\n\n", "", ISSUE_87, flags=re.S)
        with self.assertRaisesRegex(ProjectionError, "Detection"):
            project_entry(issue(87, body))

    def test_an_unknown_choice_is_refused(self):
        body = ISSUE_87.replace("### Severity\n\nlow", "### Severity\n\nlowish")
        with self.assertRaisesRegex(ProjectionError, "Severity"):
            project_row(issue(87, body))

    def test_every_form_label_is_known_to_the_projector(self):
        form = (ROOT / ".github" / "ISSUE_TEMPLATE" / "capa.yml").read_text()
        labels = re.findall(r"^      label: (.+)$", form, flags=re.M)
        self.assertEqual(sorted(labels), sorted(FORM_LABELS))


class Entry(unittest.TestCase):
    def setUp(self):
        self.entry = project_entry(issue(87, ISSUE_87))

    def test_a_field_on_several_lines_projects_whole(self):
        # F-0089: the hand projection kept only each field's first line.
        form = parse_form(ISSUE_87)
        projected = entry_fields(self.entry)
        for name in ("Problem", "Root cause", "Evidence"):
            self.assertIn("\n", form[name], f"{name}: the fixture must span lines to test this")
            self.assertTrue(words(projected[name]).endswith(words(form[name])), name)

    def test_every_field_is_the_issue_text_word_for_word(self):
        form = parse_form(ISSUE_87)
        projected = entry_fields(self.entry)
        for name in ENTRY_FIELDS:
            want = words(form[name])
            if name == "Evidence":
                want = f"[Drecoder/Engineering_Excellence_Playbook#87]({URL}87) (the finding); " + want
            self.assertEqual(words(projected[name]), want, name)

    def test_heading_order_drafts_and_status(self):
        lines = self.entry.splitlines()
        self.assertEqual(lines[0], "## 2026-11-16: Dependabot cannot read the private central CI, "
                                   "so its run on main fails")
        labels = re.findall(r"^- \*\*(.+?):\*\*", self.entry, flags=re.M)
        self.assertEqual(labels, ["Rule", "Problem", "Detection", "Root cause (DRAFT)",
                                  "Correction (DRAFT)", "Preventive action (DRAFT)",
                                  "Verification (DRAFT)", "Evidence", "Status"])
        self.assertEqual(lines[-1], "- **Status:** open.")

    def test_lines_are_wrapped_and_never_break_a_word(self):
        for line in self.entry.splitlines():
            if " " in line.strip():
                self.assertLessEqual(len(line), 100, line)
        self.assertIn(f"({URL}87)", self.entry)

    def test_a_list_inside_a_field_stays_a_nested_list(self):
        body = ISSUE_87.replace("### Correction\n\n",
                                "### Correction\n\ntwo steps:\n- first step\n- second step\n\n### X\n\n", 1)
        body = body.replace("\n\n### X\n\n", " ", 1)
        entry = project_entry(issue(87, body))
        self.assertIn("\n  - first step\n  - second step", entry)


class Row(unittest.TestCase):
    def test_row_from_the_form(self):
        row = project_row(issue(87, ISSUE_87))
        self.assertEqual(row, {
            "id": "F-0087",
            "journal": "## 2026-11-16: Dependabot cannot read the private central CI, so its run on "
                       "main fails",
            "category": "ci", "severity": "low", "detected_by": "person",
            "found": "2026-11-16", "due": "2027-05-15", "status": "open",
            "refs": {"rule_ids": ["AGENTS.md#CI Rules"],
                     "components": ["coqui-tts", "aws-builder-agent", "sovereign-vpc-gcp"],
                     "fingerprints": ["dependabot-private-reusable-workflow",
                                      "checklist-only-triage"]},
            "issue": "Drecoder/Engineering_Excellence_Playbook#87",
        })

    def test_due_date_is_computed_from_severity(self):
        for severity, due in (("critical", "2026-11-23"), ("high", "2026-12-16"),
                              ("medium", "2027-02-14"), ("low", "2027-05-15")):
            body = ISSUE_87.replace("### Severity\n\nlow", f"### Severity\n\n{severity}")
            self.assertEqual(project_row(issue(87, body))["due"], due, severity)

    def test_recurs_is_carried_when_given(self):
        body = ISSUE_87.replace("### Recurs\n\n_No response_", "### Recurs\n\nF-0034")
        self.assertEqual(project_row(issue(87, body))["refs"]["recurs"], ["F-0034"])


class Batch(unittest.TestCase):
    """project() appends every capa issue not yet in the register, in issue order."""

    def setUp(self):
        self.journal = (ROOT / "docs" / "POC_JOURNAL.md").read_text()
        self.register = json.loads((ROOT / "docs" / "FINDINGS_REGISTER.json").read_text())

    def new_issue(self, number: int, heading: str) -> dict:
        body = ISSUE_87.replace(
            "Dependabot cannot read the private central CI, so its run on main fails", heading)
        return issue(number, body)

    def test_appends_new_findings_in_order_and_passes_both_checks(self):
        issues = [self.new_issue(9002, "A second test finding"), self.new_issue(9001, "A first test finding"),
                  issue(9003, ISSUE_87, labels=("bug",))]
        journal, register, added = project(issues, self.journal, copy.deepcopy(self.register))
        self.assertEqual(added, ["F-9001", "F-9002"])
        self.assertTrue(journal.startswith(self.journal))
        self.assertLess(journal.index("A first test finding"), journal.index("A second test finding"))
        self.assertEqual([r["id"] for r in register["findings"][-2:]], ["F-9001", "F-9002"])
        self.assertEqual(append_only_check(self.journal, journal), [])
        result = register_check(journal, register, date(2026, 11, 16))
        self.assertEqual(result["errors"], [])

    def test_a_finding_already_in_the_register_is_left_alone(self):
        journal, register, added = project([issue(87, ISSUE_87)], self.journal,
                                           copy.deepcopy(self.register))
        self.assertEqual(added, [])
        self.assertEqual(journal, self.journal)

    def test_a_finding_already_in_the_register_is_not_parsed(self):
        # #84 to #89 were projected by hand before the form existed; their bodies are not form
        # output, and projection must skip them by ID, not refuse them.
        journal, register, added = project([issue(84, "a body written before the form")],
                                           self.journal, copy.deepcopy(self.register))
        self.assertEqual((journal, added), (self.journal, []))

    def test_running_twice_adds_nothing_the_second_time(self):
        issues = [self.new_issue(9001, "A first test finding")]
        journal, register, _ = project(issues, self.journal, copy.deepcopy(self.register))
        journal2, register2, added = project(issues, journal, copy.deepcopy(register))
        self.assertEqual(added, [])
        self.assertEqual((journal2, register2), (journal, register))


    # KAN-114 (F-0112, the owner's option (a)): an issue is journaled when a row names it, so a
    # finding recorded by hand under another ID (#103 as F-0100) is never projected twice.
    def test_an_issue_a_row_names_is_left_alone_and_not_parsed(self):
        register = copy.deepcopy(self.register)
        register["findings"][0]["issue"] = "Drecoder/Engineering_Excellence_Playbook#9005"
        journal, register2, added = project([issue(9005, "a body that is not form output")],
                                            self.journal, register)
        self.assertEqual((journal, added), (self.journal, []))

    def test_a_row_naming_the_same_number_in_another_repository_does_not_count(self):
        register = copy.deepcopy(self.register)
        register["findings"][0]["issue"] = "Drecoder/sovereign-vpc-gcp#9005"
        _, _, added = project([self.new_issue(9005, "A finding in this repository")],
                              self.journal, register)
        self.assertEqual(added, ["F-9005"])

    def test_the_register_names_issue_103_for_f_0100(self):
        # The case F-0112 found: projecting every capa issue must not duplicate F-0100.
        _, _, added = project([issue(103, "the hand-journaled body of #103")],
                              self.journal, copy.deepcopy(self.register))
        self.assertEqual(added, [])

    def test_every_projected_row_names_its_issue(self):
        _, register, _ = project([self.new_issue(9001, "A first test finding")], self.journal,
                                 copy.deepcopy(self.register))
        self.assertEqual(register["findings"][-1]["issue"],
                         "Drecoder/Engineering_Excellence_Playbook#9001")


class Check(unittest.TestCase):
    """--check, which journal.yml runs on every pull request: exit 1 on an unprojected issue."""

    def run_check(self, issues, tmp):
        from capa_project import main
        (tmp / "issues.json").write_text(json.dumps(issues))
        (tmp / "j.md").write_text((ROOT / "docs" / "POC_JOURNAL.md").read_text())
        (tmp / "r.json").write_text((ROOT / "docs" / "FINDINGS_REGISTER.json").read_text())
        return main([str(tmp / "issues.json"), "--check", "--journal", str(tmp / "j.md"),
                     "--register", str(tmp / "r.json")])

    def test_an_unprojected_issue_fails_and_changes_nothing(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            body = ISSUE_87.replace("Dependabot cannot read the private central CI, so its run on main fails",
                                    "A finding nobody projected")
            self.assertEqual(self.run_check([issue(9001, body)], tmp), 1)
            self.assertEqual((tmp / "r.json").read_text(),
                             (ROOT / "docs" / "FINDINGS_REGISTER.json").read_text())

    def test_the_real_register_passes_with_issue_103(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.run_check([issue(87, ISSUE_87), issue(103, "hand-journaled")], Path(d)), 0)


if __name__ == "__main__":
    unittest.main()
