# Synchronize task workboard from task artifacts

Filed as: 260803-sync-workboard
FKA:
AKA: workboard synchronizer; task inventory sync
Legacy index:

keywords: tooling, governance, historical, workboard, maintainability

Parent:
Depends on:
Blocks:
Blocked by:
Related: `260802-reconcile-workboard`

## Objective

Adapt the proven task-inventory synchronizer from `../toas` so this repository's
Open Queue is generated from `tasks/open/`, while recent closures and the
relationship view remain useful and manually authored context is preserved.

## Acceptance criteria

- A repository-local command synchronizes marker-managed workboard sections.
- Open Queue contains only task artifacts currently under `tasks/open/`.
- Recent Closures is generated from `tasks/closed/` without losing manual prose.
- Missing markers fail safely without rewriting unrelated board content.
- The command is documented and has focused tests for parsing, rendering, and
  idempotent synchronization.

## Allowed write surfaces

- `tasks/scripts/sync_workboard.py`
- `scripts/sync-workboard`
- `tasks/WORKBOARD.md`
- `tasks/README.md`
- `tests/test_workboard_sync.py`
- This task artifact and its completion evidence

## Completion evidence

- [x] Synchronizer tests pass: five focused tests pass; the full suite passes
  with 100% statement and branch coverage.
- [x] `scripts/check` passes: Ruff and pytest pass; `uv build` succeeds after
  allowing the build dependency lookup.
- [x] Workboard contains only the two files currently under `tasks/open/` in
  its generated Open Queue, with eight recent closures in the generated history
  section.

## Decisions and evidence

- Adapted the inventory parser and marker replacement pattern from
  `../toas/tasks/scripts/sync_workboard.py` rather than copying its Git-age
  heuristic or relationship-root assumptions.
- Added `scripts/sync-workboard` and `--check`; missing markers leave the board
  untouched, while marked Open Queue and Recent Closures blocks are derived from
  task directories.
- `scripts/check`: 201 tests passed at 100% statement and branch coverage;
  Ruff passed; `uv build` produced both sdist and wheel.
