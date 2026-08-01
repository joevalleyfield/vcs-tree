Filed as: 260801-collect-history-snapshots
FKA:
AKA: snapshot orchestration; topology manifest writer
Legacy index:

keywords: tooling, ready, snapshots, orchestration, persistence, colocation

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

## Evidence
- Integration tests cover Git-only, jj/colocated, linked-workspace, remote-only
  fetch, off-current work, shallow/partial, empty, null-root, and read-error
  observations across repeated snapshots.
- Tests prove deterministic ordering, stable repository keys, object
  deduplication, committed generation references, and atomic publication.
- Tests prove limit failures are explicit and untruncated.
- The full suite and Ruff checks pass at 100% coverage.

## Decisions
- Publish only snapshots backed by committed ledger generations.

## Open Fronts
- Deltas, exports, CLI exposure, and cache migration.

## Next Actions
- Implement after the ledger and both adapters close, then hand stable snapshot
  fixtures to delta and CLI integration work.
