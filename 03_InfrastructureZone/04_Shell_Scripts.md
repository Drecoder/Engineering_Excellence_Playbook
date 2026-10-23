# Shell Scripts

*Shell is glue. Keep it short, strict, and checked.*

Shell scripts run the platform's sharpest operations (bootstraps, deploy helpers, GPU sessions),
usually with credentials. They follow the same rules as any other code, checked deterministically
by ShellCheck (`AP-SH-*` in `schemas/antipatterns.v1.json`).

---

## 1️⃣ Rules

- **Strict mode first.** Every bash script starts with `set -euo pipefail`, so a failed command, an
  unset variable, or a failed pipeline stage stops the script (`AP-SH-006`).
- **Quote every expansion:** `"$var"`, `"$(cmd)"`, `"$@"`, `"${array[@]}"` (`AP-SH-001`,
  `AP-SH-002`, `AP-SH-005`). Guard destructive paths with `${var:?}` so an empty variable cannot turn
  `rm -rf "$dir/build"` into `rm -rf /build`.
- **Handle `cd` failing** (`cd dir || exit 1`) before running anything that depends on it
  (`AP-SH-003`).
- **Declare, then assign** command substitutions, so their exit status is not masked (`AP-SH-004`).
- **Never pipe a download into a shell**; download a pinned version, verify its checksum, then run
  it (`AP-SC-001`, `AP-SC-005`, `00_UniversalStandards/13_Supply_Chain.md`).
- **ShellCheck clean.** Every script passes ShellCheck, including `run:` blocks in workflows, which
  actionlint checks with ShellCheck (`AP-GHA-008`).

## 2️⃣ When Not to Use Shell

A script that grows past a screen of logic, parses structured data, or needs error handling beyond
"stop" is rewritten in a real language with tests. Shell stays the glue between well-tested tools.

---

## Principle

Fail fast, quote everything, and let ShellCheck read every line before it runs with credentials.
