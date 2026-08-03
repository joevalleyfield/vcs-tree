# vcs-tree Workboard

> **Status:** jj change-graph contract corrected; persistence ready; public pulse CLI blocked; cutover pending
> **Last Sync:** 2026-08-03

## 0. Manual Triage

- Preserve the resource script and wrapper as the live operational command.
- Treat `260728-movement-snapshot-package` as a requirements parent until the
  snapshot/ref/delta contract is grounded in representative repositories.
- Incubation is successful when the package can later graduate back to
  `Resources/tools/` without consumers depending on the project path.
- Treat closed `260802-recurring-movement-pulse` and
  `planning/recurring-pulse-v1.md` as the requirements source for turning
  snapshots and deltas into factual movement descriptions. The package owns
  pulse semantics; scheduling remains a host concern.
- Ground pulse examples in the retained generation-7-to-8 trial, which detected
  the `vcs-tree` head movement but required a separate jj query to recover its
  commit description and task-closure paths.
- Treat the closed `260803-center-pulse-on-jj-change-graphs` correction as the
  requirements source before public pulse output. Unnamed jj logical-change
  graphs are primary movement; bookmarks are optional publication hints.
- Preserve the completed orchestration, enrichment, and task/warning layers,
  but do not expose or document the public pulse until change-graph integration
  proves bookmark-free jj movement end to end.

## 1. Open Queue

- `260803-center-pulse-on-jj-change-graphs` — closed; correct the contract around
  logical changes, visible versions, unnamed topology, and publication hints.
- `260803-persist-jj-change-graph` — closed; retain visible change membership,
  heads, versions, edges, and authority provenance.
- `260803-calculate-jj-change-deltas` — closed; emit bookmark-independent
  change-version, visibility, and topology movement.
- `260803-separate-publication-hints` — closed; separate Git refs and jj
  bookmarks as non-gating publication annotations.
- `260803-integrate-change-graph-pulse` — closed; adapt completed pulse layers
  before public rendering.
- `260802-implement-pulse-orchestration` — closed; implement the pulse envelope,
  exact comparable-snapshot selection, baseline handling, and orchestration.
- `260802-enrich-pulse-movement-evidence` — closed; add delta-driven native
  descriptions and reusable parent-relative changed-path evidence.
- `260802-classify-pulse-task-warnings` — closed; derive factual task-path
  events and warning lifecycles.
- `260802-expose-pulse-output-workflow` — closed; add CLI rendering, exits, and
  end-to-end evidence.
- `260802-document-recurring-pulse-adapters` — ready; document thin recurring
  host invocation and consumption.
- `260802-recurring-movement-pulse` — closed; settled the v1 operator contract
  and dispatched five bounded implementation tasks.
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
- `260803-test-nested-repository-e2e` — closed; nested CLI workflows,
  aliases, malformed children, and compatibility behavior are covered.
- `260804-history-observability-and-index` — closed; add stderr progress for
  long scans and a supported retained-snapshot listing.
- `260805-delta-presentation-surfaces` — closed; formalize scan-relative,
  signal-first delta summaries with explicit audit and JSON views.
- `260806-history-completeness-and-bookmarks` — closed; make delta completeness
  mode-aware and disclose suppressed history movement.
- `260802-reconcile-workboard` — closed; reconcile task directories and remove
  stale workboard text.
- `260802-precommit-checks` — closed; establish the local format/lint/test/build
  gate required before code commits.
- `260801-calculate-history-deltas` — closed; deterministic factual comparison
  events and completeness gates are implemented and tested.
- `260801-integrate-history-cli` — closed; additive history commands expose
  operator workflows and keep authoritative state out of disposable cache.

## 2. Recent Closures

- `260802-expose-pulse-output-workflow` — added the public pulse CLI, stable
  summary/audit/JSON surfaces, exit behavior, and workflow coverage; 196 tests
  pass with 100% coverage.

- `260803-integrate-change-graph-pulse` — wired jj-first graph deltas through
  enrichment, task-path events, warning lifecycles, and pulse movement states;
  191 tests pass with 100% coverage.

- `260803-separate-publication-hints` — separated Git refs and jj bookmark
  provenance/completeness in snapshots and deltas; partial bookmarks cannot
  hide graph movement; 187 tests pass with 100% coverage.

- `260803-calculate-jj-change-deltas` — added bookmark-independent jj logical
  change/version/topology/visibility and visible-head deltas with partial and
  boundary gates; 186 tests pass with 100% coverage.

- `260803-persist-jj-change-graph` — persisted visible jj change membership,
  version/parent edges, authorities, heads, colocated identity mapping, and
  record-local partial outcomes; 180 tests pass with 100% coverage.

- `260803-center-pulse-on-jj-change-graphs` — made the jj logical-change graph
  the normative primary movement surface, separated publication hints, and
  added bookmark-free/colocated contract fixtures. Documentation-only change;
  no production or retained-state files changed.

- `260802-classify-pulse-task-warnings` — added deterministic task-path event
  classification and stable warning lifecycle semantics; 176 tests pass with
  100% statement and branch coverage.

- `260802-enrich-pulse-movement-evidence` — added bounded immutable-object
  enrichment, parent-relative path evidence, virtual-root handling, and stable
  partial-limit/missing-object warnings; 160 tests pass at 100% coverage.

- `260802-implement-pulse-orchestration` — added validated pulse envelopes,
  baseline/automatic/explicit source selection, partial/error preservation,
  deterministic repository ordering, and 154-test/100%-coverage validation.

- `260802-recurring-movement-pulse` — fixed exact comparison selection,
  delta-driven enrichment, factual task-path and warning lifecycle semantics,
  summary/audit/JSON output, exit behavior, grounded examples, and five bounded
  implementation lanes without changing production code.

- `260802-precommit-checks` — added the repository-local `scripts/check` gate,
  pre-commit policy in AGENTS/README, and complete format/lint/test/build
  validation with 146 tests at 100% coverage.

- `260802-reconcile-workboard` — removed stale continuation text, refreshed the
  sync date, and verified zero open versus 25 closed task artifacts.

- `260806-history-completeness-and-bookmarks` — made delta completeness
  mode-aware for Git refs versus jj bookmarks, surfaced partial/error history
  states, and validated nine actionable gaps in the retained real-world pair
  with 146 tests and 100% coverage.

- `260805-delta-presentation-surfaces` — added scan-relative delta identity,
  signal-first summaries, explicit no-op audit and JSON modes, uncertainty
  warnings, and 144-test/100%-coverage validation.

- `260804-history-observability-and-index` — added stderr phase progress,
  authoritative deterministic snapshot listing, explicit empty/uninitialized/
  corrupt index outcomes, operator documentation, and 140-test/100%-coverage
  validation.

- `260803-test-nested-repository-e2e` — covered nested parent/colocated/sibling
  CLI snapshots and deltas, aliases, default rendering, malformed-child
  preservation, and source immutability; 136 tests pass with 100% coverage.

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
