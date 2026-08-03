Filed as: 260803-persist-jj-change-graph
FKA:
AKA: visible jj graph snapshots; unnamed stack observations
Legacy index:

keywords: tooling, closed, follow-on, jj, changes, visibility, snapshots

Parent: `260803-center-pulse-on-jj-change-graphs`
Depends on: `260803-center-pulse-on-jj-change-graphs`
Blocks: `260803-calculate-jj-change-deltas`
Blocked by:
Related: `260801-implement-jj-history-adapter`; `260801-collect-history-snapshots`

# Persist the Visible jj Change Graph

Carried jj logical-change and visibility observations through collection,
immutable ledger storage, and retained snapshots.

## Closure Evidence

- Persisted jj graph annotations for every observed commit version: logical
  change ID, visibility, exposing authorities, and parent change edges.
- Added per-snapshot `change_graph` membership with visible heads, preserved
  colocated jj-to-Git object mapping, and record-local partial parsing.
- Virtual jj roots retain null identity with no fabricated ordinary metadata.
- `scripts/check` passed: 180 tests, 100% statement and branch coverage, Ruff,
  and package build (the build required the approved network retry).
