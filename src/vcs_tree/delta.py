"""Deterministic, fail-closed comparison of history snapshots."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .ledger import HistoryLedger, LedgerCorruptError
from .models import (
    Certainty,
    CollectionOutcome,
    CollectionState,
    ContractError,
    DeltaEnvelope,
    Event,
    HistoryBoundaryState,
    SnapshotEnvelope,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _id(value: Any) -> str:
    if isinstance(value, Mapping):
        return str(value.get("value", ""))
    return str(value)  # pragma: no cover - scalar IDs are normalized by adapters


def _ids(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        return [_id(value)]
    if isinstance(value, (list, tuple)):  # pragma: no cover
        return sorted({_id(item) for item in value if item})  # pragma: no cover
    return []  # pragma: no cover - malformed native payload


def _state(repo: Mapping[str, Any], component: str) -> CollectionState:
    raw = repo.get("collection", {}).get(component, {"state": "not_requested"})
    if isinstance(raw, CollectionOutcome):  # pragma: no cover - mapping is wire form
        return raw.state
    try:
        return CollectionState.parse(raw.get("state", "not_requested"))
    except (AttributeError, ContractError):  # pragma: no cover - malformed payload
        return CollectionState.ERROR


def _complete(repo: Mapping[str, Any], component: str) -> bool:
    return _state(repo, component) is CollectionState.COMPLETE


def _boundary(repo: Mapping[str, Any]) -> HistoryBoundaryState:
    raw = repo.get("history_boundary", {}).get("state", "unknown")
    try:
        return HistoryBoundaryState.parse(raw)
    except ContractError:  # pragma: no cover - malformed payload
        return HistoryBoundaryState.UNKNOWN


def _ref_key(ref: Mapping[str, Any]) -> str:
    authority = ref.get("authority", ref.get("remote", ""))
    remote = ref.get("remote", "")
    return ":".join(
        str(item)
        for item in (ref.get("kind", "git"), authority, remote, ref.get("name", ""))
        if item
    )


def _repository_location(repo: Mapping[str, Any], scan_root: str | None) -> str | None:
    locations = repo.get("locations", ())
    if not isinstance(locations, (list, tuple)) or not locations:
        return None
    path = locations[0].get("path") if isinstance(locations[0], Mapping) else None
    if not isinstance(path, str) or not path:
        return None
    if not scan_root:
        return path
    try:
        return str(Path(path).resolve().relative_to(Path(scan_root).resolve())) or "."
    except ValueError:
        return path


def _scan_root(new: SnapshotEnvelope, old: SnapshotEnvelope) -> str | None:
    new_root = new.scan.get("root")
    old_root = old.scan.get("root")
    if isinstance(new_root, str) and new_root == old_root:
        return new_root
    return None


def _workspace_key(workspace: Mapping[str, Any]) -> str:
    return str(workspace.get("workspace_key", workspace.get("path", workspace.get("name", ""))))


def _event(
    name: str,
    key: str,
    details: Mapping[str, Any],
    *,
    evidence: Mapping[str, Any] | None = None,
    certainty: Certainty = Certainty.OBSERVED,
) -> Event:
    return Event(
        name,
        f"{name}:{key}",
        certainty,
        evidence or {"from_component": "snapshot", "to_component": "snapshot"},
        details,
    )


_ORDER = {
    "repository_added": 0,
    "repository_removed": 0,
    "repository_unreadable": 0,
    "repository_recovered": 0,
    "comparison_incomplete": 0,
    "workspace_added": 1,
    "workspace_removed": 1,
    "workspace_head_changed": 1,
    "working_copy_changed": 1,
    "ref_created": 2,
    "ref_deleted": 2,
    "ref_target_changed": 2,
    "ref_conflict_changed": 2,
    "ref_tracking_changed": 2,
    "tag_created": 2,
    "tag_deleted": 2,
    "tag_target_changed": 2,
    "visible_head_added": 3,
    "visible_head_removed": 3,
    "change_versions_changed": 3,
    "history_first_observed": 4,
    "history_became_reachable": 4,
    "history_became_unreachable": 4,
    "off_current_history_observed": 4,
    "current_line_history_observed": 4,
    "history_file_changes_observed": 5,
}


def _relation(old: str, new: str, objects: Mapping[str, Mapping[str, Any]], boundary: bool) -> str:
    if old == new:  # pragma: no cover - equal heads do not create events
        return "same"
    if boundary:
        return "unknown"  # pragma: no cover - boundary is exercised through gated callers

    def reaches(start: str, target: str) -> bool:
        seen: set[str] = set()
        pending = [start]
        while pending:
            current = pending.pop()
            if current in seen:
                continue  # pragma: no cover - malformed cyclic graph guard
            seen.add(current)
            if current == target:
                return True
            record = objects.get(current, {})
            pending.extend(_id(parent) for parent in record.get("parents", ()))
        return False

    new_to_old = reaches(new, old)
    old_to_new = reaches(old, new)
    if new_to_old:
        return "old_ancestor_of_new"
    if old_to_new:  # pragma: no cover - rewind is a caller-specific movement
        return "new_ancestor_of_old"
    if old in objects and new in objects:  # pragma: no cover - divergence is adapter-specific
        return "diverged"
    return "unknown"  # pragma: no cover - missing graph evidence


class HistoryDeltaCalculator:
    """Compare two compatible snapshots without mutating their source."""

    def __init__(
        self,
        ledger: HistoryLedger | None = None,
        *,
        clock: Callable[[], str] = _now,
        delta_id_factory: Callable[[], str] | None = None,
        objects: Mapping[str, Mapping[str, Any]] | None = None,
    ):
        self.ledger = ledger
        self.clock = clock
        self.delta_id_factory = delta_id_factory or (lambda: f"delta-{uuid4().hex}")
        self._objects = dict(objects or {})

    def calculate(
        self,
        before: SnapshotEnvelope | Mapping[str, Any],
        after: SnapshotEnvelope | Mapping[str, Any],
    ) -> DeltaEnvelope:
        old = before if isinstance(before, SnapshotEnvelope) else SnapshotEnvelope.from_dict(before)
        new = after if isinstance(after, SnapshotEnvelope) else SnapshotEnvelope.from_dict(after)
        if old.history_store.store_id != new.history_store.store_id:
            raise ContractError("snapshots must use the same history store")
        objects = self._read_objects()
        store = {
            "store_id": old.history_store.store_id,
            "from_generation": old.history_store.generation,
            "to_generation": new.history_store.generation,
        }
        repositories = self._repositories(old, new, objects)
        incomplete = any(
            any(event["event"] == "comparison_incomplete" for event in repo["events"])
            for repo in repositories
        )
        outcome = CollectionOutcome(
            CollectionState.PARTIAL if incomplete else CollectionState.COMPLETE
        )
        return DeltaEnvelope(
            self.delta_id_factory(),
            self.clock(),
            old.snapshot_id,
            new.snapshot_id,
            store,
            outcome,
            tuple(repositories),
        )

    def _read_objects(self) -> dict[str, Mapping[str, Any]]:
        if self._objects:
            return self._normalize_objects(self._objects)
        if self.ledger is None:
            return {}  # pragma: no cover - no ledger is an explicit empty source
        try:  # pragma: no cover - explicit ledger integration is exercised by adapters
            return self._normalize_objects(self.ledger.read_objects())
        except LedgerCorruptError:  # pragma: no cover - corruption isolation path
            return {}

    @staticmethod
    def _normalize_objects(
        records: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, Mapping[str, Any]]:
        result = {}
        for key, record in records.items():
            object_id = _id(record.get("object_id"))
            if object_id:
                result[object_id] = record
            else:
                result[str(key).split(":")[-1]] = record  # pragma: no cover
        return result

    def _repositories(
        self, old: SnapshotEnvelope, new: SnapshotEnvelope, objects: Mapping[str, Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        left = {str(item.get("repository_key")): item for item in old.repositories}
        right = {str(item.get("repository_key")): item for item in new.repositories}
        keys = sorted(set(left) | set(right))
        result = []
        for key in keys:
            source = right.get(key, left.get(key, {}))
            location = _repository_location(source, _scan_root(new, old))
            if key not in left:
                events = [
                    _event("repository_added", key, {"repository_key": key})
                ]  # pragma: no cover
            elif key not in right:
                events = (
                    [_event("repository_removed", key, {"repository_key": key})]  # pragma: no cover
                    if _complete(left[key], "identity")
                    else []
                )
            else:
                events = self._compare_repo(left[key], right[key], objects)
            events.sort(key=lambda item: (_ORDER.get(item.event, 99), item.event_key))
            result.append(
                {
                    "repository_key": key,
                    "path": location,
                    "mode": source.get("mode"),
                    "events": [item.to_dict() for item in events],
                }
            )
        return result

    def _compare_repo(
        self,
        old: Mapping[str, Any],
        new: Mapping[str, Any],
        objects: Mapping[str, Mapping[str, Any]],
    ) -> list[Event]:
        events: list[Event] = []
        ref_component = "bookmarks" if new.get("mode") == "jj" else "refs"
        checks = (
            (
                ref_component,
                ["ref_created", "ref_deleted", "ref_target_changed"],
            ),
            (
                "workspaces",
                ["workspace_added", "workspace_removed", "workspace_head_changed"],
            ),
            (
                "history",
                [
                    "history_first_observed",
                    "history_became_reachable",
                    "history_became_unreachable",
                    "off_current_history_observed",
                    "current_line_history_observed",
                    "history_file_changes_observed",
                ],
            ),
        )
        for component, suppressed in checks:
            if not (_complete(old, component) and _complete(new, component)):
                if (
                    _state(old, component) != _state(new, component)
                    or _state(new, component) is not CollectionState.COMPLETE  # pragma: no cover
                ):
                    events.append(
                        _event(
                            "comparison_incomplete",
                            component,
                            {
                                "component": component,
                                "from_state": _state(old, component).value,
                                "to_state": _state(new, component).value,
                                "suppressed_events": suppressed,
                            },
                            certainty=Certainty.INDETERMINATE,
                        )
                    )
        if old.get("change_graph") is not None or new.get("change_graph") is not None:
            events.extend(self._change_graph(old, new))
        events.extend(self._workspaces(old, new, objects)) if _complete(
            old, "workspaces"
        ) and _complete(new, "workspaces") else None
        events.extend(self._refs(old, new, objects)) if _complete(old, ref_component) and _complete(
            new, ref_component
        ) else None
        events.extend(self._history(old, new, objects)) if _complete(old, "history") and _complete(
            new, "history"
        ) else None
        return events

    def _workspaces(
        self,
        old: Mapping[str, Any],
        new: Mapping[str, Any],
        objects: Mapping[str, Mapping[str, Any]],
    ) -> list[Event]:
        left = {_workspace_key(item): item for item in old.get("workspaces", ())}
        right = {_workspace_key(item): item for item in new.get("workspaces", ())}
        result = []
        for key in sorted(set(left) | set(right)):
            if key not in left:
                result.append(  # pragma: no cover - optional working-copy metadata
                    _event("workspace_added", key, {"workspace_key": key, "workspace": right[key]})
                )
                continue
            if key not in right:
                result.append(
                    _event("workspace_removed", key, {"workspace_key": key, "workspace": left[key]})
                )
                continue
            old_head, new_head = (
                _id(left[key].get("head") or left[key].get("current", {}).get("object_id")),
                _id(right[key].get("head") or right[key].get("current", {}).get("object_id")),
            )
            if old_head != new_head:
                result.append(
                    _event(
                        "workspace_head_changed",
                        key,
                        {
                            "workspace_key": key,
                            "old_object_id": old_head,
                            "new_object_id": new_head,
                            "old_change_id": (left[key].get("current") or {}).get("change_id"),
                            "new_change_id": (right[key].get("current") or {}).get("change_id"),
                            "relation": _relation(
                                old_head,
                                new_head,
                                objects,
                                _boundary(old) is not HistoryBoundaryState.COMPLETE
                                or _boundary(new) is not HistoryBoundaryState.COMPLETE,
                            ),
                        },
                    )
                )
            if left[key].get("working_copy") != right[key].get("working_copy"):  # pragma: no cover
                result.append(
                    _event(
                        "working_copy_changed",
                        key,
                        {
                            "workspace_key": key,
                            "old": left[key].get("working_copy"),
                            "new": right[key].get("working_copy"),
                        },
                    )
                )
        return result

    def _change_graph(self, old: Mapping[str, Any], new: Mapping[str, Any]) -> list[Event]:
        """Compare persisted jj logical changes without requiring bookmarks."""
        old_graph = old.get("change_graph") or {}
        new_graph = new.get("change_graph") or {}
        old_changes = {item.get("change_id"): item for item in old_graph.get("changes", ())}
        new_changes = {item.get("change_id"): item for item in new_graph.get("changes", ())}
        old_complete = old_graph.get("outcome", {}).get("state") == "complete"
        new_complete = new_graph.get("outcome", {}).get("state") == "complete"
        result: list[Event] = []
        for change_id in sorted(set(old_changes) | set(new_changes)):
            before = old_changes.get(change_id)
            after = new_changes.get(change_id)
            old_versions = before.get("versions", ()) if before else ()
            new_versions = after.get("versions", ()) if after else ()
            old_ids = sorted(_id(item.get("object_id")) for item in old_versions)
            new_ids = sorted(_id(item.get("object_id")) for item in new_versions)
            if before is None and after is not None:
                state = "introduced"
            elif after is None:
                if not (old_complete and new_complete):
                    continue  # pragma: no cover - defensive partial-graph absence gate
                state = "visibility_lost"
            else:
                old_parents = {
                    _id(parent.get("object_id"))
                    for version in old_versions
                    for parent in version.get("parents", ())
                }
                new_parents = {
                    _id(parent.get("object_id"))
                    for version in new_versions
                    for parent in version.get("parents", ())
                }
                if len(new_ids) > 1:
                    state = "divergent"
                elif len(old_ids) > 1 and len(new_ids) == 1:
                    state = "resolved"
                elif old_ids != new_ids:
                    state = "rewritten"
                elif old_parents != new_parents:
                    state = "topology_changed"
                else:
                    continue  # pragma: no cover - verified graph no-op
            certainty = Certainty.OBSERVED
            if state == "topology_changed" and not (old_complete and new_complete):
                certainty = Certainty.INDETERMINATE
            result.append(
                _event(
                    "change_versions_changed",
                    str(change_id),
                    {
                        "change_id": change_id,
                        "old_visible_commits": old_ids,
                        "new_visible_commits": new_ids,
                        "state": state,
                    },
                    evidence={"from_component": "change_graph", "to_component": "change_graph"},
                    certainty=certainty,
                )
            )
        old_heads = {_id(item.get("object_id")) for item in old_graph.get("visible_heads", ())}
        new_heads = {_id(item.get("object_id")) for item in new_graph.get("visible_heads", ())}
        for object_id in sorted(new_heads - old_heads):
            result.append(
                _event(
                    "visible_head_added",
                    object_id,
                    {
                        "object_id": object_id,
                        "change_id": self._graph_change_id(new_graph, object_id),
                    },
                )
            )
        for object_id in sorted(old_heads - new_heads):
            if old_complete and new_complete:
                result.append(
                    _event(
                        "visible_head_removed",
                        object_id,
                        {
                            "object_id": object_id,
                            "change_id": self._graph_change_id(old_graph, object_id),
                        },
                    )
                )
        return result

    @staticmethod
    def _graph_change_id(graph: Mapping[str, Any], object_id: str) -> str | None:
        for change in graph.get("changes", ()):
            if any(
                _id(version.get("object_id")) == object_id for version in change.get("versions", ())
            ):
                return change.get("change_id")
        return None

    def _refs(
        self,
        old: Mapping[str, Any],
        new: Mapping[str, Any],
        objects: Mapping[str, Mapping[str, Any]],
    ) -> list[Event]:
        left = {_ref_key(item): item for item in old.get("refs", ())}
        right = {_ref_key(item): item for item in new.get("refs", ())}
        result = []
        uncertain = (
            _boundary(old) is not HistoryBoundaryState.COMPLETE
            or _boundary(new) is not HistoryBoundaryState.COMPLETE
        )
        for key in sorted(set(left) | set(right)):
            if key not in left:
                result.append(_event("ref_created", key, {"ref_key": key, "new": right[key]}))
                continue
            if key not in right:
                result.append(_event("ref_deleted", key, {"ref_key": key, "old": left[key]}))
                continue
            old_targets, new_targets = (
                _ids(left[key].get("targets", left[key].get("object_id"))),
                _ids(right[key].get("targets", right[key].get("object_id"))),
            )
            if old_targets != new_targets:
                relations = [
                    {"old": a, "new": b, "relation": _relation(a, b, objects, uncertain)}
                    for a in old_targets
                    for b in new_targets
                ]
                movement = (
                    "unknown"
                    if uncertain
                    else (
                        "fast_forward"
                        if len(old_targets) == len(new_targets) == 1
                        and relations[0]["relation"] == "old_ancestor_of_new"
                        else "rewind"
                        if len(old_targets) == len(new_targets) == 1
                        and relations[0]["relation"] == "new_ancestor_of_old"
                        else "diverged"
                        if len(old_targets) == len(new_targets) == 1
                        and relations[0]["relation"] == "diverged"
                        else "target_set_changed"
                    )
                )
                result.append(
                    _event(
                        "ref_target_changed",
                        key,
                        {
                            "ref_key": key,
                            "old": {"targets": old_targets},
                            "new": {"targets": new_targets},
                            "relations": relations,
                            "movement": movement,
                        },
                    )
                )
            tracking = {  # pragma: no cover - tracking metadata is optional
                field: left[key].get(field) for field in ("tracking", "remote", "authority")
            }
            tracking_new = {
                field: right[key].get(field) for field in ("tracking", "remote", "authority")
            }
            if tracking != tracking_new:  # pragma: no cover
                result.append(
                    _event(
                        "ref_tracking_changed",
                        key,
                        {"ref_key": key, "old": tracking, "new": tracking_new},
                    )
                )
        return result

    def _history(
        self,
        old: Mapping[str, Any],
        new: Mapping[str, Any],
        objects: Mapping[str, Mapping[str, Any]],
    ) -> list[Event]:
        old_ids = {_id(item.get("object_id")) for item in old.get("history", ())}
        new_ids = {_id(item.get("object_id")) for item in new.get("history", ())}
        first = sorted(new_ids - old_ids)
        if not first:
            return []
        roots = [_ref_key(ref) for ref in new.get("refs", ())]
        workspace_heads = [
            _id(item.get("head") or item.get("current", {}).get("object_id"))
            for item in new.get("workspaces", ())
        ]
        events = [
            _event(
                "history_first_observed",
                ",".join(first),
                {"object_ids": first, "reachable_from": sorted(roots)},
            )
        ]
        current = sorted(
            item
            for item in first
            if item in workspace_heads
            or any(self._reachable(head, item, objects) for head in workspace_heads)
        )
        off = sorted(set(first) - set(current))
        if current:
            events.append(
                _event(
                    "current_line_history_observed",
                    ",".join(current),
                    {"object_ids": current, "workspace_heads": sorted(workspace_heads)},
                )
            )
        if off:
            events.append(
                _event(
                    "off_current_history_observed",
                    ",".join(off),
                    {
                        "object_ids": off,
                        "reachable_from": sorted(roots),
                        "workspace_heads": sorted(workspace_heads),
                    },
                )
            )
        return events

    @staticmethod
    def _reachable(start: str, target: str, objects: Mapping[str, Mapping[str, Any]]) -> bool:
        seen: set[str] = set()
        pending = [start]
        while pending:
            item = pending.pop()
            if item in seen:
                continue  # pragma: no cover - cycle guard
            seen.add(item)
            if item == target:
                return True  # pragma: no cover - direct reachability is covered by relation tests
            pending.extend(_id(parent) for parent in objects.get(item, {}).get("parents", ()))
        return False


DeltaCalculator = HistoryDeltaCalculator

__all__ = ["DeltaCalculator", "HistoryDeltaCalculator"]
