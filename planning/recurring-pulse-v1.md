# Recurring Movement Pulse v1

Status: accepted for implementation; jj change-graph correction applied

Schema identifier: `vcs-tree.history-pulse`

Schema version: `1`

## Purpose

The recurring movement pulse is one read-only operator workflow that captures a
new history snapshot, compares it with a comparable retained snapshot, and
turns the existing factual delta into a self-describing movement brief.

The pulse answers “what moved, and what evidence supports that description?”
It does not decide whether movement is progress, completion, regression,
important, healthy, or aligned with a priority.

Scheduling is outside the package. Cron, launchd, Codex, and other hosts may
invoke and consume the command, but they do not own pulse semantics.

## Normative Language

The words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are normative.

## Command Contract

```text
vcs-tree history pulse [PATH]
    [--state-root PATH]
    [--from SNAPSHOT]
    [--format summary|audit|json]
    [--max-enrichment-objects N]
    [--max-changed-paths N]
```

- `PATH` defaults to `.` and resolves to a canonical absolute scan root before
  candidate selection or collection.
- `--state-root` has the same authoritative-state meaning as the other history
  commands.
- `--from` selects one retained source snapshot. It never names the newly
  captured target snapshot.
- `--format summary` is the default signal-first human output.
- `--format audit` is deterministic human output including no-op repositories,
  native identifiers, path evidence, and all warnings.
- `--format json` emits the complete canonical pulse document.
- `--max-enrichment-objects` defaults to 256 delta-relevant history objects.
- `--max-changed-paths` defaults to 10,000 complete path entries across the
  pulse.

The two limits bound optional enrichment, not repository discovery, snapshot
collection, or base-delta calculation. Exceeding a limit MUST NOT silently
truncate a list. The affected enrichment component becomes `partial`, a stable
`limit_exceeded` warning identifies the omitted evidence class, and the pulse
exit status is partial.

Progress, collection status, and location warnings go to stderr. Stdout contains
only the selected output representation. The command MUST NOT fetch, repair,
reset, switch, commit, or otherwise mutate a scanned repository.

## Operation Sequence

The command performs these steps in order:

1. Resolve the state root and canonical scan root.
2. Read the retained-snapshot index and preflight an explicit `--from`, if any.
3. Capture and retain a new target snapshot using the existing collector.
4. Select the source snapshot from the pre-capture candidate set.
5. Calculate the v1 history delta, with jj logical-change graph movement as
   the primary jj surface and refs/bookmarks as separate publication hints.
6. Resolve descriptions and path evidence only for movement-relevant objects.
7. Derive factual task-path events and warning lifecycles.
8. Render one pulse document as summary, audit, or JSON.

An explicit invalid comparison MUST fail in preflight and MUST NOT create a
snapshot. A failure during or after collection may leave a valid retained target
snapshot; an error document MUST identify it when available.

## Comparable Snapshot Rules

Two snapshots are comparable for pulse v1 only when all of these are true:

1. Both use supported `vcs-tree.history-snapshot` schema versions.
2. Both belong to the same `history_store.store_id`.
3. The source generation is strictly less than the target generation.
4. Their canonical `scan.root` values are exactly equal.
5. Their collection policy is the same. V1 has one fixed discovery policy, so
   equality of the canonical scan root is the complete policy check.

Repository paths, remote URLs, overlapping directory trees, and coincidental
repository sets MUST NOT substitute for these checks.

### Automatic selection

Without `--from`, the source is the comparable retained snapshot with the
highest generation in the pre-capture candidate set. `captured_at` and
`snapshot_id` break a malformed or legacy generation tie deterministically.

The selector MUST NOT skip a latest comparable snapshot because its scan or a
repository component is partial. Skipping it would hide newly introduced or
persistent uncertainty. The delta completeness gates decide which claims the
partial pair can support.

If no comparable source exists, the command records a successful
`baseline_created` pulse. It retains the target snapshot, emits no movement
claims, and tells the operator that a later pulse can compare against it.

### Explicit selection

`--from` MUST name a retained snapshot that satisfies the store, schema, root,
and generation rules. Failure is operational, with a factual reason such as
`snapshot_not_found`, `store_mismatch`, `scope_mismatch`, or
`source_not_earlier`. The command MUST NOT fall back to another snapshot.

