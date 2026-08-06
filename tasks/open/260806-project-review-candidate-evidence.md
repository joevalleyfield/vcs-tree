Filed as: 260806-project-review-candidate-evidence
FKA:
AKA: current workspace boundary projection; factual candidate packet
Legacy index:

keywords: tooling, active, history, query, usability

Parent: `260806-support-review-consumers`
Related: `260803-evaluate-mechanical-predicates`;
  `260803-collect-current-working-copy-evidence`

# Project Review Candidate Evidence

Expose a supported factual projection for current-workspace review questions
without emitting review conclusions or requiring private-ledger joins.

## Current Reality

The facts needed to recognize Git-unborn and jj-root-parented work exist. The
real trial nevertheless joined repository keys to paths privately, inspected
snapshot JSON to relate the current workspace target to its exact parents, and
read truncated path arrays directly.

## Desired Reality

One supported request returns stable repository identity plus human path,
current workspace target and exact parents, working-copy state/freshness,
bounded paths, truncation/continuation evidence, relevant intervals, and
component completeness. It reports premises, never `initial_commit_due`.

## Investigations

- Compare query-language relation/binding, a typed current-workspace
  projection, and batch factual intent as replaceable designs.
- Determine the smallest continuation or requested-bound behavior needed for
  the 256-entry `NOAA-chart-reader/s57` case.
- Validate nested repositories and multiple jj workspace identities.

## Transformations

- Include path presentation with stable repository keys in supported results.
- Express current target-to-parent relationships without consumer-side ID
  extraction and a second query.
- Return working-copy path bounds, totals where known, truncation, freshness,
  and errors.
- Preserve three-valued completeness and native Git/jj distinctions.

## Evidence

- Supported output recovers the five substantive 2026-08-06 root-parented
  candidates and the empty parent-container distinction.
- Git-unborn and jj-root-parented fixtures are symmetrical but not conflated.
- A nested/multi-workspace fixture returns unambiguous paths and workspace keys.
- The external playbook no longer reads `repositories.json` or
  `snapshots.json` directly.
- No serialized field ranks or recommends review; `scripts/check` passes.

## Allowed Write Surfaces

- query/projection models and services under `src/vcs_tree/`
- focused query/projection tests and fixtures under `tests/`
- query and snapshot contracts/docs
- this task and `tasks/WORKBOARD.md`

## Next Actions

1. Settle the smallest public shape through fixtures before implementation.
