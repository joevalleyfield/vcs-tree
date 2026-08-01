Filed as: 260803-restore-nested-repository-reporting
FKA:
AKA: recursive history collection; nested repository integration
Legacy index:

keywords: tooling, closed, nested, implementation, snapshots, cli, ownership

Parent: `260728-movement-snapshot-package`
Depends on: `260803-define-nested-repository-semantics`
Blocks: `260803-test-nested-repository-features`
Blocked by:
Related: `260801-integrate-history-cli`; `260801-collect-history-snapshots`

# Restore Nested Repository Reporting

Extend the package history workflow to discover and report all eligible nested
Git/jj repositories according to the approved discovery semantics.

## Acceptance Criteria

- The history snapshot workflow can scan a directory tree and emit one
  deterministic repository observation per owned root, including nested
  parent/child repositories.
- A root containing both `.git` and `.jj` is collected once as colocated;
  distinct roots receive distinct local ledger keys and snapshot entries.
- Repeated scans, path aliases, and symlink aliases do not duplicate logical
  repository records or overwrite unrelated parent/child records.
- Discovery order, repository ordering, relative display paths, and persisted
  manifest ordering are deterministic.
- Inaccessible or malformed child roots produce explicit collection outcomes
  while preserving successfully observed siblings and parents.
- Existing single-repository snapshot commands and the legacy default scanner
  remain compatible; no live resource cutover occurs.

## Allowed Write Surfaces

- `src/vcs_tree/` discovery, snapshot, and CLI integration code
- `tests/` and test-only fixtures
- `README.md` only for operator-facing nested-scan usage
- this task file and `tasks/WORKBOARD.md`
- Do not edit `../../Resources/tools/` or add paging/export/shared identity.

## Completion Evidence

- Added canonical recursive discovery in `snapshot.py`, exported as
  `discover_repository_roots`, with metadata pruning, no symlink traversal,
  explicit discovery outcomes, and deterministic canonical ordering.
- Extended snapshot collection from one root to a tree of owned roots while
  preserving the single-root path. Parent/child roots receive distinct local
  keys; Git+jj markers at one root produce one colocated record.
- Added relative repository paths and merged colocated Git worktree/jj
  workspace relationships by canonical workspace path.
- Added nested discovery and publication tests covering canonical aliases,
  colocated ownership, non-directory/error outcomes, deterministic ordering,
  stable keys, and scan completeness.
- Real CLI smoke over a temporary Git parent plus colocated jj child reported
  `[('.', 'git', 'repo-0001'), ('child', 'colocated', 'repo-0002')]` with a
  complete scan outcome.
- `uv run ruff check src/vcs_tree tests` passes.
- `uv run pytest -q`: 130 tests, 100.00% coverage.
- Existing single-root, default scanner, and live resource compatibility
  surfaces remain unchanged.
