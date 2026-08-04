# Mechanical Review Evidence v1

Status: settled for engineering dispatch

Implementation dispatch: `planning/mechanical-review-dispatch.md`

## Purpose

An intelligent consumer may ask a judgment-bearing question such as “which
repositories warrant review?” `vcs-tree` does not answer that question. It
provides deterministic predicates over repository facts so the consumer can
answer it with the relevant evidence at hand and, when necessary, one direct
observation of its own.

This contract corrects the earlier backlog-pressure direction. Review pressure,
priority, health, disposition, cadence, and routing remain consumer concerns.
`vcs-tree` owns factual collection, retained observation continuity,
completeness, and mechanical predicate evaluation.

## Boundary

The boundary is:

```text
intelligent review intent
    -> consumer-selected mechanical predicates
    -> vcs-tree factual results and completeness
    -> consumer interpretation or direct follow-up observation
```

The package MUST NOT:

- label a repository stale, urgent, dormant, healthy, abandoned, or worthy of
  review;
- emit `initial_commit_due`, `contextual_review_required`, or another semantic
  review conclusion;
- rank results by inferred pressure or suggest a handling class;
- retain external review conclusions, dispositions, wake signals, or priority;
  or
- write review evidence into scanned repositories.

The package MAY expose literal repository-authored text carrying those words.
Doing so reports repository content; it does not adopt the content as a
`vcs-tree` conclusion.

## Mechanical Intent

A mechanical intent selects deterministic predicates from three factual
domains:

1. repository state and relationships;
2. elapsed observer clocks; and
3. evidence completeness and freshness.

Every result is `true`, `false`, or `indeterminate`. `false` requires enough
complete evidence to disprove the predicate. Missing, partial, stale, or
unreadable evidence produces `indeterminate` when it prevents either supported
answer.

A result includes the matching atomic facts, observation or delta identifiers,
clock origins, collection outcomes, and any limit or freshness boundary. A
match is not a review judgment.

The initial predicate families SHOULD cover:

- repository mode, continuity, location, and first observation;
- workspace existence, current commit/change, parents, and conflicts;
- recorded working-copy changes and changed paths;
- Git ref and jj bookmark existence, targets, conflicts, and tracking;
- jj visible heads, logical changes, versions, and parent relationships;
- native commit/object existence, descriptions, timestamps, and graph edges;
- fact activation, confirmation, invalidation, and reappearance within an
  explicit interval; and
- component outcome, completeness horizon, and working-copy freshness.

Core operation is request/response. Scheduling, publication, subscription,
notification, review cadence, and routing belong to hosts and intelligent
consumers. Hosts may publish factual results without changing their meaning.

## Canonical Vocabulary

Native domain terminology is normative:

- A Git **ref** is a named pointer.
- A jj **bookmark** is a named pointer.
- An **object ID** or **commit ID** is the content-addressed target.
- A jj **change ID** identifies one logical change with one or more commit
  versions.
- A **target edge** relates a ref, bookmark, workspace, or change version to a
  commit.

The schema MUST NOT call a commit ID a ref. Entities and target edges are
separate facts with separate temporal evidence.

## Components and Atomic Facts

A component is the smallest stable repository surface that is independently
collected, has one meaningful completeness outcome, and gates the same family
of absence or change assertions. A component is semantic rather than one
subprocess invocation or serialized record.

Candidate components include:

- repository identity and continuity;
- workspace topology;
- recorded working-copy state;
- working-copy filesystem refresh;
- Git refs;
- jj bookmarks;
- jj visible heads;
- commit/change history graph; and
- requested file/path evidence.

Working-copy state MUST NOT remain hidden inside workspace topology when the
two can succeed or fail independently.

An atomic fact is one independently truth-valued assertion. For example:

```text
ref exists
ref targets object ID
ref tracking state equals tracked
object has parent object ID
workspace targets commit/change version
```

Splitting SHOULD continue while sibling assertions can be collected,
confirmed, or invalidated independently. It MUST stop before identities depend
on adapter command structure or unstable presentation details.

## Temporal Evidence

Collection freshness, fact confirmation, and movement are distinct.

Each component observation records:

