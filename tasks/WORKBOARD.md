# vcs-tree Workboard

> **Status:** Incubating
> **Last Sync:** 2026-08-01

## 0. Manual Triage

- Preserve the resource script and wrapper as the live operational command.
- Treat `260728-movement-snapshot-package` as a requirements parent until the
  snapshot/ref/delta contract is grounded in representative repositories.
- Incubation is successful when the package can later graduate back to
  `Resources/tools/` without consumers depending on the project path.

## 1. Open Queue

- `260728-movement-snapshot-package` — active; grounded contracts and v1 policy
  defaults are decomposed into the ready implementation queue below.
- `260801-implement-git-history-adapter` — ready after contract models; collect
  selected Git refs, workspaces, annotated tags, and reachable history.
- `260801-implement-jj-history-adapter` — ready after contract models; collect
  jj workspaces, visible heads, bookmarks, conflicts, and null-root history.
- `260801-collect-history-snapshots` — ready after the ledger and both native
  adapters; persist deterministic lightweight manifests over ledger generations.
- `260801-calculate-history-deltas` — ready after contract models and the
  ledger; calculate deterministic factual events with completeness gates.
- `260801-integrate-history-cli` — ready after snapshot and delta delivery;
  expose operator commands and keep authoritative state out of disposable cache.

## 2. Recent Closures

- `260801-build-local-history-ledger` — implemented machine-local authoritative
  state, local writer/repository identity, checksummed immutable objects,
  generations, snapshot index, corruption isolation, 75 tests, and the 100%
  coverage gate; native adapters may now proceed.
- `260801-implement-history-contract-models` — implemented frozen v1 contract
  primitives, deterministic snapshot/delta JSON codecs, 62 tests, and the
  100% coverage gate; dependent implementation tasks may now claim the model
  surface.

- `260801-settle-v1-policy-defaults` — fixed v1 local identity, single-writer
  state, indefinite retention, corruption isolation, explicit incomplete
  ancestry, and inline payload defaults with an immediate cache warning.
- `260729-draft-history-contracts` — produced versioned draft contracts for
  append-only history storage, lightweight topology snapshots, completeness
  gates, and factual movement deltas with parse-checked examples.
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
