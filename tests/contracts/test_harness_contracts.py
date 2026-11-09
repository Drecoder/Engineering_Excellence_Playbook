"""
Contract tests for the adaptive harness (06_AgentZone/09_Adaptive_Harness.md, status: proposed):
harness_decision.v1 and knowledge_record.v1.

At the codification stage these tests check only that each schema is a valid JSON Schema and that its
example validates. The conformance cases (every decision-table row and contract constraint, with
designed-to-fail cases) belong to the test-design stage and are added when the standard is approved.
Run inside the toolchain image:

    docker run --rm -v "$PWD:/work:ro" playbook-antipattern-toolchain \
        python -m unittest discover -s tests/contracts -v
"""

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"
CONTRACTS = ("harness_decision.v1", "knowledge_record.v1")


def load(name):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


class Contracts(unittest.TestCase):
    def test_schemas_are_valid(self):
        for name in CONTRACTS:
            with self.subTest(name):
                Draft202012Validator.check_schema(load(f"{name}.schema.json"))

    def test_examples_validate(self):
        for name in CONTRACTS:
            with self.subTest(name):
                validator = Draft202012Validator(load(f"{name}.schema.json"), format_checker=FormatChecker())
                self.assertEqual([e.message for e in validator.iter_errors(load(f"examples/{name}.example.json"))], [])


if __name__ == "__main__":
    unittest.main()
