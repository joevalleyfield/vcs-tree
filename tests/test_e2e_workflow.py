"""Black-box operator workflows through the installed package command."""

import json
import os
import shutil
import subprocess

import pytest


def run_cli(*arguments, cwd=None):
    environment = os.environ.copy()
    environment.setdefault("UV_CACHE_DIR", "/tmp/vcs-tree-uv-cache")
    environment["XDG_CACHE_HOME"] = "/tmp/vcs-tree-e2e-cache"
    return subprocess.run(
        ["uv", "run", "vcs-tree", *arguments],
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


def run_git(repository, *arguments):
    return subprocess.run(
        ["git", *arguments], cwd=repository, text=True, capture_output=True, check=True
    )


def make_git_fixture(tmp_path):
    repository = tmp_path / "git-fixture"
    repository.mkdir()
    run_git(repository, "init", "-q")
    run_git(repository, "config", "user.name", "vcs-tree test")
    run_git(repository, "config", "user.email", "vcs-tree@example.test")
    (repository / "README.md").write_text("first\n", encoding="utf-8")
    run_git(repository, "add", "README.md")
    run_git(repository, "commit", "-qm", "first")
    return repository


def test_installed_cli_git_snapshot_delta_workflow_is_read_only(tmp_path):
    repository = make_git_fixture(tmp_path)
    state = tmp_path / "state"
    before_head = run_git(repository, "rev-parse", "HEAD").stdout.strip()

    initialized = run_cli(
        "history", "init", "--state-root", str(state), "--writer-id", "e2e-writer"
    )
    assert initialized.returncode == 0
    init_document = json.loads(initialized.stdout)
    assert init_document["writer_policy"] == "single_writer"
    assert any("cloud-synchronized" in warning for warning in init_document["warnings"])

    inspected = run_cli("history", "inspect", "--state-root", str(state))
    assert inspected.returncode == 0
    assert json.loads(inspected.stdout)["status"] == "ok"

    first = run_cli("history", "snapshot", "--state-root", str(state), str(repository))
    assert first.returncode == 0, first.stderr
    first_document = json.loads(first.stdout)
    first_id = first_document["snapshot_id"]
    assert run_git(repository, "rev-parse", "HEAD").stdout.strip() == before_head

    (repository / "README.md").write_text("second\n", encoding="utf-8")
    run_git(repository, "add", "README.md")
    run_git(repository, "commit", "-qm", "second")
    second = run_cli("history", "snapshot", "--state-root", str(state), str(repository))
    assert second.returncode == 0, second.stderr
    second_id = json.loads(second.stdout)["snapshot_id"]

    delta = run_cli(
        "history",
        "delta",
        "--state-root",
        str(state),
        "--from",
        first_id,
        "--to",
        second_id,
    )
    assert delta.returncode == 0, delta.stderr
    events = json.loads(delta.stdout)["repository_deltas"][0]["events"]
    assert any(event["event"] == "ref_target_changed" for event in events)
    assert run_git(repository, "rev-parse", "HEAD").stdout.strip() != before_head

    default_scan = run_cli(str(repository), "--text-symbols")
    assert default_scan.returncode == 0


def test_cli_reports_missing_and_corrupt_state_as_json(tmp_path):
    state = tmp_path / "state"
    missing = run_cli(
        "history",
        "delta",
        "--state-root",
        str(state),
        "--from",
        "missing-a",
        "--to",
        "missing-b",
    )
    assert missing.returncode == 2
    assert json.loads(missing.stdout)["status"] == "error"

    initialized = run_cli("history", "init", "--state-root", str(state))
    assert initialized.returncode == 0
    (state / "manifest.json").write_text("corrupt", encoding="utf-8")
    corrupt = run_cli("history", "inspect", "--state-root", str(state))
    assert corrupt.returncode == 2
    corrupt_document = json.loads(corrupt.stdout)
    assert corrupt_document["status"] == "degraded"
    assert "error" in corrupt_document


@pytest.mark.skipif(shutil.which("jj") is None, reason="jj is not installed")
def test_cli_colocated_fixture_reports_complete_native_surfaces(tmp_path):
    repository = tmp_path / "colocated-fixture"
    repository.mkdir()
    subprocess.run(
        ["jj", "git", "init", "--colocate", str(repository)], check=True, capture_output=True
    )
    state = tmp_path / "state"
    assert run_cli("history", "init", "--state-root", str(state)).returncode == 0
    snapshot = run_cli("history", "snapshot", "--state-root", str(state), str(repository))
    assert snapshot.returncode == 0, snapshot.stderr
    native = json.loads(snapshot.stdout)["repositories"][0]
    assert native["mode"] == "colocated"
    for component in ("workspaces", "bookmarks", "visible_heads"):
        assert native["collection"][component]["state"] == "complete"
