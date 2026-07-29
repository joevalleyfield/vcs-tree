# Git and jj History-Surface Exploration

## Objective

Identify the factual native surfaces needed to retain enough observed history
to notice:

- a fetch introducing a new line of work;
- commits or changes outside the current branch/bookmark;
- ref movement, deletion, divergence, or loss of reachability;
- multiple jj workspaces sharing one repository.

This is discovery evidence, not a finalized manifest schema.

## Tool Versions

- Git 2.54.0
- jj 0.42.0

All jj inspection used `--ignore-working-copy`. No repository was fetched or
mutated.

## Representative Repositories

### `vcs-tree`: small colocated repository

- `.git` and `.jj` coexist at one workspace root.
- `jj log -r 'all()'` exposed five visible commits including jj's virtual root.
- `git rev-list --all` exposed twelve commits despite there being no user
  branches, remotes, or tags.
- The extra Git reachability came from twelve `refs/jj/keep/*` refs; two
  additional `refs/codex/*` refs pointed to tree objects.
- Git `HEAD` pointed to the committed parent while jj `@` identified the
  separate empty working-copy commit.

This demonstrates that Git `--all` and an unfiltered ref enumeration are not
valid normalized user-history surfaces in a colocated repository.

### `toas`: rich colocated, multi-workspace repository

Time-bound counts from the initial observation:

- 1,519 jj-visible commits from `all()`;
- 40 jj visible heads;
- five jj working-copy commits across linked workspaces;
- 108 local/remote bookmark entries from `bookmark list --all-remotes`;
- 74 Git refs under `refs/heads`, `refs/remotes`, and `refs/tags`;
- 1,448 commits reachable from those Git user-facing ref classes;
- 7,198 commits from naive `git rev-list --all`;
- 7,145 internal `refs/jj/keep/*` refs and four `refs/codex/*` refs.

The current jj working-copy commit and Git `HEAD` were different: jj `@`
pointed to an empty working-copy commit whose parent was Git `HEAD`.

The repository also had:

- remote-only bookmarks visible through both jj and Git remote refs;
- commits reachable from remote refs but not from `HEAD`;
- visible jj heads with no bookmark;
- local, `@git`, and `@origin` bookmark representations that may share one
  target but retain different authority.

### `toas-dogfood`: linked jj workspace

This path has `.jj` but no `.git`. It is not an independent jj-only repository:
its `.jj/repo` file points to `../../toas/.jj/repo`. `jj workspace list`
confirmed five working copies sharing that store and visible history.

Repository identity therefore cannot be equated with the discovered workspace
path or the mere presence of `.jj`. Discovery must distinguish:

- repository/store identity;
- workspace identity and path;
- the current working-copy commit for each workspace.

No independent jj-only repository was found in the initial local project scan.

### `agent-boundaries`: Git-only repository

- `main`, `origin/main`, `origin/master`, and `origin/HEAD` all resolved to the
  same target during observation.
- All sixteen ref-reachable commits were also reachable from the current
  branch.
- Reflog output retained fetch and branch-rename events, but introduced no
  additional commit IDs in this example.

This provides a clean Git-only baseline but not an off-branch or force-update
case.

## Native Collection Surfaces

### Git

Candidate factual surfaces:

- `git for-each-ref` over explicit `refs/heads`, `refs/remotes`, and
  `refs/tags`, with ref name, object ID/type, and upstream;
- `git rev-list --parents` from the selected ref targets for the reachable
  commit graph;
- `git log`/`git cat-file` formatting for author, committer, timestamps, and
  subject;
- `git symbolic-ref -q HEAD`, falling back to `git rev-parse HEAD`, for Git-only
  checkout identity;
- `git reflog --all` only for an optional deeper observation mode.

In colocation, raw `--all` includes implementation refs and must not define the
default history boundary.

### jj

Candidate factual surfaces:

- `jj bookmark list --all-remotes -T ...`, whose `CommitRef` exposes name,
  remote, presence, conflict, normal/removed/added targets, tracking state, and
  ahead/behind counts;
- `jj log -r 'all()' -T ...` for all visible commits;
- `visible_heads()` for unbookmarked visible work;
- `working_copies()` and `current_working_copy` for workspace checkout
  identity;
- commit templates exposing commit ID, change ID, parents, author/committer
  timestamps, descriptions, bookmarks, remote bookmarks, and tags;
- `jj workspace list` and the `.jj/repo` pointer for workspace/store
  relationships.

`all()` is explicitly the visible commit universe, not every hidden historical
commit. Hidden predecessors may still be reachable by explicit ID or operation
history, so “full observed history” must not be described as the entire jj
object store.

## Initial Contract Implications

These are grounded directions, not field-level schema decisions:

1. Use native adapters and retain native identity. Git commit ID and jj commit
   ID are object identities; jj change ID is a distinct logical-change
   identity and must not replace commit ID in graph edges.
2. Record explicit ref authority: local, remote name, Git-tracking, tag, jj
   visible head, or workspace head. Equal targets do not make these sources
   interchangeable.
3. Treat repository/store and workspace as separate entities.
4. In colocated mode, jj is authoritative for working copies and visible heads;
   explicit Git user ref namespaces remain useful compatibility evidence.
5. Build the durable history store from the union of selected native roots and
   their parent closure, deduplicated by native object ID.
6. Keep snapshots lightweight: record the observed roots/ref topology,
   workspace heads, and collection outcome; persist newly seen history objects
   separately.
7. Preserve formerly observed objects even after refs move or disappear so a
   later delta can describe loss of reachability or force movement.

## Required Fixtures

Local observation does not yet ground these states:

- Git fetch adding a remote-only unrelated branch;
- remote ref fast-forward, force-update, and deletion;
- a local Git branch with work not reachable from current `HEAD`;
- Git annotated tags and peeled targets;
- reflog-only and dangling commits;
- independent jj-only repository identity;
- jj bookmark conflict and divergent change ID;
- jj hidden predecessor versus visible successor;
- jj null-root repository;
- repository-read and partial-collection errors.

Each fixture should take before/after observations so the future delta
vocabulary is tested against evidence rather than inferred from a final state.

## Open Questions

- Should optional Git reflog evidence be stored in the same history ledger or
  a separate ephemeral-observation channel?
- What stable repository/store identifier can be collected portably without
  exposing machine-specific paths?
- How should annotated tags and symbolic refs be normalized while retaining
  their native forms?
- How long should formerly observed but no-longer-reachable objects remain?
- Which jj operation-history surfaces, if any, belong outside the default
  visible-history contract?

## Next Exploration

Create controlled temporary fixtures for fetch, off-current work, force
movement, jj-only identity, bookmark conflict/divergence, null root, and hidden
history. Use their before/after output to draft the first manifest and delta
contract.
