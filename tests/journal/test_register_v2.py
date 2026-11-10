"""
Tests for the findings_register.v2 reference checks (tests/journal/register.py, check_refs) and for
version handling. Each rule has a case that must fail and one that must pass, against a small
playbook built in a temporary directory, so the tests do not depend on the real catalogs' contents.
The real register is checked against the real playbook in test_register.py.

    python -m unittest discover -s tests/journal -v
"""

import copy
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from register import V1_ACCEPTED_UNTIL, check, check_refs, headings  # noqa: E402

TEXT = """# Journal

## 2026-10-28: An earlier finding

- **Status:** fixed.

## 2026-11-08: A later finding

- **Status:** open.
"""

RULES_MD = """# Rules

## 1️⃣ CI Rules

## 3️⃣a CRAP and the Policy Engine

## 1. Design

```hcl
# not a heading
```
"""


def refs(**over):
    base = {"rule_ids": ["docs/RULES.md#CI Rules"], "components": ["gate"], "fingerprints": ["pin-on-branch"]}
    base.update(over)
    return base


BASE = {
    "schema_version": "findings_register.v2",
    "agent": "builder",
    "components": [
        {"id": "gate", "kind": "repository", "name": "the gate", "depends_on": []},
        {"id": "caller", "kind": "repository", "name": "a caller",
         "depends_on": [{"component": "gate", "kind": "build"}]},
    ],
    "findings": [
        {"id": "F-0001", "journal": "## 2026-10-28: An earlier finding", "category": "ci", "severity": "high",
         "detected_by": "person", "found": "2026-10-28", "due": "2026-11-27", "status": "fixed",
         "closed": "2026-10-29", "verification": "run 1 passes", "refs": refs()},
        {"id": "F-0002", "journal": "## 2026-11-08: A later finding", "category": "ci", "severity": "high",
         "detected_by": "person", "found": "2026-11-08", "due": "2026-12-08", "status": "open",
         "refs": refs(components=["caller"], recurs=["F-0001"], antipattern_ids=["AP-GHA-002"])},
    ],
    "controls": [],
}


