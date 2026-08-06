Filed as: 260806-operationalize-query-index
FKA:
AKA: warm temporal queries; observable derived-index rebuild
Legacy index:

keywords: tooling, closed, history, query, performance

Parent: `260806-support-review-consumers`
Related: `260803-index-temporal-fact-intervals`;
  `260804-history-observability-and-index`

# Operationalize the Temporal Query Index

Make several factual questions over one accepted observation observable,
reusable, and safe for recurring playbook execution.

## Completion Evidence

- Measured the real retained corpus at `~/.local/state/vcs-tree`: 13 snapshots,
  68 repositories, 92,896 objects, 202,452 facts, and 875 components. A cold
  rebuild took 58.372 seconds; cache reuse avoids repeating that rebuild.
- Added disposable historical-index caching keyed by hashed store ID and source
  generation, with safe stale, malformed, missing, and unwritable fallback.
- Added retained-snapshot and per-generation progress callbacks routed to query
  stderr, keeping JSON stdout machine-clean.
- Made observation capture explicit with `--capture`; default queries reuse
  retained evidence and do not observe. Capture cannot combine with a snapshot.
- Added deterministic JSON query batches. Multiple predicates reuse one index
  and evaluation timestamp, while single-query output remains compatible.
- `scripts/check` passes: 389 tests, 100% statement and branch coverage, Ruff,
  and `uv build`.

## Decisions

- Historical cache entries are disposable and valid only for their store ID and
  source generation; authoritative snapshots remain the rebuild source.
- Batch output uses a distinct `vcs-tree.history-query-batch` schema and does
  not alter the existing single-query result shape.

## Allowed Write Surfaces

- ledger/query/CLI modules under `src/vcs_tree/`
- focused temporal-query tests under `tests/`
- query workflow and temporal-index docs/contracts
- this task and `tasks/WORKBOARD.md`
