Filed as: 260801-implement-git-history-adapter
FKA:
AKA: Git native history collector
Legacy index:

keywords: tooling, ready, git, adapter, refs, history

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

## Evidence
- Controlled tests cover Git-only and colocated repositories, linked worktrees,
  unborn/empty history, dirty state, annotated tags, remote-only fetch results,
  ref movement/deletion, shallow boundaries, and command/read errors.
- Tests prove selected namespaces exclude irrelevant colocated internals.
- Tests prove collection does not change repository refs or object state.
- The full suite and Ruff checks pass at 100% coverage.

## Decisions
- Keep native command execution and normalization behind one adapter boundary.

## Open Fronts
- Reflogs, dangling objects, optional deep history, and persistence.

## Next Actions
- Implement from the exploration fixtures after the model task closes.
