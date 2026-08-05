Filed as: 260803-index-temporal-fact-intervals
FKA:
AKA: atomic fact ledger; observation intervals; tombstone index
Legacy index:

keywords: tooling, closed, history, facts, intervals, tombstones, indexing

Parent: `260803-define-backlog-review-pressure`
Depends on: `260803-version-mechanical-evidence-schema`
Blocks: `260803-evaluate-mechanical-predicates`
Blocked by:
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
- Added public `TemporalIndexBuilder`, `fact_key`, and `fact_state` APIs with a
  canonical `vcs-tree.temporal-facts` version-1 document.
- Stable fact types cover repository/workspace existence, workspace targets,
  working-copy state and paths, Git refs/targets, jj bookmarks/targets and
  visible heads, native objects/parents, and jj change/version/parent edges.
- Focused fixtures prove first observation from an explicit
  `never_observed/negative_infinity` boundary, repeated confirmation, partial
  omission without tombstones, complete invalidation, target replacement, and
  reappearance as a new episode under the same exact fact key.
- V1 colocated Git-history success plus a more-specific jj graph error leaves
  the jj fact active and advances only its snapshot-precision attempt clock.
- Repository-key replacement at one scoped location records a continuity
  boundary and suppresses cross-boundary tombstones.
- Added `HistoryLedger.read_temporal_index()` and
  `rebuild_temporal_index()`. Missing, corrupt, stale, wrong-schema, and
  wrong-store derived files rebuild from checksummed snapshots and objects;
  repeated rebuilds are byte-equivalent.
- The retained-format 34,819-object fixture proves objects remain unchanged and
  without embedded first-observation fields while referenced object/parent
  facts receive derived intervals.
- A read-only trial over the real ten-generation/34,819-object ledger produced
  18,953 facts and 875 component clocks with no continuity boundaries and no
  source or ledger mutation.
- `scripts/check` passed: Ruff format/lint, 307 tests, 100% statement and branch
  coverage, source distribution, and wheel build.

## Next Actions

- Claim `260803-evaluate-mechanical-predicates`; both of its implementation
  dependencies are now closed.

## Decisions

- Owner: Codex `/root`; claimed 2026-08-04 after schema and working-copy v2
  collection closed.
- Exact assertion keys and stable subject slot keys are separate; entity and
  relationship fact types never share an interval.
- Complete observations invalidate only absence-sensitive facts owned by that
  exact component. Native object and parent facts are positive-only because
  omission cannot prove deletion from the retained object ledger.
- The derived index stores no build wall clock, so unchanged inputs cannot
  manufacture confirmations or transitions.
