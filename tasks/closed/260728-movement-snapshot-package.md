Filed as: 260728-movement-snapshot-package
FKA:
AKA: vcs movement feed; refs and delta descriptions; package extraction
Legacy index:

keywords: tooling, decomp, closed, contract, snapshots, refs, deltas

Parent:
Depends on: `260728-bootstrap-vcs-tree-incubator`
Blocks: `260801-implement-history-contract-models`; `260801-build-local-history-ledger`;
  `260801-implement-git-history-adapter`; `260801-implement-jj-history-adapter`;
  `260801-collect-history-snapshots`; `260801-calculate-history-deltas`;
  `260801-integrate-history-cli`
Blocked by:
Related:

# Define the Movement-Snapshot Package

Extract the scanner behind a stable data model that can describe repository
movement without conflating movement with progress.

## Current Reality
The package now provides versioned snapshot and delta envelopes, a machine-local
append-only ledger, Git/jj native adapters, colocated snapshot collection, a
deterministic delta engine, and additive CLI workflows. The standalone resource
script and wrapper remain unchanged.

## Desired Reality
The project has a package boundary and factual movement model supporting:

- Git, jj, and colocated repository identity;
- working-copy state and explicit errors;
- real commit dates and jj null-root `00000000`;
- refs/bookmarks and their movement;
- enough full observed history to detect fetched lines of work and activity
  outside the current branch or bookmark;
- versioned snapshots and deltas;
- commit/change identifiers and short descriptions;
- task-file creation and closure evidence derived from deltas.

## Gap Analysis
Collection, interpretation, caching, and rendering remain coupled. A package
extraction needs to preserve existing CLI behavior while defining data that
future recurring workspace pulses can compare and summarize.

## Known Facts / Assumptions / Unknowns
- Fact: descriptions should remain factual; movement assessment belongs to a
  higher-level consumer.
- Fact: colocation is a first-class repository mode.
- Fact: the movement feed must notice work outside the current checkout,
  including a fetch that introduces an unrelated line of history.
- Fact: the repository tree may be cloud-synchronized while vcs-tree state and
  configuration remain machine-local.
- Fact: v1 is observational state, not a custody chain or audit system.
- Assumption: a versioned JSON snapshot is the first durable interchange
  surface.
- Assumption: history records should be content-addressed and deduplicated,
  while each snapshot records the ref topology that made history observable.
- Assumption: the default observed-history boundary includes commits reachable
  from local refs, remote-tracking refs, tags, and jj visible heads.
- Assumption: v1 assigns repository keys within one local ledger and permits
  one enrolled writer machine.
- Assumption: v1 retains observed history indefinitely.
- Assumption: v1 stores event ID lists inline without silent truncation.
- Unknown: whether Git reflogs and dangling objects belong in an optional deep
  mode.
- Unknown: whether task movement begins as generic path evidence or
  project-specific adapters.

## Investigations
- Inventory Git and jj ref/bookmark surfaces available locally.
- Inventory Git and jj commands that expose complete reachable history,
  parents, ref targets, visible heads, and native identifiers.
- Identify the minimum snapshot identity needed for reliable deltas.
- Locate seams that permit behavior-preserving extraction from the baseline.

## Models / Forecasts / Risks
- Combining extraction and new semantics risks losing compatibility evidence.
- A renderer-shaped schema will make later consumers brittle.
- Repeating the entire history graph in every snapshot would make frequent
  pulses noisy, slow, and unnecessarily large.
- Recording only the current branch would miss fetched or parallel work.
- A shared append-only history store plus lightweight ref-topology snapshots
  can preserve observations without repeated graph copies.

## Transformations
- Package extraction completed under `260729-package-python-project`.
- Git/jj surface exploration completed under
  `260729-explore-history-surfaces`.
- Draft snapshot and delta contracts completed under
  `260729-draft-history-contracts`.
- Initial identity, state, writer, retention, resilience, incomplete-history,
  and payload defaults settled under `260801-settle-v1-policy-defaults`.
- Implementation is decomposed into seven ready tasks covering contract
  models, authoritative state, native adapters, snapshot collection, delta
  calculation, and CLI integration.

## Evidence
- Package extraction, contract, ledger, adapter, snapshot, delta, CLI, and
  compatibility follow-ons are closed with durable task evidence.
- The final suite has 120 passing tests with 100.00% statement and branch
  coverage, and Ruff checks pass.
- An offline wheel build succeeds as
  `/tmp/vcs-tree-final-build/vcs_tree-0.1.0-py3-none-any.whl`.
- A real colocated `/Users/tim/Documents` snapshot smoke reports generation 1,
  complete Git/jj workspaces, complete jj bookmarks, and complete jj visible
  heads.
- `planning/history-surface-exploration.md` begins the native-surface contract
  with Git-only, colocated, linked-workspace, and controlled before/after
  fixture evidence.
- `docs/contracts/history-snapshot-v1.md` and
  `docs/contracts/history-delta-v1.md` provide versioned draft contracts
  grounded in that evidence.
- The v1 policy pass distinguishes authoritative application state from the
  existing disposable renderer cache and makes corruption non-custodial and
  failure-isolated.
- Compatibility checks against the baseline tree output.
- Focused fixtures for Git, jj, colocation, null-root, dirty, and error states.

## Decisions
- Preserve the standalone script as a byte-identical compatibility reference
  while new behavior develops through the package.
- Separate behavior-preserving package extraction from new movement semantics.
- Retain enough full observed history to recognize new fetched lines of work
  and non-current-branch activity.
- Prefer a deduplicated history store keyed by native object identity, with
  snapshots recording current ref topology and newly observed objects.
- Use explicit selected Git ref namespaces rather than raw `--all` in
  colocation.
- Preserve annotated ref objects separately from peeled commit roots.
- Use commit ID for jj graph identity, retain change ID as logical identity,
  and represent conflicted bookmark target sets explicitly.
- Store immutable history objects once in an append-only ledger and make
  lightweight snapshots reference a ledger generation.
- Require complete before/after components for deletion and movement events;
  partial collection produces explicit indeterminacy.
- Define off-current history against every observed target workspace head.
- Assign repository keys within one machine-local ledger and default to one
  enrolled writer machine.
- Keep authoritative ledger/key/snapshot state outside evictable cache and
  report all resolved state, configuration, and cache locations.
- Retain observed history indefinitely; corruption may lose observation
  history but never authorizes repository mutation or custody assertions.
- Mark shallow/incomplete ancestry explicitly and return unknown movement.
- Keep v1 ID lists inline and report explicit limit failure instead of
  truncating them.

## Open Fronts
- Optional Git reflog/dangling and jj operation-history depth.
- Export-bundle framing for ledger-dependent snapshots.
- Future shared/multi-writer migration and cross-machine identity.
- Task-lifecycle adapters.
- Explicit graduation/cutover of the package command in place of the live
  resource script and wrapper.

## Next Actions
- Treat optional reflog/deep-history, exports, shared identity, task-lifecycle
  adapters, and live-resource cutover as separately authorized follow-on work.
