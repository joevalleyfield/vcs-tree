Filed as: 260803-define-backlog-review-pressure
FKA: Define Backlog Review Pressure
AKA: mechanical review evidence, elapsed fact predicates, review-context substrate
Legacy index:

keywords: planning, closed, evidence, predicates, clocks, completeness, working-copy

Parent: `260728-movement-snapshot-package`
Depends on: `260802-recurring-movement-pulse`
Blocks: `260803-version-mechanical-evidence-schema`;
  `260803-collect-current-working-copy-evidence`;
  `260803-index-temporal-fact-intervals`;
  `260803-evaluate-mechanical-predicates`;
  `260803-expose-mechanical-query-cli`;
  `260803-test-mechanical-query-workflow`
Blocked by:
Related: `260803-center-pulse-on-jj-change-graphs`; `260804-history-observability-and-index`

# Define Mechanical Review Evidence

Define the deterministic repository facts, elapsed observer clocks, and
evidence-completeness predicates that an intelligent consumer needs when
performing opinionated backlog review. `vcs-tree` supplies factual context; it
does not decide which repositories warrant review.

## Current Reality

- Retained snapshots distinguish Git, jj, and colocated repositories and keep
  repository continuity, workspace targets, refs/bookmarks, jj logical-change
  graphs, native descriptions, task-path movement, and component outcomes.
- Deltas and pulse describe factual movement without deciding whether it is
  progress, priority, or project health.
- Snapshot collection retains enough state to collect additional native facts
  efficiently, but it does not expose a general mechanical-intent surface.
- Collection freshness, component completeness, fact confirmation, and
  movement do not yet have one explicit temporal model.
- Git collection reports current status evidence. jj collection always uses
  `--ignore-working-copy` and hard-codes working-copy state `unknown`, even
  though the recorded `@` commit and its diff remain mechanically observable.
- Existing contracts describe observation as universally read-only. That
  prevents the useful normal jj behavior of periodically snapshotting current
  filesystem state into `@`.
- The prior version of this task assigned pressure ranking, dispositions,
  cadence, and semantic `initial_commit_due` classification to `vcs-tree`.
  Those responsibilities conflict with the package's factual boundary.

## Desired Reality

Settle `planning/mechanical-review-evidence-v1.md` as the requirements source
for a deterministic query surface over:

- atomic repository facts and relationships;
- elapsed observer clocks and fact-validity intervals; and
- component completeness and working-copy freshness.

An intelligent consumer translates “which repositories warrant review?” into
mechanical predicates, evaluates the returned evidence, and may perform a
direct repository observation before reaching an opinionated conclusion.

`vcs-tree` may allow the normal native jj working-copy snapshot during
collection. When that refresh cannot run, it falls back to the recorded `@`,
preserves useful facts, and reports that filesystem freshness is stale or
indeterminate.

## Gap Analysis

- Component outcomes exist, but independently truth-valued facts do not retain
  confirmation intervals or tombstones.
- A single working-copy shape conflates workspace topology, recorded `@` state,
  and current filesystem freshness.
- No supported surface accepts consumer-selected mechanical predicates and
  returns true/false/indeterminate evidence.
- First observation, repeated partial collection, complete recovery, fact
  invalidation, and reappearance need consequence-backed temporal rules.
- Git unborn and jj root-parented working-copy states need symmetrical factual
  predicates without pretending their native models are identical.
- Existing read-only language needs a narrow, explicit jj snapshot exception
  without authorizing fetch, rewrite, repair, or review-driven mutation.

## Known Facts / Assumptions / Unknowns

### Facts

- The jj virtual root, Git unborn state, and repository-read errors are already
  distinct contract states.
- A jj working-copy `@` is a content-addressed commit version. “No commit object
  exists” is therefore not the jj predicate for work lacking its first durable
  boundary.
- `jj status` and `jj diff -r @` can snapshot and then describe current `@`;
  their `--ignore-working-copy` forms can describe a possibly stale recorded
  `@` without refreshing it.
- Partial evidence can support positive facts but cannot prove omitted facts
  absent.
- An explicit tombstone is useful evidence because it closes a previously
  active fact rather than leaving an unconfirmed loose end.

### Assumptions

- Mechanical predicate evaluation can remain deterministic without embedding
  semantic review categories.
- Atomic fact histories can be indexed without copying arbitrary repository
  file contents into the authoritative ledger.
- Normal jj working-copy snapshotting is an acceptable incidental observation
  side effect when it is reported and bounded.

### Unknowns

- None that block engineering dispatch. Snapshot v2, v1 normalization, derived
  temporal indexing, native working-copy paths, and generic-content deferral are
  settled in `planning/mechanical-review-dispatch.md`.

## Investigations

- Exercise the retained real corpus against candidate predicates without
  assigning review priority.
- Add controlled Git-unborn and jj-root-parented fixtures to distinguish native
  initial-boundary facts.
- Compare normal jj snapshot collection with stale-recorded fallback under
  writable, read-only, conflicted, and divergent-operation conditions.
