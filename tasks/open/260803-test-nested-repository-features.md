Filed as: 260803-test-nested-repository-features
FKA:
AKA: nested discovery feature matrix
Legacy index:

keywords: testing, blocked, nested, feature, discovery, deduplication, boundaries

Parent: `260728-movement-snapshot-package`
Depends on: `260803-restore-nested-repository-reporting`
Blocks: `260803-test-nested-repository-e2e`
Blocked by: `260803-restore-nested-repository-reporting`
Related: `260803-define-nested-repository-semantics`

# Test Nested Repository Features

Add focused behavioral tests for nested repository discovery, ownership,
deduplication, boundaries, and deterministic reporting.

## Acceptance Criteria

- Feature tests cover scan-root, nested parent/child, Git-only, jj-only, and
  colocated roots.
- Tests cover path/symlink aliases, repeated observations, stable keys, and
  deterministic ordering without collapsing distinct roots.
- Tests cover inaccessible/malformed child roots and prove sibling/parent
  observations survive explicit child errors.
- Tests prove existing single-root behavior, renderer cache behavior, and
  package contracts remain unchanged.
- The full suite retains the 100% statement and branch coverage gate.

## Allowed Write Surfaces

- `tests/`
- test-only fixtures under `tests/fixtures/`
- this task file and `tasks/WORKBOARD.md`
- No production source, live resource, or external repository changes.

## Completion Evidence

- A feature-to-rule matrix identifies each nested semantic and test.
- `uv run pytest -q` and `uv run ruff check src/vcs_tree tests` pass.
- Tests include before/after source-state checks for read-only discovery.
