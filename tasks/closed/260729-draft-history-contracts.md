Filed as: 260729-draft-history-contracts
FKA:
AKA: snapshot manifest v1; movement delta v1
Legacy index:

keywords: schema, active, contract, snapshots, history, deltas

Parent: `260728-movement-snapshot-package`
Depends on: `260729-explore-history-surfaces`
Blocks:
Blocked by:
Related:

# Draft the History Snapshot and Delta Contracts

Turn the grounded Git/jj surface evidence into reviewable, versioned data
contracts without implementing collectors or persistence.

## Current Reality
Representative and controlled fixtures now establish the native identities,
ref states, visibility boundaries, graph transitions, and error distinctions
the package must preserve. No field-level manifest or delta vocabulary exists.

## Desired Reality
Separate draft contracts define:

- the append-only history ledger and lightweight snapshot manifest;
- repositories/stores, workspaces, native objects, refs, roots, provenance,
  and collection outcomes;
- Git, jj, and colocated authority rules;
- deterministic snapshot-to-snapshot delta events;
- off-current observations, ref movement, reachability loss, rewrites,
  divergence, conflicts, and partial-read behavior;
- versioning, compatibility, invariants, examples, non-goals, and unresolved
  policy decisions.

## Gap Analysis
The investigation provides evidence and design pressure but not a stable
interchange boundary that can be reviewed before implementation decomposition.

## Known Facts / Assumptions / Unknowns
- Fact: the contract must remain factual and must not infer project progress.
- Fact: missing data under partial collection cannot imply deletion.
- Fact: repeated full-history objects do not belong in every snapshot.
- Assumption: JSON objects and RFC 3339 timestamps are the first interchange
  representation.
- Unknown: portable repository identity, retention duration, and optional
  reflog/jj-operation policy remain review decisions.

## Investigations
- Reconcile every proposed field and event with
  `planning/history-surface-exploration.md`.
- Identify which policy questions can remain explicit without making the draft
  unimplementable.

## Models / Forecasts / Risks
- A self-contained snapshot would duplicate history; a ledger-dependent
  snapshot needs explicit store/generation references.
- A single-target ref shape cannot represent jj conflicts or annotated tags.
- Event absence is unsafe when either input component is incomplete.

## Transformations
- Write `docs/contracts/history-snapshot-v1.md`.
- Write `docs/contracts/history-delta-v1.md`.
- Update the parent task with decisions, evidence, and remaining review gates.
- Do not edit package source or tests.

## Allowed Write Surface
- `docs/contracts/history-snapshot-v1.md`
- `docs/contracts/history-delta-v1.md`
- `tasks/open/260728-movement-snapshot-package.md`
- `tasks/open/260729-draft-history-contracts.md`
- `tasks/WORKBOARD.md`

## Out of Bounds
- JSON Schema or Python model implementation.
- Collector, cache, renderer, or CLI changes.
- Choosing a permanent retention duration or global repository identifier.

## Acceptance Criteria
- Both contracts define normative invariants and non-goals.
- Every grounded fixture state has an unambiguous representation or event.
- Null root, real history, and collection errors remain distinct.
- Partial collection suppresses unsupported deletion/movement assertions.
- An example demonstrates remote-only history without current-line movement.
- Open policy questions are explicit and do not leak into adapter behavior.

## Evidence
- `docs/contracts/history-snapshot-v1.md` defines the append-only ledger,
  lightweight snapshot, repositories/stores, workspaces, objects, refs, roots,
  provenance, outcomes, invariants, compatibility, and open policies.
- `docs/contracts/history-delta-v1.md` defines completeness gates and factual
  events for repositories, workspaces, refs, ancestry, reachability,
  first-observation, off-current history, jj changes, tags, and file evidence.
- The remote-only example emits ref creation, first-observation, and
  off-current events while leaving the workspace head unchanged.
- All 22 fenced JSON examples parse successfully with Python's standard JSON
  parser.
- Markdown long-line checks report no lines above 120 characters.
- Manual cross-check covers every controlled fixture state recorded in
  `planning/history-surface-exploration.md`.

## Decisions
- Owner: Codex `/root`; claimed 2026-07-29.
- Draft two contracts rather than combining stored state and comparison
  semantics.
- Use an append-only, content-addressed history ledger plus lightweight
  topology snapshots tied to ledger generations.
- Treat snapshots as ledger-dependent by default; leave portable bundle
  framing to a later contract.
- Make component completeness normative: absence cannot become deletion when
  collection is partial.
- Define “off-current” against the union of all target workspace-head
  closures.
- Use target-set ancestry for ref movement and retain human fetch/reflog
  messages only as optional provenance.
- Keep repository identity, retention, reflog/jj-operation depth, and export
  framing as explicit review questions.

## Open Fronts
- Contract review and selection of policy defaults before implementation
  decomposition.

## Next Actions
- Review the open policy questions, then decompose ledger, snapshot collector,
  and delta implementation into separate tasks.
