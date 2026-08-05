from vcs_tree.git_adapter import GitObservation
from vcs_tree.jj_adapter import JjObservation
from vcs_tree.ledger import HistoryLedger
from vcs_tree.models import (
    CollectionError,
    CollectionOutcome,
    CollectionState,
    HistoryBoundary,
    HistoryBoundaryState,
)
from vcs_tree.snapshot import (
    SnapshotCollector,
    _change_graph,
    _combine_outcomes,
    _dedupe_dicts,
    _merge_workspaces,
)


def git_observation(root, *, state=CollectionState.COMPLETE, boundary=None):
    outcome = CollectionOutcome(state)
    history = [
        {
            "kind": "commit",
            "object_id": {"algorithm": "sha1", "value": "abc"},
            "parents": [],
        }
    ]
    return GitObservation(
        root,
        outcome,
        (
            {
                "path": str(root),
                "role": "primary",
                "current": {"object_id": {"algorithm": "sha1", "value": "abc"}},
            },
        ),
        (
            {
                "name": "refs/heads/main",
                "authority": "local",
                "object_id": {"algorithm": "sha1", "value": "abc"},
                "peeled_object_id": None,
            },
        ),
        tuple(history),
        boundary or HistoryBoundary(HistoryBoundaryState.COMPLETE),
        {"identity": outcome, "workspaces": outcome, "refs": outcome, "history": outcome},
    )


def jj_observation(root, *, state=CollectionState.COMPLETE, boundary=None):
    outcome = CollectionOutcome(state)
    history = [
        {
            "kind": "commit",
            "object_id": {"algorithm": "jj", "value": "def"},
            "change_id": "change",
            "parents": [],
        }
    ]
    return JjObservation(
        root,
        "shared-store",
        ({"workspace_key": "default", "path": str(root), "current": None},),
        (
            {
                "name": "main",
                "remote": "origin",
                "targets": [{"algorithm": "jj", "value": "def"}],
                "state": "normal",
            },
        ),
        (
            {
                "object_id": {"algorithm": "jj", "value": "def"},
                "change_id": "change",
                "authority": "visible_head",
            },
        ),
        tuple(history),
        boundary or HistoryBoundary(HistoryBoundaryState.COMPLETE),
        {
            "identity": outcome,
            "workspaces": outcome,
            "bookmarks": outcome,
            "visible_heads": outcome,
            "history": outcome,
        },
    )


def test_dedupe_dicts_is_deterministic():
    records = _dedupe_dicts(
        [{"id": "b"}, {"id": "a"}, {"id": "b", "new": True}], lambda item: item["id"]
    )
    assert records == ({"id": "a"}, {"id": "b"})


def test_legacy_workspace_presentation_and_outcome_combinations(tmp_path):
    git = git_observation(tmp_path)
    git = GitObservation(
        git.root,
        git.identity,
        ({**git.workspaces[0], "working_copy": {"state": "dirty"}},),
        git.refs,
        git.history,
        git.history_boundary,
        git.collection,
    )
    workspace = _merge_workspaces(git, None, "2026-08-04T12:00:00Z")[0]
    assert workspace["working_copy"]["recorded_state"] == "dirty"
    assert workspace["working_copy"]["outcome"]["state"] == "complete"
    native = GitObservation(
        git.root,
        git.identity,
        (
            {
                **git.workspaces[0],
                "working_copy": {"outcome": {"state": "not_requested", "errors": []}},
            },
        ),
        git.refs,
        git.history,
        git.history_boundary,
        git.collection,
    )
    assert _merge_workspaces(native, None, "2026-08-04T12:00:00Z")[0]["working_copy"] == {
        "outcome": {"state": "not_requested", "errors": []}
    }

    error = CollectionError("command", "jj.history", "failed")
    assert (
        _combine_outcomes([CollectionOutcome(CollectionState.ERROR, (error,))]).state
        is CollectionState.ERROR
    )
    assert (
        _combine_outcomes([CollectionOutcome(CollectionState.PARTIAL, (error,))]).state
        is CollectionState.PARTIAL
    )
    assert (
        _combine_outcomes(
            [
                CollectionOutcome(CollectionState.NOT_REQUESTED),
                CollectionOutcome(CollectionState.NOT_REQUESTED),
            ]
        ).state
        is CollectionState.NOT_REQUESTED
    )


