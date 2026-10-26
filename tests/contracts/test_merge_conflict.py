"""
Contract tests for merge_conflict.v1 and the reference merge-conflict behavior.

Run inside the toolchain image:

    docker run --rm -v "$PWD:/work:ro" playbook-antipattern-toolchain \
        python -m unittest discover -s tests/contracts -v
"""

import copy
import json
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

sys.path.insert(0, str(Path(__file__).resolve().parent))
from merge_reference import classify, dropped_lines, resolve_by_rule, route

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"
SCHEMA = json.loads((SCHEMAS / "merge_conflict.v1.schema.json").read_text(encoding="utf-8"))
Draft202012Validator.check_schema(SCHEMA)
V = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
EXAMPLE = json.loads((SCHEMAS / "examples" / "merge_conflict.v1.example.json").read_text(encoding="utf-8"))
HUNK = EXAMPLE["conflicts"][0]["hunks"][0]

# A second real conflict: sovereign-vpc-gcp#16 and #14 each added a row to the incidents index.
INC_ROWS = (
    ["| [INC-006](2026-10-26-INC-006-apply-failing-since-inference.md) | 2026-10-23 | Post-merge apply failed |"],
    ["| [INC-005](2026-10-26-INC-005-stacked-pr-closed-scanners-dropped.md) | 2026-10-26 | Scanner gates dropped |"],
)


def rejected(doc):
    return bool(list(V.iter_errors(doc)))


def mutate(fn):
    doc = copy.deepcopy(EXAMPLE)
    fn(doc)
    return doc


def hunk(doc):
    return doc["conflicts"][0]["hunks"][0]


class Example(unittest.TestCase):
    def test_the_example_is_valid(self):
        self.assertEqual([e.message for e in V.iter_errors(EXAMPLE)], [])

    def test_the_example_classifies_and_routes_as_the_reference_does(self):
        f = EXAMPLE["conflicts"][0]
        self.assertEqual(classify(HUNK["base"]["lines"], HUNK["ours"]["lines"], HUNK["theirs"]["lines"]), (HUNK["class"], HUNK["reason"]))
        self.assertEqual(route(HUNK["class"], HUNK["reason"], f["protected"]), HUNK["route"])


class SchemaRejects(unittest.TestCase):
    """Each case would let a hunk bypass a person or be resolved by rule when it must not."""

    def test_rule_route_in_a_protected_file(self):
        self.assertTrue(rejected(mutate(lambda d: hunk(d).update(route="rule"))))

    def test_model_route_in_a_protected_file(self):
        self.assertTrue(rejected(mutate(lambda d: hunk(d).update(route="model"))))

    def test_rule_route_for_a_semantic_hunk(self):
        def semantic(d):
            d["conflicts"][0]["protected"] = False
            hunk(d).update(**{"class": "semantic", "reason": "same_lines_changed", "route": "rule"})
        self.assertTrue(rejected(mutate(semantic)))

    def test_mechanical_with_base_lines(self):
        self.assertTrue(rejected(mutate(lambda d: hunk(d)["base"]["lines"].append("  OLD: 1"))))

    def test_mechanical_with_another_reason(self):
        self.assertTrue(rejected(mutate(lambda d: hunk(d).update(reason="same_lines_changed"))))

    def test_disjoint_additions_called_semantic(self):
        self.assertTrue(rejected(mutate(lambda d: hunk(d).update(**{"class": "semantic"}))))

    def test_binary_conflict_not_routed_to_a_person(self):
        def binary(d):
            d["conflicts"][0].update(kind="binary", protected=False)
            hunk(d).update(**{"class": "semantic", "reason": "binary", "route": "model"})
        self.assertTrue(rejected(mutate(binary)))

    def test_binary_file_with_a_text_reason(self):
        def binary(d):
            d["conflicts"][0]["kind"] = "binary"
        self.assertTrue(rejected(mutate(binary)))

    def test_short_sha(self):
        self.assertTrue(rejected(mutate(lambda d: d["head"].update(sha="5b65d45"))))

    def test_path_escaping_the_repo(self):
        self.assertTrue(rejected(mutate(lambda d: d["conflicts"][0].update(path="../other/gates.yml"))))

    def test_a_report_with_no_conflicts(self):
        self.assertTrue(rejected(mutate(lambda d: d.update(conflicts=[]))))

    def test_unknown_field(self):
        self.assertTrue(rejected(mutate(lambda d: hunk(d).update(auto_resolved=True))))

    def test_unprotected_mechanical_rule_is_valid(self):
        def plain(d):
            d["conflicts"][0]["protected"] = False
            hunk(d)["route"] = "rule"
        self.assertFalse(rejected(mutate(plain)))


class Reference(unittest.TestCase):
    def test_disjoint_additions_are_mechanical(self):
        self.assertEqual(classify([], *INC_ROWS), ("mechanical", "disjoint_additions"))

    def test_an_unprotected_mechanical_hunk_routes_to_the_rule(self):
        self.assertEqual(route("mechanical", "disjoint_additions", protected=False), "rule")

    def test_a_protected_file_routes_to_a_person_even_when_mechanical(self):
        self.assertEqual(route("mechanical", "disjoint_additions", protected=True), "person")

    def test_the_rule_keeps_both_sides_and_drops_nothing(self):
        ours, theirs = INC_ROWS
        resolved = resolve_by_rule(ours, theirs)
        self.assertEqual(resolved, [*ours, *theirs])
        self.assertEqual(dropped_lines(ours, theirs, resolved), [])

    def test_both_sides_changing_the_same_line_is_semantic(self):
        self.assertEqual(classify(['  TRIVY_VERSION: "0.70.0"'], ['  TRIVY_VERSION: "0.71.1"'], ['  TRIVY_VERSION: "0.71.0"']),
                         ("semantic", "same_lines_changed"))
        self.assertEqual(route("semantic", "same_lines_changed", protected=False), "model")

    def test_identical_additions_on_both_sides_are_a_collision(self):
        self.assertEqual(classify([], ["  BANDIT_VERSION: 1"], ["  BANDIT_VERSION: 1"]), ("semantic", "same_lines_changed"))

    def test_delete_versus_change_is_semantic(self):
        self.assertEqual(classify(["old"], [], ["changed"]), ("semantic", "delete_vs_change"))

    def test_binary_goes_to_a_person(self):
        self.assertEqual(route(*classify([], [], [], binary=True), protected=False), "person")

    def test_an_exhausted_budget_goes_to_a_person(self):
        self.assertEqual(route("semantic", "same_lines_changed", protected=False, budget_exhausted=True), "person")

    def test_the_lens_finds_a_dropped_line(self):
        ours, theirs = HUNK["ours"]["lines"], HUNK["theirs"]["lines"]
        resolved = [*ours, *theirs[:-1]]  # the resolver lost TRIVY_SHA256
        self.assertEqual(dropped_lines(ours, theirs, resolved), [theirs[-1]])

    def test_a_declared_removal_is_not_a_drop(self):
        ours, theirs = HUNK["ours"]["lines"], HUNK["theirs"]["lines"]
        self.assertEqual(dropped_lines(ours, theirs, [*ours, *theirs[:-1]], {theirs[-1]}), [])

    def test_the_real_env_block_resolution_drops_nothing(self):
        ours, theirs = HUNK["ours"]["lines"], HUNK["theirs"]["lines"]
        self.assertEqual(dropped_lines(ours, theirs, resolve_by_rule(ours, theirs)), [])


if __name__ == "__main__":
    unittest.main()
