"""Bounded, read-only enrichment of delta movement evidence."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from .ledger import HistoryLedger, LedgerCorruptError
from .models import CollectionOutcome, CollectionState, DeltaEnvelope

PathLoader = Callable[[str, Any], tuple[dict[str, Any], ...]]


@dataclass(frozen=True)
class EnrichmentResult:
    repositories: tuple[Mapping[str, Any], ...]
    outcome: CollectionOutcome
    warnings: tuple[Mapping[str, Any], ...] = ()


def _id(value: Any) -> str:
    if isinstance(value, Mapping):
        return str(value.get("value", ""))
    return str(value) if value else ""


def _object_ids(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        if "value" in value and isinstance(value.get("value"), str):
            identifier = _id(value)
            if identifier and identifier != "00000000":
                found.add(identifier)
        for key, item in value.items():
            if key in {"object_id", "old_object_id", "new_object_id", "parent_id"}:
                identifier = _id(item)
                if identifier and identifier != "00000000":
                    found.add(identifier)
            elif key in {"old", "new", "targets", "removed_targets", "added_targets"}:
                if isinstance(item, Mapping) and "value" in item:
                    identifier = _id(item)
                    if identifier and identifier != "00000000":
                        found.add(identifier)
                else:
                    found.update(_object_ids(item))
            elif isinstance(item, (Mapping, list, tuple)):
                found.update(_object_ids(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            found.update(_object_ids(item))
    return found


def _normalize_objects(records: Mapping[str, Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    normalized = {}
    for key, record in records.items():
        object_id = _id(record.get("object_id"))
        if object_id:
            normalized[object_id] = record
        else:
            normalized[str(key).split(":")[-1]] = record
    return normalized


def _description(object_id: str, record: Mapping[str, Any]) -> dict[str, Any]:
    result = {
        "object_id": record.get("object_id", {"algorithm": "unknown", "value": object_id}),
        "kind": record.get("kind", "commit"),
        "parents": list(record.get("parents", ())),
        "summary": record.get("summary"),
    }
    for field in ("change_id", "author", "committer", "authorities"):
        if field in record:
            result[field] = record[field]
    return result


class PulseEnricher:
    """Enrich only object IDs named by a factual delta."""

    def __init__(
        self,
        ledger: HistoryLedger | None = None,
        *,
        objects: Mapping[str, Mapping[str, Any]] | None = None,
        path_loader: PathLoader | None = None,
        max_objects: int = 256,
        max_paths: int = 10_000,
    ):
        if max_objects < 0 or max_paths < 0:
            raise ValueError("enrichment limits must be non-negative")
        self.ledger = ledger
        self.objects = dict(objects or {})
        self.path_loader = path_loader
        self.max_objects = max_objects
        self.max_paths = max_paths

    def enrich(self, delta: DeltaEnvelope | Mapping[str, Any]) -> EnrichmentResult:
        document = delta.to_dict() if isinstance(delta, DeltaEnvelope) else delta
        repositories = document.get("repository_deltas", [])
        all_ids = sorted(_object_ids(repositories))
        warnings: list[dict[str, Any]] = []
        outcome = CollectionOutcome(CollectionState.COMPLETE)
        if len(all_ids) > self.max_objects:
            warnings.append(_limit_warning("objects", len(all_ids), self.max_objects))
            outcome = CollectionOutcome(CollectionState.PARTIAL)
        selected = all_ids[: self.max_objects]
        records = self._read_objects()
        descriptions = {
            object_id: _description(object_id, records[object_id])
            for object_id in selected
            if object_id in records and records[object_id].get("kind") != "virtual_root"
        }
        missing = [object_id for object_id in selected if object_id not in records]
        if missing:
            warnings.append(
                {
                    "warning_key": "@scan|enrichment|missing_object|ledger|description",
                    "kind": "missing_object",
                    "object_ids": missing,
                }
            )
            outcome = CollectionOutcome(CollectionState.PARTIAL)
        result = []
        path_count = 0
        for repository in repositories:
            repo_ids = sorted(_object_ids(repository.get("events", ())))
            repo_descriptions = [descriptions[item] for item in repo_ids if item in descriptions]
            path_evidence: list[dict[str, Any]] = []
            for object_id in repo_ids:
                record = records.get(object_id, {})
                for parent in record.get("parents", ()):  # one group per parent
                    parent_id = _id(parent)
                    paths = self._paths(object_id, parent_id, record)
                    if paths:
                        remaining = self.max_paths - path_count
                        if len(paths) > remaining:
                            paths = paths[: max(0, remaining)]
                            warnings.append(
                                _limit_warning("paths", path_count + len(paths) + 1, self.max_paths)
                            )
                            outcome = CollectionOutcome(CollectionState.PARTIAL)
                        path_count += len(paths)
                        if paths:
                            path_evidence.append(
                                {
                                    "object_id": record.get("object_id"),
                                    "parent_id": parent_id or None,
                                    "paths": paths,
                                }
                            )
            result.append(
                {
                    **repository,
                    "descriptions": repo_descriptions,
                    "path_evidence": path_evidence,
                    "enrichment_warnings": [item["warning_key"] for item in warnings],
                }
            )
        return EnrichmentResult(tuple(result), outcome, tuple(warnings))

    def _read_objects(self) -> dict[str, Mapping[str, Any]]:
        if self.objects:
            return _normalize_objects(self.objects)
        if self.ledger is None:
            return {}
        try:
            return _normalize_objects(self.ledger.read_objects())
        except LedgerCorruptError:
            return {}

    def _paths(
        self, object_id: str, parent_id: str | None, record: Mapping[str, Any]
    ) -> tuple[dict[str, Any], ...]:
        if record.get("kind") == "virtual_root":
            return ()
        if self.path_loader is not None:
            return tuple(self.path_loader(object_id, parent_id))
        return tuple(record.get("path_evidence", ()))


def _limit_warning(kind: str, observed: int, limit: int) -> dict[str, Any]:
    return {
        "warning_key": f"@scan|enrichment|limit_exceeded|{kind}|-",
        "kind": "limit_exceeded",
        "evidence_class": kind,
        "observed": observed,
        "limit": limit,
    }


__all__ = ["EnrichmentResult", "PulseEnricher"]