def test_git_snapshot_publishes_after_generation(tmp_path):
    (tmp_path / ".git").mkdir()
    ledger = HistoryLedger.create(tmp_path / "state", writer_id="writer-a")
    collector = SnapshotCollector(
        ledger,
        git_factory=lambda path: type(
            "Factory", (), {"collect": lambda self: git_observation(path)}
        )(),
        clock=lambda: "2026-08-01T12:00:00Z",
        snapshot_id_factory=lambda: "snapshot-a",
    )
    result = collector.collect(tmp_path)
    assert result.generation == 1
    assert result.envelope.schema_version == 2
    assert result.envelope.repositories[0]["mode"] == "git"
    assert result.envelope.history_store.generation == 1
    assert ledger.read_objects()
    reopened = HistoryLedger.open(tmp_path / "state")
    snapshots = reopened._load(reopened._SNAPSHOTS)
    assert snapshots[0]["manifest"]["snapshot_id"] == "snapshot-a"


def test_snapshot_progress_reports_phases(tmp_path):
    (tmp_path / ".git").mkdir()
    ledger = HistoryLedger.create(tmp_path / "state", writer_id="writer-a")
    messages = []
    collector = SnapshotCollector(
        ledger,
        git_factory=lambda path: type(
            "Factory", (), {"collect": lambda self: git_observation(path)}
        )(),
        snapshot_id_factory=lambda: "progress",
        progress=messages.append,
    )
    collector.collect(tmp_path)
    assert any(message.startswith("discovering") for message in messages)
    assert any(message.startswith("collecting") for message in messages)
    assert any(message.startswith("persisting") for message in messages)
    assert any("completed snapshot progress (complete)" in message for message in messages)


def test_colocated_snapshot_merges_native_surfaces_and_deduplicates(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".jj").mkdir()
    ledger = HistoryLedger.create(tmp_path / "state", writer_id="writer-a")

    def git(path):
        return type("Factory", (), {"collect": lambda self: git_observation(path)})()

    def jj(path):
        return type("Factory", (), {"collect": lambda self: jj_observation(path)})()

    collector = SnapshotCollector(
        ledger, git_factory=git, jj_factory=jj, snapshot_id_factory=lambda: "snapshot-colocated"
    )
    result = collector.collect(tmp_path)
    repository = result.envelope.repositories[0]
    assert repository["mode"] == "colocated"
    assert {item.get("authority", "") for item in repository["refs"]} == {"local", ""}
    hints = repository["publication_hints"]
    assert hints["git_refs"][0]["publication_kind"] == "git_ref"
    assert hints["jj_bookmarks"][0]["provenance"] == "observed_remote"
    assert hints["jj_bookmarks"][0]["publication_hint"] is True
    assert result.generation == 1
    assert len(ledger.read_objects()) == 2


def test_jj_change_graph_and_colocated_identity_mapping_are_retained(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".jj").mkdir()
    ledger = HistoryLedger.create(tmp_path / "state", writer_id="writer-a")
    git = git_observation(tmp_path)
    jj = jj_observation(tmp_path)
    jj_history = {
        "kind": "commit",
        "object_id": {"algorithm": "jj", "value": "abc"},
        "change_id": "change",
        "parents": [],
        "visibility": "visible",
        "authorities": ["visible_head"],
    }
    jj = JjObservation(
        jj.root,
        jj.store_hint,
        jj.workspaces,
        jj.bookmarks,
        jj.visible_heads,
        (jj_history,),
        jj.history_boundary,
        jj.collection,
    )
    collector = SnapshotCollector(
        ledger,
        git_factory=lambda _path: type("Factory", (), {"collect": lambda self: git})(),
        jj_factory=lambda _path: type("Factory", (), {"collect": lambda self: jj})(),
    )
    repository = collector.collect(tmp_path).envelope.repositories[0]
    assert repository["change_graph"]["changes"][0]["change_id"] == "change"
    assert repository["change_graph"]["visible_heads"]
    assert repository["change_graph"]["changes"][0]["versions"][0]["object_id"]["value"] == "abc"
    objects = ledger.read_objects()
    jj_record = next(
        item
        for item in objects.values()
        if item["kind"] == "commit" and item["object_id"]["algorithm"] == "jj"
    )
    assert jj_record["git_object_id"]["value"] == "abc"
    assert SnapshotCollector(ledger)._repository(tmp_path, None, None)["change_graph"] is None
    virtual = JjObservation(
        jj.root,
        jj.store_hint,
        jj.workspaces,
        jj.bookmarks,
        jj.visible_heads,
        ({"kind": "virtual_root", "change_id": "root", "object_id": {"value": "0"}},),
        jj.history_boundary,
        jj.collection,
    )
    assert _change_graph(virtual)["changes"] == []


