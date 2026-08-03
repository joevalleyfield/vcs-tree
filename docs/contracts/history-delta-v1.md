# History Delta Contract v1

Status: accepted for implementation review; jj change-graph correction applied

Schema identifier: `vcs-tree.history-delta`

Schema version: `1`

## Purpose

This contract defines factual comparison events between two
`vcs-tree.history-snapshot` v1 manifests backed by compatible history ledger
generations.

It answers questions such as:

- Which refs appeared, disappeared, or changed targets?
- Was a single-target ref movement a fast-forward, rewind, or divergence?
- Which history objects became observable for the first time?
- Which newly observed objects are outside every current workspace line?
- Which history became unreachable while remaining in the ledger?
- Did a jj logical change gain, lose, or diverge commit versions?
- Which assertions are indeterminate because collection was incomplete?

The delta is factual. It does not score activity or infer project progress.

## Normative Language

The words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are normative.

## Inputs and Preconditions

A comparison has:

- `from_snapshot`;
- `to_snapshot`;
- access to the history ledger generations referenced by both snapshots.

Snapshots MUST use supported snapshot schema versions. Repository comparison
uses `repository_key`.

Scan scopes MUST be comparable. If a repository is absent because the target
scan covered a different root, exclusion policy, or repository selection, the
delta MUST NOT emit `repository_removed`.

If store identity or repository continuity cannot be established, the delta
MUST emit an indeterminate or repository-added/removed observation rather than
guessing identity from paths or remotes.

## Delta Envelope

```json
{
  "schema": "vcs-tree.history-delta",
  "schema_version": 1,
  "delta_id": "delta-a-b",
  "computed_at": "2026-07-29T13:01:00Z",
  "from_snapshot": "snapshot-a",
  "to_snapshot": "snapshot-b",
  "history_store": {
    "store_id": "ledger",
    "from_generation": 1,
    "to_generation": 2
  },
  "outcome": {
    "state": "complete",
    "errors": []
  },
  "repository_deltas": []
}
```

Repository deltas MUST be sorted by `repository_key`. Events within a
repository MUST use the deterministic event ordering defined below.

## Common Event Shape

```json
{
  "event": "ref_target_changed",
  "event_key": "ref_target_changed:git:remote:origin:side",
  "certainty": "observed",
  "evidence": {
    "from_component": "refs",
    "to_component": "refs"
  },
  "details": {}
}
```

Required event fields:

- `event`: event vocabulary value;
- `event_key`: stable key within one repository delta;
- `certainty`: `observed` or `indeterminate`;
- `evidence`: source components and optional native authority;
- `details`: event-specific payload.

V1 MUST NOT emit `inferred` events. Derived ancestry classifications remain
`observed` because they are deterministic graph relations over observed IDs.

## Completeness Gate

Absence is meaningful only when the relevant component is complete in both
snapshots.

Rules:

1. `ref_created`, `ref_deleted`, and `ref_target_changed` require complete ref
   collection in both snapshots.
2. Ref target changes remain observable when ancestry is incomplete, but their
   ancestry relation and movement MUST be `unknown`.
3. Workspace additions, removals, and head changes require complete workspace
   collection in both snapshots.
4. File evidence requires complete file-change details for the relevant
   object/parent pair.
5. If a required component is partial, errored, or not requested, the delta
   MUST emit `comparison_incomplete` and MUST NOT emit unsupported absence or
   movement assertions.
6. `history_first_observed` remains factual when the ledger records first
   observation in the target generation, even if an earlier scan was partial.
   It MUST NOT be described as object creation.
7. History reachability events require all referenced objects and parent edges
   through the comparison boundary. Otherwise they are suppressed and
   `comparison_incomplete` identifies the boundary.

## Repository Events

### `repository_added`

The target snapshot completely observes a repository key absent from a
complete source scan.

### `repository_removed`

The source snapshot completely observes a repository key absent from a
complete target scan.

