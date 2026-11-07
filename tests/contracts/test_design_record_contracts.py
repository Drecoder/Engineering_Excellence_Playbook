"""
Contract tests for the service design record: sli.v1, slo.v1, recovery_objectives.v1,
capacity_estimate.v1, data_class.v1 (with the playbook's table in schemas/data_classes.v1.json), and
service_design_record.v1, which references the others.

The relationship rules DR-001 to DR-018 are recomputed here by design_record_reference.py from the
rules written in 00_UniversalStandards/16_Service_Design_Record.md §6. Run inside the toolchain
image:

    docker run --rm -v "$PWD:/work:ro" playbook-antipattern-toolchain \
        python -m unittest discover -s tests/contracts -v
"""

import copy
import json
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

sys.path.insert(0, str(Path(__file__).resolve().parent))
from design_record_reference import RULES, apply_patch, check_record, check_table  # noqa: E402

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"
EXAMPLES = SCHEMAS / "examples"
COMPONENTS = ("sli.v1", "slo.v1", "recovery_objectives.v1", "capacity_estimate.v1")


def load(name):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


REGISTRY = Registry().with_resources(
    (f"{n}.schema.json", Resource.from_contents(load(f"{n}.schema.json"))) for n in COMPONENTS
)


def validator(name):
    schema = load(name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker(), registry=REGISTRY)


V = {n: validator(f"{n}.schema.json") for n in COMPONENTS + ("data_class.v1", "service_design_record.v1")}
RECORD = load("examples/service_design_record.v1.example.json")
TABLE = load("data_classes.v1.json")
VECTORS = load("examples/design_record/relationship_vectors.json")


def errors(v, doc):
    return [e.message for e in v.iter_errors(doc)]


def mutated(base, fn):
    doc = copy.deepcopy(base)
    fn(doc)
    return doc


class ExamplesAreValid(unittest.TestCase):
    def test_record_example(self):
        self.assertEqual(errors(V["service_design_record.v1"], RECORD), [])

    def test_class_table(self):
        self.assertEqual(errors(V["data_class.v1"], TABLE), [])

    def test_component_examples(self):
        for n in COMPONENTS:
            with self.subTest(n):
                self.assertEqual(errors(V[n], load(f"examples/{n}.example.json")), [])

    def test_component_examples_match_the_record(self):
        """The standalone examples are the record's own parts, so the two cannot drift apart."""
        parts = [RECORD["capacity_estimate"], RECORD["recovery_objectives"]] + RECORD["slis"] + RECORD["slos"]
        for n in COMPONENTS:
            with self.subTest(n):
                self.assertIn(load(f"examples/{n}.example.json"), parts)

    def test_every_payload_carries_its_schema_version(self):
        for n in COMPONENTS + ("service_design_record.v1",):
            with self.subTest(n):
                self.assertIn("schema_version", load(f"{n}.schema.json")["required"])
        self.assertIn("schema_version", load("data_class.v1.schema.json")["required"])

    def test_record_references_components_instead_of_copying_them(self):
        props = load("service_design_record.v1.schema.json")["properties"]
        self.assertEqual(props["capacity_estimate"], {"$ref": "capacity_estimate.v1.schema.json"})
        self.assertEqual(props["recovery_objectives"], {"$ref": "recovery_objectives.v1.schema.json"})
        self.assertEqual(props["slis"]["items"], {"$ref": "sli.v1.schema.json"})
        self.assertEqual(props["slos"]["items"], {"$ref": "slo.v1.schema.json"})


