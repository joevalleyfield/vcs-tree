"""Installed-entry-point acceptance coverage for the mechanical query workflow."""

import json
import os
import shutil
import subprocess

import pytest


def run_cli(*arguments, cwd=None):
    environment = os.environ.copy()
    environment.setdefault("UV_CACHE_DIR", "/tmp/vcs-tree-uv-cache")
    environment["XDG_CACHE_HOME"] = "/tmp/vcs-tree-query-cache"
    return subprocess.run(
        ["uv", "run", "vcs-tree", *arguments],
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


def git(repo, *args, check=True):
    return subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=check)


def query(fact_type="repository-exists", attributes=None, state="ever_observed"):
    return {
        "schema": "vcs-tree.history-query",
        "schema_version": 1,
        "scope": {"all": True},
        "where": {"fact": {"type": fact_type, "attributes": attributes or {}, "state": state}},
    }


def make_unborn(tmp_path):
    repo = tmp_path / "unborn"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "query test")
    git(repo, "config", "user.email", "query@example.test")
    (repo / "draft.txt").write_text("draft\n", encoding="utf-8")
    return repo


def test_git_unborn_query_outputs_factual_result_and_all_modes(tmp_path):
    repo = make_unborn(tmp_path)
    state = tmp_path / "state"
    assert run_cli("history", "init", "--state-root", str(state)).returncode == 0
    where = json.dumps(query())
    captured = run_cli(
        "history", "query", "--capture", "--state-root", str(state), str(repo), "--where", where
    )
    assert captured.returncode == 0, captured.stderr
    summary = captured.stdout
    assert "history query" in summary and "true" in summary
    assert "initial_commit_due" not in summary
    audit = run_cli(
        "history",
        "query",
        "--state-root",
        str(state),
        str(repo),
        "--where",
        where,
        "--format",
        "audit",
    )
    assert audit.returncode == 0 and "repository_key" in audit.stdout
    document = json.loads(
        run_cli(
            "history",
            "query",
            "--state-root",
            str(state),
            "--where",
            where,
            "--format",
            "json",
            "--capture",
        ).stdout
    )
    assert document["results"][0]["evidence"]
    snapshot_id = document["capture"]["snapshot_id"]
    retained_input = json.dumps(query()).encode()
    # The installed command accepts stdin as the retained query representation.
    retained = subprocess.run(
        [
            "uv",
            "run",
            "vcs-tree",
            "history",
            "query",
            "--state-root",
            str(state),
            "--snapshot",
            snapshot_id,
            "--where-file",
            "-",
            "--format",
            "json",
        ],
        cwd=repo,
        env={**os.environ, "XDG_CACHE_HOME": "/tmp/vcs-tree-query-cache"},
        input=retained_input,
        text=False,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert retained.returncode == 0
    assert json.loads(retained.stdout)["capture"]["performed"] is False


def test_query_invalid_and_missing_snapshot_exit_usage_or_operational(tmp_path):
    repo = make_unborn(tmp_path)
    state = tmp_path / "state"
    assert run_cli("history", "init", "--state-root", str(state)).returncode == 0
    malformed = run_cli("history", "query", "--state-root", str(state), str(repo), "--where", "{}")
    assert malformed.returncode == 2 and "invalid query schema" in malformed.stdout
    missing = run_cli(
        "history",
        "query",
        "--state-root",
        str(state),
        "--snapshot",
        "missing",
        "--where",
        json.dumps(query()),
        "--format",
        "json",
    )
    assert missing.returncode == 2
    assert json.loads(missing.stdout)["status"] == "error"


@pytest.mark.skipif(shutil.which("jj") is None, reason="jj is not installed")
def test_jj_root_parent_fact_is_queryable_without_policy_conclusion(tmp_path):
    repo = tmp_path / "jj-root"
    repo.mkdir()
    subprocess.run(["jj", "git", "init", "--colocate", str(repo)], check=True, capture_output=True)
    state = tmp_path / "state"
    assert run_cli("history", "init", "--state-root", str(state)).returncode == 0
    result = run_cli(
        "history",
        "query",
        "--state-root",
        str(state),
        str(repo),
        "--format",
        "json",
        "--where",
        json.dumps(query()),
        "--capture",
    )
    assert result.returncode == 0, result.stderr
    document = json.loads(result.stdout)
    assert "initial_commit_due" not in result.stdout
    assert document["temporal_index"]["source_snapshots"]
