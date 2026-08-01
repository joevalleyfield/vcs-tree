# vcs-tree Workboard

> **Status:** Incubation implementation complete; cutover pending
> **Last Sync:** 2026-08-01

## 0. Manual Triage

- Preserve the resource script and wrapper as the live operational command.
- Treat `260728-movement-snapshot-package` as a requirements parent until the
  snapshot/ref/delta contract is grounded in representative repositories.
- Incubation is successful when the package can later graduate back to
  `Resources/tools/` without consumers depending on the project path.

## 1. Open Queue

- `260728-movement-snapshot-package` — closed; v1 package, ledger, adapters,
  snapshots, deltas, and additive CLI are implemented and validated.
- `260802-feature-behavioral-testing` — closed; component-level behavior and
  failure policies are covered without production changes.
- `260802-end-to-end-workflow-testing` — closed; installed CLI workflows,
  controlled Git/colocated fixtures, error paths, and compatibility behavior
  are covered.
- `260803-define-nested-repository-semantics` — closed; recursive discovery,
  ownership, deduplication, and boundary rules are documented for coding.
- `260803-restore-nested-repository-reporting` — closed; recursive history
  discovery and nested/colocated snapshot reporting are implemented.
- `260803-test-nested-repository-features` — closed; nested discovery behavior
  and failure boundaries are covered.
  validate feature behavior and failure boundaries.
- `260803-test-nested-repository-e2e` — blocked by nested feature tests;
  validate the installed operator workflow and compatibility behavior.
- `260804-history-observability-and-index` — ready; add stderr progress for
  long scans and a supported retained-snapshot listing.
- `260801-calculate-history-deltas` — closed; deterministic factual comparison
  events and completeness gates are implemented and tested.
- `260801-integrate-history-cli` — closed; additive history commands expose
  operator workflows and keep authoritative state out of disposable cache.

## 2. Recent Closures

- `260803-test-nested-repository-features` — covered Git/jj/colocated roots,
  nested ownership, aliases, repeated stable keys, discovery errors, ordering,
  and read-only behavior; 133 tests pass with 100% coverage.

- `260803-restore-nested-repository-reporting` — added canonical recursive
  history discovery, parent/child ownership, colocated deduplication, merged
  workspace/worktree relationships, and nested CLI smoke coverage; 130 tests
  pass with 100% coverage.

- `260803-define-nested-repository-semantics` — documented canonical-root
  ownership, colocated deduplication, parent/child reporting, symlink and
  metadata boundaries, deterministic ordering, and explicit scan outcomes.

- `260802-end-to-end-workflow-testing` — added black-box init/inspect/snapshot/
  delta workflow coverage, corrupt/missing-state errors, default scanner
  compatibility, and colocated jj smoke; 127 tests pass with 100% coverage.

- `260802-feature-behavioral-testing` — added focused contract, ledger,
  adapter, and delta behavior tests; 124 tests pass with 100% coverage.

- `260801-fix-jj-template-syntax` — corrected quoted NUL separators and current
  jj template methods; real colocated snapshot smoke now observes complete jj
  workspace, bookmark, and visible-head surfaces.

- `260801-fix-cli-entry-dispatch` — fixed installed-entry-point argument
  dispatch so `uv run vcs-tree history --help` and history subcommands reach
  the additive history parser; 120 tests and 100% coverage.

- `260801-integrate-history-cli` — added explicit init/inspect/snapshot/delta
  commands, machine-local location warnings, compatibility-preserving default
  scanning, and 119-test/100%-coverage validation.

- `260801-calculate-history-deltas` — implemented deterministic snapshot
  comparison, ancestry movement classification, remote/off-current history
  events, and fail-closed completeness gates with 113 tests and 100% coverage;
  CLI integration is now next.

- `260801-collect-history-snapshots` — implemented generation-backed snapshot
  orchestration, stable local keys, colocated Git/jj merging, object
  deduplication, and manifest indexing with 108 tests and 100% coverage; delta
  calculation is now next.
- `260801-implement-jj-history-adapter` — implemented read-only jj workspace,
  bookmark, visible-head, commit/change, conflict, and virtual-root collection
  with 101 tests and 100% coverage; snapshot orchestration is now next.
- `260801-implement-git-history-adapter` — implemented read-only Git identity,
  worktree, selected-ref, tag, reachable-history, and shallow-boundary
  collection with 90 tests and 100% coverage; jj adapter remains next.
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
