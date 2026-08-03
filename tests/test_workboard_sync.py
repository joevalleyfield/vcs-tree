from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "tasks" / "scripts" / "sync_workboard.py"
SPEC = importlib.util.spec_from_file_location("sync_workboard", SCRIPT)
assert SPEC and SPEC.loader
sync_workboard = importlib.util.module_from_spec(SPEC)
sys.modules["sync_workboard"] = sync_workboard
SPEC.loader.exec_module(sync_workboard)


def task(tmp_path: Path, name: str, body: str = "") -> sync_workboard.Task:
    path = tmp_path / f"{name}.md"
    path.write_text(body or f"# {name}\n\n## Objective\n\nDo {name}.\n", encoding="utf-8")
    return sync_workboard.Task(name, sync_workboard._objective(path.read_text(), name), path)


def test_objective_prefers_explicit_section_and_falls_back_to_intro(tmp_path: Path) -> None:
    explicit = task(
        tmp_path, "260803-explicit", "# Explicit\n\n## Goal\n\n- Keep the queue honest.\n"
    )
    intro = task(tmp_path, "260803-intro", "# Intro\n\nKeep this prose.\n\n## Acceptance\n")

    assert explicit.objective == "Keep the queue honest."
    assert intro.objective == "Keep this prose."


def test_read_tasks_ignores_inbox_and_skips_unreadable_directory(tmp_path: Path) -> None:
    (tmp_path / "inbox.md").write_text("- [ ] item", encoding="utf-8")
    task(tmp_path, "260803-one")

    assert [item.task_id for item in sync_workboard.read_tasks(tmp_path)] == ["260803-one"]
    assert sync_workboard.read_tasks(tmp_path / "missing") == []


def test_renderers_cover_empty_and_recent_cases(tmp_path: Path) -> None:
    one = task(tmp_path, "260803-one")
    two = task(tmp_path, "260804-two")

    assert sync_workboard.render_open([]) == "- _No open tasks._"
    assert "260803-one" in sync_workboard.render_open([one])
    assert sync_workboard.render_closed([]) == "- _No closed tasks._"
    assert "260804-two" in sync_workboard.render_closed([one, two], limit=1)


def test_sync_content_replaces_only_marked_blocks_and_is_idempotent() -> None:
    content = """> **Last Sync:** old

## 1. Open Queue
<!-- WORKBOARD:OPEN:START -->
stale
<!-- WORKBOARD:OPEN:END -->

## 2. Recent Closures
<!-- WORKBOARD:CLOSED:START -->
stale
<!-- WORKBOARD:CLOSED:END -->

manual prose
"""
    open_task = sync_workboard.Task("260803-open", "Open objective", Path("open.md"))
    closed_task = sync_workboard.Task("260802-closed", "Closed objective", Path("closed.md"))

    updated = sync_workboard.sync_content(content, [open_task], [closed_task], "2026-08-03")

    assert "`260803-open` — Open objective" in updated
    assert "`260802-closed` — Closed objective" in updated
    assert "manual prose" in updated
    assert sync_workboard.sync_content(updated, [open_task], [closed_task], "2026-08-03") == updated


def test_sync_content_leaves_unmarked_board_unchanged() -> None:
    content = "> **Last Sync:** old\n\nmanual\n"
    assert sync_workboard.sync_content(content, [], [], "2026-08-03") == content
