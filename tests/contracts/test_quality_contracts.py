"""
Contract tests for test quality and licenses: quality.v1, license_policy.v1, and the coverage and
license checks in ci_policy.v1.

The license decisions are recomputed here by license_reference.py from the rules written in
license_policy.v1's description and 13_Supply_Chain.md §4. Run inside the toolchain image (it pins
rfc3339-validator, without which jsonschema silently skips date checks):

    docker run --rm -v "$PWD:/work:ro" playbook-antipattern-toolchain \
        python -m unittest discover -s tests/contracts -v
"""

import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

sys.path.insert(0, str(Path(__file__).resolve().parent))
from license_reference import classify_expression, classify_package, policy_problems  # noqa: E402

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"
FORMATS = FormatChecker()


def load(name):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def validator(name):
    schema = load(name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FORMATS)


QUALITY = validator("quality.v1.schema.json")
LICENSE = validator("license_policy.v1.schema.json")
CI = validator("ci_policy.v1.schema.json")
QUALITY_EX = load("examples/quality.v1.example.json")
POLICY = load("license_policy.v1.json")
VECTORS = load("examples/license/license_vectors.json")
CI_POLICY = load("ci_policy.v1.json")
TODAY = date.fromisoformat(VECTORS["today"])


def rejected(v, doc):
    return bool(list(v.iter_errors(doc)))


def mutated(base, fn):
    doc = copy.deepcopy(base)
    fn(doc)
    return doc


class FormatsAreChecked(unittest.TestCase):
    def test_date_checker_is_active(self):
        self.assertIn("date", FORMATS.checkers)


class Quality(unittest.TestCase):
    def test_example_is_valid(self):
        self.assertEqual([e.message for e in QUALITY.iter_errors(QUALITY_EX)], [])

    def test_mutation_is_optional(self):
        self.assertFalse(rejected(QUALITY, mutated(QUALITY_EX, lambda d: d.pop("mutation"))))

    def test_rejections(self):
        cases = {
            "a token floor": lambda d: d["coverage"].update(floor=0.1),
            "a floor over 1": lambda d: d["coverage"].update(floor=1.5),
            "no approval for the floors": lambda d: d.pop("approved_in"),
            "approved outside a pull request": lambda d: d.update(approved_in="https://example.com/ok"),
            "a report outside the repository": lambda d: d["coverage"]["report"].update(path="../coverage.xml"),
            "an absolute report path": lambda d: d["coverage"]["report"].update(path="/tmp/coverage.xml"),
            "an unknown report format": lambda d: d["coverage"]["report"].update(format="html"),
            "a Python report with Stryker": lambda d: d["mutation"].update(tool="stryker"),
            "a mutation path that escapes": lambda d: d["mutation"].update(paths=["../other"]),
            "an unknown field": lambda d: d.update(skip_coverage=True),
            "a repo with a trailing newline": lambda d: d.update(repo="Drecoder/x\n"),
        }
        for name, fn in cases.items():
            with self.subTest(name):
                self.assertTrue(rejected(QUALITY, mutated(QUALITY_EX, fn)))


