Filed as: 260802-end-to-end-workflow-testing
FKA:
AKA: operator workflow smoke; package CLI acceptance
Legacy index:

keywords: testing, ready, e2e, workflow, cli, smoke, colocated

Parent: `260728-movement-snapshot-package`
Depends on: `260802-feature-behavioral-testing`
Blocks:
Blocked by:
Related: `260801-integrate-history-cli`; `260801-fix-jj-template-syntax`

# End-to-End History Workflow Testing

Exercise the installed package CLI as an operator would, using controlled
temporary repositories and a real colocated Git/jj fixture where available.

## Goal

Prove that initialization, inspection, repeated snapshot capture, and delta
comparison work together through the installed entry point and preserve the
machine-local state boundary.

## Acceptance Criteria

- A fresh state root can be initialized and inspected, with store identity,
  writer policy, resolved state/config/cache locations, and cloud-sync warning
  visible in output.
- A controlled Git fixture can produce two snapshots and a delta showing a
  factual ref/workspace/history change without mutating the source repository.
- A controlled colocated fixture exercises Git refs together with jj
  workspaces, bookmarks, visible heads, and history; incomplete native
  surfaces produce explicit partial/error output rather than false movement.
- Missing snapshots, wrong writer/state, corrupted control files, and partial
  collection produce documented non-zero outcomes with actionable JSON.
- The legacy default scan invocation remains behavior-compatible, and the live
  `../../Resources/tools/` script/wrapper are not modified.
- The workflow is runnable from a clean checkout using `uv run vcs-tree ...`.

## Allowed Write Surfaces

- `tests/`
- test-only repository fixtures under `tests/fixtures/`
- this task file and `tasks/WORKBOARD.md` for lifecycle evidence
- No production source changes, live resource changes, cache promotion, or
  external repository writes.

## Completion Evidence

- Include the exact operator command sequence and captured outcome summary.
- Record fixture paths and prove source VCS state is unchanged before/after.
- `uv run pytest -q` passes with the configured 100% coverage gate.
- `uv run ruff check src/vcs_tree tests` passes.
- A real colocated smoke is recorded separately from deterministic fixtures.
