from vcs_tree.candidate import project_current_workspaces
from vcs_tree.models import HistoryStore, SnapshotEnvelope


def snapshot(repository):
    return SnapshotEnvelope(
        "snapshot-1",
        "2026-08-06T12:00:00Z",
        {"name": "vcs-tree"},
        HistoryStore("store", 1, writer_id="writer"),
        {"root": "/workspace", "outcome": {"state": "complete", "errors": []}},
        (repository,),
    )


def test_projection_keeps_identity_workspace_parents_completeness_and_bounds(tmp_path):
    document = snapshot(
        {
            "repository_key": "repo-1",
            "mode": "jj",
            "locations": [{"path": "/workspace/project"}],
            "collection": {"jj_workspaces": {"state": "complete", "errors": []}},
            "workspaces": [
                {
                    "workspace_key": "default",
                    "role": "primary",
                    "current": {"object_id": {"value": "head"}, "change_id": "change"},
                    "parents": [{"value": "parent"}],
                    "working_copy": {
                        "recorded_state": "dirty",
                        "freshness": "current",
                        "entries": [{"path": "a"}, {"path": "b"}],
                        "entries_limit": 256,
                        "entries_truncated": True,
                        "outcome": {"state": "complete", "errors": []},
                        "entries_outcome": {"state": "partial", "errors": []},
                        "refresh": {"state": "performed", "errors": []},
                    },
                }
            ],
        }
    )
    result = project_current_workspaces(document, max_entries=1)
    repository = result["repositories"][0]
    workspace = repository["workspaces"][0]
    assert repository["path"] == "project"
    assert workspace["current"] == {"object_id": "head", "change_id": "change"}
    assert workspace["parents"] == ["parent"]
    assert workspace["working_copy"]["entries"] == [{"path": "a"}]
    assert workspace["working_copy"]["entries_truncated"] is True
    assert workspace["working_copy"]["entries_total"] is None
    assert repository["completeness"]["jj_workspaces"]["state"] == "complete"


def test_projection_rejects_negative_bounds_and_empty_workspace_repositories():
    document = snapshot({"repository_key": "repo-1", "locations": [{"path": "/workspace"}]})
    assert project_current_workspaces(document)["repositories"] == []
    try:
        project_current_workspaces(document, max_entries=-1)
    except ValueError as exc:
        assert "max_entries" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("negative bounds must be rejected")


def test_projection_preserves_external_paths_and_malformed_working_copy_as_unknown():
    document = snapshot(
        {
            "repository_key": "repo-2",
            "mode": "git",
            "locations": [{"path": "/outside/project"}],
            "workspaces": [
                {"workspace_key": "primary", "working_copy": "unreadable"},
                {"workspace_key": "secondary", "working_copy": {"entries_limit": "bad"}},
            ],
        }
    )
    result = project_current_workspaces(document)
    workspace = result["repositories"][0]["workspaces"][0]
    assert result["repositories"][0]["path"] == "/outside/project"
    assert workspace["working_copy"]["recorded_state"] == "unknown"
    assert result["repositories"][0]["workspaces"][1]["working_copy"]["entries_limit"] == 256
    no_location = project_current_workspaces(
        snapshot({"repository_key": "repo-3", "workspaces": [{"workspace_key": "primary"}]})
    )
    assert no_location["repositories"][0]["path"] is None
