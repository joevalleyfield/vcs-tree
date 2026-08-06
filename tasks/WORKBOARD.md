# vcs-tree Workboard

> **Status:** Mechanical predicates complete; query CLI ready; cutover pending
> **Last Sync:** 2026-08-06

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
- The public pulse now incorporates the completed change-graph integration,
  enrichment, and task/warning layers. Continue dogfooding migration boundaries
  and recurring-warning behavior before cutover.
- Treat `260803-define-backlog-review-pressure` and
  `planning/mechanical-review-evidence-v1.md` as the corrected requirements
  source for factual state, elapsed observer clocks, and evidence-completeness
  predicates used by intelligent review consumers.
- `vcs-tree` does not rank review pressure, decide health/priority, retain
  dispositions, or emit semantic reasons such as `initial_commit_due`. It
  supplies Git-unborn or jj-root-parented working-copy facts and completeness;
  consumers own the conclusion and any direct follow-up observation.
- Collection is non-destructive rather than universally non-mutating. Normal jj
  working-copy snapshotting is a permitted, reported observation side effect;
  failed refresh falls back to recorded `@` facts with stale/indeterminate
  filesystem freshness.
- Temporal evidence is component- and fact-specific: attempts and completeness
  belong to semantic collection components, while atomic facts retain
  confirmation intervals and explicit tombstones.
- The planning parent, snapshot-v2 schema, current working-copy collection,
  temporal indexing, and mechanical predicate evaluation are closed. Query CLI
  integration is ready, followed by black-box workflow validation.

## 1. Open Queue

<!-- WORKBOARD:OPEN:START -->
- `260806-correct-movement-evidence` — Ensure pulse and delta report repository-state transitions rather than identical states or facts that merely became observable after incomplete collection.
- `260806-group-movement-evidence` — Present factual movement as compact repository/change groups with descriptions, paths, and completeness so consumers do not reconstruct meaning from repeated low-level labels.
- `260806-operationalize-query-index` — Make several factual questions over one accepted observation observable, reusable, and safe for recurring playbook execution.
- `260806-project-review-candidate-evidence` — Expose a supported factual projection for current-workspace review questions without emitting review conclusions or requiring private-ledger joins.
- `260806-support-review-consumers` — Turn the 2026-08-06 playbook trial into factual, supported affordances that let an external reviewer spend attention on domain judgment rather than ledger mechanics.
<!-- WORKBOARD:OPEN:END -->

## 2. Recent Closures

<!-- WORKBOARD:CLOSED:START -->
- `260806-history-completeness-and-bookmarks` — Make incomplete-history reports explainable and mode-aware so downstream dispatchers can distinguish tool gaps from repository movement.
- `260805-delta-presentation-surfaces` — Separate operator-facing movement summaries from complete machine-readable delta documents while retaining an auditable way to inspect verified no-ops.
- `260804-history-observability-and-index` — Make long-running history scans observable and expose a supported operator listing of retained snapshots.
- `260803-version-mechanical-evidence-schema` — Implement the snapshot-v2 model and v1 compatibility boundary required by `planning/mechanical-review-dispatch.md` without changing native collection commands or adding predicate e...
- `260803-test-nested-repository-features` — Add focused behavioral tests for nested repository discovery, ownership, deduplication, boundaries, and deterministic reporting.
- `260803-test-nested-repository-e2e` — Exercise nested Git/jj discovery through the installed CLI and confirm the operator-visible output and persisted snapshots match the feature contract.
- `260803-test-mechanical-query-workflow` — Exercise snapshot v2, working-copy refresh/fallback, temporal intervals, predicate evaluation, and public query rendering through the installed command without changing production ...
- `260803-sync-workboard` — Adapt the proven task-inventory synchronizer from `../toas` so this repository's Open Queue is generated from `tasks/open/`, while recent closures and the relationship view remain ...
<!-- WORKBOARD:CLOSED:END -->

### Curated closure evidence

- `260803-evaluate-mechanical-predicates` — added the typed history-query v1
  model and an evidence-preserving evaluator for fact state, elapsed clocks,
  component boundaries, and three-valued boolean composition; a golden result
  plus Git-unborn/jj-root fixtures pass with 374 tests at 100% coverage.

- `260803-index-temporal-fact-intervals` — added a rebuildable canonical index
  with component clocks, stable atomic fact keys, confirmation/tombstone/
  reappearance episodes, conservative mixed-v1/v2 handling, continuity
  boundaries, and automatic derived-state recovery; the real ten-generation
  corpus projected 18,953 facts, and 307 tests pass at 100% coverage.

- `260803-collect-current-working-copy-evidence` — switched production to
  snapshot v2, added non-locking Git status and jj refresh/fallback/path
  evidence, kept linked-workspace freshness explicit, corrected the real jj
  history template, and passed a jj 0.42 controlled trial plus 288 tests at
  100% statement and branch coverage.

- `260803-version-mechanical-evidence-schema` — added explicit snapshot-v2
  validation, conservative v1/v2 normalization, native component boundaries,
  mixed-version retained reads, and a documented working-copy evidence shape;
  all ten retained v1 manifests open unchanged and 251 tests pass at 100%
  statement and branch coverage.

- `260803-define-backlog-review-pressure` — corrected the objective from
  package-owned pressure to mechanical review evidence, selected snapshot v2,
  grounded gaps in ten retained generations/68 repositories and a real sandbox
  fallback, and dispatched six bounded engineering tasks.

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