### `repository_unreadable`

A previously readable repository or component has target state `error`.

### `repository_recovered`

A previously errored repository component becomes complete.

### `comparison_incomplete`

The delta cannot establish a requested fact because one or both required
components are incomplete.

Payload:

```json
{
  "component": "refs",
  "from_state": "complete",
  "to_state": "partial",
  "suppressed_events": [
    "ref_deleted",
    "ref_target_changed"
  ]
}
```

## Workspace Events

### `workspace_added`

A workspace key appears under complete before/after workspace collection.

### `workspace_removed`

A workspace key disappears under complete before/after workspace collection.

### `workspace_head_changed`

Payload:

```json
{
  "workspace_key": "repo-01:default",
  "old_object_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "new_object_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "relation": "old_ancestor_of_new"
}
```

`relation` uses the ancestry vocabulary below. For colocated repositories, the
jj working-copy head is authoritative.

### `working_copy_changed`

Reports factual clean/dirty/conflicted state or summary changes. It does not
assert committed movement.

## Ref Events

### `ref_created`

A ref key is absent before and present after complete ref collection.

Payload includes the complete target state after creation.

### `ref_deleted`

A ref key is present before and absent or natively deleted after complete ref
collection.

Payload includes the prior target state. Deletion MUST NOT remove ledger
objects.

### `ref_target_changed`

Payload:

```json
{
  "ref_key": "git:remote:origin:side",
  "old": {
    "state": "normal",
    "targets": [
      "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    ]
  },
  "new": {
    "state": "normal",
    "targets": [
      "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    ]
  },
  "relations": [
    {
      "old": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "new": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      "relation": "old_ancestor_of_new"
    }
  ],
  "movement": "fast_forward"
}
```

### `ref_conflict_changed`

Reports changes among normal, conflicted, and deleted states, including
complete added/removed target sets.

### `ref_tracking_changed`

Reports tracked/untracked or named-remote authority changes. Equal commit
targets do not suppress this event.

### Ancestry relation vocabulary

For an old/new target pair:

- `same`;
- `old_ancestor_of_new`;
- `new_ancestor_of_old`;
- `diverged`;
- `unknown`.

For a normal single-target ref, `movement` is:

- `unchanged`;
- `fast_forward`;
- `rewind`;
- `diverged`;
- `unknown`.

`movement` MUST be `unknown` when either snapshot marks relevant ancestry as
`shallow`, `partial`, or `unknown`, unless the requested relation can be proven
without crossing that boundary.

Conflicted or multi-target refs MUST expose pairwise `relations` and use
`movement: "target_set_changed"` rather than collapsing to one scalar
ancestry result.

Human-oriented fetch or reflog messages MAY be attached as provenance but MUST
NOT determine movement classification.

## History Events

### `history_first_observed`

Lists objects whose immutable ledger records first appear in the target
generation:

```json
{
  "object_ids": [
    "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "cccccccccccccccccccccccccccccccccccccccc"
  ],
  "reachable_from": [
    {
      "role": "remote_ref",
      "source_key": "git:remote:origin:side"
    }
  ]
}
```

This event means “first observed by this history store,” not “created during
the interval.”

### `history_became_reachable`

Objects already present in the ledger enter the target snapshot's selected
root closure.

### `history_became_unreachable`

Objects in the source selected-root closure are absent from the target closure.
They remain in the ledger.

The event SHOULD group objects by the roots whose creation, movement, or
deletion changed reachability.

### `off_current_history_observed`

An object is:

- first observed in the target generation;
- reachable from at least one selected target root;
- not reachable from any target-snapshot workspace head.

Payload MUST include the authorities that expose it. This event is suitable
for “new remote-only line appeared,” but MUST NOT claim when or where the work
was authored.

### `current_line_history_observed`

An object is first observed and reachable from at least one target workspace
head.

The current-line and off-current events partition first-observed reachable
commit objects when history/workspace collection is complete.

