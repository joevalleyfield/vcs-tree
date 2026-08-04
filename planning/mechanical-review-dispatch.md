# Mechanical Review Evidence Implementation Dispatch

Status: ready for engineering dispatch

Requirements source: `planning/mechanical-review-evidence-v1.md`

## Settled Architecture

The implementation uses snapshot schema v2. The change is not additive v1:

- working-copy topology, recorded state, refresh, and freshness gain required
  independent meanings;
- native Git and jj component outcomes can no longer be collapsed into one
  aggregate outcome that hides an error;
- working-copy path/conflict evidence and refresh provenance become required
  predicate inputs; and
- current v1 readers reject version 2 and discard unknown nested fields when
  round-tripping.

The schema task lands v2 types, validation, normalization, and mixed-version
reading while production collection continues to emit v1. The working-copy
collection task activates v2 writing only after it can populate every required
v2 component. Existing snapshots are never rewritten in place.

This dispatch decision supersedes the illustrative pending-extension wording in
`docs/contracts/history-snapshot-v1.md`: v2 stores per-observation
`attempted_at`; the rebuildable temporal index derives rolling
`last_attempted_at` and `complete_as_of`. The schema task owns the corresponding
contract reconciliation.

V1-to-v2 comparison is supported for facts shared by both schemas. A v1
normalizer assigns explicit `unknown` or `not_requested` to facts absent from
v1 and uses the most specific retained outcome instead of a misleading
aggregate. Unsupported v2-only absence or freshness claims become
`comparison_incomplete`; shared positive facts remain usable.

Snapshot `captured_at` is valid coarse observer time for facts and component
outcomes actually present in v1. V2 adds component `attempted_at` timestamps for
finer provenance. Neither timestamp is a native author/committer time.

## V2 Component Boundary

Repository collection outcomes are independently represented for:

- `identity`;
- `git_worktrees`;
- `jj_workspaces`;
- `working_copy` per workspace;
- `working_copy_refresh` per workspace;
- `git_refs`;
- `jj_bookmarks`;
- `jj_visible_heads`;
- `git_history`;
- `jj_history`; and
- requested `path_evidence`.

Combined presentation fields may remain, but they are derived views and MUST
NOT replace native component outcomes. A colocated Git success cannot turn a jj
history error into complete jj change-graph evidence.

Each attempted component outcome includes `attempted_at`. `complete_as_of` is
derived by the temporal index from the latest complete outcome; it is not
redundantly copied into every snapshot.

Each workspace carries:

```text
recorded state: clean | dirty | conflicted | unknown | unreadable
refresh: performed | skipped | failed | not_applicable
freshness: current | recorded_maybe_stale | unknown | not_applicable
entries outcome and bounded changed path/type/conflict facts
```

For jj, normal collection permits the native working-copy snapshot. Failure is
retained, followed by a no-refresh read of recorded `@`. For Git, status reads
the current index/worktree without optional index-refresh writes where the
native command supports that behavior.

## Temporal Index Boundary

Atomic fact intervals are a deterministic, rebuildable projection of retained
snapshots and deltas. They are not a second authoritative evidence source and
do not require rewriting old snapshots or immutable native objects.

The index retains stable fact keys, one or more validity intervals,
`first_observed_at`, `last_confirmed_at`, `invalidated_at`, source snapshot IDs,
component outcomes, and timestamp precision. It can be deleted and rebuilt
from retained compatible observations.

V1 seeding rules are conservative:

- the first retained snapshot has a prior boundary of `never_observed`;
- `captured_at` supplies snapshot-precision observer time for facts positively
  present in a component;
- v1 omissions create tombstones only when the relevant specific component is
  complete and not contradicted by a more specific partial/error outcome;
- hidden/masked jj errors remain incomplete rather than inheriting colocated
  Git completeness; and
- no author/committer timestamp substitutes for observer time.

The first implementation vocabulary covers repository/workspace existence,
workspace targets, working-copy state and path entries, Git refs and target
edges, jj bookmarks and target edges, visible heads, native objects and parent
edges, and jj change/version edges. Generic arbitrary file-content indexing is
deferred; working-copy and retained commit path evidence are sufficient for v1
mechanical review predicates.

## Predicate and CLI Boundary

Predicate evaluation returns `true`, `false`, or `indeterminate` with evidence.
The first public vocabulary covers:

- current fact existence or equality;
- activation, confirmation, invalidation, and reappearance within an explicit
  interval;
