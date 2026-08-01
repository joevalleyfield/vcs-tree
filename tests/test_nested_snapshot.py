import vcs_tree.snapshot as snapshot_module
from vcs_tree.git_adapter import GitObservation
from vcs_tree.jj_adapter import JjObservation
from vcs_tree.ledger import HistoryLedger
from vcs_tree.models import (
    CollectionOutcome,
    CollectionState,
    HistoryBoundary,
    HistoryBoundaryState,
)
from vcs_tree.snapshot import (
    SnapshotCollector,
    _discover,
    _workspace_key,
    discover_repository_roots,
)


def git_observation(root):
    outcome = CollectionOutcome(CollectionState.COMPLETE)
    return GitObservation(
        root,
        outcome,
        ({"path": str(root), "role": "primary", "current": None},),
        (
            {
                "name": "main",
                "authority": "local",
                "object_id": {"algorithm": "sha1", "value": "abc"},
            },
        ),
        ({"kind": "commit", "object_id": {"algorithm": "sha1", "value": "abc"}, "parents": []},),
        HistoryBoundary(HistoryBoundaryState.COMPLETE),
        {"identity": outcome, "workspaces": outcome, "refs": outcome, "history": outcome},
    )


def jj_observation(root):
    outcome = CollectionOutcome(CollectionState.COMPLETE)
    return JjObservation(
        root,
        "shared-store",
        ({"workspace_key": "default", "path": str(root), "current": None},),
        ({"name": "main", "remote": None, "targets": [], "state": "normal"},),
        (),
        ({"kind": "commit", "object_id": {"algorithm": "jj", "value": "def"}, "parents": []},),
        HistoryBoundary(HistoryBoundaryState.COMPLETE),
        {
            "identity": outcome,
            "workspaces": outcome,
            "bookmarks": outcome,
            "visible_heads": outcome,
            "history": outcome,
        },
    )


def test_discovery_canonicalizes_nested_and_colocated_roots(tmp_path):
    (tmp_path / ".git").mkdir()
    child = tmp_path / "child"
    (child / ".git").mkdir(parents=True)
    (child / ".jj").mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(child, target_is_directory=True)

    roots = discover_repository_roots(tmp_path)
    assert roots == tuple(sorted((tmp_path.resolve(), child.resolve()), key=str))
    assert _workspace_key({"workspace_key": "default"}) == "default"


def test_discovery_reports_non_directory_and_walk_errors(monkeypatch, tmp_path):
    missing = tmp_path / "missing"
    assert _discover(missing) == (
        (),
        (snapshot_module.CollectionError("not_directory", "discovery", str(missing)),),
    )

    def broken_walk(*_args, onerror=None, **_kwargs):
        if onerror:
            onerror(OSError("denied"))
        yield from ()

    monkeypatch.setattr(snapshot_module.os, "walk", broken_walk)
    roots, errors = _discover(tmp_path)
    assert roots == ()
    assert errors[0].kind == "discovery_error"


def test_nested_collection_publishes_distinct_sorted_records(tmp_path):
    (tmp_path / ".git").mkdir()
    child = tmp_path / "child"
    (child / ".git").mkdir(parents=True)
    (child / ".jj").mkdir()
    ledger = HistoryLedger.create(tmp_path / "state", writer_id="writer")

    result = SnapshotCollector(
        ledger,
        git_factory=lambda path: type(
            "GitFactory", (), {"collect": lambda self: git_observation(path)}
        )(),
        jj_factory=lambda path: type(
            "JjFactory", (), {"collect": lambda self: jj_observation(path)}
        )(),
    ).collect(tmp_path)
    repositories = result.envelope.repositories
    assert [item["locations"][0]["relative_path"] for item in repositories] == [".", "child"]
    assert [item["mode"] for item in repositories] == ["git", "colocated"]
    assert [item["repository_key"] for item in repositories] == ["repo-0001", "repo-0002"]
    assert result.envelope.scan["outcome"]["state"] == "complete"
