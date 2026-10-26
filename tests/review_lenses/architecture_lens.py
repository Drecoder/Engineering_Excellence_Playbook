"""
Reference implementation of the architecture lens's deterministic part
(06_AgentZone/04_Review_Lenses.md §3): which ARCH-* rules a unit gets, which are protected, and
which deterministic findings the model must not repeat.

Implementations (the Reviewer, in TypeScript) share the spec and the vectors this module generates
(schemas/examples/review_lenses/architecture_lens_vectors.json), not this code.

    python tests/review_lenses/architecture_lens.py --check    # vectors match this implementation
    python tests/review_lenses/architecture_lens.py --write    # regenerate the vectors
"""

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "schemas"
VECTORS = SCHEMAS / "examples" / "review_lenses" / "architecture_lens_vectors.json"

sys.path.insert(0, str(ROOT / "tests" / "antipatterns"))
from reference import check_catalog, normalize  # noqa: E402  (the catalog's reference consumer)


def _load(name: str) -> Dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def load_rules() -> Dict:
    rules = _load("architecture_rules.v1.json")
    errors = list(Draft202012Validator(_load("architecture_rules.v1.schema.json")).iter_errors(rules))
    if errors:
        raise ValueError(f"invalid architecture rules: {errors[0].message}")
    return rules


def load_catalog() -> Dict:
    catalog = _load("antipatterns.v1.json")
    check_catalog(catalog)
    return catalog


def catalog_links(catalog: Dict, rules: Dict) -> Dict[str, List[str]]:
    """AP-* rule -> the ARCH-* rules it enforces, from the catalog's `related` field (the one home of the link)."""
    arch_ids = {r["id"] for r in rules["rules"]}
    links: Dict[str, List[str]] = {}
    for r in catalog["rules"]:
        arch = [x for x in r.get("related", []) if x.startswith("ARCH-")]
        unknown = [x for x in arch if x not in arch_ids]
        if unknown:
            raise ValueError(f"{r['id']} names unknown architecture rules {unknown}")
        if arch:
            links[r["id"]] = arch
    return links


def _rig_evidence(f: Dict) -> str:
    if f.get("source") == "trace":
        return f"trace {f['trace_id']} span {f['span_id']}"
    if f.get("source") == "static":
        return f["location"]
    return "deterministic"


def lens(features: Optional[Dict], antipattern_findings: List[Dict], rules: Dict, catalog: Dict) -> Dict:
    """The lens's deterministic outcome for one unit."""
    if features is None:
        return {"runs": False}
    if features["missing"]:
        selected, selected_by = list(rules["rules"]), "fail_closed"
    else:
        touches = set(features["structure"].get("touches", []))
        selected = [r for r in rules["rules"] if touches & set(r["applies_when"])]
        selected_by = "touches"
    if not selected:
        return {"runs": False}

    order = {r["id"]: i for i, r in enumerate(selected)}
    known = []
    for f in features.get("rule_findings", []):
        if f["rule"] in order:
            known.append({"rule": f["rule"], "source": "rig", "result": f.get("result", "violation"),
                          "evidence": _rig_evidence(f)})
    links = catalog_links(catalog, rules)
    for a in antipattern_findings:
        for arch in links.get(a["rule_id"], []):
            if arch in order:
                known.append({"rule": arch, "source": "catalog", "result": "violation", "finding": a["rule_id"],
                              "detector": f"{a['detector']['tool']}:{a['detector']['rule_id']}",
                              "evidence": f"{a['file']}:{a['start_line']}"})
    known.sort(key=lambda k: (order[k["rule"]], 0 if k["source"] == "rig" else 1, k.get("finding", ""), k["evidence"]))

    return {
        "runs": True,
        "selected_by": selected_by,
        "selected_rule_ids": [r["id"] for r in selected],
        "protected": [{"rule": r["id"], "class": r["protected_class"]} for r in selected if r.get("protected_class")],
        "known_findings": known,
    }


# ---------------------------------------------------------------------------------------------
# Vector inputs
# ---------------------------------------------------------------------------------------------


