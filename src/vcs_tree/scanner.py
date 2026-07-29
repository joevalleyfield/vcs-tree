"""Repository discovery, status collection, caching, and rendering."""

import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

CACHE_BASE = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache")) / "vcs-tree"
REPO_TIMEOUT = 8
DISPLAY_WAIT = 5
BACKGROUND_WAIT = 300


def get_cache_path(start_dir):
    """Get the cache file path for a scanned directory, rooted at home."""
    start_dir = Path(start_dir).resolve()
    home = Path.home()

    try:
        rel_path = start_dir.relative_to(home)
    except ValueError:
        rel_path = Path(str(start_dir).replace("/", "_"))

    return CACHE_BASE / rel_path / "status.json"


def find_repo_roots(start_dir):
    """Find all .jj and .git roots, respecting colocated-repository precedence."""
    start_dir = Path(start_dir).resolve()
    jj_roots = {directory.parent for directory in start_dir.rglob(".jj") if directory.is_dir()}
    git_roots = {directory.parent for directory in start_dir.rglob(".git") if directory.is_dir()}
    filtered_git = {root for root in git_roots if root not in jj_roots}

    return {
        "jj": sorted(jj_roots, key=str),
        "git": sorted(filtered_git, key=str),
    }


def get_jj_status(repo_path, timeout=REPO_TIMEOUT):
    """Get status and last commit date from a jj repository."""
    try:
        result = subprocess.run(
            ["jj", "status", "--no-pager"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

        commit_date = None
        date_error = None
        try:
            date_result = subprocess.run(
                ["jj", "log", "-r", "@-", "--no-graph"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            if date_result.returncode != 0:
                date_error = (
                    date_result.stderr.strip()[:30] if date_result.stderr else "jj log failed"
                )
            else:
                parts = date_result.stdout.strip().split()
                if len(parts) >= 3:
                    date_candidate = parts[2]
                    if date_candidate != "00000000":
                        commit_date = date_candidate
        except subprocess.TimeoutExpired:
            date_error = "date fetch timeout"
        except Exception as error:  # noqa: BLE001 - subprocess failures are display data
            date_error = str(error)[:30]

        return {
            "type": "jj",
            "status": result.stdout.strip(),
            "commit_date": commit_date,
            "date_error": date_error,
            "error": None,
        }
    except subprocess.TimeoutExpired:
        return {
            "type": "jj",
            "status": None,
            "commit_date": None,
            "date_error": None,
            "error": "timeout",
        }
    except Exception as error:  # noqa: BLE001 - subprocess failures are display data
        return {
            "type": "jj",
            "status": None,
            "commit_date": None,
            "date_error": None,
            "error": str(error),
        }


def get_git_status(repo_path, timeout=REPO_TIMEOUT):
    """Get status and last commit date from a Git repository."""
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

        commit_date = None
        date_error = None
        try:
            date_result = subprocess.run(
                ["git", "log", "-1", "--format=%ad", "--date=short"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            if date_result.returncode != 0:
                date_error = (
                    date_result.stderr.strip()[:30] if date_result.stderr else "git log failed"
                )
            else:
                commit_date = date_result.stdout.strip()
        except subprocess.TimeoutExpired:
            date_error = "date fetch timeout"
        except Exception as error:  # noqa: BLE001 - subprocess failures are display data
            date_error = str(error)[:30]

        return {
            "type": "git",
            "status": result.stdout.strip(),
            "commit_date": commit_date,
            "date_error": date_error,
            "error": None,
        }
    except subprocess.TimeoutExpired:
        return {
            "type": "git",
            "status": None,
            "commit_date": None,
            "date_error": None,
            "error": "timeout",
        }
    except Exception as error:  # noqa: BLE001 - subprocess failures are display data
        return {
            "type": "git",
            "status": None,
            "commit_date": None,
            "date_error": None,
            "error": str(error),
        }


def scan_repos(start_dir):
    """Scan all repositories in parallel, returning results as they complete."""
    roots = find_repo_roots(start_dir)
    start_dir = Path(start_dir).resolve()
    tasks = [
        *((root, get_jj_status) for root in roots["jj"]),
        *((root, get_git_status) for root in roots["git"]),
    ]
    results = {}
    completed_at = {}

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(check_func, repo_path): repo_path for repo_path, check_func in tasks
        }
        for future in as_completed(futures, timeout=BACKGROUND_WAIT):
            repo_path = futures[future]
            rel_path = str(repo_path.relative_to(start_dir))
            try:
                results[rel_path] = future.result()
                completed_at[rel_path] = time.time()
            except Exception as error:  # noqa: BLE001 - worker failures are display data
                results[rel_path] = {"type": "unknown", "status": None, "error": str(error)}

    return results, completed_at


def get_diff_stat(status_output, repo_type):
    """Extract a compact diff-stat from status output."""
    if not status_output:
        return "clean"

    if repo_type == "jj":
        if "clean" in status_output.lower() or "no changes" in status_output.lower():
            return "clean"

        file_lines = [
            line for line in status_output.strip().split("\n") if line and line[0] in "AMDR"
        ]
        if file_lines:
            added = sum(1 for line in file_lines if line[0] == "A")
            modified = sum(1 for line in file_lines if line[0] == "M")
            deleted = sum(1 for line in file_lines if line[0] == "D")
            parts = []
            if added:
                parts.append(f"{added}A")
            if modified:
                parts.append(f"{modified}M")
            if deleted:
                parts.append(f"{deleted}D")
            return "+".join(parts) if parts else "clean"
        return "clean"

    if repo_type == "git":
        lines = [line for line in status_output.strip().split("\n") if line.strip()]
        if not lines:
            return "clean"
        modified = sum(1 for line in lines if line[0:2] in ("M ", "MM", " M"))
        added = sum(1 for line in lines if line[0:2] in ("A ", "AM"))
        deleted = sum(1 for line in lines if line[0:2] in ("D ", "DM"))
        parts = []
        if modified:
            parts.append(f"{modified}M")
        if added:
            parts.append(f"{added}A")
        if deleted:
            parts.append(f"{deleted}D")
        return "+".join(parts) if parts else "clean"

    return "clean"


def _get_type_mark(repo_type, text_mode=False):
    """Get a repository-type symbol or text marker."""
    if text_mode:
        return {"jj": "[jj]", "git": "[git]"}.get(repo_type, "[?]")
    return {"jj": "●", "git": "■"}.get(repo_type, "○")


def _format_repo(name, info, prefix, text_symbols):
    repo_type = info.get("type", "?")
    type_mark = _get_type_mark(repo_type, text_symbols)
    diff_stat = get_diff_stat(info.get("status"), repo_type)
    commit_date = info.get("commit_date", "")

    colors = {
        "reset": "\033[0m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "red": "\033[31m",
    }

    def colorize(text, color):
        return f"{colors[color]}{text}{colors['reset']}"

    if info.get("date_error"):
        status_display = colorize(f"[{info['date_error']}]", "red")
        return f"{prefix}{name} {type_mark} {status_display}"

    if info.get("error") == "timeout":
        diff_stat = colorize("timeout", "yellow")
    elif info.get("error"):
        diff_stat = colorize(f"error: {info['error'][:15]}", "red")
    elif diff_stat == "clean":
        diff_stat = colorize("clean", "green")
    else:
        diff_stat = colorize(diff_stat, "yellow")

    date_str = f" {commit_date}" if commit_date else ""
    return f"{prefix}{name} {type_mark} {diff_stat}{date_str}"


def format_results(
    results,
    completed_at,
    elapsed_time,
    is_partial=False,
    tree_mode=False,
    text_symbols=False,
):
    """Format results as a compact tree."""
    del completed_at  # Retained for compatibility with the baseline API.
    state = "listening" if is_partial else "done"
    lines = [f"\033[2m({state} @ {elapsed_time:.1f}s)\033[0m"]
    sorted_repos = sorted(results.items())

    if tree_mode:
        tree = defaultdict(list)
        for path, info in sorted_repos:
            parts = path.split("/")
            if len(parts) > 1:
                tree["/".join(parts[:-1])].append((parts[-1], info))
            else:
                tree["."].append((path, info))

        parents = sorted(tree)
        for parent_index, parent in enumerate(parents):
            if parent != ".":
                is_parent_last = parent_index == len(parents) - 1
                parent_prefix = "└── " if is_parent_last else "├── "
                lines.append(f"\033[2m{parent_prefix}{parent}/\033[0m")
                child_prefix_base = "    " if is_parent_last else "│   "
            else:
                child_prefix_base = ""

            repos = tree[parent]
            for child_index, (name, info) in enumerate(repos):
                is_last_child = child_index == len(repos) - 1
                child_prefix = child_prefix_base + ("└── " if is_last_child else "├── ")
                lines.append(_format_repo(name, info, child_prefix, text_symbols))
    else:
        for index, (path, info) in enumerate(sorted_repos):
            prefix = "└── " if index == len(sorted_repos) - 1 else "├── "
            lines.append(_format_repo(path, info, prefix, text_symbols))

    return "\n".join(lines)


def save_cache(results, start_dir):
    """Save results to the cache file for a scan root."""
    cache_file = get_cache_path(start_dir)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_data = {
        "timestamp": datetime.now().isoformat(),
        "scanned_from": str(start_dir),
        "results": dict(results),
    }
    with cache_file.open("w") as cache_handle:
        json.dump(cache_data, cache_handle, indent=2)


def vcs_tree(start_dir=".", tree_mode=False, text_symbols=False):
    """Scan repositories, display their state, and update the cache."""
    start_dir = Path(start_dir).resolve()
    start_time = time.time()
    print(f"Scanning from {start_dir}...", file=sys.stderr)

    results = {}
    completed_at = {}

    with ThreadPoolExecutor(max_workers=10) as executor:
        roots = find_repo_roots(start_dir)
        future_to_repo = {
            executor.submit(get_jj_status, root, REPO_TIMEOUT): ("jj", root) for root in roots["jj"]
        }
        future_to_repo.update(
            {
                executor.submit(get_git_status, root, REPO_TIMEOUT): ("git", root)
                for root in roots["git"]
            }
        )
        futures_list = list(future_to_repo)
        display_shown = False
        last_completion_time = start_time
        stall_threshold = 2.0

        while time.time() - start_time < BACKGROUND_WAIT:
            elapsed = time.time() - start_time
            now = time.time()
            for future in futures_list:
                repo_type, repo_path = future_to_repo[future]
                if not future.done():
                    continue
                rel_path = str(repo_path.relative_to(start_dir))
                if rel_path in results:
                    continue
                try:
                    results[rel_path] = future.result()
                    completed_at[rel_path] = elapsed
                    last_completion_time = now
                except Exception as error:  # noqa: BLE001 - worker failures are display data
                    results[rel_path] = {
                        "type": repo_type,
                        "status": None,
                        "commit_date": None,
                        "date_error": None,
                        "error": str(error)[:50],
                    }

            if not display_shown and results and now - last_completion_time >= stall_threshold:
                print(
                    format_results(
                        results,
                        completed_at,
                        elapsed,
                        is_partial=True,
                        tree_mode=tree_mode,
                        text_symbols=text_symbols,
                    )
                )
                still_running = sum(1 for future in futures_list if not future.done())
                print(f"[collecting in background: {still_running} repos...]", file=sys.stderr)
                display_shown = True

            if all(future.done() for future in futures_list):
                break
            time.sleep(0.1)

        for future in futures_list:
            if not future.done():
                future.cancel()

    elapsed = time.time() - start_time
    save_cache(results, start_dir)
    if not display_shown:
        print(
            format_results(
                results,
                completed_at,
                elapsed,
                is_partial=False,
                tree_mode=tree_mode,
                text_symbols=text_symbols,
            )
        )