## Enrichment Scope and Cost

Pulse enrichment is delta-driven rather than history-wide. The candidate
object set is the sorted union of object IDs directly named by:

- workspace-head, ref, tag, visible-head, and jj change-version events;
- first-observed, current-line, off-current, reachability, and rewrite events;
- old/new endpoints needed to explain an ancestry movement; and
- parent objects required to state parent-relative changed paths.

The pulse MUST NOT walk unrelated retained history merely to add prose.

For each candidate object, the pulse exposes available immutable ledger facts:

- native commit ID and object kind;
- jj change ID when present;
- ordered parent IDs;
- short description;
- author and committer timestamps as distinct facts;
- authorities that exposed the object, including Git refs/tags and jj
  bookmarks/visible heads; and
- complete parent-relative changed paths when collected.

Git and jj/colocated repositories share this public description shape. A jj
logical change is identified by `change_id`, but every visible commit version
retains its own ID, parents, visibility, and exposing authorities; it is not
collapsed to one description or synthetic stack. Unnamed topology is carried
by parent edges, visible heads, and workspace heads. The jj null root remains `virtual_root` with ID
`00000000` and has no fabricated author, committer, description, or date.

Descriptions already present in immutable ledger objects SHOULD be reused.
Changed-path collection MUST be read-only and stored as immutable
object/parent evidence so later pulses do not repeat native queries. Missing,
partial, or unsupported path detail remains explicit and does not invalidate a
complete base delta.

## Changed-Path Vocabulary

Each entry is parent-relative and uses one of:

- `added` with `path`;
- `modified` with `path`;
- `deleted` with `path`;
- `renamed` with `old_path` and `path`;
- `copied` with `old_path` and `path`;
- `type_changed` with `path`; or
- `unmerged` with `path`.

An entry includes `commit_id` and `parent_id`; `parent_id` is `null` for a root
comparison. Paths are repository-relative POSIX strings. Rename and copy claims
MUST come from the native diff result and its configured detection policy.
Separate delete/add entries MUST NOT be rewritten as a rename by the pulse.

Merge commits retain one evidence group per parent. The pulse MUST NOT merge
different parent-relative views into a single synthetic change list.

## Task-Path Event Semantics

Pulse v1 recognizes only repository-root-relative Markdown paths under:

```text
tasks/open/**.md
tasks/closed/**.md
```

Matching is case-sensitive. The path is evidence; filename text and embedded
dates are not event time, intent, priority, or status authority.

The event vocabulary is:

- `task_path_added`: an `added` file entry enters an open or closed task path;
- `task_path_removed`: a `deleted` file entry leaves an open or closed task
  path;
- `task_path_moved`: a native `renamed` entry crosses between open and closed;
- `task_path_renamed`: a native `renamed` entry stays within one task area;
- `task_path_copied`: a native `copied` entry has an open or closed task path
  as source or destination; and
- `task_path_modified`: a task path is modified or type-changed.

Every event includes the underlying changed-path entry, object/parent IDs, and
`from_area`/`to_area` values from `open`, `closed`, or `outside`.

Only a native rename from `tasks/open/` to `tasks/closed/` may render as “task
path moved open → closed.” Adding a file directly under `tasks/closed/` renders
as “closed-task path added”; it MUST NOT claim that a previously open task was
closed. Delete/add pairs, copies, merge-parent disagreement, and incomplete path
collection remain separate or explicitly ambiguous.

Task-path events describe repository structure. They MUST NOT say that work was
completed, accepted, useful, or performed during the filename’s date.

## Warning Identity and Lifecycle

Warnings cover scan/repository collection outcomes, history boundaries,
comparison suppression, missing enrichment, and resource limits. Each warning
has a stable identity:

```text
repository-key | component | kind | stage | affected-event-class
```

The scope-level repository key is `@scan`. Empty fields use `-`. Mutable text,
snapshot IDs, generations, timestamps, path spellings, and exit messages MUST
NOT participate in the identity. The complete tuple is serialized as
`warning_key` without hashing in v1 so operators can inspect it.

Lifecycle is calculated from normalized warning sets in the source and target
observations:

