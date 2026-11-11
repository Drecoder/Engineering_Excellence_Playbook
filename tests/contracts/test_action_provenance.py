"""
Provenance of the playbook sync action (action.yml), F-0037.

Inside a composite action, `github.action_ref` and `github.action_repository` name the action that
is running at that point. In the `with:` inputs of a nested `uses:` step they name that nested
action (peter-evans/create-pull-request), not the playbook, so the sync PR recorded the wrong
source. The action captures the playbook's ref in its own `run` step and every later step reads
that output.

The designed-to-fail case is the action as it was before the fix (SYNC_ACTION_BEFORE_F0037): the
check must refuse it. Plain text parsing, so the test needs nothing beyond the standard library.

    python -m unittest discover -s tests/contracts -v
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACTION = ROOT / "action.yml"

CONTEXT = re.compile(r"\$\{\{\s*github\.action_(ref|repository)\s*\}\}")

# The nested step of the action before F-0037 was fixed, kept verbatim as the failing case.
SYNC_ACTION_BEFORE_F0037 = """\
runs:
  using: composite
  steps:
    - name: Vendor rules
      shell: bash
      env:
        PLAYBOOK_REF: ${{ github.action_ref }}
      run: |
        echo vendor
    - name: Open or update sync PR
      id: pr
      uses: peter-evans/create-pull-request@22a9089034f40e5a961c8808d113e2c98fb63676 # v7
      with:
        commit-message: "chore: sync playbook rules (${{ github.action_ref }})"
        title: "chore: sync Engineering Excellence Playbook rules (${{ github.action_ref }})"
        body: |
          Vendored rules from `${{ github.action_repository }}@${{ github.action_ref }}`.
"""


def steps(text: str) -> list[str]:
    """Split the composite action's steps into one text block each."""
    body = text.split("\n  steps:\n", 1)[1]
    return [b for b in re.split(r"\n(?=    - )", "\n" + body) if b.strip()]


def violations(text: str) -> list[str]:
    """Steps that call a nested action yet read the github.action_* context."""
    found = []
    for block in steps(text):
        if re.search(r"^\s+uses:", block, re.MULTILINE) and CONTEXT.search(block):
            name = re.search(r"- name:\s*(.+)", block)
            found.append(name.group(1).strip() if name else block.splitlines()[0].strip())
    return found


class SyncActionProvenance(unittest.TestCase):
    def test_nested_action_steps_never_read_action_context(self):
        self.assertEqual(violations(ACTION.read_text(encoding="utf-8")), [])

    def test_the_pr_names_the_captured_playbook_ref(self):
        text = ACTION.read_text(encoding="utf-8")
        pr = next(b for b in steps(text) if "create-pull-request@" in b)
        for field in ("commit-message:", "title:", "body:"):
            line = next(l for l in pr.splitlines() if l.strip().startswith(field))
            if field == "body:":
                line = pr.split("body:", 1)[1]
            self.assertIn("steps.vendor.outputs.ref", line, f"{field} must name the captured ref")

    def test_the_vendor_step_publishes_ref_and_repository(self):
        text = ACTION.read_text(encoding="utf-8")
        vendor = next(b for b in steps(text) if "id: vendor" in b)
        self.assertNotRegex(vendor, r"^\s+uses:", )
        self.assertIn('echo "ref=$PLAYBOOK_REF"', vendor)
        self.assertIn('echo "repository=$PLAYBOOK_REPO"', vendor)

    def test_designed_to_fail_the_action_before_the_fix_is_refused(self):
        self.assertEqual(violations(SYNC_ACTION_BEFORE_F0037), ["Open or update sync PR"])


if __name__ == "__main__":
    unittest.main()
