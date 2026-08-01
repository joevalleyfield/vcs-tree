Filed as: 260803-define-nested-repository-semantics
FKA:
AKA: nested discovery contract; repository ownership boundaries
Legacy index:

keywords: tooling, closed, nested, discovery, ownership, deduplication, boundaries

Parent: `260728-movement-snapshot-package`
Depends on: `260728-movement-snapshot-package`; `260802-end-to-end-workflow-testing`
Blocks: `260803-restore-nested-repository-reporting`
Blocked by:
Related: `260729-explore-history-surfaces`

# Define Nested Repository Discovery Semantics

Specify the v1 behavior for recursively discovering and reporting nested Git,
jj, and colocated repositories in a scanned tree.

## Acceptance Criteria

- Define whether the scan root itself and every nested repository root are
  eligible, including repositories nested inside another repository.
- Define ownership for a path containing `.git`, `.jj`, or both: one logical
  repository record per resolved root, with colocated mode rather than duplicate
  Git/jj records.
- Define deduplication across repeated discovery, relative-path aliases, and
  symlinked paths without inventing cross-machine identity.
- Define deterministic ordering and stable local repository-key assignment;
  parent and child repositories remain distinct when their roots differ.
- Define scan boundaries, inaccessible directories, metadata directories, and
  partial/error reporting without treating an unreadable child as deletion.
- Record compatibility expectations against the original recursive
  `find_repo_roots` behavior and identify any intentional v1 differences.

## Allowed Write Surfaces

- `docs/contracts/` or `planning/` for the nested-discovery note
- this task file and `tasks/WORKBOARD.md`
- No production source, tests, live resource files, or repository writes.

## Completion Evidence

- Added `docs/contracts/nested-discovery-v1.md`, defining the discovery
  universe, canonical-root ownership, colocated deduplication, parent/child
  boundaries, symlink and metadata traversal, deterministic ordering, local key
  assignment, and partial/error handling.
- The note includes examples and a direct mapping to implementation,
  feature-validation, and E2E-validation tasks.
- The incumbent recursive `.git`/`.jj` behavior is preserved explicitly, with
  v1 additions limited to canonical grouping, outcomes, ordering, and safe
  traversal boundaries.
- No unresolved ownership or boundary question blocks downstream coding.