class SchemasDesignedToFail(unittest.TestCase):
    """Each document breaks one schema rule and must be rejected."""

    def assertRejected(self, name, doc):
        self.assertTrue(errors(V[name], doc), f"{name} accepted an invalid document")

    def test_rejections(self):
        sli = RECORD["slis"][1]
        slo = RECORD["slos"][0]
        cases = {
            "latency SLI without slower_than": ("sli.v1", mutated(sli, lambda d: d.update(counts_as_bad=[{"condition": "server_error", "detail": "An error."}]))),
            "slower_than without a threshold": ("sli.v1", mutated(sli, lambda d: d["counts_as_bad"][0].pop("threshold_ms"))),
            "a threshold on a condition that takes none": ("sli.v1", mutated(RECORD["slis"][0], lambda d: d["counts_as_bad"][0].update(threshold_ms=10))),
            "SLO without a paging alert": ("slo.v1", mutated(slo, lambda d: d.update(burn_rate_alerts=[a for a in d["burn_rate_alerts"] if a["severity"] != "page"] * 2))),
            "SLO target of 100%": ("slo.v1", mutated(slo, lambda d: d.update(target_percent=100))),
            "SLO with an unsupported window": ("slo.v1", mutated(slo, lambda d: d.update(window_days=14))),
            "recovery with an unknown failover scope": ("recovery_objectives.v1", mutated(RECORD["recovery_objectives"], lambda d: d["failover"].update(scope="planet"))),
            "estimate without a serial point": ("capacity_estimate.v1", mutated(RECORD["capacity_estimate"], lambda d: d.pop("serial_point"))),
            "missing schema_version": ("sli.v1", mutated(sli, lambda d: d.pop("schema_version"))),
            "wrong schema_version": ("slo.v1", mutated(slo, lambda d: d.update(schema_version="slo.v2"))),
            "a strong class that allows replica reads": ("data_class.v1", mutated(TABLE, lambda d: d["classes"][3].update(replica_reads=True))),
            "a strong class with a staleness bound": ("data_class.v1", mutated(TABLE, lambda d: d["classes"][3].update(max_staleness_seconds=5))),
            "a quorum class with two copies": ("data_class.v1", mutated(TABLE, lambda d: d["classes"][4].update(min_copies=2))),
            "a cache store without its cache block": ("service_design_record.v1", mutated(RECORD, lambda d: d["stores"][2].pop("cache"))),
            "a cache block on a non-cache store": ("service_design_record.v1", mutated(RECORD, lambda d: d["stores"][1].update(cache=RECORD["stores"][2]["cache"]))),
            "a store with an unknown field": ("service_design_record.v1", mutated(RECORD, lambda d: d["stores"][1].update(region="us-east-1"))),
            "an invalid embedded component": ("service_design_record.v1", mutated(RECORD, lambda d: d["slos"][0].update(target_percent=80))),
            "a record without concurrency": ("service_design_record.v1", mutated(RECORD, lambda d: d.pop("concurrency"))),
        }
        for name, (schema, doc) in cases.items():
            with self.subTest(name):
                self.assertRejected(schema, doc)


class RelationshipRules(unittest.TestCase):
    def test_record_vectors(self):
        for case in VECTORS["record_cases"]:
            with self.subTest(case["name"]):
                doc = apply_patch(copy.deepcopy(RECORD), case["patch"])
                self.assertEqual(errors(V["service_design_record.v1"], doc), [], "a vector must stay schema-valid")
                self.assertEqual(check_record(doc, TABLE), case["expect"])

    def test_table_vectors(self):
        for case in VECTORS["table_cases"]:
            with self.subTest(case["name"]):
                doc = apply_patch(copy.deepcopy(TABLE), case["patch"])
                self.assertEqual(errors(V["data_class.v1"], doc), [], "a vector must stay schema-valid")
                self.assertEqual(check_table(doc), case["expect"])

    def test_every_rule_has_a_failing_vector(self):
        expected = {r for c in VECTORS["record_cases"] + VECTORS["table_cases"] for r in c["expect"]}
        self.assertEqual(expected, set(RULES))

    def test_every_rule_has_a_single_rule_vector(self):
        """A vector that fails only one rule proves that rule fires on its own."""
        alone = {c["expect"][0] for c in VECTORS["record_cases"] + VECTORS["table_cases"] if len(c["expect"]) == 1}
        self.assertEqual(alone, set(RULES))

    def test_vectors_reference_the_published_files(self):
        self.assertEqual(VECTORS["record"], "examples/service_design_record.v1.example.json")
        self.assertEqual(VECTORS["table"], "data_classes.v1.json")


if __name__ == "__main__":
    unittest.main()