- `new`: absent in the source warning set and present in the target;
- `persistent`: present in both; and
- `recovered`: present in the source and absent in the target.

Comparison-only warnings that cannot be attributed to one observation are
`new` for that pulse and carry both evidence states. A changed error `message`
with the same stable identity remains persistent; the current message is shown
as detail. A changed `kind`, `stage`, component, or affected event class is a
recovery plus a new warning, not an in-place mutation.

Null roots, verified no movement, and a first baseline are states, not warnings.
Persistent warnings remain visible in the concise summary after new and
recovered groups; repetition MUST NOT obscure lifecycle changes.

## Pulse JSON Envelope

```json
{
  "schema": "vcs-tree.history-pulse",
  "schema_version": 1,
  "pulse_id": "pulse-snapshot-8",
  "generated_at": "2026-08-02T15:00:00Z",
  "scope": {"root": "/Users/tim/Documents"},
  "target_snapshot": {
    "snapshot_id": "snapshot-8",
    "generation": 8,
    "captured_at": "2026-08-02T14:59:00Z"
  },
  "comparison": {
    "state": "selected",
    "selection": "automatic",
    "source_snapshot_id": "snapshot-7",
    "source_generation": 7
  },
  "outcome": {"state": "complete", "errors": []},
  "movement": {"state": "observed", "repository_count": 1},
  "repositories": [],
  "warnings": [],
  "summary": {
    "observed_repositories": 68,
    "movement_repositories": 1,
    "no_op_repositories": 67,
    "task_path_events": 1,
    "new_warnings": 0,
    "persistent_warnings": 0,
    "recovered_warnings": 0
  }
}
```

`comparison.state` is `selected` or `baseline_created`.
`comparison.selection` is `automatic`, `explicit`, or `none`.

`outcome.state` is:

- `complete`: collection, delta, and requested enrichment are complete;
- `partial`: the document contains useful facts but at least one requested
  claim was suppressed or enrichment was incomplete; or
- `error`: no trustworthy pulse result could be completed.

`movement.state` is `observed`, `empty`, `unknown`, or `baseline`.
`unknown` is required when incompleteness prevents deciding whether any
movement occurred. A pulse may have `movement.state: "observed"` and
`outcome.state: "partial"` when some movement is factual but other claims are
suppressed.

Repository entries are sorted by scan-relative path, then repository key, and
contain:

- `repository_key`, `path`, and `mode`;
- the complete base `events` array from history delta v1;
- sorted `descriptions` for delta-relevant objects;
- complete `path_evidence` groups when available;
- derived `task_path_events`; and
- repository warning keys.

The JSON representation never omits verified no-op repositories. Human summary
may collapse them; audit and JSON retain them. All arrays are deterministic.

## Exit Behavior

| Exit | Meaning |
| ---: | --- |
| `0` | Complete movement, empty, or baseline pulse. Inspect JSON state to distinguish them. |
| `2` | Command-line usage error, consistent with argparse. No pulse contract is promised. |
| `3` | Partial pulse. A pulse document exists and contains usable facts plus explicit uncertainty. |
| `4` | Operational failure. No trustworthy pulse was completed; an error document is emitted when possible. |

A complete pulse with observed movement is not a process failure and returns
zero. Hosts decide whether movement should trigger another action.

## Human Output

### Summary

The default output is signal-first:

```text
pulse /Users/tim/Documents: generation 7 -> 8 (complete)
vcs-tree [colocated]
  aea6409b  chore: reconcile task workboard
  paths: M tasks/WORKBOARD.md; A tasks/closed/260802-reconcile-workboard.md
  task path: added directly in closed tasks/closed/260802-reconcile-workboard.md
67 repositories with no observed movement
warnings: 0 new, 0 persistent, 0 recovered
```

This grounded generation-7-to-8 example deliberately says that a closed-task
path was added. Because the evidence is not an open-to-closed rename, it does
not claim that the task transitioned during the interval.

### Audit

Audit includes snapshot/store identifiers, every repository, base delta event
keys, full native IDs, descriptions, parent-relative paths, task-path events,
and warning details. A verified no-op repository renders “no observed
movement.” Audit ordering matches JSON ordering.

