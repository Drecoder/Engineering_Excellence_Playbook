"""
Tests for the architecture lens reference and its conformance vectors. Run inside the toolchain
image:

    docker run --rm -v "$PWD:/work:ro" playbook-antipattern-toolchain \
        python -m unittest discover -s tests/review_lenses -v
"""

import copy
import json
import unittest

from jsonschema import Draft202012Validator

from architecture_lens import (
    SCHEMAS,
    VECTORS,
    build_vectors,
    catalog_links,
    lens,
    load_catalog,
    load_rules,
)

RULES = load_rules()
CATALOG = load_catalog()
DOC = json.loads(VECTORS.read_text(encoding="utf-8"))
BY_NAME = {v["name"]: v for v in DOC["vectors"]}


def _validator(name):
    return Draft202012Validator(json.loads((SCHEMAS / name).read_text(encoding="utf-8")))


class Vectors(unittest.TestCase):
    def test_vectors_match_the_reference(self):
        self.assertEqual(build_vectors(), DOC, "vectors are stale; run architecture_lens.py --write")

    def test_vector_inputs_are_valid_contracts(self):
        features = _validator("features.v1.json")
        finding = _validator("antipattern_finding.v1.schema.json")
        for v in DOC["vectors"]:
            with self.subTest(v["name"]):
                if v["features"] is not None:
                    self.assertEqual(list(features.iter_errors(v["features"])), [])
                for f in v["antipattern_findings"]:
                    self.assertEqual(list(finding.iter_errors(f)), [])

    def test_counts_follow_the_rules_file(self):
        self.assertEqual(DOC["architecture_rules_count"], len(RULES["rules"]))
        self.assertEqual(len(BY_NAME["fail_closed_selects_every_rule"]["expected"]["selected_rule_ids"]), len(RULES["rules"]))


class Semantics(unittest.TestCase):
    def test_lens_does_not_run_without_features_or_matches(self):
        self.assertEqual(BY_NAME["no_features_record"]["expected"], {"runs": False})
        self.assertEqual(BY_NAME["touches_nothing_covered"]["expected"], {"runs": False})

    def test_migration_gets_expand_contract_rules_and_squawk_hits(self):
        e = BY_NAME["migration_with_catalog_hits"]["expected"]
        self.assertEqual(e["selected_rule_ids"], ["ARCH-008", "ARCH-009", "ARCH-010"])
        self.assertEqual(e["protected"], [{"rule": "ARCH-009", "class": "irreversible"}])
        self.assertEqual([(k["rule"], k["finding"]) for k in e["known_findings"]],
                         [("ARCH-008", "AP-DB-001"), ("ARCH-009", "AP-DB-002")])

    def test_rig_hits_for_unselected_rules_are_left_out(self):
        e = BY_NAME["rig_hits_only_for_selected_rules"]["expected"]
        self.assertEqual([k["rule"] for k in e["known_findings"]], ["ARCH-005"])
        self.assertEqual(e["known_findings"][0]["evidence"], "trace 4bf92f3577b34da6a3ce929d0e0e4736 span 00f067aa0ba902b7")

    def test_catalog_hits_follow_the_selected_rules(self):
        e = BY_NAME["catalog_hits_filtered_by_selected_rules"]["expected"]
        found = [(k["rule"], k["source"], k.get("finding"), k["result"]) for k in e["known_findings"]]
        self.assertIn(("ARCH-017", "catalog", "AP-PY-004", "violation"), found)
        self.assertIn(("ARCH-017", "rig", None, "unverifiable"), found)  # unverifiable is shown, never compliant
        self.assertFalse(any(f == "AP-API-004" for _, _, f, _ in found))  # ARCH-004 not selected
        self.assertFalse(any(f == "AP-REACT-001" for _, _, f, _ in found))  # no ARCH link

    def test_fail_closed_includes_catalog_hits(self):
        e = BY_NAME["fail_closed_selects_every_rule"]["expected"]
        self.assertEqual(e["selected_by"], "fail_closed")
        self.assertEqual([k["finding"] for k in e["known_findings"]], ["AP-PY-004"])

    def test_cache_names_the_security_class(self):
        self.assertIn({"rule": "ARCH-022", "class": "security"}, BY_NAME["cache_protected_security"]["expected"]["protected"])


class Links(unittest.TestCase):
    def test_every_catalog_link_targets_an_existing_rule(self):
        links = catalog_links(CATALOG, RULES)
        self.assertEqual(links["AP-DB-002"], ["ARCH-009"])
        self.assertGreaterEqual(len(links), 14)

    def test_link_to_an_unknown_rule_is_rejected(self):
        bad = copy.deepcopy(CATALOG)
        bad["rules"][0]["related"] = ["ARCH-099"]
        with self.assertRaisesRegex(ValueError, "unknown architecture rules"):
            catalog_links(bad, RULES)
        with self.assertRaisesRegex(ValueError, "unknown architecture rules"):
            lens(BY_NAME["queue_publish"]["features"], [], RULES, bad)


if __name__ == "__main__":
    unittest.main()
