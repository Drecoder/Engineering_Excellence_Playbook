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
from context_order_reference import FIRST, LAST, MIDDLE, pass_orders, segments, slot_of  # noqa: E402

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


if __name__ == "__main__":
    unittest.main()
