Filed as: 260803-evaluate-mechanical-predicates
FKA:
AKA: factual query engine; three-valued evidence predicates
Legacy index:

keywords: tooling, blocked, predicates, query, evidence, clocks, completeness

Parent: `260803-define-backlog-review-pressure`
Depends on: `260803-collect-current-working-copy-evidence`; `260803-index-temporal-fact-intervals`
Blocks: `260803-expose-mechanical-query-cli`
Blocked by: `260803-collect-current-working-copy-evidence`; `260803-index-temporal-fact-intervals`
Related: `260801-calculate-history-deltas`; `260802-implement-pulse-orchestration`

# Evaluate Mechanical Evidence Predicates

Implement the versioned, deterministic predicate document and evaluation
service that intelligent consumers use to translate review intent into factual
repository queries.

## Contract

Follow the query grammar, predicate vocabulary, three-valued logic, and elapsed
semantics in `planning/mechanical-review-dispatch.md`. This task returns a model
and service; it does not add public CLI parsing or rendering.

## Acceptance Criteria

- A typed `vcs-tree.history-query` version 1 document validates repository
  scope and exactly one `where` predicate.
- Boolean nodes support `all`, `any`, and `not` with the documented
  true/false/indeterminate truth tables.
- `fact` leaves select stable fact type/attributes and active, inactive, or
  ever-observed state.
- `elapsed` leaves support current-interval start, last confirmation, last
  invalidation, and last transition with numeric comparison against
  non-negative seconds.
- `component` leaves support outcome, `complete_as_of`, and working-copy
  freshness comparisons.
- `never_observed` has a negative-infinity origin and positive-infinity elapsed
  duration. Finite lower-bound comparisons match while evidence preserves the
  sentinel; it is not confused with unknown.
- False requires sufficient evidence. Missing, partial, stale, identity-broken,
  or unsupported evidence returns indeterminate when it prevents a supported
  answer.
- Evaluation is per repository in deterministic repository/fact order and
  returns every leaf result, evidence snapshot/fact/component, clock origin,
  and completeness/freshness boundary.
- Repeated evaluation at an explicitly supplied evaluation time is byte-stable
  and does not mutate the temporal index or source repositories.
- No schema field, predicate, result, or message encodes urgency, staleness,
  dormancy, health, priority, review requirement, or `initial_commit_due`.

## Allowed Write Surfaces

- one new predicate/query model module under `src/vcs_tree/`
- one new evaluator module under `src/vcs_tree/`
- `src/vcs_tree/models.py` only for the public query envelope boundary
- `src/vcs_tree/__init__.py`
- focused predicate-model/evaluator tests under `tests/`
- a new query contract under `docs/contracts/`
- this task file and `tasks/WORKBOARD.md`

Do not edit native adapters, snapshot/delta collection, temporal index
construction, CLI dispatch/rendering, review semantics, the baseline script, or
live resource files.

## Required Fixtures

- Every leaf operator and malformed document/value.
- Three-valued nested boolean matrices.
- Never-observed, active, tombstoned, reappeared, partial, stale, and
  identity-uncertain facts.
- Git unborn facts and jj root-parented recorded `@` facts that remain factual
  without emitting an initial-commit conclusion.
- Multiple repositories and facts supplied in noncanonical input order.

## Completion Evidence

- Focused tests cover every validation and truth-table branch.
- Golden JSON proves deterministic evidence-rich results without opinionated
  reason codes.
- `scripts/check` passes with 100% statement and branch coverage.

## Next Actions

- Claim after both factual prerequisite tasks close.

