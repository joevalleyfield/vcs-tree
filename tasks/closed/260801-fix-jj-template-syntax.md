Filed as: 260801-fix-jj-template-syntax
FKA:
AKA: jj template separator compatibility
Legacy index:

keywords: tooling, closed, jj, compatibility, bugfix

Parent: `260728-movement-snapshot-package`
Depends on: `260801-implement-jj-history-adapter`
Blocks:
Blocked by:
Related: `260801-collect-history-snapshots`

# Fix jj Template Separator Syntax

Use valid quoted jj template string literals for NUL-delimited workspace,
bookmark, and visible-head records.

## Evidence
- A real `history snapshot` against `/Users/tim/Documents` reported jj template
  parse errors for all three surfaces.
- Git collection continued, but colocated jj workspaces/bookmarks/visible-heads
  were unavailable.
- Updated templates to use quoted separators and current jj `WorkspaceRef` and
  `CommitRef` methods (`self.root()`, `self.target()`, `self.normal_target()`,
  and target lists).
- Real colocated smoke now reports complete jj workspaces, bookmarks, and
  visible heads with one workspace observed.
- `uv run pytest -q`: 120 tests, 100.00% coverage; Ruff passes.