class Refs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name) / "playbook"
        root.mkdir()
        (root.parent / "outside.md").write_text("# Outside\n", encoding="utf-8")  # exists, but not in the playbook
        (root / "schemas").mkdir()
        (root / "docs").mkdir()
        (root / "00_UniversalStandards").mkdir()
        (root / "schemas/architecture_rules.v1.json").write_text(json.dumps({"rules": [{"id": "ARCH-001"}]}))
        (root / "schemas/governance_baseline.v1.json").write_text(json.dumps({"controls": [{"id": "GOV-001"}]}))
        (root / "schemas/antipatterns.v1.json").write_text(json.dumps({"rules": [{"id": "AP-GHA-002"}]}))
        (root / "00_UniversalStandards/07_Security_In_Depth.md").write_text("| `SEC-004` | No IAM users |\n")
        (root / "docs/RULES.md").write_text(RULES_MD, encoding="utf-8")
        cls.root = root

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def errors(self, mutate=None):
        reg = copy.deepcopy(BASE)
        if mutate:
            mutate(reg)
        return check_refs(reg, self.root)

    def has(self, text, mutate):
        errs = self.errors(mutate)
        self.assertTrue(any(text in e for e in errs), errs)

    def test_a_resolvable_register_has_no_errors(self):
        self.assertEqual(self.errors(), [])

    def test_catalog_ids_resolve_and_unknown_ones_fail(self):
        ok = lambda r: r["findings"][0]["refs"].update(rule_ids=["ARCH-001", "SEC-004", "GOV-001", "docs/RULES.md#CI Rules"])  # noqa: E731
        self.assertEqual(self.errors(ok), [])
        for bad in ("ARCH-999", "SEC-999", "GOV-999"):
            self.has(f"rule {bad} is not in its catalog",
                     lambda r, b=bad: r["findings"][0]["refs"].update(rule_ids=[b]))

    def test_a_heading_resolves_with_or_without_its_number(self):
        for head in ("CI Rules", "1️⃣ CI Rules", "CRAP and the Policy Engine", "Design", "1. Design"):
            self.assertEqual(self.errors(lambda r, h=head: r["findings"][0]["refs"].update(
                rule_ids=[f"docs/RULES.md#{h}", "docs/RULES.md#CI Rules"])), [], head)

    def test_a_missing_heading_fails(self):
        self.has("has no heading", lambda r: r["findings"][0]["refs"].update(rule_ids=["docs/RULES.md#Gate Rules"]))

    def test_a_line_in_a_code_fence_is_not_a_heading(self):
        self.assertNotIn("not a heading", headings(self.root / "docs/RULES.md"))
        self.has("has no heading", lambda r: r["findings"][0]["refs"].update(rule_ids=["docs/RULES.md#not a heading"]))

    def test_a_missing_file_or_a_path_outside_the_playbook_fails(self):
        for path in ("docs/NOPE.md#CI Rules", "../outside.md#Outside"):
            self.has("no playbook file", lambda r, p=path: r["findings"][0]["refs"].update(rule_ids=[p]))

    def test_an_unknown_component_fails(self):
        self.has("unknown component ghost", lambda r: r["findings"][0]["refs"].update(components=["ghost"]))

    def test_a_dependency_on_an_unknown_or_the_same_component_fails(self):
        self.has("depends on unknown component ghost",
                 lambda r: r["components"][0]["depends_on"].append({"component": "ghost", "kind": "build"}))
        self.has("depends on itself",
                 lambda r: r["components"][0]["depends_on"].append({"component": "gate", "kind": "build"}))

    def test_a_duplicate_component_fails(self):
        self.has("id used more than once", lambda r: r["components"].append(copy.deepcopy(r["components"][0])))

    def test_an_unknown_antipattern_fails(self):
        self.has("AP-GHA-999 is not in the anti-pattern catalog",
                 lambda r: r["findings"][1]["refs"].update(antipattern_ids=["AP-GHA-999"]))

    def test_recurring_an_open_or_later_closed_finding_fails(self):
        self.has("was not closed before F-0002 was found",
                 lambda r: (r["findings"][0].update(status="open"), r["findings"][0].pop("closed")))
        self.has("was not closed before F-0002 was found",
                 lambda r: r["findings"][0].update(closed="2026-11-08"))

    def test_recurring_needs_a_shared_fingerprint_and_rule(self):
        self.has("shares no fingerprint", lambda r: r["findings"][1]["refs"].update(fingerprints=["other"]))
        self.has("shares no rule", lambda r: r["findings"][1]["refs"].update(rule_ids=["docs/RULES.md#Design"]))

    def test_recurring_itself_or_an_unknown_finding_fails(self):
        for target in ("F-0002", "F-0099"):
            self.has("not another finding", lambda r, t=target: r["findings"][1]["refs"].update(recurs=[t]))


class Versions(unittest.TestCase):
    def test_an_unsupported_version_fails(self):
        reg = dict(BASE, schema_version="findings_register.v3")
        result = check(TEXT, reg, date(2026, 11, 10))
        self.assertTrue(any("unsupported register version" in e for e in result["errors"]))
        self.assertFalse(result["production_ready"])

    def test_v1_is_accepted_until_its_window_closes(self):
        v1 = {"schema_version": "findings_register.v1", "findings": [
            {k: v for k, v in f.items() if k != "refs"} for f in BASE["findings"]], "controls": []}
        self.assertEqual(check(TEXT, v1, V1_ACCEPTED_UNTIL)["errors"], [])
        after = date.fromordinal(V1_ACCEPTED_UNTIL.toordinal() + 1)
        self.assertTrue(any("migrate the register" in e for e in check(TEXT, v1, after)["errors"]))


if __name__ == "__main__":
    unittest.main()
