"""
Conformance cases for the adaptive harness (06_AgentZone/09_Adaptive_Harness.md, PROPOSED): the
test-design stage, KAN-47. The cases are schemas/examples/harness/vectors.json; the oracle is
harness_reference.py.

Inputs and decisions are checked against the playbook's locked harness_decision.v1 and
knowledge_record.v1. Every violation is emitted as a ddi.event.v1 (kind "error") and a
ddi.capa_draft.v1 citing eep-rule IDs, validated against Drecoder/agent-ddi-harness's schemas at the
commit pinned in harness_conformance/ddi_pin.json. Those files are read from a checkout of that
commit, never copied: set DDI_HARNESS_DIR, or check it out at .ddi-harness in the repository root.
A missing or changed pinned file fails these tests; it never skips them.

Designed-to-fail cases count only when shown to fail: each must be caught, and must pass through
when the checks it expects are switched off. Every check and every schema constraint has such a case.

    git clone https://github.com/Drecoder/agent-ddi-harness .ddi-harness
    git -C .ddi-harness checkout <commit in tests/contracts/harness_conformance/ddi_pin.json>
    docker run --rm -v "$PWD:/work:ro" playbook-antipattern-toolchain \
        python -m unittest discover -s tests/contracts -v
"""

import copy
import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_reference as ref  # noqa: E402
from context_order_reference import pass_orders, slot_of  # noqa: E402
from design_record_reference import apply_patch  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"
VECTORS = json.loads((SCHEMAS / "examples/harness/vectors.json").read_text(encoding="utf-8"))
PIN = json.loads((Path(__file__).resolve().parent / "harness_conformance/ddi_pin.json").read_text(encoding="utf-8"))
DDI = Path(os.environ.get("DDI_HARNESS_DIR", ROOT / ".ddi-harness"))
CASES = VECTORS["cases"]
BY_TARGET = {}
for _c in CASES:
    BY_TARGET.setdefault(_c["target"], []).append(_c)
CHECKED = ("decision", "record", "gate")


def base(kind):
    return json.loads((SCHEMAS / VECTORS["base"][kind]).read_text(encoding="utf-8"))


def context(case):
    return apply_patch(copy.deepcopy(VECTORS["context"]), copy.deepcopy(case.get("context_patch", [])))


def decision(case):
    return apply_patch(base("decision"), copy.deepcopy(case["patch"]))


def record(case):
    return apply_patch(base("record"), copy.deepcopy(case["patch"]))


def violations(case, disabled=frozenset()):
    """The check names the reference reports for a decision, record or gate case."""
    if case["target"] == "decision":
        return [c for c, _ in ref.check_decision(decision(case), context(case), disabled)]
    if case["target"] == "record":
        return [c for c, _ in ref.check_record(record(case), context(case), disabled)]
    ctx = None if case.get("context_unavailable") else context(case)
    _allow, found = ref.action_gate(decision(case), ctx, case["gate"], disabled)
    return [c for c, _ in found]


def schema_paths(doc_kind, doc):
    validator = ref.VALIDATE[doc_kind]
    return ["/".join(map(str, e.absolute_schema_path)) for e in validator.iter_errors(doc)]


def ddi_file(rel):
    path = DDI / rel
    if not path.is_file():
        raise AssertionError(f"pinned agent-ddi-harness file missing: {path} (check out {PIN['commit']})")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != PIN["files"][rel]:
        raise AssertionError(f"{rel} does not match the pin at {PIN['commit']}")
    return json.loads(data)


class Pin(unittest.TestCase):
    def test_every_pinned_file_matches(self):
        self.assertRegex(PIN["commit"], r"^[0-9a-f]{40}$")
        for rel in PIN["files"]:
            with self.subTest(rel):
                ddi_file(rel)

    def test_every_cited_eep_rule_resolves_in_the_pinned_catalog(self):
        rule_schema = Draft202012Validator(ddi_file("schemas/eep-rule.schema.json"))
        catalog = {r["id"]: r for f in ("eep-rules/habits.json", "eep-rules/capa.json") for r in ddi_file(f)["rules"]}
        for check in ref.CHECKS:
            for rid in ref.eep_rules(check):
                with self.subTest(check=check, rule=rid):
                    self.assertIn(rid, catalog)
                    self.assertEqual(list(rule_schema.iter_errors(catalog[rid])), [])


