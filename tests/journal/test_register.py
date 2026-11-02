"""
Tests for the CAPA register check: each rule has a case that must fail and one that must pass, and
the real journal and register are checked together on a fixed date.

    python -m unittest discover -s tests/journal -v
"""

import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from register import check, main  # noqa: E402

ROOT = HERE.parents[1]
JOURNAL = ROOT / "docs" / "POC_JOURNAL.md"
REGISTER = ROOT / "docs" / "FINDINGS_REGISTER.json"

TEXT = """# Journal

---

## 2026-10-28: A security finding

- **Status:** open.

## 2026-10-28: A quality finding

- **Status:** fixed.
"""

BASE = {
    "schema_version": "findings_register.v1",
    "findings": [
        {"id": "F-0001", "journal": "## 2026-10-28: A security finding", "category": "security",
         "severity": "high", "detected_by": "person", "found": "2026-10-28", "due": "2026-11-27",
         "status": "open"},
        {"id": "F-0002", "journal": "## 2026-10-28: A quality finding", "category": "quality",
         "severity": "medium", "detected_by": "control", "found": "2026-10-28", "due": "2027-01-26",
         "status": "fixed", "closed": "2026-10-30", "verification": "run 123 passes"},
    ],
    "controls": [
        {"id": "C-001", "name": "A proven control", "proven": True, "evidence": "#1"},
        {"id": "C-002", "name": "An unproven control", "proven": False},
    ],
}
ON_TIME = date(2026, 11, 1)


def variant(changes):
    reg = copy.deepcopy(BASE)
    for (i, key), value in changes.items():
        if value is None:
            reg["findings"][i].pop(key, None)
        else:
            reg["findings"][i][key] = value
    return reg


class Rows(unittest.TestCase):
    def test_a_complete_register_has_no_errors(self):
        self.assertEqual(check(TEXT, BASE, ON_TIME)["errors"], [])

    def test_a_journal_entry_without_a_row_fails(self):
        reg = copy.deepcopy(BASE)
        reg["findings"].pop(1)
        self.assertIn("no register row for journal entry: ## 2026-10-28: A quality finding",
                      check(TEXT, reg, ON_TIME)["errors"])

    def test_a_row_for_no_entry_fails(self):
        reg = variant({(1, "journal"): "## 2026-10-28: Not in the journal"})
        self.assertTrue(any("names no journal entry" in e for e in check(TEXT, reg, ON_TIME)["errors"]))

    def test_a_duplicate_id_fails(self):
        reg = variant({(1, "id"): "F-0001"})
        self.assertTrue(any("used more than once" in e for e in check(TEXT, reg, ON_TIME)["errors"]))


class Deadlines(unittest.TestCase):
    def test_a_due_date_past_the_severity_deadline_fails(self):
        reg = variant({(0, "due"): "2026-11-28"})  # high: 30 days from 2026-10-28 is 2026-11-27
        self.assertTrue(any("past the high deadline 2026-11-27" in e
                            for e in check(TEXT, reg, ON_TIME)["errors"]))

    def test_each_severity_has_its_deadline(self):
        for severity, last_ok in (("critical", "2026-11-04"), ("high", "2026-11-27"),
                                  ("medium", "2027-01-26"), ("low", "2027-04-26")):
            ok = variant({(0, "severity"): severity, (0, "due"): last_ok})
            self.assertEqual(check(TEXT, ok, ON_TIME)["errors"], [], severity)
            late = date.fromisoformat(last_ok).toordinal() + 1
            bad = variant({(0, "severity"): severity, (0, "due"): date.fromordinal(late).isoformat()})
            self.assertTrue(check(TEXT, bad, ON_TIME)["errors"], severity)

    def test_closing_before_finding_fails(self):
        reg = variant({(1, "closed"): "2026-10-27"})
        self.assertTrue(any("before it was found" in e for e in check(TEXT, reg, ON_TIME)["errors"]))

    def test_an_open_finding_past_due_is_overdue(self):
        result = check(TEXT, BASE, date(2026, 11, 28))
        self.assertEqual(len(result["overdue"]), 1)
        self.assertEqual(result["errors"], [])

    def test_overdue_warns_on_a_pull_request_and_fails_the_daily_run(self):
        with tempfile.TemporaryDirectory() as d:
            j, r = Path(d) / "j.md", Path(d) / "r.json"
            j.write_text(TEXT, encoding="utf-8")
            r.write_text(json.dumps(BASE), encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                pr = main(["x", str(j), str(r), "--mode", "pr", "--today", "2026-11-28"])
                daily = main(["x", str(j), str(r), "--mode", "scheduled", "--today", "2026-11-28"])
                fine = main(["x", str(j), str(r), "--mode", "scheduled", "--today", "2026-11-01"])
            self.assertEqual((pr, daily, fine), (0, 1, 0))
            self.assertIn("::warning::CAPA register: overdue: F-0001", out.getvalue())
            self.assertIn("::error::CAPA register: overdue: F-0001", out.getvalue())


class MetricsAndReadiness(unittest.TestCase):
    def test_metrics(self):
        m = check(TEXT, BASE, ON_TIME)["metrics"]
        self.assertEqual((m["findings"], m["open"]), (2, 1))
        self.assertEqual(m["open_by_severity"], {"critical": 0, "high": 1, "medium": 0, "low": 0})
        self.assertEqual((m["controls_proven"], m["controls_total"]), (1, 2))
        self.assertEqual(m["detected_by_control"], 1)
        self.assertEqual(m["mean_days_to_close"], 2.0)

    def test_an_open_high_security_finding_blocks_production(self):
        result = check(TEXT, BASE, ON_TIME)
        self.assertFalse(result["production_ready"])
        self.assertEqual(len(result["blockers"]), 1)

    def test_an_open_medium_or_non_governed_finding_does_not(self):
        for change in ({(0, "severity"): "medium"}, {(0, "category"): "quality"}):
            self.assertTrue(check(TEXT, variant(change), ON_TIME)["production_ready"], change)

    def test_closing_the_blocker_makes_it_ready(self):
        reg = variant({(0, "status"): "fixed", (0, "closed"): "2026-10-30", (0, "verification"): "run 9 passes"})
        self.assertTrue(check(TEXT, reg, ON_TIME)["production_ready"])


class TheRealRegister(unittest.TestCase):
    def test_every_journal_entry_has_a_row_and_every_deadline_holds(self):
        result = check(JOURNAL.read_text(encoding="utf-8"),
                       json.loads(REGISTER.read_text(encoding="utf-8")), date(2026, 10, 29))
        self.assertEqual(result["errors"], [])

    def test_the_open_governance_findings_block_production(self):
        result = check(JOURNAL.read_text(encoding="utf-8"),
                       json.loads(REGISTER.read_text(encoding="utf-8")), date(2026, 10, 29))
        self.assertFalse(result["production_ready"])


if __name__ == "__main__":
    unittest.main()
