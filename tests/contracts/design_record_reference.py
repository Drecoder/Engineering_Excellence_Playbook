"""
Reference behavior for service_design_record.v1 that a schema cannot express
(00_UniversalStandards/16_Service_Design_Record.md §6).

Every consumer (the Design exit gate, the Builder's intake, the Reviewer's architecture lens) must
agree with these functions on schemas/examples/design_record/relationship_vectors.json. This is a
specification aid, not the gate. Both functions return the sorted IDs of the rules that fail.
"""

import json
import math
from pathlib import Path

PLACEMENT = {"single_zone": 0, "multi_zone": 1, "multi_region": 2}
REPLICATION = {"none": 0, "asynchronous": 1, "synchronous": 2}

RULE_SET = json.loads((Path(__file__).resolve().parents[2] / "schemas" / "design_record_rules.v1.json").read_text(encoding="utf-8"))
RULES = {r["id"]: r["title"] for r in RULE_SET["rules"]}


def check_table(table: dict) -> list:
    ids = [c["id"] for c in table["classes"]]
    return ["DR-018"] if len(ids) != len(set(ids)) else []


def check_record(record: dict, table: dict) -> list:
    if record.get("rules_version") != RULE_SET["schema_version"]:
        raise ValueError(f"unsupported rule set {record.get('rules_version')!r}; this reference implements {RULE_SET['schema_version']}")
    failed = set()
    service = record["service"]
    classes = {c["id"]: c for c in table["classes"]}
    cap = record["capacity_estimate"]
    rec = record["recovery_objectives"]
    slis, slos = record["slis"], record["slos"]

    components = [cap, rec] + slis + slos
    if any(c["service"] != service for c in components):
        failed.add("DR-001")

    sli_ids = [s["id"] for s in slis]
    slo_ids = [s["id"] for s in slos]
    if len(sli_ids) != len(set(sli_ids)) or len(slo_ids) != len(set(slo_ids)):
        failed.add("DR-002")

    kinds_of = {}
    for s in slis:
        kinds_of.setdefault(s["id"], set()).add(s["kind"])
    if any(o["sli"] not in kinds_of for o in slos):
        failed.add("DR-003")
    covered = set().union(*(kinds_of.get(o["sli"], set()) for o in slos))
    if not {"availability", "latency"} <= covered:
        failed.add("DR-004")

    for o in slos:
        commitment = o.get("external_commitment_percent")
        if commitment is not None and not o["target_percent"] > commitment:
            failed.add("DR-005")
        budget_seconds = (100 - o["target_percent"]) / 100 * o["window_days"] * 86400
        if rec["rto_seconds"] > budget_seconds:
            failed.add("DR-006")

    for s in record["stores"]:
        cls = classes.get(s["data_class"])
        cached = classes.get(s["cache"]["caches_class"]) if "cache" in s else None
        if cls is None or ("cache" in s and cached is None):
            failed.add("DR-007")
        if cls is not None:
            if (s["copies"] < cls["min_copies"]
                    or PLACEMENT[s["placement"]] < PLACEMENT[cls["placement"]]
                    or REPLICATION[s["replication"]] < REPLICATION[cls["replication"]]):
                failed.add("DR-008")
            if cls["backup_required"]:
                if "backup" not in s:
                    failed.add("DR-009")
                else:
                    restore_loss = s["backup"]["interval_seconds"] + s["backup"]["completion_seconds"]
                    failover_loss = s.get("replication_lag_seconds", 0)
                    if max(restore_loss, failover_loss) > rec["rpo_seconds"]:
                        failed.add("DR-010")
                if rec["failover"]["scope"] == "region" and s["placement"] != "multi_region":
                    failed.add("DR-011")
            if s["value_data"] and cls["consistency"] != "strong":
                failed.add("DR-012")
        if cached is not None:
            c = s["cache"]
            if c["mode"] not in cached["caching"] or c["ttl_seconds"] > cached["max_staleness_seconds"]:
                failed.add("DR-013")

    if any(f["downtime_seconds"] > rec["rto_seconds"] for f in rec["failure_scenarios"]):
        failed.add("DR-019")
    expected_per_year = sum(f["expected_per_year"] * f["downtime_seconds"] for f in rec["failure_scenarios"])
    for o in slos:
        if "availability" in kinds_of.get(o["sli"], set()):
            allowed_per_year = (100 - o["target_percent"]) / 100 * 365 * 86400
            if expected_per_year > allowed_per_year:
                failed.add("DR-020")

    rate = cap["arrival_rate_per_second"]
    little = math.ceil(rate["peak"] * cap["p99_latency_ms"] / 1000)
    if cap["in_flight_at_peak"] < little:
        failed.add("DR-014")
    if record["concurrency"]["max_in_flight"] < cap["in_flight_at_peak"]:
        failed.add("DR-015")
    if rate["mean"] > rate["peak"]:
        failed.add("DR-016")
    cost = cap["monthly_cost_usd"]
    if cost["total"] + 1e-9 < cost["compute"] + cost["storage"] + cost["egress"]:
        failed.add("DR-017")

    return sorted(failed)


def apply_patch(doc, patch):
    """A JSON Patch subset (RFC 6902: add, replace, remove) over JSON Pointers, for the vectors."""
    for op in patch:
        parts = [p.replace("~1", "/").replace("~0", "~") for p in op["path"].split("/")[1:]]
        parent = doc
        for p in parts[:-1]:
            parent = parent[int(p)] if isinstance(parent, list) else parent[p]
        last = parts[-1]
        if isinstance(parent, list):
            index = len(parent) if last == "-" else int(last)
            if op["op"] == "add":
                parent.insert(index, op["value"])
            elif op["op"] == "replace":
                parent[index] = op["value"]
            else:
                del parent[index]
        elif op["op"] == "remove":
            del parent[last]
        else:
            parent[last] = op["value"]
    return doc
