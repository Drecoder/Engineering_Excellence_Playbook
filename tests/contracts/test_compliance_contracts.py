"""
Contract tests for the compliance engine: compliance_submission.v6, compliance_registry.v1, and the
canonical identity and attestation payload vectors every implementation must reproduce.

The payloads and digests are recomputed here from the rule in 06_AgentZone/02_Compliance_Engine.md,
independently of any implementation. Run inside the toolchain image (it pins rfc3339-validator,
without which jsonschema silently skips date-time checks):

    docker run --rm -v "$PWD:/work:ro" playbook-antipattern-toolchain \
        python -m unittest discover -s tests/contracts -v
"""

import copy
import hashlib
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"
FORMATS = FormatChecker()


def load(name):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def validator(name):
    schema = load(name)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FORMATS)


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256(text):
    return "sha256:" + hashlib.sha256(text.encode("ascii")).hexdigest()


def attestation_payload(evidence):
    fields = {k: v for k, v in evidence.items() if k != "attestation_signature"}
    fields["monitored_paths"] = sorted(fields["monitored_paths"])
    return canonical_json(fields)


SUBMISSION = validator("compliance_submission.v6.schema.json")
REGISTRY = validator("compliance_registry.v1.schema.json")
IDENTITY = load("examples/compliance/canonical_identity_vectors.json")
ATTESTATION = load("examples/compliance/attestation_payload_vectors.json")


def submission(evidence, artifact=None):
    return {
        "contract_version": "6.0.0",
        "submission_id": "sub-1",
        "lifecycle_stage": "PRODUCTION_READINESS",
        "submitted_at": "2026-10-28T10:00:00Z",
        "evaluated_artifact": artifact or IDENTITY["vectors"][0]["artifact"],
        "evidence": [evidence],
    }


def errors(v, doc):
    return [e.message for e in v.iter_errors(doc)]


class FormatsAreChecked(unittest.TestCase):
    def test_date_time_checker_is_active(self):
        self.assertIn("date-time", FORMATS.checkers, "install rfc3339-validator")


class CanonicalIdentity(unittest.TestCase):
    def test_vectors_reproduce(self):
        for vector in IDENTITY["vectors"]:
            identity = canonical_json(vector["artifact"])
            self.assertEqual(identity, vector["canonical_identity"])
            self.assertEqual(sha256(identity), vector["identity_digest"])

    def test_vector_artifacts_are_valid(self):
        evidence = ATTESTATION["vectors"][0]["evidence"]
        for vector in IDENTITY["vectors"]:
            self.assertEqual(errors(SUBMISSION, submission(evidence, vector["artifact"])), [])


class AttestationPayload(unittest.TestCase):
    def test_vectors_reproduce(self):
        for vector in ATTESTATION["vectors"]:
            payload = attestation_payload(vector["evidence"])
            self.assertEqual(payload, vector["attestation_payload"], vector["note"])
            self.assertEqual(sha256(payload), vector["payload_sha256"], vector["note"])

    def test_payload_has_the_eleven_signed_fields(self):
        for vector in ATTESTATION["vectors"]:
            self.assertEqual(len(json.loads(vector["attestation_payload"])), 11)

    def test_vector_evidence_is_valid(self):
        for vector in ATTESTATION["vectors"]:
            self.assertEqual(errors(SUBMISSION, submission(vector["evidence"])), [], vector["note"])

    def test_timestamp_is_signed_as_submitted(self):
        stamps = {json.loads(v["attestation_payload"])["timestamp_utc"] for v in ATTESTATION["vectors"]}
        self.assertEqual(stamps, {v["evidence"]["timestamp_utc"] for v in ATTESTATION["vectors"]})

    def test_changing_any_signed_field_changes_the_payload(self):
        evidence = ATTESTATION["vectors"][0]["evidence"]
        original = attestation_payload(evidence)
        changes = {
            "evidence_tier": "OBSERVED",
            "evidence_presence": False,
            "check_version": "1.4.3",
            "verification_result": "FAILED",
            "monitored_paths": ["src/z.py"],
            "timestamp_utc": "2026-10-28T10:00:00.0Z",
        }
        for field, value in changes.items():
            tampered = {**copy.deepcopy(evidence), field: value}
            self.assertNotEqual(attestation_payload(tampered), original, field)


class Timestamps(unittest.TestCase):
    def test_invalid_timestamps_are_rejected(self):
        evidence = ATTESTATION["vectors"][0]["evidence"]
        for stamp in ATTESTATION["invalid_timestamps"]:
            doc = submission({**evidence, "timestamp_utc": stamp})
            self.assertNotEqual(errors(SUBMISSION, doc), [], stamp)


class Registry(unittest.TestCase):
    def test_registry_is_valid(self):
        self.assertEqual(errors(REGISTRY, load("compliance_registry.v1.json")), [])

    def test_no_stage_lists_a_criterion_twice(self):
        for version, contract in load("compliance_registry.v1.json")["contracts"].items():
            for stage, body in contract["stages"].items():
                ids = [c["criterion_id"] for c in body["criteria"]]
                self.assertEqual(len(ids), len(set(ids)), f"{version}/{stage}")

    def test_production_readiness_needs_verified_evidence(self):
        stage = load("compliance_registry.v1.json")["contracts"]["6.0.0"]["stages"]["PRODUCTION_READINESS"]
        tiers = {c["criterion_id"]: c["min_evidence_tier"] for c in stage["criteria"]}
        self.assertEqual(tiers, {"DEC-001": "VERIFIED", "RES-001": "VERIFIED", "SEC-001": "VERIFIED"})


if __name__ == "__main__":
    unittest.main()