def test_repeated_snapshot_reuses_key_and_objects(tmp_path):
    (tmp_path / ".git").mkdir()
    ledger = HistoryLedger.create(tmp_path / "state", writer_id="writer-a")
    collector = SnapshotCollector(
        ledger,
        git_factory=lambda path: type(
            "Factory", (), {"collect": lambda self: git_observation(path)}
        )(),
        snapshot_id_factory=iter(["one", "two"]).__next__,
    )
    first = collector.collect(tmp_path)
    second = collector.collect(tmp_path)
    assert (
        first.envelope.repositories[0]["repository_key"]
        == second.envelope.repositories[0]["repository_key"]
    )
    assert second.generation == 2
    assert len(ledger.read_objects()) == 1


def test_jj_only_and_incomplete_boundary_are_preserved(tmp_path):
    (tmp_path / ".jj").mkdir()
    ledger = HistoryLedger.create(tmp_path / "state", writer_id="writer-a")
    collector = SnapshotCollector(
        ledger,
        jj_factory=lambda path: type(
            "Factory",
            (),
            {
                "collect": lambda self: jj_observation(
                    path, boundary=HistoryBoundary(HistoryBoundaryState.SHALLOW)
                )
            },
        )(),
        snapshot_id_factory=lambda: "jj-snapshot",
    )
    result = collector.collect(tmp_path)
    assert result.envelope.repositories[0]["mode"] == "jj"
    assert result.envelope.repositories[0]["history_boundary"]["state"] == "shallow"


def test_partial_native_outcome_is_preserved(tmp_path):
    (tmp_path / ".git").mkdir()
    ledger = HistoryLedger.create(tmp_path / "state", writer_id="writer-a")
    error = CollectionError("command_error", "git.history", "failed", 1)
    observation = git_observation(tmp_path, state=CollectionState.PARTIAL)
    observation = GitObservation(
        observation.root,
        observation.identity,
        observation.workspaces,
        observation.refs,
        observation.history,
        observation.history_boundary,
        {
            "identity": CollectionOutcome(CollectionState.COMPLETE),
            "history": CollectionOutcome(CollectionState.PARTIAL, (error,)),
        },
    )
    collector = SnapshotCollector(
        ledger,
        git_factory=lambda path: type("Factory", (), {"collect": lambda self: observation})(),
        snapshot_id_factory=lambda: "partial",
    )
    result = collector.collect(tmp_path)
    assert result.envelope.repositories[0]["collection"]["history"]["state"] == "partial"


def test_colocated_git_success_does_not_mask_jj_history_error(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".jj").mkdir()
    ledger = HistoryLedger.create(tmp_path / "state", writer_id="writer-a")
    git = git_observation(tmp_path)
    jj = jj_observation(tmp_path)
    error = CollectionError("command_error", "jj.history", "failed", 1)
    jj = JjObservation(
        jj.root,
        jj.store_hint,
        jj.workspaces,
        jj.bookmarks,
        jj.visible_heads,
        (),
        HistoryBoundary(HistoryBoundaryState.UNKNOWN),
        {**jj.collection, "history": CollectionOutcome(CollectionState.ERROR, (error,))},
    )
    collector = SnapshotCollector(
        ledger,
        git_factory=lambda _path: type("Git", (), {"collect": lambda self: git})(),
        jj_factory=lambda _path: type("Jj", (), {"collect": lambda self: jj})(),
        clock=lambda: "2026-08-04T12:00:00Z",
    )
    collection = collector.collect(tmp_path).envelope.repositories[0]["collection"]
    assert collection["git_history"]["state"] == "complete"
    assert collection["jj_history"]["state"] == "error"
    assert collection["history"]["state"] == "error"


def test_boundary_precedence_and_empty_observations(tmp_path):
    ledger = HistoryLedger.create(tmp_path / "state", writer_id="writer-a")
    collector = SnapshotCollector(ledger)
    unknown = collector._boundary(
        None, jj_observation(tmp_path, boundary=HistoryBoundary(HistoryBoundaryState.UNKNOWN))
    )
    assert unknown.state is HistoryBoundaryState.UNKNOWN
    empty = collector._repository(tmp_path, None, None)
    assert empty["mode"] == "jj"
