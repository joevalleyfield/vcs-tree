# History Snapshot Contract v1

Status: draft for implementation review

Schema identifier: `vcs-tree.history-snapshot`

Schema version: `1`

## Purpose

This contract defines factual stored state for Git, jj, and colocated
repositories. It retains enough observed history to recognize remote-only and
off-current work without copying the entire history graph into every snapshot.

The contract deliberately separates:

1. an append-only history ledger containing native objects once;
2. lightweight snapshots containing repository, workspace, ref, and root
   topology at an observation time;
3. optional export bundles that package a snapshot with required ledger
   objects for transport.

This contract does not define movement events. Those are defined by
`history-delta-v1.md`.

## Normative Language

The words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are normative.

## Terms

- **Repository store**: the underlying object and ref database. Multiple jj
  workspaces may share one store.
- **Workspace**: a checkout or jj working copy associated with a store.
- **Native object ID**: an ID assigned by the VCS, such as a Git/jj commit ID.
- **History root**: a selected commit target whose parent closure belongs to
  the default observed-history universe.
- **Observed history**: objects reached through selected factual roots during
  collection. It is not every object physically present in the store.
- **Current history**: ancestors of current workspace heads.
- **Ledger generation**: an append-only store position containing every object
  referenced by a snapshot.

## Storage Architecture

### History ledger

The ledger MUST be content-addressed by repository key, native object kind, and
native object ID. Re-observing an object MUST NOT duplicate its immutable
record.

An object that later becomes unreachable MUST remain in the ledger according
to the configured retention policy. Ref deletion MUST NOT immediately erase
previously observed objects.

The ledger contains:

- immutable native object records;
- first-observation facts;
- optional parent-relative file-change details;
- ledger generations or another monotonic completeness boundary.

### Snapshot manifest

A snapshot MUST reference a ledger generation that contains all objects needed
to resolve its roots. A snapshot MUST NOT embed the complete history closure by
default.

### Export bundle

An export bundle MAY include a snapshot plus some or all referenced ledger
objects. Bundle framing is outside v1. A snapshot without its referenced ledger
is valid metadata but is not self-contained for ancestry queries.

## Snapshot Envelope

Every snapshot has this top-level shape:

```json
{
  "schema": "vcs-tree.history-snapshot",
  "schema_version": 1,
  "snapshot_id": "01K1CEXAMPLE00000000000000",
  "captured_at": "2026-07-29T13:00:00Z",
  "collector": {
    "name": "vcs-tree",
    "version": "0.1.0"
  },
  "history_store": {
    "store_id": "local-ledger-01",
    "generation": 42
  },
  "scan": {
    "root": "/workspace",
    "outcome": {
      "state": "complete",
      "errors": []
    }
  },
  "repositories": []
}
```

Required envelope fields:

- `schema`: exactly `vcs-tree.history-snapshot`;
- `schema_version`: integer `1`;
- `snapshot_id`: unique within the history store;
- `captured_at`: RFC 3339 timestamp normalized to UTC;
- `collector`: collector identity and version;
- `history_store`: store identity and generation;
- `scan`: scan scope and outcome;
- `repositories`: deterministically ordered repository observations.

`scan.root` is observation provenance, not portable repository identity.

## Collection Outcome

Every independently collected component MUST carry an outcome:

```json
{
  "state": "partial",
  "errors": [
    {
      "kind": "timeout",
      "stage": "git.refs",
      "message": "repository check exceeded 8 seconds",
      "exit_code": null
    }
  ]
}
```

`state` is one of:

- `complete`: the component was fully collected;
- `partial`: some factual records are present but absence is not meaningful;
- `error`: no reliable component result was collected;
- `not_requested`: collection policy omitted the component.

Errors MUST be factual and stage-scoped. Implementations MAY redact command
stderr, but MUST retain `kind` and `stage`.

An empty complete component and an errored component are different states.

## Repository Observation

Each repository observation has:

