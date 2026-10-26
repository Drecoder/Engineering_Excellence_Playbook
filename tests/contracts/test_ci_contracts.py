"""
Contract tests for policy-driven CI: ci_policy.v1, ci_exceptions.v1, gate_plan.v1.

Run inside the toolchain image (it pins rfc3339-validator, without which jsonschema silently skips
date checks):

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
from ci_reference import (
    canonical_sha256,
    evaluate_exceptions,
    finding_is_excepted,
    plan_is_trusted,
)

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"
FORMATS = FormatChecker()


def load(name):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def validator(name):
    schema = load(name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FORMATS)


POLICY = validator("ci_policy.v1.schema.json")
EXCEPTIONS = validator("ci_exceptions.v1.schema.json")
PLAN = validator("gate_plan.v1.schema.json")
POLICY_DOC = load("ci_policy.v1.json")
EXC_EX = load("examples/ci_exceptions.v1.example.json")
PLAN_EX = load("examples/gate_plan.v1.example.json")


def rejected(v, doc):
    return bool(list(v.iter_errors(doc)))


def check(doc, check_id):
    return next(c for c in doc["checks"] if c["id"] == check_id)


class FormatsAreChecked(unittest.TestCase):
    def test_date_checker_is_active(self):
        self.assertIn("date", FORMATS.checkers)
        self.assertIn("date-time", FORMATS.checkers, "install rfc3339-validator")


class Documents(unittest.TestCase):
    def test_policy_and_examples_are_valid(self):
        for v, doc in [(POLICY, POLICY_DOC), (EXCEPTIONS, EXC_EX), (PLAN, PLAN_EX)]:
            self.assertEqual([e.message for e in v.iter_errors(doc)], [])

    def test_check_ids_are_unique(self):
        ids = [c["id"] for c in POLICY_DOC["checks"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_floor_categories_scan_the_whole_repo(self):
        floor = set(POLICY_DOC["floors"]["full_repo_categories"])
        for c in POLICY_DOC["checks"]:
            if c["category"] in floor:
                self.assertEqual(c["scope"], "full_repo", c["id"])

    def test_exceptable_checks_are_in_allowed_categories(self):
        allowed = set(POLICY_DOC["exceptions"]["allowed_categories"])
        for c in POLICY_DOC["checks"]:
            if c["exceptions_allowed"]:
                self.assertIn(c["category"], allowed, c["id"])

    def test_plan_matches_policy_and_exceptions(self):
        for planned in PLAN_EX["checks"]:
            self.assertEqual(planned["blocks_on"], check(POLICY_DOC, planned["id"])["blocks_on"], planned["id"])
        by_id = {e["id"]: e for e in EXC_EX["exceptions"]}
        for applied in PLAN_EX["exceptions"]["applied"]:
            source = by_id[applied["id"]]
            for field in ("check", "finding_id", "resource", "expires"):
                self.assertEqual(applied[field], source[field], field)
            self.assertTrue(check(POLICY_DOC, applied["check"])["exceptions_allowed"])

    def test_plan_records_the_policy_digest(self):
        self.assertEqual(PLAN_EX["policy"]["sha256"], canonical_sha256(POLICY_DOC))
        self.assertEqual(PLAN_EX["policy"]["version"], POLICY_DOC["policy_version"])


class Canonicalization(unittest.TestCase):
    """Every language must produce the same digest: sorted keys, compact separators, ASCII escapes."""

    def test_key_order_and_whitespace_do_not_change_the_digest(self):
        a = json.loads('{"b": 1, "a": {"d": [1, 2], "c": "x"}}')
        b = json.loads('{\n  "a": {"c": "x", "d": [1, 2]},\n  "b": 1\n}')
        self.assertEqual(canonical_sha256(a), canonical_sha256(b))

    def test_fixed_vector(self):
        # Canonical text: {"a":"é","b":[1,2]} (keys sorted, compact, non-ASCII escaped).
        self.assertEqual(
            canonical_sha256({"b": [1, 2], "a": "é"}),
            "e72bd1bfe08db42c7cb48a01fcbbe441a57d28e5e64fcb08dcfab2cffe99f7a2",
        )

    def test_a_value_change_changes_the_digest(self):
        doc = copy.deepcopy(POLICY_DOC)
        doc["exceptions"]["max_days"] = 29
        self.assertNotEqual(canonical_sha256(doc), canonical_sha256(POLICY_DOC))


TODAY = date(2026, 10, 26)


class ExceptionFloors(unittest.TestCase):
    """A caller exception can never weaken a check the policy marks as unexceptable."""

    def entry(self, **fields):
        doc = copy.deepcopy(EXC_EX)
        doc["exceptions"][0].update(fields)
        return doc

    def test_the_example_is_applied(self):
        result = evaluate_exceptions(POLICY_DOC, EXC_EX, TODAY)
        self.assertEqual(result["rejected"], [])
        self.assertEqual(result["applied"], PLAN_EX["exceptions"]["applied"])

    def test_every_pass_fail_and_secrets_check_refuses_exceptions(self):
        unexceptable = [c["id"] for c in POLICY_DOC["checks"] if c["category"] in
                        ("format", "lint", "type", "compile", "validate", "test", "secrets")]
        self.assertIn("gitleaks", unexceptable)
        self.assertIn("mypy", unexceptable)
        for check_id in unexceptable:
            result = evaluate_exceptions(POLICY_DOC, self.entry(check=check_id), TODAY)
            self.assertEqual(result["rejected"], [{"id": "EXC-001", "reason": "check_not_exceptable"}], check_id)

    def test_a_counted_only_check_refuses_exceptions(self):
        result = evaluate_exceptions(POLICY_DOC, self.entry(check="checkov-other"), TODAY)
        self.assertEqual(result["rejected"][0]["reason"], "check_not_exceptable")

    def test_an_unknown_check(self):
        result = evaluate_exceptions(POLICY_DOC, self.entry(check="no-such-check"), TODAY)
        self.assertEqual(result["rejected"][0]["reason"], "unknown_check")

    def test_longer_than_the_cap(self):
        result = evaluate_exceptions(POLICY_DOC, self.entry(expires="2026-12-26"), TODAY)
        self.assertEqual(result["rejected"][0]["reason"], "over_max_days")

    def test_expires_before_it_was_created(self):
        result = evaluate_exceptions(POLICY_DOC, self.entry(expires="2026-10-01"), TODAY)
        self.assertEqual(result["rejected"][0]["reason"], "over_max_days")

    def test_expired(self):
        result = evaluate_exceptions(POLICY_DOC, self.entry(created="2026-09-01", expires="2026-09-30"), TODAY)
        self.assertEqual(result["rejected"][0]["reason"], "expired")

    def test_an_applied_exception_covers_only_its_own_resource(self):
        applied = evaluate_exceptions(POLICY_DOC, EXC_EX, TODAY)["applied"]
        self.assertTrue(finding_is_excepted(applied, "trivy-misconfig", "GCP-0035", "google_compute_firewall.runner_egress"))
        self.assertFalse(finding_is_excepted(applied, "trivy-misconfig", "GCP-0035", "google_compute_firewall.other_egress"))
        self.assertFalse(finding_is_excepted(applied, "trivy-misconfig", "GCP-0036", "google_compute_firewall.runner_egress"))
        self.assertFalse(finding_is_excepted(applied, "trivy-vuln", "GCP-0035", "google_compute_firewall.runner_egress"))

    def test_an_exception_without_a_code_owner_approval(self):
        doc = copy.deepcopy(EXC_EX)
        del doc["exceptions"][0]["approved_by"]
        self.assertTrue(rejected(EXCEPTIONS, doc))


class PlanProvenance(unittest.TestCase):
    """Only a plan the factory wrote for this exact head counts; anything else fails closed."""

    HEAD = PLAN_EX["commit"]
    FACTORY = PLAN_EX["factory_commit"]

    def test_the_example_is_trusted_for_its_head(self):
        self.assertTrue(plan_is_trusted(PLAN_EX, self.HEAD, self.FACTORY))

    def test_a_missing_plan(self):
        self.assertFalse(plan_is_trusted(None, self.HEAD, self.FACTORY))

    def test_a_plan_for_another_commit(self):
        self.assertFalse(plan_is_trusted(PLAN_EX, "0" * 40, self.FACTORY))

    def test_a_plan_from_another_factory_pin(self):
        self.assertFalse(plan_is_trusted(PLAN_EX, self.HEAD, "1" * 40))


class PolicyRejects(unittest.TestCase):
    """Each case weakens a playbook threshold; the schema must refuse it."""

    def mutate(self, check_id, **fields):
        doc = copy.deepcopy(POLICY_DOC)
        check(doc, check_id).update(fields)
        return doc

    def test_secret_scanning_honoring_exclusions(self):
        self.assertTrue(rejected(POLICY, self.mutate("gitleaks", honors_exclude_paths=True)))

    def test_secret_scanning_with_exceptions(self):
        self.assertTrue(rejected(POLICY, self.mutate("gitleaks", exceptions_allowed=True)))

    def test_secret_scanning_scoped_to_the_change(self):
        self.assertTrue(rejected(POLICY, self.mutate("gitleaks", scope="changed_units")))

    def test_pass_fail_check_with_exceptions(self):
        self.assertTrue(rejected(POLICY, self.mutate("tflint", exceptions_allowed=True)))

    def test_pass_fail_check_with_a_severity_threshold(self):
        self.assertTrue(rejected(POLICY, self.mutate("mypy", blocks_on="critical")))

    def test_dependency_scanner_without_kev(self):
        self.assertTrue(rejected(POLICY, self.mutate("pip-audit", blocks_on="critical")))

    def test_dependency_scanner_that_never_blocks(self):
        self.assertTrue(rejected(POLICY, self.mutate("govulncheck", blocks_on="never")))

    def test_dependency_scanner_scoped_to_the_change(self):
        self.assertTrue(rejected(POLICY, self.mutate("npm-audit", scope="changed_units")))

    def test_sast_scoped_to_the_change(self):
        self.assertTrue(rejected(POLICY, self.mutate("semgrep", scope="changed_units")))

    def test_factory_tool_without_a_version(self):
        doc = copy.deepcopy(POLICY_DOC)
        del check(doc, "ruff")["tool"]["version"]
        self.assertTrue(rejected(POLICY, doc))

    def test_version_range(self):
        doc = copy.deepcopy(POLICY_DOC)
        check(doc, "ruff")["tool"]["version"] = "^0.17"
        self.assertTrue(rejected(POLICY, doc))

    def test_project_tool_with_a_factory_pin(self):
        doc = copy.deepcopy(POLICY_DOC)
        check(doc, "tsc")["tool"]["version"] = "5.6.3"
        self.assertTrue(rejected(POLICY, doc))

    def test_rules_without_a_commit_pin(self):
        doc = copy.deepcopy(POLICY_DOC)
        check(doc, "semgrep")["tool"]["rules"]["commit"] = "develop"
        self.assertTrue(rejected(POLICY, doc))

    def test_applies_when_both_always_and_stacks(self):
        self.assertTrue(rejected(POLICY, self.mutate("trivy-vuln", applies_when={"always": True, "stacks": ["py"]})))

    def test_floors_that_can_be_turned_off(self):
        for floor in ("high_risk_runs_all", "unknown_input_runs_all"):
            doc = copy.deepcopy(POLICY_DOC)
            doc["floors"][floor] = False
            self.assertTrue(rejected(POLICY, doc), floor)

    def test_exceptions_longer_than_the_cap(self):
        doc = copy.deepcopy(POLICY_DOC)
        doc["exceptions"]["max_days"] = 120
        self.assertTrue(rejected(POLICY, doc))

    def test_secrets_listed_as_exceptable(self):
        doc = copy.deepcopy(POLICY_DOC)
        doc["exceptions"]["allowed_categories"].append("secrets")
        self.assertTrue(rejected(POLICY, doc))

    def test_unknown_field(self):
        self.assertTrue(rejected(POLICY, self.mutate("trivy-vuln", skip=True)))


class ExceptionsReject(unittest.TestCase):
    def mutate(self, **fields):
        doc = copy.deepcopy(EXC_EX)
        doc["exceptions"][0].update(fields)
        return doc

    def test_wildcard_path(self):
        self.assertTrue(rejected(EXCEPTIONS, self.mutate(path="modules/*/main.tf")))

    def test_directory_path_by_pattern(self):
        self.assertTrue(rejected(EXCEPTIONS, self.mutate(path="modules/network/**")))

    def test_path_escaping_the_repo(self):
        self.assertTrue(rejected(EXCEPTIONS, self.mutate(path="../other/main.tf")))

    def test_missing_follow_up(self):
        doc = copy.deepcopy(EXC_EX)
        del doc["exceptions"][0]["follow_up"]
        self.assertTrue(rejected(EXCEPTIONS, doc))

    def test_follow_up_that_is_not_an_issue_or_pull_request(self):
        self.assertTrue(rejected(EXCEPTIONS, self.mutate(follow_up="https://example.com/todo")))

    def test_approval_that_is_not_a_pull_request(self):
        self.assertTrue(rejected(EXCEPTIONS, self.mutate(approved_in="https://github.com/Drecoder/sovereign-vpc-gcp/issues/15")))

    def test_reason_too_short(self):
        self.assertTrue(rejected(EXCEPTIONS, self.mutate(reason="needed")))

    def test_invalid_date(self):
        self.assertTrue(rejected(EXCEPTIONS, self.mutate(expires="2026-13-40")))

    def test_missing_resource(self):
        doc = copy.deepcopy(EXC_EX)
        del doc["exceptions"][0]["resource"]
        self.assertTrue(rejected(EXCEPTIONS, doc))

    def test_unknown_field(self):
        self.assertTrue(rejected(EXCEPTIONS, self.mutate(permanent=True)))


class PlanRejects(unittest.TestCase):
    def mutate(self, fn):
        doc = copy.deepcopy(PLAN_EX)
        fn(doc)
        return doc

    def test_scoped_mode_despite_an_unreadable_input(self):
        self.assertTrue(rejected(PLAN, self.mutate(lambda d: d["inputs"]["fail_closed_reasons"].append("features_unavailable"))))

    def test_scoped_mode_for_a_high_risk_change(self):
        def high(d):
            d["inputs"]["risk"] = {"tier": "high", "reasons": ["iam"]}
        self.assertTrue(rejected(PLAN, self.mutate(high)))

    def test_high_risk_without_a_reason(self):
        def high(d):
            d["inputs"]["risk"] = {"tier": "high", "reasons": []}
            d["mode"] = "full"
        self.assertTrue(rejected(PLAN, self.mutate(high)))

    def test_standard_risk_with_a_reason(self):
        self.assertTrue(rejected(PLAN, self.mutate(lambda d: d["inputs"]["risk"]["reasons"].append("delete"))))

    def test_a_plan_with_no_checks(self):
        self.assertTrue(rejected(PLAN, self.mutate(lambda d: d.update(checks=[]))))

    def test_short_commit(self):
        self.assertTrue(rejected(PLAN, self.mutate(lambda d: d.update(commit="38cb5ac"))))

    def test_full_mode_for_a_high_risk_change_is_valid(self):
        def high(d):
            d["inputs"]["risk"] = {"tier": "high", "reasons": ["iam"]}
            d["mode"] = "full"
        self.assertFalse(rejected(PLAN, self.mutate(high)))


if __name__ == "__main__":
    unittest.main()
