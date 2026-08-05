# Temporal Facts Contract v1

Status: implemented derived contract

Schema: `vcs-tree.temporal-facts`

Schema version: `1`

The temporal fact index is a deterministic, disposable projection of retained
snapshot observations and immutable object details. It is not a second
authoritative evidence source. Deleting or corrupting it causes a rebuild; it
never authorizes mutation of a source repository or rewriting retained
snapshots and objects.

## Source ordering and compatibility

The builder accepts retained snapshot v1 and v2 manifests and orders them by
generation, `captured_at`, and snapshot ID. Snapshot v1 component outcomes that
are actually present use `captured_at` with `snapshot` precision. Facts and
components absent from v1 remain `unknown` or `not_requested`; a colocated Git
success never promotes an errored jj change graph.

All snapshots in one projection must belong to one history store. Repository
keys provide continuity within that store. If the same scoped location appears
under a different repository key, the index records a continuity boundary and
does not create cross-boundary tombstones.

## Components

Each component record contains:

```json
{
  "component_key": "repo-1:git_refs",
  "repository_key": "repo-1",
  "component": "git_refs",
  "last_attempted_at": {
    "state": "observed",
    "at": "2026-08-04T12:02:00Z",
    "time_precision": "component",
    "snapshot_id": "snapshot-2"
  },
  "complete_as_of": {
    "state": "observed",
    "at": "2026-08-04T12:01:00Z",
    "time_precision": "component",
    "snapshot_id": "snapshot-1"
  },
  "last_outcome": "partial",
  "errors": []
}
```

Every attempted complete, partial, or error observation advances
`last_attempted_at`. Only complete observations advance `complete_as_of`.
Working-copy refresh additionally retains its native `performed`, `failed`,
`skipped`, or `not_applicable` outcome and latest freshness. A component with
no supported attempt or completion uses `{"state":"never_observed"}` rather
than a fabricated timestamp.

## Atomic facts

Fact keys identify exact assertions. Slot keys identify the stable subject of
that assertion, allowing mutually exclusive values or targets to be related
without conflating their validity intervals. Names are percent-encoded and
compound values use canonical sorted JSON.

The v1 vocabulary is:

- `repository-exists`;
- `workspace-exists` and `workspace-target`;
- `working-copy-state` and `working-copy-path`;
- `git-ref-exists` and `git-ref-target`;
- `jj-bookmark-exists` and `jj-bookmark-target`;
- `jj-visible-head`;
- `native-object-exists` and `native-parent-edge`; and
- `jj-change-exists`, `jj-change-version`, and `jj-change-parent`.

Entity existence and relationship edges always have distinct fact types and
keys. For example, changing a Git ref target confirms the `git-ref-exists`
fact, invalidates the old `git-ref-target` edge, and opens the new target edge.

Native object and parent facts are positive-only because retained object
omission does not prove object deletion. They are timestamped only when a
compatible snapshot positively references them; aggregate object-ledger
presence does not manufacture a first-observation time.

## Validity episodes

Each fact retains ordered intervals:

```json
{
  "episode": 1,
  "prior_boundary": {
    "state": "never_observed",
    "origin": "negative_infinity"
  },
  "first_observed_at": "2026-08-04T12:01:00Z",
  "last_confirmed_at": "2026-08-04T12:02:00Z",
  "invalidated_at": "2026-08-04T12:03:00Z",
  "opened_by": {},
  "last_confirmed_by": {},
  "invalidated_by": {}
}
```

A positive complete or partial observation opens or confirms an interval. A
partial observation never invalidates an omitted fact. A complete observation
invalidates an omitted active fact only when that exact semantic component
supports absence. Reappearance after a tombstone opens the next episode under
the same fact key.

The first episode has a `never_observed` prior boundary with a
`negative_infinity` origin. Lookup of a key absent from the index returns the
same explicit wire state. Consumers may therefore give never-observed clocks
positive-infinity elapsed semantics without serializing non-portable numeric
infinity.

Every opening, confirmation, and invalidation retains snapshot ID, component,
outcome, observer time, and precision.

## Persistence and rebuilding

The checksummed derived file is `temporal-facts.json` under the machine-local
history state root. It records its source generation and ordered source
snapshots. `HistoryLedger.read_temporal_index()` returns a current valid index;
missing, malformed, wrong-schema, wrong-store, or stale data is rebuilt from
`snapshots.json` and `objects.json`. `rebuild_temporal_index()` performs the
same replacement explicitly.

No wall-clock build timestamp is stored. Rebuilding twice against unchanged
inputs produces byte-equivalent canonical JSON and no additional transitions.
