Filed as: 260806-extend-temporal-index
FKA:
AKA: incremental temporal projection; consecutive-generation query reuse
Legacy index:

keywords: tooling, active, history, query, performance

Parent: `260806-support-review-consumers`
Depends on: `260806-operationalize-query-index`;
  `260803-index-temporal-fact-intervals`
Blocks: `agent-boundaries:260806-dogfood-repository-review`
Blocked by:
Related: `/Users/tim/Documents/Journal/objectives/scale-vcs-tree-recurring-consumer-facts.md`;
  `/Users/tim/Documents/agent-boundaries/planning/repository-review-dogfood-20260806.md`

# Extend the Temporal Index Across Generations

## Status

Completed on 2026-08-06.

Reuse a validated prior-generation temporal projection when evaluating the
next retained generation instead of rebuilding every historical snapshot.

## Current Reality

The derived query cache is reusable only for an exact generation. A new pulse
therefore invalidates the cache and rebuilds all retained snapshots: live
generation-16 and generation-17 review runs indexed 16 and 17 snapshots and
took 220.30 and 255.50 seconds respectively.

## Desired Reality

A valid generation-N projection can be extended deterministically with
generation N+1. Missing, corrupt, incompatible, discontinuous, or ambiguous
state falls back safely to a full rebuild with an explicit reason. Authoritative
snapshots remain unchanged and a full rebuild remains the correctness oracle.

## Known Facts / Assumptions / Unknowns

- Fact: temporal indexes are disposable projections, not authoritative state.
- Fact: exact-generation cache reuse and full rebuild already exist.
- Fact: consumer batches reuse one index within a generation.
- Assumption: interval/tombstone state in the projection contains enough
  information to extend one ordered generation without replaying older inputs.
- Unknown: whether extension should update the canonical derived index, the
  historical cache, or both. Choose the smallest crash-safe design that avoids
  duplicate logic.

## Models / Forecasts / Risks

- A skipped generation or mismatched store/writer/schema must not be treated as
  contiguous.
- Extension and full rebuild must agree on ordering, interval boundaries,
  component continuity, reappearance, and tombstones.
- An interrupted extension must not poison a previously valid cache.

## Transformations

- Define and implement validated consecutive-generation extension.
- Fall back to full rebuild with specific progress when validation fails.
- Write derived results atomically and retain exact-generation cache behavior.
- Report cache hit, extension, and full rebuild distinctly on stderr.
- Document cost and correctness behavior for recurring consumers.

## Evidence

- Property/golden tests compare extension with a full rebuild for confirmation,
  tombstone, reappearance, component partial/error, repository disappearance,
  and identity-boundary cases.
- Gap, schema mismatch, corrupt cache, wrong store, and interrupted-write cases
  rebuild safely and visibly.
- A black-box consecutive-generation query proves generation N+1 does not read
  or index generations 1..N when the validated projection is available.
- A bounded real-store trial records generation-N and N+1 timings and verifies
  query output equivalence with a clean full rebuild.
- `scripts/check` passes with 100% statement and branch coverage and `uv build`.

## Allowed Write Surfaces

- temporal ledger/index/query modules under `src/vcs_tree/`
- focused tests under `tests/`
- temporal-query docs/contracts
- this task and `tasks/WORKBOARD.md`

## Next Actions

1. Claim under the Engineer role and first encode extension-versus-rebuild
   equivalence plus discontinuity fallback as tests.

## Completion Evidence

- Added a validated `TemporalIndexBuilder.extend()` path that applies one
  consecutive retained snapshot to copied fact intervals, component clocks,
  tombstones, reappearance episodes, and continuity boundaries.
- Historical query cache resolution now attempts generation-N extension from a
  valid generation-N-1 cache, reports extension/fallback/full-rebuild progress,
  writes the new projection atomically, and preserves exact-generation cache
  hits. Any extension exception safely falls back to the complete rebuild.
- Golden tests prove extension equals a clean rebuild for ref replacement and
  interval state; gap, store mismatch, incompatible/corrupt inputs, extension
  failure, repository identity boundaries, and missing paths are covered.
- Query contract documents disposable projection, validation, fallback, and
  authoritative-snapshot invariants.
- `scripts/check`: Ruff passed; 400 tests passed at 100% statement and branch
  coverage; `uv build` passed.
