# Nested Repository Discovery Contract v1

Status: ready for implementation

This note defines how a tree scan discovers and owns nested Git, jj, and
colocated repositories. It applies to package snapshot collection and to the
operator-facing tree report. It does not change the native Git/jj history
boundaries or assign portable clone identity.

## Normative language

The words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are normative.

## Discovery universe

Given a requested scan root:

1. The scan root MUST be resolved to an absolute canonical path before
   discovery. If it is itself a repository root, it is eligible.
2. Every descendant directory containing a `.git` directory or a `.jj`
   directory is an eligible repository root. A repository nested inside another
   repository is not excluded by the parent.
3. `.git` files (for example, indirections used by some worktrees or
   submodules) are outside this v1 discovery universe, matching the incumbent
   scanner's directory-marker behavior.
4. Recursive traversal MUST NOT descend into `.git` or `.jj` metadata trees.
   Directory symlinks encountered during traversal MUST NOT be followed.
   An explicitly supplied scan-root symlink is resolved before applying these
   rules.
5. A child whose metadata or parent directory cannot be read MUST NOT erase or
   hide other discovered roots. The scan outcome records an explicit partial or
   error item for that path and continues where possible.

## Repository ownership

Candidate roots are grouped by their canonical resolved root path.

- One canonical root produces exactly one logical repository observation.
- A root with `.git` only is `git`; `.jj` only is `jj`; both markers produce
  one `colocated` observation.
- Colocation MUST NOT produce two repository records, two snapshot entries, or
  two local repository keys.
- Distinct canonical roots remain distinct even when one is nested below the
  other, shares a remote URL, or points at the same native store through a
  workspace relationship. Native adapters may report shared-store hints, but
  the local ledger key is assigned to the observed root continuity record.
- Discovery itself is read-only; no repository is initialized, fetched,
  updated, or rewritten while finding and grouping roots. A later history
  collection may perform the narrowly authorized native jj working-copy
  snapshot defined by `history-snapshot-v1.md`; that observation side effect is
  not part of discovery.

## Aliases and deduplication

- Repeated marker discovery for one canonical root MUST collapse to one
  candidate before adapter invocation.
- Relative paths, absolute paths, and an explicitly supplied symlink alias to
  the same scan root MUST resolve to the same scan scope and local continuity
  identity.
- A symlink alias discovered beneath the scan root is not traversed in v1. If
  an integration supplies aliases explicitly, canonical-root grouping still
  MUST prevent duplicate records.
- No cross-machine or portable clone identity is inferred from path, remote,
  or native store hints. Canonical paths only stabilize one local ledger's
  observation universe.

## Ordering and presentation

- Candidate roots MUST be sorted by canonical path using a stable lexical
  ordering before adapter invocation and persistence.
- Display paths are POSIX-style paths relative to the canonical scan root;
  the scan root itself is `.`. They MUST be deterministic and MUST NOT be used
  as repository identity.
- Parent and child roots appear as separate entries in sorted order. A
  colocated entry appears once at its relative path.
- Repository keys are requested from the local ledger in this sorted order.
  Repeated scans reuse existing keys; new roots receive keys without renaming
  prior roots.

## Outcomes and boundaries

- The scan envelope reports the requested canonical root and an aggregate
  outcome. A complete scan means all eligible traversed paths were observed;
  a partial/error scan identifies unreadable or malformed paths.
- A repository component error belongs to that repository record and MUST NOT
  be represented as repository absence. A later successful observation may
  recover it.
- A nested root outside the requested canonical scan root is not included,
  even if a native store or symlink points there.
- Empty directories and directories without recognized marker directories are
  not repository records.

## Compatibility mapping

The incumbent `find_repo_roots` behavior is preserved for recursive `.git` and
`.jj` directory discovery, exact-path colocated precedence, and parent/child
reporting. V1 adds canonical-root grouping, explicit scan outcomes, stable
sorted adapter/persistence order, and metadata/symlink traversal boundaries.

## Downstream task mapping

| Rule area | Owning task | Validation |
| --- | --- | --- |
| Discovery universe, ownership, aliases, ordering | `260803-restore-nested-repository-reporting` | `260803-test-nested-repository-features` |
| Snapshot/CLI integration and scan outcomes | `260803-restore-nested-repository-reporting` | `260803-test-nested-repository-e2e` |
| Parent/child, colocated, inaccessible, and compatibility behavior | `260803-test-nested-repository-features` | `260803-test-nested-repository-e2e` |
