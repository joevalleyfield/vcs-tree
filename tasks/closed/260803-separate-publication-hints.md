Filed as: 260803-separate-publication-hints
FKA:
AKA: bookmark publication annotations; ref authority separation
Legacy index:

keywords: tooling, closed, follow-on, jj, bookmarks, refs, publication, colocated

Parent: `260803-center-pulse-on-jj-change-graphs`
Depends on: `260803-center-pulse-on-jj-change-graphs`; `260803-persist-jj-change-graph`; `260803-calculate-jj-change-deltas`
Blocks: `260803-integrate-change-graph-pulse`
Blocked by:
Related: `260806-history-completeness-and-bookmarks`

# Separate Bookmarks as Publication Hints

Represented Git refs and jj bookmarks as distinct publication-related
authorities that annotate, but never define, jj change movement.

## Closure Evidence

- Snapshots retain separate `publication_hints.git_refs` and
  `publication_hints.jj_bookmarks` arrays with local/remote provenance and
  independent collection outcomes; compatibility `refs`/`bookmarks` fields
  remain available.
- Colocated deltas emit separate Git ref and jj bookmark event families and
  completeness warnings. Partial bookmark collection leaves graph movement
  observable and suppresses only bookmark absence/target claims.
- `scripts/check` passed: 187 tests, 100% statement and branch coverage, Ruff,
  and package build.
