"""
Reference checker for the adaptive harness (06_AgentZone/09_Adaptive_Harness.md, PROPOSED).

A specification aid and conformance oracle for the test-design stage (KAN-47), not the harness.
Every implementation must agree with it on schemas/examples/harness/vectors.json.

It checks inputs and decisions against the playbook's locked contracts, harness_decision.v1 and
knowledge_record.v1, and adds the cross-file checks those schemas leave to the standard (a
concurrency target within the approved ceiling, a rung on model_ladder.v1 chosen at a task boundary,
a retry within the attempt limit, freshness, attribution chains, retrieval order). It defines no new
contract. Every violation is reported as a ddi.event.v1 (kind "error") and a ddi.capa_draft.v1 that
cite eep-rule IDs; those schemas belong to Drecoder/agent-ddi-harness and are read at the commit
pinned in tests/contracts/harness_conformance/ddi_pin.json, never copied.

Pure: no clock, network or environment. The decision time is the decision's own recorded_at; the
caller passes everything else (the policy decision's digest, the ceiling, the run's earlier
decisions, today's date for review_by) in a context dict. Missing context fails closed.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"
LADDER = json.loads((SCHEMAS / "model_ladder.v1.json").read_text(encoding="utf-8"))


def _validator(name):
    schema = json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=FormatChecker())


VALIDATE = {n: _validator(n) for n in ("harness_decision.v1", "knowledge_record.v1")}

# §5: GREEN needs every burn-rate pair evaluated within its own short window.
SHORT_WINDOW = {"page": timedelta(minutes=5), "ticket": timedelta(minutes=30)}
# A recorded GREEN carries one evaluation time, so it must be inside the stricter (page) window.
GREEN_FRESH = SHORT_WINDOW["page"]

# §6 terms, from the Policy Engine's rule IDs.
HIGH_CRAP = frozenset({"QP-011", "QP-025", "QP-030"})
SURVIVING = frozenset({"QP-013", "QP-021", "QP-031"})
EVIDENCE_FINDINGS = frozenset(f"QP-00{i}" for i in range(1, 7))

# §7: the allowed action set of each row. Row 0 is "the table cannot decide" (§10): pause or escalate.
ROWS = {
    0: frozenset({"pause", "escalate_to_human"}),
    1: frozenset({"stop", "escalate_to_human"}),
    2: frozenset({"stop", "escalate_to_human"}),
    3: frozenset({"request_evaluation", "pause", "stop", "escalate_to_human"}),
    4: frozenset({"stop", "route_remediation", "escalate_to_human"}),
    5: frozenset({"route_remediation"}),
    6: frozenset({"route_remediation"}),
    7: frozenset({"route_remediation"}),
    8: frozenset({"pause", "escalate_to_human"}),
    9: frozenset({"pace_down", "reduce_concurrency", "retry", "switch_tool", "pause"}),
    10: frozenset({"request_evidence", "pause", "escalate_to_human"}),
    11: frozenset({"request_evaluation", "advance"}),
    12: frozenset({"advance"}),
}
# §7 "within a row, the harness may also reorder its own work, change pacing, and choose a tool or a
# ladder rung for the next task". Not in rows 1-3, which the schema closes to stop/escalate-class
# actions, and never in row 0.
WITHIN_ROW = frozenset({"reorder_work", "pace_down", "switch_tool", "change_model_rung"})

# §3: transient events are never promoted into long-term memory.
TRANSIENT = frozenset({"tool_failure", "retry", "timeout", "build_failure:infra", "build_failure:flaky",
                       "build_failure:unknown"})

# Each check and the eep-rule IDs its violation cites. Every violation is a block (CAPA-001) and its
# draft is only a claim (CAPA-003); evidence checks add HAB-005 (prove with evidence) and scope checks
# HAB-004 (keep to what the intent asks). Recurrence is CAPA-002: the draft's fingerprint is stable.
EVIDENCE, SCOPE = "HAB-005", "HAB-004"
CHECKS = {
    "schema": EVIDENCE,
    "table_row": EVIDENCE,
    "allowed_action": SCOPE,
    "fresh_green_to_advance": EVIDENCE,
    "concurrency_down_within_ceiling": SCOPE,
    "rung_on_ladder_at_boundary": SCOPE,
    "retry_within_attempt_limit": SCOPE,
    "capability_unchanged": SCOPE,
    "loop_a_chain": EVIDENCE,
    "re_evaluated_after_remediation": EVIDENCE,
    "no_oscillation": SCOPE,
    "record_schema": EVIDENCE,
    "standing_from_attributed_evidence": EVIDENCE,
    "attribution_chain": EVIDENCE,
    "no_transient_promotion": EVIDENCE,
    "loop_b_link": EVIDENCE,
    "action_gate_available": SCOPE,
}


def eep_rules(check):
    return sorted({"CAPA-001", "CAPA-003", CHECKS[check]})


def _t(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


# ---------------------------------------------------------------- reliability states (§5)

def service_state(sources, now):
    """The state of one service or harness from its burn-rate alert fixtures, one per source.

    A source is {has_slos, pairs: [{severity, evaluated_at, firing}], budget_spent, saturation_firing,
    open_incidents}. Sources that disagree make the state UNKNOWN; so does no source at all.
    """
    states = {_one_source(s, _t(now)) for s in sources}
    return states.pop() if len(states) == 1 else "UNKNOWN"


def _one_source(src, now):
    pairs = src.get("pairs", [])
    if (any(p["firing"] for p in pairs) or src.get("budget_spent") or src.get("saturation_firing")
            or src.get("open_incidents", 0) > 0):
        return "RED"
    fresh = all(timedelta(0) <= now - _t(p["evaluated_at"]) <= SHORT_WINDOW[p["severity"]] for p in pairs)
    return "GREEN" if src.get("has_slos") and pairs and fresh else "UNKNOWN"


def effective_states(decision):
    """Each subject's state as the checker trusts it. A GREEN with no SLOs, evaluated outside the page
    window before recorded_at (or after it), or contradicted by another entry, is UNKNOWN."""
    at = _t(decision["recorded_at"])
    by_subject = {}
    for r in decision["inputs"]["reliability"]:
        state = r["state"]
        if state == "GREEN":
            age = at - _t(r["evaluated_at"])
            if not r.get("slo_ids") or not timedelta(0) <= age <= GREEN_FRESH:
                state = "UNKNOWN"
        by_subject.setdefault((r["subject_kind"], r["subject"]), set()).add(state)
    return {k: (v.pop() if len(v) == 1 else "UNKNOWN") for k, v in by_subject.items()}


def practice_standing(record, ctx):
    """§5 practice standing, counting only attributions whose chain resolves (§5 causal attribution)."""
    if date.fromisoformat(record["review_by"]) < date.fromisoformat(ctx["today"]):
        return "UNKNOWN"
    if any(not a["superseded_by_fix"] for a in record["attributions"] if chain_resolves(a, record, ctx)):
        return "RED"
    if record["evidence_tier"] == "VERIFIED" and record["outcomes"]["verified"] >= 1:
        return "GREEN"
    return "UNKNOWN"


def chain_resolves(attribution, record, ctx):
    """A harness decision cited the record, that decision led to the change, a defect record names it."""
    d = ctx.get("decisions", {}).get(attribution["decision_id"])
    return bool(d and record["record_id"] in d.get("cited", []) and d.get("change") == attribution["change"]
                and ctx.get("defects", {}).get(attribution["defect_record"]) == attribution["change"])


# ---------------------------------------------------------------- the decision table (§6-7)

def quality(decision, ctx):
    """The Policy Engine decision as trusted: MISSING unless its digest verifies against the document."""
    q = decision["inputs"]["quality"]
    if q["decision"] == "MISSING" or set(q.get("rules", [])) & EVIDENCE_FINDINGS:
        return "MISSING"
    if q.get("policy_decision_sha256") is None or q["policy_decision_sha256"] != ctx.get("policy_document_sha256"):
        return "MISSING"
    return q["decision"]


def row(decision, ctx):
    """The first row of §7 that applies, or 0 when none does."""
    g, q = decision["inputs"]["governance"], decision["inputs"]["quality"]
    states = effective_states(decision)
    rules = set(q.get("rules", []))
    high_crap = bool(rules & HIGH_CRAP)
    surviving = q.get("survivors_on_changed_lines", 0) > 0 or bool(rules & SURVIVING)
    service_red = any(s == "RED" for (k, _), s in states.items() if k == "service")
    harness_red = any(s == "RED" for (k, _), s in states.items() if k == "harness")
    unknown = not states or any(s == "UNKNOWN" for s in states.values())
    verdict = quality(decision, ctx)
    conditions = [
        (1, g["budget_spent_fraction"] >= 1),
        (2, verdict == "QUARANTINE"),
        (3, verdict == "MISSING"),
        (4, verdict == "BLOCK" and (service_red or harness_red)),
        (5, verdict == "BLOCK" and high_crap and surviving),
        (6, verdict == "BLOCK" and high_crap),
        (7, verdict == "BLOCK"),
        (8, verdict == "PASS" and service_red),
        (9, verdict == "PASS" and harness_red),
        (10, verdict == "PASS" and unknown),
        (11, verdict == "PASS" and surviving and not high_crap),
        (12, verdict == "PASS" and not high_crap and all(s == "GREEN" for s in states.values())),
    ]
    return next((n for n, applies in conditions if applies), 0)


def allowed(n):
    return ROWS[n] | (WITHIN_ROW if n >= 4 else frozenset())


# ---------------------------------------------------------------- checks

def check_decision(decision, ctx, disabled=frozenset()):
    """Every violation of the standard by one harness_decision.v1, as (check, message) pairs."""
    out = []

    def fail(check, message):
        if check not in disabled:
            out.append((check, message))

    errors = sorted(VALIDATE["harness_decision.v1"].iter_errors(decision), key=lambda e: list(e.path))
    for e in errors:
        fail("schema", f"{'/'.join(map(str, e.path)) or '$'}: {e.message}")
    if errors:
        return out
    a, g = decision["action"], decision["inputs"]["governance"]
    n = row(decision, ctx)
    if n and a["table_row"] != n:
        fail("table_row", f"row {a['table_row']} recorded, row {n} applies")
    if a["kind"] not in allowed(n):
        fail("allowed_action", f"{a['kind']} is not allowed by row {n}")
    if a["kind"] == "advance":
        states = effective_states(decision)
        if not states or any(s != "GREEN" for s in states.values()) or quality(decision, ctx) != "PASS":
            fail("fresh_green_to_advance", "advance without a verified PASS and a fresh GREEN for every subject")
    if a["kind"] == "reduce_concurrency":
        ceiling = ctx.get("concurrency_ceiling")
        try:
            frm, to = int(a["from"]), int(a["to"])
        except (KeyError, ValueError):
            frm = to = None
        if ceiling is None or frm is None or not 1 <= to < frm <= ceiling:
            fail("concurrency_down_within_ceiling",
                 f"concurrency {a.get('from')}->{a.get('to')} is not a decrease within the ceiling {ceiling}")
    if a["kind"] == "change_model_rung":
        rung = next((r for r in LADDER["rungs"] if r["label"] == a["selected"]["rung"]), None)
        if rung is None or rung["modelId"] != a["selected"]["model_id"] or ctx.get("task_boundary") is not True:
            fail("rung_on_ladder_at_boundary", "the rung is not on model_ladder.v1, or not chosen at a task boundary")
    if g["attempt"] > g["max_attempts"] or (a["kind"] == "retry" and g["attempt"] >= g["max_attempts"]):
        fail("retry_within_attempt_limit", f"attempt {g['attempt']} of {g['max_attempts']}")
    prev_boundary = ctx.get("previous_capability_boundary")
    if prev_boundary is not None and g["capability_boundary"] != prev_boundary:
        fail("capability_unchanged", "the capability boundary changed inside a run")
    run = ctx.get("run_decisions", [])
    prev = decision.get("previous")
    if (run and prev is None) or (prev is not None and prev["decision_id"] not in run):
        fail("loop_a_chain", "the decision does not name an earlier decision of its run")
    after = ctx.get("after_remediation")
    if after:
        q = decision["inputs"]["quality"]
        ev = q.get("evaluation", {})
        if (ev.get("commit") != after["commit"] or ev.get("merge_base") != after["merge_base"]
                or q.get("policy_decision_sha256") == after["previous_policy_decision_sha256"]):
            fail("re_evaluated_after_remediation", "not a new evaluation of the remediation against its merge base")
    history = ctx.get("steering", [])
    if "from" in a and "to" in a and any(h == [a["to"], a["from"]] for h in history):
        fail("no_oscillation", f"steering {a['from']}->{a['to']} reverses an earlier step of the run")
    return out


def check_record(record, ctx, disabled=frozenset()):
    """Every violation of the standard by one knowledge_record.v1."""
    out = []

    def fail(check, message):
        if check not in disabled:
            out.append((check, message))

    errors = sorted(VALIDATE["knowledge_record.v1"].iter_errors(record), key=lambda e: list(e.path))
    for e in errors:
        fail("record_schema", f"{'/'.join(map(str, e.path)) or '$'}: {e.message}")
    if errors:
        return out
    for a in record["attributions"]:
        if not chain_resolves(a, record, ctx):
            fail("attribution_chain", f"attribution to {a['change']} has no recorded chain")
    expected = practice_standing(record, ctx)
    if record["standing"] != expected:
        fail("standing_from_attributed_evidence", f"standing {record['standing']}, evidence gives {expected}")
    if ctx.get("source_event") in TRANSIENT:
        fail("no_transient_promotion", f"a {ctx['source_event']} event was promoted to long-term memory")
    known = ctx.get("decisions", {})
    if any(d not in known for d in record.get("derived_from", [])):
        fail("loop_b_link", "derived_from names a decision that is not a sealed record")
    return out


# ---------------------------------------------------------------- retrieval (§4)

def retrieve(records, query, ctx):
    """Eligible records in §4 order, each with its label. Lexicographic; no numeric weight."""
    out = []
    for r in records:
        fit = _applicability(r["subject"], query)
        verifies = ctx.get("source_digests", {}).get(r["record_id"]) == r["source"]["sha256"]
        if fit is None or r["status"] != "active" or not verifies:
            continue
        standing = practice_standing(r, ctx)
        out.append((
            _precedence(r), {"GREEN": 0, "UNKNOWN": 1, "RED": 2}[standing], fit, -r["outcomes"]["verified"],
            -_t(r["recorded_at"]).timestamp(), r["record_id"],
            {"record_id": r["record_id"], "label": LABEL[standing]},
        ))
    return [entry[-1] for entry in sorted(out, key=lambda e: e[:-1])]


LABEL = {"GREEN": "guidance", "UNKNOWN": "unproven", "RED": "caution"}


def _precedence(r):
    # 07 §7: playbook rules (an approved practice), a person's decision, VERIFIED and OBSERVED, claims.
    if r["kind"] == "practice" and r.get("approved_in"):
        return 0
    if r["kind"] == "decision":
        return 1
    return 2 if r["evidence_tier"] in ("VERIFIED", "OBSERVED") else 3


def _applicability(subject, query):
    """0 exact rule or fingerprint, 1 component, 2 repository, 3 language; None when nothing applies."""
    if set(subject.get("rules", [])) & set(query.get("rules", [])) or (
            subject.get("fingerprint") and subject.get("fingerprint") == query.get("fingerprint")):
        return 0
    for rank, key in ((1, "component"), (2, "repo"), (3, "language")):
        if subject.get(key) and subject.get(key) == query.get(key):
            return rank
    return None


def render_retrieved(records):
    """Retrieved records as delimited data (§3): summaries are JSON strings inside one data block, so no
    summary can close the block or read as an instruction."""
    lines = ["<retrieved_records>"]
    for r in records:
        lines.append(json.dumps({"record_id": r["record_id"], "tier": r["evidence_tier"], "summary": r["summary"]},
                                ensure_ascii=True).replace("<", "\\u003c").replace(">", "\\u003e"))
    lines.append("</retrieved_records>")
    return "\n".join(lines)


# ---------------------------------------------------------------- the harness boundary (KAN-47, 2026-11-16)

def inbound(text, rotor):
    """Rotor at the inbound boundary. Until a stage is promoted the input passes unchanged; when Rotor is
    down it still passes unchanged, with a visible warning."""
    if rotor == "pass_through":
        return {"text": text, "warning": None}
    if rotor == "down":
        return {"text": text, "warning": "rotor unavailable: input passed in its original order"}
    raise ValueError(f"unknown rotor state {rotor!r}")


def action_gate(decision, ctx, gate="up", disabled=frozenset()):
    """The outbound EEP action gate. Deterministic; fails closed when unavailable or undecided."""
    if gate != "up" and "action_gate_available" not in disabled:
        return False, [("action_gate_available", f"gate {gate}: deny")]
    try:
        violations = check_decision(decision, ctx, disabled)
    except Exception as exc:  # noqa: BLE001 - undecided is a deny, never an allow
        if "action_gate_available" in disabled:
            return True, []
        return False, [("action_gate_available", f"gate could not decide: {type(exc).__name__}")]
    return not violations, violations


# ---------------------------------------------------------------- emission (ddi.event.v1, ddi.capa_draft.v1)

def emit(check, message, subject, run_id, t, now):
    """One error event and one CAPA draft for a violation. The draft's fingerprint is the check plus the
    subject, so a recurrence updates the same draft (CAPA-002)."""
    rules = eep_rules(check)
    name = f"harness.block.{check}"
    event = {"schema": "ddi.event.v1", "run_id": run_id, "kind": "error", "name": name, "t": t,
             "check": check, "eep_rules": rules, "subject": subject, "message": message}
    draft = {
        "schema": "ddi.capa_draft.v1",
        "fingerprint": hashlib.sha256(f"{check}|{subject}".encode()).hexdigest()[:16],
        "kind": "capa", "source": "harness_reference", "subject": subject,
        "status": "draft", "trust": "unverified_claim", "ci_provenance": None,
        "occurrences": 1, "first_seen": now, "last_seen": now, "runs": [run_id],
        "domain_context": "adaptive harness, 06_AgentZone/09_Adaptive_Harness.md",
        "event": name, "conflicting_paths": None, "assumptions": None, "root_cause": None,
        "invariant_check": {"check": check, "eep_rules": rules, "message": message},
        "correction": None, "preventive_action": None,
        "verification": "none: a draft is a claim until CI-signed results back it (CAPA-003)",
        "caveats": ["emitted by the reference checker; promotion past BLOCK needs a new PASS"],
        "sync_notes": None,
    }
    return event, draft
