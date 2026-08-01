Filed as: 260803-test-nested-repository-e2e
FKA:
AKA: nested repository operator workflow
Legacy index:

keywords: testing, closed, nested, e2e, cli, workflow, smoke

Parent: `260728-movement-snapshot-package`
Depends on: `260803-test-nested-repository-features`
Blocks:
Blocked by:
Related: `260802-end-to-end-workflow-testing`; `260801-integrate-history-cli`

# Test Nested Repository End-to-End Workflow

Exercise nested Git/jj discovery through the installed CLI and confirm the
operator-visible output and persisted snapshots match the feature contract.

## Acceptance Criteria

- A temporary tree containing nested parent/child Git repositories can be
  initialized, inspected, snapshotted, and compared through `uv run vcs-tree`.
- A colocated child and a separate nested sibling are each represented once,
  with stable distinct repository keys and deterministic report order.
- Alias paths and an unreadable child produce no duplicate or false deletion;
  explicit partial/error outcomes preserve usable sibling observations.
- The default renderer invocation still reports nested repositories as before,
  with disposable cache behavior unchanged; live resource files are untouched.
- A real colocated nested smoke is recorded separately from deterministic
  temporary fixtures when jj is available.

## Allowed Write Surfaces

- `tests/` and test-only repository fixtures
- this task file and `tasks/WORKBOARD.md`
- No production source, live resource, cache promotion, or external repository
  writes.

## Completion Evidence

- Added black-box CLI coverage for a temporary Git parent, colocated jj child,
  and separate nested Git sibling: `history init`, `history snapshot` twice,
  `history delta --from ID --to ID`, and the default renderer invocation.
- Verified deterministic records `[('.', 'git'), ('child', 'colocated'),
  ('sibling', 'git')]`, stable keys through a symlink alias, and unchanged
  parent `HEAD` during discovery/snapshot collection.
- Verified malformed nested `.git` children preserve the parent and return an
  explicit child identity error. A minimal Git adapter boundary check prevents
  upward parent-root attribution.
- Real nested colocated jj smoke is covered when jj is available; the
  deterministic fixture remains independent of external repositories.
- `uv run pytest -q`: 136 tests, 100.00% coverage.
- `uv run ruff check src/vcs_tree tests` passes.
