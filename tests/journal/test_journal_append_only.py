"""
Tests for the proof journal's append-only check. Each forbidden change has a fixture that must
fail, and each allowed change one that must pass; the real journal is checked against itself.

    python -m unittest discover -s tests/journal -v
"""

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from journal_append_only import entries, main, violations  # noqa: E402

FIXTURES = HERE / "fixtures"
JOURNAL = HERE.parents[1] / "docs" / "POC_JOURNAL.md"


def read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class AllowedChanges(unittest.TestCase):
    def test_new_entry_at_the_end(self):
        self.assertEqual(violations(read("base.txt"), read("append_ok.txt")), [])

    def test_a_late_found_entry_still_goes_at_the_end(self):
        self.assertEqual(violations(read("base.txt"), read("late_dated_append_ok.txt")), [])

    def test_the_preamble_may_change(self):
        self.assertEqual(violations(read("base.txt"), read("preamble_changed_ok.txt")), [])

    def test_trailing_whitespace_is_not_an_edit(self):
        self.assertEqual(violations(read("base.txt"), read("trailing_whitespace_ok.txt")), [])

    def test_a_new_journal_passes(self):
        self.assertEqual(violations(None, read("base.txt")), [])


class ForbiddenChanges(unittest.TestCase):
    def assert_fails_with(self, fixture: str, expected: str):
        problems = violations(read("base.txt"), read(fixture))
        self.assertTrue(problems, f"{fixture} should be refused")
        self.assertTrue(any(expected in p for p in problems), problems)

    def test_editing_an_entry(self):
        self.assert_fails_with("edited.txt", "entry edited: ## 2026-10-29: Second finding")

    def test_renaming_an_entry(self):
        self.assert_fails_with("heading_edited.txt", "entry deleted: ## 2026-10-29: Second finding")

    def test_deleting_an_entry(self):
        self.assert_fails_with("deleted.txt", "entry deleted: ## 2026-10-28: First finding")

    def test_reordering_entries(self):
        self.assert_fails_with("reordered.txt", "entry moved")

    def test_inserting_before_an_existing_entry(self):
        self.assert_fails_with("inserted_middle.txt", "entry moved")

    def test_deleting_the_journal(self):
        self.assertEqual(violations(read("base.txt"), None), ["the journal was deleted"])


class TheRealJournal(unittest.TestCase):
    def test_it_has_entries_the_check_can_see(self):
        self.assertGreater(len(entries(JOURNAL.read_text(encoding="utf-8"))), 0)

    def test_it_is_append_only_against_itself(self):
        text = JOURNAL.read_text(encoding="utf-8")
        self.assertEqual(violations(text, text), [])

    def test_the_command_line_exits_1_on_a_violation(self):
        self.assertEqual(main(["x", str(FIXTURES / "base.txt"), str(FIXTURES / "edited.txt")]), 1)
        self.assertEqual(main(["x", str(FIXTURES / "base.txt"), str(FIXTURES / "append_ok.txt")]), 0)


if __name__ == "__main__":
    unittest.main()
