Filed as: 260816-document-discoverability
FKA:
AKA: capability-discoverability, command-reference
Legacy index:

keywords: active, documentation, discoverability, cli, history, pulse, query

Parent:
Depends on:
Blocks:
Blocked by:
Related: 260806-support-review-consumers, 260803-expose-mechanical-query-cli

# Document the complete vcs-tree capability surface

Make the package's implemented history, pulse, query, and workspace-evidence
capabilities discoverable to operators and downstream consumers.

## Current Reality

The installed CLI supports the original scanner plus eight history commands:
`init`, `inspect`, `snapshot`, `delta`, `list`, `pulse`, `query`, and
`candidates`. Top-level help documents only the original scanner. The README
documents only the first five history commands. Pulse, mechanical query, and
current-workspace evidence guidance is distributed across planning notes,
contracts, and the recurring-pulse guide.

The package also exposes a substantial importable API for snapshot envelopes,
temporal facts, predicate evaluation, Git/jj adapters, pulse orchestration,
and workspace projections, but the README describes the package primarily as
a scanner.

## Desired Reality

An operator who starts with `vcs-tree --help` or the README can discover the
complete supported command surface, understand which workflows are intended
for operators versus library consumers, and follow links to the normative
contracts and operational guides for deeper details.

## Gap Analysis

- Top-level help does not advertise the `history` command family.
- History subcommands have uneven help text and several options lack
  explanations.
- README examples omit `pulse`, `query`, and `candidates`.
- There is no concise command/reference section mapping workflows to their
  outputs, state requirements, and relevant documentation.
- The importable API and its stability boundary are not summarized for
  downstream consumers.

## Known Facts / Assumptions / Unknowns

Facts:

- `src/vcs_tree/cli.py` defines all eight history subcommands.
- `planning/recurring-pulse-v1.md`,
  `planning/mechanical-review-dispatch.md`, and `docs/recurring-pulse.md`
  contain workflow-specific guidance.
- Versioned contracts exist under `docs/contracts/`.

Assumptions:

- This task is documentation and help-surface work; it does not change
  command semantics or cut over the live resource command.
- The existing command names and output formats remain the supported surface.

Unknowns:

- Whether every public Python symbol should be documented individually or
  only grouped by consumer workflow.

## Investigations

- Compare every parser branch and option in `src/vcs_tree/cli.py` with README
  examples and help output.
- Confirm links and examples against the current contracts and recurring
  workflow guides.
- Identify any command behavior whose discoverability requires a warning,
  state initialization, or explicit snapshot selection.

## Models / Forecasts / Risks

The primary risk is documenting internal implementation details as stable
operator features. Keep the reference centered on supported commands and
versioned contracts; describe the Python API at the level of supported
consumer groupings and preserve the incubation/cutover boundary.

## Transformations

- Add `history` to the top-level CLI help or otherwise make the command family
  visible from the default entry point.
- Add a README capability map and command reference covering all history
  subcommands, common options, output modes, state behavior, and exit states.
- Link pulse, query, nested-discovery, snapshot, delta, and temporal contracts
  from the relevant reference sections.
- Add a concise importable-API overview and clarify which files are normative
  contracts versus implementation details.
- Add or update smoke checks for help output and documentation links/examples
  as appropriate without weakening the existing source gate.

## Evidence

- `vcs-tree --help` reveals the history workflow.
- Each supported history subcommand is represented in the README with a
  runnable synopsis and a link to deeper guidance where applicable.
- README references resolve to existing files and examples match the parser.
- `scripts/check` passes when source or tests are changed; otherwise the
  applicable documentation/task checks pass.

## Decisions

- Filed as a focused documentation/discoverability task rather than expanding
  command semantics.
- Preserve the live resource script and wrapper boundary during the work.

## Open Fronts

- Decide whether top-level help should gain a true `history` subparser or a
  concise epilog while preserving the scanner's positional compatibility.

## Next Actions

- Audit the current help output and README against the parser.
- Implement the smallest coherent help and documentation update.
- Verify links, examples, and command help, then close this task with evidence.
