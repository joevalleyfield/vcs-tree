Filed as: 260803-test-mechanical-query-workflow
FKA:
AKA: query black-box acceptance; review-evidence e2e
Legacy index:

keywords: testing, blocked, e2e, query, compatibility, git, jj

Parent: `260803-define-backlog-review-pressure`
Depends on: `260803-collect-current-working-copy-evidence`; `260803-index-temporal-fact-intervals`; `260803-evaluate-mechanical-predicates`; `260803-expose-mechanical-query-cli`
Blocks:
Blocked by: `260803-collect-current-working-copy-evidence`;
  `260803-index-temporal-fact-intervals`;
  `260803-evaluate-mechanical-predicates`;
  `260803-expose-mechanical-query-cli`
Related: `260802-end-to-end-workflow-testing`; `260802-feature-behavioral-testing`

# Test the Mechanical Query Workflow End to End

Exercise snapshot v2, working-copy refresh/fallback, temporal intervals,
predicate evaluation, and public query rendering through the installed command
without changing production behavior.

## Acceptance Criteria

- A controlled Git-unborn repository with changed paths produces factual
  unborn/current evidence but no semantic initial-commit conclusion.
- A controlled jj repository with nonempty `@` rooted only at the virtual root
  is normally refreshed, records current path evidence, and satisfies the
  corresponding factual predicate.
- A controlled refresh failure falls back to recorded `@`, preserves useful
  facts, reports stale freshness, and makes freshness-dependent predicates
  indeterminate.
- Repeated complete observations create confirmations; supported disappearance
  creates a tombstone; reappearance opens a new interval.
- Repeated partial observations reconfirm positive facts without tombstoning
  omissions or advancing component completeness.
- A mixed retained v1/v2 store is queryable without rewriting v1 snapshots.
  Shared facts compare; v2-only claims over v1 evidence are explicitly
  incomplete.
- A colocated Git-history success plus jj-history error remains incomplete for
  jj graph predicates.
- Summary, audit, and JSON agree on counts/evidence and use documented exits.
- Existing snapshot, delta, pulse, list, and default scanner black-box workflows
  continue to pass.

## Allowed Write Surfaces

- `tests/`
- test-only fixtures under `tests/fixtures/`
- operator examples under `docs/`
- this task file and `tasks/WORKBOARD.md`

No production source, contract semantics, live resource files, external
repositories, or retained machine-local ledger may be modified.

## Required Scenarios

- Git unborn changed/clean/error.
- jj normal refresh, empty/nonempty root-parented `@`, conflict, and stale
  fallback.
- Fact confirmation/tombstone/reappearance and partial recovery.
- Mixed v1/v2 compatibility and masked colocated native error.
- Inline/file/stdin predicates and all output/exit modes.

## Completion Evidence

- Installed-entry-point black-box tests cover the complete workflow in
  temporary repositories and state roots.
- The test suite proves source fixtures receive only the explicitly permitted
  jj working-copy snapshot side effect.
- `scripts/check` passes with 100% statement and branch coverage and successful
  package build.
- Closure records total tests and representative command/output assertions.

## Next Actions

- Claim after the public query workflow closes.