```json
{
  "repository_key": "repo-01",
  "mode": "colocated",
  "store": {
    "backend": "git",
    "object_format": "sha1",
    "native_hint": null
  },
  "locations": [
    {
      "path": "/workspace/project",
      "role": "primary"
    }
  ],
  "collection": {
    "identity": {
      "state": "complete",
      "errors": []
    },
    "workspaces": {
      "state": "complete",
      "errors": []
    },
    "refs": {
      "state": "complete",
      "errors": []
    },
    "history": {
      "state": "complete",
      "errors": []
    }
  },
  "workspaces": [],
  "refs": [],
  "roots": []
}
```

### Repository key

`repository_key` is an opaque identity assigned by the observing history
store. It MUST remain stable for that store across workspace moves when the
observer can establish continuity.

V1 does not claim that repository keys are portable between machines or that
two clones share one identity. Paths and remote URLs MUST NOT be treated as
globally unique repository IDs.

### Mode

`mode` is one of:

- `git`: Git worktree without jj authority;
- `jj`: jj repository without a colocated worktree `.git`;
- `colocated`: Git and jj operate on the same worktree/store.

Linked jj workspaces MUST share a `repository_key` and have distinct workspace
records.

### Store

`store.backend` identifies the physical object backend. A non-colocated jj
repository backed by Git still uses `backend: "git"` and `mode: "jj"`.

`object_format` is `sha1`, `sha256`, or a future versioned value.

`native_hint` MAY contain a local, redacted continuity hint. It MUST NOT be
interpreted as portable identity.

## Workspace Record

```json
{
  "workspace_key": "repo-01:default",
  "native_name": "default",
  "path": "/workspace/project",
  "is_primary": true,
  "current": {
    "object_id": {
      "algorithm": "sha1",
      "value": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    },
    "change_id": "abcdefghijklmnopqrstuvxyzabcdefg"
  },
  "parents": [
    {
      "algorithm": "sha1",
      "value": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    }
  ],
  "working_copy": {
    "state": "dirty",
    "summary": {
      "added": 1,
      "modified": 2,
      "deleted": 0
    },
    "entries_outcome": {
      "state": "not_requested",
      "errors": []
    },
    "entries": []
  }
}
```

Rules:

- Git-only repositories normally have one workspace.
- jj repositories MUST include every enumerated shared workspace when
  workspace collection is complete.
- In colocated mode, jj is authoritative for current working-copy identity.
  Git `HEAD` MAY be retained as a separate symbolic ref, but MUST NOT replace
  jj `@`.
- `current.object_id` MAY be null only for an unborn Git workspace or a
  component error represented by its collection outcome.
- `change_id` is required for jj commits and null for Git-only commits.
- `working_copy.state` is `clean`, `dirty`, `conflicted`, `unknown`, or
  `unreadable`.

## Native Object ID

```json
{
  "algorithm": "sha1",
  "value": "0123456789abcdef0123456789abcdef01234567"
}
```

IDs MUST retain their full native value and be normalized to lowercase when
the native representation is case-insensitive hexadecimal.

Short IDs are presentation only and MUST NOT appear as ledger keys.

## History Object Record

### Commit

```json
{
  "repository_key": "repo-01",
  "kind": "commit",
  "object_id": {
    "algorithm": "sha1",
    "value": "0123456789abcdef0123456789abcdef01234567"
  },
  "change_id": "abcdefghijklmnopqrstuvxyzabcdefg",
  "parents": [],
  "author": {
    "name": "Example",
    "email": "example@example.invalid",
    "timestamp": "2026-07-29T12:00:00Z"
  },
  "committer": {
    "name": "Example",
    "email": "example@example.invalid",
    "timestamp": "2026-07-29T12:01:00Z"
  },
  "summary": "short native description",
  "first_observed": {
    "snapshot_id": "01K1CEXAMPLE00000000000000",
    "captured_at": "2026-07-29T13:00:00Z"
  },
  "file_changes": {
    "outcome": {
      "state": "not_requested",
      "errors": []
    },
    "by_parent": []
  }
}
```

Rules:

- `parents` contains native commit IDs and defines graph edges.
- `change_id` is required for jj-visible commits and null for Git-only
  observations.
