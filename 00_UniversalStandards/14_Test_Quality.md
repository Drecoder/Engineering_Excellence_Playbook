# Test Quality

*A passing suite is evidence only if the tests could have failed.*

Tests are the evidence behind every merge, every autonomy promotion, and every claim that work is
done. This standard covers how good that evidence is. File-level test anti-patterns are the
`AP-TEST-*` rules in `schemas/antipatterns.v1.json`; the measurements below are pipeline checks.

---

## 1️⃣ Tests That Can Fail

- **No committed `.only` or `.skip`.** A focused test silently disables the rest of the file; a
  skipped one stops checking its behavior with no record of why (`AP-TEST-001`, `AP-TEST-003`). A
  test that must wait links an issue with an owner and a date.
- **Every test asserts.** A test without an assertion passes whatever the code does
  (`AP-TEST-002`).
- **Expected failures are asserted precisely:** `pytest.raises` with `match=` or a specific type,
  never an assertion inside `except`, never `assert False` (`AP-TEST-004`–`006`).

## 2️⃣ Coverage: a Floor, Not a Goal

- The pipeline measures **changed-line coverage** on every pull request. Changed lines without a
  test reaching them are reported, and the Reviewer's features record them (`features.v1`
  `structure.untested`).
- A repository sets a coverage floor and the pipeline holds it; coverage is never raised by tests
  that assert nothing, which is why `AP-TEST-002` exists. The floors are committed as
  `.ci/quality.v1.json` (`schemas/quality.v1.schema.json`): the total-coverage floor blocks, the
  changed-line target is reported, and a floor is lowered only through a reviewed pull request.

## 3️⃣ Mutation Testing: Do the Tests Notice?

- Coverage shows code ran; **mutation testing** shows the tests would notice if it were wrong. A
  mutation tool (Stryker for TypeScript, mutmut for Python, or equivalent) changes the code in small
  ways and checks that a test fails.
- It runs on the changed code of a pull request, or nightly on a whole repository; the **mutation
  score** is a metric with a floor, tracked like any other quality metric.
- Surviving mutants on critical paths (authorization, money, data deletion) are findings.

## 4️⃣ Determinism

- Tests do not depend on wall-clock time, network services outside the test, ordering between
  tests, or shared state; a flaky test is a defect, rerun once at most and then fixed or quarantined
  with an owner (`06_AgentZone/01_Agent_Standards.md`, build-failure routing).
- Test evidence counts only as telemetry, like every other verification
  (`AGENTS.md` → Observability Rules).

---

## Principle

Count a test only if it could fail, measure whether the suite notices wrong code, and treat a flaky
test as a bug.
