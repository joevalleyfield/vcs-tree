Filed as: 260802-recurring-movement-pulse
FKA:
AKA: workspace pulse, self-describing delta, movement assessment input
Legacy index:

keywords: cli, tooling, decomp, active, contract, pulse, automation, movement

Parent: 260728-movement-snapshot-package
Depends on: 260804-history-observability-and-index, 260805-delta-presentation-surfaces, 260806-history-completeness-and-bookmarks
Blocks:
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

Settle a versioned contract, tentatively exposed as:

```text
vcs-tree history pulse PATH
```

One invocation should:

1. capture a new observation of the requested scope;
2. choose or accept an explicit comparable prior observation;
3. calculate the factual delta;
4. enrich detected movement with available commit/change identifiers, short
   descriptions, refs/bookmarks, and changed paths;
5. report recognizable task creation and closure path events without inferring
   intent from filenames or dates;
6. group uncertainty as new, persistent, or recovered; and
7. render concise human output plus a stable machine-readable form.

The operation must remain read-only with respect to scanned repositories. It
must distinguish an empty pulse, partial evidence, and operational failure with
documented exit behavior. It must not label movement as progress, completion,
regression, priority, or importance.

## Facts and Constraints

- The live scan currently covers 68 repositories and takes roughly one minute.
  The command should support scheduled or background use, but scheduling is a
  host concern rather than package-core behavior.
- Git and jj/colocated repositories require one coherent description model;
  Git-only assumptions must not become the public contract.
- Rewrites, divergence, off-current work, null roots, incomplete ancestry, and
  suppressed history movement must remain explicit evidence states.
- A task filename date is not authoritative event time. Task creation and
  closure must derive from observed path transitions and version-control
  evidence.
- Existing ledgers can contain persistent completeness warnings. Repetition
  should not obscure newly introduced or newly recovered uncertainty.
- The existing resource script and wrapper remain the live operational command
  until the incubating package is intentionally cut over.

## Planning Investigations

- Define automatic comparison selection and the rules that make two retained
  observations comparable.
- Define description collection across Git commits, jj changes/commits,
  bookmarks, tags, divergent refs, rewrites, and incomplete history.
- Define task-path event semantics for additions, moves into `tasks/closed/`,
  renames, deletions, and ambiguous rewrites.
- Define stable warning identities and new/persistent/recovered presentation.
- Bound scan and enrichment cost, including explicit scope and comparison
  overrides for recurring use.
- Specify concise terminal, audit, and JSON examples together with exit codes.

## Dispatch Lanes

Once the operator contract is settled, create bounded follow-on tasks for:

1. pulse orchestration and comparable-snapshot selection;
2. movement-description and changed-path enrichment;
3. task-event and warning-lifecycle presentation;
4. human/JSON output, exit behavior, and end-to-end evidence; and
5. host-adapter documentation for recurring invocation.

Each follow-on must name acceptance criteria, allowed write surfaces, fixtures,
and completion evidence. Keep host integrations thin: they invoke and consume
the CLI rather than owning pulse semantics.

## Acceptance Criteria

- A planning artifact under `planning/` or `docs/contracts/` fixes the v1 pulse
  inputs, comparison rules, event vocabulary, output modes, and exit behavior.
- Examples cover the observed generation-7-to-8 movement, including the commit
  description and task closure, as well as no-movement and partial-evidence
  cases.
- The contract preserves null roots and uncertainty without manufacturing a
  last-commit date or other unavailable facts.
- Follow-on task artifacts divide implementation into independently claimable
  units with explicit write surfaces and verification evidence.
- The core contract contains no dependency on Codex, cron, launchd, or another
  scheduler; host documentation may show those as adapters.
- No production source, tests, retained history, or live resource command is
  changed while this parent remains in planning.

## Allowed Write Surfaces

- `tasks/`
- `planning/`
- `docs/contracts/`

## Next Action

Claim this parent as a planning task, draft `planning/recurring-pulse-v1.md`,
and dispatch the bounded implementation tasks only after the examples expose a
stable operator contract.
