Filed as: 260803-separate-publication-hints
FKA:
AKA: bookmark publication annotations; ref authority separation
Legacy index:

keywords: tooling, blocked, follow-on, jj, bookmarks, refs, publication, colocated

Parent: `260803-center-pulse-on-jj-change-graphs`
Depends on: `260803-center-pulse-on-jj-change-graphs`; `260803-persist-jj-change-graph`; `260803-calculate-jj-change-deltas`
Blocks: `260803-integrate-change-graph-pulse`
Blocked by: stable jj change delta and authority model
Related: `260806-history-completeness-and-bookmarks`

# Separate Bookmarks as Publication Hints

Represent Git refs and jj bookmarks as distinct publication-related authorities
that annotate, but never define, jj change movement.

## Acceptance Criteria

- Colocated snapshots and deltas retain separate completeness and provenance for
  Git refs, local jj bookmarks, tracked bookmarks, and observed remote bookmarks.
- Local bookmark appearance is labeled as intent/hint rather than proof of
  publication; remote observation is reported factually with collection time
  and without claiming server freshness.
- Bookmark target changes observed in both snapshots remain reportable even if
  an unrelated bookmark record is unavailable.
- Bookmark creation/deletion and other absence claims require complete bookmark
  membership for the relevant authority and scope.
- Conflicted bookmarks retain removed and added target sets and map every
  available target to its logical change/commit version.
- Bookmark collection partial/error states affect publication hints only. They
  do not suppress change-version, topology, workspace, visible-head, description,
  or changed-path movement.
- Git-only ref behavior remains compatible and jj-only/colocated behavior has
  explicit regression coverage.

## Allowed Write Surfaces

- `src/vcs_tree/snapshot.py`
- `src/vcs_tree/delta.py`
- `src/vcs_tree/models.py` only for authority records fixed by the parent
- `tests/test_snapshot.py`
- `tests/test_delta.py`
- `tests/test_jj_adapter.py` only for publication-authority fixtures
- this task file and `tasks/WORKBOARD.md`

Do not edit pulse rendering, scheduler adapters, task-path semantics, or live
resource files.

## Completion Evidence

- A matrix covers Git-only, jj-only, and colocated local/tracked/remote/conflict
  cases under complete and partial collection.
- Tests prove partial bookmarks cannot hide or downgrade otherwise complete
  unnamed-stack movement.
- Full `scripts/check` success with 100% statement and branch coverage.

