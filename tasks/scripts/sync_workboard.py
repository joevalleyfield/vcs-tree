#!/usr/bin/env python3
"""Synchronize the generated parts of ``tasks/WORKBOARD.md``.

Task files are the source of truth: files in ``tasks/open`` are queue entries,
and files in ``tasks/closed`` are historical entries.  Only marker-delimited
sections are rewritten; prose outside those sections is left untouched.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TASKS = ROOT / "tasks"
WORKBOARD = TASKS / "WORKBOARD.md"

OPEN_START = "<!-- WORKBOARD:OPEN:START -->"
OPEN_END = "<!-- WORKBOARD:OPEN:END -->"
CLOSED_START = "<!-- WORKBOARD:CLOSED:START -->"
CLOSED_END = "<!-- WORKBOARD:CLOSED:END -->"
SYNC_RE = re.compile(r"(^> \*\*Last Sync:\*\* ).*$", re.MULTILINE)


@dataclass(frozen=True)
class Task:
    task_id: str
    objective: str
    path: Path


def _sort_key(task: Task) -> tuple[int, str]:
    match = re.match(r"^(\d+)", task.task_id)
    return (int(match.group(1)) if match else 0, task.task_id)


def _section(lines: list[str], names: tuple[str, ...]) -> str:
    for index, line in enumerate(lines):
        heading = line.strip().casefold()
        if not heading.startswith("## ") or heading[3:] not in {name.casefold() for name in names}:
            continue
        end = next(
            (offset for offset, candidate in enumerate(lines[index + 1 :], index + 1)
             if candidate.strip().startswith("## ")),
            len(lines),
        )
        return "\n".join(lines[index + 1 : end]).strip()
    return ""


def _objective(content: str, task_id: str) -> str:
    lines = content.splitlines()
    explicit = _section(lines, ("Objective", "Goal"))
    if explicit:
        value = explicit
    else:
        value = ""
        seen_title = False
        prose: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not seen_title:
                if stripped.startswith("# "):
                    seen_title = True
                continue
            if stripped.startswith("## "):
                break
            if stripped and not any(stripped.startswith(prefix) for prefix in (
                "Filed as:", "FKA:", "AKA:", "Legacy index:", "keywords:",
                "Parent:", "Depends on:", "Blocks:", "Blocked by:", "Related:",
            )):
                prose.append(stripped)
            elif prose and not stripped:
                break
        value = " ".join(prose)
    value = " ".join(
        re.sub(r"^\s*(?:[-*]\s+|\d+\.\s+)", "", line).strip()
        for line in value.splitlines()
        if line.strip()
    )
    if not value:
        value = task_id.replace("-", " ")
    return value[:180] + ("..." if len(value) > 180 else "")


def read_tasks(directory: Path) -> list[Task]:
    tasks: list[Task] = []
    if not directory.exists():
        return tasks
    for path in directory.glob("*.md"):
        if path.name == "inbox.md":
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        tasks.append(Task(path.stem, _objective(content, path.stem), path))
    return sorted(tasks, key=_sort_key)


def render_open(tasks: list[Task]) -> str:
    if not tasks:
        return "- _No open tasks._"
    return "\n".join(f"- `{task.task_id}` — {task.objective}" for task in tasks)


def render_closed(tasks: list[Task], limit: int = 8) -> str:
    recent = sorted(tasks, key=_sort_key, reverse=True)[:limit]
    if not recent:
        return "- _No closed tasks._"
    return "\n".join(f"- `{task.task_id}` — {task.objective}" for task in recent)


def replace_block(content: str, start: str, end: str, replacement: str) -> str:
    start_index = content.find(start)
    end_index = content.find(end)
    if start_index < 0 or end_index < 0 or end_index < start_index:
        return content
    return content[: start_index + len(start)] + "\n" + replacement + "\n" + content[end_index:]


def sync_content(content: str, open_tasks: list[Task], closed_tasks: list[Task], date: str) -> str:
    if any(marker not in content for marker in (OPEN_START, OPEN_END, CLOSED_START, CLOSED_END)):
        return content
    updated = replace_block(content, OPEN_START, OPEN_END, render_open(open_tasks))
    updated = replace_block(updated, CLOSED_START, CLOSED_END, render_closed(closed_tasks))
    return SYNC_RE.sub(rf"\g<1>{date}", updated, count=1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report drift without writing")
    args = parser.parse_args()
    if not WORKBOARD.exists():
        raise SystemExit(f"workboard not found: {WORKBOARD}")
    before = WORKBOARD.read_text(encoding="utf-8")
    after = sync_content(before, read_tasks(TASKS / "open"), read_tasks(TASKS / "closed"), date.today().isoformat())
    if args.check:
        if after != before:
            print("workboard is out of sync")
            return 1
        print("workboard is in sync")
        return 0
    if after != before:
        WORKBOARD.write_text(after, encoding="utf-8")
    print(f"synced {len(read_tasks(TASKS / 'open'))} open and {len(read_tasks(TASKS / 'closed'))} closed tasks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
