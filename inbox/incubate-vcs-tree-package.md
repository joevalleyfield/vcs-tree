# Delegation: Incubate vcs-tree as a Package

## Status
Accepted

## Date
2026-07-28

## Source Objective
`Journal/objectives/incubate-vcs-tree-package.md`

## Desired Reality
This project begins as a faithful, isolated copy of the live resource script
with enough local documentation and task discipline to support a behavior-
preserving package extraction. The resource command remains live until a later
explicit cutover, and the incubator may eventually graduate back to
`Resources/tools/` after stabilization.

## Constraints
- Do not modify or redirect the live resource script or wrapper.
- Preserve explicit distinctions among real commit dates, jj null-root
  `00000000`, and repository-read errors.
- Collect factual movement evidence; do not embed project-health judgment in
  the package.

