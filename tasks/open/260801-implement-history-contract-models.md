Filed as: 260801-implement-history-contract-models
FKA:
AKA: history model foundation; v1 wire types
Legacy index:

keywords: tooling, ready, models, contracts, json, validation

Parent: `260728-movement-snapshot-package`
Depends on: `260729-draft-history-contracts`; `260801-settle-v1-policy-defaults`
Blocks: `260801-build-local-history-ledger`; `260801-implement-git-history-adapter`;
  `260801-implement-jj-history-adapter`; `260801-collect-history-snapshots`;
  `260801-calculate-history-deltas`
Blocked by:
Related:

# Implement the History Contract Models

Create the shared typed vocabulary and deterministic JSON boundary used by all
v1 history collection, persistence, and comparison components.

## Current Reality
The snapshot and delta contracts define records, enumerations, ordering, and
invariants in Markdown. The package has no corresponding in-memory types,
validation boundary, or version-aware serializer.

## Desired Reality
The package can construct, validate, serialize, and deserialize supported v1
snapshot, ledger-object, and delta records without invoking repository commands
or reading application state.

## Gap Analysis
Every later task otherwise risks inventing its own representation of outcomes,
identifiers, refs, workspaces, history boundaries, snapshots, and events.

## Known Facts / Assumptions / Unknowns
- Fact: the two contract documents are normative for v1 field meaning.
- Fact: real commit IDs, jj null root, unborn state, and read errors remain
  distinct.
- Fact: unsupported major schema versions are rejected.
- Assumption: ordinary Python types with an explicit conversion boundary are
  sufficient; this task does not choose a database representation.
- Unknown: none that block implementation.

## Investigations
- Inventory every normative enum and required/optional field in both contracts.
- Select representative complete examples and edge cases as fixtures.

## Models / Forecasts / Risks
- Permissive parsing could turn malformed state into false movement claims.
- Serializer-specific object identity would couple contracts to persistence.
- Duplicating Git and jj types where the contract shares a shape will invite
  incompatible adapter output.

## Transformations
- Add typed v1 records for collection outcomes, completeness boundaries, native
  IDs, history objects, refs, roots, workspaces, repositories, snapshots, and
  delta events/envelopes.
- Add explicit validation for required fields, enum values, schema identity,
  schema version, and cross-field invariants that do not require ledger access.
- Add deterministic JSON-compatible conversion and parsing at the package
  boundary.
- Export only the intended public model and serialization surface.
- Allowed write surfaces: `src/vcs_tree/`, `tests/`, and this task file; update
  `tasks/WORKBOARD.md` only for lifecycle changes.
- Do not add subprocess collection, filesystem persistence, CLI commands,
  JSON Schema, or new contract semantics.

## Evidence
- Focused tests cover valid round trips, deterministic output, all enums,
  malformed input, unsupported versions, and null-root/error distinctions.
- Representative snapshot and delta fixtures conform to the documented v1
  shapes.
- The full test suite and Ruff checks pass at the repository's 100% coverage
  requirement.
- Completion records the exact public API and verification commands.

## Decisions
- Keep models independent of collection and storage implementations.

## Open Fronts
- External JSON Schema remains outside v1.
- Ledger-backed invariants remain owned by the ledger and snapshot tasks.

## Next Actions
- Implement the smallest public model/codec surface satisfying the contracts.
- Close this task with tests and API evidence before dependent tasks claim the
  shared representation.
