import copy

import pytest

import vcs_tree.snapshot_schema as schema_module
from vcs_tree.models import (
    V2_REPOSITORY_COMPONENTS,
    CollectionError,
    CollectionState,
    ContractError,
    HistoryStore,
    ObservationOutcome,
    SnapshotEnvelope,
    SnapshotEnvelopeV2,
    dumps,
    loads,
)
from vcs_tree.snapshot_schema import component_comparison, normalize_snapshot, parse_snapshot

CAPTURED = "2026-08-04T12:00:00Z"
ERROR_DICT = CollectionError("command", "working-copy", "failed").to_dict()


def outcome(state="complete", *, attempted_at=CAPTURED, errors=()):
    value = {"state": state, "errors": list(errors)}
    if attempted_at is not None:
        value["attempted_at"] = attempted_at
    return value


def repository_v2(mode="git", *, refresh="performed", freshness="current"):
    refresh_value = {"state": refresh, "errors": []}
    if refresh != "not_applicable":
        refresh_value["attempted_at"] = CAPTURED
    if refresh == "failed":
        refresh_value["errors"] = [
            CollectionError("permission", "jj.refresh", "read only").to_dict()
        ]
    return {
        "repository_key": f"repo-{mode}",
        "mode": mode,
        "collection": {name: outcome() for name in V2_REPOSITORY_COMPONENTS},
        "workspaces": [
            {
                "workspace_key": "default",
                "working_copy": {
                    "outcome": outcome(),
                    "recorded_state": "dirty",
                    "refresh": refresh_value,
                    "freshness": freshness,
                    "entries_outcome": outcome(),
                    "entries_limit": 2,
                    "entries_truncated": False,
                    "entries": [{"status": "modified", "path": "README.md"}],
                },
            }
        ],
        "presentation": {"native": mode},
    }


def snapshot_v2(mode="git", **repository_options):
    return SnapshotEnvelopeV2(
        "snapshot-v2",
        CAPTURED,
        {"name": "vcs-tree", "version": "0.1.0"},
        HistoryStore("store", 2, writer_id="writer"),
        {"root": "/workspace"},
        (repository_v2(mode, **repository_options),),
    )


def snapshot_v1(mode="git"):
    graph_error = CollectionError("command", "jj.log", "failed").to_dict()
    repository = {
        "repository_key": f"repo-{mode}",
        "mode": mode,
        "collection": {
            "identity": {"state": "complete", "errors": []},
            "workspaces": {"state": "complete", "errors": []},
            "refs": {"state": "complete", "errors": []},
            "history": {"state": "complete", "errors": []},
        },
        "workspaces": [
            {
                "workspace_key": "default",
                "working_copy": {
                    "state": "dirty",
                    "entries_outcome": {"state": "complete", "errors": []},
                    "entries": [{"status": "modified", "path": "README.md"}],
                },
            }
        ],
        "refs": [{"name": "refs/heads/main"}],
        "publication_hints": {"outcomes": {"jj_bookmarks": {"state": "complete", "errors": []}}},
        "change_graph": {
            "visible_heads": [],
            "outcome": {"state": "error", "errors": [graph_error]},
        },
    }
    return SnapshotEnvelope(
        "snapshot-v1",
        CAPTURED,
        {"name": "vcs-tree", "version": "0.1.0"},
        HistoryStore("store", 1, writer_id="writer"),
        {"root": "/workspace"},
        (repository,),
    )


@pytest.mark.parametrize("mode", ["git", "jj", "colocated"])
def test_v2_round_trip_preserves_validated_native_presentation(mode):
    document = snapshot_v2(mode)
    assert SnapshotEnvelopeV2.from_dict(document.to_dict()) == document
    assert parse_snapshot(document.to_dict()) == document
    assert loads(dumps(document), kind="snapshot") == document
    assert dumps(document) == dumps(document)
    assert document.to_dict()["repositories"][0]["presentation"] == {"native": mode}


def test_refresh_failure_and_not_applicable_workspace_shapes_are_valid():
    failed = snapshot_v2("jj", refresh="failed", freshness="recorded_maybe_stale")
    assert failed.repositories[0]["workspaces"][0]["working_copy"]["freshness"] == (
        "recorded_maybe_stale"
    )
    not_applicable = snapshot_v2("git", refresh="not_applicable", freshness="current")
    assert SnapshotEnvelopeV2.from_dict(not_applicable.to_dict()) == not_applicable


