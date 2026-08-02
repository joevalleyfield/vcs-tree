Filed as: 260802-enrich-pulse-movement-evidence
FKA:
AKA: commit descriptions; changed-path evidence
Legacy index:

keywords: tooling, ready, pulse, enrichment, git, jj, paths

Parent: `260802-recurring-movement-pulse`
Depends on: `260802-recurring-movement-pulse`
Blocks: `260802-classify-pulse-task-warnings`; `260802-expose-pulse-output-workflow`
Blocked by:
Related: `260802-implement-pulse-orchestration`

# Enrich Pulse Movement Evidence

Collect and retain self-describing evidence for only the history objects named
by factual delta movement.

## Contract

Follow the enrichment scope, native description shape, changed-path vocabulary,
null-root rules, and cost bounds in `planning/recurring-pulse-v1.md`.

## Acceptance Criteria

- Delta-relevant object selection is deterministic and excludes unrelated
  retained history.
- Git and jj/colocated movement records expose native commit IDs, jj change IDs
  when present, parents, short descriptions, distinct author/committer times,
  and exposing refs/bookmarks/visible heads.
- Parent-relative file evidence supports add, modify, delete, native rename,
  native copy, type change, unmerged paths, root commits, and one group per
  merge parent.
- Paths are repository-relative POSIX strings. Separate delete/add results are
  never upgraded to a rename by package logic.
- Immutable path evidence can be reused by later pulses without repeating a
  native query; integrity failures remain isolated from source repositories.
- The jj `00000000` virtual root remains distinct and receives no manufactured
  description, author, committer, changed paths, or timestamp.
- Object and path limits produce explicit partial enrichment and stable
  `limit_exceeded` facts without truncating a purportedly complete list.
- Adapter failure preserves base movement and reports which descriptions or
  path evidence are unavailable.

## Allowed Write Surfaces

- `src/vcs_tree/git_adapter.py`
- `src/vcs_tree/jj_adapter.py`
- `src/vcs_tree/ledger.py`
- `src/vcs_tree/snapshot.py`
- `src/vcs_tree/enrichment.py`
- `tests/test_git_adapter.py`
- `tests/test_jj_adapter.py`
- `tests/test_ledger.py`
- `tests/test_snapshot.py`
- `tests/test_enrichment.py`
- this task file and `tasks/WORKBOARD.md`

Do not edit pulse selection, task semantics, renderers, CLI dispatch, host
documentation, the baseline script, or live resource files.

## Required Fixtures

- Controlled Git history with a root commit, modification, deletion, native
  rename/copy, type change, and two-parent merge.
- Controlled jj/colocated history with a described change, rewritten commit,
  divergent versions, bookmark/visible-head authority, and the null root.
- A ledger replay proving already retained path evidence avoids a second native
  query.
- Command failure and low object/path limits proving partial outcomes without
  false absence or truncation.

## Completion Evidence

- Focused adapter, ledger, snapshot, and enrichment tests covering every native
  status and failure boundary.
- Full `scripts/check` success with 100% statement and branch coverage.
- Task closure records the exact test count plus example Git and colocated
  description/path records.