## jj Change Events

### `change_versions_changed`

Groups visible commit versions by jj change ID:

```json
{
  "change_id": "abcdefghijklmnopqrstuvxyzabcdefg",
  "old_visible_commits": [
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  ],
  "new_visible_commits": [
    "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "cccccccccccccccccccccccccccccccccccccccc"
  ],
  "state": "divergent"
}
```

`state` is:

- `rewritten`: one visible commit version replaced another;
- `divergent`: multiple target-visible commit IDs share the change ID;
- `resolved`: a previously divergent visible set becomes one;
- `hidden`: no visible version remains while prior versions remain in the
  ledger;
- `visible`: a previously hidden/logically unknown change becomes visible.

Graph relations MUST still use commit IDs.

This event is the primary jj movement event. It MUST be emitted when the
before/after visible-version sets for a `change_id` differ, whether or not any
bookmark names the change. Every old and new visible commit ID is retained.
Valid observed version movement remains `observed` when an unrelated bookmark
component is partial or errored.

The state vocabulary is:

| State | Required evidence | Absence gate |
| --- | --- | --- |
| `introduced` | target has a valid logical change/version absent from source | none for positive observation |
| `rewritten` | same `change_id`, one or more old versions replaced by new versions | graph complete for loss claims |
| `divergent` | target has multiple visible versions for one `change_id` | none for positive observation |
| `topology_changed` | parent change is observed for a retained version | parent edges available |
| `resolved` | target visible set becomes one after prior divergence | graph complete for prior set |
| `visibility_gained` | a known version becomes visible | graph complete for source absence |
| `visibility_lost` | a prior visible version is no longer visible | graph complete in both snapshots |

`hidden` and deletion-like claims MUST NOT be emitted from a partial graph;
they become `indeterminate` with `comparison_incomplete` evidence instead. The
jj null root is a graph boundary, never an ordinary logical-change event.

### `visible_head_added` and `visible_head_removed`

Report jj visible-head set movement separately from bookmark movement.
Unbookmarked work MUST remain observable through these events.

Visible-head and workspace-head movement are independent topology facts. They
identify affected commit IDs and, when available, logical change IDs. Neither
requires a bookmark or is suppressed by bookmark incompleteness.

### Publication-hint events

Git refs and jj bookmarks remain separate event families. Bookmark events carry
authority provenance and may report local intent, tracked state, or observed
remote targets, but MUST NOT claim publication or server freshness. Partial
bookmark collection may suppress bookmark absence/target claims while leaving
change-version, topology, visible-head, workspace-head, description, and path
events intact.

## Tag Events

### `tag_created`, `tag_deleted`, and `tag_target_changed`

Tag events preserve:

- native tag ref name;
- direct tag-object target;
- peeled commit target;
- annotated versus lightweight form.

A tag-object metadata change normally creates a new tag object ID and therefore
appears as target movement.

## File Evidence Events

### `history_file_changes_observed`

Reports newly available parent-relative file changes for a history object.

Generic payload:

```json
{
  "commit_id": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "parent_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "entries": [
    {
      "status": "renamed",
      "old_path": "tasks/open/example.md",
      "path": "tasks/closed/example.md"
    }
  ]
}
```

This is factual path evidence. A downstream adapter MAY describe task creation
or closure according to a project contract. The base delta MUST NOT interpret
the rename as progress.

## Event Ordering

Within one repository delta, writers MUST sort by:

1. repository/component outcome events;
2. workspace events;
3. ref and tag events;
4. visible-head and jj change events;
5. history reachability and first-observation events;
6. file evidence events;
7. `event_key` within each category.

List-valued IDs and authorities MUST be sorted deterministically. Native parent
order remains unchanged where included.

## V1 Payload Representation

V1 stores event ID lists inline. It does not page lists or replace them with
side-record references.

