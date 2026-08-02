Filed as: 260802-precommit-checks
FKA:
AKA: local quality gate; pre-commit validation
Legacy index:

keywords: housekeeping, closed, checks, format, lint, test, build, policy

Parent:
Depends on:
Blocks:
Blocked by:
Related:

# Establish the Local Pre-Commit Quality Gate

Provide one repository-local command for formatting, linting, testing, and
package-build validation, and document that it must pass before code commits.

## Acceptance Criteria

- A checked-in executable script runs Ruff format check, Ruff lint, the full
  pytest/coverage gate, and `uv build` in a deterministic order.
- The script uses the project-managed uv environment and returns nonzero on the
  first failed check.
- AGENTS and README policy direct contributors to run the script before code
  commits and identify the required 100% coverage gate.
- The complete local gate passes on the resulting tree.

## Allowed Write Surfaces

- `scripts/` or `.codex-local/` for the local validation entry point
- `AGENTS.md`, `README.md`, and this task/workboard
- No production behavior or live resource changes.

## Completion Evidence

- `scripts/check` completes Ruff format check, Ruff lint, pytest, and uv build
  successfully; the build required network access only to resolve hatchling in
  the sandbox.
- `uv run pytest -q` passes 146 tests with 100% statement and branch coverage.
- `AGENTS.md` and `README.md` now require `scripts/check` before code commits;
  the script keeps uv's disposable cache outside the repository by default.
