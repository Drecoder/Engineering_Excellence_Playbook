"""
Tests for the cyclic tri-pass reference ordering (context_order_reference.py). The guarantees are
checked for every chunk count up to 300, with equal, random and skewed weights, with and without
pinned chunks, so they hold by test, not by example.

    python -m unittest tests/contracts/test_context_order.py -v
"""

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from context_order_reference import (  # noqa: E402
    FIRST, LAST, MIDDLE, focus_groups, pass_orders, route, segments, slot_of, windows,
)

RNG = random.Random(20261116)
N_MAX = 300


def weight_sets(n):
    yield [1] * n
    yield [RNG.randint(1, 500) for _ in range(n)]
    if n:
        skewed = [1] * n
        skewed[RNG.randrange(n)] = 10_000  # one huge chunk
        yield skewed


def pinned_sets(n):
    yield frozenset()
    if n:
        yield frozenset({0})
        yield frozenset(RNG.sample(range(n), min(n, 3)))


def cases():
    for n in range(N_MAX + 1):
        for w in weight_sets(n):
            for p in pinned_sets(n):
                yield n, w, p


class Segments(unittest.TestCase):
    def test_contiguous_non_empty_and_complete(self):
        for n in range(N_MAX + 1):
            for w in weight_sets(n):
                segs = segments(w)
                self.assertEqual([i for s in segs for i in s], list(range(n)), n)
                self.assertTrue(all(segs), n)
                self.assertEqual(len(segs), 3 if n >= 3 else n, n)

    def test_near_equal_weight_when_chunks_are_equal(self):
        for n in range(3, N_MAX + 1):
            sizes = [len(s) for s in segments([1] * n)]
            self.assertLessEqual(max(sizes) - min(sizes), 1, (n, sizes))

    def test_vectors(self):
        """Exact plans, so every implementation cuts and rotates the same way."""
        # a tie (boundaries at weight 1 and 3, target 2) cuts at the earlier boundary
        self.assertEqual(segments([1, 2, 1, 2]), [[0], [1, 2], [3]])
        self.assertEqual(segments([5, 1, 1, 1, 1, 5]), [[0], [1, 2, 3, 4], [5]])
        self.assertEqual(pass_orders([1] * 7, frozenset({0})),
                         [[0, 1, 2, 3, 4, 5, 6], [0, 3, 4, 5, 6, 1, 2], [0, 5, 6, 1, 2, 3, 4]])

    def test_bad_weights_are_refused(self):
        for bad in ([0], [-1], [1.5], [True], ["3"]):
            with self.assertRaises(ValueError, msg=bad):
                segments(bad)


class Passes(unittest.TestCase):
    def test_pass_1_is_true_order(self):
        for n, w, p in cases():
            first = pass_orders(w, p)[0]
            self.assertEqual(first, sorted(p) + [i for i in range(n) if i not in p], (n, p))

    def test_every_pass_reads_every_chunk_once(self):
        for n, w, p in cases():
            for order in pass_orders(w, p):
                self.assertEqual(sorted(order), list(range(n)), (n, p))

    def test_pass_count_and_no_repeated_pass(self):
        for n, w, p in cases():
            passes = pass_orders(w, p)
            rotating = n - len(p)
            self.assertEqual(len(passes), max(1, min(3, rotating)), (n, p))
            self.assertEqual(len({tuple(o) for o in passes}), len(passes), (n, p))

    def test_pinned_chunks_lead_every_pass(self):
        for n, w, p in cases():
            for order in pass_orders(w, p):
                self.assertEqual(order[: len(p)], sorted(p), (n, p))

    def test_rotated_passes_have_at_most_one_seam(self):
        # a seam is a step that goes backwards in true order, outside the pinned head
        for n, w, p in cases():
            for order in pass_orders(w, p)[1:]:
                body = order[len(p):]
                seams = sum(1 for a, b in zip(body, body[1:]) if b < a)
                self.assertLessEqual(seams, 1, (n, p, order))