Writers MUST NOT silently truncate an inline list. If a configured resource
limit prevents complete materialization, the affected component or delta
outcome MUST be `partial` or `error` with `kind: "limit_exceeded"`. Events that
depend on the omitted IDs are then governed by the completeness gate.

Paging or content-addressed side records require evidence of actual scale
pressure and a later compatible contract extension or schema version.

## Worked Remote-Only Example

Source snapshot:

- workspace `default` is at commit `A`;
- `main` and `origin/main` target `A`;
- ledger generation 1 contains `A`.

Target snapshot after a local fetch:

- workspace `default` remains at `A`;
- `origin/side` appears at `C`;
- `C` has parent `B`, and `B` has parent `A`;
- ledger generation 2 first observes `B` and `C`.

Required delta events:

```json
[
  {
    "event": "ref_created",
    "event_key": "ref_created:git:remote:origin:side",
    "certainty": "observed",
    "evidence": {
      "from_component": "refs",
      "to_component": "refs"
    },
    "details": {
      "ref_key": "git:remote:origin:side",
      "targets": ["C"]
    }
  },
  {
    "event": "history_first_observed",
    "event_key": "history_first_observed:B,C",
    "certainty": "observed",
    "evidence": {
      "from_component": "history",
      "to_component": "history"
    },
    "details": {
      "object_ids": ["B", "C"],
      "reachable_from": ["git:remote:origin:side"]
    }
  },
  {
    "event": "off_current_history_observed",
    "event_key": "off_current_history_observed:B,C",
    "certainty": "observed",
    "evidence": {
      "from_component": "workspaces",
      "to_component": "history"
    },
    "details": {
      "object_ids": ["B", "C"],
      "reachable_from": ["git:remote:origin:side"],
      "workspace_heads": ["A"]
    }
  }
]
```

No `workspace_head_changed` or `current_line_history_observed` event is emitted.
The delta MAY record fetch provenance if the collector performed the fetch,
but a passive scan says only that remote-tracking history became observable.

## Invariants

1. Every event cites complete-enough evidence or has
   `certainty: "indeterminate"`.
2. Partial target collection never produces a deletion assertion.
3. First-observed time and commit author/committer time remain distinct.
4. Ref movement classification is based on target sets and graph ancestry.
5. jj logical-change events never replace commit IDs in graph events.
12. jj logical-change and topology events do not require bookmark presence.
13. Publication-hint uncertainty cannot downgrade independently supported
    change-graph movement.
6. Reachability loss never deletes immutable ledger records.
7. Off-current means outside all observed target workspace-head closures.
8. Event vocabulary remains factual and does not encode project health.
9. Shallow or incomplete ancestry produces `movement: "unknown"`.
10. Inline ID lists are complete or the enclosing outcome reports an explicit
    limit failure.
11. Corrupted ledger state suppresses dependent movement and loss assertions;
    it never causes source-repository mutation.

## Versioning and Compatibility

- The delta schema version is independent from snapshot schema version, but
  each delta version MUST declare supported snapshot versions.
- Additive optional event fields MAY be introduced within v1.
- New required fields, changed event meaning, or incompatible enum/cardinality
  changes require a new delta schema version.
- Readers MUST retain unknown events when forwarding data or explicitly report
  that they were ignored.

## Non-Goals

V1 does not:

- infer progress, intent, productivity, ownership, or project health;
- prove that a fetch caused an observed ref change unless fetch provenance was
  recorded;
- infer object creation time from first observation or commit timestamps;
- compare unrelated repository keys by matching paths or remote URLs;
- prescribe UI grouping or prose summaries;
- define alert thresholds;
- define project-specific task lifecycle semantics;
- garbage-collect history;
- provide custody-chain or forensic audit guarantees.

## Open Policy Questions

1. Should optional reflog/jj-operation events use this vocabulary or a separate
   ephemeral delta channel?
2. Which repository identity continuity failures require explicit operator
   reconciliation?
3. What evidence threshold justifies adding paging or content-addressed side
   records after v1?
