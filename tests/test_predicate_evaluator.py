import copy
import json
from pathlib import Path

import pytest

from vcs_tree.models import ContractError
from vcs_tree.predicate_evaluator import PredicateEvaluator
from vcs_tree.predicate_models import HistoryQuery

EVALUATED_AT = "2026-08-04T14:00:00Z"


def clock(at="2026-08-04T13:00:00Z"):
    return {"state": "observed", "at": at, "time_precision": "component", "snapshot_id": "s4"}


def component(repository, name, outcome="complete", *, complete=True, freshness=None):
    value = {
        "component_key": f"{repository}:{name}",
        "repository_key": repository,
        "component": name,
        "last_attempted_at": clock(),
        "complete_as_of": clock() if complete else {"state": "never_observed"},
        "last_outcome": outcome,
        "errors": [],
    }
    if freshness is not None:
        value["freshness"] = freshness
    return value


def interval(first, confirmed, invalidated=None, episode=1):
    evidence = {
        "snapshot_id": f"s{episode}",
        "component": "git_refs",
        "outcome": "complete",
        "observed_at": confirmed,
        "time_precision": "component",
    }
    return {
        "episode": episode,
        "prior_boundary": {
            "state": "never_observed" if episode == 1 else "tombstone",
            "origin": "negative_infinity" if episode == 1 else first,
        },
        "first_observed_at": first,
        "last_confirmed_at": confirmed,
        "invalidated_at": invalidated,
        "opened_by": evidence,
        "last_confirmed_by": evidence,
        "invalidated_by": evidence if invalidated else None,
    }


def fact_record(
    repository,
    key,
    attributes,
    intervals,
    component_name="git_refs",
    *,
    fact_type="git-ref-exists",
    authorized=True,
):
    return {
        "fact_key": key,
        "slot_key": key,
        "fact_type": fact_type,
        "repository_key": repository,
        "component": component_name,
        "component_key": f"{repository}:{component_name}",
        "attributes": attributes,
        "absence_authorized": authorized,
        "intervals": intervals,
    }


@pytest.fixture
def index():
    main = fact_record(
        "repo-a",
        "git-ref-exists:repo-a:main",
        {"name": "main", "metadata": {"authority": "local"}},
        [
            interval("2026-08-04T10:00:00Z", "2026-08-04T10:30:00Z", "2026-08-04T11:00:00Z"),
            interval("2026-08-04T12:00:00Z", "2026-08-04T13:00:00Z", episode=2),
        ],
    )
    side = fact_record(
        "repo-a",
        "git-ref-exists:repo-a:side",
        {"name": "side"},
        [interval("2026-08-04T09:00:00Z", "2026-08-04T09:30:00Z", "2026-08-04T11:30:00Z")],
    )
    return {
        "schema": "vcs-tree.temporal-facts",
        "schema_version": 1,
        "store_id": "store",
        "source_generation": 4,
        "source_snapshots": [
            {"snapshot_id": "s1", "generation": 1, "schema_version": 2},
            {"snapshot_id": "s4", "generation": 4, "schema_version": 2},
        ],
        "components": [
            {
                **component("ignored", "repository_identity"),
                "component_key": "scan:%2Fscope:repository_identity",
                "repository_key": None,
            },
            component("repo-c", "git_refs", "partial", complete=False),
            component("repo-a", "working_copy/repo-a:default", freshness="recorded_maybe_stale"),
            component("repo-a", "path_evidence/repo-a:default"),
            component("repo-b", "git_refs"),
            component("repo-a", "git_refs"),
            component("repo-a", "jj_history", "error", complete=False),
        ],
        "facts": [
            side,
            main,
            fact_record(
                "repo-a",
                "git-ref-exists:repo-a:fresh",
                {"name": "fresh", "labels": ["one"]},
                [interval("2026-08-04T13:30:00Z", "2026-08-04T13:30:00Z")],
            ),
            fact_record("repo-a", "git-ref-exists:repo-a:ghost", {"name": "ghost"}, []),
        ],
        "continuity_boundaries": [],
    }


def query(where, repositories=("repo-a",)):
    return HistoryQuery.from_dict(
        {
            "schema": "vcs-tree.history-query",
            "schema_version": 1,
            "scope": {"repository_keys": list(repositories)},
            "where": where,
        }
    )