- jj rewrites create a new `object_id` record and retain the same `change_id`.
- Divergent jj changes have multiple visible commit records sharing one
  `change_id`.
- Author and committer timestamps are factual metadata. They MUST NOT be used
  alone to establish when an object first became observable.
- `summary` is the native first-line description and MAY be empty.

### Virtual jj root

The jj null root MUST be represented as:

```json
{
  "repository_key": "repo-01",
  "kind": "virtual_root",
  "object_id": {
    "algorithm": "sha1",
    "value": "0000000000000000000000000000000000000000"
  },
  "change_id": "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz",
  "parents": [],
  "author": null,
  "committer": null,
  "summary": ""
}
```

The virtual root, an unborn repository, and a repository-read error MUST remain
distinct.

### Annotated tag object

```json
{
  "repository_key": "repo-01",
  "kind": "tag",
  "object_id": {
    "algorithm": "sha1",
    "value": "cccccccccccccccccccccccccccccccccccccccc"
  },
  "target": {
    "algorithm": "sha1",
    "value": "0123456789abcdef0123456789abcdef01234567"
  },
  "target_kind": "commit",
  "name": "v1",
  "message": "release"
}
```

Tag objects and their peeled commit targets MUST remain distinct.

## Parent-Relative File Changes

When collected, `file_changes.by_parent` contains:

```json
{
  "parent": {
    "algorithm": "sha1",
    "value": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  },
  "entries": [
    {
      "status": "renamed",
      "path": "tasks/closed/example.md",
      "old_path": "tasks/open/example.md"
    }
  ]
}
```

`status` is `added`, `modified`, `deleted`, `renamed`, `copied`,
`type_changed`, or `conflicted`.

Merge commits MUST keep changes separated by parent. Generic file evidence MAY
later feed a project-specific task-lifecycle adapter; this contract does not
label a path change as task progress.

## Ref Record

```json
{
  "ref_key": "jj:bookmark:origin:topic",
  "kind": "jj_remote_bookmark",
  "native_name": "topic",
  "authority": {
    "scope": "remote",
    "remote": "origin",
    "tracked": false
  },
  "state": "conflicted",
  "symbolic_target": null,
  "direct_targets": [],
  "peeled_targets": [],
  "added_targets": [
    {
      "algorithm": "sha1",
      "value": "dddddddddddddddddddddddddddddddddddddddd"
    },
    {
      "algorithm": "sha1",
      "value": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
    }
  ],
  "removed_targets": []
}
```

`kind` is one of:

- `git_local_branch`;
- `git_remote_tracking`;
- `git_tag`;
- `git_symbolic`;
- `jj_local_bookmark`;
- `jj_remote_bookmark`;
- `jj_git_tracking_bookmark`;
- `jj_tag`.

Rules:

- `state` is `normal`, `conflicted`, or `deleted`.
- A normal direct ref has exactly one `direct_targets` entry.
- An annotated Git tag has the tag object in `direct_targets` and the final
  commit root in `peeled_targets`.
- A symbolic ref uses `symbolic_target` and MAY also record its resolved direct
  target.
- A conflicted jj ref uses `added_targets` and `removed_targets`; it MUST NOT be
  collapsed to one target.
- Untracked jj remote bookmarks MUST be collected by the default policy.
- Equal targets from local, Git-tracking, and named remote authorities MUST
  remain separate ref records.

## History Root

Roots connect topology to the history ledger:

```json
{
  "role": "remote_ref",
  "source_key": "jj:bookmark:origin:topic",
  "targets": [
    {
      "algorithm": "sha1",
      "value": "dddddddddddddddddddddddddddddddddddddddd"
    }
  ]
}
```

`role` is:

- `local_ref`;
- `remote_ref`;
- `tag`;
- `visible_head`;
- `workspace_head`.

Visible jj heads and workspace heads are roots even when no named ref points to
them.

The default history universe is the union of root targets and their parent
closure. Raw Git `--all`, `refs/jj/keep/*`, `refs/codex/*`, reflogs, dangling
objects, and hidden jj predecessors are excluded unless an explicit deeper
policy adds them with separate provenance.

## Provenance

