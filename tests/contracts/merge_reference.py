"""
Reference behavior for merge conflicts (06_AgentZone/06_Merge_Conflicts.md): how rig classifies and
routes a hunk, how a rule resolves one, and how the merge-resolution lens finds dropped lines.

Any implementation must agree with these functions on the contract tests' vectors. This is a
specification aid, not rig or the Builder.
"""


def classify(base: list[str], ours: list[str], theirs: list[str], binary: bool = False) -> tuple[str, str]:
    """(class, reason) for one hunk. Mechanical only when provably disjoint additions; else semantic."""
    if binary:
        return "semantic", "binary"
    if not base and ours and theirs:
        if set(ours) & set(theirs):
            return "semantic", "same_lines_changed"  # both added a line with the same text: a collision
        return "mechanical", "disjoint_additions"
    if base and (not ours or not theirs):
        return "semantic", "delete_vs_change"
    if base:
        return "semantic", "same_lines_changed"
    return "semantic", "unclassified"


def route(hunk_class: str, reason: str, protected: bool, budget_exhausted: bool = False) -> str:
    """Who resolves the hunk. Protected files, binary conflicts, and an exhausted budget go to a person."""
    if protected or reason == "binary" or budget_exhausted:
        return "person"
    return "rule" if hunk_class == "mechanical" else "model"


def resolve_by_rule(ours: list[str], theirs: list[str]) -> list[str]:
    """The rule for disjoint additions: keep both sides, ours (the pull request) then theirs."""
    return [*ours, *theirs]


def dropped_lines(ours: list[str], theirs: list[str], resolved: list[str], removed_on_purpose: set[str] = frozenset()) -> list[str]:
    """Lines either side added that are absent from the resolution and not declared as removed."""
    present = set(resolved)
    return [line for line in [*ours, *theirs] if line not in present and line not in removed_on_purpose]