class Vectors(unittest.TestCase):
    def test_ids_are_unique_and_every_case_is_tagged(self):
        ids = [c["id"] for c in CASES]
        self.assertEqual(len(ids), len(set(ids)))
        for c in CASES:
            with self.subTest(c["id"]):
                self.assertTrue(c["criteria"])
                self.assertTrue(set(c["criteria"]) <= set(range(1, 25)))

    def test_every_acceptance_criterion_has_a_case(self):
        covered = {n for c in CASES for n in c["criteria"]}
        self.assertEqual(sorted(set(range(1, 25)) - covered), [])

    def test_every_adversarial_case_of_section_14_is_present(self):
        wanted = {
            "a forged stale GREEN", "sources that contradict each other",
            "a decision record whose policy-decision digest does not verify",
            "a retrieved record carrying instructions", "a highly similar CLAIMED record competing with a VERIFIED one",
            "the budget running out in the middle of an escalation", "steering that oscillates",
            "a defect counted against a practice without its attribution chain",
        }
        present = {c["adversarial"] for c in CASES if "adversarial" in c}
        self.assertEqual(sorted(wanted - present), [])
        for c in CASES:
            if "adversarial" in c:
                with self.subTest(c["id"]):
                    self.assertTrue(c["designed_to_fail"])


class DecisionTable(unittest.TestCase):
    def test_each_case_gives_its_expected_violations(self):
        for c in BY_TARGET["decision"] + BY_TARGET["record"] + BY_TARGET["gate"]:
            with self.subTest(c["id"]):
                self.assertEqual(sorted(set(violations(c))), sorted(c["expect"]["violations"]))

    def test_each_case_gives_its_expected_row(self):
        for c in BY_TARGET["decision"]:
            if "row" in c["expect"]:
                with self.subTest(c["id"]):
                    self.assertEqual(ref.row(decision(c), context(c)), c["expect"]["row"])

    def test_every_row_has_a_case(self):
        rows = {c["expect"]["row"] for c in BY_TARGET["decision"] if "row" in c["expect"]}
        self.assertEqual(sorted(set(ref.ROWS) - rows), [])

    def test_the_first_matching_row_decides(self):
        # A spent budget on a QUARANTINE with missing-evidence findings is still row 1, not 2 or 3.
        c = next(x for x in CASES if x["id"] == "HD-006")
        d = decision(c)
        d["inputs"]["governance"]["budget_spent_fraction"] = 1.5
        d["inputs"]["quality"]["rules"] = ["QP-030", "QP-002"]
        self.assertEqual(ref.row(d, context(c)), 1)

    def test_no_row_allows_an_action_outside_the_vocabulary(self):
        vocab = set(ref.VALIDATE["harness_decision.v1"].schema["properties"]["action"]["properties"]["kind"]["enum"])
        for n in ref.ROWS:
            with self.subTest(row=n):
                self.assertTrue(ref.allowed(n) <= vocab)
        self.assertTrue({"approve", "merge", "deploy", "grant", "restore_concurrency"}.isdisjoint(vocab))

    def test_retrieved_text_never_reaches_the_table(self):
        # The table reads standing and tier only; a record's summary cannot move the row.
        c = next(x for x in CASES if x["id"] == "HD-007")
        d = decision(c)
        before = ref.row(d, context(c))
        d["inputs"]["knowledge"][0]["evidence_tier"] = "VERIFIED"
        self.assertEqual(ref.row(d, context(c)), before)
        self.assertEqual(before, 2)


class Proof(unittest.TestCase):
    """Each designed-to-fail case is shown to fail, and each check and schema constraint has one."""

    def test_designed_to_fail_cases_are_caught_and_pass_without_their_checks(self):
        for c in [x for t in CHECKED for x in BY_TARGET[t] if x["designed_to_fail"]]:
            with self.subTest(c["id"]):
                expected = set(c["expect"]["violations"])
                self.assertTrue(expected, "a designed-to-fail case must expect a violation")
                self.assertEqual(violations(c, disabled=frozenset(expected)), [],
                                 "with its checks switched off the defect must get through")

    def test_controls_report_nothing(self):
        for c in [x for t in CHECKED for x in BY_TARGET[t] if not x["designed_to_fail"]]:
            with self.subTest(c["id"]):
                self.assertEqual(violations(c), [])

    def test_every_check_has_a_case_designed_to_fail_it(self):
        exercised = {v for x in CASES if x["designed_to_fail"] for v in x["expect"].get("violations", [])}
        self.assertEqual(sorted(set(ref.CHECKS) - exercised), [])

    def test_every_schema_constraint_has_a_case_that_trips_it(self):
        constraints = []
        for kind in ("harness_decision.v1", "knowledge_record.v1"):
            schema = ref.VALIDATE[kind].schema
            constraints += [f"{kind}#/allOf/{i}" for i in range(len(schema["allOf"]))]
        constraints += [f"harness_decision.v1#/properties/{p}" for p in
                        ("action/allOf/0", "action/allOf/1", "inputs/properties/quality")]
        tripped = set()
        for c in CASES:
            for want in c["expect"].get("schema_constraints", []):
                kind, prefix = want.split("#/")
                doc = decision(c) if kind == "harness_decision.v1" else record(c)
                with self.subTest(c["id"], constraint=want):
                    self.assertTrue(any(p.startswith(prefix) for p in schema_paths(kind, doc)), schema_paths(kind, doc))
                tripped.add(want)
        self.assertEqual(sorted(set(constraints) - tripped), [])


