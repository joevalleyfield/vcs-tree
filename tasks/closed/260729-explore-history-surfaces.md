Filed as: 260729-explore-history-surfaces
FKA:
AKA: Git and jj history inventory; off-branch movement exploration
Legacy index:

keywords: tooling, investigation, active, contract, history, refs

Parent: `260728-movement-snapshot-package`
Depends on: `260729-package-python-project`
Blocks:
Blocked by:
Related:

# Explore Git and jj History Surfaces

Ground the movement contract in actual Git, jj, and colocated repository
outputs so it can detect fetched lines of work and activity outside the
current checkout.

## Current Reality
The parent task now requires a deduplicated observed-history model, but the
commands, identifiers, ref classes, visibility rules, and colocation behavior
have not been inventoried against representative repositories.

## Desired Reality
A local investigation note identifies the smallest factual surfaces needed to
collect:

- complete default-scope reachable history and parent edges;
- local and remote ref/bookmark targets;
- jj visible heads and both change and commit identities;
- current checkout identity;
- evidence that distinguishes newly fetched history from current-line work;
- gaps requiring fixtures or optional deeper collection.

## Gap Analysis
The conceptual model is strong enough to guide observation, but not yet strong
enough to freeze a manifest schema or divide implementation safely.

## Known Facts / Assumptions / Unknowns
- Fact: raw Git and jj commands may be used here as compatibility inspection.
- Fact: existing repositories are read-only; controlled temporary fixtures may
  fetch locally, create refs, or rewrite their own disposable history.
- Assumption: existing Git-only and colocated repositories provide enough
  initial evidence to narrow fixture design.
- Unknown: whether a representative jj-only repository is locally available.

## Investigations
- Record tool versions and native output for refs/bookmarks, graph edges,
  current checkout identity, remote surfaces, and visible heads.
- Compare Git and jj views of at least one colocated repository.
- Inspect a Git-only repository for tracking refs and reflog-only evidence.
- Identify fields that are factual, stable enough to normalize, or necessarily
  native.

## Models / Forecasts / Risks
- Human-oriented output is discovery evidence, not the future parser contract;
  machine templates or explicit formats should be identified where possible.
- `--all` and similarly named concepts may cover different visibility
  universes across tools.
- Local repositories may not exercise fetch, divergence, or abandoned-work
  cases; those become explicit fixture requirements rather than inferred facts.

## Transformations
- Write `planning/history-surface-exploration.md`.
- Update this task with findings, evidence, decisions, and remaining gaps.
- Do not edit package source or tests during this investigation.

## Allowed Write Surface
- `planning/history-surface-exploration.md`
- `tasks/open/260729-explore-history-surfaces.md`
- `tasks/WORKBOARD.md`

## Out of Bounds
- Package source and tests.
- Network fetches or mutations to non-fixture repositories.
- Final manifest schema selection.

## Evidence
- `planning/history-surface-exploration.md` records Git 2.54.0 and jj 0.42.0
  native surfaces from `vcs-tree`, `toas`, the linked `toas-dogfood`
  workspace, and Git-only `agent-boundaries`.
- The survey used `--ignore-working-copy` for jj and performed no fetches or
  repository mutations.
- Colocation evidence showed that naive Git `--all` included 7,145
  `refs/jj/keep/*` refs in `toas`, while explicit user-facing Git ref classes
  reached 1,448 commits and jj exposed 1,519 visible commits.
- Workspace evidence showed `.jj` without `.git` can be a linked workspace
  pointing at another path's repository store.
- The note enumerates controlled before/after fixtures required for fetch,
  off-current work, force movement, conflicts, divergence, hidden history,
  null root, and errors.
- Controlled Git fixtures confirmed fetch-introduced and local-only
  off-current work, annotated-tag peeling, non-ancestral force movement,
  ref deletion, and immediate loss of deleted-remote reflog visibility.
- A controlled jj fetch confirmed that new remote-only work appears as an
  untracked remote bookmark requiring `--all-remotes`; a subsequent fetch
  grounded fast-forward ancestry.
- Independent non-colocated jj fixtures confirmed the internal Git store,
  explicit null root, hidden rewrite predecessors, unbookmarked visible heads,
  divergent commit IDs sharing a change ID, and multi-target bookmark
  conflicts.
- No package source or tests were changed.

## Decisions
- Owner: Codex `/root`; claimed 2026-07-29.
- Treat the parent history-retention direction as the investigation objective,
  not as a finalized storage schema.
- Exclude raw Git `--all` from the default colocated collection surface.
- Separate repository/store identity from workspace identity.
- Retain commit ID for graph identity and jj change ID as a distinct logical
  identity.
- Keep the task active until controlled before/after fixtures ground the
  missing movement states.
- Classify ref transitions using prior/new target sets plus ancestry, not
  human-oriented fetch or reflog messages.
- Preserve annotated ref objects separately from peeled commit targets.
- Include jj untracked remote bookmarks, visible heads, and working copies in
  the default factual surface.
- Model jj bookmark targets as sets with explicit conflict state.

## Open Fronts
- Portable repository/store identity and retention-policy questions move
  forward into the manifest contract.
- Optional reflog and jj operation-history policy remains unresolved.
- Partial collection errors need explicit manifest placement.

## Next Actions
- Draft the first versioned history/snapshot/ref/delta contract in the parent
  task.
