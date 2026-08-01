Filed as: 260801-collect-history-snapshots
FKA:
AKA: snapshot orchestration; topology manifest writer
Legacy index:

keywords: tooling, closed, snapshots, orchestration, persistence, colocation

Parent: `260728-movement-snapshot-package`
Depends on: `260801-build-local-history-ledger`;
  `260801-implement-git-history-adapter`; `260801-implement-jj-history-adapter`
Blocks: `260801-integrate-history-cli`
Blocked by:
Related: `260801-calculate-history-deltas`

# Collect and Persist History Snapshots

Combine native observations into deterministic lightweight snapshot manifests
backed by committed ledger generations.

## Current Reality
The contracts describe snapshots, and preceding tasks supply state and native
observations, but no component owns orchestration, colocation merge rules, or
snapshot persistence.

## Desired Reality
One collection operation observes the requested repository tree, appends new
immutable objects, commits a ledger generation, and persists a deterministic
snapshot whose topology and outcomes accurately describe that observation.

## Gap Analysis
Adapters alone cannot assign repository identities, deduplicate colocated
observations, enforce generation invariants, or produce comparable manifests.

## Known Facts / Assumptions / Unknowns
- Fact: colocation is one first-class repository mode, not two repository scans.
- Fact: every referenced object is present in the committed generation unless
  the relevant boundary explicitly reports otherwise.
- Fact: empty, unborn, virtual-root, partial, and error states are distinct.
- Assumption: snapshots remain lightweight references over the retained ledger.
- Unknown: portable export framing is deferred.

## Investigations
- Define deterministic merge precedence for shared Git/jj facts already
  assigned to the two adapters.
- Define crash boundaries between object append, generation commit, and snapshot
  index publication.

## Models / Forecasts / Risks
- Publishing a snapshot before its generation commits creates dangling roots.
- Scanning colocated repositories twice can invent duplicate repository keys.
- A partial component must not erase prior knowledge or imply absence.

## Transformations
- Add a collector/orchestrator that resolves repository mode and invokes the
  required native adapters once per observation surface.
- Assign/reuse ledger repository keys and merge Git/jj results for colocation.
- Append newly observed immutable objects and commit a generation before
  publishing its snapshot.
- Persist deterministic snapshot envelopes, topology, component outcomes,
  provenance, and snapshot index entries.
- Preserve complete ID lists or fail the affected component explicitly with
  `limit_exceeded`; never silently truncate.
- Allowed write surfaces: `src/vcs_tree/`, `tests/`, integration fixtures, and
  this task file; update `tasks/WORKBOARD.md` only for lifecycle changes.
- Do not calculate deltas, define export bundles, add paging, or redirect the
  live resource command.
- Implemented `src/vcs_tree/snapshot.py` with `SnapshotCollector` and
  `SnapshotResult` orchestration over the Git/jj adapters and local ledger.
- Assigned stable local repository keys, merged colocated native surfaces,
  preserved roots/workspaces/refs/outcomes, and deduplicated immutable history
  objects before generation commit.
- Extended the ledger snapshot index to retain each published manifest
  alongside its committed generation.
- Published v1 envelopes only after object and generation writes; delta
  calculation, export, paging, and CLI remain outside this task.

## Evidence
- Integration tests cover Git-only, jj/colocated, linked-workspace, remote-only
  fetch, off-current work, shallow/partial, empty, null-root, and read-error
  observations across repeated snapshots.
- Tests prove deterministic ordering, stable repository keys, object
  deduplication, committed generation references, and atomic publication.
- Tests prove limit failures are explicit and untruncated.
- The full suite and Ruff checks pass at 100% coverage.
- Added `tests/test_snapshot.py` covering Git-only, jj-only, colocated merge,
  repeated snapshots, stable keys, object deduplication, partial outcomes,
  shallow/unknown boundaries, deterministic roots, and manifest indexing.
- `uv run ruff check src/vcs_tree tests` passed.
- `uv run pytest -q` passed: 108 tests, 100.00% total coverage.
- End-to-end read-only collection of this repository into a temporary ledger
  produced generation 1 and a colocated snapshot without changing source VCS
  state.

## Decisions
- Publish only snapshots backed by committed ledger generations.
- Use the resolved repository path as the v1 local continuity key; no portable
  clone identity is inferred.
- In colocated mode, jj owns workspace observations while Git owns the selected
  user-ref surface; native histories are retained together in one record.

## Open Fronts
- Deltas, exports, CLI exposure, and cache migration.
- Limit policy remains explicit in later snapshot/CLI surfaces; no IDs are
  silently truncated here.

## Next Actions
- Claim `260801-calculate-history-deltas`; the collector now provides durable,
  generation-backed snapshot fixtures for comparison.
