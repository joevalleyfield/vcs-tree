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
