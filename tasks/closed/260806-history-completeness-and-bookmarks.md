Filed as: 260806-history-completeness-and-bookmarks
FKA:
AKA: delta completeness; jj bookmark movement
Legacy index:

keywords: delta, closed, completeness, history, bookmarks, jj, git, dispatch

Parent: `260728-movement-snapshot-package`
Depends on: `260805-delta-presentation-surfaces`; `260801-implement-jj-history-adapter`
Blocks:
Blocked by:
Related: `260801-calculate-history-deltas`

# Close History Completeness and Bookmark Delta Gaps

Make incomplete-history reports explainable and mode-aware so downstream
dispatchers can distinguish tool gaps from repository movement.

## Current Reality

The delta engine checks a generic `refs` component for every repository, even
though jj-only snapshots expose `bookmarks` instead. It also suppresses history
comparisons when the history component is partial or errored without emitting a
`comparison_incomplete` event. The result can say `partial` while omitting the
actual history cause, or warn that jj refs are unavailable when bookmarks are
complete.

## Desired Reality

- Git/colocated repositories gate ref comparisons on `refs`.
- jj-only repositories gate ref-like comparisons on `bookmarks` while keeping
  the existing factual movement event vocabulary stable.
- Any incomplete history component emits an indeterminate comparison event
  naming its from/to states and suppressed history event families.
- Human summaries expose the incomplete component and state transition rather
  than only printing `comparison_incomplete`.

## Acceptance Criteria

- jj bookmark-complete snapshots do not produce false refs-incomplete warnings.
- Git refs errors and jj bookmark errors/not-requested states remain explicit
  unknown movement warnings.
- History partial/error/not-requested transitions produce explicit warnings and
  suppress history movement claims.
- Existing complete Git, jj, and colocated movement events remain compatible.
- Default and JSON delta views identify the affected component and states.
- A controlled fixture demonstrates the exact reason for a partial delta and
  the summary distinguishes unknown movement from verified no-op.
- `uv run ruff check src/vcs_tree tests` and `uv run pytest -q` pass with the
  100% statement and branch coverage gate.

## Allowed Write Surfaces

- `src/vcs_tree/delta.py` and delta CLI presentation only
- `tests/` and test fixtures
- `docs/contracts/` or `README.md` for the compatibility note
- this task file and `tasks/WORKBOARD.md`
- No adapter redesign, ledger migration, or repository mutation.

## Completion Evidence

- Focused delta tests cover Git refs, jj bookmarks, colocated refs, history
  partial/error, and complete no-op cases.
- Installed-CLI coverage shows component/state explanations in summary and JSON.
- Full Ruff and pytest validation records the coverage gate.

Implementation evidence:

- Mode-aware gating now compares `bookmarks` for jj-only repositories and
  `refs` for Git/colocated repositories, eliminating false jj ref warnings.
- History partial/error states now emit indeterminate comparison events with
  suppressed history event families and explicit from/to states.
- The real retained snapshot pair now reports nine actionable gaps: eight
  history failures/partial states and one Git refs error, plus the observed
  vcs-tree workspace movement; 58 repositories are verified no-ops.
- `uv run ruff check src/vcs_tree tests` passes; `uv run pytest -q` passes 146
  tests with 100% statement and branch coverage.

## Open Fronts

- A future adapter task may add richer jj bookmark event names; this task keeps
  the existing generic ref event names for compatibility.
