Filed as: 260728-movement-snapshot-package
FKA:
AKA: vcs movement feed; refs and delta descriptions; package extraction
Legacy index:

keywords: tooling, decomp, inception, contract, snapshots, refs, deltas

Parent:
Depends on: `260728-bootstrap-vcs-tree-incubator`
Blocks:
Blocked by:
Related:

# Define the Movement-Snapshot Package

Extract the scanner behind a stable data model that can describe repository
movement without conflating movement with progress.

## Current Reality
The baseline behavior now has an installable, tested `src/` package boundary
and console entry point. Its present-state collection and cache remain shaped
around the existing renderer; it does not yet expose a versioned snapshot
schema, normalized refs, or snapshot-to-snapshot descriptions.

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
- Assumption: a versioned JSON snapshot is the first durable interchange
  surface.
- Assumption: history records should be content-addressed and deduplicated,
  while each snapshot records the ref topology that made history observable.
- Assumption: the default observed-history boundary includes commits reachable
  from local refs, remote-tracking refs, tags, and jj visible heads.
- Unknown: which refs belong in the default collection and how remote/tracking
  refs should be normalized across Git and jj.
- Unknown: whether Git reflogs and dangling objects belong in an optional deep
  mode.
- Unknown: how long unreachable history remains locally retained.
- Unknown: how jj change IDs and commit IDs participate in stable identity.
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
- Snapshot, ref, and delta transformations remain to be decomposed after their
  contract is explicit.

## Evidence
- The package follow-on closed with a locked Python 3.9+ project, 26 passing
  tests, 88.12% branch coverage, passing Ruff checks, build artifacts, and a
  behavior-compatible empty-directory smoke scan.
- `planning/history-surface-exploration.md` begins the native-surface contract
  with Git-only, colocated, linked-workspace, and controlled before/after
  fixture evidence.
- A written snapshot/ref/delta contract grounded in representative repositories.
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

## Open Fronts
- Snapshot persistence and cache migration.
- Ref normalization.
- Observed-history boundary, unreachable-history retention, and optional Git
  reflog/dangling-object coverage.
- jj change identity versus commit identity.
- Delta description vocabulary.
- Task-lifecycle adapters.

## Next Actions
- Draft the first versioned history/snapshot/ref/delta contract against
  `planning/history-surface-exploration.md`.
