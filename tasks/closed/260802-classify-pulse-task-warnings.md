Filed as: 260802-classify-pulse-task-warnings
FKA:
AKA: task path facts; warning lifecycle
Legacy index:

keywords: tooling, closed, pulse, tasks, warnings, uncertainty, semantics

Parent: `260802-recurring-movement-pulse`
Depends on: `260802-implement-pulse-orchestration`; `260802-enrich-pulse-movement-evidence`
Blocks: `260802-expose-pulse-output-workflow`
Blocked by: pulse orchestration and movement-evidence enrichment
Related: `260806-history-completeness-and-bookmarks`

# Classify Pulse Task Paths and Warning Lifecycles

Derived path-factual task events and stable new/persistent/recovered
uncertainty from completed pulse and enrichment surfaces.

## Completion Evidence

- Implemented `vcs_tree.pulse_semantics` with deterministic task-path events,
  inspectable warning identities, and new/persistent/recovered lifecycles.
- Added table-driven fixtures for all statuses and area boundaries, including
  the direct closed-path addition and merge/partial evidence shapes.
- `scripts/check`: 176 tests passed; 100% statement and branch coverage;
  Ruff format/lint and `uv build` passed.
- A direct `added` entry under `tasks/closed/` is emitted as
  `task_path_added` with `from_area: outside`, never as `task_path_moved`.
