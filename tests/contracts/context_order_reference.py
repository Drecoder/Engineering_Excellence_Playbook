"""
Reference ordering for cyclic tri-pass reading (06_AgentZone/11_Cyclic_Tri_Pass_Reading.md, PROPOSED).

Chunks are cut on symbol boundaries upstream; this module only orders them. It is pure: no I/O, no
model, the same plan for the same input.

The chunks, in true order, are cut into three contiguous segments S0, S1, S2 of near-equal token
weight. Each pass reads all three segments, each in its true internal order, rotated:

    pass 1:  S0 S1 S2   (true order: identical to a linear read)
    pass 2:  S1 S2 S0   (one seam, between S2 and S0)
    pass 3:  S2 S0 S1   (one seam, between S2 and S0)

So every segment, and every chunk in it, sits in the first slot of exactly one pass, the middle slot
of exactly one pass, and the last slot of exactly one pass. No chunk is in the middle twice.

Pinned chunks (a file's header: imports, exports, interfaces) are not rotated. They come first in
every pass, after the table of contents, so all three passes share one cacheable prefix, and pass 1
shares its whole prompt with a linear read.

Plain rotations of the chunk list cannot give this guarantee when the chunk count is not a multiple
of 3 (tested in test_context_order.py), which is why the segments, not the chunks, are rotated.
"""

from __future__ import annotations

FIRST, MIDDLE, LAST = "first", "middle", "last"
SLOTS = (FIRST, MIDDLE, LAST)


def segments(weights: list[int]) -> list[list[int]]:
    """Cut chunk indices 0..n-1 into contiguous segments of near-equal total weight.

    Returns 3 non-empty segments when n >= 3, otherwise one segment per chunk. Weights are token
    counts and must be positive. Each cut is the chunk boundary nearest to 1/3 and 2/3 of the total,
    moved only as far as needed to keep every segment non-empty.
    """
    n = len(weights)
    if any((not isinstance(w, int)) or isinstance(w, bool) or w <= 0 for w in weights):
        raise ValueError("every chunk weight must be a positive integer token count")
    if n < 3:
        return [[i] for i in range(n)]
    total = sum(weights)
    prefix = [0]
    for w in weights:
        prefix.append(prefix[-1] + w)

    def nearest_cut(target: float, lo: int, hi: int) -> int:
        # cut index c means a segment boundary before chunk c; lo <= c <= hi
        return min(range(lo, hi + 1), key=lambda c: (abs(prefix[c] - target), c))

    c1 = nearest_cut(total / 3, 1, n - 2)
    c2 = nearest_cut(2 * total / 3, c1 + 1, n - 1)
    return [list(range(0, c1)), list(range(c1, c2)), list(range(c2, n))]


def pass_orders(weights: list[int], pinned: frozenset[int] = frozenset()) -> list[list[int]]:
    """The reading order of each pass: pinned chunks first (true order), then rotated segments.

    n >= 3 rotating chunks: 3 passes. 2 rotating chunks: 2 passes (each chunk first once, last once;
    there is no middle). 0 or 1: 1 pass. Passes are never repeated.
    """
    n = len(weights)
    if any(not (0 <= p < n) for p in pinned):
        raise ValueError("a pinned index is not a chunk")
    rotating = [i for i in range(n) if i not in pinned]
    head = sorted(pinned)
    segs = [[rotating[j] for j in seg] for seg in segments([weights[i] for i in rotating])]
    k = len(segs)
    if k == 0:
        return [head]
    passes = []
    for r in range(min(k, 3)):
        order = list(head)
        for s in range(k):
            order.extend(segs[(r + s) % k])
        passes.append(order)
    return passes


def slot_of(weights: list[int], pinned: frozenset[int] = frozenset()) -> dict[int, list[str]]:
    """For each rotating chunk, the slot (first, middle, last) it occupies in each pass."""
    rotating = [i for i in range(len(weights)) if i not in pinned]
    segs = [[rotating[j] for j in seg] for seg in segments([weights[i] for i in rotating])]
    k = len(segs)
    out: dict[int, list[str]] = {}
    for r in range(min(k, 3)):
        for s in range(k):
            slot = FIRST if s == 0 else LAST if s == k - 1 else MIDDLE
            for i in segs[(r + s) % k]:
                out.setdefault(i, []).append(slot)
    return out


