"""
Contract tests for the Policy Engine: quality_policy.v1 (with the playbook's policy in
schemas/quality_policy.v1.json), quality_metrics.v1, policy_evaluation_request.v1 and
policy_decision.v1, and the decision rules in 00_UniversalStandards/17_Quality_Policy_Engine.md.

The decisions are recomputed here by policy_engine_reference.py on the vectors in
schemas/examples/policy_engine/vectors.json. Run inside the toolchain image:

    docker run --rm -v "$PWD:/work:ro" playbook-antipattern-toolchain \
        python -m unittest discover -s tests/contracts -v
"""

import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

sys.path.insert(0, str(Path(__file__).resolve().parent))
from design_record_reference import apply_patch  # noqa: E402
from policy_engine_reference import IMPLEMENTED, RULES, canonical, evaluate, shown  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"
EXAMPLES = SCHEMAS / "examples" / "policy_engine"
REFERENCE = Path(__file__).resolve().parent / "policy_engine_reference.py"


def load(path):
    return json.loads((SCHEMAS / path).read_text(encoding="utf-8"))


def validator(name):
    schema = load(f"{name}.schema.json")
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


V = {n: validator(n) for n in ("quality_policy.v1", "quality_metrics.v1", "policy_evaluation_request.v1", "policy_decision.v1")}
VECTORS = load("examples/policy_engine/vectors.json")
BASE = {role: load(VECTORS[role]) for role in ("candidate", "baseline", "request", "policy")}


def errors(name, doc):
    return [e.message for e in V[name].iter_errors(doc)]


def serialize(doc):
    return (json.dumps(doc, indent=2) + "\n").encode("utf-8")


def build(case):
    """The request bytes and file map for one vector."""
    docs = {role: apply_patch(copy.deepcopy(BASE[role]), case.get("patch", {}).get(role, [])) for role in BASE}
    stale = set(case.get("stale", []))
    data = {}
    for role in ("policy", "candidate", "baseline"):
        original = serialize(BASE[role]) if role in stale else None
        data[role] = case.get("raw", {}).get(role, "").encode() or serialize(docs[role])
        if role not in stale:
            docs["request"][role]["sha256"] = hashlib.sha256(data[role]).hexdigest()
        else:
            docs["request"][role]["sha256"] = hashlib.sha256(original).hexdigest()
    request = case.get("raw", {}).get("request", "").encode() or serialize(docs["request"])
    files = {docs["request"][role]["path"]: data[role] for role in data if role not in case.get("omit", [])}
    return request, files


def run(case):
    request, files = build(case)
    return evaluate(request, files)