def test_v1_normalization_is_coarse_conservative_and_preserves_facts():
    normalized = normalize_snapshot(snapshot_v1("colocated"))
    repository = normalized["repositories"][0]
    assert normalized["source_schema_version"] == 1
    assert repository["components"]["git_history"]["state"] == "complete"
    assert repository["components"]["git_history"]["attempted_at"] == CAPTURED
    assert repository["components"]["git_history"]["time_precision"] == "snapshot"
    assert repository["components"]["jj_history"]["state"] == "error"
    assert repository["components"]["git_worktrees"]["state"] == "unknown"
    assert repository["components"]["path_evidence"]["state"] == "not_requested"
    assert repository["workspaces"][0]["recorded_state"] == "dirty"
    assert repository["workspaces"][0]["refresh"]["state"] == "unknown"
    assert repository["facts"]["refs"] == [{"name": "refs/heads/main"}]


@pytest.mark.parametrize(
    ("mode", "component", "state"),
    [
        ("git", "git_worktrees", "complete"),
        ("git", "jj_workspaces", "not_requested"),
        ("git", "jj_bookmarks", "not_requested"),
        ("git", "jj_visible_heads", "not_requested"),
        ("git", "jj_history", "not_requested"),
        ("jj", "git_worktrees", "not_requested"),
        ("jj", "git_refs", "not_requested"),
        ("jj", "git_history", "not_requested"),
        ("jj", "jj_workspaces", "complete"),
        ("jj", "jj_bookmarks", "complete"),
        ("jj", "jj_visible_heads", "error"),
    ],
)
def test_v1_mode_specific_normalization(mode, component, state):
    repository = normalize_snapshot(snapshot_v1(mode))["repositories"][0]
    assert repository["components"][component]["state"] == state


def test_v1_missing_and_malformed_optional_facts_stay_unknown():
    document = snapshot_v1("jj").to_dict()
    repository = document["repositories"][0]
    repository["collection"] = []
    repository["workspaces"] = [
        {"path": "/work", "working_copy": {"state": "surprising", "entries": []}},
        "ignored",
    ]
    repository["publication_hints"] = []
    repository["change_graph"] = []
    repository["collection"] = {"identity": {"state": "not_requested", "errors": []}}
    normalized = normalize_snapshot(document)["repositories"][0]
    assert normalized["components"]["identity"]["state"] == "not_requested"
    assert "attempted_at" not in normalized["components"]["identity"]
    assert normalized["components"]["jj_bookmarks"]["state"] == "unknown"
    assert normalized["components"]["jj_history"]["state"] == "unknown"
    assert normalized["workspaces"][0]["workspace_key"] == "/work"
    assert normalized["workspaces"][0]["recorded_state"] == "unknown"
    assert normalized["workspaces"][0]["entries_outcome"]["state"] == "unknown"


def test_v2_normalization_and_cross_version_comparison_boundaries():
    before = normalize_snapshot(snapshot_v1("git"))["repositories"][0]
    after = normalize_snapshot(snapshot_v2("git"))["repositories"][0]
    assert after["components"]["git_refs"]["time_precision"] == "component"
    assert component_comparison(before, after, "git_refs")["state"] == "complete"
    incomplete = component_comparison(before, after, "path_evidence")
    assert incomplete == {
        "state": "comparison_incomplete",
        "before_state": "not_requested",
        "after_state": "complete",
    }
    with pytest.raises(ContractError):
        component_comparison(before, after, "made_up")
    with pytest.raises(ContractError):
        schema_module._v1_component({}, "made_up", CAPTURED)

    not_requested = snapshot_v2("git").to_dict()
    not_requested["repositories"][0]["collection"]["path_evidence"] = outcome(
        "not_requested", attempted_at=None
    )
    normalized = normalize_snapshot(not_requested)["repositories"][0]
    assert normalized["components"]["path_evidence"]["time_precision"] == "unknown"


def test_parse_snapshot_rejects_wrong_schema_and_versions():
    with pytest.raises(ContractError):
        parse_snapshot([])
    with pytest.raises(ContractError):
        parse_snapshot({"schema": "wrong", "schema_version": 1})
    with pytest.raises(ContractError):
        parse_snapshot({"schema": SnapshotEnvelope.schema, "schema_version": 9})


