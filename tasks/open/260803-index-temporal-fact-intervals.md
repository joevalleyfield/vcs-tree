Filed as: 260803-index-temporal-fact-intervals
FKA:
AKA: atomic fact ledger; observation intervals; tombstone index
Legacy index:

keywords: tooling, blocked, history, facts, intervals, tombstones, indexing

Parent: `260803-define-backlog-review-pressure`
Depends on: `260803-version-mechanical-evidence-schema`
Blocks: `260803-evaluate-mechanical-predicates`
Blocked by: `260803-version-mechanical-evidence-schema`
Related: `260801-build-local-history-ledger`; `260801-calculate-history-deltas`

# Index Temporal Fact Intervals

Build a deterministic, rebuildable temporal projection of retained v1/v2
observations so mechanical consumers can query confirmations, invalidations,
reappearances, and elapsed observer time without rescanning every generation.

## Contract

Follow the temporal and identity rules in
`planning/mechanical-review-evidence-v1.md` and the v1 seeding/storage boundary
in `planning/mechanical-review-dispatch.md`.

## Acceptance Criteria

- A stable atomic fact vocabulary covers repository/workspace existence,
  workspace targets, recorded working-copy state and paths, Git refs/targets,
  jj bookmarks/targets, visible heads, native objects/parents, and jj
  change/version edges.
- Entity facts and relationship facts use separate stable keys.
- The projection retains validity episodes with first observed, last confirmed,
  invalidated, evidence snapshot/component, and timestamp precision.
- First retained observation uses a prior `never_observed` boundary with
  negative-infinity comparison semantics.
- Partial observations reconfirm only positive facts actually present and
  cannot create tombstones from omission.
- Complete observations tombstone prior active facts whose absence is supported
  by that specific component.
- Reappearance opens a new interval under the same fact slot only when identity
  continuity is supported.
- V1 seeding uses `captured_at` as coarse observer time and the most specific
  available component outcome; masked jj errors never authorize tombstones.
- Component `last_attempted_at` and `complete_as_of` are derived independently
  from retained attempt outcomes.
- The persisted index is explicitly rebuildable and disposable. Deletion or
  corruption triggers a deterministic rebuild from retained snapshots rather
  than loss claims or source-repository mutation.
- Rebuilding twice without new snapshots produces byte-equivalent canonical
  data and does not manufacture transitions.

## Allowed Write Surfaces

- one new temporal-fact module under `src/vcs_tree/`
- `src/vcs_tree/ledger.py`
- `src/vcs_tree/delta.py`
- `src/vcs_tree/__init__.py`
- new focused temporal-fact tests under `tests/`
- `tests/test_ledger.py`
- `tests/test_delta.py`
- relevant temporal sections under `docs/contracts/`
- this task file and `tasks/WORKBOARD.md`

Do not edit native adapters, snapshot collection commands, CLI dispatch,
predicate evaluation, semantic review logic, the baseline script, or live
resource files.

## Required Fixtures

- Never observed, first positive observation, repeated confirmation, complete
  invalidation, and reappearance.
- Partial positive evidence followed by repeated partial and complete recovery.
- Ref retained while its target edge changes.
- V1 colocated snapshot with masked jj error.
- Repository continuity loss preventing cross-boundary tombstones.
- Corrupt/missing derived index rebuilt from mixed v1/v2 snapshots.

## Completion Evidence

- Focused interval, identity, rebuild, and corruption tests cover every branch.
- A retained-format fixture reproduces the 34,819-object corpus property that
  native objects lack embedded first-observation fields and proves the derived
  index does not rewrite them.
- `scripts/check` passes with 100% statement and branch coverage.

## Next Actions

- Claim after `260803-version-mechanical-evidence-schema` closes; it may run in
  parallel with working-copy collection.

