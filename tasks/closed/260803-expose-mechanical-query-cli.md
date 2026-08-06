Filed as: 260803-expose-mechanical-query-cli
FKA:
AKA: history query command; evidence query rendering
Legacy index:

keywords: cli, closed, query, rendering, json, audit, summary

Parent: `260803-define-backlog-review-pressure`
Depends on: `260803-evaluate-mechanical-predicates`
Blocks: `260803-test-mechanical-query-workflow`
Blocked by:
Related: `260802-expose-pulse-output-workflow`; `260805-delta-presentation-surfaces`

# Expose the Mechanical Query Workflow

Add the public history query command and deterministic summary, audit, and JSON
surfaces without adding semantic review ranking or host scheduling.

## Command Contract

```text
vcs-tree history query [PATH]
    (--where JSON | --where-file PATH|-)
    [--snapshot SNAPSHOT]
    [--format summary|audit|json]
```

- `PATH` defaults to `.` and resolves canonically.
- Without `--snapshot`, the command captures one current v2 observation before
  evaluation, including the documented jj refresh/fallback behavior.
- With `--snapshot`, evaluation uses that retained snapshot/index boundary and
  performs no source-repository collection.
- `--where` and `--where-file` are mutually exclusive representations of the
  same canonical query document; `-` reads stdin.
- Summary is the default signal-first view, audit includes every repository and
  leaf result, and JSON is complete/deterministic.

## Acceptance Criteria

- Query parsing delegates semantic validation to the query model and reports
  actionable syntax/schema errors.
- Current capture identifies the retained target snapshot even when later
  evaluation/rendering fails.
- Explicit snapshot selection validates store, schema, scope, and index
  availability without silently selecting another generation.
- Summary counts true, false, and indeterminate repository evaluations and may
  omit false detail while reporting the omission.
- Audit and JSON include predicate evidence, temporal origins, component
  completeness, working-copy freshness, and refresh errors.
- Repository and predicate ordering is deterministic across input order and
  repeated runs at a fixed evaluation time.
- Complete true or false evaluation exits 0; usable partial/indeterminate exits
  3; operational failure exits 4; argparse/usage errors exit 2.
- A match is not a process failure, task assignment, review recommendation, or
  permission to mutate a repository.
- Existing default scanner, history snapshot/delta/list/pulse commands, and live
  resource wrapper remain behavior-compatible.

## Allowed Write Surfaces

- `src/vcs_tree/cli.py`
- one new query orchestration/rendering module under `src/vcs_tree/`
- `tests/test_cli.py`
- focused query orchestration/rendering tests under `tests/`
- `README.md`
- relevant query/presentation documentation under `docs/` and `planning/`
- this task file and `tasks/WORKBOARD.md`

Do not edit native adapters, temporal index construction, predicate semantics,
the baseline script, live resource files, host schedulers, or review logic.

## Required Fixtures

- Inline, file, and stdin query documents.
- Current capture, explicit retained snapshot, and first-observation query.
- True, false, mixed, and indeterminate multi-repository results.
- Post-capture evaluator/render failure retaining the target ID.
- Missing/wrong-scope/unsupported snapshot and malformed query documents.

## Completion Evidence

- Focused CLI/render tests cover every mode and exit branch.
- Golden summary/audit/JSON examples remain free of opinionated review labels.
- `scripts/check` passes with 100% statement and branch coverage.

## Decisions

- The public command owns capture-or-retained-boundary orchestration; semantic
  truth remains entirely in `PredicateEvaluator`.
- Summary is signal-first and reports omitted false repository detail; audit
  retains every repository result and JSON is the complete canonical envelope.
- A successful capture keeps its snapshot ID in an operational error response
  if evaluation fails. Explicit snapshots are validated and never replaced by
  another generation.

## Completion Evidence

- Added `history query [PATH]` with inline/file/stdin query input, retained
  snapshot selection, current v2 capture, summary/audit/JSON rendering, and
  exit codes 0/3/4/2 for complete, indeterminate, operational, and usage
  outcomes.
- Added focused CLI/orchestration tests for every input, renderer, snapshot
  validation, capture failure, and exit branch. Golden output contains only
  factual outcomes and provenance.
- `scripts/check` passes: 378 tests, 100% statement and branch coverage, Ruff,
  and package builds.

## Next Actions

- Claim `260803-test-mechanical-query-workflow`; exercise the installed command
  end to end against snapshot, working-copy, temporal, and rendering surfaces.
