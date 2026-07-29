import json
import subprocess
from unittest.mock import Mock

import pytest

from vcs_tree import scanner


def completed(stdout="", stderr="", returncode=0):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def test_find_repo_roots_treats_colocation_as_jj(tmp_path):
    colocated = tmp_path / "colocated"
    (colocated / ".jj").mkdir(parents=True)
    (colocated / ".git").mkdir()
    nested_git = colocated / "vendor" / "nested"
    (nested_git / ".git").mkdir(parents=True)
    git_only = tmp_path / "git-only"
    (git_only / ".git").mkdir(parents=True)

    assert scanner.find_repo_roots(tmp_path) == {
        "jj": [colocated],
        "git": [nested_git, git_only],
    }


def test_get_git_status_collects_status_and_date(monkeypatch, tmp_path):
    run = Mock(side_effect=[completed(" M file.py\n"), completed("2026-07-29\n")])
    monkeypatch.setattr(scanner.subprocess, "run", run)

    assert scanner.get_git_status(tmp_path) == {
        "type": "git",
        "status": "M file.py",
        "commit_date": "2026-07-29",
        "date_error": None,
        "error": None,
    }
    assert run.call_count == 2


def test_get_git_status_preserves_date_error(monkeypatch, tmp_path):
    run = Mock(side_effect=[completed(), completed(stderr="not a repo", returncode=128)])
    monkeypatch.setattr(scanner.subprocess, "run", run)

    result = scanner.get_git_status(tmp_path)

    assert result["date_error"] == "not a repo"
    assert result["error"] is None


def test_get_git_status_reports_timeout(monkeypatch, tmp_path):
    monkeypatch.setattr(
        scanner.subprocess,
        "run",
        Mock(side_effect=subprocess.TimeoutExpired("git", 8)),
    )

    assert scanner.get_git_status(tmp_path)["error"] == "timeout"


def test_get_git_status_reports_date_timeout(monkeypatch, tmp_path):
    run = Mock(side_effect=[completed(), subprocess.TimeoutExpired("git log", 8)])
    monkeypatch.setattr(scanner.subprocess, "run", run)

    assert scanner.get_git_status(tmp_path)["date_error"] == "date fetch timeout"


def test_get_git_status_reports_process_error(monkeypatch, tmp_path):
    monkeypatch.setattr(scanner.subprocess, "run", Mock(side_effect=OSError("git missing")))

    assert scanner.get_git_status(tmp_path)["error"] == "git missing"


@pytest.mark.parametrize(
    ("log_output", "expected_date"),
    [
        ("abc user 2026-07-29 rest", "2026-07-29"),
        ("abc user 00000000 root()", None),
    ],
)
def test_get_jj_status_distinguishes_real_date_from_null_root(
    monkeypatch,
    tmp_path,
    log_output,
    expected_date,
):
    run = Mock(side_effect=[completed("The working copy has no changes.\n"), completed(log_output)])
    monkeypatch.setattr(scanner.subprocess, "run", run)

    result = scanner.get_jj_status(tmp_path)

    assert result["commit_date"] == expected_date
    assert result["date_error"] is None


def test_get_jj_status_preserves_log_error(monkeypatch, tmp_path):
    run = Mock(side_effect=[completed(), completed(stderr="broken store", returncode=1)])
    monkeypatch.setattr(scanner.subprocess, "run", run)

    assert scanner.get_jj_status(tmp_path)["date_error"] == "broken store"


def test_get_jj_status_reports_date_timeout(monkeypatch, tmp_path):
    run = Mock(side_effect=[completed(), subprocess.TimeoutExpired("jj log", 8)])
    monkeypatch.setattr(scanner.subprocess, "run", run)

    assert scanner.get_jj_status(tmp_path)["date_error"] == "date fetch timeout"


def test_get_jj_status_reports_process_error(monkeypatch, tmp_path):
    monkeypatch.setattr(scanner.subprocess, "run", Mock(side_effect=OSError("jj missing")))

    assert scanner.get_jj_status(tmp_path)["error"] == "jj missing"


