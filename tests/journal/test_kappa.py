"""
Tests for Kappa-first learning (tests/journal/kappa.py, KAN-60 slice 3): the retrieval selects what
applies and hands its history to the next prompt, and the check refuses a learning record that
omits applicable history, was made against other Kappa, skips re-checking a reused correction,
reports Kappa unavailable, or was committed after the work began.

The retrieval runs on the real register and journal, so its cases are the Builder's own history.

    python -m unittest discover -s tests/journal -v
"""

import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
from kappa import (  # noqa: E402
    KappaError,
    check_order,
    check_record,
    fields_of,
    main,
    parse_commits,
    record_paths,
    render,
    retrieve,
    sha256,
)

JOURNAL = (ROOT / "docs/POC_JOURNAL.md").read_text(encoding="utf-8")
REGISTER_TEXT = (ROOT / "docs/FINDINGS_REGISTER.json").read_text(encoding="utf-8")
REGISTER = json.loads(REGISTER_TEXT)
ROWS = {r["id"]: r for r in REGISTER["findings"]}
RECORD = ".kappa/KAN-99.json"


def ids(found):
    return [f["id"] for f in found]


def record_for(component, rule_ids=(), fingerprints=(), skip=()):
    """A complete record for a query: every selected finding with a disposition."""
    found = retrieve(REGISTER, JOURNAL, component, rule_ids, fingerprints)
    return {
        "schema_version": "kappa_learning.v1",
        "agent": "builder",
        "work": {"ticket": "KAN-99", "repository": "Drecoder/x", "problem": "a test problem statement"},
        "kappa": {"status": "consulted", "register_sha256": sha256(REGISTER_TEXT),
                  "journal_sha256": sha256(JOURNAL)},
        "query": {"component": component, "rule_ids": list(rule_ids), "fingerprints": list(fingerprints)},
        "result": "matches" if found else "none_found",
        "classification": "related" if found else "new",
        "findings": [{"id": f["id"], "relation": "related", "applies": True,
                      "reason": "considered against the current change", "reuses_correction": False}
                     for f in found if f["id"] not in skip],
        "lessons": [], "uncertainty": [],
    }


def errs(rec):
    return check_record(rec, REGISTER, JOURNAL, REGISTER_TEXT, JOURNAL)


class Retrieval(unittest.TestCase):
    def test_every_open_finding_in_the_component_is_selected(self):
        found = ids(retrieve(REGISTER, JOURNAL, "factory-orchestrator"))
        open_here = sorted(f for f, r in ROWS.items()
                           if r["status"] == "open" and "factory-orchestrator" in r["refs"]["components"])
        self.assertTrue(set(open_here) <= set(found))
        self.assertIn("F-0021", found)

    def test_a_closed_finding_is_not_selected_by_its_component_alone(self):
        self.assertNotIn("F-0051", ids(retrieve(REGISTER, JOURNAL, "factory-orchestrator")))

    def test_a_fingerprint_selects_closed_findings_in_any_component(self):
        found = ids(retrieve(REGISTER, JOURNAL, "coqui-tts", fingerprints=["rule-without-control"]))
        self.assertIn("F-0014", found)  # proven, in the playbook
        self.assertIn("F-0027", found)

    def test_a_rule_selects_closed_findings_only_in_the_component(self):
        found = ids(retrieve(REGISTER, JOURNAL, "playbook", rule_ids=["AGENTS.md#Observability Rules"]))
        self.assertIn("F-0017", found)  # fixed, playbook
        other = ids(retrieve(REGISTER, JOURNAL, "agent-notepad", rule_ids=["AGENTS.md#Observability Rules"]))
        self.assertNotIn("F-0017", other)

    def test_recurrence_links_both_ways(self):
        why = {f["id"]: f["why"] for f in retrieve(REGISTER, JOURNAL, "playbook")}
        self.assertEqual(why["F-0014"], ["related to F-0030"])  # F-0030, open, recurs it
        reg = copy.deepcopy(REGISTER)
        next(r for r in reg["findings"] if r["id"] == "F-0009")["refs"]["fingerprints"] = ["other"]
        why = {f["id"]: f["why"] for f in retrieve(reg, JOURNAL, "agent-notepad",
                                                    fingerprints=["critical-cve-in-image"])}
        self.assertEqual(why["F-0009"], ["related to F-0003"])  # it recurs a selected finding

    def test_a_causal_citation_is_a_relation_and_a_list_of_examples_is_not(self):
        found = {f["id"]: f["why"] for f in
                 retrieve(REGISTER, JOURNAL, "agent-notepad", fingerprints=["diagnosis-from-latest-failure-only"])}
        self.assertIn("related to F-0097", found["F-0039"])  # named in F-0097's heading
        self.assertEqual(found["F-0085"], ["related to F-0097"])  # only in F-0097's Related note
        found = ids(retrieve(REGISTER, JOURNAL, "agent-notepad", fingerprints=["finding-board-drift"]))
        self.assertNotIn("F-0001", found)  # F-0099 lists it as an example only

    def test_an_unknown_component_is_refused(self):
        with self.assertRaises(KappaError):
            retrieve(REGISTER, JOURNAL, "no-such-repo")

    def test_nothing_applies_gives_an_empty_slice(self):
        reg = copy.deepcopy(REGISTER)
        reg["findings"] = [r for r in reg["findings"] if "agent-notepad" not in r["refs"]["components"]]
        self.assertEqual(retrieve(reg, JOURNAL, "agent-notepad"), [])
        self.assertIn("none_found", render([], {"component": "agent-notepad"}))