- elapsed time since current activation, last confirmation, invalidation, or
  observed transition, including `never_observed` negative-infinity semantics;
- component outcome, `complete_as_of`, and working-copy freshness; and
- conjunction/disjunction over explicitly supplied mechanical predicates.

The canonical query document has schema `vcs-tree.history-query`, version `1`,
a repository scope, and one `where` predicate. Boolean nodes are `all`, `any`,
and `not`. Leaf nodes are:

- `fact`, with a stable fact type, attribute selector, and requested
  `active`, `inactive`, or `ever_observed` state;
- `elapsed`, with a fact selector, clock (`current_interval_started`,
  `last_confirmed`, `last_invalidated`, or `last_transition`), numeric relation,
  and non-negative seconds; and
- `component`, with component name, field (`outcome`, `complete_as_of`, or
  `freshness`), relation, and value.

Evaluation uses three-valued logic: `not indeterminate` remains indeterminate;
`all` returns false when any child is false and otherwise preserves
indeterminate; `any` returns true when any child is true and otherwise preserves
indeterminate. A never-observed clock has a negative-infinity origin and
positive-infinity elapsed duration, so every finite lower-bound threshold
matches while the evidence still says `never_observed`.

No predicate is named for urgency, staleness, dormancy, health, priority, or
`initial_commit_due`.

The public command is provisionally:

```text
vcs-tree history query PATH --where JSON [--format summary|audit|json]
```

The exact argument framing may use a JSON file/stdin form if needed for safe
shell usage, but the task MUST keep one canonical JSON predicate document.
Summary is signal-first, audit includes false and indeterminate evaluations,
and JSON is complete and deterministic. Match/no-match is exit 0, usable
partial evidence is exit 3, operational failure is exit 4, and CLI usage stays
exit 2.

## Retained Corpus Trial

Read-only inspection of the machine-local ledger on 2026-08-03 found ten
retained `/Users/tim/Documents` generations through generation 10. The latest
snapshot contains 68 repositories:

| Mode | Repositories |
| --- | ---: |
| colocated | 46 |
| Git-only | 16 |
| jj-only | 6 |

Latest component outcomes report 61 complete, six error, and one partial
aggregate `history` components. More specific evidence shows all 52 jj-capable
repositories with `change_graph.outcome: error`; the six jj-only errors remain
visible while 46 colocated errors are masked by aggregate Git history success.
The v2 normalizer and collection task MUST prevent that unsupported promotion.

Across jj-capable records, 75 workspace entries are `unknown`, compared with 11
dirty, eight clean, and additional non-jj workspace records contributed by
colocation. Git-only records provide six clean, nine dirty, and one unknown
working-copy state. This grounds the independent working-copy component and jj
refresh work.

The object ledger contains 34,819 immutable records and none stores
`first_observed`. Generation counts and snapshot comparisons can identify some
newly visible objects, but the ledger does not provide query-ready atomic fact
intervals or tombstones.

Generation 9 to 10 comparison produced 61 verified no-op repositories and
seven `comparison_incomplete` warnings (six jj-only history errors and one
partial large repository). This proves existing deltas are usable predicate
input but are not a complete temporal index.

During contract editing, ordinary jj refresh failed in the managed sandbox
because the colocated Git object store was read-only. The no-refresh fallback
read recorded `@` and reported no changes while an independent non-refreshing
Git worktree check saw the edited files. This is the required refresh-failure
fixture shape.

## Task Graph

```text
260803-version-mechanical-evidence-schema
    ├── 260803-collect-current-working-copy-evidence
    └── 260803-index-temporal-fact-intervals
              └──────────────┬──────────────┘
                             v
             260803-evaluate-mechanical-predicates
                             |
                             v
             260803-expose-mechanical-query-cli
                             |
                             v
             260803-test-mechanical-query-workflow
```

The schema task is ready immediately. Working-copy collection and temporal
indexing become independently claimable after it closes. Predicate evaluation
requires both factual lanes. CLI integration and black-box testing follow in
order.

## Deferred Work

- Semantic review ranking, dispositions, cadence, wake signals, and routing
  remain outside `vcs-tree`.
- Generic arbitrary file-content retention is excluded. A future task may add a
  replaceable requested-content collector if dogfooding proves path and native
  object evidence insufficient.
- Cross-machine fact identity remains outside v2; local repository continuity
  rules continue to apply.
