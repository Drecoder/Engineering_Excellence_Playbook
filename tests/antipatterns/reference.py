"""
Reference consumer for antipatterns.v1: the behavior rig and the Reviewer must both reproduce.

Consumers share the spec and the test vectors (schemas/examples/antipatterns/finding_vectors.json),
not this code: rig (Python) and the Reviewer (TypeScript) each implement it and must pass the
same vectors. Anything here that disagrees with 00_UniversalStandards/11_Anti_Pattern_Catalog.md
is a bug in this file.
"""

import hashlib
import json
import math
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from jsonschema import Draft202012Validator

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"


def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


CATALOG_VALIDATOR = _validator("antipatterns.v1.schema.json")
FINDING_VALIDATOR = _validator("antipattern_finding.v1.schema.json")


class CatalogError(ValueError):
    pass


def check_catalog(catalog: Dict) -> None:
    """Reject an invalid catalog: schema errors, duplicate IDs, or two rules on one detector rule."""
    errors = sorted(CATALOG_VALIDATOR.iter_errors(catalog), key=lambda e: list(e.path))
    if errors:
        raise CatalogError(f"schema: {errors[0].message} at {list(errors[0].path)}")
    seen_ids, seen_detectors = set(), {}
    for rule in catalog["rules"]:
        if rule["id"] in seen_ids:
            raise CatalogError(f"duplicate rule id {rule['id']}")
        seen_ids.add(rule["id"])
        if rule["enforcement"]["state"] == "retired":
            continue
        key = (rule["detector"]["tool"], rule["detector"]["rule_id"])
        if key in seen_detectors:
            raise CatalogError(f"{rule['id']} and {seen_detectors[key]} both map {key[0]}:{key[1]}")
        seen_detectors[key] = rule["id"]


def load_catalog(path: Optional[Path] = None) -> Dict:
    catalog = json.loads((path or SCHEMAS / "antipatterns.v1.json").read_text(encoding="utf-8"))
    check_catalog(catalog)
    return catalog


def index(catalog: Dict) -> Dict[Tuple[str, str], Dict]:
    """(tool, detector rule_id) -> rule, for rules that produce findings (advisory only)."""
    return {
        (r["detector"]["tool"], r["detector"]["rule_id"]): r
        for r in catalog["rules"]
        if r["enforcement"]["state"] == "advisory"
    }


def fingerprint(rule_id: str, file: str, start_line: int, detector_rule_id: str) -> str:
    return hashlib.sha256(f"{rule_id}|{file}|{start_line}|{detector_rule_id}".encode()).hexdigest()[:16]


def normalize(hit: Dict, catalog: Dict, reported_by: str, idx: Optional[Dict] = None) -> Optional[Dict]:
    """
    Turn one detector hit {tool, rule_id, file, start_line, end_line?} into a finding, or None when
    no advisory catalog rule maps it (unmapped, planned, or retired). Severity and confidence come
    from the catalog, never from the detector. blocking is always False.
    """
    rule = (idx or index(catalog)).get((hit["tool"], hit["rule_id"]))
    if rule is None:
        return None
    file = hit["file"].replace("\\", "/")
    if file.startswith("./"):
        file = file[2:]
    finding = {
        "schema_version": "antipattern_finding.v1",
        "rule_id": rule["id"],
        "rule_revision": rule["revision"],
        "catalog_version": catalog["catalog_version"],
        "detector": {"tool": hit["tool"], "rule_id": hit["rule_id"]},
        "file": file,
        "start_line": hit["start_line"],
        "end_line": hit.get("end_line", hit["start_line"]),
        "severity": rule["severity"],
        "confidence": rule["confidence"],
        "enforcement_state": "advisory",
        "blocking": False,
        "reported_by": reported_by,
        "fingerprint": fingerprint(rule["id"], file, hit["start_line"], hit["rule_id"]),
    }
    errors = list(FINDING_VALIDATOR.iter_errors(finding))
    if errors:
        raise CatalogError(f"finding for {rule['id']} is invalid: {errors[0].message}")
    return finding


def gate_effect(findings: Iterable[Dict]) -> Dict:
    """
    What anti-pattern findings contribute to a pipeline or review decision: never a block. The CI
    gate's own thresholds still apply to the underlying tools; the catalog adds and removes nothing.
    """
    items: List[Dict] = list(findings)
    for f in items:
        if f.get("blocking") is not False:
            raise CatalogError(f"{f.get('rule_id')}: a v1 finding must carry blocking=false")
    return {"blocks": False, "advisory_findings": len(items), "exit_code": 0}


def wilson_lower_bound(successes: int, trials: int, confidence: float) -> float:
    """Wilson score interval lower bound for a proportion."""
    if trials == 0:
        return 0.0
    z = {0.90: 1.6449, 0.95: 1.96, 0.99: 2.5758}[confidence]
    p = successes / trials
    denom = 1 + z * z / trials
    centre = p + z * z / (2 * trials)
    margin = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials))
    return (centre - margin) / denom


def promotion_eligible(rule: Dict, criteria: Dict, today_iso: str) -> Tuple[bool, str]:
    """
    Whether a rule's measured evidence meets the catalog's promotion criteria. Eligible means a
    reviewed change may PROPOSE adding the detector rule to the CI gate's own list; it never makes
    the catalog block. Unmeasured rules are never eligible.
    """
    b = rule["benchmark"]
    if b["status"] != "measured":
        return False, "unmeasured"
    if rule["detector"]["mapping"]["status"] != "verified":
        return False, "mapping not verified"
    from datetime import date

    age = (date.fromisoformat(today_iso) - date.fromisoformat(b["measured_on"])).days
    if age > criteria["max_age_days"]:
        return False, f"measurement is {age} days old"
    if b["true_positives"] < criteria["min_true_positives"]:
        return False, "too few true positives"
    if b["clean_cases"] < criteria["min_clean_cases"]:
        return False, "too few clean cases"
    lb = wilson_lower_bound(b["true_positives"], b["true_positives"] + b["false_positives"], criteria["confidence_level"])
    if lb < criteria["min_precision_lower_bound"]:
        return False, f"precision lower bound {lb:.3f} below {criteria['min_precision_lower_bound']}"
    return True, "eligible for a reviewed gate proposal"
