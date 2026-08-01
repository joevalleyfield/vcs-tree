Filed as: 260805-delta-presentation-surfaces
FKA:
AKA: scan-relative delta view; signal-to-noise output
Legacy index:

keywords: cli, ready, delta, presentation, scan-relative, identity, json, summary

Parent: `260728-movement-snapshot-package`
Depends on: `260804-history-observability-and-index`; `260801-calculate-history-deltas`
Blocks:
Blocked by:
Related: `260803-restore-nested-repository-reporting`

# Formalize Signal-to-Noise Delta Presentations

Separate operator-facing movement summaries from complete machine-readable
delta documents while retaining an auditable way to inspect verified no-ops.

## Current Reality

`history delta` emits full JSON by default. Repository deltas are keyed by
opaque machine-local identifiers such as `repo-0061`; empty repository entries
are included alongside events; repository paths are present only in the source
snapshots. The delta already records certainty and explicit incomplete
comparison events, but an operator must reconstruct repository identity and
discard no-ops manually.

## Desired Reality

The default interactive delta view is concise and scan-relative. A repository
is headed by its path relative to the snapshot scan root (with `.` for the
root), followed by mode and observed events. Durable local continuity IDs stay
available as secondary metadata and never become the headline identity.

The CLI also offers explicit complete and audit-oriented views:

- default summary: changed repositories and aggregate uncertainty only;
- `--all`: summary including verified no-op repositories;
- `--format json`: canonical full JSON, including empty entries;
- `--events-only`: compact machine-readable JSON containing only repositories
  with events plus aggregate completeness warnings.

## Gap Analysis

- Delta rendering has no presentation mode or scan-relative repository path.
- Opaque local keys are the only repository identity in delta output.
- No-op entries overwhelm the default operator view.
- JSON is useful for interchange but is a poor default reading surface.

## Known Facts / Assumptions / Unknowns

- Local repository keys remain useful for exact matching and object joins, but
  they are not clone identities and should remain secondary in output.
- Relative paths must be computed against each snapshot's recorded scan root;
  differing roots require an explicit path-comparison warning rather than a
  misleading relative path.
- Existing JSON consumers need an additive compatibility path while the
  interactive default changes.
- The final option spelling and TTY-vs-pipe default behavior need confirmation
  during implementation, with explicit flags remaining the stable contract.

## Acceptance Criteria

- Delta repository records expose a scan-relative display path and repository
  mode without requiring a ledger lookup.
- The default human view suppresses no-ops, groups events by path, and makes
  `observed`, `indeterminate`, and suppressed-event warnings legible.
- An explicit audit view shows verified no-ops and reports their count.
- Canonical JSON remains available with all repository entries and durable
  local identity metadata; compact JSON omits no-op entries only when asked.
- Root mismatch, missing path metadata, and incomplete components are explicit
  warnings; they never become silent “no change” results.
- Snapshot/delta machine-readable contracts remain parseable and existing
  callers can select the full JSON behavior explicitly.

## Allowed Write Surfaces

- `src/vcs_tree/` presentation models, CLI formatting, and path projection
- `tests/` and test-only fixtures
- `docs/contracts/` and `README.md` for the additive output contract
- this task file and `tasks/WORKBOARD.md`
- No live resource cutover, ledger retention change, repository mutation, or
  durable-ID policy expansion beyond local continuity metadata.

## Completion Evidence

- Focused tests cover default summary, audit no-ops, full JSON, compact JSON,
  relative-root handling, root mismatch, and incomplete/unknown events.
- An installed-CLI fixture demonstrates that a noisy multi-repository delta
  renders as one concise movement report while `--all` recovers the no-ops.
- Contract examples show path, mode, local identity, certainty, and warning
  placement.
- `uv run ruff check src/vcs_tree tests` and `uv run pytest -q` pass with the
  repository's 100% statement and branch coverage gate.

## Decisions

- Presentation identity is scan-relative path; local continuity identity is
  secondary metadata.
- No-ops remain inspectable but are not the no-args headline.
- Full JSON remains an explicit compatibility surface rather than being
  removed.

## Open Fronts

- Decide whether the human summary is selected by TTY detection or is always
  the no-args mode, with `--format json` as the deterministic escape hatch.
- Decide whether snapshot listing receives the same summary/JSON dual surface.

## Next Actions

1. Claim this task and specify the presentation schema examples.
2. Implement path projection and the four output modes with focused tests.
3. Add installed-CLI end-to-end coverage and update operator documentation.