### No movement

```text
pulse /workspace: generation 8 -> 9 (complete)
no observed movement across 68 repositories
warnings: 0 new, 0 persistent, 0 recovered
```

### Partial evidence

```text
pulse /workspace: generation 9 -> 10 (partial)
project [colocated]
  workspace head changed abcdef12 -> 01234567
  description/path evidence unavailable
warnings: 1 new, 2 persistent, 0 recovered
  NEW project | history | timeout | jj.history | description,path
some movement is observed; additional conclusions were suppressed
```

The corresponding JSON uses `outcome.state: "partial"`,
`movement.state: "observed"`, and exit `3`.

### Baseline

```text
pulse /workspace: baseline generation 1 captured (complete)
no comparable prior snapshot; no movement comparison was made
```

## Failure Boundaries

- A scan-level or store failure that prevents a target snapshot is operational
  failure.
- A retained target with partial scan outcome produces a partial pulse when a
  comparison can still be calculated.
- An incomplete repository component suppresses only dependent claims under
  the existing delta completeness gates.
- Missing descriptions or changed paths make enrichment partial; they do not
  erase base movement events.
- Ledger corruption is reported and never authorizes source-repository writes.
- An explicit comparison mismatch is operational failure, never an automatic
  fallback.

## jj-First Movement Contract

For jj and colocated repositories, `change_versions_changed`, visible-head,
workspace-head, and parent-topology events are primary movement facts. They do
not require a bookmark. Git refs and jj bookmarks are optional publication
hints with separate authority provenance; bookmark incompleteness can suppress
only publication absence/target claims. Positive graph movement supported by
valid records remains observable under partial bookmark collection.

The retained generation-7-to-8 example remains valid for Git/task-path
evidence. A bookmark-free jj example is normative: an unnamed stack grows,
one logical change is rewritten, a rebase changes a parent edge, and a sibling
stack gains a visible head. Each change/version/topology/head fact remains
describable without inventing a stack name.

Before/after graph fixture (no bookmarks):

```text
before: change C1 -> version v1, parent null-root; visible head v1
after:  change C1 -> version v2, parent v0; visible head v2
        change C2 -> version w1, parent v2; visible head w1
delta:  C1 rewritten + topology_changed; C2 introduced;
        visible_head_added(v2), visible_head_added(w1)
```

Colocated publication-hint fixture:

```text
before: C1/v1 visible; local bookmark topic -> v1; remote bookmark absent
after:  C1/v2 visible; local bookmark topic -> v2; remote bookmark malformed
delta:  C1 rewritten and visible-head movement remain observed;
        remote bookmark absence/target is comparison_incomplete only
```

## Compatibility and Non-Goals

Pulse v1 consumes history snapshot v1 and history delta v1. It does not change
the existing default scanner invocation or the live resource script/wrapper.

Pulse v1 does not:

- schedule itself or define host retry policy;
- infer progress, health, priority, ownership, or intent;
- treat a task filename date as an event timestamp;
- infer a rename from separate additions and deletions;
- fetch remote state or mutate source repositories;
- compare stores or scan roots by heuristic identity; or
- hide a latest partial observation to produce a cleaner comparison.

## Implementation Dispatch

The implementation is split into the following ordered tasks:

1. `260802-implement-pulse-orchestration` — pulse envelope, preflight,
   comparable-snapshot selection, and orchestration.
2. `260802-enrich-pulse-movement-evidence` — immutable descriptions and
   parent-relative changed-path evidence across Git and jj/colocated modes.
3. `260802-classify-pulse-task-warnings` — task-path derivation and stable
   warning lifecycle classification.
4. `260803-integrate-change-graph-pulse` — adapt pulse enrichment and warning
   semantics to consume the jj-first delta.
5. `260802-expose-pulse-output-workflow` — CLI, summary/audit/JSON rendering,
   exit behavior, and end-to-end evidence after change-graph integration.
6. `260802-document-recurring-pulse-adapters` — thin host invocation and
   consumption guidance after the CLI is proven.

The contract correction is complete. `260803-persist-jj-change-graph` is now
the next ready implementation slice; subsequent tasks retain explicit
dependencies and non-overlapping primary write surfaces.
