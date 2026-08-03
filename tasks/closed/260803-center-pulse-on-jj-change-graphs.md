Filed as: 260803-center-pulse-on-jj-change-graphs
FKA:
AKA: jj-first pulse semantics; unnamed change stacks
Legacy index:

keywords: planning, closed, pulse, jj, changes, stacks, topology, contract

Parent: `260802-recurring-movement-pulse`
Depends on:
Blocks: `260803-persist-jj-change-graph`; `260803-calculate-jj-change-deltas`; `260803-separate-publication-hints`; `260803-integrate-change-graph-pulse`; `260802-expose-pulse-output-workflow`
Blocked by:
Related: `260806-history-completeness-and-bookmarks`

# Center Pulse on jj Change Graphs

Corrected the pulse contract before public output. In jj repositories,
logical changes and their visible graph are the primary movement surface;
bookmarks are optional publication hints.

## Closure Evidence

- Updated `planning/recurring-pulse-v1.md`,
  `docs/contracts/history-snapshot-v1.md`, and
  `docs/contracts/history-delta-v1.md` with normative jj-first graph rules.
- Added event/state vocabulary covering introduced, rewritten, divergent,
  topology-changed, resolved, visibility gain/loss, and publication-hint
  uncertainty, plus bookmark-free and colocated before/after fixtures.
- `git diff --check` passed; no source, test, ledger, or live-resource files
  changed. The next task is `260803-persist-jj-change-graph`.
