"""
Append-only check for the proof journal (docs/POC_JOURNAL.md).

An entry is a section that starts with a heading `## YYYY-MM-DD: <title>` and runs to the next
such heading or the end of the file. Between the base and the head of a change:

- every base entry must still be there, byte for byte (trailing whitespace aside), in the same
  order, as the first entries of the head;
- new entries may only follow them, at the end;
- the preamble (everything before the first entry) may change: it documents the format.

This holds for changes that go through pull requests. It does not make the file immutable: anyone
who can bypass branch protection or change this check can still rewrite history. That guarantee
waits for the notepad's hash-chained, sealed records (06_AgentZone/07_Agent_Notepad.md).

    python tests/journal/journal_append_only.py BASE_FILE HEAD_FILE

Exits 0 when the change is append-only, 1 with one line per violation otherwise. A missing base
file (the journal is new) passes; a missing head file (the journal was deleted) fails.
"""

import re
import sys
from pathlib import Path

ENTRY_HEADING = re.compile(r"^## \d{4}-\d{2}-\d{2}: .+$", re.MULTILINE)


def entries(text: str) -> list[tuple[str, str]]:
    """(heading, body) for each entry, in file order; body has trailing whitespace stripped."""
    starts = [m.start() for m in ENTRY_HEADING.finditer(text)]
    out = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(text)
        block = text[start:end].rstrip()
        heading = block.splitlines()[0]
        out.append((heading, block))
    return out


def violations(base: str | None, head: str | None) -> list[str]:
    if base is None:
        return []
    if head is None:
        return ["the journal was deleted"]
    old, new = entries(base), entries(head)
    problems = []
    new_headings = [h for h, _ in new]
    for i, (heading, block) in enumerate(old):
        if i < len(new) and new[i] == (heading, block):
            continue
        if heading not in new_headings:
            problems.append(f"entry deleted: {heading}")
        elif i >= len(new) or new[i][0] != heading:
            problems.append(f"entry moved, or a new entry inserted before it: {heading}")
        else:
            problems.append(f"entry edited: {heading}")
    return problems


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__.strip().splitlines()[0])
        print("usage: journal_append_only.py BASE_FILE HEAD_FILE", file=sys.stderr)
        return 2
    base_path, head_path = Path(argv[1]), Path(argv[2])
    base = base_path.read_text(encoding="utf-8") if base_path.is_file() else None
    head = head_path.read_text(encoding="utf-8") if head_path.is_file() else None
    problems = violations(base, head)
    added = len(entries(head or "")) - len(entries(base or ""))
    if problems:
        for p in problems:
            print(f"::error::journal is append-only: {p}")
        return 1
    print(f"journal append-only: ok ({len(entries(base or ''))} entries kept, {max(added, 0)} added)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
