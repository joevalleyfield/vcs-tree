Filed as: 260803-test-nested-repository-features
FKA:
AKA: nested discovery feature matrix
Legacy index:

keywords: testing, closed, nested, feature, discovery, deduplication, boundaries

Parent: `260728-movement-snapshot-package`
Depends on: `260803-restore-nested-repository-reporting`
Blocks: `260803-test-nested-repository-e2e`
Blocked by:
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

- Expanded `tests/test_nested_snapshot.py` into a feature-to-rule matrix for
  scan-root, nested parent/child, Git-only, jj-only, colocated, alias,
  repeated-scan, deterministic-order, stable-key, and discovery-error cases.
- Tests prove a discovery error preserves parent and sibling records, and that
  source marker state is unchanged before/after repeated collection.
- `uv run pytest -q`: 133 tests, 100.00% coverage.
- `uv run ruff check src/vcs_tree tests` passes.
- The dependent nested E2E task remains the next validation slice.
