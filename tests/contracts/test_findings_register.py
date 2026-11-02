"""
Contract tests for findings_register.v1: the real register is valid, and each structural rule
refuses what it must. The deadline, cross-reference, and readiness rules are tested in
tests/journal/test_register.py.

    docker run --rm -v "$PWD:/work:ro" playbook-antipattern-toolchain \
        python -m unittest discover -s tests/contracts -v
"""

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schemas" / "findings_register.v1.schema.json").read_text(encoding="utf-8"))
REGISTER = json.loads((ROOT / "docs" / "FINDINGS_REGISTER.json").read_text(encoding="utf-8"))
Draft202012Validator.check_schema(SCHEMA)
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def errors(doc):
    return list(VALIDATOR.iter_errors(doc))


class FindingsRegister(unittest.TestCase):
    def test_the_real_register_is_valid(self):
        self.assertEqual([e.message for e in errors(REGISTER)], [])

    def mutate(self, fn):
        doc = copy.deepcopy(REGISTER)
        fn(doc)
        return errors(doc)

    def test_an_unknown_severity_is_refused(self):
        self.assertTrue(self.mutate(lambda d: d["findings"][0].update(severity="severe")))

    def test_an_unknown_category_is_refused(self):
        self.assertTrue(self.mutate(lambda d: d["findings"][0].update(category="misc")))

    def test_a_closed_finding_needs_a_date_and_verification(self):
        closed = next(i for i, f in enumerate(REGISTER["findings"]) if f["status"] != "open")
        self.assertTrue(self.mutate(lambda d: d["findings"][closed].pop("verification")))
        self.assertTrue(self.mutate(lambda d: d["findings"][closed].pop("closed")))

    def test_an_open_finding_cannot_carry_a_closed_date(self):
        opened = next(i for i, f in enumerate(REGISTER["findings"]) if f["status"] == "open")
        self.assertTrue(self.mutate(lambda d: d["findings"][opened].update(closed="2026-10-29")))

    def test_a_proven_control_needs_evidence(self):
        proven = next(i for i, c in enumerate(REGISTER["controls"]) if c["proven"])
        self.assertTrue(self.mutate(lambda d: d["controls"][proven].pop("evidence")))

    def test_dates_are_checked(self):
        self.assertTrue(self.mutate(lambda d: d["findings"][0].update(due="2026-13-40")))

    def test_unknown_fields_are_refused(self):
        self.assertTrue(self.mutate(lambda d: d["findings"][0].update(owner_note="x")))


if __name__ == "__main__":
    unittest.main()