@pytest.mark.parametrize(
    "mutate",
    [
        lambda repo: repo.pop("repository_key"),
        lambda repo: repo.update(mode="unknown"),
        lambda repo: repo.update(collection=[]),
        lambda repo: repo["collection"].pop("identity"),
        lambda repo: repo.update(workspaces={}),
        lambda repo: repo["workspaces"][0].pop("workspace_key"),
        lambda repo: repo["workspaces"][0].pop("working_copy"),
        lambda repo: repo["workspaces"][0]["working_copy"].update(recorded_state="bad"),
        lambda repo: repo["workspaces"][0]["working_copy"].update(freshness="bad"),
        lambda repo: repo["workspaces"][0]["working_copy"].update(entries_limit=-1),
        lambda repo: repo["workspaces"][0]["working_copy"].update(entries_limit=True),
        lambda repo: repo["workspaces"][0]["working_copy"].update(entries_truncated=1),
        lambda repo: repo["workspaces"][0]["working_copy"].update(entries_limit=0),
        lambda repo: repo["workspaces"][0]["working_copy"]["entries"][0].update(status="bad"),
        lambda repo: repo["workspaces"][0]["working_copy"]["entries"][0].pop("path"),
        lambda repo: repo["workspaces"][0]["working_copy"]["entries"][0].update(old_path=""),
    ],
)
def test_v2_repository_validation_rejects_malformed_shapes(mutate):
    repository = repository_v2()
    mutate(repository)
    with pytest.raises(ContractError):
        snapshot_v2_from(repository)


def snapshot_v2_from(repository):
    return SnapshotEnvelopeV2(
        "snapshot-v2",
        CAPTURED,
        {},
        HistoryStore("store", 2, writer_id="writer"),
        {},
        (repository,),
    )


@pytest.mark.parametrize(
    ("refresh", "freshness", "change"),
    [
        ("performed", "unknown", None),
        ("failed", "current", None),
        ("failed", "unknown", {"errors": []}),
        ("skipped", "current", None),
        ("not_applicable", "unknown", None),
        ("performed", "current", {"errors": [ERROR_DICT]}),
        ("not_applicable", "current", {"attempted_at": CAPTURED}),
        ("not_applicable", "current", {"errors": [ERROR_DICT]}),
        ("skipped", "unknown", {"errors": [ERROR_DICT]}),
        ("skipped", "unknown", {"attempted_at": None}),
    ],
)
def test_v2_refresh_validation_rejects_contradictions(refresh, freshness, change):
    repository = repository_v2(refresh=refresh, freshness=freshness)
    value = repository["workspaces"][0]["working_copy"]["refresh"]
    if change:
        value.update(change)
    with pytest.raises(ContractError):
        snapshot_v2_from(repository)


def test_v2_not_requested_entries_are_empty_and_untruncated():
    repository = repository_v2()
    working_copy = repository["workspaces"][0]["working_copy"]
    working_copy["entries_outcome"] = outcome("not_requested", attempted_at=None)
    with pytest.raises(ContractError):
        snapshot_v2_from(repository)
    working_copy["entries"] = []
    working_copy["entries_truncated"] = True
    with pytest.raises(ContractError):
        snapshot_v2_from(repository)
    working_copy["entries_truncated"] = False
    assert snapshot_v2_from(repository)


def test_observation_outcome_guards_and_round_trip():
    error = CollectionError("command", "git.refs", "failed")
    partial = ObservationOutcome(CollectionState.PARTIAL, CAPTURED, (error,))
    assert ObservationOutcome.from_dict(partial.to_dict()) == partial
    with pytest.raises(ContractError):
        ObservationOutcome(CollectionState.COMPLETE, CAPTURED, (error,))
    with pytest.raises(ContractError):
        ObservationOutcome(CollectionState.ERROR)
    with pytest.raises(ContractError):
        ObservationOutcome(CollectionState.ERROR, CAPTURED)
    with pytest.raises(ContractError):
        ObservationOutcome(CollectionState.NOT_REQUESTED, CAPTURED)
    with pytest.raises(ContractError):
        ObservationOutcome(CollectionState.NOT_REQUESTED, errors=(error,))
    assert ObservationOutcome(CollectionState.NOT_REQUESTED).to_dict() == {
        "state": "not_requested",
        "errors": [],
    }
    malformed = partial.to_dict()
    malformed["attempted_at"] = "bad"
    with pytest.raises(ContractError):
        ObservationOutcome.from_dict(malformed)


def test_v2_does_not_mutate_source_mapping_during_round_trip():
    repository = repository_v2()
    original = copy.deepcopy(repository)
    snapshot_v2_from(repository).to_dict()
    assert repository == original
