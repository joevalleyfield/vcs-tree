Filed as: 260803-calculate-jj-change-deltas
FKA:
AKA: unnamed stack deltas; logical change movement
Legacy index:

keywords: tooling, closed, follow-on, jj, delta, rewrite, topology, visibility

Parent: `260803-center-pulse-on-jj-change-graphs`
Depends on: `260803-center-pulse-on-jj-change-graphs`; `260803-persist-jj-change-graph`
Blocks: `260803-separate-publication-hints`; `260803-integrate-change-graph-pulse`
Blocked by:
Related: `260801-calculate-history-deltas`

# Calculate jj Logical-Change and Stack Deltas

Made unnamed jj change movement a first-class factual delta independent of
bookmark presence.

## Closure Evidence

- Added bookmark-independent `change_versions_changed` events for introduced,
  rewritten, divergent, resolved, topology-changed, and visibility-lost graph
  states, retaining every old/new commit ID.
- Added visible-head add/remove events with affected logical change IDs and
  enriched workspace-head events with old/new change IDs.
- Partial graph outcomes preserve positive movement and suppress unsupported
  absence claims; incomplete topology is indeterminate. Existing Git/ref
  behavior remains covered.
- `scripts/check` passed: 186 tests, 100% statement and branch coverage, Ruff,
  and package build.
