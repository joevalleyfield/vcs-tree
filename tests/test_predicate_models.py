import pytest

from vcs_tree.models import ContractError
from vcs_tree.predicate_models import FactSelector, HistoryQuery


def query(where, scope=None):
    return {
        "schema": "vcs-tree.history-query",
        "schema_version": 1,
        "scope": scope or {"repository_keys": ["repo-b", "repo-a"]},
        "where": where,
    }


def fact(state="active"):
    return {"fact": {"type": "git-ref-exists", "attributes": {"name": "main"}, "state": state}}


def elapsed(seconds=60):
    return {
        "elapsed": {
            "fact": {"type": "git-ref-exists", "attributes": {"name": "main"}},
            "clock": "last_confirmed",
            "relation": "gte",
            "seconds": seconds,
        }
    }


def component(field="outcome", relation="eq", value="complete"):
    return {
        "component": {
            "name": "git_refs",
            "field": field,
            "relation": relation,
            "value": value,
        }
    }


def test_query_round_trip_canonicalizes_scope_and_every_node():
    where = {
        "all": [
            fact(),
            elapsed(),
            component(),
            {"any": [fact("inactive"), {"not": fact("ever_observed")}]},
        ]
    }
    document = HistoryQuery.from_dict(query(where))
    assert document.repository_keys == ("repo-a", "repo-b")
    assert HistoryQuery.from_dict(document.to_dict()) == document
    assert HistoryQuery.from_dict(query(fact(), {"all": True})).repository_keys is None
    assert FactSelector.from_dict(
        {"type": "working-copy-path", "attributes": {"path": "x", "nested": [1]}}
    ).to_dict() == {
        "type": "working-copy-path",
        "attributes": {"nested": [1], "path": "x"},
    }


@pytest.mark.parametrize(
    "document,match",
    [
        (None, "query must be an object"),
        ({}, "missing required field"),
        ({**query(fact()), "extra": True}, "unknown field"),
        ({**query(fact()), "schema": "other"}, "unsupported query schema"),
        ({**query(fact()), "schema_version": 2}, "unsupported query schema version"),
        ({**query(fact()), "schema_version": True}, "unsupported query schema version"),
        (query(fact(), {"all": False}), "scope.all must be true"),
        (query(fact(), {"repository_keys": []}), "non-empty array"),
        (query(fact(), {"repository_keys": [""]}), "entries must be"),
        (query(fact(), {"repository_keys": ["a", "a"]}), "duplicates"),
        (query(fact(), {"all": True, "repository_keys": ["a"]}), "exactly all or"),
        (query({}), "exactly one predicate"),
        (query({"all": []}), "non-empty array"),
        (query({"any": "bad"}), "non-empty array"),
        (query({"unknown": {}}), "unsupported predicate operator"),
        (query({"fact": {"type": "unknown", "attributes": {}, "state": "active"}}), "invalid"),
        (
            query({"fact": {"type": "git-ref-exists", "attributes": [], "state": "active"}}),
            "must be an object",
        ),
        (
            query({"fact": {"type": "git-ref-exists", "attributes": {}, "state": "maybe"}}),
            "invalid",
        ),
        (
            query(
                {"fact": {"type": "git-ref-exists", "attributes": {}, "state": "active", "x": 1}}
            ),
            "unknown field",
        ),
        (query(elapsed(-1)), "finite non-negative"),
        (query(elapsed(True)), "finite non-negative"),
        (query(elapsed(float("inf"))), "finite non-negative"),
        (query({"elapsed": {**elapsed()["elapsed"], "clock": "bad"}}), "invalid"),
        (query({"elapsed": {**elapsed()["elapsed"], "relation": "bad"}}), "invalid"),
        (query(component("outcome", "gte")), "only supports"),
        (query(component("freshness", "lt", "current")), "only supports"),
        (query(component("bad")), "invalid"),
        (query(component(value="")), "non-empty string"),
        (query(component("complete_as_of", "eq", "bad")), "RFC 3339"),
        (query(component("complete_as_of", "eq", "2026-08-04T10:00:00")), "timezone"),
        (query({"component": {**component()["component"], "name": ""}}), "non-empty string"),
    ],
)
def test_malformed_query_documents_are_rejected(document, match):
    with pytest.raises(ContractError, match=match):
        HistoryQuery.from_dict(document)


def test_selector_rejects_missing_extra_and_non_json_attributes():
    with pytest.raises(ContractError, match="missing required"):
        FactSelector.from_dict({"type": "git-ref-exists"})
    with pytest.raises(ContractError, match="unknown field"):
        FactSelector.from_dict({"type": "git-ref-exists", "attributes": {}, "x": 1})
    with pytest.raises(ContractError, match="JSON values"):
        FactSelector.from_dict({"type": "git-ref-exists", "attributes": {"x": {1}}})
    with pytest.raises(ContractError, match="JSON values"):
        FactSelector.from_dict({"type": "git-ref-exists", "attributes": {"x": float("nan")}})
