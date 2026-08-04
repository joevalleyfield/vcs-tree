Filed as: 260803-define-backlog-review-pressure
FKA:
AKA: stale-time pressure, dormant project review, backlog resurfacing
Legacy index:

keywords: planning, active, backlog, staleness, review, cadence, disposition

Parent: `260728-movement-snapshot-package`
Depends on: `260802-recurring-movement-pulse`
Blocks:
Blocked by:
Related: `260803-center-pulse-on-jj-change-graphs`; `260804-history-observability-and-index`

# Define Backlog Review Pressure

Define a second recurring vcs-tree instrument that surfaces repositories whose
elapsed time and unresolved evidence warrant a conscious review. Pulse answers
“what moved?”; backlog answers “what has waited long enough that we should
explicitly renew, defer, or retire our attention?”

## Current Reality

- The scanner distinguishes a real last-commit date, jj null root `00000000`,
  and repository-read errors.
- The retained history ledger records observation time, repository continuity,
  working-copy state, logical jj change graphs, descriptions, task paths, and
  movement across generations.
- Pulse reports factual movement without deciding whether it constitutes
  progress or priority.
- No durable surface records when a repository was consciously reviewed, why it
  was allowed to remain dormant, or when that decision should return for review.
- Raw inactivity alone cannot distinguish a finished archive, a deliberately
  parked project, an abandoned dirty working copy, and a newly initialized
  repository that never received its first commit.

## Desired Reality

Settle a versioned backlog-review contract, tentatively exposed through a
command such as:

```text
vcs-tree history backlog PATH
```

The operation should produce an opinionated, evidence-backed, pressure-ranked
handoff for a coordinating agent, notes keeper, or other downstream role. A
separate explicit action records the operator's disposition. The package may
strongly recommend review from deterministic evidence; it must not silently
write into a repository or disguise inactivity as a factual health judgment.

## Review-Pressure Model

Pressure combines elapsed time with the kind and immediacy of unresolved
evidence. It need not begin gently: some first observations are already ripe for
action. Every pressure result names the factual or intentional boundary and the
evidence that selected it. Candidate inputs include:

- last observed repository movement and last real commit/change timestamps;
- dirty, conflicted, or unknown working-copy state;
- visible unnamed jj changes and change stacks that have not moved;
- open-task paths and their last observed path/content movement;
- first observation of an initialized repository with no real commit;
- prior conscious review/disposition and its next-review date or condition; and
- movement after a repository was marked dormant.

The contract must distinguish native author/committer timestamps from observer
time. A null-root repository has no last-commit date. If it contains substantive
vision or implementation evidence, first observation immediately emits a
high-pressure `initial_commit_due` reason: the work already exists in the real
world but lacks its first durable VCS boundary. A metadata-only empty root emits
the gentler `initialized_empty` intent signal. Any continuing age clock starts
from first observation or an explicit intent/review record and is labeled
accordingly.

## Opinionated Surfacing and Handoff

Backlog is allowed to rank, filter, and strongly surface evidence. Settle a
small stable pressure vocabulary and reason codes that downstream roles can act
on without reparsing prose. At minimum, the model must support:

- immediate review pressure for ripe, unresolved work;
- due review pressure accumulated over time;
- latent/watch pressure that remains visible without dominating the queue;
- intentionally deferred pressure with its next boundary; and
- suppressed/archive state that can still be awakened by explicit triggers.

Each entry should include `why_now`, supporting observations, the active clock,
prior disposition, and a suggested handling class such as coordinate, record,
review, or leave dormant. Suggested handling is routing input, not an assignment
or permission to mutate the repository.

The contract must define deterministic, conservative evidence for substantive
null-root content. Investigate at least:

- vision artifacts such as README, AGENTS, planning, docs, or task files;
- implementation and test files;
- meaningful working-copy additions reported by Git or jj;
- generated, vendored, cache, environment, and metadata-only files that should
  not create false initial-commit pressure; and
- partial/unreadable inventories, which remain uncertain rather than empty.

## Conscious Dispositions

