Filed as: 260801-implement-jj-history-adapter
FKA:
AKA: jj native history collector
Legacy index:

keywords: tooling, closed, jj, adapter, bookmarks, history

Parent: `260728-movement-snapshot-package`
Depends on: `260801-implement-history-contract-models`;
  `260729-explore-history-surfaces`
Blocks: `260801-collect-history-snapshots`
Blocked by:
Related: `260801-implement-git-history-adapter`

# Implement the jj History Adapter

Collect factual jj workspace heads, visible heads, bookmarks, conflicts,
change identities, and reachable history into the shared v1 models.

## Current Reality
Controlled exploration covers colocated and linked jj surfaces, but the package
does not expose jj graph identity or bookmark topology through the contract.

## Desired Reality
Given a jj repository/workspace, the adapter returns normalized v1 observations
that preserve commit/change identity, divergence, conflicts, visible heads,
linked workspaces, null root, and explicit collection boundaries.

## Gap Analysis
Current scanning cannot distinguish logical changes from commit versions or
describe off-current jj history and conflicted bookmark target sets.

## Known Facts / Assumptions / Unknowns
- Fact: commit ID is graph identity and change ID is logical identity.
- Fact: `00000000` is a virtual jj root, not a real commit or error sentinel.
- Fact: linked jj workspaces share a repository key later assigned by the
  ledger and retain distinct workspace identities.
- Fact: conflicted bookmark target sets are first-class state.
- Assumption: jj operation history is outside the default v1 boundary.
- Unknown: optional operation-depth collection is deferred.

## Investigations
- Reconfirm templates/commands against controlled null-root, divergence,
  conflict, hidden rewrite, and linked-workspace fixtures.
- Determine the narrowest stable adapter handling for supported jj versions.

## Models / Forecasts / Risks
- Conflating change and commit IDs will hide rewrites or fabricate graph edges.
- Dropping removed sides of conflicts will make later resolution uninterpretable.
- Treating hidden history as deleted conflicts with the observed-history ledger.

## Transformations
- Add a jj adapter that identifies a common store and distinct workspaces without
  assigning ledger repository keys itself.
- Collect workspace heads, working-copy facts, visible heads, bookmarks,
  tracking state, and conflicted target sets.
- Walk locally observable selected history with commit IDs, change IDs, parents,
  descriptions, authorship/commit dates, and virtual-root representation.
- Emit explicit complete, partial, and error outcomes with provenance.
- Treat colocation as one combined repository observation surface and avoid
  duplicating Git facts owned by the Git adapter.
- Allowed write surfaces: `src/vcs_tree/`, `tests/`, jj-specific fixtures, and
  this task file; update `tasks/WORKBOARD.md` only for lifecycle changes.
- Do not write ledger state, calculate deltas, inspect operation history by
  default, or change existing renderer output.
- Implemented `src/vcs_tree/jj_adapter.py` with an injectable read-only jj
  command boundary and normalized `JjObservation` output.
- Added workspace/store hints, all-remotes bookmark collection, conflict target
  sets, visible heads, commit/change identity, parent edges, and virtual-root
  records.
- Kept jj-native observations independent from Git facts for later colocation
  merging and ledger persistence.
- Exported `JjAdapter` and `JjObservation` from `vcs_tree`.

## Evidence
- Controlled tests cover colocated and linked workspaces, null root, dirty and
  conflicted working copies, visible heads, divergence, hidden rewrites,
  bookmark conflicts/resolution, and command/read errors.
- Tests prove commit/change identity and conflicted target sets survive model
  round trips without loss.
- Tests prove collection does not mutate the jj or Git repository.
- The full suite and Ruff checks pass at 100% coverage.
- Added `tests/test_jj_adapter.py` covering parser fixtures, linked-store
  hints, workspaces, dirty state, bookmarks/conflicts, visible heads, null
  root, malformed output, timeouts, process errors, and command failures.
- `uv run ruff check src/vcs_tree tests` passed.
- `uv run pytest -q` passed: 101 tests, 100.00% total coverage.
- Read-only smoke collection of this repository returned complete identity and
  boundary outcomes without changing repository state.

## Decisions
- Keep jj-native semantics intact until the snapshot collector combines them
  with Git facts for colocated repositories.
- Preserve commit IDs for graph identity and change IDs for logical-change
  identity; represent the all-zero jj parent as an explicit virtual root.
- Collect all-remotes bookmarks and visible heads so unbookmarked or remote-only
  work remains factual.

## Open Fronts
- Operation history, optional deep collection, persistence, and delta meaning.
- Snapshot orchestration still owns repository keys and Git/jj colocation merge.

## Next Actions
- Claim `260801-collect-history-snapshots`; it can now combine both native
  adapters over the local ledger.
