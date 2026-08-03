"""Human and machine renderers for the recurring movement pulse."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


def render_json(document: Mapping[str, Any]) -> str:
    return json.dumps(document, indent=2, sort_keys=True)


def render_summary(document: Mapping[str, Any]) -> str:
    target = document.get("target_snapshot", {})
    scope = document.get("scope", {}).get("root", ".")
    outcome = document.get("outcome", {}).get("state", "unknown")
    comparison = document.get("comparison", {})
    if comparison.get("state") == "baseline_created":
        lines = [
            f"pulse {scope}: baseline generation {target.get('generation')} captured ({outcome})"
        ]
        lines.append("no comparable prior snapshot; no movement comparison was made")
    else:
        lines = [
            f"pulse {scope}: generation {comparison.get('source_generation')} -> "
            f"{target.get('generation')} ({outcome})"
        ]
        repositories = document.get("repositories", ())
        for repository in repositories:
            events = [
                event
                for event in repository.get("events", ())
                if event.get("event") != "comparison_incomplete"
            ]
            if not events:
                continue
            lines.append(f"{repository.get('path')} [{repository.get('mode') or 'unknown'}]")
            for event in events:
                details = event.get("details", {})
                suffix = ""
                if isinstance(details, Mapping) and details.get("state"):
                    suffix = f" ({details['state']})"
                lines.append(f"  {event.get('event')}{suffix}")
            for task_event in repository.get("task_path_events", ()):
                task_path = task_event.get("new_path") or task_event.get("old_path")
                lines.append(f"  task path: {task_event.get('event')} {task_path}")
        summary = document.get("summary", {})
        noops = summary.get("no_op_repositories", 0)
        if noops:
            lines.append(f"{noops} repositories with no observed movement")
    summary = document.get("summary", {})
    lines.append(
        f"warnings: {summary.get('new_warnings', 0)} new, "
        f"{summary.get('persistent_warnings', 0)} persistent, "
        f"{summary.get('recovered_warnings', 0)} recovered"
    )
    return "\n".join(lines)


def render_audit(document: Mapping[str, Any]) -> str:
    lines = [render_summary(document), "", "audit:"]
    for repository in document.get("repositories", ()):
        lines.append(json.dumps(repository, sort_keys=True))
    if document.get("warnings"):
        lines.append("warnings:")
        lines.extend(json.dumps(item, sort_keys=True) for item in document["warnings"])
    return "\n".join(lines)


def render(document: Mapping[str, Any], format_name: str) -> str:
    if format_name == "json":
        return render_json(document)
    if format_name == "audit":
        return render_audit(document)
    return render_summary(document)


__all__ = ["render", "render_audit", "render_json", "render_summary"]