class Schemas(unittest.TestCase):
    def test_the_playbook_policy_is_valid_and_its_rule_ids_are_unique(self):
        self.assertEqual(errors("quality_policy.v1", IMPLEMENTED), [])
        ids = [r["id"] for r in IMPLEMENTED["rules"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, sorted(ids))

    def test_the_policy_makes_unknown_severity_blocking(self):
        self.assertIn("unknown", IMPLEMENTED["vulnerabilities"]["block_new_severities"])

    def test_examples_are_valid(self):
        self.assertEqual(errors("quality_metrics.v1", BASE["candidate"]), [])
        self.assertEqual(errors("quality_metrics.v1", BASE["baseline"]), [])
        self.assertEqual(errors("policy_evaluation_request.v1", BASE["request"]), [])

    def test_the_example_request_names_the_example_files_by_their_digests(self):
        request = BASE["request"]
        for role, path in (("candidate", EXAMPLES / request["candidate"]["path"]),
                           ("baseline", EXAMPLES / request["baseline"]["path"]),
                           ("policy", SCHEMAS / request["policy"]["path"])):
            self.assertEqual(request[role]["sha256"], hashlib.sha256(path.read_bytes()).hexdigest(), role)
        self.assertEqual(request["policy"]["policy_version"], IMPLEMENTED["policy_version"])

    def test_the_example_decision_is_what_the_engine_produces(self):
        request = (EXAMPLES / "request.policy_evaluation_request.v1.json").read_bytes()
        files = {"quality_policy.v1.json": (SCHEMAS / "quality_policy.v1.json").read_bytes(),
                 "candidate.quality_metrics.v1.json": (EXAMPLES / "candidate.quality_metrics.v1.json").read_bytes(),
                 "baseline.quality_metrics.v1.json": (EXAMPLES / "baseline.quality_metrics.v1.json").read_bytes()}
        expected = (EXAMPLES / "decision.policy_decision.v1.json").read_bytes()
        self.assertEqual(canonical(evaluate(request, files)) + b"\n", expected)

    def test_metrics_reject_a_tool_from_another_language(self):
        doc = copy.deepcopy(BASE["candidate"])
        doc["toolchain"]["tools"].append({"name": "radon", "version": "6.0.1"})
        self.assertTrue(errors("quality_metrics.v1", doc))

    def test_metrics_reject_host_installed_tools(self):
        doc = copy.deepcopy(BASE["candidate"])
        doc["toolchain"]["image"] = "quality-toolchain:latest"
        self.assertTrue(errors("quality_metrics.v1", doc))

    def test_metrics_reject_precomputed_ratios(self):
        doc = copy.deepcopy(BASE["candidate"])
        doc["modules"][1]["functions"][0]["coverage"] = 1.0
        self.assertTrue(errors("quality_metrics.v1", doc))

    def test_metrics_reject_path_traversal(self):
        doc = copy.deepcopy(BASE["candidate"])
        doc["modules"][1]["path"] = "src/../../etc/passwd"
        self.assertTrue(errors("quality_metrics.v1", doc))

    def test_a_rename_needs_its_old_path_and_nothing_else_has_one(self):
        doc = copy.deepcopy(BASE["request"])
        doc["changes"][0]["status"] = "renamed"
        self.assertTrue(errors("policy_evaluation_request.v1", doc))
        doc = copy.deepcopy(BASE["request"])
        doc["changes"][0]["old_path"] = "src/old.ts"
        self.assertTrue(errors("policy_evaluation_request.v1", doc))

    def test_a_decision_and_its_exit_code_cannot_disagree(self):
        decision = run({"name": "base"})
        decision["exit_code"] = 1
        self.assertTrue(errors("policy_decision.v1", decision))

    def test_a_pass_has_no_findings_and_a_block_has_no_quarantine_finding(self):
        decision = run({"name": "base"})
        decision["findings"] = [{"rule": "QP-020", "decision": "BLOCK", "detail": "x"}]
        self.assertTrue(errors("policy_decision.v1", decision))
        decision.update(decision="BLOCK", exit_code=1, findings=[{"rule": "QP-010", "decision": "QUARANTINE", "detail": "x"}])
        self.assertTrue(errors("policy_decision.v1", decision))


class Vectors(unittest.TestCase):
    def test_every_vector(self):
        for case in VECTORS["cases"]:
            with self.subTest(case["name"]):
                decision = run(case)
                self.assertEqual(errors("policy_decision.v1", decision), [])
                got = {"decision": decision["decision"], "rules": sorted({f["rule"] for f in decision["findings"]})}
                self.assertEqual(got, case["expect"])

    def test_every_rule_is_shown_to_fail(self):
        """A rule counts only if some vector is designed to make it fail."""
        failing = {r for case in VECTORS["cases"] for r in case["expect"]["rules"]}
        self.assertEqual(sorted(set(RULES) - failing), [])

    def test_vector_names_are_unique(self):
        names = [c["name"] for c in VECTORS["cases"]]
        self.assertEqual(len(names), len(set(names)))

    def test_patched_documents_stay_schema_valid_unless_the_case_is_about_validity(self):
        for case in VECTORS["cases"]:
            if "QP-001" in case["expect"]["rules"]:
                continue
            for role, schema in (("candidate", "quality_metrics.v1"), ("baseline", "quality_metrics.v1"), ("policy", "quality_policy.v1")):
                doc = apply_patch(copy.deepcopy(BASE[role]), case.get("patch", {}).get(role, []))
                with self.subTest(case["name"], role=role):
                    self.assertEqual(errors(schema, doc), [])


class Behavior(unittest.TestCase):
    def test_the_decision_is_deterministic(self):
        case = next(c for c in VECTORS["cases"] if c["expect"]["decision"] == "QUARANTINE")
        self.assertEqual(canonical(run(case)), canonical(run(case)))

    def test_findings_are_sorted(self):
        case = next(c for c in VECTORS["cases"] if len(c["expect"]["rules"]) > 2)
        findings = run(case)["findings"]
        keys = [(f["rule"], f.get("module", ""), f.get("function", ""), f["detail"]) for f in findings]
        self.assertEqual(keys, sorted(keys))

    def test_scores_are_compared_exactly_not_after_rounding(self):
        """CRAP of 15 + 1/15625 rounds to 15.0001 and must still block; 15 exactly must pass."""
        over = {"name": "over", "patch": {"candidate": [
            {"op": "replace", "path": "/modules/1/functions/3", "value": {"name": "fenceToken", "start_line": 40, "end_line": 48,
             "complexity": 15, "lines_instrumented": 25, "lines_hit": 24}}]}}
        decision = run(over)
        self.assertIn("QP-025", {f["rule"] for f in decision["findings"]})

    def test_display_values_round_half_even(self):
        self.assertEqual(shown(Fraction(1, 20000)), 0.0)
        self.assertEqual(shown(Fraction(3, 20000)), 0.0002)
        self.assertEqual(shown(Fraction(2, 3)), 0.6667)

    def test_the_request_digest_covers_the_changes(self):
        a = run({"name": "a"})
        b = run({"name": "b", "patch": {"request": [{"op": "replace", "path": "/changes/1/hunks", "value": [[1, 31]]}]}})
        self.assertNotEqual(a["inputs"]["request"], b["inputs"]["request"])
        self.assertEqual(a["decision"], b["decision"])

    def test_garbage_never_passes_and_never_crashes(self):
        for raw in (b"", b"null", b"[]", b"{}", b"\xff", b'{"schema_version": "policy_evaluation_request.v1"}'):
            with self.subTest(raw=raw):
                decision = evaluate(raw, {})
                self.assertEqual(decision["decision"], "BLOCK")
                self.assertEqual(errors("policy_decision.v1", decision), [])


class CommandLine(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        for name in ("request.policy_evaluation_request.v1.json", "candidate.quality_metrics.v1.json", "baseline.quality_metrics.v1.json"):
            shutil.copy(EXAMPLES / name, self.dir / name)
        shutil.copy(SCHEMAS / "quality_policy.v1.json", self.dir / "quality_policy.v1.json")

    def tearDown(self):
        shutil.rmtree(self.dir)

    def cli(self):
        return subprocess.run([sys.executable, str(REFERENCE), str(self.dir / "request.policy_evaluation_request.v1.json")],
                              capture_output=True, check=False)

    def test_pass_exits_0_with_the_canonical_decision(self):
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, (EXAMPLES / "decision.policy_decision.v1.json").read_bytes())

    def test_block_exits_1(self):
        (self.dir / "baseline.quality_metrics.v1.json").write_text("{}")
        self.assertEqual(self.cli().returncode, 1)

    def test_quarantine_exits_2(self):
        request, files = build(next(c for c in VECTORS["cases"] if c["name"] == "a new function in the red CRAP zone quarantines"))
        (self.dir / "request.policy_evaluation_request.v1.json").write_bytes(request)
        for path, data in files.items():
            (self.dir / path).write_bytes(data)
        self.assertEqual(self.cli().returncode, 2)

    def test_no_request_exits_3(self):
        result = subprocess.run([sys.executable, str(REFERENCE), str(self.dir / "missing.json")], capture_output=True, check=False)
        self.assertEqual(result.returncode, 3)
        self.assertEqual(result.stdout, b"")


if __name__ == "__main__":
    unittest.main()
