# History Query Contract v1

Status: implemented

This contract defines the mechanical query boundary over a
`vcs-tree.temporal-facts` version 1 index. It reports factual repository
evidence. It does not decide whether a repository needs review or encode
urgency, priority, health, dormancy, or an initial-commit conclusion.

## Query envelope

The canonical input is one JSON object:

```json
{
  "schema": "vcs-tree.history-query",
  "schema_version": 1,
  "scope": {"repository_keys": ["repository-key"]},
  "where": {
    "fact": {
      "type": "git-ref-exists",
      "attributes": {"name": "refs/heads/main"},
      "state": "active"
    }
  }
}
```

`scope` contains exactly one of:

- `{"all": true}`, selecting every repository key represented by an indexed
  fact or component; or
- `{"repository_keys": [...]}`, a non-empty, duplicate-free list. Explicit
  keys need not already be represented, allowing an indeterminate result for
  unobserved repositories.

Exactly one `where` predicate is required. Objects reject unknown fields. The
model canonicalizes explicit repository keys into lexical order.

## Predicates

Each predicate object contains exactly one operator.

### Boolean operators

- `{"all": [predicate, ...]}` and `{"any": [predicate, ...]}` require at
  least one child.
- `{"not": predicate}` requires one child.

The evaluator uses Kleene-style three-valued logic:

| Inputs | `all` | `any` |
| --- | --- | --- |
| any false | false | true only if another input is true; otherwise false or indeterminate |
| any true | false only if another input is false; otherwise true or indeterminate | true |
| indeterminate and no decisive input | indeterminate | indeterminate |

`not` exchanges true and false and preserves indeterminate.

### Fact leaf

```json
{
  "fact": {
    "type": "working-copy-state",
    "attributes": {"workspace_key": "repo:default", "state": "dirty"},
    "state": "ever_observed"
  }
}
```

`type` is one of the stable atomic fact types documented by the temporal-facts
contract. `attributes` is a recursive subset selector: every selected key and
value must be present, while unselected attributes do not constrain a match.
`state` is `active`, `inactive`, or `ever_observed`.

A matching positive observation is sufficient for true. A tombstone is
sufficient for an inactive match. False absence requires an applicable
component with a recorded complete boundary. Native object facts, partial or
unobserved components, stale/unknown working-copy freshness, and repository
identity continuity breaks cannot establish absence and therefore produce
indeterminate when no positive answer exists.

### Elapsed leaf

```json
{
  "elapsed": {
    "fact": {"type": "git-ref-exists", "attributes": {"name": "refs/heads/main"}},
    "clock": "last_confirmed",
    "relation": "gte",
    "seconds": 86400
  }
}
```

Clocks are `current_interval_started`, `last_confirmed`, `last_invalidated`,
and `last_transition`. Relations are `eq`, `ne`, `lt`, `lte`, `gt`, and `gte`.
Seconds must be a finite, non-negative JSON number. Elapsed time is evaluated
against the caller-supplied RFC 3339 `evaluated_at`; evaluation never reads the
process clock.

When complete component evidence proves that the selected fact has never been
observed, its origin is the explicit `negative_infinity` sentinel and elapsed
state is `positive_infinity`. It is not serialized as a numeric infinity.
Consequently, finite `gt`, `gte`, and `ne` comparisons are true, while `lt`,
`lte`, and `eq` are false. A clock that cannot be supported due to incomplete
evidence is indeterminate rather than never-observed.

For a represented fact, `current_interval_started` uses the latest episode's
first observation, `last_confirmed` its latest confirmation,
`last_invalidated` the most recent tombstone across episodes, and
`last_transition` the latest activation or invalidation. A transition kind
that has never occurred also retains the negative-infinity sentinel.

### Component leaf

```json
{
  "component": {
    "name": "working_copy/repo:default",
    "field": "freshness",
    "relation": "eq",
    "value": "current"
  }
}
```

Fields are `outcome`, `complete_as_of`, and `freshness`. Outcome and freshness
support `eq` and `ne`. `complete_as_of` supports every relation and compares
RFC 3339 instants. A missing component, never-observed completeness clock, or
unusable timestamp yields indeterminate.

## Result envelope

The evaluator returns `vcs-tree.history-query-result` version 1. It repeats the
canonical query and explicit evaluation time, identifies the source temporal
index generation and snapshots, and emits results in lexical repository-key
order. Each nested predicate node retains its canonical predicate and outcome.
Every leaf additionally carries:

- selected atomic fact records and their interval evidence;
- selected component records;
- contributing fact snapshot IDs;
- component `complete_as_of`, latest outcome, and freshness boundaries;
- applicable identity-continuity boundaries; and
- for elapsed leaves, the clock name, normalized evaluation instant, origin,
  and finite, positive-infinity, or indeterminate elapsed state.

Facts and components are emitted in stable key order. Repeating evaluation
with byte-identical inputs and the same `evaluated_at` produces the same JSON
data and does not mutate the query, temporal index, snapshots, or repositories.

The model/service API is exported as `HistoryQuery`, `PredicateNode`,
`FactSelector`, and `PredicateEvaluator`. Public command parsing and rendering
are specified separately.