def _features(touches=None, missing=(), rule_findings=()) -> Dict:
    f = {
        "schema_version": "features.v1", "unit_id": "u1", "lane": "accept", "repo": "drecoder/svc",
        "sha": "3f66082", "language": "typescript",
        "diff": {"lines_added": 12, "lines_removed": 3, "hunks": 2, "file_kind": "code"},
        "structure": {"visibility": "internal", "fan_in": 1, "fan_out": 2}, "missing": list(missing),
    }
    if touches is not None:
        f["structure"]["touches"] = list(touches)
    if rule_findings:
        f["rule_findings"] = list(rule_findings)
    return f


def _ap(catalog: Dict, tool: str, rule_id: str, file: str, line: int) -> Dict:
    return normalize({"tool": tool, "rule_id": rule_id, "file": file, "start_line": line}, catalog, "rig")


def vector_inputs(catalog: Dict) -> List[Dict]:
    trace = {"rule": "ARCH-005", "blocking": True, "source": "trace", "result": "violation",
             "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736", "span_id": "00f067aa0ba902b7"}
    static_other = {"rule": "ARCH-019", "blocking": True, "source": "static", "result": "violation",
                    "location": "src/routes/users.ts:40"}
    unverifiable = {"rule": "ARCH-017", "blocking": False, "source": "trace", "result": "unverifiable",
                    "trace_id": "0af7651916cd43dd8448eb211c80319c", "span_id": "b7ad6b7169203331"}
    return [
        {"name": "no_features_record", "features": None, "antipattern_findings": []},
        {"name": "touches_nothing_covered", "features": _features(touches=[]), "antipattern_findings": []},
        {"name": "migration_with_catalog_hits", "features": _features(touches=["migration"]),
         "antipattern_findings": [_ap(catalog, "squawk", "adding-required-field", "migrations/0042.sql", 1),
                                  _ap(catalog, "squawk", "ban-drop-column", "migrations/0043.sql", 2)]},
        {"name": "queue_publish", "features": _features(touches=["queue_publish"]), "antipattern_findings": []},
        {"name": "rig_hits_only_for_selected_rules", "features": _features(touches=["db_transaction"], rule_findings=[trace, static_other]),
         "antipattern_findings": []},
        {"name": "fail_closed_selects_every_rule", "features": _features(touches=[], missing=["stale_index"]),
         "antipattern_findings": [_ap(catalog, "bandit", "B113", "src/client.py", 9)]},
        {"name": "catalog_hits_filtered_by_selected_rules",
         "features": _features(touches=["http_client"], rule_findings=[unverifiable]),
         "antipattern_findings": [_ap(catalog, "bandit", "B113", "src/client.py", 9),
                                  _ap(catalog, "oasdiff", "response-required-property-removed", "api/openapi.yaml", 30),
                                  _ap(catalog, "eslint-plugin-react-hooks", "react-hooks/rules-of-hooks", "web/a.tsx", 4)]},
        {"name": "cache_protected_security", "features": _features(touches=["cache"]), "antipattern_findings": []},
    ]


def build_vectors() -> Dict:
    rules, catalog = load_rules(), load_catalog()
    vectors = []
    for v in vector_inputs(catalog):
        vectors.append({**v, "expected": lens(v["features"], v["antipattern_findings"], rules, catalog)})
    return {
        "description": "Conformance vectors for the architecture lens (06_AgentZone/04_Review_Lenses.md §3). For each unit (a features.v1 record, or null, and its antipattern_finding.v1 findings), an implementation must produce exactly `expected`: whether the lens runs, how rules were selected, the selected ARCH-* rules in file order, the protected rules, and the known findings the model must not repeat (rig's hits and catalog findings whose rule is related to a selected ARCH rule). Generated by tests/review_lenses/architecture_lens.py.",
        "architecture_rules_count": len(rules["rules"]),
        "catalog_version": catalog["catalog_version"],
        "vectors": vectors,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    args = ap.parse_args()
    built = build_vectors()
    text = json.dumps(built, indent=2, ensure_ascii=False) + "\n"
    if args.write:
        VECTORS.parent.mkdir(parents=True, exist_ok=True)
        VECTORS.write_text(text, encoding="utf-8")
        print(f"wrote {len(built['vectors'])} vectors")
        return 0
    current = VECTORS.read_text(encoding="utf-8") if VECTORS.exists() else ""
    if current != text:
        print("architecture lens vectors are out of date; run with --write", file=sys.stderr)
        return 1
    print(f"{len(built['vectors'])} vectors up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
