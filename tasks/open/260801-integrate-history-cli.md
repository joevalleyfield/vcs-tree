Filed as: 260801-integrate-history-cli
FKA:
AKA: history command surface; cache compatibility migration
Legacy index:

keywords: tooling, ready, cli, snapshots, deltas, cache, warnings

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
- CLI tests cover store inspection/init, snapshot collection, delta comparison,
  partial/error exits, writer refusal, and location/cloud-sync warnings.
- Compatibility tests prove the incumbent default command and renderer cache
  behavior remain unchanged.
- Documentation clearly distinguishes authoritative state from disposable cache.
- The full suite and Ruff checks pass at 100% coverage.

## Decisions
- Make the history workflow explicit and additive during incubation.

## Open Fronts
- Live-resource cutover, recurring pulses, exports, and task-lifecycle adapters.

## Next Actions
- Integrate only after snapshot and delta APIs close with stable evidence.
