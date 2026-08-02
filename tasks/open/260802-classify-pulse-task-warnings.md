Filed as: 260802-classify-pulse-task-warnings
FKA:
AKA: task path facts; warning lifecycle
Legacy index:

keywords: tooling, blocked, pulse, tasks, warnings, uncertainty, semantics

Parent: `260802-recurring-movement-pulse`
Depends on: `260802-implement-pulse-orchestration`; `260802-enrich-pulse-movement-evidence`
Blocks: `260802-expose-pulse-output-workflow`
Blocked by: pulse orchestration and movement-evidence enrichment
Related: `260806-history-completeness-and-bookmarks`

# Classify Pulse Task Paths and Warning Lifecycles

Derive path-factual task events and stable new/persistent/recovered uncertainty
from the completed pulse and enrichment surfaces.

## Acceptance Criteria

- Root-relative, case-sensitive `tasks/open/**.md` and
  `tasks/closed/**.md` paths are classified without using filename dates or
  document content.
- Added, removed, modified, copied, within-area renamed, and open/closed moved
  events retain commit, parent, old path, new path, and area evidence.
- Only a native rename may produce an open-to-closed or closed-to-open move.
  Direct addition under `tasks/closed/` is not reported as a proven closure.
- Delete/add pairs, copy events, incomplete evidence, and merge-parent
  disagreement remain separate or explicitly ambiguous.
- Warning keys use repository, component, kind, stage, and affected event class;
  mutable text, paths, snapshots, generations, and timestamps do not affect
  identity.
- Warning lifecycles correctly report new, persistent, and recovered states,
  including changed messages, changed kinds, scan-level warnings, comparison-
  only warnings, and history-boundary recovery.
- Null roots, baselines, and verified no-ops do not become warnings.
- Derived arrays and summary counts are deterministic.

## Allowed Write Surfaces

- `src/vcs_tree/pulse_semantics.py`
- `tests/test_pulse_semantics.py`
- this task file and `tasks/WORKBOARD.md`

Do not edit collectors, ledger storage, pulse selection, CLI/renderers, host
documentation, the baseline script, or live resource files.

## Required Fixtures

- Path tables covering every changed-path status across outside/open/closed
  source and destination areas.
- The retained generation-7-to-8 example: modified `tasks/WORKBOARD.md` plus a
  direct addition of `tasks/closed/260802-reconcile-workboard.md`.
- Warning pairs covering absent/present, present/present with message change,
  present/absent, kind change, comparison-only suppression, and scan scope.
- A merge with different parent-relative task evidence and a partial path
  collection.

## Completion Evidence

- Table-driven task-path and warning-lifecycle tests covering every vocabulary
  value and identity field.
- Full `scripts/check` success with 100% statement and branch coverage.
- Task closure records the exact test count and demonstrates that the grounded
  closed-path addition is not mislabeled as a proven transition.

