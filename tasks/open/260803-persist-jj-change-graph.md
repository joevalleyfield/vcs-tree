Filed as: 260803-persist-jj-change-graph
FKA:
AKA: visible jj graph snapshots; unnamed stack observations
Legacy index:

keywords: tooling, ready, follow-on, jj, changes, visibility, snapshots

Parent: `260803-center-pulse-on-jj-change-graphs`
Depends on: `260803-center-pulse-on-jj-change-graphs`
Blocks: `260803-calculate-jj-change-deltas`
Blocked by:
Related: `260801-implement-jj-history-adapter`; `260801-collect-history-snapshots`

# Persist the Visible jj Change Graph

Carry the jj logical-change and visibility observations required by the revised
contract through collection, immutable ledger storage, and retained snapshots.

## Acceptance Criteria

- Each retained jj observation preserves logical `change_id`, every visible
  commit version, parent commit/change edges, and the authorities that expose a
  version.
- Visible heads and workspace heads survive snapshot serialization and reload;
  unnamed and off-workspace visible stacks do not require bookmarks.
- Per-snapshot membership is sufficient to compare visibility across
  generations while immutable object records remain deduplicated.
- Colocated snapshots preserve the mapping between jj change/commit identity and
  Git object identity without collapsing Git refs and jj bookmarks into one
  completeness authority.
- Partial collection retains every valid record and identifies the failed stage
  or record boundary. One malformed record does not erase unrelated valid
  changes.
- Null-root identity remains `00000000`/virtual-root evidence and carries no
  fabricated ordinary metadata.
- Existing snapshot schema compatibility is preserved or migrated according to
  the parent contract's explicit decision.

## Allowed Write Surfaces

- `src/vcs_tree/jj_adapter.py`
- `src/vcs_tree/snapshot.py`
- `src/vcs_tree/models.py`
- `src/vcs_tree/ledger.py` only if snapshot membership requires storage support
- `tests/test_jj_adapter.py`
- `tests/test_snapshot.py`
- `tests/test_models.py`
- `tests/test_ledger.py` only for changed storage behavior
- this task file and `tasks/WORKBOARD.md`

Do not implement delta, pulse rendering, task classification, scheduling, or
live resource cutover behavior.

## Required Fixtures

- A jj-only repository with two unnamed visible stacks and no bookmarks.
- One logical change with multiple visible commit versions.
- A rebase changing parent topology while retaining logical change identity.
- A colocated repository with distinct Git refs, local jj bookmarks, remote jj
  bookmarks, visible heads, and workspace heads.
- Partial bookmark/record collection proving valid change-graph observations
  remain present.

## Completion Evidence

- Round-trip snapshot assertions retain the complete fixture graph and
  authority distinctions.
- Failure tests prove record-local preservation and explicit partial outcomes.
- Full `scripts/check` success with 100% statement and branch coverage.
