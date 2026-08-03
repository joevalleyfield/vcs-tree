Filed as: 260803-calculate-jj-change-deltas
FKA:
AKA: unnamed stack deltas; logical change movement
Legacy index:

keywords: tooling, blocked, follow-on, jj, delta, rewrite, topology, visibility

Parent: `260803-center-pulse-on-jj-change-graphs`
Depends on: `260803-center-pulse-on-jj-change-graphs`; `260803-persist-jj-change-graph`
Blocks: `260803-separate-publication-hints`; `260803-integrate-change-graph-pulse`
Blocked by: persisted jj change-graph observations
Related: `260801-calculate-history-deltas`

# Calculate jj Logical-Change and Stack Deltas

Make unnamed jj change movement a first-class factual delta independent of
bookmark presence.

## Acceptance Criteria

- Delta groups visible commit versions by stable jj `change_id` and reports the
  parent contract's version, visibility, and topology events deterministically.
- Rewrites retain old and new commit IDs; divergent visible versions are not
  collapsed; rebases distinguish changed topology from a new logical change.
- Visible-head and workspace-head movement identifies the affected logical
  changes even when no bookmark names any part of the stack.
- Positive facts supported by valid records remain observable under partial
  collection. Visibility-loss, deletion, abandonment, or other absence claims
  require the exact completeness boundary fixed by the contract.
- History-boundary uncertainty changes ancestry/topology classification to
  unknown only where needed; it does not erase observed IDs or version changes.
- Git-only behavior and existing factual ref/workspace events remain compatible.
- Repository and global partial outcomes enumerate suppressed event families
  without turning warning-only events into observed movement.

## Allowed Write Surfaces

- `src/vcs_tree/delta.py`
- `src/vcs_tree/models.py` only for contract records fixed by the parent
- `tests/test_delta.py`
- `tests/test_feature_behavior.py`
- this task file and `tasks/WORKBOARD.md`

Do not edit collectors, ledger persistence, pulse presentation, scheduling, or
live resource files.

## Required Fixtures

- Bookmark-free stack growth, rewrite, rebase, divergence, hiding, and sibling
  stack introduction across retained snapshots.
- Partial graph membership where one positive version change remains provable
  but visibility loss is not.
- Shallow/unknown ancestry with observed version IDs and unknown relation.
- Git-only regression fixtures proving unchanged event behavior.

## Completion Evidence

- Event-table tests cover every vocabulary value and completeness gate.
- A real temporary jj repository demonstrates unnamed movement without
  bookmarks.
- Full `scripts/check` success with 100% statement and branch coverage.

