Filed as: 260806-correct-movement-evidence
FKA:
AKA: false movement regression; recovery versus movement
Legacy index:

keywords: tooling, active, history, pulse, correctness

Parent: `260806-support-review-consumers`
Blocks: `260806-group-movement-evidence`
Related: `260806-history-completeness-and-bookmarks`

Claimed by Engineer on 2026-08-06 for the bounded movement-evidence correction.

# Correct Movement Evidence

Ensure pulse and delta report repository-state transitions rather than
identical states or facts that merely became observable after incomplete
collection.

## Current Reality

In the retained generation 12-to-13 trial, `steward-auth` produced dozens of
introduced change-version events as history recovered from error to complete.
`zed`, `mermaid-kinetic-parser`, and `rhizome` produced divergent-version
events whose old and new visible commit sets were identical. Pulse presented
these as movement.

## Desired Reality

Identical before/after factual state is a no-op. Collection recovery is a
separate factual lifecycle event and cannot establish repository movement
without supporting comparison evidence.

## Known Facts / Assumptions / Unknowns

- Fact: partial/error evidence cannot prove absence in the earlier snapshot.
- Fact: equal old/new version sets contain no version-membership transition.
- Assumption: recovery deserves visibility in uncertainty/observation output.
- Unknown: whether existing `comparison_incomplete` plus recovered warning
  lifecycle is sufficient or needs a dedicated factual recovery event.

## Investigations

- Trace generation 12-to-13 event derivation for the four named repositories.
- Reduce identical-divergence and error-to-complete cases to minimal Git/jj
  fixtures.
- Check workspace-head, topology, publication-hint, task-path, and enrichment
  layers for the same absence/recovery mistake.

## Transformations

- Enforce before/after inequality for every movement event.
- Gate newly observable historical facts across incomplete boundaries.
- Preserve recovery and uncertainty without counting them as movement.
- Reconcile pulse repository movement state and summary counts.

## Completion Evidence

- Focused jj graph fixtures cover equal divergent version sets, partial-to-
  complete recovery, and complete-to-partial observation. Recovery now emits
  an indeterminate `comparison_incomplete` event rather than introduced or
  visibility movement; equal version sets emit no event.
- Graph incompleteness is explicit and suppresses newly observable version and
  visible-head additions, while complete graph changes remain visible.
- The full suite passes with 384 tests and 100% statement and branch coverage.
- Ruff format and lint pass, and `uv build` successfully produces the source
  distribution and wheel. The repository's `.codex-local/bin/uvt` wrapper is
  absent, so the equivalent `uv` commands used `UV_CACHE_DIR=/tmp/vcs-tree-uv-cache`.

## Decisions

- Existing `comparison_incomplete` is sufficient recovery visibility; no new
  recovery event vocabulary is needed.
- A graph event requires complete before/after graph evidence when it asserts
  appearance or disappearance. A changed topology remains available as an
  indeterminate factual comparison when both versions are present.

## Allowed Write Surfaces

- movement/delta/pulse modules under `src/vcs_tree/`
- focused movement tests and fixtures under `tests/`
- movement contracts/docs if semantics require clarification
- this task and `tasks/WORKBOARD.md`
