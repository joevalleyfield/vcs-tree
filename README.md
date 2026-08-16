# vcs-tree

`vcs-tree` inventories Git and Jujutsu repositories below a directory and
renders their working-copy state in one compact tree.

This repository is the incubation surface for turning the existing
`Resources/tools/vcs-tree.py` script into a reusable package. During
incubation, the resource script and its shell wrapper remain the live command.
The copy here may evolve without silently changing that operational surface.

## Current State

- The scanner is available as the importable `vcs_tree` package.
- Installing the project provides a `vcs-tree` command.
- `vcs-tree.py` remains an unchanged baseline copy of
  `../../Resources/tools/vcs-tree.py` for extraction compatibility checks.
- The resource script and wrapper remain the live operational command until a
  separately tasked cutover.

Run the packaged command without installing it globally:

  ```bash
  uv run vcs-tree ~/Documents
  ```

Use `--flat` to omit directory grouping and `--text-symbols` for ASCII repo
type markers. The module form is equivalent:

```bash
uv run python -m vcs_tree ~/Documents
```

The default scanner is still the compatibility-preserving invocation. The
durable observation and analysis workflows are grouped under `history`:

```bash
vcs-tree --help
vcs-tree history --help
```

## Capabilities and command reference

`vcs-tree` has two consumer surfaces:

- The operator CLI discovers Git, jj, colocated, nested, and linked-workspace
  state, persists versioned observations, and renders factual movement and
  evidence.
- The importable `vcs_tree` package exposes the same observation models and
  deterministic projections for callers that need to make their own review,
  scheduling, or health decisions.

### Scanner

```text
vcs-tree [PATH] [--flat] [--text-symbols]
```

Scans a directory and renders the current working-copy state. It writes only
the disposable renderer cache described below.

### Durable history workflows

All history commands accept `--state-root PATH`, which selects the
machine-local authoritative ledger. Initialize it once before collecting
snapshots:

```bash
vcs-tree history init --state-root PATH
vcs-tree history inspect --state-root PATH
```

| Command | Purpose | Output |
| --- | --- | --- |
| `history snapshot [PATH]` | Discover repositories and persist one observation | Canonical snapshot JSON on stdout; progress on stderr |
| `history list` | List retained snapshots without scanning repositories | Deterministic snapshot index JSON |
| `history delta --from ID --to ID` | Compare two retained observations | Signal-first summary; use `--format json` for the full contract |
| `history pulse [PATH]` | Capture a new observation and report movement since the selected baseline | Summary, `--format audit`, or canonical JSON |
| `history query [PATH]` | Evaluate factual temporal predicates | Summary, audit, or canonical query-result JSON |
| `history candidates [PATH]` | Project current working-copy evidence for review consumers | JSON by default or `--format summary` |

Useful workflow options include `history delta --all` for verified no-op
repositories, `history delta --events-only` for a compact event document,
`history pulse --from ID` for an explicit baseline, `history query --where
JSON` or `--where-file PATH` for predicates, and `history query --capture` to
collect the observation before evaluating it. `query` and `candidates` can
also target a retained snapshot with `--snapshot ID`.

History collection preserves incomplete and unreadable components as factual
outcomes rather than silently treating them as no movement. A complete
operation returns 0; an incomplete or partial observation generally returns
2 or 3 according to the command contract, and an operational failure returns
4. Inspect the emitted JSON and stderr diagnostics when a non-zero result
needs triage.

The normative formats and boundaries are:

- [History snapshot v1](docs/contracts/history-snapshot-v1.md) and
  [snapshot v2](docs/contracts/history-snapshot-v2.md) — retained
  observations, repository/workspace shape, completeness, and compatibility.
- [History delta v1](docs/contracts/history-delta-v1.md) — movement events,
  jj change graphs, refs, file evidence, and uncertainty.
- [History query v1](docs/contracts/history-query-v1.md) — factual predicates
  and result envelopes.
- [Temporal facts v1](docs/contracts/temporal-facts-v1.md) — rebuildable
  fact intervals and component evidence.
- [Nested discovery v1](docs/contracts/nested-discovery-v1.md) — ownership,
  aliases, deduplication, and scan boundaries.
- [Recurring pulse adapters](docs/recurring-pulse.md) — foreground,
  background, cron, and launchd invocation patterns.

### Importable API

The package API is intended for consumers that need structured facts rather
than terminal rendering. The main groups are:

- `SnapshotCollector`, `SnapshotEnvelope`, `SnapshotEnvelopeV2`, and the
  Git/jj adapters for collection and schema-aware observation.
- `HistoryLedger`, `HistoryDeltaCalculator`, and `TemporalIndexBuilder` for
  retained state, comparisons, and temporal projections.
