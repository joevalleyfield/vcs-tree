Filed as: 260801-integrate-history-cli
FKA:
AKA: history command surface; cache compatibility migration
Legacy index:

keywords: tooling, closed, cli, snapshots, deltas, cache, warnings

Parent: `260728-movement-snapshot-package`
Depends on: `260801-collect-history-snapshots`;
  `260801-calculate-history-deltas`
Blocks:
Blocked by:
Related: `260801-build-local-history-ledger`

# Integrate Snapshot and Delta Commands

Expose history collection and comparison through an operator-facing CLI while
preserving the incumbent renderer and making all storage locations unmistakable.

## Current Reality
The console command preserves the baseline scan/render behavior and writes only
a disposable renderer cache. History APIs will otherwise remain package-only.

## Desired Reality
Operators can initialize/inspect authoritative state, collect snapshots, and
compare them from the package CLI, with resolved state/config/cache locations,
writer policy, and machine-local/cloud-sync warnings clearly reported.

## Gap Analysis
There is no supported command workflow for using the history ledger, and the
existing cache could be mistaken for authoritative state.

## Known Facts / Assumptions / Unknowns
- Fact: the live resource script and wrapper remain untouched until an explicit
  cutover task.
- Fact: default project/tree cloud synchronization does not synchronize
  machine-local control state or repository keys.
- Fact: authoritative state is never placed in the disposable renderer cache.
- Assumption: additive subcommands/options can preserve current default output.
- Unknown: graduation/cutover and recurring pulse integration are separate work.

## Investigations
- Inventory exact current CLI invocation and output compatibility requirements.
- Choose concise operator output for paths, writer identity, partial outcomes,
  and recovery guidance.

## Models / Forecasts / Risks
- Changing default invocation would break the incubation compatibility promise.
- Quietly selecting a machine-local state root could surprise a cloud-drive user.
- Automatic cache-to-ledger promotion could treat disposable data as authority.

## Transformations
- Add explicit commands/options to initialize and inspect the history store,
  collect a snapshot, and calculate/render a factual delta.
- Report resolved authoritative state, configuration, and disposable cache
  locations plus active writer policy/identity.
- Warn that machine-local control state does not follow a cloud-synchronized
  repository tree and that v1 permits only the enrolled writer.
- Keep existing renderer-cache data disposable; do not silently promote it to
  ledger authority.
- Preserve existing default scan/render behavior and error/exit compatibility.
- Allowed write surfaces: `src/vcs_tree/`, `tests/`, CLI fixtures,
  `README.md`, and this task file; update `tasks/WORKBOARD.md` only for lifecycle
  changes.
- Do not edit or redirect `../../Resources/tools/`, add recurring automation,
  implement export bundles, or perform the eventual cutover.

## Evidence
- Added additive `history init`, `history inspect`, `history snapshot`, and
  `history delta` command workflows while leaving the default scanner parser and
  renderer invocation unchanged.
- Init and inspect report authoritative state, config, and disposable cache
  locations, writer identity/policy, and the machine-local/cloud-sync warning.
- Snapshot and delta commands use the durable ledger and return non-zero JSON
  error/partial results without promoting renderer cache data.
- Added CLI compatibility and workflow tests, including uninitialized stores,
  malformed/degraded state, missing snapshots, and ledger errors.
- Documented the distinction between authoritative state and disposable cache
  in `README.md`.
- `uv run ruff check src/vcs_tree tests` passes.
- `uv run pytest -q`: 119 tests, 100.00% coverage.

## Decisions
- Make the history workflow explicit and additive during incubation.
- Keep `history` behind a dispatch in `main` so arbitrary positional paths
  retain the incumbent default parser behavior.

## Open Fronts
- Live-resource cutover, recurring pulses, exports, and task-lifecycle adapters.

## Next Actions
- Integrate only after snapshot and delta APIs close with stable evidence.
