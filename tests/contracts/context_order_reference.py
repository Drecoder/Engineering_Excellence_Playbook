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
