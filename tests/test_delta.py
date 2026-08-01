from vcs_tree.delta import HistoryDeltaCalculator
from vcs_tree.models import HistoryStore, SnapshotEnvelope


def snap(store, sid, generation, repo):
    return SnapshotEnvelope(
        sid,
        "2026-08-01T12:00:00Z",
        {"name": "test"},
        HistoryStore(store, generation, writer_id="writer"),
        {"outcome": {"state": "complete", "errors": []}},
        (repo,),
    )


def repo(
    refs=(),
    workspaces=(),
    history=(),
    *,
    ref_state="complete",
    workspace_state="complete",
    history_state="complete",
    boundary="complete",
):
    return {
        "repository_key": "repo-0001",
        "mode": "git",
        "refs": list(refs),
        "workspaces": list(workspaces),
        "history": list(history),
        "history_boundary": {"state": boundary, "boundary_objects": []},
        "collection": {
            "refs": {"state": ref_state, "errors": []},
            "workspaces": {"state": workspace_state, "errors": []},
            "history": {"state": history_state, "errors": []},
            "identity": {"state": "complete", "errors": []},
        },
    }


def test_ref_creation_and_fast_forward_are_deterministic():
    a = repo(
        refs=(
            {
                "name": "main",
                "authority": "local",
                "object_id": {"algorithm": "sha1", "value": "a"},
            },
        ),
        workspaces=({"workspace_key": "default", "head": {"algorithm": "sha1", "value": "a"}},),
        history=({"object_id": {"algorithm": "sha1", "value": "a"}, "parents": []},),
    )
    b = repo(
        refs=(
            {
                "name": "main",
                "authority": "local",
                "object_id": {"algorithm": "sha1", "value": "b"},
            },
            {
                "name": "side",
                "authority": "remote",
                "remote": "origin",
                "object_id": {"algorithm": "sha1", "value": "c"},
            },
        ),
        workspaces=({"workspace_key": "default", "head": {"algorithm": "sha1", "value": "a"}},),
        history=(
            {"object_id": {"algorithm": "sha1", "value": "a"}, "parents": []},
            {
                "object_id": {"algorithm": "sha1", "value": "b"},
                "parents": [{"algorithm": "sha1", "value": "a"}],
            },
            {
                "object_id": {"algorithm": "sha1", "value": "c"},
                "parents": [{"algorithm": "sha1", "value": "a"}],
            },
        ),
    )
    delta = HistoryDeltaCalculator(
        objects={"a": a["history"][0], "b": b["history"][1], "c": b["history"][2]},
        delta_id_factory=lambda: "d",
        clock=lambda: "2026-08-01T12:01:00Z",
    ).calculate(snap("s", "a", 1, a), snap("s", "b", 2, b))
    events = delta.repository_deltas[0]["events"]
    assert [event["event"] for event in events] == [
        "ref_created",
        "ref_target_changed",
        "history_first_observed",
        "off_current_history_observed",
    ]
    assert events[1]["details"]["movement"] == "fast_forward"
    assert delta.outcome.state.value == "complete"


def test_partial_refs_suppress_deletion_and_report_incomplete():
    a = repo(
        refs=(
            {
                "name": "main",
                "authority": "local",
                "object_id": {"algorithm": "sha1", "value": "a"},
            },
        )
    )
    b = repo(refs=(), ref_state="partial")
    delta = HistoryDeltaCalculator().calculate(snap("s", "a", 1, a), snap("s", "b", 2, b))
    events = delta.repository_deltas[0]["events"]
    assert [event["event"] for event in events] == ["comparison_incomplete"]
    assert delta.outcome.state.value == "partial"


def test_shallow_boundary_makes_movement_unknown_and_workspace_changes_reported():
    a = repo(
        refs=(
            {
                "name": "main",
                "authority": "local",
                "object_id": {"algorithm": "sha1", "value": "a"},
            },
        ),
        workspaces=({"workspace_key": "default", "head": {"algorithm": "sha1", "value": "a"}},),
        boundary="shallow",
    )
    b = repo(
        refs=(
            {
                "name": "main",
                "authority": "local",
                "object_id": {"algorithm": "sha1", "value": "b"},
            },
        ),
        workspaces=({"workspace_key": "default", "head": {"algorithm": "sha1", "value": "b"}},),
        boundary="shallow",
    )
    delta = HistoryDeltaCalculator(
        objects={
            "a": {"object_id": {"value": "a"}, "parents": []},
            "b": {"object_id": {"value": "b"}, "parents": [{"value": "a"}]},
        }
    ).calculate(snap("s", "a", 1, a), snap("s", "b", 2, b))
    events = delta.repository_deltas[0]["events"]
    assert events[0]["details"]["relation"] == "unknown"
    assert events[1]["details"]["movement"] == "unknown"


def test_store_mismatch_is_rejected():
    r = repo()
    try:
        HistoryDeltaCalculator().calculate(snap("a", "x", 1, r), snap("b", "y", 1, r))
    except ValueError as error:
        assert "same history store" in str(error)
    else:
        raise AssertionError("store mismatch should fail")


def test_workspace_ref_and_relation_variants():
    old = repo(
        refs=({"name": "gone", "authority": "local", "object_id": {"value": "a"}},),
        workspaces=(
            {"workspace_key": "old", "head": {"value": "a"}, "working_copy": {"state": "clean"}},
        ),
        history=({"object_id": {"value": "a"}, "parents": []},),
    )
    new = repo(
        refs=(
            {
                "name": "new",
                "authority": "local",
                "object_id": {"value": "b"},
                "tracking": "origin",
            },
        ),
        workspaces=(
            {"workspace_key": "new", "head": {"value": "b"}, "working_copy": {"state": "dirty"}},
        ),
        history=({"object_id": {"value": "b"}, "parents": []},),
    )
    delta = HistoryDeltaCalculator(
        objects={"a": old["history"][0], "b": new["history"][0]}
    ).calculate(snap("s", "a", 1, old), snap("s", "b", 2, new))
    names = [event["event"] for event in delta.repository_deltas[0]["events"]]
    assert "workspace_added" in names and "workspace_removed" in names
    assert "ref_created" in names and "ref_deleted" in names
