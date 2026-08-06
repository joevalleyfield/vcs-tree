Filed as: 260806-expose-workspace-family-identity
FKA:
AKA: linked jj workspace identity; repository operation family
Legacy index:

keywords: tooling, active, history, identity, usability

Parent: `260806-support-review-consumers`
Depends on: `260803-restore-nested-repository-reporting`;
  `260806-project-review-candidate-evidence`;
  `260806-group-movement-evidence`
Blocks: `agent-boundaries:260806-dogfood-repository-review`
Blocked by:
Related: `/Users/tim/Documents/Journal/objectives/scale-vcs-tree-recurring-consumer-facts.md`;
  `/Users/tim/Documents/agent-boundaries/planning/repository-review-dogfood-20260806.md`

# Expose Factual Workspace-Family Identity

## Status

Completed on 2026-08-06.

Let public consumers recognize several linked jj workspace paths as views of
one operation/repository without collapsing their distinct local evidence.

## Current Reality

The generation-17 public candidate projection reports the same TOAS workspace
set independently beneath `repo-0054`, `repo-0055`, `repo-0057`, and
`repo-0059`. Pulse consequently repeats one logical change stack across four
repository paths. Repository keys and paths are stable, but no public factual
relationship tells a consumer that these roots share one jj operation.

## Desired Reality

Snapshot, pulse, and candidate consumers receive a stable, store-scoped family
relationship for linked jj workspaces. Each discovered path, repository key,
workspace role, current target, freshness, and completeness remains distinct.
Independent clones, nested repositories, colocated roots, and ambiguous or
unreadable metadata are not merged by guesswork.

## Known Facts / Assumptions / Unknowns

- Fact: the same workspace keys and change IDs appear across the four TOAS
  repository records.
- Fact: change IDs alone are not an adequate cross-repository identity
  contract.
- Fact: `vcs-tree` owns repository/workspace identity facts, while consumers
  own domain grouping and pressure.
- Unknown: which native jj operation-store identifier can be normalized and
  persisted without exposing unstable host-internal paths. Settle this in the
  contract before implementation.

## Models / Forecasts / Risks

- Symlink aliases and linked workspaces are different relationships and need
  separate coverage.
- A shared Git object store does not by itself prove one jj operation.
- Family identity must remain useful across path movement while staying scoped
  to the observer store/writer continuity boundary.
- Incomplete native identity must remain explicit rather than generating a
  false family.

## Transformations

- Define a factual, versioned workspace-family relationship and completeness
  semantics.
- Collect and persist stable family identity for jj and colocated repositories.
- Project the relationship through supported snapshot, pulse, and candidate
  JSON surfaces without performing consumer aggregation.
- Preserve existing repository keys and compatibility or version the changed
  contract explicitly.
- Document consumer use and non-goals.

## Evidence

- Controlled fixtures distinguish linked workspaces, symlink aliases,
  independent clones, nested repositories, colocated repositories, moved paths,
  and incomplete/unreadable native identity.
- Public black-box tests expose the same family for linked workspace roots while
  retaining their separate paths, keys, roles, freshness, and errors.
- Pulse keeps per-path movement auditable and supplies enough relationship data
  for a consumer to present one family-aware domain collection.
- A bounded real-corpus acceptance demonstrates the TOAS workspace family
  without private-ledger parsing.
- `scripts/check` passes with 100% statement and branch coverage and `uv build`.

## Allowed Write Surfaces

- snapshot/native adapter/model/pulse/candidate modules under `src/vcs_tree/`
- focused fixtures and tests under `tests/`
- identity and public-output docs/contracts
- this task and `tasks/WORKBOARD.md`

## Next Actions

1. Claim under the Engineer role and settle the stable family identifier and
   incomplete-identity contract before changing collection.

## Completion Evidence

- jj collection reads the native `.jj/repo/config-id` from primary and linked
  workspace metadata, emitting a path-independent `jj-config-id:<value>` family
  id. Missing or unreadable identity is reported as an error with a null id;
  independent stores therefore cannot be merged by path or change id.
- Snapshot repositories, delta repository records, pulse repositories, and
  current-workspace candidate projections preserve the family relationship
  while retaining distinct repository paths, keys, workspace roles, and
  completeness facts.
- Contract documentation records the identity source, Git-only
  `not_requested` behavior, and no-guessing rule for incomplete identity.
- Controlled linked-store and unavailable/empty-identity fixtures pass.
- `scripts/check`: Ruff passed; 395 tests passed at 100% statement and branch
  coverage; `uv build` passed.
