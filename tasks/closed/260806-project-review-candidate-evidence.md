Filed as: 260806-project-review-candidate-evidence
FKA:
AKA: current workspace boundary projection; factual candidate packet
Legacy index:

keywords: tooling, closed, history, query, usability

Parent: `260806-support-review-consumers`
Related: `260803-evaluate-mechanical-predicates`;
  `260803-collect-current-working-copy-evidence`

# Project Review Candidate Evidence

Expose a supported factual projection for current-workspace review questions
without emitting review conclusions or requiring private-ledger joins.

## Completion Evidence

- Added `project_current_workspaces` and the `history candidates` CLI command.
  Packets contain stable repository key/path/mode, workspace keys and roles,
  current object/change IDs, exact parent IDs, working-copy state/freshness,
  bounded entries, totals/truncation, refresh outcomes, and component
  completeness.
- Git-unborn and jj-root-parented representations remain native and distinct;
  multiple workspace identities and external/nested paths remain unambiguous.
- The real generation-13 corpus confirmed the 256-entry truncation case for
  `NOAA-chart-reader/s57`; the projection preserves `entries_truncated` and
  unknown totals rather than implying completeness.
- The projection emits no ranking, recommendation, disposition, or
  `initial_commit_due` conclusion. JSON and summary output are supported.
- `scripts/check` passes: 393 tests, 100% statement and branch coverage, Ruff,
  and `uv build`.

## Decisions

- The projection reads one retained snapshot and performs no private-ledger
  joins; repository paths and workspace boundaries are carried in the packet.
- A bounded working-copy list is evidence only. Truncation is explicit and
  continuation is left to a later requested-bound design.

## Allowed Write Surfaces

- query/projection models and services under `src/vcs_tree/`
- focused query/projection tests and fixtures under `tests/`
- query and snapshot contracts/docs
- this task and `tasks/WORKBOARD.md`
