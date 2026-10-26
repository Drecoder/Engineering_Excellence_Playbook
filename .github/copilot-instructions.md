# Copilot / agent instructions

## CI must stay centralized

- All CI lives in one shared reusable workflow in `Drecoder/sovereign-vpc-gcp` (the CI factory). Consumers call it and pass configuration through its inputs (dependency injection).
- Do not add per-repo or per-module CI pipelines, copied setup steps, or local setup actions.
- Fix CI failures (missing setup, lint scope, frozen fixtures, audits, action pinning) in the central workflow, not by working around them here.
- Consumers pin the shared workflow to a commit SHA or controlled release, never `@main`.
- Restate this point in every PR review comment until it is fully addressed.
