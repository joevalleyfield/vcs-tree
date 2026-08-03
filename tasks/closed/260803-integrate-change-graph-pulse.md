Filed as: 260803-integrate-change-graph-pulse
FKA:
AKA: jj-first pulse integration; change-stack movement brief
Legacy index:

keywords: tooling, closed, follow-on, pulse, jj, integration, enrichment, warnings

Parent: `260802-recurring-movement-pulse`
Depends on: `260803-calculate-jj-change-deltas`; `260803-separate-publication-hints`
Blocks: `260802-expose-pulse-output-workflow`
Blocked by:
Related: `260802-enrich-pulse-movement-evidence`; `260802-classify-pulse-task-warnings`

# Integrate jj Change Graph Movement into Pulse

Adapted the completed pulse orchestration, enrichment, and warning semantics
to consume the jj-first delta before public CLI/rendering work.

## Closure Evidence

- Pulse orchestration now enriches jj change-version/head events, retains
  descriptions and parent-relative paths, derives task-path events, and emits
  stable warning lifecycles for graph, publication, comparison, and enrichment
  surfaces.
- Factual movement counts exclude `comparison_incomplete`; observed movement
  remains `observed` under partial outcomes, while warning-only partial pulses
  remain `unknown`.
- Added bookmark-free rewrite, partial-publication, warning-only, task-path,
  and compatibility fixtures. `scripts/check` passed: 191 tests, 100%
  statement and branch coverage, Ruff, and package build.
