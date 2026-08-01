Filed as: 260801-implement-git-history-adapter
FKA:
AKA: Git native history collector
Legacy index:

keywords: tooling, closed, git, adapter, refs, history

Parent: `260728-movement-snapshot-package`
Depends on: `260801-implement-history-contract-models`;
  `260729-explore-history-surfaces`
Blocks: `260801-collect-history-snapshots`
Blocked by:
Related: `260801-implement-jj-history-adapter`

# Implement the Git History Adapter

Collect factual Git workspaces, selected refs, annotated tags, reachable
objects, and completeness signals into the shared v1 models.

## Current Reality
The exploration records reliable Git command surfaces and fixtures, but package
collection remains renderer-shaped and current-state oriented.

## Desired Reality
Given a Git repository/worktree, the adapter returns normalized v1 observations
covering selected local, remote-tracking, and tag namespaces and all reachable
history, with explicit partial/error outcomes.

## Gap Analysis
The package cannot yet notice fetched remote-only lines, off-current branch
work, ref deletion/movement, annotated tags, shallow ancestry, or linked
worktrees through the history contract.

## Known Facts / Assumptions / Unknowns
- Fact: use explicit selected namespaces rather than raw `--all` in colocation.
- Fact: annotated tag objects and peeled commit roots are distinct.
- Fact: incomplete/shallow ancestry must be explicit.
- Assumption: reflogs, dangling objects, and promisor retrieval are not default
  v1 boundaries.
- Unknown: optional deep mode is deferred.

## Investigations
- Reconfirm command parsing against the controlled fixtures before codifying it.
- Identify stable machine-readable delimiters for paths and ref names.

## Models / Forecasts / Risks
- Implicit object fetching would mutate repository state during observation.
- Treating missing shallow parents as deletion would create false movement.
- Colocated internal refs can duplicate or distort jj-visible topology.

## Transformations
- Add a Git adapter that identifies the common repository and distinct linked
  workspaces without assigning ledger repository keys itself.
- Collect workspace heads and working-copy facts without mutating the repository.
- Collect the documented local, remote-tracking, and tag namespaces, preserving
  symbolic/annotated distinctions and peeled targets.
- Walk the complete selected reachable graph available locally, emitting native
  IDs, parents, metadata, and optional file evidence only as requested.
- Emit explicit complete, shallow, partial, and error outcomes with provenance.
- Allowed write surfaces: `src/vcs_tree/`, `tests/`, Git-specific fixtures, and
  this task file; update `tasks/WORKBOARD.md` only for lifecycle changes.
- Do not write ledger state, calculate deltas, inspect reflogs/dangling objects,
  fetch objects, or change existing renderer output.
- Implemented `src/vcs_tree/git_adapter.py` with an injectable read-only Git
  command boundary and normalized `GitObservation` output.
- Added selected `refs/heads`, `refs/remotes`, and `refs/tags` collection,
  annotated/peeled tag preservation, worktree/status facts, reachable commit
  metadata, and shallow-boundary detection.
- Kept repository identity, collection outcomes, and history boundaries
  separate so later snapshot orchestration can assign ledger keys.
- Exported `GitAdapter` and `GitObservation` from `vcs_tree`.

## Evidence
- Controlled tests cover Git-only and colocated repositories, linked worktrees,
  unborn/empty history, dirty state, annotated tags, remote-only fetch results,
  ref movement/deletion, shallow boundaries, and command/read errors.
- Tests prove selected namespaces exclude irrelevant colocated internals.
- Tests prove collection does not change repository refs or object state.
- The full suite and Ruff checks pass at 100% coverage.
- Added `tests/test_git_adapter.py` covering parser fixtures, Git-only and
  linked-worktree shapes, selected refs/tags, empty history, shallow history,
  identity/ref/history/status failures, timeouts, and process errors.
- `uv run ruff check src/vcs_tree tests` passed.
- `uv run pytest -q` passed: 90 tests, 100.00% total coverage.
- Read-only smoke collection of this repository returned a complete identity,
  zero selected refs, zero history objects, and a complete boundary without
  changing repository state.

## Decisions
- Keep native command execution and normalization behind one adapter boundary.
- Use explicit user-facing ref namespaces and never `git --all` as the default
  history boundary in a colocated repository.
- Use peeled commit IDs as history roots while retaining annotated tag object
  identity in the ref record.

## Open Fronts
- Reflogs, dangling objects, optional deep history, and persistence.
- jj-native collection remains in `260801-implement-jj-history-adapter`.

## Next Actions
- Claim `260801-implement-jj-history-adapter`; snapshot orchestration can later
  combine the two native observations for colocated repositories.
