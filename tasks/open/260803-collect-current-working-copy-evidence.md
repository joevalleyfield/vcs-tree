Filed as: 260803-collect-current-working-copy-evidence
FKA:
AKA: jj refresh fallback; current workspace evidence
Legacy index:

keywords: tooling, active, adapters, jj, git, working-copy, completeness

Parent: `260803-define-backlog-review-pressure`
Depends on: `260803-version-mechanical-evidence-schema`
Blocks: `260803-evaluate-mechanical-predicates`; `260803-test-mechanical-query-workflow`
Blocked by:
Related: `260801-implement-jj-history-adapter`; `260801-implement-git-history-adapter`

# Collect Current Working-Copy Evidence

Make Git and jj working-copy observations current, symmetric where their native
models permit it, and explicit about refresh, fallback, paths, conflicts, and
component completeness.

## Contract

Follow the snapshot-v2 boundary in
`planning/mechanical-review-dispatch.md`. Normal jj observation may snapshot the
filesystem into `@`; fallback reads recorded `@` without calling it current.

## Acceptance Criteria

- The primary requested jj workspace is refreshed through the normal native
  observation path before its v2 facts are collected.
- Refresh success records `performed/current` and collects `@` commit/change
  IDs, parents, empty/nonempty state, conflicts, description, and bounded
  parent-relative path/type evidence.
- Refresh failure is retained and triggers a no-refresh fallback. Successful
  fallback records usable `@` facts as `recorded_maybe_stale`; it does not
  collapse them to `unknown`.
- A skipped refresh is distinguishable from failure. Linked workspaces not
  refreshed through their own filesystem location remain recorded/stale rather
  than implicitly current.
- Git status observes HEAD/index/worktree state and paths without optional
  index-refresh writes where supported. Git unborn state remains distinct from
  error and clean state.
- Workspace topology, working-copy state, refresh, native history, and path
  evidence have independent outcomes and attempt times.
- Colocated aggregation never promotes an errored jj history/change graph to
  complete because Git history succeeded.
- Git unborn facts and jj `@`-parented-only-by-virtual-root facts provide the
  mechanical premises documented for an intelligent initial-boundary review.
- No collection command fetches, moves bookmarks/refs, commits, rebases,
  abandons, repairs, resets, or intentionally rewrites user files/history.
- Existing nested-repository and pulse consumers remain compatible through the
  v2 normalization/presentation boundary.
- Production snapshot collection switches from v1 to v2 only in this task,
  after every required v2 component and workspace field is populated.

## Allowed Write Surfaces

- `src/vcs_tree/git_adapter.py`
- `src/vcs_tree/jj_adapter.py`
- `src/vcs_tree/snapshot.py`
- one new working-copy helper module under `src/vcs_tree/`
- `tests/test_git_adapter.py`
- `tests/test_jj_adapter.py`
- `tests/test_snapshot.py`
- `tests/test_nested_snapshot.py`
- focused new working-copy fixtures/tests under `tests/`
- relevant working-copy sections under `docs/contracts/`
- this task file and `tasks/WORKBOARD.md`

Do not edit temporal fact indexing, predicate/query evaluation, CLI dispatch,
review semantics, the baseline script, or live resource files.

## Required Fixtures

- jj refresh success with nonempty `@`, changed paths, and conflicts.
- Native refresh permission failure followed by successful stale-recorded
  fallback.
- Refresh and fallback both failing with separately retained errors.
- Linked jj workspaces with one refreshed location and one recorded-only
  location.
- jj `@` whose only parent is the virtual root, both empty and nonempty.
- Git unborn clean/error/changed states and status-path failure.
- Colocated Git-history success plus jj-history error.

## Completion Evidence

- Focused tests prove every refresh/fallback/completeness branch.
- A controlled temporary jj repository shows normal observation snapshotting
  an edited file into `@` and emitting its path evidence.
- `scripts/check` passes with 100% statement and branch coverage.
- Closure records supported jj version behavior and exact native commands.

## Next Actions

- Claim after `260803-version-mechanical-evidence-schema` closes.

## Decisions

- Owner: Codex `/root`; claimed 2026-08-04 after the schema dependency closed.