# --- Arm E: chunk-aligned, end-focused windows ------------------------------------------------
#
# The rotating chunks, in true order, are tiled into focus groups: contiguous runs of whole chunks
# whose total weight is at most the focus budget (a chunk heavier than the budget is a group on its
# own). Window i reads, in order: the table of contents and the pinned chunks (the shared, cacheable
# prefix), then context (the whole chunks just before focus group i, nearest first, as many as fit
# in the context budget, presented in true order), then focus group i, then the restated task. So
# every rotating chunk is in the focus slot, the end of a window before the restated task, exactly
# once, and a defect that crosses a group boundary is read whole in the later window.


def focus_groups(weights: list[int], focus_budget: int) -> list[list[int]]:
    """Tile chunk indices 0..n-1, in true order, into contiguous groups of total weight at most
    focus_budget. A group closes when the next chunk would overflow it; a chunk heavier than the
    budget is a group of its own."""
    if any((not isinstance(w, int)) or isinstance(w, bool) or w <= 0 for w in weights):
        raise ValueError("every chunk weight must be a positive integer token count")
    if (not isinstance(focus_budget, int)) or isinstance(focus_budget, bool) or focus_budget <= 0:
        raise ValueError("the focus budget must be a positive integer token count")
    groups: list[list[int]] = []
    current: list[int] = []
    used = 0
    for i, w in enumerate(weights):
        if current and used + w > focus_budget:
            groups.append(current)
            current, used = [], 0
        current.append(i)
        used += w
    if current:
        groups.append(current)
    return groups


def windows(weights: list[int], pinned: frozenset[int] = frozenset(), focus_budget: int = 1,
            context_budget: int = 0) -> list[dict[str, list[int]]]:
    """Each window as {"head": pinned chunks, "context": [...], "focus": [...]}, in true order.

    The reading order of a window is head + context + focus, then the restated task. Context is the
    run of whole rotating chunks immediately before the focus group whose total weight fits in
    context_budget, taken nearest first and presented in true order; it stops at the first chunk
    that does not fit, and never includes a pinned chunk.
    """
    n = len(weights)
    if any(not (0 <= p < n) for p in pinned):
        raise ValueError("a pinned index is not a chunk")
    if (not isinstance(context_budget, int)) or isinstance(context_budget, bool) or context_budget < 0:
        raise ValueError("the context budget must be a non-negative integer token count")
    head = sorted(pinned)
    rotating = [i for i in range(n) if i not in pinned]
    groups = focus_groups([weights[i] for i in rotating], focus_budget) if rotating else []
    out = []
    for g in groups:
        start = g[0]  # position in `rotating`
        context: list[int] = []
        used = 0
        j = start - 1
        while j >= 0 and used + weights[rotating[j]] <= context_budget:
            used += weights[rotating[j]]
            context.insert(0, rotating[j])
            j -= 1
        out.append({"head": list(head), "context": context, "focus": [rotating[k] for k in g]})
    if not out:
        out.append({"head": list(head), "context": [], "focus": []})
    return out


# --- Arm F: size-routed hybrid ----------------------------------------------------------------
#
# The arm is chosen from the rotating chunks' total token weight L and the stage's two thresholds
# (open decision D3), fixed in the benchmark policy file before the first run:
#     L <= t_short          -> "A"  single linear read, prefix cached
#     t_short < L <= t_long -> "C"  parallel per-unit map-reduce
#     L > t_long            -> the long arm, "D" (tri-pass) or "E" (end-focused windows)
# A length on a threshold goes to the shorter band. Anything malformed fails closed to the long arm,
# the highest-scrutiny reading (AGENTS.md -> Agent Rules: fail closed).

LONG_ARMS = ("D", "E")


def route(total_tokens, t_short: int, t_long: int, long_arm: str) -> str:
    if long_arm not in LONG_ARMS:
        raise ValueError(f"the long arm must be one of {LONG_ARMS}")
    if (not isinstance(t_short, int)) or isinstance(t_short, bool) or (not isinstance(t_long, int)) \
            or isinstance(t_long, bool) or not (0 < t_short < t_long):
        raise ValueError("thresholds must be integers with 0 < t_short < t_long")
    if (not isinstance(total_tokens, int)) or isinstance(total_tokens, bool) or total_tokens < 0:
        return long_arm  # unknown or malformed length: fail closed
    if total_tokens <= t_short:
        return "A"
    if total_tokens <= t_long:
        return "C"
    return long_arm
