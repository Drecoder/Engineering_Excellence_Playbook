"""
Tests for the antipatterns.v1 catalog. Run inside the pinned toolchain image:

    docker run --rm -v "$PWD:/work:ro" playbook-antipattern-toolchain \
        python -m unittest discover -s tests/antipatterns -v
"""

import copy
import json
import unittest
from pathlib import Path

from reference import (
    FINDING_VALIDATOR,
    CatalogError,
    check_catalog,
    gate_effect,
    index,
    load_catalog,
    normalize,
    promotion_eligible,
    wilson_lower_bound,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "schemas" / "examples" / "antipatterns"
CATALOG = load_catalog()
RULES = {r["id"]: r for r in CATALOG["rules"]}


def minimal_catalog(rule):
    cat = copy.deepcopy(CATALOG)
    cat["rules"] = [rule]
    return cat


class CatalogContract(unittest.TestCase):
    def test_catalog_validates(self):
        check_catalog(CATALOG)  # raises on any error

    def test_rule_ids_and_detector_mappings_are_unique(self):
        ids = [r["id"] for r in CATALOG["rules"]]
        self.assertEqual(len(ids), len(set(ids)))
        keys = [(r["detector"]["tool"], r["detector"]["rule_id"]) for r in CATALOG["rules"]]
        self.assertEqual(len(keys), len(set(keys)))

    def test_duplicate_id_is_rejected(self):
        cat = copy.deepcopy(CATALOG)
        cat["rules"].append(copy.deepcopy(cat["rules"][0]))
        with self.assertRaisesRegex(CatalogError, "duplicate rule id"):
            check_catalog(cat)

    def test_two_rules_on_one_detector_rule_are_rejected(self):
        cat = copy.deepcopy(CATALOG)
        clone = copy.deepcopy(RULES["AP-PY-001"])
        clone["id"] = "AP-PY-099"
        cat["rules"].append(clone)
        with self.assertRaisesRegex(CatalogError, "both map bandit:B602"):
            check_catalog(cat)

    def test_every_required_stack_is_covered(self):
        covered = {(r["stack"], r["framework"]) for r in CATALOG["rules"]}
        for need in [("go", "none"), ("typescript", "none"), ("typescript", "nodejs"), ("typescript", "react"),
                     ("typescript", "angular"), ("python", "none"), ("python", "django"), ("python", "fastapi"),
                     ("hcl", "terraform"), ("hcl", "terragrunt"), ("docker", "dockerfile")]:
            self.assertIn(need, covered, need)

    def test_terragrunt_checks_are_marked_custom(self):
        tg = [r for r in CATALOG["rules"] if r["framework"] == "terragrunt"]
        self.assertTrue(tg)
        for r in tg:
            self.assertEqual(r["detector"]["tool"], "rig", r["id"])
            self.assertTrue(r["detector"]["custom"], r["id"])

    def test_implemented_and_planned_are_distinct(self):
        for r in CATALOG["rules"]:
            status = r["detector"]["mapping"]["status"]
            if status == "planned":
                self.assertEqual(r["enforcement"]["state"], "planned", r["id"])
            else:
                self.assertEqual(r["enforcement"]["state"], "advisory", r["id"])
            if status == "verified":
                self.assertIn("@sha256:", r["detector"]["mapping"]["toolchain"], r["id"])

    def test_local_references_exist(self):
        for r in CATALOG["rules"]:
            for ref in r["references"]:
                if not ref.startswith("https://"):
                    self.assertTrue((ROOT / ref).exists(), f"{r['id']}: {ref}")


class Examples(unittest.TestCase):
    def test_valid_example_passes(self):
        rule = json.loads((EXAMPLES / "valid_rule.json").read_text(encoding="utf-8"))
        check_catalog(minimal_catalog(rule))

    def test_every_invalid_example_is_rejected(self):
        cases = json.loads((EXAMPLES / "invalid_rules.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(cases), 10)
        for case in cases:
            with self.subTest(case["name"]):
                with self.assertRaises(CatalogError, msg=case["why"]):
                    check_catalog(minimal_catalog(case["rule"]))


class AdvisoryNeverBlocks(unittest.TestCase):
    def test_every_rule_declares_blocks_false(self):
        for r in CATALOG["rules"]:
            self.assertIs(r["enforcement"]["blocks"], False, r["id"])

    def test_findings_from_every_advisory_rule_never_block(self):
        idx = index(CATALOG)
        findings = []
        for (tool, rid), rule in idx.items():
            f = normalize({"tool": tool, "rule_id": rid, "file": "x", "start_line": 1}, CATALOG, "rig", idx)
            self.assertIsNotNone(f, rule["id"])
            self.assertIs(f["blocking"], False, rule["id"])
            findings.append(f)
        self.assertEqual(gate_effect(findings), {"blocks": False, "advisory_findings": len(findings), "exit_code": 0})

    def test_critical_severity_does_not_block(self):
        critical = [r for r in CATALOG["rules"] if r["severity"] == "critical" and r["enforcement"]["state"] == "advisory"]
        self.assertTrue(critical)
        f = normalize({"tool": critical[0]["detector"]["tool"], "rule_id": critical[0]["detector"]["rule_id"],
                       "file": "x", "start_line": 1}, CATALOG, "reviewer")
        self.assertEqual(gate_effect([f])["exit_code"], 0)

    def test_a_blocking_finding_is_rejected_by_the_contract(self):
        f = normalize({"tool": "bandit", "rule_id": "B602", "file": "x", "start_line": 1}, CATALOG, "rig")
        f["blocking"] = True
        self.assertTrue(list(FINDING_VALIDATOR.iter_errors(f)))
        with self.assertRaises(CatalogError):
            gate_effect([f])


class Normalization(unittest.TestCase):
    def test_conformance_vectors(self):
        doc = json.loads((EXAMPLES / "finding_vectors.json").read_text(encoding="utf-8"))
        self.assertEqual(doc["catalog_version"], CATALOG["catalog_version"])
        for v in doc["vectors"]:
            with self.subTest(v["name"]):
                self.assertEqual(normalize(v["hit"], CATALOG, v["reported_by"]), v["expect"])

    def test_both_consumers_get_the_same_fingerprint(self):
        hit = {"tool": "bandit", "rule_id": "B602", "file": "src/a.py", "start_line": 3}
        a, b = normalize(hit, CATALOG, "rig"), normalize(hit, CATALOG, "reviewer")
        self.assertEqual(a["fingerprint"], b["fingerprint"])
        self.assertEqual({k: v for k, v in a.items() if k != "reported_by"}, {k: v for k, v in b.items() if k != "reported_by"})


class Benchmark(unittest.TestCase):
    def test_no_rule_claims_unvalidated_precision(self):
        for r in CATALOG["rules"]:
            self.assertEqual(r["benchmark"]["status"], "unmeasured", r["id"])
            ok, why = promotion_eligible(r, CATALOG["promotion"], "2026-10-22")
            self.assertFalse(ok, r["id"])
            self.assertEqual(why, "unmeasured")

    def test_wilson_lower_bound(self):
        self.assertAlmostEqual(wilson_lower_bound(15, 26, 0.95), 0.3897, places=3)
        self.assertAlmostEqual(wilson_lower_bound(50, 50, 0.95), 0.9287, places=3)
        self.assertEqual(wilson_lower_bound(0, 0, 0.95), 0.0)

    def test_promotion_needs_every_criterion(self):
        rule = copy.deepcopy(RULES["AP-PY-001"])
        crit = CATALOG["promotion"]
        rule["benchmark"] = {"status": "measured", "corpus": "bench@abc", "measured_on": "2026-10-01",
                             "true_positives": 60, "false_positives": 0, "false_negatives": 3, "clean_cases": 80,
                             "precision": 1.0, "precision_lower_bound": 0.94, "recall": 0.95}
        self.assertEqual(promotion_eligible(rule, crit, "2026-10-22"), (True, "eligible for a reviewed gate proposal"))
        stale = promotion_eligible(rule, crit, "2027-03-01")
        self.assertFalse(stale[0])
        noisy = copy.deepcopy(rule)
        noisy["benchmark"]["false_positives"] = 8
        self.assertFalse(promotion_eligible(noisy, crit, "2026-10-22")[0])
        few = copy.deepcopy(rule)
        few["benchmark"]["true_positives"] = 12
        self.assertFalse(promotion_eligible(few, crit, "2026-10-22")[0])


if __name__ == "__main__":
    unittest.main()
