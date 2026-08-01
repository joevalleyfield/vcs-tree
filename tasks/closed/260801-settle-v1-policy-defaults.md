Filed as: 260801-settle-v1-policy-defaults
FKA:
AKA: single-writer local state; non-custodial history policy
Legacy index:

keywords: schema, active, contract, policy, storage, resilience

Parent: `260728-movement-snapshot-package`
Depends on: `260729-draft-history-contracts`
Blocks:
Blocked by:
Related:

# Settle the Initial History-Contract Policies

Record the accepted v1 defaults for identity, state placement, writer policy,
retention, corruption handling, incomplete ancestry, and payload size.

## Current Reality
The draft contracts leave these policies open. The repository tree lives on a
cloud drive, while the existing renderer cache is machine-local. Without an
explicit boundary, durable control state could be mistaken for disposable
cache or silently differ across machines.

## Desired Reality
The contracts and README state that v1:

- assigns repository keys within one local ledger only;
- uses a single authorized writer machine;
- distinguishes authoritative state from disposable machine-local cache;
- warns where state and configuration live and whether they are machine-local;
- retains observed history indefinitely by default;
- treats ledger corruption as isolated loss of observation history, never as
  repository corruption or custody-chain failure;
- marks shallow/incomplete ancestry and returns unknown movement;
- keeps ID lists inline without silent truncation.

## Gap Analysis
These defaults are accepted but not yet normative or visible to an operator.

## Known Facts / Assumptions / Unknowns
- Fact: source repositories may sync through a cloud drive independently of
  vcs-tree state.
- Fact: v1 is not a custody-chain or audit-log system.
- Fact: the current scanner cache defaults under `XDG_CACHE_HOME` or
  `~/.cache` and is disposable.
- Assumption: shared or multi-writer state is future policy work.

## Transformations
- Update both v1 contracts with the accepted defaults and invariants.
- Add an immediate README warning about current machine-local cache behavior.
- Update the parent task and workboard.
- Do not edit package source or tests.

## Allowed Write Surface
- `README.md`
- `docs/contracts/history-snapshot-v1.md`
- `docs/contracts/history-delta-v1.md`
- `tasks/open/260728-movement-snapshot-package.md`
- `tasks/open/260801-settle-v1-policy-defaults.md`
- `tasks/WORKBOARD.md`

## Out of Bounds
- Implementing state storage, locking, recovery, or warnings.
- Shared-writer or cross-machine identity design.
- Custody-chain, tamper-evidence, or audit guarantees.

## Acceptance Criteria
- Authoritative state is prohibited from evictable cache locations.
- Machine-local placement and the single-writer default are explicit.
- Corruption cannot authorize repository mutation or false deletion events.
- Shallow ancestry produces explicit unknown movement.
- Inline lists cannot be silently truncated.
- Current cache behavior is documented for the operator.

## Evidence
- `docs/contracts/history-snapshot-v1.md` defines machine-local authoritative
  state, single-writer enrollment, indefinite retention, explicit location
  reporting, corruption isolation, and v1 ancestry boundaries.
- `docs/contracts/history-delta-v1.md` requires unknown ancestry movement,
  inline complete ID lists, explicit limit failures, and suppression of claims
  dependent on corrupt state.
- `README.md` warns that the current renderer cache is machine-local and
  disposable, while the planned ledger and registry are authoritative state.
- Contract JSON examples parse successfully and Markdown long-line checks
  pass.

## Decisions
- Owner: Codex `/root`; claimed 2026-08-01.
- Repository keys are local-ledger identities; v1 makes no cross-machine clone
  identity claim.
- The current machine is the sole enrolled writer until policy changes.
- Authoritative state cannot live in `~/.cache`/`XDG_CACHE_HOME`; configuration
  may remain machine-local but must be reported.
- Retention is indefinite by default.
- Corruption is isolated observational-data loss, not source-repository loss
  or custody-chain failure.
- Shallow/incomplete ancestry yields unknown movement.
- V1 lists IDs inline and never silently truncates.

## Open Fronts
- Shared/multi-writer state, portable identity, optional deep history, and
  export framing remain future policy work.

## Next Actions
- Decompose the now-active parent into implementation tasks.