- `attempted_at`: when that collection attempt occurred; and
- its complete, partial, error, or not-requested outcome.

The rebuildable temporal index derives `last_attempted_at` and
`complete_as_of` from retained component observations. These rolling clocks are
not redundantly copied into every snapshot.

Each atomic fact retains one or more validity intervals containing:

- `first_observed_at`;
- `last_confirmed_at`;
- `invalidated_at`, when a complete observation proves the fact absent; and
- the supporting snapshot, delta, component, and collection outcome.

“Never observed” has the comparison semantics of negative infinity. Every
finite elapsed threshold matches it. The wire form MUST use an explicit state
such as `never_observed`, not a fabricated timestamp or non-portable numeric
infinity.

A partial collection:

- contributes a newer attempt to derived `last_attempted_at`;
- does not advance `complete_as_of`;
- may advance `last_confirmed_at` only for positive facts actually and
  trustworthily observed;
- cannot invalidate an omitted fact; and
- remains visibly partial on repeated runs until a complete collection clears
  the boundary.

A failed collection advances only derived `last_attempted_at` and its error
evidence.
If the component has never produced state-bearing evidence, its facts remain
`never_observed`.

A complete observation confirms present facts and lands tombstones for prior
active facts it can now prove absent. Tombstones are durable evidence and stop
consumers from treating a resolved disappearance as an unbounded loose end.

When identity continuity is supported, reappearance opens a new validity
interval under the same stable fact slot. The contract constrains observable
intervals, predicates, and audit results; it does not require a particular
internal episode representation.

Movement remains an explicit delta between observations. “Elapsed since last
observed movement” is derived from retained fact transitions and SHOULD be
indexed for efficiency rather than introduced as an ambiguous collection
clock.

## Identity Consequences

Identity matters only when it changes a supported answer.

- A content-addressed object is the same fact when repository/store continuity,
  native algorithm, and full object ID match.
- A named ref is the same fact slot when repository continuity and canonical
  ref name match. Deletion closes one interval; recreation opens another. This
  does not claim continuous human intent.
- A target edge is identified by its stable source and target identities.
- When repository continuity cannot be established, `vcs-tree` MUST NOT merge
  intervals or create cross-boundary tombstones.

Counts such as “changed N times during duration D” are derived from retained
intervals. They need not be stored as new authoritative facts.

## jj Working-Copy Observation Policy

Periodic native working-copy snapshots are a useful part of jj observation.
History collection SHOULD run the normal non-destructive jj observation path,
allowing jj to snapshot current filesystem state into the working-copy commit
`@` before facts are collected.

This is a narrow source-repository side effect. It does not authorize fetch,
bookmark movement, commit/rebase/abandon operations, repair, reset, or an
intentional rewrite of user files or repository history.

The result MUST report working-copy refresh provenance:

- `performed`: native jj snapshotting succeeded and the collected `@` reflects
  that refresh;
- `skipped`: an explicit collection policy requested recorded state only;
- `failed`: refresh failed and the error is retained; or
- `not_applicable`: the observation mode has no jj working copy.

If normal refresh fails, collection SHOULD retry using a jj mode that does not
snapshot or update the working copy. A successful fallback may still collect
the recorded `@` commit/change IDs, parents, conflicts, description, and diff
paths. It MUST label filesystem freshness `recorded_maybe_stale`, retain the
refresh error, and avoid claiming that `@` matches current files.

The fallback distinguishes two separately useful facts:

```text
recorded @ state is observable
current filesystem synchronization is indeterminate
```

Git collection SHOULD report equivalent provenance for its HEAD/index/worktree
observation and SHOULD suppress optional index refresh writes where supported.

## Initial Durable Boundary Predicates

`initial_commit_due` is an intelligent conclusion, not a package reason code.
`vcs-tree` supplies its factual premises.

For Git, a consumer can request evidence equivalent to:

```text
workspace is unborn
AND index or working-tree changes are observed
AND identity, workspace, and working-copy evidence meet requested completeness
```

For jj, the corresponding facts are:

```text
workspace @ exists
AND @ has only the virtual root as parent
AND @ contains recorded changes
AND @ refresh and path evidence meet requested completeness/freshness
```

