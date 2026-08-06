from vcs_tree.delta import HistoryDeltaCalculator, _repository_location, _scan_root
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
    change_graph=None,
):
    result = {
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
    if change_graph is not None:
        result["mode"] = "jj"
        result["change_graph"] = change_graph
        result["bookmarks"] = []
        result["collection"].pop("refs")
        result["collection"]["bookmarks"] = {"state": "complete", "errors": []}
    return result


def graph(changes=(), heads=(), state="complete"):
    return {
        "changes": list(changes),
        "visible_heads": list(heads),
        "outcome": {"state": state, "errors": []},
    }


def change(change_id, versions):
    return {"change_id": change_id, "versions": list(versions)}


def version(object_id, parents=()):
    return {"object_id": {"value": object_id}, "visibility": "visible", "parents": list(parents)}


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


def test_repository_location_is_scan_relative_or_explicitly_absolute():
    record = {"locations": [{"path": "/tmp/root/project"}]}
    assert _repository_location(record, "/tmp/root") == "project"
    assert _repository_location(record, None) == "/tmp/root/project"
    assert _repository_location(record, "/other/root") == "/tmp/root/project"
    assert _repository_location({"locations": [{"path": ""}]}, "/tmp/root") is None
    assert _repository_location({"locations": [{}]}, "/tmp/root") is None


def test_jj_bookmarks_are_checked_instead_of_git_refs():
    a = repo()
    b = repo()
    for item in (a, b):
        item["mode"] = "jj"
        item["bookmarks"] = []
        item["collection"]["bookmarks"] = {"state": "complete", "errors": []}
        item["collection"].pop("refs")
    delta = HistoryDeltaCalculator(
        delta_id_factory=lambda: "d", clock=lambda: "2026-08-01T12:01:00Z"
    ).calculate(snap("s", "a", 1, a), snap("s", "b", 2, b))
    assert delta.repository_deltas[0]["events"] == []


def test_colocated_publication_hints_are_separate_and_partial_bookmarks_do_not_hide_graph():
    old = repo(
        refs=({"name": "main", "authority": "local", "object_id": {"value": "g1"}},),
        change_graph=graph(changes=(), heads=()),
    )
    new = repo(
        refs=({"name": "main", "authority": "local", "object_id": {"value": "g1"}},),
        change_graph=graph(changes=(change("c1", (version("j1"),)),), heads=()),
    )
    for item in (old, new):
        item["mode"] = "colocated"
        item["bookmarks"] = [{"name": "topic", "remote": "origin", "targets": [{"value": "j1"}]}]
        item["collection"]["bookmarks"] = {"state": "complete", "errors": []}
        item["collection"]["refs"] = {"state": "complete", "errors": []}
    new["bookmarks"][0]["targets"] = [{"value": "j2"}]
    events = (
        HistoryDeltaCalculator()
        .calculate(snap("s", "a", 1, old), snap("s", "b", 2, new))
        .repository_deltas[0]["events"]
    )
    assert any(event["event"] == "bookmark_target_changed" for event in events)
    assert any(event["details"].get("state") == "introduced" for event in events)
    new["collection"]["refs"] = {"state": "partial", "errors": []}
    events = (
        HistoryDeltaCalculator()
        .calculate(snap("s", "a", 1, old), snap("s", "b", 2, new))
        .repository_deltas[0]["events"]
    )
    assert any(
        event["event"] == "comparison_incomplete" and event["details"]["component"] == "git_refs"
        for event in events
    )
    new["collection"]["bookmarks"] = {"state": "partial", "errors": []}
    events = (
        HistoryDeltaCalculator()
        .calculate(snap("s", "a", 1, old), snap("s", "b", 2, new))
        .repository_deltas[0]["events"]
    )
    assert any(
        event["event"] == "comparison_incomplete"
        and event["details"]["component"] == "jj_bookmarks"
        for event in events
    )
    assert any(event["details"].get("state") == "introduced" for event in events)


def test_jj_change_graph_event_vocabulary_and_heads():
    old_graph = graph(
        changes=(
            change("rewrite", (version("r1"),)),
            change("diverge", (version("d1"), version("d2"))),
            change("becomes_divergent", (version("b1"),)),
            change("topology", (version("t1", ({"object_id": {"value": "p1"}},)),)),
            change("gone", (version("g1"),)),
        ),
        heads=({"object_id": {"value": "r1"}, "change_id": "rewrite"},),
    )
    new_graph = graph(
        changes=(
            change("rewrite", (version("r2"),)),
            change("diverge", (version("d3"),)),
            change("becomes_divergent", (version("b2"), version("b3"))),
            change("topology", (version("t1", ({"object_id": {"value": "p2"}},)),)),
            change("introduced", (version("i1"),)),
        ),
        heads=(
            {"object_id": {"value": "r2"}, "change_id": "rewrite"},
            {"object_id": {"value": "i1"}, "change_id": "introduced"},
            {"object_id": {"value": "unmatched"}, "change_id": "unknown"},
        ),
    )
    events = (
        HistoryDeltaCalculator()
        .calculate(
            snap("s", "a", 1, repo(change_graph=old_graph)),
            snap("s", "b", 2, repo(change_graph=new_graph)),
        )
        .repository_deltas[0]["events"]
    )
    states = {
        event["details"].get("change_id"): event["details"].get("state")
        for event in events
        if event["event"] == "change_versions_changed"
    }
    assert states == {
        "becomes_divergent": "divergent",
        "diverge": "resolved",
        "gone": "visibility_lost",
        "introduced": "introduced",
        "rewrite": "rewritten",
        "topology": "topology_changed",
    }
    assert {event["event"] for event in events} >= {"visible_head_added", "visible_head_removed"}


def test_jj_graph_partial_suppresses_recovery_and_visibility_loss():
    old = graph(changes=(change("gone", (version("g1"),)),), heads=(), state="partial")
    new = graph(changes=(change("new", (version("n1"),)),), heads=(), state="complete")
    events = (
        HistoryDeltaCalculator()
        .calculate(
            snap("s", "a", 1, repo(change_graph=old)),
            snap("s", "b", 2, repo(change_graph=new)),
        )
        .repository_deltas[0]["events"]
    )
    assert any(event["event"] == "comparison_incomplete" for event in events)
    assert not any(event["details"].get("state") == "introduced" for event in events)
    assert not any(event["details"].get("state") == "visibility_lost" for event in events)


def test_jj_graph_recovery_does_not_call_newly_observable_changes_introduced():
    old = graph(changes=(), heads=(), state="partial")
    new = graph(changes=(change("recovered", (version("r1"),)),), heads=())
    events = (
        HistoryDeltaCalculator()
        .calculate(
            snap("s", "a", 1, repo(change_graph=old)),
            snap("s", "b", 2, repo(change_graph=new)),
        )
        .repository_deltas[0]["events"]
    )
    assert [event["event"] for event in events] == ["comparison_incomplete"]
    assert events[0]["details"]["component"] == "change_graph"


def test_jj_graph_recovery_does_not_call_partial_target_changes_introduced():
    old = graph(changes=(), heads=())
    new = graph(changes=(change("recovered", (version("r1"),)),), heads=(), state="partial")
    events = (
        HistoryDeltaCalculator()
        .calculate(
            snap("s", "a", 1, repo(change_graph=old)),
            snap("s", "b", 2, repo(change_graph=new)),
        )
        .repository_deltas[0]["events"]
    )
    assert [event["event"] for event in events] == ["comparison_incomplete"]


def test_jj_graph_equal_divergent_versions_are_a_noop():
    graph_data = graph(
        changes=(change("same", (version("v1"), version("v2"))),),
        heads=(),
    )
    events = (
        HistoryDeltaCalculator()
        .calculate(
            snap("s", "a", 1, repo(change_graph=graph_data)),
            snap("s", "b", 2, repo(change_graph=graph_data)),
        )
        .repository_deltas[0]["events"]
    )
    assert events == []


def test_jj_graph_partial_topology_is_indeterminate_and_scan_scope_mismatch_is_explicit():
    old = graph(changes=(change("same", (version("v1"),)),), state="partial")
    new = graph(
        changes=(change("same", (version("v1", ({"object_id": {"value": "p"}},)),)),),
        state="complete",
    )
    events = (
        HistoryDeltaCalculator()
        .calculate(
            snap("s", "a", 1, repo(change_graph=old)), snap("s", "b", 2, repo(change_graph=new))
        )
        .repository_deltas[0]["events"]
    )
    topology = next(event for event in events if event["event"] == "change_versions_changed")
    assert topology["certainty"] == "indeterminate"
    before = snap("s", "a", 1, repo())
    after = snap("s", "b", 2, repo())
    before.scan["root"] = "/a"
    after.scan["root"] = "/b"
    assert _scan_root(after, before) is None


def test_jj_graph_unknown_boundary_retains_version_events():
    old = graph(changes=(change("same", (version("v1"),)),), state="complete")
    new = graph(
        changes=(change("same", (version("v1", ({"object_id": {"value": "p"}},)),)),),
        state="complete",
    )
    before = repo(change_graph=old, boundary="unknown")
    after = repo(change_graph=new, boundary="unknown")
    events = (
        HistoryDeltaCalculator()
        .calculate(snap("s", "a", 1, before), snap("s", "b", 2, after))
        .repository_deltas[0]["events"]
    )
    topology = next(event for event in events if event["event"] == "change_versions_changed")
    assert topology["details"]["state"] == "topology_changed"


def test_jj_graph_noop_and_scan_root_match():
    graph_data = graph(changes=(change("same", (version("v1"),)),), heads=())
    before = snap("s", "a", 1, repo(change_graph=graph_data))
    after = snap("s", "b", 2, repo(change_graph=graph_data))
    before.scan["root"] = "/same"
    after.scan["root"] = "/same"
    assert HistoryDeltaCalculator().calculate(before, after).repository_deltas[0]["events"] == []
    assert _scan_root(after, before) == "/same"


def test_jj_graph_direct_suppression_branches():
    calculator = HistoryDeltaCalculator()
    partial_old = {
        "change_graph": graph(
            changes=(change("gone", (version("g1"),)),), heads=(), state="partial"
        )
    }
    complete_new = {"change_graph": graph(changes=(), heads=(), state="complete")}
    assert calculator._change_graph(partial_old, complete_new) == []
    same = graph(changes=(change("same", (version("v1"),)),), heads=(), state="complete")
    assert calculator._change_graph({"change_graph": same}, {"change_graph": same}) == []
    old_heads = {
        "change_graph": graph(
            changes=(), heads=({"object_id": {"value": "gone"}},), state="partial"
        )
    }
    assert (
        calculator._change_graph(
            old_heads, {"change_graph": graph(changes=(), heads=(), state="complete")}
        )
        == []
    )


def test_incomplete_history_is_reported_and_suppresses_history_events():
    a = repo(history_state="complete")
    b = repo(history_state="partial")
    events = (
        HistoryDeltaCalculator()
        .calculate(snap("s", "a", 1, a), snap("s", "b", 2, b))
        .repository_deltas[0]["events"]
    )
    assert len(events) == 1
    assert events[0]["event"] == "comparison_incomplete"
    assert events[0]["details"]["component"] == "history"
    assert events[0]["details"]["to_state"] == "partial"


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
