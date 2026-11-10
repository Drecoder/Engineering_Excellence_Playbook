"""
Contract tests for the CAPA register. findings_register.v2: the real register is valid, and each
structural rule refuses what it must. findings_register.v1, still accepted until its deprecation
window closes (tests/journal/register.py), is tested against its frozen example. The deadline,
cross-reference, reference-resolution and readiness rules are tested in tests/journal/.

    docker run --rm -v "$PWD:/work:ro" playbook-antipattern-toolchain \
        python -m unittest discover -s tests/contracts -v
"""

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
load = lambda rel: json.loads((ROOT / rel).read_text(encoding="utf-8"))  # noqa: E731
SCHEMA = load("schemas/findings_register.v1.schema.json")
REGISTER = load("schemas/examples/findings_register.v1.example.json")
SCHEMA_V2 = load("schemas/findings_register.v2.schema.json")
REGISTER_V2 = load("docs/FINDINGS_REGISTER.json")
for _s in (SCHEMA, SCHEMA_V2):
    Draft202012Validator.check_schema(_s)
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
VALIDATOR_V2 = Draft202012Validator(SCHEMA_V2, format_checker=FormatChecker())


def errors(doc):
    return list(VALIDATOR.iter_errors(doc))


class FindingsRegister(unittest.TestCase):
    """findings_register.v1, against its frozen example."""

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


class FindingsRegisterV2(unittest.TestCase):
    def mutate(self, fn):
        doc = copy.deepcopy(REGISTER_V2)
        fn(doc)
        return list(VALIDATOR_V2.iter_errors(doc))

    def test_the_real_register_is_valid(self):
        self.assertEqual([e.message for e in VALIDATOR_V2.iter_errors(REGISTER_V2)], [])

    def test_the_real_register_is_v2_and_names_its_agent(self):
        self.assertEqual((REGISTER_V2["schema_version"], REGISTER_V2["agent"]), ("findings_register.v2", "builder"))

    def test_a_v1_register_is_not_a_v2_register(self):
        self.assertTrue(list(VALIDATOR_V2.iter_errors(REGISTER)))

    def test_the_agent_and_the_component_registry_are_required(self):
        self.assertTrue(self.mutate(lambda d: d.pop("agent")))
        self.assertTrue(self.mutate(lambda d: d.pop("components")))
        self.assertTrue(self.mutate(lambda d: d.update(components=[])))

    def test_every_finding_needs_rules_components_and_fingerprints(self):
        self.assertTrue(self.mutate(lambda d: d["findings"][0].pop("refs")))
        for key in ("rule_ids", "components", "fingerprints"):
            self.assertTrue(self.mutate(lambda d, k=key: d["findings"][0]["refs"].pop(k)), key)
            self.assertTrue(self.mutate(lambda d, k=key: d["findings"][0]["refs"].update({k: []})), key)

    def test_reference_shapes_are_checked(self):
        bad = {
            "rule_ids": ["CI Rules"],            # neither a catalog ID nor PATH#HEADING
            "components": ["Not A Slug"],
            "fingerprints": ["Pinned_To_Main"],
            "antipattern_ids": ["GHA-002"],
            "recurs": ["0011"],
        }
        for key, value in bad.items():
            self.assertTrue(self.mutate(lambda d, k=key, v=value: d["findings"][0]["refs"].update({k: [v]})), key)
        for good in ("SEC-004", "AGENTS.md#CI Rules", "00_UniversalStandards/14_Test_Quality.md#Determinism"):
            self.assertFalse(self.mutate(lambda d, g=good: d["findings"][0]["refs"].update(rule_ids=[g])), good)

    def test_a_dependency_kind_is_from_the_list(self):
        self.assertTrue(self.mutate(lambda d: d["components"][3]["depends_on"][0].update(kind="uses")))

    def test_a_ticket_key_is_optional_and_shaped(self):
        self.assertFalse(self.mutate(lambda d: d["findings"][0].update(ticket="KAN-60")))
        self.assertTrue(self.mutate(lambda d: d["findings"][0].update(ticket="kan60")))

    def test_unknown_reference_fields_are_refused(self):
        self.assertTrue(self.mutate(lambda d: d["findings"][0]["refs"].update(weight=0.5)))


if __name__ == "__main__":
    unittest.main()
