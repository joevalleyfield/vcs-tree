# vcs-tree Agent Notes

## Orientation

This is the incubation repository for packaging
`../../Resources/tools/vcs-tree.py`. The resource script and wrapper remain
the live operational command until a separately tasked cutover.

Read `README.md` for the product boundary and `tasks/WORKBOARD.md` for current
work. Workspace-level coordination rules remain in `../../AGENTS.md`.

## VCS

This project uses Git+jj colocation. Prefer `jj` for repository operations.

- Inspect with `jj status`, `jj diff`, and `jj log`.
- Use `jj commit` for coherent changes.
- Do not use raw Git commands unless a Git-specific compatibility check
  requires them.

## Task Discipline

- Any repo-modifying work must have an associated file in `tasks/open/`.
- New tasks use `tasks/open/YYMMDD-short-intent.md`.
- Preserve `Filed as`, `FKA`, `AKA`, `Legacy index`, relationship fields, and
  a flat `keywords:` line.
- A change that materially achieves a task must update that task in the same
  commit.
- Close work by moving its task to `tasks/closed/` with decisions and evidence.
- Keep `tasks/WORKBOARD.md` aligned when tasks open, close, or materially
  change disposition.

## Implementation Boundaries

- Preserve the live files under `Resources/tools/`; do not edit or redirect
  them from this project without an explicit cutover task.
- First extract behavior; do not combine package restructuring with new delta
  semantics unless a task explicitly owns both.
- Keep collection factual. Progress and project-health assessment belong to
  callers.
- Preserve distinct representations for a real commit date, jj null root
  `00000000`, and repository-read errors.
- Treat Git/jj colocation as a first-class mode rather than two unrelated
  scans of the same repository.

## Verification

The bootstrap has no automated suite yet. Re-verify copied baselines by hash
and smoke-run the copied script.

When Python tooling is added, prefer `.codex-local/bin/uvt` over plain `uv`
for local project commands, consistent with workspace guidance.

Before any code commit, run `scripts/check`. It is the repository-local quality
gate and must pass Ruff formatting, Ruff lint, the full pytest suite with the
100% statement-and-branch coverage requirement, and `uv build`. Documentation
and task-only commits may use narrower checks when no source or test files are
changed.
