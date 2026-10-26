"""
Reference behavior for the CI engine's checks that a schema cannot express (15_Central_CI.md §9).

Any engine implementation must agree with these functions on the same inputs; the contract tests
pin that agreement. This is a specification aid, not the engine.
"""

import hashlib
import json
from datetime import date


def canonical_sha256(doc) -> str:
    """SHA-256 of canonical JSON: keys sorted at every level, no whitespace, ASCII escapes."""
    text = json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def evaluate_exceptions(policy: dict, exceptions: dict, today: date) -> dict:
    """Split a caller's exceptions into applied and rejected, as gate_plan.v1 records them.

    Applied entries still match only their exact finding and resource when scan results arrive;
    this step decides which entries are eligible at all.
    """
    checks = {c["id"]: c for c in policy["checks"]}
    allowed = set(policy["exceptions"]["allowed_categories"])
    max_days = policy["exceptions"]["max_days"]
    applied, rejected = [], []
    for e in exceptions["exceptions"]:
        check = checks.get(e["check"])
        created, expires = date.fromisoformat(e["created"]), date.fromisoformat(e["expires"])
        if check is None:
            reason = "unknown_check"
        elif not check["exceptions_allowed"] or check["category"] not in allowed:
            reason = "check_not_exceptable"
        elif expires <= created or (expires - created).days > max_days:
            reason = "over_max_days"
        elif expires < today:
            reason = "expired"
        else:
            applied.append({k: e[k] for k in ("id", "check", "finding_id", "resource", "expires")})
            continue
        rejected.append({"id": e["id"], "reason": reason})
    return {"applied": applied, "rejected": rejected}


def finding_is_excepted(applied: list, check_id: str, finding_id: str, resource: str) -> bool:
    """An applied exception covers only its exact check, finding, and resource."""
    return any(a["check"] == check_id and a["finding_id"] == finding_id and a["resource"] == resource for a in applied)


def plan_is_trusted(plan, head_sha: str, factory_commit: str) -> bool:
    """A gate plan counts only if the factory wrote it for this exact head; anything else fails closed."""
    return (
        isinstance(plan, dict)
        and plan.get("schema_version") == "gate_plan.v1"
        and plan.get("commit") == head_sha
        and plan.get("factory_commit") == factory_commit
    )
