Filed as: 260803-restore-nested-repository-reporting
FKA:
AKA: recursive history collection; nested repository integration
Legacy index:

keywords: tooling, blocked, nested, implementation, snapshots, cli, ownership

Parent: `260728-movement-snapshot-package`
Depends on: `260803-define-nested-repository-semantics`
Blocks: `260803-test-nested-repository-features`
Blocked by: `260803-define-nested-repository-semantics`
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

- Implementation references the approved nested-discovery note and records
  ownership/deduplication decisions.
- Deterministic nested tree output is demonstrated with parent/child,
  colocated, and alias fixtures.
- `uv run ruff check src/vcs_tree tests` and the 100% coverage suite pass.
- Existing single-root and default scanner compatibility evidence remains green.
