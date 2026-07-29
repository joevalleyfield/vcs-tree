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
- Assumption: a versioned JSON snapshot is the first durable interchange
  surface.
- Unknown: which refs belong in the default collection and how remote/tracking
  refs should be normalized across Git and jj.
- Unknown: whether task movement begins as generic path evidence or
  project-specific adapters.

## Investigations
- Inventory Git and jj ref/bookmark surfaces available locally.
- Identify the minimum snapshot identity needed for reliable deltas.
- Locate seams that permit behavior-preserving extraction from the baseline.

## Models / Forecasts / Risks
- Combining extraction and new semantics risks losing compatibility evidence.
- A renderer-shaped schema will make later consumers brittle.
- Recording every ref or file detail may make frequent pulses noisy and slow.

## Transformations
- Package extraction completed under `260729-package-python-project`.
- Snapshot, ref, and delta transformations remain to be decomposed after their
  contract is explicit.

## Evidence
- The package follow-on closed with a locked Python 3.9+ project, 26 passing
  tests, 88.12% branch coverage, passing Ruff checks, build artifacts, and a
  behavior-compatible empty-directory smoke scan.
- A written snapshot/ref/delta contract grounded in representative repositories.
- Compatibility checks against the baseline tree output.
- Focused fixtures for Git, jj, colocation, null-root, dirty, and error states.

## Decisions
- Preserve the standalone script as a byte-identical compatibility reference
  while new behavior develops through the package.
- Separate behavior-preserving package extraction from new movement semantics.

## Open Fronts
- Snapshot persistence and cache migration.
- Ref normalization.
- Delta description vocabulary.
- Task-lifecycle adapters.

## Next Actions
- Inspect representative local Git/jj ref outputs and draft the first
  snapshot/ref/delta contract against the extracted package.
