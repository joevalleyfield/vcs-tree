# vcs-tree Workboard

> **Status:** Incubating
> **Last Sync:** 2026-07-29

## 0. Manual Triage

- Preserve the resource script and wrapper as the live operational command.
- Treat `260728-movement-snapshot-package` as a requirements parent until the
  snapshot/ref/delta contract is grounded in representative repositories.
- Incubation is successful when the package can later graduate back to
  `Resources/tools/` without consumers depending on the project path.

## 1. Open Queue

- `260728-movement-snapshot-package` — inception; defines package extraction
  and the factual movement model for refs, snapshots, deltas, descriptions,
  and task lifecycle evidence.

## 2. Recent Closures

- `260729-explore-history-surfaces` — grounded the history contract in local
  Git-only, colocated, linked-workspace, and controlled before/after fixtures
  covering fetches, off-current work, tags, ref movement/deletion, jj null
  root, hidden rewrites, divergence, and bookmark conflicts.
- `260729-enforce-total-coverage` — expanded the suite to 47 tests covering
  every measured statement and branch, raised the gate to 100%, and reduced
  successful terminal reports to the aggregate coverage row.
- `260729-package-python-project` — established the installable Python 3.9+
  `src/` package, `vcs-tree` entry point, uv lockfile, pytest branch-coverage
  gate, Ruff checks, build artifacts, and compatibility evidence while leaving
  the standalone baseline and live resource command unchanged.
- `260728-bootstrap-vcs-tree-incubator` — established the independent
  Git+jj-colocated project, byte-identical scanner copy, README, AGENTS,
  inbox, task discipline, root allowlist entry, and smoke evidence without
  redirecting the live resource command.
