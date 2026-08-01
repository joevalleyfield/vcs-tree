Filed as: 260801-build-local-history-ledger
FKA:
AKA: authoritative history state; local repository registry
Legacy index:

keywords: tooling, closed, ledger, state, identity, resilience

Parent: `260728-movement-snapshot-package`
Depends on: `260801-implement-history-contract-models`
Blocks: `260801-collect-history-snapshots`; `260801-calculate-history-deltas`
Blocked by:
Related: `260801-integrate-history-cli`

# Build the Local History Ledger

Implement authoritative machine-local history state with locally assigned
repository keys, one enrolled writer, immutable objects, and isolated recovery.

## Current Reality
The package has only a disposable renderer cache. It has no authoritative state
root, repository registry, writer enrollment, ledger generation, snapshot
index, or integrity boundary.

## Desired Reality
A local history store safely assigns repository keys, admits only its enrolled
writer, appends immutable objects, advances generations atomically, retains
observations indefinitely, and reports corruption without touching source repos.

## Gap Analysis
Snapshots cannot be durable or comparable until repository identity and history
objects survive individual scans outside the evictable cache.

## Known Facts / Assumptions / Unknowns
- Fact: authoritative state must not live under `XDG_CACHE_HOME` or `~/.cache`.
- Fact: v1 has one enrolled writer and no cross-machine clone identity.
- Fact: corruption may lose observation history but cannot authorize repository
  mutation, custody claims, or unsupported loss/movement claims.
- Assumption: a simple local on-disk representation is adequate if its public
  behavior and atomicity are tested.
- Unknown: export framing and multi-writer migration are deferred.

## Investigations
- Resolve the platform-appropriate default application state and configuration
  roots already used by the surrounding workspace conventions.
- Choose atomic file/update boundaries and integrity checks appropriate to the
  selected representation.

## Models / Forecasts / Risks
- Cloud-synchronized project trees make accidental project-relative control
  state especially surprising.
- A writer marker without verified ownership could permit competing mutation.
- Partial writes must not create a generation that appears complete.

## Transformations
- Add state-root resolution distinct from the existing renderer cache.
- Add store creation with opaque store and writer identities and explicit
  single-writer enrollment.
- Add repository lookup/assignment within one ledger, without inferring clone
  equivalence across ledgers.
- Add immutable, content-addressed history-object insertion and monotonic
  committed generations.
- Add snapshot index/integrity metadata sufficient for later snapshot storage.
- Refuse writes from a non-enrolled writer and surface resolved state,
  configuration, cache, policy, and writer information to callers.
- Isolate detected corrupt records/components and provide a safe replacement or
  reinitialization path that never mutates observed repositories.
- Allowed write surfaces: `src/vcs_tree/`, `tests/`, project-local test fixtures,
  and this task file; update `tasks/WORKBOARD.md` only for lifecycle changes.
- Do not migrate the existing CLI cache, collect repository history, define
  export bundles, or add another writer.
- Implemented `src/vcs_tree/ledger.py` with machine-local path resolution,
  state/config/cache reporting, single-writer enrollment, and opaque local
  repository keys.
- Added independently checksummed manifest, registry, immutable-object,
  generation, and snapshot-index components with atomic replacement writes.
- Added fail-closed corruption detection that degrades only affected
  components and never mutates a source repository.
- Exported the ledger API from `vcs_tree`.

## Evidence
- Tests prove stable local keys, immutable deduplication, monotonic generations,
  atomic failure behavior, writer refusal, and indefinite retention semantics.
- Tests corrupt isolated state and prove dependent assertions fail closed while
  unrelated readable state remains usable.
- Tests prove default authoritative paths are not cache paths and that location
  metadata/warnings are available to the caller.
- The full suite and Ruff checks pass at 100% coverage.
- Added `tests/test_ledger.py` covering stable identity, deduplication,
  retention, generations, writer refusal, state placement warnings, atomic
  failure, malformed components, and isolated corruption.
- `uv run ruff check src/vcs_tree tests` passed.
- `uv run pytest -q` passed: 75 tests, 100.00% total coverage.
- `uv build --wheel --offline --out-dir /tmp/vcs-tree-ledger-build` passed.

## Decisions
- Treat all ledger contents as observational application state, never custody
  evidence or repository instructions.
- Keep each persisted component independently checksummed so object-history
  damage cannot erase the repository registry or authorize source mutation.
- Use `~/.local/state/vcs-tree` (or `XDG_STATE_HOME`) for authority and keep
  `XDG_CONFIG_HOME`/`XDG_CACHE_HOME` in the operator location report.

## Open Fronts
- Portable export, shared writers, cross-machine identity, and cache migration.
- Snapshot orchestration still owns publishing full manifests over committed
  generations.

## Next Actions
- Claim `260801-implement-git-history-adapter` or
  `260801-implement-jj-history-adapter`; both can now use the ledger's stable
  identity and object APIs through the later snapshot task.
