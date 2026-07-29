Filed as: 260729-package-python-project
FKA:
AKA: src layout; pytest and ruff bootstrap; installable vcs-tree
Legacy index:

keywords: tooling, active, packaging, pytest, ruff, uv

Parent: `260728-movement-snapshot-package`
Depends on: `260728-bootstrap-vcs-tree-incubator`
Blocks:
Blocked by:
Related:

# Package the Existing Scanner

Extract the behavior-preserving scanner into an installable Python project so
later snapshot work has a tested package boundary.

## Current Reality
The scanner is a byte-identical standalone copy of the live resource script.
There is no importable package, installed command, project metadata, automated
test suite, or lint configuration.

## Desired Reality
The repository has a `src/` package, an installed `vcs-tree` command, pytest
coverage for the existing collection and rendering behavior, and reproducible
uv and Ruff configuration. The standalone baseline and live resource command
remain unchanged.

## Gap Analysis
The baseline's collection, rendering, caching, and argument parsing need
importable seams. Project metadata, development dependencies, documentation,
and automated verification need to be established around those seams.

## Known Facts / Assumptions / Unknowns
- Fact: this extraction must not introduce snapshot/ref/delta semantics.
- Fact: Git/jj colocation and null-root/error distinctions must remain intact.
- Assumption: Python 3.9 is the appropriate minimum because the current
  baseline runs on the workspace's system Python 3.9.
- Unknown: public API stability beyond the initial `vcs_tree` entry point is
  intentionally deferred.

## Investigations
- Map the complete standalone script into package module boundaries.
- Verify the available Python/uv toolchain before locking dependencies.

## Models / Forecasts / Risks
- Leaving the baseline intact provides a stable byte-level compatibility
  reference during extraction.
- Tests should isolate subprocess and time behavior rather than require local
  repository state or multi-second waits.

## Transformations
- Add build and tool metadata, lockfile, and ignore rules.
- Add an importable `vcs_tree` package and console entry point.
- Add focused pytest coverage and update usage/development documentation.

## Evidence
- `shasum -a 256 vcs-tree.py ../../Resources/tools/vcs-tree.py` reports
  `d7cbfed62f9725cb99ade1075ffa954b0b2bc0ce5f8856713360bde6998bddd9`
  for both files.
- `uv lock --check` resolves the committed lockfile successfully.
- `uv run pytest` passes 26 tests on Python 3.9.6 with 88.12% branch coverage,
  above the configured 85% gate.
- `uv run ruff check .` and `uv run ruff format --check .` pass.
- `uv build` produces both the 0.1.0 wheel and source distribution.
- Artifact inspection confirms the wheel contains only the importable package
  and distribution metadata, while the source archive's explicit allowlist
  excludes repository administration data.
- `uv run vcs-tree --help` exposes the installed command and documented
  options.
- The baseline and packaged commands both smoke-scan an empty directory and
  render the same `(done @ 0.0s)` tree output.

## Decisions
- Preserve `vcs-tree.py` as the unchanged extraction baseline.
- Keep the first package release behavior-only; movement snapshots remain with
  the parent inception task.
- Support Python 3.9+ and test against the workspace's Python 3.9.6.
- Keep the package dependency-free at runtime; pytest, pytest-cov, Ruff, and
  Hatchling are locked development/build dependencies.
- Exclude only the immutable baseline script from Ruff so its compatibility
  hash remains meaningful.
- Use an explicit source-distribution allowlist so Hatch cannot package `.jj`
  internals or project coordination artifacts.

## Open Fronts
- Snapshot/ref/delta contract and cache migration remain in the parent task.

## Next Actions
- Continue the snapshot/ref/delta contract investigation in the parent task.
