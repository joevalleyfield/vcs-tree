Filed as: 260802-expose-pulse-output-workflow
FKA:
AKA: pulse CLI; pulse rendering; pulse e2e
Legacy index:

keywords: cli, blocked, pulse, json, rendering, e2e, exits

Parent: `260802-recurring-movement-pulse`
Depends on: `260802-implement-pulse-orchestration`; `260802-enrich-pulse-movement-evidence`; `260802-classify-pulse-task-warnings`; `260803-integrate-change-graph-pulse`
Blocks: `260802-document-recurring-pulse-adapters`
Blocked by: jj change-graph pulse integration
Related: `260805-delta-presentation-surfaces`

# Expose and Validate the Pulse Output Workflow

Add the public command, stable JSON, concise summary, audit rendering, exit
behavior, and black-box evidence for the full pulse workflow.

## Acceptance Criteria

- The installed entry point accepts the complete `history pulse` syntax in the
  v1 plan while the default scanner and existing history commands remain
  compatible.
- Stdout contains only summary, audit, or JSON; progress and location warnings
  remain on stderr.
- Summary is signal-first, collapses verified no-ops, groups warnings as new,
  persistent, and recovered, and never uses progress/health language.
- Audit and JSON retain every repository, event key, native ID, description,
  parent-relative path, task-path event, and warning.
- JSON validates the v1 envelope and is byte-stable for fixed clocks/IDs and
  equivalent unordered inputs.
- Exit `0` covers complete movement, empty, and baseline states; `3` covers a
  usable partial pulse; `4` covers operational failure; argparse retains `2`
  for usage errors.
- Explicit comparison mismatch fails before collection. Post-capture failure
  reports the retained target snapshot when available.
- The command never mutates controlled Git, jj, or colocated source fixtures.

## Allowed Write Surfaces

- `src/vcs_tree/cli.py`
- `src/vcs_tree/pulse_render.py`
- `tests/test_cli.py`
- `tests/test_e2e_workflow.py`
- `tests/test_pulse_render.py`
- `README.md` for command reference only
- this task file and `tasks/WORKBOARD.md`

Do not edit collection/ledger semantics, task/warning classifiers, scheduler
adapters, the baseline script, or live resource files.

## Required Fixtures

- Installed-CLI temporary state with controlled Git-only and colocated
  repositories for baseline, movement, empty, and partial pulses.
- A bookmark-free jj-only repository with unnamed stack growth, rewrite, and
  rebase movement plus a partial publication-hint case.
- The generation-7-to-8 shape with commit `aea6409b`, summary
  `chore: reconcile task workboard`, a workboard modification, and a direct
  closed-task-path addition.
- Explicit missing/scope-mismatched source snapshots and a forced post-capture
  enrichment failure.
- Before/after hashes or status evidence proving fixture repositories and
  `vcs-tree.py` remain unchanged.

## Completion Evidence

- Golden summary, audit, and JSON assertions for movement, empty, partial, and
  baseline workflows.
- Installed CLI help and subprocess evidence for exit codes `0`, `2`, `3`, and
  `4`.
- Full `scripts/check` success with 100% statement and branch coverage.
- Task closure records the exact test count and source-immutability evidence.
