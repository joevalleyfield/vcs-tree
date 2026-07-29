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

## Controlled Before/After Fixtures

Fixtures were created under an isolated temporary root. Their remotes were
local bare repositories; no network or non-fixture repository was mutated.

### Git fetch and off-current work

The observer began with `main`, `origin/main`, and one reachable base commit.
After another clone pushed `side` with two commits:

- `git fetch` created `origin/side`;
- the selected reachable graph gained exactly the two side commits;
- `git rev-list --remotes --not HEAD` reported both as off-current;
- current `HEAD` and `main` remained unchanged.

A separate `local-work` branch then added one local-only commit while `HEAD`
returned to `main`. Explicit local and remote ref roots therefore expose both
forms of non-current work without scanning internal refs.

### Git tags, force movement, and deletion

An annotated `side-v1` tag pointed to a tag object, not directly to its commit.
`for-each-ref` exposed the tag object plus a peeled commit target. The contract
must preserve the tag ref/object while using the peeled commit as a history
root.

The remote `side` ref was then rewritten from its two-commit line to a new
one-commit line based on `main`. Neither old target was an ancestor of the new
target nor vice versa. Comparing prior/new targets plus graph ancestry is
therefore sufficient to classify a force movement without relying on reflog
text.

After the remote branch was deleted and the observer fetched with pruning:

- `origin/side` disappeared;
- the rewritten target and prior side tip were no longer reachable from the
  selected refs;
- the deleted remote ref's reflog was no longer enumerated;
- `git fsck --unreachable --no-reflogs` still found both commit objects.

This directly supports the append-only observed-history ledger: ref and reflog
surfaces alone do not preserve prior observations after deletion.

### jj fetch

A non-colocated jj clone initially had tracked `main` local/remote bookmarks.
After the local remote gained `jj-side`:

- `jj git fetch` created untracked `jj-side@origin`;
- it was visible only because collection used `bookmark list --all-remotes`;
- `remote_bookmarks(remote="origin") ~ ::@` selected the fetched off-current
  commit.

A subsequent fast-forward fetch moved that remote bookmark to a child commit;
the revset from old target to new target returned exactly the new commit.
Untracked remote bookmarks must therefore be included in the factual snapshot
even though jj's default bookmark listing omits them.

### jj null root and non-colocated identity

`jj git init --no-colocate` created no worktree `.git`; its backing Git store
lived under `.jj/repo/store/git`. The initial visible graph contained:

- a working-copy commit with a normal jj change ID and commit ID;
- parent commit ID `0000000000000000000000000000000000000000`;
- virtual-root change ID `zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz`.

The null root is therefore an explicit native graph object, not a missing date
or collection failure.

### jj rewrite, hidden predecessor, and visible heads

Describing the initial working-copy change:

- preserved its change ID;
- replaced its commit ID;
- removed the predecessor commit from `all()`;
- retained both versions in `jj evolog`.

Creating a side line and then a new working copy from `root()` left the side
commit as an unbookmarked off-current member of `visible_heads()`. Bookmark
roots alone are not enough to observe jj work.

### jj divergent change and bookmark conflict

Two concurrent descriptions from the same operation produced two visible
commit IDs with the same change ID. `divergent()` selected both versions.
Graph storage must key edges by commit ID while retaining change ID as a
logical relationship.

Two concurrent creations of bookmark `topic` at different visible heads
produced a conflicted `CommitRef` with:

- no normal target;
- no removed target in this creation/creation case;
- two added targets.

Ref records therefore need target sets and conflict state rather than a single
nullable target field.

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
8. Represent annotated ref objects separately from their peeled history
   targets.
9. Represent jj ref conflicts with removed/added target sets, not one target.
10. Include untracked remote bookmarks and visible heads in jj's default
    factual observation boundary.
11. Classify ref movement from old/new targets and ancestry; retain native
    fetch/reflog messages only as optional provenance.

## Remaining Contract Cases

The controlled fixtures grounded:

- Git fetch adding a remote-only unrelated branch;
- remote ref fast-forward, force-update, and deletion;
- a local Git branch with work not reachable from current `HEAD`;
- Git annotated tags and peeled targets;
- reflog-only and dangling commits;
- independent jj-only repository identity;
- jj bookmark conflict and divergent change ID;
- jj hidden predecessor versus visible successor;
- jj null-root repository;

Repository-read and partial-collection errors remain represented by the
existing scanner behavior/tests but need explicit placement in the manifest
contract. Remote jj bookmark deletion/force movement can share the same
old-target/new-target ancestry classification unless later evidence shows
native semantics that must be retained.

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

## Next Contract Step

Draft the first versioned manifest and delta contract from these observations.
Keep portable repository identity, unreachable-history retention, optional
reflog evidence, and jj operation history as explicit unresolved policy
questions rather than burying them in adapter implementation.