class ReliabilityStates(unittest.TestCase):
    def test_each_fixture_gives_its_state(self):
        for c in BY_TARGET["state"]:
            with self.subTest(c["id"]):
                self.assertEqual(ref.service_state(c["sources"], c["now"]), c["expect"]["state"])

    def test_designed_to_fail_fixtures_defeat_a_naive_reader(self):
        # A reader that trusts "not firing" as GREEN gets every designed-to-fail fixture wrong.
        def naive(sources):
            return "RED" if any(p["firing"] for s in sources for p in s["pairs"]) else "GREEN"
        for c in BY_TARGET["state"]:
            if c["designed_to_fail"]:
                with self.subTest(c["id"]):
                    self.assertNotEqual(naive(c["sources"]), c["expect"]["state"])

    def test_unknown_never_becomes_green(self):
        for c in BY_TARGET["state"]:
            if c["expect"]["state"] == "UNKNOWN":
                with self.subTest(c["id"]):
                    self.assertNotEqual(ref.service_state(c["sources"], c["now"]), "GREEN")


class Retrieval(unittest.TestCase):
    def _run(self, c):
        ctx = context(c)
        ctx["source_digests"] = {r["record_id"]: r["source"]["sha256"] for r in c["records"]
                                 if r["record_id"] not in c.get("tamper", [])}
        return ref.retrieve(c["records"], c["query"], ctx)

    def test_records_are_valid(self):
        for c in BY_TARGET["retrieval"] + BY_TARGET["render"]:
            for r in c["records"]:
                with self.subTest(c["id"], record=r["record_id"]):
                    self.assertEqual(schema_paths("knowledge_record.v1", r), [])

    def test_each_case_gives_its_order_and_labels(self):
        for c in BY_TARGET["retrieval"]:
            with self.subTest(c["id"]):
                got = self._run(c)
                self.assertEqual([g["record_id"] for g in got], c["expect"]["order"])
                for rid, label in c["expect"].get("labels", {}).items():
                    self.assertEqual(next(g["label"] for g in got if g["record_id"] == rid), label)

    def test_similarity_order_fails_every_designed_to_fail_case(self):
        for c in BY_TARGET["retrieval"]:
            if c["designed_to_fail"]:
                with self.subTest(c["id"]):
                    by_similarity = sorted(c["similarity"], key=lambda r: -c["similarity"][r])
                    self.assertNotEqual(by_similarity, c["expect"]["order"])

    def test_instructions_in_a_record_stay_data(self):
        for c in BY_TARGET["render"]:
            with self.subTest(c["id"]):
                out = ref.render_retrieved(c["records"])
                self.assertEqual(out.count("</retrieved_records>"), c["expect"]["closing_tags"])
                body = [json.loads(line) for line in out.splitlines()[1:-1]]
                self.assertEqual([b["summary"] for b in body], [r["summary"] for r in c["records"]])
                summaries = "\n".join(r["summary"] for r in c["records"])
                naive = f"<retrieved_records>\n{summaries}\n</retrieved_records>"
                self.assertNotEqual(naive.count("</retrieved_records>"), c["expect"]["closing_tags"])


