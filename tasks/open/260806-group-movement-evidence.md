Filed as: 260806-group-movement-evidence
FKA:
AKA: movement packet; logical change summaries
Legacy index:

keywords: tooling, blocked, history, pulse, usability

Parent: `260806-support-review-consumers`
Depends on: `260806-correct-movement-evidence`
Blocked by: `260806-correct-movement-evidence`

# Group Movement Evidence for Consumers

Present factual movement as compact repository/change groups with descriptions,
paths, and completeness so consumers do not reconstruct meaning from repeated
low-level labels.

## Current Reality

The 2026-08-06 pulse repeated `change_versions_changed` dozens of times for one
repository. Detailed events retain identifiers but the human summary omits the
descriptions and grouping needed for movement assessment.

## Desired Reality

Summary, audit, and JSON preserve one canonical factual model while allowing a
consumer to see repository groups, logical jj changes or Git objects, old/new
versions, short descriptions, task-path evidence, publication hints, and
uncertainty without losing native identifiers.

## Models / Forecasts / Risks

- Grouping must not merge unrelated changes or hide divergent versions.
- Descriptions are repository-authored facts, not progress judgments.
- Presentation-only compaction must not fork machine semantics.

## Transformations

- Define deterministic repository/change grouping over corrected events.
- Attach already-retained bounded enrichment and task-path evidence.
- Keep observation recovery and suppressed evidence outside movement groups.
- Render signal-first summaries with audit access to every contributing event.

## Evidence

- A many-change repository produces a compact readable group, not repeated
  indistinguishable lines.
- Unnamed jj stacks remain primary; bookmarks remain publication hints.
- Merge parents and divergent versions retain separate evidence.
- JSON round-trips all contributing event identifiers.
- `scripts/check` passes.

## Allowed Write Surfaces

- pulse presentation/grouping modules under `src/vcs_tree/`
- focused tests and fixtures under `tests/`
- `docs/recurring-pulse.md` and movement contracts
- this task and `tasks/WORKBOARD.md`

## Next Actions

1. Claim only after movement-correctness semantics close.
