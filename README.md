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
