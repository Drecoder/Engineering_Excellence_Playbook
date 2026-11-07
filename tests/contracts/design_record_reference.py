"""
Reference behavior for service_design_record.v1 that a schema cannot express
(00_UniversalStandards/16_Service_Design_Record.md §6).

Every consumer (the Design exit gate, the Builder's intake, the Reviewer's architecture lens) must
agree with these functions on schemas/examples/design_record/relationship_vectors.json. This is a
specification aid, not the gate. Both functions return the sorted IDs of the rules that fail.
"""

import math

PLACEMENT = {"single_zone": 0, "multi_zone": 1, "multi_region": 2}
REPLICATION = {"none": 0, "asynchronous": 1, "synchronous": 2}

RULES = {
    "DR-001": "Every component names the record's service.",
    "DR-002": "SLI ids are unique and SLO ids are unique.",
    "DR-003": "Every SLO names an SLI in the record.",
    "DR-004": "The record has an SLO on an availability SLI and an SLO on a latency SLI.",
    "DR-005": "An SLO target is strictly higher than its external commitment.",
    "DR-006": "One outage lasting the RTO fits inside every SLO's error budget.",
    "DR-007": "Every store, and every cache's cached class, names a class in the table.",
    "DR-008": "Every store meets its class's minimum copies, placement and replication.",
    "DR-009": "A store whose class requires backup declares a backup interval.",
    "DR-010": "No backup interval is longer than the RPO.",
    "DR-011": "A region-scoped failover places every backed-up store in more than one region.",
    "DR-012": "A store holding value data uses a strongly consistent class.",
    "DR-013": "A cache uses a mode its cached class allows and a TTL within that class's staleness bound.",
    "DR-014": "In-flight load at peak covers Little's Law: peak rate x P99 latency, rounded up.",
    "DR-015": "Declared concurrency holds the in-flight load at peak.",
    "DR-016": "Mean arrival rate does not exceed peak.",
    "DR-017": "Total monthly cost is at least the sum of its parts.",
    "DR-018": "Class ids in the table are unique.",
}


def check_table(table: dict) -> list:
    ids = [c["id"] for c in table["classes"]]
    return ["DR-018"] if len(ids) != len(set(ids)) else []


def check_record(record: dict, table: dict) -> list:
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
                if "backup_interval_seconds" not in s:
                    failed.add("DR-009")
                elif s["backup_interval_seconds"] > rec["rpo_seconds"]:
                    failed.add("DR-010")
                if rec["failover"]["scope"] == "region" and s["placement"] != "multi_region":
                    failed.add("DR-011")
            if s["value_data"] and cls["consistency"] != "strong":
                failed.add("DR-012")
        if cached is not None:
            c = s["cache"]
            if c["mode"] not in cached["caching"] or c["ttl_seconds"] > cached["max_staleness_seconds"]:
                failed.add("DR-013")

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
