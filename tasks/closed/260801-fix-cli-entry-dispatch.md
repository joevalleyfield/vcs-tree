Filed as: 260801-fix-cli-entry-dispatch
FKA:
AKA: installed entry-point history dispatch
Legacy index:

keywords: tooling, closed, cli, bugfix, dispatch

Parent: `260728-movement-snapshot-package`
Depends on: `260801-integrate-history-cli`
Blocks:
Blocked by:
Related: `260801-integrate-history-cli`

# Fix Installed CLI History Dispatch

Ensure the installed `vcs-tree` entry point dispatches `history` commands when
`main()` receives its arguments from the process environment.

## Evidence
- `uv run vcs-tree history --help` currently falls through to the legacy parser.
- The explicit `main([...])` test path already dispatches correctly.
- `main()` now reads process arguments before dispatching, so the installed
  entry point exposes the history parser and subcommands.
- `uv run pytest -q`: 120 tests, 100.00% coverage; Ruff passes.
- `uv run vcs-tree history --help` lists init, inspect, snapshot, and delta.

## Allowed surfaces
- `src/vcs_tree/cli.py`, `tests/test_cli.py`, and this task file.