def fact(state="active", name="main", *, fact_type="git-ref-exists", attributes=None):
    return {
        "fact": {
            "type": fact_type,
            "attributes": attributes if attributes is not None else {"name": name},
            "state": state,
        }
    }


def elapsed(clock_name="last_confirmed", relation="gte", seconds=0, name="main"):
    return {
        "elapsed": {
            "fact": {"type": "git-ref-exists", "attributes": {"name": name}},
            "clock": clock_name,
            "relation": relation,
            "seconds": seconds,
        }
    }


def component_predicate(name="git_refs", field="outcome", relation="eq", value="complete"):
    return {"component": {"name": name, "field": field, "relation": relation, "value": value}}


def outcome(index, where, repository="repo-a"):
    result = PredicateEvaluator().evaluate(
        query(where, (repository,)), index, evaluated_at=EVALUATED_AT
    )
    return result["results"][0]


def test_fact_states_attributes_and_evidence(index):
    active = outcome(index, fact(attributes={"metadata": {"authority": "local"}}))
    inactive = outcome(index, fact("inactive", "side"))
    observed = outcome(index, fact("ever_observed", "side"))
    missing = outcome(index, fact(name="missing"))
    assert [active["outcome"], inactive["outcome"], observed["outcome"], missing["outcome"]] == [
        "true",
        "true",
        "true",
        "false",
    ]
    assert active["evidence"]["source_snapshots"] == ["s1", "s2"]
    assert active["evidence"]["completeness"][0]["complete_as_of"]["at"].endswith("13:00:00Z")
    assert active["evidence"]["continuity_boundaries"] == []
    assert outcome(index, fact("inactive", "main"))["outcome"] == "false"
    assert outcome(index, fact(attributes={"labels": ["one"]}))["outcome"] == "true"
    assert outcome(index, fact("ever_observed", "ghost"))["outcome"] == "false"
    working_copy = fact(
        fact_type="working-copy-state",
        attributes={"workspace_key": "repo-a:default", "state": "clean"},
    )
    assert outcome(index, working_copy)["outcome"] == "indeterminate"
    assert outcome(index, fact(fact_type="repository-exists", attributes={}))["outcome"] == "false"


def test_false_requires_complete_fresh_and_continuous_evidence(index):
    assert outcome(index, fact(name="missing"), "repo-c")["outcome"] == "indeterminate"
    assert outcome(index, fact(name="missing"), "repo-z")["outcome"] == "indeterminate"
    assert (
        outcome(
            index,
            fact(
                name="ignored",
                fact_type="native-object-exists",
                attributes={"object_id": {"algorithm": "sha1", "value": "dead"}},
            ),
        )["outcome"]
        == "indeterminate"
    )
    stale = fact(
        fact_type="working-copy-path",
        attributes={"workspace_key": "repo-a:default", "path": "unseen"},
    )
    stale_result = outcome(index, stale)
    assert stale_result["outcome"] == "indeterminate"
    assert len(stale_result["evidence"]["components"]) == 2
    no_workspace = fact(fact_type="working-copy-path", attributes={"path": "unseen"})
    assert outcome(index, no_workspace)["outcome"] == "indeterminate"

    broken = copy.deepcopy(index)
    broken["continuity_boundaries"] = [
        {
            "snapshot_id": "s4",
            "scope": "/scope",
            "path": "/scope/repo",
            "before_repository_key": "repo-a",
            "after_repository_key": "replacement",
        }
    ]
    result = outcome(broken, fact(name="missing"))
    assert result["outcome"] == "indeterminate"
    assert result["evidence"]["continuity_boundaries"][0]["after_repository_key"] == "replacement"


@pytest.mark.parametrize(
    "clock_name,seconds",
    [
        ("current_interval_started", 7200),
        ("last_confirmed", 3600),
        ("last_invalidated", 10800),
        ("last_transition", 7200),
    ],
)
def test_elapsed_observed_clocks(index, clock_name, seconds):
    result = outcome(index, elapsed(clock_name, "eq", seconds))
    assert result["outcome"] == "true"
    observation = result["evidence"]["clock"]["observations"][0]
    assert observation["origin"]["state"] == "observed"
    assert observation["elapsed"] == {"state": "finite", "seconds": seconds}


