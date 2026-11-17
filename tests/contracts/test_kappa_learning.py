"""
Contract tests for kappa_learning.v1, the Builder's learning handoff (KAN-60 slice 3). The example,
and every learning record committed under .kappa/, are valid; each structural rule refuses what it
must. Completeness against the register and commit order are checked in tests/journal/test_kappa.py.

    docker run --rm -v "$PWD:/work:ro" playbook-antipattern-toolchain \
        python -m unittest discover -s tests/contracts -v
"""

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "schemas/kappa_learning.v1.schema.json").read_text(encoding="utf-8"))
EXAMPLE = json.loads((ROOT / "schemas/examples/kappa_learning.v1.example.json").read_text(encoding="utf-8"))
Draft202012Validator.check_schema(SCHEMA)
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def errors(doc):
    return [e.message for e in VALIDATOR.iter_errors(doc)]


class KappaLearning(unittest.TestCase):
    def mutate(self, fn):
        doc = copy.deepcopy(EXAMPLE)
        fn(doc)
        return errors(doc)

    def test_the_example_is_valid(self):
        self.assertEqual(errors(EXAMPLE), [])

    def test_every_committed_record_is_valid(self):
        records = sorted((ROOT / ".kappa").glob("*.json"))
        self.assertTrue(records)
        for path in records:
            self.assertEqual(errors(json.loads(path.read_text(encoding="utf-8"))), [], path.name)

    def test_an_unknown_field_is_refused(self):
        self.assertTrue(self.mutate(lambda d: d.update(confidence=0.9)))

    def test_consulted_needs_both_digests(self):
        self.assertTrue(self.mutate(lambda d: d["kappa"].pop("register_sha256")))
        self.assertTrue(self.mutate(lambda d: d["kappa"].pop("journal_sha256")))

    def test_unavailable_needs_its_error(self):
        self.assertTrue(self.mutate(lambda d: d.update(kappa={"status": "unavailable"})))
        self.assertEqual(self.mutate(lambda d: d.update(kappa={"status": "unavailable", "error": "timeout"})), [])

    def test_a_reused_correction_needs_its_revalidation(self):
        def reuse(d):
            d["findings"][0].update(reuses_correction=True)
            d["findings"][0].pop("revalidation", None)
        self.assertTrue(self.mutate(reuse))

    def test_a_placeholder_reason_is_refused(self):
        self.assertTrue(self.mutate(lambda d: d["findings"][0].update(reason="n/a")))

    def test_unknown_enums_are_refused(self):
        self.assertTrue(self.mutate(lambda d: d["findings"][0].update(relation="maybe")))
        self.assertTrue(self.mutate(lambda d: d.update(result="some")))
        self.assertTrue(self.mutate(lambda d: d.update(classification="unclear")))
        self.assertTrue(self.mutate(lambda d: d["kappa"].update(status="skipped")))

    def test_ids_and_ticket_have_their_form(self):
        self.assertTrue(self.mutate(lambda d: d["findings"][0].update(id="F-21")))
        self.assertTrue(self.mutate(lambda d: d["work"].update(ticket="kan60")))


if __name__ == "__main__":
    unittest.main()
