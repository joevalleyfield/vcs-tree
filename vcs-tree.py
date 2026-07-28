#!/usr/bin/env python3
"""
VCS tree scanner with parallel repo checks, progressive caching, and graceful timeouts.
Displays results at 5 seconds, continues collecting for up to 5 minutes.
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from collections import defaultdict

CACHE_BASE = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache")) / "vcs-tree"


def get_cache_path(start_dir):
    """Get cache file path for a scanned directory, rooted at ~"""
    start_dir = Path(start_dir).resolve()
    home = Path.home()

    # Make relative to home if possible
    try:
        rel_path = start_dir.relative_to(home)
    except ValueError:
        # Not under home, use absolute path with sanitization
        rel_path = Path(str(start_dir).replace("/", "_"))

    cache_file = CACHE_BASE / rel_path / "status.json"
    return cache_file
REPO_TIMEOUT = 8  # seconds per repo before marking timeout
DISPLAY_WAIT = 5  # seconds before showing initial results
BACKGROUND_WAIT = 300  # 5 minutes to keep collecting


def find_repo_roots(start_dir):
    """Find all .jj and .git roots, respecting precedence."""
    start_dir = Path(start_dir).resolve()

    jj_roots = set()
    git_roots = set()

    # Find all .jj directories
    for jj_dir in start_dir.rglob(".jj"):
        if jj_dir.is_dir():
            jj_roots.add(jj_dir.parent)

    # Find all .git directories
    for git_dir in start_dir.rglob(".git"):
        if git_dir.is_dir():
            git_roots.add(git_dir.parent)

    # Only filter git roots if they have a jj root at the exact same location
    # (jj takes precedence over git). Show all nested git repos.
    filtered_git = {g for g in git_roots if g not in jj_roots}

    return {
        "jj": sorted(jj_roots, key=str),
        "git": sorted(filtered_git, key=str),
    }


def get_jj_status(repo_path, timeout=REPO_TIMEOUT):
    """Get status and last commit date from a jj repo."""
    try:
        result = subprocess.run(
            ["jj", "status", "--no-pager"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # Get last committed date (parent commit, not working copy)
        commit_date = None
        date_error = None
        try:
            date_result = subprocess.run(
                ["jj", "log", "-r", "@-", "--no-graph"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if date_result.returncode != 0:
                # jj log failed (e.g., repo in broken state)
                date_error = date_result.stderr.strip()[:30] if date_result.stderr else "jj log failed"
            else:
                # Parse date from output: "hash author date time commit_id"
                parts = date_result.stdout.strip().split()
                if len(parts) >= 3:
                    date_candidate = parts[2]
                    # Skip synthetic root() commit placeholder (newly initialized repo)
                    if date_candidate != "00000000":
                        commit_date = date_candidate
        except subprocess.TimeoutExpired:
            date_error = "date fetch timeout"
        except Exception as e:
            date_error = str(e)[:30]

        return {
            "type": "jj",
            "status": result.stdout.strip(),
            "commit_date": commit_date,
            "date_error": date_error,
            "error": None,
        }
    except subprocess.TimeoutExpired:
        return {"type": "jj", "status": None, "commit_date": None, "date_error": None, "error": "timeout"}
    except Exception as e:
        return {"type": "jj", "status": None, "commit_date": None, "date_error": None, "error": str(e)}


def get_git_status(repo_path, timeout=REPO_TIMEOUT):
    """Get status and last commit date from a git repo."""
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # Get last commit date
        commit_date = None
        date_error = None
        try:
            date_result = subprocess.run(
                ["git", "log", "-1", "--format=%ad", "--date=short"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if date_result.returncode != 0:
                date_error = date_result.stderr.strip()[:30] if date_result.stderr else "git log failed"
            else:
                commit_date = date_result.stdout.strip()
        except subprocess.TimeoutExpired:
            date_error = "date fetch timeout"
        except Exception as e:
            date_error = str(e)[:30]

        return {
            "type": "git",
            "status": result.stdout.strip(),
            "commit_date": commit_date,
            "date_error": date_error,
            "error": None,
        }
    except subprocess.TimeoutExpired:
        return {"type": "git", "status": None, "commit_date": None, "date_error": None, "error": "timeout"}
    except Exception as e:
        return {"type": "git", "status": None, "commit_date": None, "date_error": None, "error": str(e)}


def scan_repos(start_dir):
    """Scan all repos in parallel, returning results as they complete."""
    roots = find_repo_roots(start_dir)
    start_dir = Path(start_dir).resolve()

    # Build list of (repo_path, check_func) tuples
    tasks = []
    for jj_root in roots["jj"]:
        tasks.append((jj_root, get_jj_status))
    for git_root in roots["git"]:
        tasks.append((git_root, get_git_status))

    results = {}
    completed_at = {}

    # Run all checks in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all tasks
        futures = {
            executor.submit(check_func, repo_path): (repo_path, check_func.__name__)
            for repo_path, check_func in tasks
        }

        # Collect results as they complete
        for future in as_completed(futures, timeout=BACKGROUND_WAIT):
            repo_path, func_name = futures[future]
            try:
                result = future.result()
                rel_path = str(repo_path.relative_to(start_dir))
                if rel_path == ".":
                    rel_path = "."
                results[rel_path] = result
                completed_at[rel_path] = time.time()
            except Exception as e:
                rel_path = str(repo_path.relative_to(start_dir))
                results[rel_path] = {"type": "unknown", "status": None, "error": str(e)}

    return results, completed_at


def get_diff_stat(status_output, repo_type):
    """Extract a compact diff-stat from status output."""
    if not status_output:
        return "clean"

    if repo_type == "jj":
        # jj status shows "working copy changes:" followed by file lines like "M src/main.rs"
        if "clean" in status_output.lower() or "no changes" in status_output.lower():
            return "clean"

        lines = status_output.strip().split("\n")
        # Count lines that start with a status marker (A, M, D, R, etc.)
        file_lines = [l for l in lines if l and l[0] in "AMDR"]
        if file_lines:
            # Count by type
            added = sum(1 for l in file_lines if l[0] == "A")
            modified = sum(1 for l in file_lines if l[0] == "M")
            deleted = sum(1 for l in file_lines if l[0] == "D")
            parts = []
            if added:
                parts.append(f"{added}A")
            if modified:
                parts.append(f"{modified}M")
            if deleted:
                parts.append(f"{deleted}D")
            return "+".join(parts) if parts else "clean"
        return "clean"
    elif repo_type == "git":
        # git status --short shows "XY filename" for each change
        lines = [l for l in status_output.strip().split("\n") if l.strip()]
        if not lines:
            return "clean"
        # Count modified, added, deleted
        modified = sum(1 for l in lines if l[0:2] in ("M ", "MM", " M"))
        added = sum(1 for l in lines if l[0:2] in ("A ", "AM"))
        deleted = sum(1 for l in lines if l[0:2] in ("D ", "DM"))
        parts = []
        if modified:
            parts.append(f"{modified}M")
        if added:
            parts.append(f"{added}A")
        if deleted:
            parts.append(f"{deleted}D")
        return "+".join(parts) if parts else "clean"
    return "clean"


def format_results(results, completed_at, elapsed_time, is_partial=False,
                   tree_mode=False, text_symbols=False):
    """Format results as a compact tree."""

    # ANSI colors
    COLORS = {
        "reset": "\033[0m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "red": "\033[31m",
        "dim": "\033[2m",
    }

    def colorize(text, color):
        """Add ANSI color to text."""
        return f"{COLORS[color]}{text}{COLORS['reset']}"

    lines = []

    if is_partial:
        lines.append(colorize(f"(listening @ {elapsed_time:.1f}s)", "dim"))
    else:
        lines.append(colorize(f"(done @ {elapsed_time:.1f}s)", "dim"))

    # Sort all repos by path
    sorted_repos = sorted(results.items())

    # Build tree structure if tree_mode
    if tree_mode:
        # Group by parent directory
        from collections import defaultdict
        tree = defaultdict(list)
        for path, info in sorted_repos:
            parts = path.split("/")
            if len(parts) > 1:
                parent = "/".join(parts[:-1])
                tree[parent].append((parts[-1], info))
            else:
                tree["."].append((path, info))

        # Render tree
        parents = sorted(tree.keys())
        for parent_idx, parent in enumerate(parents):
            if parent != ".":
                is_parent_last = parent_idx == len(parents) - 1
                parent_prefix = "└── " if is_parent_last else "├── "
                lines.append(colorize(f"{parent_prefix}{parent}/", "dim"))
                child_prefix_base = "    " if is_parent_last else "│   "
            else:
                parent_prefix = ""
                child_prefix_base = ""

            repos = tree[parent]
            for child_idx, (name, info) in enumerate(repos):
                is_last_child = child_idx == len(repos) - 1
                child_prefix = child_prefix_base + ("└── " if is_last_child else "├── ")

                repo_type = info.get("type", "?")
                type_mark = _get_type_mark(repo_type, text_symbols)
                diff_stat = get_diff_stat(info.get("status"), repo_type)
                commit_date = info.get("commit_date", "")

                # If date fetch failed, status is unreliable—show error instead
                if info.get("date_error"):
                    err = info["date_error"]
                    status_display = colorize(f"[{err}]", "red")
                    lines.append(f"{child_prefix}{name} {type_mark} {status_display}")
                else:
                    # Color based on status
                    if info["error"] == "timeout":
                        diff_stat = colorize("timeout", "yellow")
                    elif info["error"]:
                        diff_stat = colorize(f"error: {info['error'][:15]}", "red")
                    elif diff_stat == "clean":
                        diff_stat = colorize("clean", "green")
                    else:
                        diff_stat = colorize(diff_stat, "yellow")

                    # Add commit date if available
                    date_str = f" {commit_date}" if commit_date else ""
                    lines.append(f"{child_prefix}{name} {type_mark} {diff_stat}{date_str}")
    else:
        # Flat mode
        for i, (path, info) in enumerate(sorted_repos):
            is_last = i == len(sorted_repos) - 1
            prefix = "└── " if is_last else "├── "

            repo_type = info.get("type", "?")
            type_mark = _get_type_mark(repo_type, text_symbols)
            diff_stat = get_diff_stat(info.get("status"), repo_type)
            commit_date = info.get("commit_date", "")

            # If date fetch failed, status is unreliable—show error instead
            if info.get("date_error"):
                err = info["date_error"]
                status_display = colorize(f"[{err}]", "red")
                lines.append(f"{prefix}{path} {type_mark} {status_display}")
            else:
                # Color based on status
                if info["error"] == "timeout":
                    diff_stat = colorize("timeout", "yellow")
                elif info["error"]:
                    diff_stat = colorize(f"error: {info['error'][:15]}", "red")
                elif diff_stat == "clean":
                    diff_stat = colorize("clean", "green")
                else:
                    diff_stat = colorize(diff_stat, "yellow")

                # Add commit date if available
                date_str = f" {commit_date}" if commit_date else ""
                lines.append(f"{prefix}{path} {type_mark} {diff_stat}{date_str}")

    return "\n".join(lines)


def _get_type_mark(repo_type, text_mode=False):
    """Get type symbol or text."""
    if text_mode:
        return {
            "jj": "[jj]",
            "git": "[git]",
        }.get(repo_type, "[?]")
    else:
        return {
            "jj": "●",
            "git": "■",
        }.get(repo_type, "○")


def save_cache(results, start_dir):
    """Save results to cache file rooted at ~/."""
    cache_file = get_cache_path(start_dir)
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    cache_data = {
        "timestamp": datetime.now().isoformat(),
        "scanned_from": str(start_dir),
        "results": {k: v for k, v in results.items()},
    }

    with open(cache_file, "w") as f:
        json.dump(cache_data, f, indent=2)


def vcs_tree(start_dir=".", tree_mode=False, text_symbols=False):
    """Main function: scan repos with stall-detection display timing."""
    start_dir = Path(start_dir).resolve()
    start_time = time.time()

    print(f"Scanning from {start_dir}...", file=sys.stderr)

    results = {}
    completed_at = {}
    completion_times = []  # Track when completions occur

    # Run repos in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        roots = find_repo_roots(start_dir)
        tasks = []

        for jj_root in roots["jj"]:
            tasks.append(executor.submit(get_jj_status, jj_root, REPO_TIMEOUT))
            tasks.append(("jj", jj_root))

        for git_root in roots["git"]:
            tasks.append(executor.submit(get_git_status, git_root, REPO_TIMEOUT))
            tasks.append(("git", git_root))

        # Track which futures map to which repos
        future_to_repo = {}
        futures_list = []
        for i, task in enumerate(tasks):
            if hasattr(task, "result"):  # It's a future
                futures_list.append(task)
                if i + 1 < len(tasks) and isinstance(tasks[i + 1], tuple):
                    future_to_repo[task] = tasks[i + 1]

        # Stall-detection loop: display when no new completions for 2 seconds
        display_shown = False
        last_completion_time = start_time
        stall_threshold = 2.0  # seconds

        while time.time() - start_time < BACKGROUND_WAIT:
            elapsed = time.time() - start_time
            now = time.time()

            # Collect any completed tasks
            for future in futures_list:
                repo_info = future_to_repo.get(future)
                if repo_info and future.done():
                    repo_type, repo_path = repo_info
                    rel_path = str(repo_path.relative_to(start_dir))
                    if rel_path == ".":
                        rel_path = "."

                    # Skip if already processed
                    if rel_path in results:
                        continue

                    try:
                        result = future.result()
                        results[rel_path] = result
                        completed_at[rel_path] = elapsed
                        last_completion_time = now
                        completion_times.append(now)
                    except Exception as e:
                        results[rel_path] = {
                            "type": repo_type,
                            "status": None,
                            "commit_date": None,
                            "date_error": None,
                            "error": str(e)[:50],
                        }

            # Check for stall: if no completions for stall_threshold and we have some results
            if not display_shown and results and (now - last_completion_time) >= stall_threshold:
                print(format_results(results, completed_at, elapsed, is_partial=True,
                                    tree_mode=tree_mode, text_symbols=text_symbols))

                # Count repos still running
                still_running = sum(1 for f in futures_list if not f.done())
                print(f"[collecting in background: {still_running} repos...]", file=sys.stderr)
                display_shown = True

            # Check if all done
            if all(f.done() for f in futures_list):
                break

            time.sleep(0.1)

        # Collect any final results
        for future in futures_list:
            if not future.done():
                try:
                    future.cancel()
                except Exception:
                    pass

    elapsed = time.time() - start_time

    # Save to cache
    save_cache(results, start_dir)

    # If nothing was displayed yet (no stall detected, very fast completion),
    # show the results now. Otherwise keep silent and let background collection happen.
    if not display_shown:
        print(format_results(results, completed_at, elapsed, is_partial=False,
                            tree_mode=tree_mode, text_symbols=text_symbols))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Parallel VCS repo scanner with stall-detection display.")
    parser.add_argument("path", nargs="?", default=".", help="Directory to scan (default: .)")
    parser.add_argument("--flat", action="store_true", help="Flat mode (no directory hierarchy)")
    parser.add_argument("--text-symbols", action="store_true", help="Spell out repo types (jj, git) instead of unicode")

    args = parser.parse_args()
    vcs_tree(args.path, tree_mode=not args.flat, text_symbols=args.text_symbols)
