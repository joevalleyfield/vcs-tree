Filed as: 260802-document-recurring-pulse-adapters
FKA:
AKA: scheduled pulse guide; host consumers
Legacy index:

keywords: docs, historical, pulse, automation, scheduling, adapters

Parent: `260802-recurring-movement-pulse`
Depends on: `260802-expose-pulse-output-workflow`
Blocks:
Blocked by:
Related:

# Document Thin Recurring Pulse Adapters

Document how a host invokes and consumes the proven pulse CLI without moving
selection, warning, task-path, or assessment semantics outside the package.

## Acceptance Criteria

- Documentation shows one-shot interactive, background, and scheduled
  invocations using explicit scan and state roots.
- Examples cover summary for a person, JSON for a consumer, exit handling, log
  separation, locking/single-writer expectations, and recovery after partial or
  operational failure.
- Cron and launchd MAY appear as thin examples; no scheduler becomes a package
  dependency or source of pulse semantics.
- Host guidance treats exit `0` as a complete baseline/movement/empty result,
  `3` as usable partial evidence, and `4` as operational failure. It inspects
  JSON state rather than treating movement as failure.
- The guide states that source repositories are read-only, authoritative state
  is machine-local/single-writer, and cloud-synchronized repository trees do
  not synchronize pulse state.
- The guide does not prescribe progress, health, priority, notification, or
  retry judgments.

## Allowed Write Surfaces

- `docs/recurring-pulse.md`
- `README.md` links and concise operator guidance
- this task file and `tasks/WORKBOARD.md`

Do not add scheduler code, service files, dependencies, source/test changes,
Codex-specific core behavior, or live resource changes.

## Required Examples

- Foreground summary and JSON capture with separate stderr log.
- A shell-neutral argument table for scan root, state root, explicit source,
  format, and enrichment limits.
- Minimal cron and launchd adapter snippets that invoke the installed command
  and preserve its exit/output contract.
- Recovery instructions using `history inspect`, `history list`, and explicit
  `--from` without deleting or repairing retained state.

## Completion Evidence

- [x] All documented commands match installed `--help` output and are smoke-run
  against temporary state where safe.
- [x] Markdown link target and line-length checks pass (`README.md` points to
  the new guide; changed documentation lines are at most 100 characters).
- [x] Foreground summary, JSON plus separated stderr, `history init`,
  `history inspect`, and `history list` were mechanically run against a
  temporary initialized state root; both pulse formats returned baseline exit
  `0`.
- [x] Cron and launchd examples were reviewed statically because they require
  host-specific locking and service registration; neither adds package code or
  semantics.

## Decisions and evidence

- Added `docs/recurring-pulse.md` with explicit scan/state roots, exit handling,
  JSON inspection, bounds, single-writer/cloud-drive warnings, recovery, and
  thin cron/launchd adapters.
- Added one concise README link; no scheduler dependency, service file, source,
  test, or live-resource change was introduced.