class SlotGuarantee(unittest.TestCase):
    def test_three_or_more_chunks_each_slot_exactly_once(self):
        for n, w, p in cases():
            if n - len(p) < 3:
                continue
            for chunk, slots in slot_of(w, p).items():
                self.assertEqual(sorted(slots), sorted([FIRST, MIDDLE, LAST]), (n, p, chunk))

    def test_never_in_the_middle_twice(self):
        for n, w, p in cases():
            for chunk, slots in slot_of(w, p).items():
                self.assertLessEqual(slots.count(MIDDLE), 1, (n, p, chunk))

    def test_two_chunks_are_first_once_and_last_once(self):
        for w in ([1, 1], [7, 900]):
            self.assertEqual(slot_of(w), {0: [FIRST, LAST], 1: [LAST, FIRST]})

    def test_plain_rotations_cannot_give_the_guarantee(self):
        """Why segments, not chunks, are rotated: for N = 4 no choice of three distinct shifts of
        the chunk list puts chunk 0 in each third of the read (by position) exactly once."""
        n = 4
        third = lambda pos: (3 * pos) // n  # noqa: E731
        for s1 in range(1, n):
            for s2 in range(1, n):
                if s1 == s2:
                    continue
                ok = all(sorted(third((i - s) % n) for s in (0, s1, s2)) == [0, 1, 2] for i in range(n))
                self.assertFalse(ok, (s1, s2))


class Determinism(unittest.TestCase):
    def test_same_input_same_plan(self):
        w = [RNG.randint(1, 300) for _ in range(57)]
        p = frozenset({0, 3})
        self.assertEqual(pass_orders(w, p), pass_orders(list(w), frozenset(p)))

    def test_a_pinned_index_must_be_a_chunk(self):
        with self.assertRaises(ValueError):
            pass_orders([1, 1, 1], frozenset({3}))


BUDGETS = ((1, 0), (1, 1), (50, 0), (300, 150), (800, 400), (10_000, 10_000))


