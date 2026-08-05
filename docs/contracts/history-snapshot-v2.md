# History Snapshot Contract v2

Status: implementation contract

Schema: `vcs-tree.history-snapshot`

Schema version: `2`

V2 separates native collection outcomes and working-copy refresh provenance so
one successful backend cannot promote a failed colocated backend to complete.
It does not add review, priority, health, or disposition judgments.

## Compatibility

Readers accept snapshot versions 1 and 2 and reject other versions. Existing
v1 manifests remain immutable. `normalize_snapshot` projects either version
onto a common evidence vocabulary: v1 observations use snapshot-precision
`captured_at`, absent v2 facts become `unknown` or `not_requested`, and v2-only
comparisons report `comparison_incomplete` unless both component outcomes are
complete.

Production collection remains v1 until every required v2 component can be
populated. Constructing, serializing, retaining, and reading v2 explicitly is
supported independently of that cutover.

## Component outcomes

Every repository has these required keys under `collection`:

- `identity`
- `git_worktrees`
- `jj_workspaces`
- `git_refs`
- `jj_bookmarks`
- `jj_visible_heads`
- `git_history`
- `jj_history`
- `path_evidence`

An attempted component has:

```json
{
  "state": "complete",
  "attempted_at": "2026-08-04T12:00:00Z",
  "errors": []
}
```

`state` is `complete`, `partial`, `error`, or `not_requested`. Every state
except `not_requested` requires an RFC 3339 `attempted_at`. `not_requested`
forbids both an attempt timestamp and errors. `complete` forbids errors.
`attempted_at` is observer time, not native author or committer time.

Native inapplicability is represented by `not_requested`; collection failure
is `partial` or `error`. In colocated repositories, Git and jj outcomes remain
independent. In particular, `git_history: complete` says nothing about
`jj_history`.

## Repository and workspace shape

A repository requires `repository_key`, `mode`, the complete component map,
and a `workspaces` array. `mode` is `git`, `jj`, or `colocated`. Additional
factual presentation fields are preserved during typed round trips.

Each workspace requires `workspace_key` and this working-copy record:

```json
{
  "outcome": {
    "state": "complete",
    "attempted_at": "2026-08-04T12:00:00Z",
    "errors": []
  },
  "recorded_state": "dirty",
  "refresh": {
    "state": "performed",
    "attempted_at": "2026-08-04T12:00:00Z",
    "errors": []
  },
  "freshness": "current",
  "entries_outcome": {
    "state": "complete",
    "attempted_at": "2026-08-04T12:00:00Z",
    "errors": []
  },
  "entries_limit": 256,
  "entries_truncated": false,
  "entries": [
    {"status": "modified", "path": "README.md"}
  ]
}
```

`recorded_state` is `clean`, `dirty`, `conflicted`, `unknown`, or
`unreadable`. Refresh is `performed`, `skipped`, `failed`, or
`not_applicable`. All refresh states except `not_applicable` carry an attempt
timestamp; `performed` and `skipped` forbid errors. `not_applicable` forbids an
attempt and errors. `failed` requires a retained error. A performed refresh
requires `current` freshness. Failed and skipped refreshes permit only
`recorded_maybe_stale` or `unknown`. A not-applicable refresh permits `current`
`unknown`, or `not_applicable`, allowing Git status to describe current files
or a failed status attempt without pretending a jj-style refresh occurred.

Freshness is `current`, `recorded_maybe_stale`, `unknown`, or
`not_applicable`. It describes the relationship between recorded state and the
filesystem; it does not replace collection completeness.

`entries_limit` is a non-negative bound and the entries array cannot exceed
it. `entries_truncated` reports whether additional entries were omitted.
`not_requested` entry evidence must be empty and untruncated. Entry status is
`added`, `modified`, `deleted`, `renamed`, `copied`, `type_changed`, or
`conflicted`; every entry has a path and may have an `old_path`.

## Temporal projection

Snapshots store observation attempts, not rolling clocks. A rebuildable
temporal index derives `first_observed_at`, `last_confirmed_at`,
`invalidated_at`, `complete_as_of`, and fact intervals. V1 normalization uses
`captured_at` with explicit `snapshot` precision only for outcomes and facts
actually retained. V2 uses `component` precision for `attempted_at`.

Never-observed facts are not written with a fabricated timestamp. Their
logical origin is negative infinity when a consumer evaluates elapsed clocks.

## Native working-copy commands

The implemented Git observation uses:

```text
git --no-optional-locks status --porcelain=v2 --branch -z --untracked-files=all
```

This reads HEAD, index, worktree, unborn state, conflicts, and bounded path
evidence while suppressing optional index-refresh locks. It does not fetch,
reset, checkout, commit, or move refs.

The primary requested jj workspace is first read with an ordinary `jj log -r
@ --no-graph -T ...` command. That normal native path may snapshot filesystem
changes into `@`. If it fails, collection repeats the same query with
`--ignore-working-copy`; a successful fallback retains the recorded commit,
change, parents, empty/conflict flags, and description with
`recorded_maybe_stale` freshness. The refresh and fallback failures have
distinct stages.

Path evidence is then read from recorded `@` with:

```text
jj diff -r @ --summary --ignore-working-copy
```

Other enumerated jj workspaces are not refreshed through the requested
workspace's filesystem location. Their refresh state is `skipped` and their
freshness is `recorded_maybe_stale`. History, bookmarks, visible heads, and
workspace enumeration continue to use `--ignore-working-copy` after the
primary refresh attempt.

These templates and fallback behaviors are exercised against jj 0.42.0. The
history template quotes NUL separators and includes both author and committer
timestamps, matching the ten-field retained history record.
