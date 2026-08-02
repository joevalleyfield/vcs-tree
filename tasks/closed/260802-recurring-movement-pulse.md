Filed as: 260802-recurring-movement-pulse
FKA:
AKA: workspace pulse, self-describing delta, movement assessment input
Legacy index:

keywords: cli, tooling, decomp, closed, contract, pulse, automation, movement

Parent: 260728-movement-snapshot-package
Depends on: 260804-history-observability-and-index, 260805-delta-presentation-surfaces, 260806-history-completeness-and-bookmarks
Blocks: 260802-implement-pulse-orchestration, 260802-enrich-pulse-movement-evidence, 260802-classify-pulse-task-warnings, 260802-expose-pulse-output-workflow, 260802-document-recurring-pulse-adapters
Blocked by:
Related: 260802-reconcile-workboard

# Operationalize the Recurring Movement Pulse

Define and decompose a single operator workflow that turns retained repository
observations into a factual, assessment-ready movement brief. The package must
describe what moved and what evidence supports that description; deciding
whether the movement is useful progress remains a human or agent responsibility.

## Grounded Pressure

The history package already exposes initialization, inspection, snapshots,
retained-snapshot listing, and deltas. A live trial across `/Users/tim/Documents`
captured 68 repositories and compared generations 7 and 8. The delta correctly
identified a `vcs-tree` workspace-head change, but recovering the useful account
of that movement still required a separate jj query:

- commit `aea6409b` — `chore: reconcile task workboard`;
- modified `tasks/WORKBOARD.md`;
- added `tasks/closed/260802-reconcile-workboard.md`.

The primitives therefore detect movement, while the operator still has to
select the comparison, correlate commit descriptions, inspect changed paths,
and translate task-path transitions into factual lifecycle events.

## Desired Operator Contract

Settled as:

```text
vcs-tree history pulse [PATH]
```

One invocation will:

1. capture a new observation of the requested scope;
2. choose or accept an explicit comparable prior observation;
3. calculate the factual delta;
4. enrich detected movement with available commit/change identifiers, short
   descriptions, refs/bookmarks, and changed paths;
5. report recognizable task creation and closure path events without inferring
   intent from filenames or dates;
6. group uncertainty as new, persistent, or recovered; and
7. render concise human output plus a stable machine-readable form.

The operation remains read-only with respect to scanned repositories. It
distinguishes baseline, empty pulse, partial evidence, and operational failure
with documented output and exits. It does not label movement as progress,
completion, regression, priority, or importance.

## Facts and Constraints

- The live scan currently covers 68 repositories and takes roughly one minute.
  The command supports scheduled or background use, but scheduling is a host
  concern rather than package-core behavior.
- Git and jj/colocated repositories use one coherent description model;
  Git-only assumptions are not part of the public contract.
- Rewrites, divergence, off-current work, null roots, incomplete ancestry, and
  suppressed history movement remain explicit evidence states.
- A task filename date is not authoritative event time. Task creation and
  closure descriptions derive from observed path transitions and
  version-control evidence.
- Existing ledgers can contain persistent completeness warnings. Repetition
  does not obscure newly introduced or newly recovered uncertainty.
- The existing resource script and wrapper remain the live operational command
  until the incubating package is intentionally cut over.

## Acceptance Criteria

- A planning artifact under `planning/` fixes the v1 pulse inputs, comparison
  rules, event vocabulary, output modes, and exit behavior.
- Examples cover the observed generation-7-to-8 movement, including the commit
  description and closed-task path, as well as no-movement, baseline, and
  partial-evidence cases.
- The contract preserves null roots and uncertainty without manufacturing a
  last-commit date or other unavailable facts.
- Follow-on task artifacts divide implementation into independently claimable
  units with explicit write surfaces, fixtures, dependencies, and verification
  evidence.
- The core contract contains no dependency on Codex, cron, launchd, or another
  scheduler; host documentation may show those as adapters.
- No production source, tests, retained history, or live resource command was
  changed during planning.

## Allowed Write Surfaces

- `tasks/`
- `planning/`
- `docs/contracts/`

## Completion Evidence

- Added `planning/recurring-pulse-v1.md` with the command grammar, operation
  sequence, exact comparison rules, cost bounds, enrichment and path vocabulary,
  task-path semantics, warning identities/lifecycles, pulse envelope, stable
  rendering modes, exit codes, examples, and failure boundaries.
- Grounded the summary example in generations 7 to 8 and explicitly classified
  `tasks/closed/260802-reconcile-workboard.md` as a direct closed-task-path
  addition, not a proven open-to-closed transition.
- Dispatched five follow-on tasks. Orchestration and enrichment are ready;
  semantics, output/E2E, and host documentation have explicit dependencies.
- Each child names acceptance criteria, exact allowed write surfaces, required
  fixtures/examples, and completion evidence.
- Validation parsed every fenced JSON object, checked task/workboard references,
  and confirmed that no production source, tests, retained history, baseline,
  or live resource file changed.
- The full `scripts/check` gate passed: Ruff formatting and lint, 146 tests at
  100% statement and branch coverage, and both source and wheel builds.

## Decisions

- Owner: Codex `/root`; planning completed 2026-08-02.
- Automatic selection uses the newest earlier snapshot in the same store with
  the exact canonical scan root and does not skip partial observations.
- A pulse returns zero for any complete result, whether movement, empty, or
  baseline; partial is `3`, operational failure is `4`, and argparse keeps `2`.
- Enrichment is delta-driven and bounded. Limits create explicit partial
  evidence and never silently truncate a complete list.
- Task events remain path-factual. Only a native rename proves an open/closed
  move; direct additions and delete/add pairs retain their literal evidence.
- Warning identity excludes mutable messages and observation-specific IDs so
  new, persistent, and recovered uncertainty remains comparable.
- Host scheduling remains a thin adapter after the public CLI is proven.

## Next Actions

- Claim either `260802-implement-pulse-orchestration` or
  `260802-enrich-pulse-movement-evidence`.
- Do not begin dependent task/warning, output, or host-documentation work until
  its declared blockers close.
