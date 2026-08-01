Filed as: 260804-history-observability-and-index
FKA:
AKA: snapshot listing; history scan progress
Legacy index:

keywords: tooling, ready, cli, observability, progress, snapshots, index

Parent: `260728-movement-snapshot-package`
Depends on: `260801-integrate-history-cli`; `260803-restore-nested-repository-reporting`
Blocks:
Blocked by:
Related: `260801-build-local-history-ledger`; `260803-test-nested-repository-e2e`

# Add History Progress and Snapshot Index Listing

Make long-running history scans observable and expose a supported operator
listing of retained snapshots.

## Acceptance Criteria

- History snapshot collection emits concise phase/progress/status messages on
  stderr while preserving machine-readable JSON on stdout.
- Progress identifies discovery, repository collection, ledger persistence, and
  completion/partial/error states without requiring renderer output parsing.
- A supported CLI command lists retained snapshots in deterministic order with
  snapshot ID, top scan path, capture timestamp, generation, outcome, and store
  identity where available.
- Listing reads the authoritative snapshot index and does not infer history
  from disposable renderer cache files.
- Empty, corrupt, and partially readable indexes produce explicit operator
  outcomes without deleting or rewriting retained history.
- Existing default scanner output and JSON snapshot/delta stdout contracts remain
  compatible.

## Allowed Write Surfaces

- `src/vcs_tree/` CLI, ledger-read, and progress reporting code
- `tests/` and test-only fixtures
- `README.md` for operator command documentation
- this task file and `tasks/WORKBOARD.md`
- No live resource cutover, cache promotion, paging, or repository mutation.

## Completion Evidence

- Capture a long-running/nested scan showing stderr phase updates and clean JSON
  stdout.
- Capture snapshot listing output with top path, timestamp, generation, and
  outcome for repeated snapshots.
- Test missing/corrupt/empty index behavior and preserve the 100% coverage gate.
- `uv run ruff check src/vcs_tree tests` and `uv run pytest -q` pass.