@pytest.mark.parametrize(
    ("status", "repo_type", "expected"),
    [
        ("", "git", "clean"),
        (" M tracked\nA  added\nD  removed", "git", "1M+1A+1D"),
        ("Working copy changes:\nA new\nM changed\nD gone", "jj", "1A+1M+1D"),
        ("The working copy has no changes.", "jj", "clean"),
        ("anything", "unknown", "clean"),
    ],
)
def test_get_diff_stat(status, repo_type, expected):
    assert scanner.get_diff_stat(status, repo_type) == expected


def test_format_results_renders_flat_states():
    results = {
        "clean": {
            "type": "git",
            "status": "",
            "commit_date": "2026-07-29",
            "date_error": None,
            "error": None,
        },
        "timed": {
            "type": "jj",
            "status": None,
            "commit_date": None,
            "date_error": None,
            "error": "timeout",
        },
        "unreadable": {
            "type": "git",
            "status": None,
            "commit_date": None,
            "date_error": "git log failed",
            "error": None,
        },
    }

    output = scanner.format_results(results, {}, 1.25, text_symbols=True)

    assert "(done @ 1.2s)" in output
    assert "clean [git]" in output
    assert "2026-07-29" in output
    assert "timed [jj]" in output
    assert "timeout" in output
    assert "unreadable [git]" in output
    assert "[git log failed]" in output


def test_format_results_groups_tree_paths():
    info = {
        "type": "git",
        "status": "",
        "commit_date": "",
        "date_error": None,
        "error": None,
    }

    output = scanner.format_results({"group/one": info, "root": info}, {}, 0, tree_mode=True)

    assert "group/" in output
    assert "one ■" in output
    assert "root ■" in output


def test_save_cache_uses_scan_specific_path(monkeypatch, tmp_path):
    cache_base = tmp_path / "cache"
    scan_root = tmp_path / "workspace"
    scan_root.mkdir()
    monkeypatch.setattr(scanner, "CACHE_BASE", cache_base)

    scanner.save_cache({"repo": {"type": "git"}}, scan_root)

    cache_files = list(cache_base.rglob("status.json"))
    assert len(cache_files) == 1
    payload = json.loads(cache_files[0].read_text())
    assert payload["scanned_from"] == str(scan_root)
    assert payload["results"] == {"repo": {"type": "git"}}


def test_vcs_tree_scans_empty_directory(monkeypatch, tmp_path, capsys):
    cache = tmp_path / "status.json"
    monkeypatch.setattr(scanner, "find_repo_roots", lambda _path: {"jj": [], "git": []})
    monkeypatch.setattr(scanner, "get_cache_path", lambda _path: cache)

    scanner.vcs_tree(tmp_path, tree_mode=True, text_symbols=True)

    captured = capsys.readouterr()
    assert f"Scanning from {tmp_path}" in captured.err
    assert "(done @" in captured.out
    assert json.loads(cache.read_text())["results"] == {}


def test_vcs_tree_collects_finished_repository(monkeypatch, tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    cache = tmp_path / "status.json"
    monkeypatch.setattr(scanner, "find_repo_roots", lambda _path: {"jj": [], "git": [repo]})
    monkeypatch.setattr(
        scanner,
        "get_git_status",
        lambda _path, _timeout: {
            "type": "git",
            "status": "",
            "commit_date": "2026-07-29",
            "date_error": None,
            "error": None,
        },
    )
    monkeypatch.setattr(scanner, "get_cache_path", lambda _path: cache)

    scanner.vcs_tree(tmp_path)

    assert "repo ■" in capsys.readouterr().out
    assert json.loads(cache.read_text())["results"]["repo"]["type"] == "git"


def test_scan_repos_records_worker_error(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    def fail(_path):
        raise RuntimeError("broken")

    monkeypatch.setattr(scanner, "find_repo_roots", lambda _path: {"jj": [repo], "git": []})
    monkeypatch.setattr(scanner, "get_jj_status", fail)

    results, completed = scanner.scan_repos(tmp_path)

    assert results["repo"]["error"] == "broken"
    assert completed == {}


def test_scan_repos_records_success(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    result = {"type": "jj", "status": "", "error": None}
    monkeypatch.setattr(scanner, "find_repo_roots", lambda _path: {"jj": [repo], "git": []})
    monkeypatch.setattr(scanner, "get_jj_status", lambda _path: result)

    results, completed = scanner.scan_repos(tmp_path)

    assert results == {"repo": result}
    assert completed["repo"] > 0
