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
from vcs_tree.snapshot import SnapshotCollector, _dedupe_dicts


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
    assert result.generation == 1
    assert len(ledger.read_objects()) == 2


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


def test_boundary_precedence_and_empty_observations(tmp_path):
    ledger = HistoryLedger.create(tmp_path / "state", writer_id="writer-a")
    collector = SnapshotCollector(ledger)
    unknown = collector._boundary(
        None, jj_observation(tmp_path, boundary=HistoryBoundary(HistoryBoundaryState.UNKNOWN))
    )
    assert unknown.state is HistoryBoundaryState.UNKNOWN
    empty = collector._repository(tmp_path, None, None)
    assert empty["mode"] == "jj"