@pytest.mark.parametrize(
    "relation,expected",
    [
        ("lt", "false"),
        ("lte", "false"),
        ("eq", "false"),
        ("ne", "true"),
        ("gt", "true"),
        ("gte", "true"),
    ],
)
def test_never_observed_is_positive_infinity(index, relation, expected):
    result = outcome(index, elapsed("last_transition", relation, 60, "missing"), "repo-b")
    assert result["outcome"] == expected
    observation = result["evidence"]["clock"]["observations"][0]
    assert observation == {
        "origin": {"state": "never_observed", "value": "negative_infinity"},
        "elapsed": {"state": "positive_infinity"},
    }


def test_elapsed_indeterminate_partial_malformed_and_future(index):
    assert outcome(index, elapsed(name="missing"), "repo-c")["outcome"] == "indeterminate"
    malformed = copy.deepcopy(index)
    malformed["facts"][1]["intervals"][-1]["last_confirmed_at"] = "bad"
    result = outcome(malformed, elapsed())
    assert result["outcome"] == "indeterminate"
    assert result["evidence"]["clock"]["observations"][0]["origin"]["state"] == "unsupported"
    future = copy.deepcopy(index)
    future["facts"][1]["intervals"][-1]["last_confirmed_at"] = "2026-08-04T15:00:00Z"
    assert outcome(future, elapsed())["outcome"] == "indeterminate"
    assert outcome(index, elapsed(name="ghost"))["outcome"] == "true"
    assert outcome(index, elapsed("last_invalidated", name="fresh"))["outcome"] == "true"


def test_boolean_three_valued_truth_tables(index):
    true = component_predicate()
    false = component_predicate(value="partial")
    unknown = component_predicate("missing")
    cases = [
        ({"all": [true, true]}, "true"),
        ({"all": [true, unknown]}, "indeterminate"),
        ({"all": [unknown, false]}, "false"),
        ({"any": [false, false]}, "false"),
        ({"any": [false, unknown]}, "indeterminate"),
        ({"any": [unknown, true]}, "true"),
        ({"not": true}, "false"),
        ({"not": false}, "true"),
        ({"not": unknown}, "indeterminate"),
    ]
    for where, expected in cases:
        result = outcome(index, where)
        assert result["outcome"] == expected
        assert result["children"]


@pytest.mark.parametrize(
    "field,relation,value,expected",
    [
        ("outcome", "eq", "complete", "true"),
        ("outcome", "ne", "complete", "false"),
        ("freshness", "eq", "recorded_maybe_stale", "true"),
        ("complete_as_of", "lt", "2026-08-04T14:00:00Z", "true"),
        ("complete_as_of", "lte", "2026-08-04T13:00:00Z", "true"),
        ("complete_as_of", "gt", "2026-08-04T12:00:00Z", "true"),
        ("complete_as_of", "gte", "2026-08-04T13:00:00Z", "true"),
        ("complete_as_of", "eq", "2026-08-04T13:00:00Z", "true"),
        ("complete_as_of", "ne", "2026-08-04T12:00:00Z", "true"),
    ],
)
def test_component_fields_and_relations(index, field, relation, value, expected):
    name = "working_copy/repo-a:default" if field == "freshness" else "git_refs"
    assert outcome(index, component_predicate(name, field, relation, value))["outcome"] == expected


def test_component_missing_unobserved_and_bad_time_are_indeterminate(index):
    assert outcome(index, component_predicate("missing"))["outcome"] == "indeterminate"
    assert (
        outcome(index, component_predicate("jj_history", "complete_as_of", "eq", EVALUATED_AT))[
            "outcome"
        ]
        == "indeterminate"
    )
    malformed = copy.deepcopy(index)
    malformed["components"][-2]["complete_as_of"]["at"] = "bad"
    assert (
        outcome(malformed, component_predicate(field="complete_as_of", value=EVALUATED_AT))[
            "outcome"
        ]
        == "indeterminate"
    )
    assert (
        outcome(index, component_predicate(field="freshness", value="current"))["outcome"]
        == "indeterminate"
    )


def test_all_scope_order_determinism_and_input_immutability(index):
    query_document = {
        "schema": "vcs-tree.history-query",
        "schema_version": 1,
        "scope": {"all": True},
        "where": fact(),
    }
    original = copy.deepcopy(index)
    evaluator = PredicateEvaluator()
    first = evaluator.evaluate(query_document, index, evaluated_at=EVALUATED_AT)
    second = evaluator.evaluate(query_document, index, evaluated_at=EVALUATED_AT)
    assert [item["repository_key"] for item in first["results"]] == ["repo-a", "repo-b", "repo-c"]
    assert json.dumps(first, sort_keys=True, separators=(",", ":")) == json.dumps(
        second, sort_keys=True, separators=(",", ":")
    )
    assert index == original
    assert first["temporal_index"]["source_generation"] == 4