class HandoffContext(unittest.TestCase):
    """The diagnosis prompt receives the history, not only IDs."""

    def test_the_slice_carries_root_cause_correction_and_preventive_action(self):
        text = render(retrieve(REGISTER, JOURNAL, "playbook", fingerprints=["projection-drops-continuation-lines"]),
                      {"component": "playbook"})
        self.assertIn("## F-0089", text)
        self.assertIn("one-off script run by hand", text)  # its root cause
        self.assertIn("built test first", text)  # its preventive action
        self.assertIn("Register verification:", text)

    def test_plain_form_entries_are_read_too(self):
        row = ROWS["F-0025"]
        block = next(b for h, b in __import__("journal_append_only").entries(JOURNAL) if h == row["journal"])
        fields = fields_of(block)
        self.assertTrue(fields["Root cause"].startswith("the incident record and the journal"))
        self.assertIn("Correction", fields)

    def test_every_selected_entry_has_its_fields(self):
        for f in retrieve(REGISTER, JOURNAL, "sovereign-vpc-gcp"):
            self.assertIn("Problem", f["fields"], f["id"])


class Record(unittest.TestCase):
    def test_a_complete_record_passes(self):
        self.assertEqual(errs(record_for("factory-orchestrator", fingerprints=["surviving-mutant-critical-path"])), [])

    def test_an_omitted_applicable_finding_fails_by_name(self):
        e = errs(record_for("factory-orchestrator", skip=("F-0021",)))
        self.assertEqual(e, ["F-0021 applies to this work (the slice selects it) and has no disposition"])

    def test_an_unknown_finding_fails(self):
        rec = record_for("factory-orchestrator")
        rec["findings"].append(dict(rec["findings"][0], id="F-9999"))
        self.assertIn("F-9999 is not a finding in the register", errs(rec))

    def test_a_duplicate_disposition_fails(self):
        rec = record_for("factory-orchestrator")
        rec["findings"].append(dict(rec["findings"][0]))
        self.assertTrue(any("two dispositions" in e for e in errs(rec)))

    def test_other_kappa_fails(self):
        rec = record_for("factory-orchestrator")
        rec["kappa"]["register_sha256"] = "0" * 64
        self.assertTrue(any(e.startswith("register_sha256") for e in errs(rec)))
        rec = record_for("factory-orchestrator")
        rec["kappa"]["journal_sha256"] = "0" * 64
        self.assertTrue(any(e.startswith("journal_sha256") for e in errs(rec)))

    def test_kappa_unavailable_fails_closed(self):
        rec = record_for("factory-orchestrator")
        rec["kappa"] = {"status": "unavailable", "error": "register not readable"}
        e = errs(rec)
        self.assertEqual(len(e), 1)
        self.assertIn("fails closed", e[0])
        self.assertIn("register not readable", e[0])

    def test_another_agents_record_fails(self):
        rec = record_for("factory-orchestrator")
        rec["agent"] = "pentest"
        self.assertTrue(any("only its own journal" in e for e in errs(rec)))

    def test_a_reused_correction_must_be_rechecked(self):
        rec = record_for("factory-orchestrator")
        rec["findings"][0]["reuses_correction"] = True
        self.assertTrue(any("without saying how it was re-checked" in e for e in errs(rec)))
        rec["findings"][0]["revalidation"] = "re-read the fence test on main at be7918e"
        self.assertEqual(errs(rec), [])

    def test_a_placeholder_reason_fails(self):
        rec = record_for("factory-orchestrator")
        rec["findings"][0]["reason"] = "n/a"
        self.assertTrue(any("too short" in e for e in errs(rec)))

    def test_an_unknown_relation_fails(self):
        rec = record_for("factory-orchestrator")
        rec["findings"][0]["relation"] = "maybe"
        self.assertTrue(any("relation 'maybe'" in e for e in errs(rec)))

    def test_none_found_with_applicable_history_fails(self):
        rec = record_for("factory-orchestrator")
        rec.update(result="none_found", findings=[])
        e = errs(rec)
        self.assertTrue(any("result is none_found" in x for x in e))
        self.assertTrue(any("F-0021 applies" in x for x in e))

    def test_none_found_passes_when_nothing_applies(self):
        reg = copy.deepcopy(REGISTER)
        reg["findings"] = [r for r in reg["findings"] if "agent-notepad" not in r["refs"]["components"]]
        text = json.dumps(reg)
        rec = record_for("factory-orchestrator")
        rec.update(query={"component": "agent-notepad"}, result="none_found", findings=[], classification="new")
        rec["kappa"]["register_sha256"] = sha256(text)
        self.assertEqual(check_record(rec, reg, JOURNAL, text, JOURNAL), [])

    def test_matches_with_nothing_listed_fails(self):
        reg = copy.deepcopy(REGISTER)
        reg["findings"] = [r for r in reg["findings"] if "agent-notepad" not in r["refs"]["components"]]
        text = json.dumps(reg)
        rec = record_for("factory-orchestrator")
        rec.update(query={"component": "agent-notepad"}, result="matches", findings=[], classification="new")
        rec["kappa"]["register_sha256"] = sha256(text)
        self.assertIn("result is matches, but no finding is listed", check_record(rec, reg, JOURNAL, text, JOURNAL))

    def test_an_unknown_result_fails(self):
        rec = record_for("factory-orchestrator")
        rec["result"] = "some"
        self.assertIn("result 'some' is neither matches nor none_found", errs(rec))

    def test_classification_must_agree_with_the_dispositions(self):
        rec = record_for("factory-orchestrator")
        rec["classification"] = "new"
        rec["findings"][0]["relation"] = "recurring"
        self.assertTrue(any("classification is new" in e for e in errs(rec)))
        rec = record_for("factory-orchestrator")
        rec["classification"] = "regression_of_prior_correction"
        self.assertTrue(any("regression_of_prior_correction" in e for e in errs(rec)))
        rec["findings"][0]["relation"] = "caused_by_prior_correction"
        self.assertEqual(errs(rec), [])
        rec["classification"] = "maybe"
        self.assertTrue(any("classification 'maybe'" in e for e in errs(rec)))

    def test_an_unknown_schema_version_is_refused_first(self):
        rec = record_for("factory-orchestrator")
        rec["schema_version"] = "kappa_learning.v0"
        self.assertEqual(len(errs(rec)), 1)

    def test_an_unknown_component_in_the_query_fails(self):
        rec = record_for("factory-orchestrator")
        rec["query"]["component"] = "no-such-repo"
        self.assertTrue(any("no-such-repo" in e for e in errs(rec)))


