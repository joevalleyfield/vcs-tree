Filed as: 260728-bootstrap-vcs-tree-incubator
FKA:
AKA: project bootstrap; package incubation scaffold
Legacy index:

keywords: tooling, migration, historical, maintainability, bootstrap

Parent:
Depends on:
Blocks:
Blocked by:
Related:

# Bootstrap the vcs-tree Incubator

Create an isolated project surface around a faithful copy of the live scanner
without changing or redirecting the existing resource command.

## Claim
Claimed by Engineer on 2026-07-28 for the bounded bootstrap transformation.

## Current Reality
`vcs-tree` is a 500-line Python script plus a shell wrapper under
`Resources/tools/`. It performs discovery, Git/jj collection, caching,
parallel execution, rendering, and CLI parsing in one file.

## Desired Reality
`Projects/vcs-tree/` is a nested Git+jj repository with the copied baseline,
project documentation, agent guidance, and standard task surfaces needed for
behavior-preserving package extraction.

## Gap Analysis
There is no isolated project, local operating contract, or task queue in which
the package refactor can proceed without changing the live resource command.

## Known Facts / Assumptions / Unknowns
- Fact: the live resource files must remain in place during incubation.
- Fact: the Python copy must initially be byte-identical.
- Assumption: the incubator will graduate back to `Resources/tools/` after
  stabilization.
- Unknown: the eventual installed-command and migration mechanism.

## Transformations
- Establish the project, inbox, docs, and task surfaces.
- Copy the current Python script unchanged.
- Initialize Git+jj colocation.
- Add the nested project to the Documents root allowlist.

## Evidence
- Source and copy SHA-256 both equal
  `d7cbfed62f9725cb99ade1075ffa954b0b2bc0ce5f8856713360bde6998bddd9`.
- `jj root` and `jj workspace root` both resolve to
  `/Users/tim/Documents/Projects/vcs-tree`.
- The copied script completed a scan of its own project in 0.1 seconds and
  reported the independent jj repository.
- The live wrapper remains at `Resources/tools/vcs-tree` with SHA-256
  `67c7d8782cc745b922a2298a3bcd682e52bd3e246b1caffb2518f88708eb8fe2`.
- `Documents/.gitignore` contains `Projects/vcs-tree/`.

## Decisions
- The live command is not redirected during bootstrap.
- Packaging and new movement semantics remain a follow-on.
- The incubator is an independent Git+jj colocated repository.

## Open Fronts
- Package/module extraction.
- Snapshot, ref, delta, and description models.
- Eventual graduation to Resources.

## Next Actions
- Continue through `260728-movement-snapshot-package`.
