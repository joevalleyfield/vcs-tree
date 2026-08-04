Filed as: 260803-version-mechanical-evidence-schema
FKA:
AKA: snapshot v2; evidence schema compatibility
Legacy index:

keywords: tooling, closed, schema, models, compatibility, snapshots

Parent: `260803-define-backlog-review-pressure`
Depends on: `260803-define-backlog-review-pressure`
Blocks: `260803-collect-current-working-copy-evidence`; `260803-index-temporal-fact-intervals`
Blocked by:
Related: `260801-implement-history-contract-models`; `260801-collect-history-snapshots`

# Version the Mechanical Evidence Schema

Implement the snapshot-v2 model and v1 compatibility boundary required by
`planning/mechanical-review-dispatch.md` without changing native collection
commands or adding predicate evaluation.

## Current Reality

- Snapshot and delta models accept exactly schema version 1.
- V1 component outcomes collapse some native surfaces and cannot represent
  independent working-copy refresh or freshness.
- Existing parsers discard unknown nested fields during typed round trips.
- Ten retained v1 generations must remain readable and must not be rewritten.

## Desired Reality

The package can validate, serialize, write, read, and normalize snapshot v2
while continuing to consume v1. Engineers working on collection and temporal
facts have one stable typed boundary with no remaining schema choices.

## Contract

Follow `planning/mechanical-review-evidence-v1.md` and
`planning/mechanical-review-dispatch.md`. The dispatch document is authoritative
for v2 component names, working-copy shape, timestamp placement, and v1
normalization.

## Acceptance Criteria

- Models and serializers can explicitly construct
  `vcs-tree.history-snapshot` schema version 2, but production snapshot
  collection continues to emit v1 until the dependent collection task can
  populate every required v2 component.
- Version-aware readers accept v1 and v2 and reject unsupported versions.
- Existing retained v1 manifests open and list without in-place migration.
- V2 validates independent outcomes for identity, native workspace surfaces,
  per-workspace working-copy state/refresh, Git refs, jj bookmarks/visible
  heads, native histories, and requested path evidence.
- Every attempted v2 component outcome carries an RFC 3339 `attempted_at`;
  `not_requested` has no fabricated attempt.
- V2 validates recorded state, refresh state, freshness, bounded entries, and
  entry completeness independently for each workspace.
- A v1 normalizer preserves positive facts and uses snapshot `captured_at` as
  coarse observer time with explicit precision.
- V1 fields absent from the v2 vocabulary normalize to `unknown` or
  `not_requested`; they never normalize to current/complete by optimism.
- V1 colocation uses the most specific retained native outcome. A complete Git
  history surface cannot hide an errored jj change graph.
- Shared v1/v2 repository facts remain comparable; v2-only claims expose an
  explicit incomplete boundary.
- Snapshot v1 and v2 deterministic JSON round trips and mixed-version retained
  listing are covered at 100% statement and branch coverage.

## Allowed Write Surfaces

- `docs/contracts/history-snapshot-v1.md`
- new versioned contract documents under `docs/contracts/`
- `src/vcs_tree/models.py`
- one new schema/normalization module under `src/vcs_tree/`
- `src/vcs_tree/ledger.py`
- `src/vcs_tree/__init__.py`
- `tests/test_models.py`
- `tests/test_ledger.py`
- one focused schema/normalization test module under `tests/`
- this task file and `tasks/WORKBOARD.md`

Do not edit native adapters, snapshot orchestration, delta calculation,
predicate/query code, CLI dispatch, the baseline script, or live resource
files.

## Required Fixtures

- Representative complete v1 and v2 Git, jj, and colocated manifests.
- V1 colocated data with Git history complete and jj change-graph error.
- V2 refresh performed/current, refresh failed/stale fallback, and
  not-requested workspace records.
- A mixed v1/v2 snapshot index and unsupported-version documents.

## Completion Evidence

- `scripts/check` passes with 100% statement and branch coverage.
- A temporary ledger opens retained-format v1 snapshots and explicitly
  constructed v2 fixtures without modifying the v1 documents.
- Closure records the public model/normalization API and the exact compatibility
  behavior for absent v2 facts.
- Added `SnapshotEnvelopeV2`, `ObservationOutcome`, working-copy/refresh enums,
  and strict component/workspace validation in `vcs_tree.models` while leaving
  `SnapshotCollector` on `SnapshotEnvelope` v1.
- Added public `parse_snapshot`, `normalize_snapshot`, and
  `component_comparison` APIs. V1 uses `captured_at` with `snapshot` precision;
  absent native/v2-only facts are `unknown` or `not_requested`; colocated
  `jj_history` uses the retained `change_graph.outcome` rather than aggregate
  Git history.
- Added `HistoryLedger.read_snapshot_envelopes()` for validated mixed-version
  listing. Bare legacy index entries remain listable and are skipped by the
  typed manifest view; malformed retained manifests fail closed.
- Read-only validation opened all ten retained machine-local manifests as v1
  at generation 10 without rewriting the index.
- `uv run pytest -q` passed: 251 tests, 100% statement and branch coverage.
- `scripts/check` passed, including Ruff, the full suite, and source/wheel
  builds.

## Decisions

- Owner: Codex `/root`; claimed 2026-08-04.
- This task implements schema v2 rather than an additive v1 extension.
- Rolling temporal clocks remain derived; snapshots store observation outcomes
  and per-attempt time.
- No existing snapshot or immutable object is rewritten.
- V2 repository outcomes require nine independent native components; working
  copy and refresh outcomes remain per workspace.
- Every attempted component and refresh records RFC 3339 observer time.
  `not_requested` carries no fabricated attempt.
- Bounded working-copy evidence records `entries_limit` and
  `entries_truncated`; entry completeness remains independent.

## Next Actions

- Claim `260803-collect-current-working-copy-evidence` or
  `260803-index-temporal-fact-intervals`; both dependencies are now satisfied.
