Filed as: 260729-enforce-total-coverage
FKA:
AKA: readable coverage report; 100 percent coverage gate
Legacy index:

keywords: tooling, active, pytest, coverage, quality

Parent: `260729-package-python-project`
Depends on: `260729-package-python-project`
Blocks:
Blocked by:
Related:

# Enforce Total Package Coverage

Raise the automated coverage requirement and make failures visually concise so
uncovered behavior is immediately apparent.

## Current Reality
The suite passes 26 tests at 88.12% branch coverage against an 85% gate. The
terminal report lists every package module, including fully covered modules.

## Desired Reality
The suite exercises every measured statement and branch, fails below 100%,
and suppresses fully covered files from the terminal detail table.

## Gap Analysis
Subprocess fallback paths, individual diff-stat branches, renderer variants,
and long-running collection states lack focused tests. The report configuration
does not use coverage.py's `skip-covered` view.

## Known Facts / Assumptions / Unknowns
- Fact: branch coverage is already enabled.
- Fact: the current misses are deterministic through mocks and fixtures.
- Assumption: the two-line `__main__` launcher should be exercised rather than
  omitted from measurement.

## Investigations
- Use the current missing-line and partial-branch report as the test inventory.

## Models / Forecasts / Risks
- Coverage must come from meaningful state assertions, not blanket exclusions.
- Timing tests need a deterministic fake clock and executor.

## Transformations
- Add focused tests for all currently unmeasured package behavior.
- Set the coverage failure threshold to 100%.
- Use `term-missing:skip-covered` for a compact success report.
- Update development documentation.

## Evidence
- `uv run pytest` passes 47 tests on Python 3.9.6 with 244/244
  statements and 76/76 branches covered.
- The successful terminal report contains only the aggregate `TOTAL` row and
  reports that four fully covered files were skipped.
- `uv run ruff check .` and `uv run ruff format --check .` pass.

## Decisions
- Measure the complete package, including the module launcher.
- Enforce `--cov-fail-under=100` and display
  `term-missing:skip-covered`.
- Use deterministic executor, future, and clock fakes to cover stall,
  background-deadline, cancellation, and worker-error behavior without slowing
  the suite.

## Open Fronts
None.

## Next Actions
- Keep the 100% gate green as package behavior expands.
