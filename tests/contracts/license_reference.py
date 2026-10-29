"""
Reference behavior for license_policy.v1 that a schema cannot express (13_Supply_Chain.md §4).

Every consumer (the central gates, the release pipeline) must agree with these functions on
schemas/examples/license/license_vectors.json. This is a specification aid, not the gate.
"""

import re
from datetime import date

RANK = {"allowed": 0, "review_required": 1, "unknown": 2, "denied": 3}
_TOKEN = re.compile(r"\(|\)|[A-Za-z0-9][A-Za-z0-9.+:-]*")


def classify_id(license_id: str, policy: dict) -> str:
    for verdict in ("denied", "review_required", "allowed"):
        if license_id in policy[verdict]:
            return verdict
    return "unknown"


def classify_expression(expression: str, policy: dict) -> str:
    """OR takes the best term, AND the worst; WITH is judged by its base license; anything unparsable is unknown."""
    tokens = _TOKEN.findall(expression or "")
    if not tokens or "".join(tokens) != re.sub(r"\s+", "", expression):
        return "unknown"
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def take():
        nonlocal pos
        pos += 1
        return tokens[pos - 1]

    def term():
        tok = take() if peek() is not None else None
        if tok == "(":
            verdict = disjunction()
            if take() != ")":
                raise ValueError("unbalanced")
            return verdict
        if tok is None or tok in (")", "AND", "OR", "WITH"):
            raise ValueError("expected a license")
        if peek() == "WITH":
            take()
            if peek() is None or peek() in ("(", ")", "AND", "OR", "WITH"):
                raise ValueError("expected an exception")
            take()
        return classify_id(tok, policy)

    def conjunction():
        verdict = term()
        while peek() == "AND":
            take()
            verdict = max(verdict, term(), key=RANK.__getitem__)
        return verdict

    def disjunction():
        verdict = conjunction()
        while peek() == "OR":
            take()
            verdict = min(verdict, conjunction(), key=RANK.__getitem__)
        return verdict

    try:
        verdict = disjunction()
    except (ValueError, IndexError):
        return "unknown"
    return verdict if pos == len(tokens) else "unknown"


def classify_package(package: dict, policy: dict, today: date) -> str:
    """A package's declared licenses all apply (AND); none declared is unknown; a live exception allows it."""
    for e in policy["exceptions"]:
        if (e["package"], e["version"], e["license"]) == (package["name"], package["version"], " AND ".join(package["licenses"])):
            created, expires = date.fromisoformat(e["created"]), date.fromisoformat(e["expires"])
            if created <= today <= expires and (expires - created).days <= 365:
                return "allowed"
    if not package["licenses"]:
        return "unknown"
    return max((classify_expression(x, policy) for x in package["licenses"]), key=RANK.__getitem__)


def policy_problems(policy: dict) -> list:
    """What a schema cannot catch: a license on more than one list, or an exception living longer than a year."""
    problems = []
    lists = ("allowed", "review_required", "denied")
    for i, a in enumerate(lists):
        for b in lists[i + 1:]:
            for dup in sorted(set(policy[a]) & set(policy[b])):
                problems.append(f"{dup} is on both {a} and {b}")
    for e in policy["exceptions"]:
        if (date.fromisoformat(e["expires"]) - date.fromisoformat(e["created"])).days > 365:
            problems.append(f"{e['id']} lives longer than 365 days")
    return problems