class Order(unittest.TestCase):
    """The stage ran before the work: the record is committed before any other change."""

    def commits(self, *changes):
        return parse_commits("\n".join(f"c{i}\t{p}" if p else f"c{i}\t"
                                       for i, paths in enumerate(changes) for p in (paths or [""])))

    def test_the_record_first_then_the_work_passes(self):
        self.assertEqual(check_order(self.commits([RECORD], ["src/a.py"], ["src/a.py", RECORD]), RECORD), [])

    def test_the_work_before_the_record_fails(self):
        e = check_order(self.commits(["src/a.py"], [RECORD]), RECORD)
        self.assertEqual(len(e), 1)
        self.assertIn("committed after the work began: c0 changes src/a.py", e[0])

    def test_the_record_in_the_same_commit_as_the_work_fails(self):
        self.assertTrue(check_order(self.commits([RECORD, "src/a.py"]), RECORD))

    def test_no_record_fails(self):
        self.assertTrue(check_order(self.commits(["src/a.py"]), RECORD))

    def test_an_empty_commit_before_the_record_is_not_work(self):
        self.assertEqual(check_order(self.commits([], [RECORD], ["src/a.py"]), RECORD), [])

    def test_only_learning_records_are_found(self):
        c = self.commits([RECORD, ".kappa/notes.txt", "kappa/x.json"], ["src/a.py"])
        self.assertEqual(record_paths(c), [RECORD])


