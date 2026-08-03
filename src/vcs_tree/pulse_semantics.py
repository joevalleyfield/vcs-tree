"""Deterministic, factual semantics derived from an enriched history pulse."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

_AREAS = ("open", "closed")
_STATUSES = {"added", "deleted", "modified", "type_changed", "renamed", "copied"}


def _area(path: Any) -> str:
    """Return the task area for a repository-relative, case-sensitive path."""
    if not isinstance(path, str) or path.startswith("/") or "\\" in path:
        return "outside"
    for area in _AREAS:
        prefix = f"tasks/{area}/"
        if path.startswith(prefix) and path.endswith(".md") and len(path) > len(prefix) + 3:
            return area
    return "outside"


def _entry_event(
    entry: Mapping[str, Any], group: Mapping[str, Any], event: str, old_path: Any, new_path: Any
) -> dict[str, Any]:
    result = {
        "event": event,
        "change": dict(entry),
        "commit_id": group.get("object_id", entry.get("object_id")),
        "parent_id": group.get("parent_id", entry.get("parent_id")),
        "old_path": old_path,
        "new_path": new_path,
        "from_area": _area(old_path),
        "to_area": _area(new_path),
    }
    return result


def classify_task_paths(path_evidence: Iterable[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    """Classify native changed-path entries into the pulse task vocabulary.

    ``path_evidence`` is the parent-relative group shape emitted by the
    enrichment layer. Separate add/delete entries are deliberately preserved.
    """
    events: list[dict[str, Any]] = []
    for group in path_evidence:
        if not isinstance(group, Mapping):
            continue
        for raw in group.get("paths", ()):
            if not isinstance(raw, Mapping):
                continue
            entry = dict(raw)
            status = str(entry.get("status", "")).lower()
            if status not in _STATUSES:
                continue
            path = entry.get("path")
            old = entry.get("old_path", entry.get("from_path"))
            if status == "added" and _area(path) != "outside":
                events.append(_entry_event(entry, group, "task_path_added", None, path))
            elif status == "deleted" and _area(path) != "outside":
                events.append(_entry_event(entry, group, "task_path_removed", path, None))
            elif status in {"modified", "type_changed"} and _area(path) != "outside":
                events.append(_entry_event(entry, group, "task_path_modified", path, path))
            elif status == "renamed":
                destination = path
                source = old
                source_area, destination_area = _area(source), _area(destination)
                if source_area != "outside" or destination_area != "outside":
                    kind = (
                        "task_path_moved"
                        if source_area in _AREAS
                        and destination_area in _AREAS
                        and source_area != destination_area
                        else "task_path_renamed"
                    )
                    events.append(_entry_event(entry, group, kind, source, destination))
            elif status == "copied":
                source = old
                destination = path
                if _area(source) != "outside" or _area(destination) != "outside":
                    events.append(
                        _entry_event(entry, group, "task_path_copied", source, destination)
                    )
    return tuple(
        sorted(
            events,
            key=lambda item: (
                str(item.get("commit_id") or ""),
                str(item.get("parent_id") or ""),
                item["event"],
                str(item.get("old_path") or ""),
                str(item.get("new_path") or ""),
            ),
        )
    )


def warning_key(warning: Mapping[str, Any] | str) -> str:
    """Build the inspectable stable warning identity."""
    if isinstance(warning, str):
        return warning
    if warning.get("warning_key"):
        return str(warning["warning_key"])
    fields = (
        warning.get("repository_key", "@scan"),
        warning.get("component", "scan"),
        warning.get("kind", "warning"),
        warning.get("stage", "-"),
        warning.get("affected_event_class", warning.get("evidence_class", "-")),
    )
    return "|".join(str(value or "-") for value in fields)


def classify_warning_lifecycles(
    source: Iterable[Mapping[str, Any] | str] = (),
    target: Iterable[Mapping[str, Any] | str] = (),
    comparison_only: Iterable[Mapping[str, Any] | str] = (),
) -> tuple[dict[str, Any], ...]:
    """Compare normalized warning sets and report new/persistent/recovered."""

    def normalize(items: Iterable[Mapping[str, Any] | str]) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for item in items:
            record = {"warning_key": warning_key(item)} if isinstance(item, str) else dict(item)
            key = warning_key(record)
            record["warning_key"] = key
            result[key] = record
        return result

    before, after = normalize(source), normalize(target)
    records: list[dict[str, Any]] = []
    for key in sorted(set(before) | set(after)):
        if key in before and key in after:
            state, detail = "persistent", after[key]
        elif key in after:
            state, detail = "new", after[key]
        else:
            state, detail = "recovered", before[key]
        records.append(
            {
                **detail,
                "warning_key": key,
                "lifecycle": state,
                "source_present": key in before,
                "target_present": key in after,
            }
        )
    for item in normalize(comparison_only).values():
        key = item["warning_key"]
        records.append(
            {
                **item,
                "warning_key": key,
                "lifecycle": "new",
                "source_present": False,
                "target_present": False,
                "comparison_only": True,
            }
        )
    return tuple(sorted(records, key=lambda item: (item["lifecycle"], item["warning_key"])))


# Short aliases make the contract convenient for downstream pulse assembly.
task_path_events = classify_task_paths
warning_lifecycles = classify_warning_lifecycles

__all__ = [
    "classify_task_paths",
    "classify_warning_lifecycles",
    "task_path_events",
    "warning_key",
    "warning_lifecycles",
]