The jj working-copy commit is a content-addressed commit version. Therefore
“no commit object exists” is not a valid jj formulation of the predicate.

A consumer may inspect the reported paths or perform one direct repository
observation to decide whether the content is substantive, generated, empty,
finished, or otherwise merits an initial durable boundary. `vcs-tree` does not
classify vision, implementation, or generated content.

## Requested File Evidence

V2 owns bounded path/type/conflict evidence for recorded working-copy changes
and retained native commit changes. Generic consumer-supplied arbitrary path or
content collection is deferred until dogfooding proves that these native path
surfaces are insufficient.

The authoritative ledger SHOULD reference native VCS objects and retain path,
hash, relationship, and temporal evidence rather than copy arbitrary file
contents. Bounded content may be returned transiently when requested. Content
unavailable from a retained native object remains subject to current repository
state and explicit freshness limits.

Core snapshot and delta semantics MUST NOT depend on a future optional content
collector. Any later request/result boundary should remain replaceable if that
responsibility belongs in another tool.

## Decision Thought Experiments

| Situation | Rejected shortcut | Consequence-backed rule |
| --- | --- | --- |
| First discovery is unreadable | Use failure time as last movement | Failure proves an attempt, not unchanged state. Attempt advances; state remains `never_observed`. |
| A component repeatedly returns partial facts | Refresh the whole component clock | Positive facts may be reconfirmed, but completeness does not advance and the partial boundary repeats. |
| A complete scan no longer contains a ref | Merely stop confirmation | Complete absence lands a tombstone so consumers do not chase an unresolved loose end. |
| A deleted ref name later reappears | Decide whether it is metaphysically the same branch | Reuse the stable named slot, open a new interval, and make no claim about human intent. |
| jj refresh is blocked by a sandbox | Return all working-copy state as unknown | Fall back to recorded `@`, report its facts, and label filesystem freshness stale/indeterminate. |
| jj `@` is based only on the virtual root | Claim no commit object exists | Report the actual `@` commit, its root parent, recorded changes, paths, and freshness. The consumer decides whether an initial durable boundary is due. |
| Review finds a priority or disposition | Store it beside snapshots | It is external interpretation. `vcs-tree` observes it later only if another actor records it in the repository. |

These rationales are normative design evidence. Later revisions SHOULD preserve
the consequences even if field names or storage representation change.

### Grounded sandbox fallback trial

On 2026-08-03, while this contract correction was being written in the managed
project sandbox, ordinary `jj status` attempted its native working-copy
snapshot and failed because it could not create an object beneath the colocated
`.git/objects` directory. The fallback commands:

```text
jj --ignore-working-copy status
jj --ignore-working-copy diff --stat
```

succeeded against recorded `@` and reported no changes. A non-refreshing Git
worktree check simultaneously reported the edited contract/task files and the
new planning artifact. The recorded jj facts were readable but stale relative
to the filesystem.

This trial rejects both “normal jj observation is always read-only” and “a
failed refresh makes all `@` facts unknown.” Refresh provenance and recorded
state freshness are independently necessary facts.

## Output and Exit Direction

The eventual mechanical-intent surface SHOULD provide deterministic summary,
audit, and JSON representations. JSON carries every predicate result and its
evidence. Audit includes non-matches and indeterminate predicates. Summary may
omit verified false results but MUST count them.

Exit behavior follows existing history conventions:

- complete evaluation, regardless of true/false matches, is success;
- usable partial or indeterminate evidence is the existing partial exit class;
- operational failure means no trustworthy result was completed; and
- argument or predicate syntax errors use the CLI usage exit.

No matching fact is a process failure or an instruction to perform review.

## Follow-On Boundaries

The retained-corpus trial and dispatch decisions are recorded in
`planning/mechanical-review-dispatch.md`. Engineering is decomposed into:

1. `260803-version-mechanical-evidence-schema`;
2. `260803-collect-current-working-copy-evidence`;
3. `260803-index-temporal-fact-intervals`;
4. `260803-evaluate-mechanical-predicates`;
5. `260803-expose-mechanical-query-cli`; and
6. `260803-test-mechanical-query-workflow`.

No lane owns intelligent ranking, dispositions, cadence, notifications, or
repository-authored review mutation.
