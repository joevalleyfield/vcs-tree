Filed as: 260803-center-pulse-on-jj-change-graphs
FKA:
AKA: jj-first pulse semantics; unnamed change stacks
Legacy index:

keywords: planning, active, pulse, jj, changes, stacks, topology, contract

Parent: `260802-recurring-movement-pulse`
Depends on:
Blocks: `260803-persist-jj-change-graph`; `260803-calculate-jj-change-deltas`; `260803-separate-publication-hints`; `260803-integrate-change-graph-pulse`; `260802-expose-pulse-output-workflow`
Blocked by:
Related: `260806-history-completeness-and-bookmarks`

# Center Pulse on jj Change Graphs

Correct the pulse contract before its public CLI is exposed. In a jj repository,
logical changes and their visible graph are the primary movement surface.
Bookmarks are optional publication hints; unnamed stacks must remain fully
observable without them.

## Grounded Pressure

The current contract names change-version and visible-head events, but the
implemented real-snapshot path does not yet carry those facts through delta and
pulse. Collection and completeness policy still gives bookmarks/ref sets too
much authority over the account of repository movement.

This is a correction to the existing pulse trajectory, not a parallel product.
Completed orchestration, enrichment, and task/warning semantics remain useful,
but public rendering must wait until they consume a jj change-centered delta.

## Contract Decisions to Settle

- Define a logical change by jj `change_id`, preserving every observed commit
  version rather than selecting one preferred version.
- Define unnamed stack/topology observations from visible changes, parent
  edges, visible heads, and workspace heads without inventing a named stack
  object that jj does not provide.
- Define factual events for first observation, version replacement, divergence,
  topology/parent change, visibility gain/loss, and visible-head movement.
- Distinguish positive observation from absence claims under partial
  collection. Validly observed change movement remains reportable even when an
  unrelated record or authority is unavailable.
- Treat Git refs and jj bookmarks as separate authorities in colocated
  repositories. Bookmarks annotate tentative/observed publication state and do
  not gate change-graph movement.
- Preserve the jj null root as a virtual graph boundary without a fabricated
  date, description, or ordinary change event.

## Acceptance Criteria

- `planning/recurring-pulse-v1.md` and the history contracts make the jj change
  graph the normative primary movement surface.
- Bookmark/ref completeness can suppress only publication/ref claims, never an
  otherwise supported change, rewrite, topology, workspace, or visible-head
  claim.
- The contract distinguishes local bookmark intent, tracked state, and observed
  remote bookmark state without claiming publication from weak evidence.
- A bookmark-free fixture specifies an unnamed stack growing, rewriting,
  rebasing, and gaining a sibling stack; every movement remains describable.
- A partial-bookmark fixture specifies valid observed target movement plus an
  unrelated malformed/unavailable bookmark and fixes which positive and absence
  claims remain supported.
- The four follow-on tasks remain bounded, ordered, and independently claimable.
- No production source, tests, retained ledger, or live resource command changes
  while this requirements correction is active.

## Allowed Write Surfaces

- `planning/recurring-pulse-v1.md`
- `docs/contracts/history-snapshot-v1.md`
- `docs/contracts/history-delta-v1.md`
- this task file and `tasks/WORKBOARD.md`

## Completion Evidence

- Before/after contract examples for bookmark-free, rewritten, divergent,
  partially observed, and colocated publication-hint cases.
- A vocabulary table maps each event to its required evidence and exact
  completeness gate.
- Closure records any schema-compatibility decision required by the correction.

