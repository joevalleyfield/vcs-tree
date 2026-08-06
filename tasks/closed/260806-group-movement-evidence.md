Filed as: 260806-group-movement-evidence
FKA:
AKA: movement packet; logical change summaries
Legacy index:

keywords: tooling, closed, history, pulse, usability

Parent: `260806-support-review-consumers`
Depends on: `260806-correct-movement-evidence`
Blocked by:

# Group Movement Evidence for Consumers

Present factual movement as compact repository/change groups with descriptions,
paths, and completeness so consumers do not reconstruct meaning from repeated
low-level labels.

## Completion Evidence

- Added deterministic `movement_groups` to every pulse repository entry,
  grouping by jj logical `change_id` or native event key while preserving the
  complete base events array.
- Groups retain old/new version IDs, bounded descriptions, parent-relative
  path evidence, task-path events, publication-hint details, uncertainty, and
  native event keys. `comparison_incomplete` recovery/suppression evidence is
  excluded from movement groups and remains available in events/warnings.
- Human summaries render grouped descriptions, states, versions, and task
  paths; audit and JSON continue to retain all repository evidence and no-ops.
- `scripts/check` passed: Ruff format/lint, 387 tests, 100% statement and
  branch coverage, and `uv build` produced the source distribution and wheel.

## Decisions

- Grouping is a derived presentation projection; raw delta semantics and
  identifiers remain canonical and auditable.
- Publication events are attached as hints and never used to name or suppress
  unnamed jj logical-change groups.

## Allowed Write Surfaces

- pulse presentation/grouping modules under `src/vcs_tree/`
- focused tests and fixtures under `tests/`
- `docs/recurring-pulse.md` and movement contracts
- this task and `tasks/WORKBOARD.md`