- `PredicateEvaluator`, `HistoryQuery`, and predicate models for mechanical
  evidence evaluation.
- `PulseOrchestrator`, `PulseEnricher`, and
  `project_current_workspaces` for movement and current-workspace evidence.

These APIs provide facts and evidence; callers decide review priority,
project health, scheduling, and follow-up actions. Versioned documents under
`docs/contracts/` are the compatibility boundary. Internal helpers and the
incubation path are not supported integration surfaces.

## Local State Warning

The current command writes only a disposable renderer cache under
`$XDG_CACHE_HOME/vcs-tree` or `~/.cache/vcs-tree`. That cache is machine-local;
it does not follow repositories stored on a cloud-synchronized drive and may
be deleted without affecting repository history.

The planned history ledger, repository-key registry, and snapshot index are
different: they are authoritative vcs-tree state and will not be placed in an
evictable cache. V1 will default to one machine-local writer and will report
and warn about the resolved state, configuration, and cache locations. Shared
or multi-writer state is not enabled until that policy is explicitly changed.

## Development

The project supports Python 3.9 and newer. uv creates the local environment
from `pyproject.toml` and `uv.lock`:

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv build
```

Before committing code, run the repository-local gate:

```bash
scripts/check
```

It runs formatting, linting, the full 100% statement-and-branch coverage
suite, and the package build in order.

pytest enforces 100% statement and branch coverage for the package. Its
terminal report hides fully covered files, so any detail row points directly
to a regression. Ruff checks the extracted package and tests while deliberately
excluding `vcs-tree.py`, whose exact bytes are retained as compatibility
evidence.

The package layout is:

```text
src/vcs_tree/
├── cli.py       # argument parsing and installed entry point
└── scanner.py   # discovery, collection, rendering, and cache behavior
```

## Direction

The package should provide factual inputs for movement assessment:

- repository discovery across Git, jj, and colocated repositories;
- working-copy state and readable failure states;
- refs/bookmarks and their movement;
- versioned snapshots and snapshot-to-snapshot deltas;
- commit/change identifiers, timestamps, and short descriptions;
- file-level descriptions useful for recognizing task creation and closure.

Higher-level callers decide whether observed movement constitutes progress.
The package should not infer project health from cleanliness, activity, or
commit volume alone.

## Semantic States

Commit recency has three meaningful states:

- a real date means a repository has a real committed parent;
- jj's `00000000` null root means the repository is initialized but has no
  real commit yet;
- an explicit error means repository state could not be read.

These states must remain distinct in data and rendering.

## Incubation and Graduation

`Projects/vcs-tree/` is an incubation location. Once the CLI, versioned
snapshot format, Git/jj behavior, ref/delta semantics, and compatibility
story are stable, the package will likely graduate to
`Resources/tools/vcs-tree/`.

Consumers should eventually invoke an installed `vcs-tree` entry point rather
than depend on either filesystem location. No cutover is part of the bootstrap
task.

## Project Surfaces

- `AGENTS.md` — local operating rules
- `inbox/` — accepted project objectives and delegations
- `tasks/open/` — active and inception work
- `tasks/closed/` — completed task evidence
- `tasks/WORKBOARD.md` — current operational index
# History workflow

The additive `history` commands keep the existing scanner invocation intact:

```text
vcs-tree history init --state-root PATH
vcs-tree history inspect --state-root PATH
vcs-tree history snapshot --state-root PATH REPOSITORY
vcs-tree history list --state-root PATH
vcs-tree history delta --state-root PATH --from SNAPSHOT --to SNAPSHOT
vcs-tree history delta --state-root PATH --from SNAPSHOT --to SNAPSHOT --format json
```

Snapshot collection keeps JSON on stdout and emits concise discovery,
collection, persistence, and completion status on stderr. `history list` reads
the authoritative retained-snapshot index and reports deterministic IDs, paths,
timestamps, generations, outcomes, and store identity; it does not inspect or
repair disposable renderer cache files.

Delta commands default to a signal-first human summary using repository paths
relative to the scan root. Use `--all` to include verified no-op repositories,
`--format json` for the complete canonical document, or `--events-only` for a
compact machine-readable document containing only repositories with events.
Local continuity IDs remain available in JSON as secondary metadata.

For thin foreground, background, cron, and launchd host adapters, see
[`docs/recurring-pulse.md`](docs/recurring-pulse.md). The guide keeps scheduling
and assessment outside the package and calls out machine-local state explicitly.

Authoritative history state, repository keys, and writer enrollment are
machine-local. The command reports the resolved state, configuration, and
disposable cache locations and warns that these control structures do not
follow a cloud-synchronized repository tree. The renderer cache remains
disposable and is never promoted to authoritative history.
