# Tasks

This directory tracks active, closed, and inception work for `vcs-tree`.

## Naming

Use `YYMMDD-short-intent.md`:

```text
tasks/open/260728-movement-snapshot-package.md
```

Every task begins with:

```markdown
Filed as: YYMMDD-short-intent
FKA:
AKA:
Legacy index:

keywords:

Parent:
Depends on:
Blocks:
Blocked by:
Related:
```

`Filed as` never changes. Preserve prior names under `FKA`, search-friendly
aliases under `AKA`, and old numeric identifiers under `Legacy index`.

## Relationships and Lifecycle

- `Parent` provides a navigation root.
- `Depends on` records causal prerequisites.
- `Blocked by` is the unresolved subset of dependencies.
- `Blocks` records active downstream gates.
- `Related` records adjacency without ordering.

Include one lifecycle keyword:

- `active` — ready or underway;
- `inception` — a grounded pressure not yet narrow enough to implement;
- `parked` — intentionally deferred;
- `blocked` — cannot proceed until a named condition changes;
- `follow-on` — bounded work derived from a parent;
- `historical` — retained for reference.

## Queue Movement

- Active or inception work lives in `tasks/open/`.
- Completed work moves to `tasks/closed/`.
- Add decisions and verification evidence before closing.
- Update `tasks/WORKBOARD.md` whenever queue membership or disposition changes.

