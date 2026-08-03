Filed as: 260802-expose-pulse-output-workflow
FKA:
AKA: pulse CLI; pulse rendering; pulse e2e
Legacy index:

keywords: cli, closed, pulse, json, rendering, e2e, exits

Parent: `260802-recurring-movement-pulse`
Depends on: `260802-implement-pulse-orchestration`; `260802-enrich-pulse-movement-evidence`; `260802-classify-pulse-task-warnings`; `260803-integrate-change-graph-pulse`
Blocks: `260802-document-recurring-pulse-adapters`
Blocked by:
Related: `260805-delta-presentation-surfaces`

# Expose and Validate the Pulse Output Workflow

Added the public command, stable JSON, concise summary, audit rendering, exit
behavior, and black-box evidence for the full pulse workflow.

## Closure Evidence

- Added installed `history pulse` syntax with summary, audit, and stable JSON
  renderers, stderr progress, enrichment limits, and exit codes 0/3/4 while
  preserving argparse usage exit 2 and existing history commands.
- Summary suppresses verified no-ops and warning-only events; audit/JSON retain
  complete repositories, native events, descriptions, paths, task events, and
  warning lifecycles.
- Added parser, renderer, CLI, and pulse workflow fixtures for baseline,
  movement, partial, unknown, and selection-error cases. `scripts/check`
  passed: 196 tests, 100% statement and branch coverage, Ruff, and build.
