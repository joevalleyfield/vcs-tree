import subprocess

import pytest

from vcs_tree.jj_adapter import (
    NULL_COMMIT,
    JjAdapter,
    _annotate_graph,
    _parse_bookmark,
    _parse_history,
    _parse_workspace,
)
from vcs_tree.models import CollectionOutcome, CollectionState, HistoryBoundaryState


def completed(stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess(["jj"], returncode, stdout, stderr)


def history_line(commit="ABC"):
    return (
        f"{commit}\x00change\x00P Q\x00Alice\x00a@example\x002026-01-01T00:00:00Z"
        "\x00Bob\x00b@example\x002026-01-02T00:00:00Z\x00summary"
    )


def test_parsers_preserve_jj_identity_conflicts_and_workspaces():
    commit = _parse_history(history_line())
    assert commit["object_id"]["value"] == "abc"
    assert commit["change_id"] == "change"
    assert len(commit["parents"]) == 2
    assert commit["committer"]["email"] == "b@example"
    virtual = _parse_history(history_line(NULL_COMMIT))
    assert virtual["kind"] == "virtual_root"
    assert virtual["summary"] == ""
    bookmark = _parse_bookmark("topic\x00origin\x00conflicted\x00\x00old\x00new1,new2\x00ahead")
    assert bookmark["state"] == "conflicted"
    assert len(bookmark["added_targets"]) == 2
    workspace = _parse_workspace("default\x00/repo\x00ABC\x00change\x00dirty\x00A:1")
    assert workspace["is_primary"] is True
    assert workspace["working_copy"]["state"] == "dirty"


@pytest.mark.parametrize(
    "parser,value",
    [
        (_parse_history, "bad"),
        (_parse_bookmark, "bad"),
        (_parse_workspace, "bad"),
    ],
)
def test_parsers_reject_malformed_records(parser, value):
    with pytest.raises(ValueError):
        parser(value)


def test_successful_collection_includes_all_jj_surfaces(tmp_path):
    (tmp_path / ".jj").mkdir()
    (tmp_path / ".jj" / "repo").write_text("../shared/.jj/repo\n", encoding="utf-8")
    responses = iter(
        [
            completed(str(tmp_path)),
            completed("default\x00" + str(tmp_path) + "\x00ABC\x00change\x00dirty\x00A:1\n\n"),
            completed("topic\x00origin\x00normal\x00ABC\x00\x00\x00ahead\n\n"),
            completed("ABC\x00change\n\n"),
            completed(history_line() + "\n\n" + history_line(NULL_COMMIT) + "\n"),
        ]
    )
    observation = JjAdapter(tmp_path, runner=lambda _command: next(responses)).collect()
    assert observation.root == tmp_path
    assert observation.store_hint == "../shared/.jj/repo"
    assert observation.workspaces[0]["current"]["change_id"] == "change"
    assert observation.bookmarks[0]["targets"][0]["value"] == "abc"
    assert observation.visible_heads[0]["authority"] == "visible_head"
    assert observation.history[1]["kind"] == "virtual_root"
    assert observation.history_boundary.state is HistoryBoundaryState.COMPLETE
    commit = observation.history[0]
    assert commit["visibility"] == "visible"
    assert "visible_head" in commit["authorities"]
    assert commit["parent_changes"] == [
        {"object_id": {"algorithm": "jj", "value": "p"}, "change_id": None},
        {"object_id": {"algorithm": "jj", "value": "q"}, "change_id": None},
    ]
    assert observation.to_dict()["root"] == str(tmp_path)


def test_identity_error_isolated(tmp_path):
    observation = JjAdapter(
        tmp_path, runner=lambda _command: completed("", "not a jj repo", 1)
    ).collect()
    assert observation.collection["identity"].state is CollectionState.ERROR
    assert observation.history_boundary.state is HistoryBoundaryState.UNKNOWN


@pytest.mark.parametrize(
    "failure",
    [
        subprocess.TimeoutExpired("jj", 8),
        OSError("jj missing"),
        completed("", "failed", 1),
    ],
)
def test_command_failures_are_factual(tmp_path, failure):
    def runner(_command):
        if isinstance(failure, BaseException):
            raise failure
        return failure

    output, error = JjAdapter(tmp_path, runner=runner)._call(("status",), "jj.status")
    assert output == ""
    assert error is not None


def test_component_errors_and_parse_errors(tmp_path):
    error_adapter = JjAdapter(tmp_path, runner=lambda _command: completed("", "bad", 1))
    for method in (
        error_adapter._workspaces,
        error_adapter._bookmarks,
        error_adapter._visible_heads,
        error_adapter._history,
    ):
        result = method()
        assert result[1].state is CollectionState.ERROR

    malformed = JjAdapter(tmp_path, runner=lambda _command: completed("bad\n"))
    for method in (malformed._workspaces, malformed._bookmarks, malformed._history):
        result = method()
        assert result[1].state is CollectionState.PARTIAL
    heads, outcome = malformed._visible_heads()
    assert heads == () and outcome.state is CollectionState.PARTIAL


def test_partial_history_and_bookmarks_keep_valid_records(tmp_path):
    adapter = JjAdapter(
        tmp_path,
        runner=lambda _command: completed(
            history_line() + "\nbad\n"
            if _command[0] == "log" and "all()" in _command
            else "good\x00origin\x00normal\x00ABC\x00\x00\x00ahead\nbad\n"
            if _command[0] == "bookmark"
            else ""
        ),
    )
    history, history_outcome = adapter._history()
    bookmarks, bookmark_outcome = adapter._bookmarks()
    assert len(history) == 1 and history_outcome.state is CollectionState.PARTIAL
    assert len(bookmarks) == 1 and bookmark_outcome.state is CollectionState.PARTIAL


def test_graph_annotations_preserve_partial_unknowns_and_ignore_unmatched_authorities(tmp_path):
    record = _parse_history(history_line("ABC"))
    record["parents"] = []
    heads = ({"object_id": {"algorithm": "jj", "value": "other"}, "change_id": "x"},)
    result = _annotate_graph(
        (record,),
        heads,
        ({"current": {"object_id": {"value": "workspace"}}},),
        ({"name": "local", "targets": [{"value": "bookmark"}], "added_targets": []},),
        CollectionOutcome(CollectionState.PARTIAL),
    )
    assert result[0]["visibility"] == "unknown"
    assert result[0]["authorities"] == []


def test_store_hint_and_default_runner(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return completed("ok")

    monkeypatch.setattr("vcs_tree.jj_adapter.subprocess.run", fake_run)
    output, error = JjAdapter(tmp_path)._call(("status",), "jj.status")
    assert output == "ok" and error is None
    assert calls[0][0][0] == "jj"
    assert JjAdapter(tmp_path)._store_hint() is None
    pointer = tmp_path / ".jj"
    pointer.mkdir()
    (pointer / "repo").write_text("\n", encoding="utf-8")
    assert JjAdapter(tmp_path)._store_hint().endswith(".jj/repo")
