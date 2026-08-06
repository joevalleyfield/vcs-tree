Filed as: 260806-support-review-consumers
FKA:
AKA: recurring review factual affordances; playbook dogfood follow-up
Legacy index:

keywords: tooling, closed, history, review-consumer, dogfood

Parent: `260728-movement-snapshot-package`
Blocks: `260806-correct-movement-evidence`;
  `260806-group-movement-evidence`;
  `260806-project-review-candidate-evidence`;
  `260806-operationalize-query-index`
Related: `/Users/tim/Documents/agent-boundaries/planning/recurring-repository-review-v0.md`

# Support Recurring Review Consumers

Turn the 2026-08-06 playbook trial into factual, supported affordances that let
an external reviewer spend attention on domain judgment rather than ledger
mechanics.

## Completion Evidence

- Public generation-12→13 delta reported a partial comparison with eight
  explicit comparison warnings and 64 unchanged repositories; no private
  snapshot/repository ledger parsing was used in the acceptance workflow.
- One explicit public pulse capture from generation 13 produced generation 14
  over `/Users/tim/Documents`: 68 repositories observed, 62 no-op repositories,
  six grouped movement repositories, six new warnings, ten persistent warnings,
  and two recovered warnings. The process returned partial status with usable
  factual evidence and explicit uncertainty.
- The public movement JSON contained deterministic repository/change groups
  with descriptions, old/new versions, paths, task events, publication hints,
  uncertainty, and complete contributing native events. Recovery events stayed
  outside movement groups.
- The public `history candidates` request over the captured snapshot returned
  the current-workspace packet for all 68 repositories, including stable paths,
  workspace keys, current object/change IDs, exact parents, freshness, bounded
  entries, truncation, and completeness. A 32-entry requested bound remained
  explicit in JSON.
- A public two-predicate query batch reused the captured snapshot without a new
  observation and returned one shared evaluation timestamp. Historical index
  materialization took 94.03 seconds cold; the same writable-cache query took
  21.06 seconds warm and emitted `cache hit` progress on stderr.
- `scripts/check` passed with 393 tests, 100% statement and branch coverage,
  Ruff, and `uv build`; the worktree was clean before this task closure.

## Decisions

- `vcs-tree` remains a factual observation service. No review ranking, health,
  priority, disposition, Journal memory, adapter policy, or
  `initial_commit_due` conclusion was added.
- The public workflow is now: one explicit capture, grouped movement and
  candidate projection from its returned snapshot, then reusable batch factual
  queries. Consumer context and policy remain outside this repository.

## Allowed Write Surfaces

- `planning/`
- `docs/contracts/`
- this task and `tasks/WORKBOARD.md`