def test_never_observed_result_matches_golden_document(index):
    compact = {
        **index,
        "source_snapshots": [index["source_snapshots"][-1]],
        "components": [
            item for item in index["components"] if item.get("repository_key") == "repo-b"
        ],
        "facts": [],
    }
    document = query(elapsed("last_transition", "gte", 60, "missing"), ("repo-b",))
    result = PredicateEvaluator().evaluate(document, compact, evaluated_at=EVALUATED_AT)
    golden = json.loads(
        (Path(__file__).parent / "fixtures" / "predicate-result-v1.json").read_text()
    )
    assert result == golden


def test_git_unborn_and_jj_root_parent_evidence_stays_mechanical(index):
    observed = [interval("2026-08-04T13:00:00Z", "2026-08-04T13:00:00Z")]
    factual = copy.deepcopy(index)
    factual["components"].extend(
        [
            component("git-unborn", "git_worktrees"),
            component("git-unborn", "working_copy/git-unborn:default", freshness="current"),
            component("jj-root", "jj_workspaces"),
            component("jj-root", "jj_history"),
        ]
    )
    factual["facts"].extend(
        [
            fact_record(
                "git-unborn",
                "working-copy-state:git-unborn:dirty",
                {"workspace_key": "git-unborn:default", "state": "dirty"},
                observed,
                "working_copy/git-unborn:default",
                fact_type="working-copy-state",
            ),
            fact_record(
                "jj-root",
                "workspace-target:jj-root:default",
                {
                    "workspace_key": "jj-root:default",
                    "target": {"algorithm": "jj", "value": "working-copy-version"},
                    "change_id": "working-copy-change",
                },
                observed,
                "jj_workspaces",
                fact_type="workspace-target",
            ),
            fact_record(
                "jj-root",
                "jj-change-parent:jj-root:root",
                {
                    "change_id": "working-copy-change",
                    "version": {"algorithm": "jj", "value": "working-copy-version"},
                    "parent_change_id": None,
                    "parent_object_id": {"algorithm": "jj", "value": "00000000"},
                },
                observed,
                "jj_history",
                fact_type="jj-change-parent",
            ),
        ]
    )
    git_query = {
        "all": [
            fact(
                fact_type="working-copy-state",
                attributes={"workspace_key": "git-unborn:default", "state": "dirty"},
            ),
            fact("ever_observed", fact_type="workspace-target", attributes={}),
        ]
    }
    git_result = outcome(factual, git_query, "git-unborn")
    assert git_result["outcome"] == "false"

    jj_query = {
        "all": [
            fact(fact_type="workspace-target", attributes={"change_id": "working-copy-change"}),
            fact(
                fact_type="jj-change-parent",
                attributes={"parent_object_id": {"algorithm": "jj", "value": "00000000"}},
            ),
        ]
    }
    jj_result = outcome(factual, jj_query, "jj-root")
    assert jj_result["outcome"] == "true"
    rendered = json.dumps([git_result, jj_result], sort_keys=True)
    assert not any(
        word in rendered for word in ("urgency", "health", "priority", "initial_commit_due")
    )


@pytest.mark.parametrize(
    "bad,match",
    [
        (None, "must be an object"),
        ({}, "schema"),
        (
            {
                "schema": "vcs-tree.temporal-facts",
                "schema_version": 2,
                "facts": [],
                "components": [],
            },
            "version",
        ),
        (
            {
                "schema": "vcs-tree.temporal-facts",
                "schema_version": 1,
                "facts": {},
                "components": [],
            },
            "must be arrays",
        ),
    ],
)
def test_invalid_temporal_indexes_are_rejected(index, bad, match):
    with pytest.raises(ContractError, match=match):
        PredicateEvaluator().evaluate(query(fact()), bad, evaluated_at=EVALUATED_AT)


@pytest.mark.parametrize("evaluated_at", [None, "bad", "2026-08-04T14:00:00"])
def test_evaluation_time_must_be_zoned(index, evaluated_at):
    with pytest.raises(ContractError, match="evaluated_at"):
        PredicateEvaluator().evaluate(query(fact()), index, evaluated_at=evaluated_at)