class Cli(unittest.TestCase):
    def run_check(self, tmp, commits, record):
        (tmp / "commits.tsv").write_text(commits)
        if record is not None:
            (tmp / ".kappa").mkdir(exist_ok=True)
            (tmp / RECORD).write_text(json.dumps(record))
        return main(["check", "--commits", str(tmp / "commits.tsv"), "--head", str(tmp),
                     "--journal", str(ROOT / "docs/POC_JOURNAL.md"),
                     "--register", str(ROOT / "docs/FINDINGS_REGISTER.json")])

    def test_check_passes_and_fails(self):
        import contextlib, io, tempfile  # noqa: E401
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()) as out:
            tmp = Path(d)
            good = record_for("factory-orchestrator")
            self.assertEqual(self.run_check(tmp, f"a\t{RECORD}\nb\tsrc/x.ts\n", good), 0)
            self.assertEqual(self.run_check(tmp, f"a\tsrc/x.ts\nb\t{RECORD}\n", good), 1)
            self.assertEqual(self.run_check(tmp, f"a\t{RECORD}\n", record_for("factory-orchestrator", skip=("F-0021",))), 1)
            self.assertEqual(self.run_check(tmp, "a\tsrc/x.ts\n", None), 1)
            self.assertEqual(self.run_check(tmp, f"a\t{RECORD}\na\t.kappa/KAN-1.json\n", good), 1)
        self.assertIn("F-0021 applies", out.getvalue())
        self.assertIn("expected one learning record", out.getvalue())

    def test_slice_cli_prints_markdown_and_json(self):
        import contextlib, io  # noqa: E401
        for fmt, needle in (("md", "## F-0021"), ("json", '"F-0021"')):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(main(["slice", "--component", "factory-orchestrator", "--format", fmt,
                                       "--journal", str(ROOT / "docs/POC_JOURNAL.md"),
                                       "--register", str(ROOT / "docs/FINDINGS_REGISTER.json")]), 0)
            self.assertIn(needle, out.getvalue())


class ThisChangesOwnRecord(unittest.TestCase):
    """The change that adds the rule carries a record of its own, and it passes against main's Kappa
    as it stood when the record was made. Its digests pin that Kappa, so the test reads it back."""

    def test_kan_60s_record_is_well_formed(self):
        rec = json.loads((ROOT / ".kappa/KAN-60.json").read_text(encoding="utf-8"))
        self.assertEqual(rec["schema_version"], "kappa_learning.v1")
        self.assertEqual(rec["work"]["ticket"], "KAN-60")
        self.assertGreater(len(rec["findings"]), 0)


if __name__ == "__main__":
    unittest.main()
