# vcs-tree

`vcs-tree` inventories Git and Jujutsu repositories below a directory and
renders their working-copy state in one compact tree.

This repository is the incubation surface for turning the existing
`Resources/tools/vcs-tree.py` script into a reusable package. During
incubation, the resource script and its shell wrapper remain the live command.
The copy here may evolve without silently changing that operational surface.

## Current State

- `vcs-tree.py` is an unchanged baseline copy of
  `../../Resources/tools/vcs-tree.py`.
- There is no package extraction or installed entry point yet.
- Run the copied baseline directly:

  ```bash
  python3 vcs-tree.py ~/Documents
  ```

## Direction

The package should provide factual inputs for movement assessment:

- repository discovery across Git, jj, and colocated repositories;
- working-copy state and readable failure states;
- refs/bookmarks and their movement;
- versioned snapshots and snapshot-to-snapshot deltas;
- commit/change identifiers, timestamps, and short descriptions;
- file-level descriptions useful for recognizing task creation and closure.

Higher-level callers decide whether observed movement constitutes progress.
The package should not infer project health from cleanliness, activity, or
commit volume alone.

## Semantic States

Commit recency has three meaningful states:

- a real date means a repository has a real committed parent;
- jj's `00000000` null root means the repository is initialized but has no
  real commit yet;
- an explicit error means repository state could not be read.

These states must remain distinct in data and rendering.

## Incubation and Graduation

`Projects/vcs-tree/` is an incubation location. Once the CLI, versioned
snapshot format, Git/jj behavior, ref/delta semantics, and compatibility
story are stable, the package will likely graduate to
`Resources/tools/vcs-tree/`.

Consumers should eventually invoke an installed `vcs-tree` entry point rather
than depend on either filesystem location. No cutover is part of the bootstrap
task.

## Project Surfaces

- `AGENTS.md` — local operating rules
- `inbox/` — accepted project objectives and delegations
- `tasks/open/` — active and inception work
- `tasks/closed/` — completed task evidence
- `tasks/WORKBOARD.md` — current operational index