Every repository observation MUST identify which adapter supplied each
component:

```json
{
  "component": "refs",
  "adapter": "jj",
  "surface": "bookmark list --all-remotes",
  "policy": "default"
}
```

Provenance MAY describe command families but SHOULD NOT persist secrets,
credentials, or unredacted remote URLs.

In colocated mode:

- jj is authoritative for workspaces, current working copies, visible heads,
  change IDs, and jj bookmark state;
- explicit Git user ref namespaces MAY supply compatibility evidence;
- internal Git implementation refs MUST NOT become user refs or history roots.

## Determinism

Writers MUST:

- emit UTF-8 JSON;
- sort repositories by `repository_key`;
- sort workspaces by `workspace_key`;
- sort refs by `ref_key`;
- sort roots by `(role, source_key)`;
- sort object IDs lexicographically within target sets;
- preserve parent order from the native commit;
- use null rather than omitting required nullable fields.

Object and list ordering MUST NOT carry semantic meaning except native parent
order.

V1 does not require a canonical JSON byte encoding or content-derived
`snapshot_id`.

## Invariants

1. Every root target is present in the referenced ledger generation unless
   history collection is partial or errored.
2. Every parent edge refers to an object in the same repository ledger or an
   explicit shallow-boundary marker introduced by a future version.
3. Commit graph identity uses commit/object ID, never jj change ID.
4. Repository/store identity and workspace identity are different keys.
5. Null root, unborn state, empty history, and read errors are distinguishable.
6. Component absence is meaningful only when its outcome is `complete`.
7. Snapshots contain facts observed at capture time, not progress judgments.
8. Previously observed unreachable objects are not deleted merely because a
   later snapshot omits their roots.

## Versioning and Compatibility

- Additive optional fields MAY be introduced without changing
  `schema_version`.
- New required fields, changed meanings, enum removals, or incompatible
  cardinality changes require a new schema version.
- Readers MUST reject unsupported major schema versions.
- Readers SHOULD retain unknown additive fields during read/write forwarding
  when practical.
- A migration MUST preserve native IDs, root/error distinctions, and
  first-observation facts.

## Non-Goals

V1 does not:

- infer whether movement is progress, healthy, intentional, or complete;
- claim that author/committer timestamps are observation timestamps;
- mirror every object in a Git or jj store;
- treat reflogs or jj operation history as default roots;
- define permanent retention duration;
- define cross-machine clone equivalence;
- define package APIs, SQL tables, JSON Schema, or cache migration;
- interpret generic file paths as project task lifecycle.

## Open Policy Questions

1. How is `repository_key` continuity preserved portably after moves?
2. What retention policy applies to formerly observed unreachable objects?
3. Should optional reflog and jj operation-history observations share the main
   ledger or use a separate ephemeral channel?
4. Should export bundles materialize full root closure or only objects missing
   from a named receiver generation?
5. Which author/email redaction policy applies outside a local machine?

These questions MUST remain policy/configuration decisions. Adapters MUST NOT
choose incompatible answers implicitly.

## Minimal Remote-Only Example

This abbreviated topology example shows remote-only history without moving the
current workspace. It is illustrative rather than a validation fixture:

```json
{
  "schema": "vcs-tree.history-snapshot",
  "schema_version": 1,
  "snapshot_id": "snapshot-b",
  "captured_at": "2026-07-29T13:00:00Z",
  "collector": {
    "name": "vcs-tree",
    "version": "0.1.0"
  },
  "history_store": {
    "store_id": "ledger",
    "generation": 2
  },
  "scan": {
    "root": "/workspace",
    "outcome": {
      "state": "complete",
      "errors": []
    }
  },
  "repositories": [
    {
      "repository_key": "repo-01",
      "mode": "git",
      "workspace_current": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "refs": {
        "refs/heads/main": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "refs/remotes/origin/side": "cccccccccccccccccccccccccccccccccccccccc"
      },
      "roots": [
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "cccccccccccccccccccccccccccccccccccccccc"
      ]
    }
  ]
}
```

The compact example illustrates topology only; normative repository records
use the expanded structures defined above.
