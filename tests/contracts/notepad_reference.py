"""
Reference behavior for notepad_channels.v1 that a schema cannot express (07_Agent_Notepad.md §3).

The notepad service and the central CI check must agree with these functions on
schemas/examples/notepad/channel_vectors.json. This is a specification aid, not the service.
"""

import re

_SEGMENT = r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}"


def pattern_regex(pattern: str) -> "re.Pattern[str]":
    """A declared pattern as a full-match regex: * is exactly one name segment, everything else literal."""
    head, _, ext = pattern.rpartition(".")
    return re.compile("".join(_SEGMENT if part == "*" else re.escape(part) for part in re.split(r"(\*)", head)) + re.escape("." + ext))


def declarations(channels: dict) -> list:
    """(channel, file declaration) pairs, in declaration order."""
    return [(c["channel"], f) for c in channels["channels"] for f in c["files"]]


def overlaps(channels: dict) -> list:
    """Declared patterns that could both match one path: a defect, rejected at load."""
    pats = [f["pattern"] for _, f in declarations(channels)]
    found = []
    for i, a in enumerate(pats):
        for b in pats[i + 1:]:
            probe_a, probe_b = a.replace("*", "x0"), b.replace("*", "x0")
            if a == b or pattern_regex(a).fullmatch(probe_b) or pattern_regex(b).fullmatch(probe_a):
                found.append((a, b))
    return found


def classify(path: str, channels: dict):
    """The (channel, region) a path belongs to, or None: an undeclared path is rejected."""
    matches = [(c, f["region"]) for c, f in declarations(channels) if pattern_regex(f["pattern"]).fullmatch(path)]
    return matches[0] if len(matches) == 1 else None
