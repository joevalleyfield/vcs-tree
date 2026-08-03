Filed as: 260803-integrate-change-graph-pulse
FKA:
AKA: jj-first pulse integration; change-stack movement brief
Legacy index:

keywords: tooling, ready, follow-on, pulse, jj, integration, enrichment, warnings

Parent: `260803-center-pulse-on-jj-change-graphs`
Depends on: `260803-calculate-jj-change-deltas`; `260803-separate-publication-hints`
Blocks: `260802-expose-pulse-output-workflow`
Blocked by:
Related: `260802-enrich-pulse-movement-evidence`; `260802-classify-pulse-task-warnings`

# Integrate jj Change Graph Movement into Pulse

Adapt the completed pulse orchestration, enrichment, and warning semantics to
consume the jj-first delta before public CLI/rendering work begins.

## Acceptance Criteria

- Delta-relevant logical changes and every visible commit version receive
  descriptions and parent-relative path evidence within existing bounds.
- Pulse repository entries retain change/version/topology events independently
  of optional publication hints.
- Movement counts include factual movement events and exclude warning-only
  `comparison_incomplete` events.
- `movement.state` is `observed` when any supported movement exists, including
  under an overall partial outcome; it is `unknown` when uncertainty prevents
  deciding whether movement occurred and no movement was observed.
- Warning identities distinguish change graph, enrichment, and publication
  surfaces so persistent bookmark uncertainty does not obscure new change-stack
  movement.
- Existing task-path derivation consumes changed-path evidence from rewritten or
  rebased jj versions without inferring intent or collapsing merge parents.
- Git-only and generation-7-to-8 behavior remain compatible.

## Allowed Write Surfaces

- `src/vcs_tree/pulse.py`
- `src/vcs_tree/enrichment.py`
- `src/vcs_tree/pulse_semantics.py`
- `src/vcs_tree/models.py` only for parent-approved pulse records
- `tests/test_pulse.py`
- `tests/test_enrichment.py`
- `tests/test_pulse_semantics.py`
- this task file and `tasks/WORKBOARD.md`

Do not expose the CLI, implement renderers/host adapters, alter collection or
base delta semantics, or edit live resource files.

## Required Fixtures

- Bookmark-free unnamed stack growth and rewrite with descriptions and paths.
- Observed stack movement plus partial publication hints, producing
  `movement: observed` and a usable partial result.
- Warning-only incompleteness producing `movement: unknown`, not observed.
- Colocated change versions mapped to Git object/path evidence.

## Completion Evidence

- Pulse envelope tests cover complete/partial/unknown movement combinations and
  deterministic counts.
- Regression evidence covers prior enrichment, task-path, and warning fixtures.
- Full `scripts/check` success with 100% statement and branch coverage.
