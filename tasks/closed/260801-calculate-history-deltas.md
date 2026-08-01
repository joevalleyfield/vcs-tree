Filed as: 260801-calculate-history-deltas
FKA:
AKA: snapshot comparison engine; factual movement events
Legacy index:

keywords: tooling, closed, delta, comparison, movement, completeness

Parent: `260728-movement-snapshot-package`
Depends on: `260801-implement-history-contract-models`;
  `260801-build-local-history-ledger`
Blocks: `260801-integrate-history-cli`
Blocked by:
Related: `260801-collect-history-snapshots`

# Calculate Factual History Deltas

Compare compatible snapshots and ledger generations into deterministic factual
events while failing closed at incomplete or corrupt boundaries.

## Current Reality
The delta contract defines event meaning and ordering, but the package has no
comparison engine.

## Desired Reality
Given two supported snapshots and their readable ledger generations, the
package emits the complete ordered v1 delta or an explicit partial/error result
without turning missing evidence into movement, deletion, or loss.

## Gap Analysis
Snapshots can record observations but cannot yet answer what refs, workspaces,
reachable history, jj changes, tags, or file evidence changed between them.

## Known Facts / Assumptions / Unknowns
- Fact: comparison uses repository keys within one compatible local ledger.
- Fact: deletion and movement require complete before/after components.
- Fact: shallow/incomplete ancestry yields `movement: "unknown"`.
- Fact: first observation remains factual when recorded by a readable ledger.
- Assumption: v1 materializes complete inline ID lists or reports an explicit
  `limit_exceeded` outcome.
- Unknown: progress/health interpretation and task lifecycle are caller-owned.

## Investigations
- Map each event type to its minimum before/after snapshot components and ledger
  reads.
- Define internal reachability calculations that preserve native object-kind
  distinctions.

## Models / Forecasts / Risks
- Treating an unreadable generation as empty would fabricate mass deletion.
- Using only current workspace ancestry would miss fetched and off-current work.
- Unstable event order would make recurring reports noisy.

## Transformations
- Add compatible snapshot/store precondition validation.
- Implement repository, workspace, ref, tag, history reachability, off-current,
  jj change/version, visible-head, and optional file-evidence events specified
  by the v1 contract.
- Apply completeness gates per component and emit `comparison_incomplete` while
  suppressing unsupported absence/movement assertions.
- Calculate ancestry relations with explicit unknown results for incomplete
  boundaries.
- Emit deterministic repository/event ordering and full inline payloads, or
  explicit limit failure without partial event claims.
- Allowed write surfaces: `src/vcs_tree/`, `tests/`, delta fixtures, and this
  task file; update `tasks/WORKBOARD.md` only for lifecycle changes.
- Do not assess progress, edit repositories, create task files from events,
  introduce paging, or add CLI commands.

## Evidence
- Added `src/vcs_tree/delta.py` with a side-effect-free
  `HistoryDeltaCalculator`/`DeltaCalculator` surface.
- Implemented compatible-store validation, deterministic repository/event
  ordering, repository/workspace/ref events, ancestry movement classification,
  first-observed/current-line/off-current history events, and explicit
  `comparison_incomplete` gates for incomplete refs/workspaces.
- Shallow and unknown ancestry return `unknown`; immutable ledger reads are
  treated as read-only and corruption is isolated from movement claims.
- Added focused delta fixtures covering ref creation and fast-forward movement,
  remote-only history, partial suppression, shallow movement, repository
  identity mismatch, and workspace/ref additions/removals.
- `uv run ruff check src/vcs_tree tests` passes.
- `uv run pytest -q`: 113 tests, 100.00% coverage.

## Decisions
- Keep the engine factual and side-effect free.
- Keep v1 comparison inputs as `SnapshotEnvelope` values or JSON mappings;
  ledger object records remain an optional read-only source.

## Open Fronts
- Progress interpretation, task-lifecycle adapters, paging, and CLI rendering.

## Next Actions
- Integrate the delta calculator into the operator-facing CLI task.