class EndFocusedWindows(unittest.TestCase):
    """Arm E: every rotating chunk is in the focus slot (the end of a window) exactly once."""

    def test_focus_groups_partition_the_chunks_in_true_order(self):
        for n in range(N_MAX + 1):
            for w in weight_sets(n):
                for fb, _ in BUDGETS:
                    groups = focus_groups(w, fb)
                    self.assertEqual([i for g in groups for i in g], list(range(n)), (n, fb))
                    self.assertTrue(all(groups), (n, fb))

    def test_a_group_fits_its_budget_unless_it_is_one_heavy_chunk(self):
        for n in range(1, N_MAX + 1):
            for w in weight_sets(n):
                for fb, _ in BUDGETS:
                    for g in focus_groups(w, fb):
                        if len(g) > 1:
                            self.assertLessEqual(sum(w[i] for i in g), fb, (n, fb, g))

    def test_groups_are_greedy_so_no_two_neighbours_could_merge(self):
        for n in range(2, N_MAX + 1):
            for w in weight_sets(n):
                for fb, _ in BUDGETS:
                    groups = focus_groups(w, fb)
                    for a, b in zip(groups, groups[1:]):
                        self.assertGreater(sum(w[i] for i in a) + w[b[0]], fb, (n, fb))

    def test_every_rotating_chunk_is_in_focus_exactly_once(self):
        for n, w, p in cases():
            for fb, cb in BUDGETS:
                focused = [i for win in windows(w, p, fb, cb) for i in win["focus"]]
                self.assertEqual(sorted(focused), [i for i in range(n) if i not in p], (n, p, fb))

    def test_focus_is_last_and_windows_are_in_true_order(self):
        for n, w, p in cases():
            for fb, cb in BUDGETS:
                wins = windows(w, p, fb, cb)
                for win in wins:
                    order = win["head"] + win["context"] + win["focus"]
                    if win["focus"]:
                        self.assertEqual(order[-len(win["focus"]):], win["focus"], (n, p))
                    body = win["context"] + win["focus"]
                    self.assertEqual(body, sorted(body), (n, p))  # no seam inside a window
                firsts = [win["focus"][0] for win in wins if win["focus"]]
                self.assertEqual(firsts, sorted(firsts), (n, p))

    def test_pinned_chunks_lead_every_window_and_never_rotate(self):
        for n, w, p in cases():
            for fb, cb in BUDGETS:
                for win in windows(w, p, fb, cb):
                    self.assertEqual(win["head"], sorted(p), (n, p))
                    self.assertFalse(set(win["context"] + win["focus"]) & p, (n, p))

    def test_context_is_the_whole_chunks_just_before_focus_within_budget(self):
        for n, w, p in cases():
            rotating = [i for i in range(n) if i not in p]
            pos = {c: k for k, c in enumerate(rotating)}
            for fb, cb in BUDGETS:
                for win in windows(w, p, fb, cb):
                    if not win["focus"]:
                        continue
                    ctx, start = win["context"], pos[win["focus"][0]]
                    self.assertLessEqual(sum(w[i] for i in ctx), cb, (n, p, cb))
                    self.assertEqual([pos[c] for c in ctx], list(range(start - len(ctx), start)), (n, p))
                    before = start - len(ctx) - 1  # the next chunk back must not have fit
                    if before >= 0:
                        self.assertGreater(sum(w[i] for i in ctx) + w[rotating[before]], cb, (n, p, cb))

    def test_a_defect_across_a_group_boundary_is_read_whole_once(self):
        # with context of at least one chunk, the last chunk of group i sits in group i+1's window
        w = [10] * 12
        wins = windows(w, frozenset(), 30, 10)
        for a, b in zip(wins, wins[1:]):
            self.assertIn(a["focus"][-1], b["context"])
            self.assertIn(b["focus"][0], b["focus"])

    def test_vectors(self):
        self.assertEqual(focus_groups([3, 3, 3, 9, 1], 6), [[0, 1], [2], [3], [4]])
        self.assertEqual(windows([1, 4, 4, 4, 4], frozenset({0}), 8, 4),
                         [{"head": [0], "context": [], "focus": [1, 2]},
                          {"head": [0], "context": [2], "focus": [3, 4]}])
        self.assertEqual(windows([], frozenset(), 5, 5), [{"head": [], "context": [], "focus": []}])

    def test_bad_budgets_are_refused(self):
        for fb, cb in ((0, 0), (-1, 0), (1.5, 0), (True, 0), (5, -1), (5, 1.5), (5, True)):
            with self.assertRaises(ValueError, msg=(fb, cb)):
                windows([1, 1, 1], frozenset(), fb, cb)


class SizeRouting(unittest.TestCase):
    """Arm F: route by total rotating tokens; a length on a threshold takes the shorter band."""

    def test_bands_and_boundaries(self):
        for long_arm in ("D", "E"):
            self.assertEqual(route(0, 100, 1000, long_arm), "A")
            self.assertEqual(route(100, 100, 1000, long_arm), "A")
            self.assertEqual(route(101, 100, 1000, long_arm), "C")
            self.assertEqual(route(1000, 100, 1000, long_arm), "C")
            self.assertEqual(route(1001, 100, 1000, long_arm), long_arm)

    def test_route_is_monotone_in_length(self):
        rank = {"A": 0, "C": 1, "D": 2, "E": 2}
        for long_arm in ("D", "E"):
            arms = [route(L, 40, 90, long_arm) for L in range(0, 200)]
            self.assertEqual([rank[a] for a in arms], sorted(rank[a] for a in arms))

    def test_a_malformed_length_fails_closed_to_the_long_arm(self):
        for bad in (None, -1, 1.5, "500", True):
            self.assertEqual(route(bad, 100, 1000, "E"), "E", bad)
            self.assertEqual(route(bad, 100, 1000, "D"), "D", bad)

    def test_bad_thresholds_or_long_arm_are_refused(self):
        for t_short, t_long, arm in ((0, 10, "D"), (10, 10, "D"), (20, 10, "D"), (1.5, 10, "D"),
                                     (True, 10, "D"), (1, 10, "A"), (1, 10, "C"), (1, 10, "X")):
            with self.assertRaises(ValueError, msg=(t_short, t_long, arm)):
                route(50, t_short, t_long, arm)


if __name__ == "__main__":
    unittest.main()
