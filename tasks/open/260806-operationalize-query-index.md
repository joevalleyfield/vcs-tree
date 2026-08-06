Filed as: 260806-operationalize-query-index
FKA:
AKA: warm temporal queries; observable derived-index rebuild
Legacy index:

keywords: tooling, active, history, query, performance

Parent: `260806-support-review-consumers`
Related: `260803-index-temporal-fact-intervals`;
  `260804-history-observability-and-index`

# Operationalize the Temporal Query Index

Make several factual questions over one accepted observation observable,
reusable, and safe for recurring playbook execution.

## Current Reality

An explicit retained query rebuilt temporal state for about a minute without
progress. Repeating explicit questions can repay that cost, while a query
without `--snapshot` may capture another observation implicitly.

## Desired Reality

One observation supports multiple predicates at one evaluation time. Cold
rebuild, warm reuse, and stale replacement are explicit; progress is visible;
and the derived index remains disposable and tied to its source generation.

## Investigations

- Measure cold/warm behavior on the 13-generation, 68-repository retained
  corpus.
- Identify why explicit snapshot evaluation bypasses reusable current-derived
  state and what compatibility constraints apply to historical snapshots.
- Compare batch query input with a reusable evaluation/session boundary.

## Transformations

- Reuse a current compatible derived index for repeated questions.
- Expose rebuild phases/progress without contaminating JSON stdout.
- Make capture-on-query explicit rather than surprising.
- Support multiple predicates with one snapshot and evaluation timestamp.

## Evidence

- Benchmarks record cold and warm real-corpus costs and an evidence-backed
  operational budget.
- Warm repeated evaluation performs no observation and no rebuild.
- Historical snapshot queries remain correct and visibly distinct.
- Interrupted/corrupt derived state rebuilds safely from authoritative data.
- CLI JSON remains machine-clean; `scripts/check` passes.

## Allowed Write Surfaces

- ledger/query/CLI modules under `src/vcs_tree/`
- focused temporal-query tests under `tests/`
- query workflow and temporal-index docs/contracts
- this task and `tasks/WORKBOARD.md`

## Next Actions

1. Record a reproducible cold/warm benchmark before selecting a design.

Claimed by Engineer on 2026-08-06 for the bounded query-index operationalization.

## Local Investigation Note

The retained corpus is available at `~/.local/state/vcs-tree` and contains 13
snapshots, 68 repositories, and 92,896 immutable objects. A real cold
`TemporalIndexBuilder` run over the corpus took 58.372 seconds and produced
202,452 facts, 875 components, and 13 source snapshots. The persisted
`temporal-facts.json` was absent before the run, confirming the cold path.

The earlier synthetic 13-generation/68-repository equivalent measured 0.1862
seconds cold and 0.0237 microseconds for in-process reuse; it is retained only
as a scale sanity check, not as the operational result. The real corpus now
provides the evidence-backed budget for the design: repeated questions must
reuse a compatible derived index and must not pay the approximately one-minute
rebuild cost.

## Implementation Progress

- Historical snapshot queries now use a disposable cache keyed by a hashed
  store ID and source generation. Missing, stale, malformed, or unwritable
  cache state falls back safely to an authoritative rebuild.
- Temporal-index builds report retained-snapshot and per-generation phases
  through an optional callback. The query CLI routes these messages to stderr,
  keeping JSON stdout machine-clean.
- Focused cache/progress tests and the full quality gate pass: 389 tests,
  100% statement and branch coverage, Ruff, and `uv build`.
