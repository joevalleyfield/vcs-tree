Filed as: 260802-feature-behavioral-testing
FKA:
AKA: feature contract test matrix; component behavior coverage
Legacy index:

keywords: testing, ready, feature, behavior, contracts, adapters, cli

Parent: `260728-movement-snapshot-package`
Depends on: `260801-implement-history-contract-models`;
  `260801-build-local-history-ledger`; `260801-implement-git-history-adapter`;
  `260801-implement-jj-history-adapter`; `260801-collect-history-snapshots`;
  `260801-calculate-history-deltas`; `260801-integrate-history-cli`
Blocks: `260802-end-to-end-workflow-testing`
Blocked by:
Related:

# Feature-Level Behavioral Testing

Build a focused behavioral test matrix for the implemented v1 package
features, proving contract semantics at component boundaries without changing
production behavior.

## Goal

Make each supported feature and its failure policy directly testable: models,
machine-local ledger, Git/jj observations, colocated snapshots, factual deltas,
and additive CLI commands.

## Acceptance Criteria

- Tests cover valid and invalid contract documents, schema/version rejection,
  deterministic serialization, and null-root/error distinctions.
- Tests cover ledger identity, single-writer refusal, generation/snapshot
  invariants, checksummed corruption isolation, retention, and resolved
  location warnings.
- Tests cover Git and jj complete, partial, shallow, error, conflict, linked,
  and colocated observations without source-repository mutation.
- Tests cover snapshot generation publication, stable repository keys,
  immutable-object deduplication, and explicit component outcomes.
- Tests cover delta event ordering, ancestry movement, remote/off-current
  history, completeness suppression, and store compatibility failures.
- Tests cover CLI init/inspect/snapshot/delta output and non-zero partial/error
  behavior while preserving the default scanner invocation.
- The existing 100% statement and branch coverage gate remains passing.

## Allowed Write Surfaces

- `tests/`
- test-only fixtures under `tests/fixtures/`
- this task file and `tasks/WORKBOARD.md` for lifecycle evidence
- No production source changes, live resource changes, or new CLI semantics.

## Completion Evidence

- A concise feature-to-test matrix is recorded in the task evidence.
- `uv run pytest -q` passes with the configured 100% coverage gate.
- `uv run ruff check src/vcs_tree tests` passes.
- Tests demonstrate read-only behavior for repository adapters and explicit
  failure outcomes for corrupt/incomplete inputs.
