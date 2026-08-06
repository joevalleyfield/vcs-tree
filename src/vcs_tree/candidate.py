"""Supported factual projection for current workspace review evidence."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .models import SnapshotEnvelope
from .snapshot_schema import parse_snapshot


def _id(value: Any) -> str | None:
    if isinstance(value, Mapping):
        value = value.get("value")
    return str(value) if value else None


def _path(repository: Mapping[str, Any], root: str) -> str | None:
    locations = repository.get("locations", ())
    raw = locations[0].get("path") if locations and isinstance(locations[0], Mapping) else None
    if not isinstance(raw, str):
        return None
    try:
        return str(Path(raw).resolve().relative_to(Path(root).resolve())) or "."
    except ValueError:
        return raw


def _outcomes(repository: Mapping[str, Any]) -> dict[str, Any]:
    collection = repository.get("collection", {})
    return {
        str(name): {
            "state": value.get("state", "unknown"),
            "errors": list(value.get("errors", ())),
        }
        for name, value in collection.items()
        if isinstance(value, Mapping)
    }


def _workspace(workspace: Mapping[str, Any], *, max_entries: int) -> dict[str, Any]:
    working_copy = workspace.get("working_copy", {})
    if not isinstance(working_copy, Mapping):
        working_copy = {}
    entries = list(working_copy.get("entries", ()))
    source_limit = working_copy.get("entries_limit", max_entries)
    try:
        limit = max(0, min(int(source_limit), max_entries))
    except (TypeError, ValueError):
        limit = max_entries
    truncated = bool(working_copy.get("entries_truncated")) or len(entries) > limit
    current = workspace.get("current") or working_copy.get("current") or {}
    parents = workspace.get("parents") or working_copy.get("parents") or ()
    result = {
        "workspace_key": workspace.get("workspace_key", workspace.get("path", "")),
        "role": workspace.get("role", "unknown"),
        "current": {
            "object_id": _id(current.get("object_id")),
            "change_id": current.get("change_id"),
        },
        "parents": [_id(parent) for parent in parents if _id(parent)],
        "working_copy": {
            "recorded_state": working_copy.get(
                "recorded_state", working_copy.get("state", "unknown")
            ),
            "freshness": working_copy.get("freshness", "unknown"),
            "entries": entries[:limit],
            "entries_limit": limit,
            "entries_truncated": truncated,
            "entries_total": None if truncated else len(entries),
            "outcome": working_copy.get("outcome", {"state": "unknown", "errors": []}),
            "entries_outcome": working_copy.get(
                "entries_outcome", {"state": "unknown", "errors": []}
            ),
            "refresh": working_copy.get("refresh", {"state": "unknown", "errors": []}),
        },
    }
    return result


def project_current_workspaces(
    snapshot: SnapshotEnvelope | Mapping[str, Any], *, max_entries: int = 256
) -> dict[str, Any]:
    """Project retained snapshot facts without adding review conclusions."""
    if max_entries < 0:
        raise ValueError("max_entries must be non-negative")
    document = snapshot if isinstance(snapshot, SnapshotEnvelope) else parse_snapshot(snapshot)
    root = str(document.scan.get("root", ""))
    repositories = []
    for repository in document.repositories:
        workspaces = repository.get("workspaces", ())
        if not workspaces:
            continue
        repositories.append(
            {
                "repository_key": repository.get("repository_key"),
                "path": _path(repository, root),
                "mode": repository.get("mode", "unknown"),
                "workspace_family": repository.get(
                    "workspace_family",
                    {
                        "family_id": None,
                        "kind": "jj_operation_store",
                        "source": "config-id",
                        "outcome": {"state": "unknown", "errors": []},
                    },
                ),
                "workspaces": [
                    _workspace(workspace, max_entries=max_entries)
                    for workspace in workspaces
                    if isinstance(workspace, Mapping)
                ],
                "completeness": _outcomes(repository),
            }
        )
    repositories.sort(
        key=lambda item: (str(item.get("path", "")), str(item.get("repository_key", "")))
    )
    return {
        "schema": "vcs-tree.current-workspace-evidence",
        "schema_version": 1,
        "snapshot": {
            "snapshot_id": document.snapshot_id,
            "generation": document.history_store.generation,
            "captured_at": document.captured_at,
        },
        "scope": {"root": root},
        "repositories": repositories,
    }


__all__ = ["project_current_workspaces"]