- Inventory current component outcome boundaries and identify where working
  copy, workspace, graph, or path facts can fail independently.
- Validate fact identity and tombstone behavior for ref movement, deletion,
  recreation, partial collection, recovery, and repository continuity loss.
- Determine the compatible schema evolution path before implementation tasks
  claim source or tests.

## Models / Forecasts / Risks

- Repository-wide clocks are too coarse: one successful surface can hide a
  failed one.
- Per-command clocks are unstable: adapter implementation changes would alter
  public fact identity.
- Per-record clocks remain too coarse when independently truth-valued fields
  change separately.
- Atomized facts are more truthful and useful but require stable semantic keys
  and efficient interval indexing.
- Normal jj snapshotting improves freshness but is a real metadata side effect.
  Unreported fallback would make fresh and stale evidence indistinguishable.
- Storing review conclusions or arbitrary file contents would turn the ledger
  into a second knowledge or custody system and blur the package boundary.

## Transformations

- Replace the backlog-pressure contract direction with
  `planning/mechanical-review-evidence-v1.md`.
- Reconcile snapshot, nested-discovery, and pulse language around the narrow jj
  working-copy snapshot exception.
- Preserve canonical VCS terminology: refs/bookmarks are named pointers;
  object/commit IDs are targets; jj change IDs are logical identities.
- Define component attempt/completeness metadata, atomic fact confirmation
  intervals, explicit tombstones, and `never_observed` negative-infinity
  semantics.
- Define the factual Git-unborn and jj-root-parented premises that permit an
  intelligent consumer to conclude `initial_commit_due` after any required
  direct observation.
- Dispatch bounded implementation tasks only after schema compatibility and
  real-snapshot evidence are settled.

## Evidence

- Decision thought experiments cover first unreadable observation, repeated
  partial evidence, tombstones, reappearance, jj refresh fallback, and the
  root-parented jj working copy.
- A managed-sandbox trial made normal jj snapshotting fail on the read-only
  colocated object store while `--ignore-working-copy` still read a stale
  recorded `@`; an independent worktree check proved current contract edits.
  This grounds the refresh/fallback provenance requirement.
- Read-only corpus inspection found ten retained `/Users/tim/Documents`
  generations and 68 latest repositories: 46 colocated, 16 Git-only, and six
  jj-only.
- All 52 jj-capable latest records carry errored change-graph outcomes; 46
  colocated records mask that error behind aggregate Git history success.
- The retained object ledger contains 34,819 records with no embedded
  `first_observed` field. Generation 9-to-10 comparison produced 61 verified
  no-ops and seven explicit incomplete-history warnings.
- `planning/mechanical-review-dispatch.md` fixes schema v2, v1 compatibility,
  component granularity, temporal-index placement, query grammar, task graph,
  and deferred generic-content scope.
- Six bounded engineering task artifacts name dependencies, acceptance
  criteria, fixtures, allowed write surfaces, and completion evidence.
- Contract review finds no `vcs-tree`-owned pressure, disposition, cadence,
  health, routing, or semantic review conclusion.
- A real-snapshot trial identifies which predicates are already derivable and
  which components remain incomplete.
- Follow-on tasks name bounded source/test surfaces and fixtures.
- Documentation/task validation passes; no production source, tests, retained
  ledger, live resource command, or repository disposition changes while this
  parent remains in planning.

## Decisions

- `vcs-tree` owns factual repository collection and mechanical predicate
  evaluation, not opinionated backlog review.
- High-level review intent is translated by intelligent consumers into
  predicates over state, elapsed observer time, and completeness.
- A component is one independently collectible semantic completeness gate. An
  atomic fact is one independently truth-valued assertion.
- V2 component observations retain per-attempt time and outcomes. A rebuildable
  index derives attempt/completeness horizons and atomic fact confirmation
  intervals with explicit tombstones.
- “Never observed” compares as negative infinity but uses an explicit wire
  state rather than a fabricated timestamp.
- Partial collection refreshes only positive facts actually observed; it does
  not refresh component completeness or create tombstones.
- Normal jj working-copy snapshotting is allowed during collection. A failed or
  explicitly skipped refresh falls back to recorded `@` evidence with explicit
  stale/indeterminate filesystem freshness.
- `initial_commit_due` remains a consumer conclusion. `vcs-tree` supplies Git
  unborn or jj root-parented working-copy facts and their completeness.
- External review conclusions enter later observations only when another actor
  records them in the repository.

## Open Fronts

- None remain in this planning parent. Schema/model, collection, temporal index,
  predicate, CLI, and black-box work are owned by the six blocked/ready
  engineering tasks listed in `Blocks`.

## Allowed Write Surfaces

- `planning/`
- `docs/contracts/`
- this task file and `tasks/WORKBOARD.md`

## Next Actions

1. Claim `260803-version-mechanical-evidence-schema`.
2. After schema closure, claim working-copy collection and temporal indexing in
   parallel.
