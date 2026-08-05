import subprocess

import pytest

from vcs_tree.git_adapter import (
    GitAdapter,
    _parse_commit,
    _parse_ref,
    _parse_worktrees,
)
from vcs_tree.models import CollectionState, HistoryBoundaryState


def completed(stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess(["git"], returncode, stdout, stderr)


def test_parsers_preserve_native_shapes():
    ref = _parse_ref("refs/tags/v1\x00ABC\x00tag\x00DEF")
    assert ref["authority"] == "tag"
    assert ref["peeled_object_id"]["value"] == "def"
    commit = _parse_commit(
        "ABC\x00P Q\x00Alice\x00a@example\x002026-01-01T00:00:00Z"
        "\x00Bob\x00b@example\x002026-01-02T00:00:00Z\x00summary"
    )
    assert [item["value"] for item in commit["parents"]] == ["p", "q"]
    assert commit["committer"]["email"] == "b@example"
    worktrees = _parse_worktrees(
        "worktree /repo\nHEAD ABC\nbranch refs/heads/main\n\nworktree /linked\nHEAD DEF\n"
    )
    assert worktrees[1]["role"] == "linked"


@pytest.mark.parametrize(
    "parser,value",
    [
        (_parse_ref, "bad"),
        (_parse_commit, "bad"),
    ],
)
def test_parsers_reject_malformed_records(parser, value):
    with pytest.raises(ValueError):
        parser(value)


def test_worktree_parser_ignores_unknown_lines():
    assert _parse_worktrees("unknown value\n") == ()


def test_successful_collection_normalizes_refs_history_and_workspaces(tmp_path):
    shallow = tmp_path / ".git"
    shallow.mkdir()
    (shallow / "shallow").write_text("ABC\n", encoding="utf-8")
    responses = iter(
        [
            completed(str(tmp_path)),
            completed("worktree " + str(tmp_path) + "\nHEAD ABC\nbranch refs/heads/main\n\n"),
            completed(
                "# branch.oid ABC\x00# branch.head main\x00"
                "1 .M N... 100644 100644 100644 abc abc file\x00"
            ),
            completed("refs/heads/main\x00ABC\x00commit\x00\nrefs/tags/v1\x00TAG\x00tag\x00ABC\n"),
            completed(
                "ABC\x00P\x00Alice\x00a@example\x002026-01-01T00:00:00Z\x00Bob\x00b@example\x002026-01-02T00:00:00Z\x00summary\n"
            ),
        ]
    )
    observation = GitAdapter(tmp_path, runner=lambda _command: next(responses)).collect()
    assert observation.identity.state is CollectionState.COMPLETE
    assert observation.refs[1]["authority"] == "tag"
    assert observation.history[0]["summary"] == "summary"
    assert observation.history_boundary.state is HistoryBoundaryState.SHALLOW
    assert observation.workspaces[0]["working_copy"]["state"] == "dirty"
    assert observation.to_dict()["root"] == str(tmp_path)


def test_empty_refs_are_a_complete_empty_history(tmp_path):
    responses = iter([completed(str(tmp_path)), completed(""), completed(""), completed("")])
    adapter = GitAdapter(tmp_path, runner=lambda _command: next(responses))
    observation = adapter.collect()
    assert observation.refs == ()
    assert observation.history == ()
    assert observation.history_boundary.state is HistoryBoundaryState.COMPLETE


def test_identity_error_isolated(tmp_path):
    observation = GitAdapter(
        tmp_path, runner=lambda _command: completed("", "not a repo", 128)
    ).collect()
    assert observation.identity.state is CollectionState.ERROR
    assert observation.collection["identity"].errors[0].exit_code == 128


def test_identity_rejects_parent_repository_boundary(tmp_path):
    child = tmp_path / "child"
    child.mkdir()
    observation = GitAdapter(
        child, runner=lambda _command: completed(str(tmp_path) + "\n")
    ).collect()
    assert observation.identity.state is CollectionState.ERROR
    assert observation.collection["identity"].errors[0].kind == "boundary_error"


@pytest.mark.parametrize(
    "failure",
    [
        subprocess.TimeoutExpired("git", 8),
        OSError("git missing"),
        completed("", "failed", 1),
    ],
)
def test_command_failures_are_factual(tmp_path, failure):
    def runner(_command):
        if isinstance(failure, BaseException):
            raise failure
        return failure

    output, error = GitAdapter(tmp_path, runner=runner)._call(("status",), "git.status")
    assert output == ""
    assert error is not None


def test_workspaces_and_refs_report_errors_and_parse_errors(tmp_path):
    adapter = GitAdapter(tmp_path, runner=lambda _command: completed("", "broken", 1))
    workspaces, outcome = adapter._workspaces()
    assert workspaces == () and outcome.state is CollectionState.ERROR
    refs, outcome = adapter._refs()
    assert refs == () and outcome.state is CollectionState.ERROR

    malformed = GitAdapter(tmp_path, runner=lambda _command: completed("bad\n"))
    refs, outcome = malformed._refs()
    assert refs == () and outcome.state is CollectionState.PARTIAL


def test_worktree_status_error_and_unknown_history_paths(tmp_path):
    responses = iter(
        [completed("worktree " + str(tmp_path) + "\nHEAD ABC\n\n"), completed("", "bad", 1)]
    )
    workspaces, outcome = GitAdapter(
        tmp_path, runner=lambda _command: next(responses)
    )._workspaces()
    assert workspaces[0]["working_copy"]["state"] == "unreadable"
    assert outcome.state is CollectionState.COMPLETE

    adapter = GitAdapter(tmp_path, runner=lambda _command: completed("", "bad", 1))
    history, outcome, boundary = adapter._history(
        ({"object_id": {"value": "abc"}, "peeled_object_id": None},)
    )
    assert history == () and outcome.state is CollectionState.ERROR
    assert boundary.state is HistoryBoundaryState.UNKNOWN


def test_history_parse_error_and_no_root_boundary(tmp_path):
    malformed = GitAdapter(tmp_path, runner=lambda _command: completed("bad\n"))
    history, outcome, boundary = malformed._history(
        ({"object_id": {"value": "abc"}, "peeled_object_id": None},)
    )
    assert history == () and outcome.state is CollectionState.PARTIAL
    assert boundary.state is HistoryBoundaryState.UNKNOWN
    empty = GitAdapter(tmp_path, runner=lambda _command: completed())
    _, outcome, boundary = empty._history(())
    assert outcome.state is CollectionState.COMPLETE
    assert boundary.state is HistoryBoundaryState.COMPLETE


def test_default_runner_and_additional_error_branches(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return completed("ok")

    monkeypatch.setattr("vcs_tree.git_adapter.subprocess.run", fake_run)
    output, error = GitAdapter(tmp_path)._call(("status",), "git.status")
    assert output == "ok" and error is None
    assert calls[0][0][0] == "git"

    responses = iter([completed(""), completed("", "bad", 1)])
    no_status = GitAdapter(tmp_path, runner=lambda _command: next(responses))
    workspaces, outcome = no_status._workspaces()
    assert workspaces[0]["working_copy"]["state"] == "unreadable"
    assert outcome.state is CollectionState.COMPLETE

    responses = iter(
        [
            completed("worktree /other\nHEAD ABC\n\nworktree " + str(tmp_path) + "\nHEAD DEF\n\n"),
            completed("# branch.oid DEF\x00# branch.head main\x00"),
        ]
    )
    workspaces, outcome = GitAdapter(
        tmp_path, runner=lambda _command: next(responses)
    )._workspaces()
    assert workspaces[0]["role"] == "primary"
    assert workspaces[1]["working_copy"]["state"] == "clean"
    assert outcome.state is CollectionState.COMPLETE

    complete = GitAdapter(
        tmp_path,
        runner=lambda _command: completed(
            "ABC\x00\x00Alice\x00a@example\x002026-01-01T00:00:00Z\x00Bob\x00b@example\x002026-01-02T00:00:00Z\x00summary\n"
        ),
    )
    _, outcome, boundary = complete._history(
        ({"object_id": {"value": "abc"}, "peeled_object_id": None},)
    )
    assert outcome.state is CollectionState.COMPLETE
    assert boundary.state is HistoryBoundaryState.COMPLETE


def test_shallow_file_without_entries_keeps_complete_boundary(tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "shallow").write_text("\n", encoding="utf-8")
    adapter = GitAdapter(
        tmp_path,
        runner=lambda _command: completed(
            "ABC\x00\x00Alice\x00a@example\x002026-01-01T00:00:00Z"
            "\x00Bob\x00b@example\x002026-01-02T00:00:00Z\x00summary\n"
        ),
    )
    _, outcome, boundary = adapter._history(
        ({"object_id": {"value": "abc"}, "peeled_object_id": None},)
    )
    assert outcome.state is CollectionState.COMPLETE
    assert boundary.state is HistoryBoundaryState.COMPLETE


def test_git_working_copy_distinguishes_unborn_changed_and_status_errors(tmp_path):
    unborn = GitAdapter(
        tmp_path,
        runner=lambda _command: completed("# branch.oid (initial)\x00? draft.txt\x00"),
        clock=lambda: "2026-08-04T12:00:00Z",
    )._working_copy()
    assert unborn["unborn"] is True
    assert unborn["current"] is None
    assert unborn["recorded_state"] == "dirty"
    assert unborn["entries"][0] == {"status": "added", "path": "draft.txt"}
    assert unborn["refresh"]["state"] == "not_applicable"
    assert unborn["freshness"] == "current"

    error = GitAdapter(
        tmp_path, runner=lambda _command: completed("", "status denied", 1)
    )._working_copy()
    assert error["recorded_state"] == "unreadable"
    assert error["outcome"]["state"] == "error"
    assert error["entries_outcome"]["errors"][0]["stage"] == "git.working_copy"
    assert error["freshness"] == "unknown"


def test_git_working_copy_parse_failure_and_entry_bound(tmp_path):
    malformed = GitAdapter(tmp_path, runner=lambda _command: completed("bad\x00"))._working_copy()
    assert malformed["recorded_state"] == "unknown"
    assert malformed["outcome"]["state"] == "partial"

    changed = GitAdapter(
        tmp_path,
        runner=lambda _command: completed("# branch.oid ABC\x00? first\x00? second\x00"),
        entry_limit=1,
    )._working_copy()
    assert changed["current"]["object_id"]["value"] == "abc"
    assert changed["entries"] == [{"status": "added", "path": "first"}]
    assert changed["entries_truncated"] is True


def test_git_status_suppresses_optional_lock_refresh(tmp_path):
    calls = []

    def runner(command):
        calls.append(command)
        return completed("# branch.oid ABC\x00")

    GitAdapter(tmp_path, runner=runner)._working_copy()
    assert calls == [
        (
            "--no-optional-locks",
            "status",
            "--porcelain=v2",
            "--branch",
            "-z",
            "--untracked-files=all",
        )
    ]


def test_linked_git_worktree_is_explicitly_not_observed(tmp_path):
    adapter = GitAdapter(tmp_path, entry_limit=7)
    value = adapter._unobserved_working_copy()
    assert value["outcome"]["state"] == "not_requested"
    assert value["freshness"] == "not_applicable"
    assert value["entries_limit"] == 7
    assert adapter._working_copy_outcomes(({"working_copy": value},))[0].state is (
        CollectionState.NOT_REQUESTED
    )
    assert adapter._working_copy_outcomes(())[0].state is CollectionState.NOT_REQUESTED
