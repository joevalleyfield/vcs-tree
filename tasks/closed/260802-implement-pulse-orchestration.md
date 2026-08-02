Filed as: 260802-implement-pulse-orchestration
FKA:
AKA: pulse selector; pulse envelope
Legacy index:

keywords: cli, tooling, closed, pulse, orchestration, snapshots, contract

Parent: `260802-recurring-movement-pulse`
Depends on: `260802-recurring-movement-pulse`
Blocks: `260802-classify-pulse-task-warnings`; `260802-expose-pulse-output-workflow`
Blocked by:
Related: `260802-enrich-pulse-movement-evidence`

# Implement Pulse Orchestration and Comparison Selection

Implement the package-level pulse envelope and orchestration service without
adding the public CLI renderer yet.

## Contract

Follow `planning/recurring-pulse-v1.md`. Resolve the scan root, preflight an
explicit source, capture a target, select the newest earlier comparable source,
calculate the existing delta, and return a deterministic pulse document.

## Acceptance Criteria

- Automatic selection requires supported snapshot schema, one store ID, an
  exactly equal canonical scan root, and an earlier generation.
- Selection uses the highest eligible generation and deterministic tie breaks;
  it does not skip a partial latest candidate.
- Explicit selection reports not-found, store, scope, schema, and ordering
  failures without capturing a target or falling back.
- A first observation returns a complete `baseline_created` result without
  movement claims.
- A selected comparison preserves every base delta repository and event,
  including verified no-ops and indeterminate events.
- The pulse model validates schema/version, comparison state, outcome state,
  movement state, deterministic repository order, and summary counts.
- Source repositories remain read-only. A post-capture failure identifies the
  retained target snapshot when available.

## Allowed Write Surfaces

- `src/vcs_tree/models.py`
- `src/vcs_tree/pulse.py`
- `tests/test_models.py`
- `tests/test_pulse.py`
- this task file and `tasks/WORKBOARD.md`

Do not edit adapters, enrichment, renderers, CLI dispatch, host documentation,
the baseline script, or live resource files.

## Required Fixtures

- In-memory retained snapshots covering exact-root success, overlapping-root
  rejection, store mismatch, unsupported schema, duplicate generation tie,
  explicit source failure, and no prior baseline.
- A latest partial snapshot followed by a complete target, proving the partial
  source is selected and its uncertainty is retained.
- A multi-repository delta containing movement, no-op, and indeterminate
  entries in noncanonical input order.

## Completion Evidence

- Focused model and pulse-orchestration tests covering every selection and
  error branch.
- Full `scripts/check` success with 100% statement and branch coverage.
- Task closure records the exact test count and representative selected source,
  baseline, and explicit-mismatch assertions.

Implementation evidence:

- Added `PulseEnvelope` schema/version validation and deterministic JSON round
  trips, plus `PulseOrchestrator` baseline, automatic, and explicit selection.
- Automatic selection requires supported schema, matching local store and
  canonical scope, and chooses the highest eligible generation with stable
  timestamp/ID tie breaks. Explicit mismatch errors occur before capture.
- Target snapshots and base delta repositories/events are retained in the
  pulse document; partial and error outcomes remain explicit.
- `scripts/check` passes: Ruff format/lint, 154 tests with 100% statement and
  branch coverage, and `uv build`.