Investigate a small factual vocabulary capable of expressing at least:

- bring forward for active consideration;
- intentionally defer until a date or named condition;
- leave dormant with a widening review interval;
- watch for movement or an external wake signal; and
- archive or suppress routine review without erasing history.

A disposition is user/agent-authored evidence, not a conclusion calculated by
vcs-tree. Every record needs a timestamp, reason, actor/writer identity, and the
repository continuity key it applies to. Determine whether this intentional
state belongs in machine-local history state, portable configuration, or an
explicit exportable sidecar; do not silently write into scanned repositories.

## Cadence and Resurfacing

Repeated intentional deferral should permit review intervals to widen so a
stable dormant corpus does not dominate every run. The contract must settle:

- whether widening uses fixed bands, bounded backoff, or explicit dates;
- the maximum interval before an otherwise dormant item is reconsidered;
- which factual events reset or shorten the interval;
- how repository movement after dormancy resurfaces immediately; and
- how a host records an external “the world changed” wake signal that vcs-tree
  cannot infer from version-control evidence.

The algorithm must remain explainable: each candidate reports why it is present,
which clock is running, the prior disposition, and what made it due now.

## Investigations

- Inventory which required clocks and evidence already survive retained
  snapshots and which need an additive observation or review record.
- Compare central machine-local, portable sidecar, and repository-local storage
  for intentional dispositions, including continuity across moves and machines.
- Define pressure independently for clean/inactive, dirty/inactive,
  conflicted, null-root, open-task, unnamed-change, unreadable, and archived
  repositories.
- Establish deterministic vision/implementation evidence and exclusions for
  immediate null-root `initial_commit_due` pressure.
- Determine whether task/change-stack pressure is summarized under a repository
  or emitted as independently reviewable items.
- Define how missing scans, partial evidence, clock skew, rewrites, and imported
  old history affect age claims.
- Establish concise summary, audit, and JSON examples plus exit behavior.

## Acceptance Criteria

- A planning artifact fixes the v1 evidence model, disposition vocabulary,
  pressure vocabulary/reasons, downstream handoff, storage boundary,
  cadence/backoff rules, resurfacing triggers, output modes, and exit behavior.
- The contract explicitly permits evidence-backed opinionated ranking while
  separating calculated review pressure from conscious priority/health
  decisions and repository mutation authority.
- Examples cover clean finished work, stale dirty work, an unnamed jj stack,
  an open task, a null-root repository, a partial/error repository, intentional
  dormancy, repeated deferral, movement after dormancy, and an external wake.
- Null-root fixtures distinguish VCS-metadata-only, vision-only,
  implementation-bearing, generated-only, and partially unreadable trees.
  Vision or implementation produces immediate `initial_commit_due` pressure on
  first observation; metadata-only initialization does not.
- A real `/Users/tim/Documents` trial groups the 68-repository corpus without
  treating Archive contents or every old clean repository as equally actionable.
- Repeated runs without new evidence are stable and do not manufacture newly
  urgent items or reset review clocks.
- Pulse and backlog share retained observations but remain distinct operator
  questions and separately consumable outputs.
- Follow-on implementation tasks name bounded write surfaces, fixtures, and
  completion evidence only after the contract is settled.
- No production source, tests, retained ledger, live resource command, or
  repository disposition changes while this parent remains in planning.

## Allowed Write Surfaces

- `planning/`
- `docs/contracts/`
- this task file and `tasks/WORKBOARD.md`

## Completion Evidence

- Decision tables identify the clock, evidence requirements, supported claims,
  opinionated pressure/reason, downstream handling class, and uncertainty
  behavior for each review-pressure class.
- Worked examples show interval widening and every immediate resurfacing trigger.
- The task closes only after dispatching independently claimable implementation
  work grounded in the real corpus trial.

## Next Action

Draft `planning/backlog-review-v1.md` from retained snapshots and a sampled
cross-section of active, dormant, archived, dirty, null-root, and unreadable
repositories before choosing thresholds or a persistence mechanism.