class Boundary(unittest.TestCase):
    def test_inbound_passes_input_unchanged(self):
        for c in BY_TARGET["inbound"]:
            if "text" in c:
                with self.subTest(c["id"]):
                    out = ref.inbound(c["text"], c["rotor"])
                    self.assertEqual(out["text"] == c["text"], c["expect"]["text_unchanged"])
                    self.assertEqual(out["warning"] is not None, c["expect"]["warning"])

    def test_unknown_rotor_state_is_refused(self):
        with self.assertRaises(ValueError):
            ref.inbound("x", "promoted-without-review")

    def test_golden_readme_miss(self):
        c = next(x for x in BY_TARGET["inbound"] if "weights" in x)
        slots = slot_of(c["weights"])[c["focus"]]
        self.assertEqual(sorted(slots), sorted(c["expect"]["slots"]))
        self.assertEqual(pass_orders(c["weights"])[0], list(range(len(c["weights"]))))
        # A single linear read leaves the focus section in the middle and never first: the miss.
        linear = list(range(len(c["weights"])))
        self.assertNotEqual(linear.index(c["focus"]), 0)
        self.assertTrue(c["designed_to_fail"])

    def test_gate_cases_allow_or_deny(self):
        for c in BY_TARGET["gate"]:
            with self.subTest(c["id"]):
                ctx = None if c.get("context_unavailable") else context(c)
                allow, _ = ref.action_gate(decision(c), ctx, c["gate"])
                self.assertEqual(allow, c["expect"]["allow"])


class GoldenTasks(unittest.TestCase):
    def test_runs_through_the_gate(self):
        for c in BY_TARGET["golden"]:
            with self.subTest(c["id"]):
                ctx = copy.deepcopy(VECTORS["context"])
                previous = ctx["run_decisions"][-1]
                got = []
                for i, step in enumerate(c["steps"]):
                    d = apply_patch(base("decision"), copy.deepcopy(step["patch"]))
                    d["decision_id"] = f"{i + 1:08d}-1111-4111-8111-{i + 1:012d}"
                    d["previous"] = {"decision_id": previous, "outcome": "completed"}
                    allow, _ = ref.action_gate(d, ctx, "up")
                    got.append(allow)
                    ctx["run_decisions"].append(d["decision_id"])
                    previous = d["decision_id"]
                self.assertEqual(got, c["expect"]["allowed"])
                if c["designed_to_fail"]:
                    self.assertIn(False, got)


class Emission(unittest.TestCase):
    """Every block emits a ddi.event.v1 (kind error) and a ddi.capa_draft.v1 at the pinned commit."""

    @classmethod
    def setUpClass(cls):
        def load(rel):
            return Draft202012Validator(ddi_file(rel), format_checker=FormatChecker())
        cls.event_schema = load("schemas/ddi-event.schema.json")
        cls.draft_schema = load("schemas/capa-conflict-draft.schema.json")

    def test_every_violation_emits_a_valid_event_and_draft(self):
        n = 0
        for c in [x for t in CHECKED for x in BY_TARGET[t]]:
            ctx = None if c.get("context_unavailable") else context(c)
            if c["target"] == "decision":
                found = ref.check_decision(decision(c), ctx)
            elif c["target"] == "record":
                found = ref.check_record(record(c), ctx)
            else:
                found = ref.action_gate(decision(c), ctx, c["gate"])[1]
            for check, message in found:
                event, draft = ref.emit(check, message, c["id"], "run-" + c["id"].lower(), 1.0, "2026-11-08T02:40:01Z")
                with self.subTest(c["id"], check=check):
                    self.assertEqual(event["kind"], "error")
                    self.assertEqual([e.message for e in self.event_schema.iter_errors(event)], [])
                    self.assertEqual([e.message for e in self.draft_schema.iter_errors(draft)], [])
                    self.assertIn("CAPA-001", event["eep_rules"])
                    self.assertEqual(draft["status"], "draft")
                    n += 1
        self.assertGreater(n, 0)

    def test_a_recurrence_updates_the_same_draft(self):
        a = ref.emit("schema", "x", "HD-007", "run-1", 1.0, "2026-11-08T02:40:01Z")[1]
        b = ref.emit("schema", "y", "HD-007", "run-2", 9.0, "2026-11-09T02:40:01Z")[1]
        c = ref.emit("schema", "x", "HD-008", "run-1", 1.0, "2026-11-08T02:40:01Z")[1]
        self.assertEqual(a["fingerprint"], b["fingerprint"])
        self.assertNotEqual(a["fingerprint"], c["fingerprint"])

    def test_a_forged_certification_is_rejected(self):
        event, draft = ref.emit("schema", "x", "HD-007", "run-1", 1.0, "2026-11-08T02:40:01Z")
        self.assertTrue(list(self.event_schema.iter_errors({**event, "ci_signed_evidence": True})))
        self.assertTrue(list(self.draft_schema.iter_errors({**draft, "trust": "ci_certified"})))


if __name__ == "__main__":
    unittest.main()
