"""Version-aware snapshot parsing and conservative comparison normalization."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Union

from .models import (
    V2_REPOSITORY_COMPONENTS,
    CollectionState,
    ContractError,
    ObservationOutcome,
    SnapshotEnvelope,
    SnapshotEnvelopeV2,
)

SnapshotDocument = Union[SnapshotEnvelope, SnapshotEnvelopeV2]


def parse_snapshot(value: Any) -> SnapshotDocument:
    """Parse a supported snapshot mapping without migrating its representation."""
    if not isinstance(value, Mapping):
        raise ContractError("snapshot document must be an object")
    if value.get("schema") != SnapshotEnvelope.schema:
        raise ContractError(f"expected schema {SnapshotEnvelope.schema!r}")
    version = value.get("schema_version")
    if version == SnapshotEnvelope.schema_version:
        return SnapshotEnvelope.from_dict(value)
    if version == SnapshotEnvelopeV2.schema_version:
        return SnapshotEnvelopeV2.from_dict(value)
    raise ContractError(f"unsupported {SnapshotEnvelope.schema} schema version")


def _copy(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True))


def _unknown() -> dict[str, Any]:
    return {"state": "unknown", "time_precision": "unknown", "errors": []}


def _not_requested() -> dict[str, Any]:
    return {"state": "not_requested", "time_precision": "unknown", "errors": []}


def _v1_outcome(value: Any, captured_at: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or value.get("state") not in {
        state.value for state in CollectionState
    }:
        return _unknown()
    result = {
        "state": value["state"],
        "time_precision": "snapshot",
        "errors": _copy(value.get("errors", [])),
    }
    if value["state"] != CollectionState.NOT_REQUESTED.value:
        result["attempted_at"] = captured_at
    return result


def _v2_outcome(value: Any) -> dict[str, Any]:
    result = ObservationOutcome.from_dict(value).to_dict()
    result["time_precision"] = "component" if "attempted_at" in result else "unknown"
    return result


def _v1_component(repository: Mapping[str, Any], name: str, captured_at: str) -> dict[str, Any]:
    mode = repository.get("mode")
    collection = repository.get("collection")
    collection = collection if isinstance(collection, Mapping) else {}
    if name == "identity":
        return _v1_outcome(collection.get("identity"), captured_at)
    if name == "git_worktrees":
        if mode == "git":
            return _v1_outcome(collection.get("workspaces"), captured_at)
        return _not_requested() if mode == "jj" else _unknown()
    if name == "jj_workspaces":
        if mode in {"jj", "colocated"}:
            return _v1_outcome(collection.get("workspaces"), captured_at)
        return _not_requested()
    if name == "git_refs":
        if mode in {"git", "colocated"}:
            return _v1_outcome(collection.get("refs"), captured_at)
        return _not_requested()
    if name == "jj_bookmarks":
        if mode in {"jj", "colocated"}:
            hints = repository.get("publication_hints")
            outcomes = hints.get("outcomes", {}) if isinstance(hints, Mapping) else {}
            return _v1_outcome(outcomes.get("jj_bookmarks"), captured_at)
        return _not_requested()
    if name == "jj_visible_heads":
        if mode in {"jj", "colocated"}:
            graph = repository.get("change_graph")
            return _v1_outcome(
                graph.get("outcome") if isinstance(graph, Mapping) else None, captured_at
            )
        return _not_requested()
    if name == "git_history":
        if mode in {"git", "colocated"}:
            return _v1_outcome(collection.get("history"), captured_at)
        return _not_requested()
    if name == "jj_history":
        if mode in {"jj", "colocated"}:
            graph = repository.get("change_graph")
            return _v1_outcome(
                graph.get("outcome") if isinstance(graph, Mapping) else None, captured_at
            )
        return _not_requested()
    if name == "path_evidence":
        return _not_requested()
    raise ContractError(f"unsupported normalized component: {name}")


def _normalize_v1_workspace(
    workspace: Mapping[str, Any], repository: Mapping[str, Any], captured_at: str
) -> dict[str, Any]:
    collection = repository.get("collection")
    collection = collection if isinstance(collection, Mapping) else {}
    working_copy = workspace.get("working_copy")
    working_copy = working_copy if isinstance(working_copy, Mapping) else {}
    state = working_copy.get("state", "unknown")
    if state not in {"clean", "dirty", "conflicted", "unknown", "unreadable"}:
        state = "unknown"
    entries_outcome = working_copy.get("entries_outcome")
    return {
        "workspace_key": workspace.get("workspace_key", workspace.get("path", "unknown")),
        "recorded_state": state,
        "outcome": _v1_outcome(collection.get("workspaces"), captured_at),
        "refresh": _unknown(),
        "freshness": "unknown",
        "entries_outcome": _v1_outcome(entries_outcome, captured_at),
        "entries": _copy(working_copy.get("entries", [])),
    }


def normalize_snapshot(value: SnapshotDocument | Mapping[str, Any]) -> dict[str, Any]:
    """Project v1 and v2 snapshots onto one conservative evidence vocabulary."""
    document = (
        value
        if isinstance(value, (SnapshotEnvelope, SnapshotEnvelopeV2))
        else parse_snapshot(value)
    )
    repositories = []
    for repository in document.repositories:
        if isinstance(document, SnapshotEnvelopeV2):
            components = {
                name: _v2_outcome(repository["collection"][name])
                for name in V2_REPOSITORY_COMPONENTS
            }
            workspaces = [_copy(item) for item in repository["workspaces"]]
        else:
            components = {
                name: _v1_component(repository, name, document.captured_at)
                for name in V2_REPOSITORY_COMPONENTS
            }
            workspaces = [
                _normalize_v1_workspace(item, repository, document.captured_at)
                for item in repository.get("workspaces", [])
                if isinstance(item, Mapping)
            ]
        repositories.append(
            {
                "repository_key": repository.get("repository_key"),
                "mode": repository.get("mode"),
                "components": components,
                "workspaces": workspaces,
                "facts": _copy(repository),
            }
        )
    return {
        "snapshot_id": document.snapshot_id,
        "captured_at": document.captured_at,
        "source_schema_version": document.schema_version,
        "repositories": repositories,
    }


def component_comparison(
    before_repository: Mapping[str, Any],
    after_repository: Mapping[str, Any],
    component: str,
) -> dict[str, str]:
    """Return the explicit boundary for one normalized component comparison."""
    if component not in V2_REPOSITORY_COMPONENTS:
        raise ContractError(f"unsupported normalized component: {component}")
    before = before_repository.get("components", {}).get(component, {})
    after = after_repository.get("components", {}).get(component, {})
    before_state = before.get("state", "unknown")
    after_state = after.get("state", "unknown")
    state = "complete" if before_state == after_state == "complete" else "comparison_incomplete"
    return {"state": state, "before_state": before_state, "after_state": after_state}


__all__ = [
    "SnapshotDocument",
    "component_comparison",
    "normalize_snapshot",
    "parse_snapshot",
]
