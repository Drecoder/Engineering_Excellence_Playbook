"""
Reference implementation of the spend rule in price_table.v1's description and the
one-budget-per-ticket rule in AGENTS.md → Agent Rules. It exists to prove the vectors in
schemas/examples/budget/spend_vectors.json against the written rule; consumers implement the same
rule in their own language and run the same vectors.
"""

FLAG_PERCENT = 80


class Unpriced(Exception):
    """A call whose provider and model_id have no row in the price table."""


def duplicate_rows(table):
    seen, dups = set(), []
    for row in table["prices"]:
        key = (row["provider"], row["model_id"])
        if key in seen:
            dups.append(key)
        seen.add(key)
    return dups


def price_call(table, call):
    rows = [r for r in table["prices"] if r["provider"] == call["provider"] and r["model_id"] == call["model_id"]]
    if len(rows) != 1:
        raise Unpriced((call["provider"], call["model_id"]))
    rates = rows[0]["rates"]
    numerator = (
        call["prompt_tokens"] * rates["prompt"]
        + call["cached_tokens"] * rates["cached"]
        + call["completion_tokens"] * rates["completion"]
    )
    return -(-numerator // 1_000_000)  # ceiling division, integers only


def ticket_spend(table, ticket_key, records):
    seen, total = set(), 0
    for r in records:
        if r["ticket_key"] != ticket_key:
            continue
        key = (r["run_id"], r["call_id"])
        if key in seen:
            continue
        seen.add(key)
        total += price_call(table, r)
    return total


def budget_state(limit, spent):
    if spent >= limit:
        return "exhausted"
    if spent * 100 >= limit * FLAG_PERCENT:
        return "flagged"
    return "ok"