class LicensePolicy(unittest.TestCase):
    def test_policy_is_valid_and_consistent(self):
        self.assertEqual([e.message for e in LICENSE.iter_errors(POLICY)], [])
        self.assertEqual(policy_problems(POLICY), [])

    def test_expression_vectors(self):
        self.assertTrue(VECTORS["expressions"])
        for v in VECTORS["expressions"]:
            with self.subTest(v["expression"]):
                self.assertEqual(classify_expression(v["expression"], POLICY), v["verdict"])

    def test_package_vectors(self):
        self.assertTrue(VECTORS["packages"])
        for v in VECTORS["packages"]:
            with self.subTest(v["package"]["name"]):
                self.assertEqual(classify_package(v["package"], POLICY, TODAY), v["verdict"])

    def exception(self, **overrides):
        e = {
            "id": "LIC-001", "package": "dual-declared", "version": "1.0.0", "license": "MIT AND AGPL-3.0-only",
            "owner": "github:Drecoder", "reason": "Used only in an internal benchmark, never distributed.",
            "approved_in": "https://github.com/Drecoder/Engineering_Excellence_Playbook/pull/1",
            "created": "2026-10-01", "expires": "2026-12-01",
        }
        e.update(overrides)
        return e

    def test_a_live_exception_allows_exactly_its_package_version(self):
        policy = mutated(POLICY, lambda d: d["exceptions"].append(self.exception()))
        self.assertFalse(rejected(LICENSE, policy))
        package = {"name": "dual-declared", "version": "1.0.0", "licenses": ["MIT", "AGPL-3.0-only"]}
        self.assertEqual(classify_package(package, policy, TODAY), "allowed")
        self.assertEqual(classify_package(dict(package, version="1.0.1"), policy, TODAY), "denied")

    def test_an_expired_exception_does_not_apply(self):
        policy = mutated(POLICY, lambda d: d["exceptions"].append(self.exception(expires="2026-10-27")))
        package = {"name": "dual-declared", "version": "1.0.0", "licenses": ["MIT", "AGPL-3.0-only"]}
        self.assertEqual(classify_package(package, policy, TODAY), "denied")

    def test_rejections(self):
        cases = {
            "an exception without a reason": lambda d: d["exceptions"].append({k: v for k, v in self.exception().items() if k != "reason"}),
            "an exception for a version range": lambda d: d["exceptions"].append(self.exception(version=">= 1.0")),
            "an exception approved outside a pull request": lambda d: d["exceptions"].append(self.exception(approved_in="ok")),
            "an exception with a bad date": lambda d: d["exceptions"].append(self.exception(expires="next year")),
            "a duplicate on one list": lambda d: d["allowed"].append("MIT"),
            "an unknown field": lambda d: d.update(allow_all=True),
        }
        for name, fn in cases.items():
            with self.subTest(name):
                self.assertTrue(rejected(LICENSE, mutated(POLICY, fn)))

    def test_problems_a_schema_cannot_catch(self):
        on_two_lists = mutated(POLICY, lambda d: d["denied"].append("MIT"))
        self.assertEqual(policy_problems(on_two_lists), ["MIT is on both allowed and denied"])
        too_long = mutated(POLICY, lambda d: d["exceptions"].append(self.exception(expires="2027-12-01")))
        self.assertEqual(policy_problems(too_long), ["LIC-001 lives longer than 365 days"])


class CiPolicyChecks(unittest.TestCase):
    def by_id(self, check_id):
        return next(c for c in CI_POLICY["checks"] if c["id"] == check_id)

    def test_coverage_and_license_checks_are_declared(self):
        for check_id in ("pytest-coverage", "vitest-coverage", "changed-line-coverage", "license"):
            self.assertIn(check_id, {c["id"] for c in CI_POLICY["checks"]})
        self.assertEqual(self.by_id("license")["blocks_on"], "denied_license")
        self.assertEqual(self.by_id("changed-line-coverage")["blocks_on"], "never")

    def test_rejections(self):
        cases = {
            "a coverage check with exceptions": ("pytest-coverage", {"exceptions_allowed": True}),
            "a coverage check on changed units only": ("pytest-coverage", {"scope": "changed_units"}),
            "a coverage check with a severity threshold": ("pytest-coverage", {"blocks_on": "critical"}),
            "a license check that never blocks": ("license", {"blocks_on": "never"}),
            "a license check with exceptions": ("license", {"exceptions_allowed": True}),
            "denied_license on another category": ("pytest-coverage", {"blocks_on": "denied_license"}),
        }
        for name, (check_id, change) in cases.items():
            with self.subTest(name):
                doc = copy.deepcopy(CI_POLICY)
                next(c for c in doc["checks"] if c["id"] == check_id).update(change)
                self.assertTrue(rejected(CI, doc))


if __name__ == "__main__":
    unittest.main()
