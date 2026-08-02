"""Versioned snapshot and delta contract primitives.

This module intentionally owns the wire boundary, not collection or storage.
Repository and event payloads remain ordinary JSON mappings until their
collection/comparison tasks need richer domain behavior.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar, TypeVar


class ContractError(ValueError):
    """Raised when a contract document cannot be represented safely."""


class _ValueEnum(str, Enum):
    @classmethod
    def parse(cls, value: Any) -> _ValueEnum:
        if not isinstance(value, str):
            raise ContractError(f"expected {cls.__name__} value")
        try:
            return cls(value)
        except ValueError as exc:
            raise ContractError(f"invalid {cls.__name__}: {value!r}") from exc


class CollectionState(_ValueEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    ERROR = "error"
    NOT_REQUESTED = "not_requested"


class IntegrityState(_ValueEnum):
    OK = "ok"
    DEGRADED = "degraded"
    ERROR = "error"


class HistoryBoundaryState(_ValueEnum):
    COMPLETE = "complete"
    SHALLOW = "shallow"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class RepositoryMode(_ValueEnum):
    GIT = "git"
    JJ = "jj"
    COLOCATED = "colocated"


class Backend(_ValueEnum):
    GIT = "git"
    JJ = "jj"


class Placement(_ValueEnum):
    MACHINE_LOCAL = "machine_local"


class WriterPolicy(_ValueEnum):
    SINGLE_WRITER = "single_writer"


class Retention(_ValueEnum):
    INDEFINITE = "indefinite"


class Certainty(_ValueEnum):
    OBSERVED = "observed"
    INDETERMINATE = "indeterminate"


def _required(mapping: Mapping[str, Any], name: str) -> Any:
    if name not in mapping:
        raise ContractError(f"missing required field: {name}")
    return mapping[name]


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{name} must be a non-empty string")
    return value


def _object(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{name} must be an object")
    return value


def _list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContractError(f"{name} must be an array")
    return value


def _timestamp(value: Any, name: str) -> str:
    text = _string(value, name)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ContractError(f"{name} must be an RFC 3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"{name} must include a timezone")
    return text


def _copy_json(value: Any, name: str) -> Any:
    try:
        copied = json.loads(json.dumps(value))
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{name} must contain JSON-compatible values") from exc
    return copied


@dataclass(frozen=True)
class ObjectId:
    algorithm: str
    value: str

    def __post_init__(self) -> None:
        _string(self.algorithm, "algorithm")
        value = _string(self.value, "value")
        if self.algorithm in {"sha1", "sha256"} and value != value.lower():
            object.__setattr__(self, "value", value.lower())

    def to_dict(self) -> dict[str, str]:
        return {"algorithm": self.algorithm, "value": self.value}

    @classmethod
    def from_dict(cls, value: Any) -> ObjectId:
        obj = _object(value, "object_id")
        return cls(
            _string(_required(obj, "algorithm"), "algorithm"),
            _string(_required(obj, "value"), "value"),
        )


@dataclass(frozen=True)
class CollectionError:
    kind: str
    stage: str
    message: str
    exit_code: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "stage": self.stage,
            "message": self.message,
            "exit_code": self.exit_code,
        }

    @classmethod
    def from_dict(cls, value: Any) -> CollectionError:
        obj = _object(value, "error")
        exit_code = obj.get("exit_code")
        if exit_code is not None and not isinstance(exit_code, int):
            raise ContractError("error.exit_code must be an integer or null")
        return cls(
            _string(_required(obj, "kind"), "error.kind"),
            _string(_required(obj, "stage"), "error.stage"),
            _string(_required(obj, "message"), "error.message"),
            exit_code,
        )


@dataclass(frozen=True)
class CollectionOutcome:
    state: CollectionState
    errors: tuple[CollectionError, ...] = ()

    def __post_init__(self) -> None:
        if self.state is CollectionState.COMPLETE and self.errors:
            raise ContractError("complete outcome cannot contain errors")

    def to_dict(self) -> dict[str, Any]:
        return {"state": self.state.value, "errors": [error.to_dict() for error in self.errors]}

    @classmethod
    def from_dict(cls, value: Any) -> CollectionOutcome:
        obj = _object(value, "outcome")
        errors = tuple(
            CollectionError.from_dict(item)
            for item in _list(obj.get("errors", []), "outcome.errors")
        )
        return cls(CollectionState.parse(_required(obj, "state")), errors)


@dataclass(frozen=True)
class HistoryBoundary:
    state: HistoryBoundaryState
    boundary_objects: tuple[ObjectId, ...] = ()

    def __post_init__(self) -> None:
        if self.state is HistoryBoundaryState.COMPLETE and self.boundary_objects:
            raise ContractError("complete history boundary cannot contain boundary objects")

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "boundary_objects": [item.to_dict() for item in self.boundary_objects],
        }

    @classmethod
    def from_dict(cls, value: Any) -> HistoryBoundary:
        obj = _object(value, "history_boundary")
        items = tuple(
            ObjectId.from_dict(item)
            for item in _list(obj.get("boundary_objects", []), "boundary_objects")
        )
        return cls(HistoryBoundaryState.parse(_required(obj, "state")), items)


@dataclass(frozen=True)
class HistoryStore:
    store_id: str
    generation: int
    placement: Placement = Placement.MACHINE_LOCAL
    writer_policy: WriterPolicy = WriterPolicy.SINGLE_WRITER
    writer_id: str = ""
    retention: Retention = Retention.INDEFINITE
    integrity: IntegrityState = IntegrityState.OK

    def __post_init__(self) -> None:
        _string(self.store_id, "store_id")
        _string(self.writer_id, "writer_id")
        if self.generation < 0:
            raise ContractError("generation must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "store_id": self.store_id,
            "generation": self.generation,
            "placement": self.placement.value,
            "writer_policy": self.writer_policy.value,
            "writer_id": self.writer_id,
            "retention": self.retention.value,
            "integrity": self.integrity.value,
        }

    @classmethod
    def from_dict(cls, value: Any) -> HistoryStore:
        obj = _object(value, "history_store")
        return cls(
            _string(_required(obj, "store_id"), "store_id"),
            _required(obj, "generation"),
            Placement.parse(_required(obj, "placement")),
            WriterPolicy.parse(_required(obj, "writer_policy")),
            _string(_required(obj, "writer_id"), "writer_id"),
            Retention.parse(_required(obj, "retention")),
            IntegrityState.parse(_required(obj, "integrity")),
        )


@dataclass(frozen=True)
class SnapshotEnvelope:
    snapshot_id: str
    captured_at: str
    collector: Mapping[str, Any]
    history_store: HistoryStore
    scan: Mapping[str, Any]
    repositories: tuple[Mapping[str, Any], ...] = ()
    schema: ClassVar[str] = "vcs-tree.history-snapshot"
    schema_version: ClassVar[int] = 1

    def __post_init__(self) -> None:
        _string(self.snapshot_id, "snapshot_id")
        _timestamp(self.captured_at, "captured_at")
        _object(self.collector, "collector")
        _object(self.scan, "scan")
        for repository in self.repositories:
            _object(repository, "repository")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "schema_version": self.schema_version,
            "snapshot_id": self.snapshot_id,
            "captured_at": self.captured_at,
            "collector": _copy_json(self.collector, "collector"),
            "history_store": self.history_store.to_dict(),
            "scan": _copy_json(self.scan, "scan"),
            "repositories": _copy_json(list(self.repositories), "repositories"),
        }

    @classmethod
    def from_dict(cls, value: Any) -> SnapshotEnvelope:
        obj = _envelope(value, cls.schema, cls.schema_version)
        repositories = tuple(
            _object(item, "repository")
            for item in _list(_required(obj, "repositories"), "repositories")
        )
        return cls(
            _string(_required(obj, "snapshot_id"), "snapshot_id"),
            _timestamp(_required(obj, "captured_at"), "captured_at"),
            _object(_required(obj, "collector"), "collector"),
            HistoryStore.from_dict(_required(obj, "history_store")),
            _object(_required(obj, "scan"), "scan"),
            repositories,
        )


@dataclass(frozen=True)
class DeltaEnvelope:
    delta_id: str
    computed_at: str
    from_snapshot: str
    to_snapshot: str
    history_store: Mapping[str, Any]
    outcome: CollectionOutcome
    repository_deltas: tuple[Mapping[str, Any], ...] = ()
    schema: ClassVar[str] = "vcs-tree.history-delta"
    schema_version: ClassVar[int] = 1

    def __post_init__(self) -> None:
        _string(self.delta_id, "delta_id")
        _timestamp(self.computed_at, "computed_at")
        _string(self.from_snapshot, "from_snapshot")
        _string(self.to_snapshot, "to_snapshot")
        _object(self.history_store, "history_store")
        for item in self.repository_deltas:
            _object(item, "repository_delta")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "schema_version": self.schema_version,
            "delta_id": self.delta_id,
            "computed_at": self.computed_at,
            "from_snapshot": self.from_snapshot,
            "to_snapshot": self.to_snapshot,
            "history_store": _copy_json(self.history_store, "history_store"),
            "outcome": self.outcome.to_dict(),
            "repository_deltas": _copy_json(list(self.repository_deltas), "repository_deltas"),
        }

    @classmethod
    def from_dict(cls, value: Any) -> DeltaEnvelope:
        obj = _envelope(value, cls.schema, cls.schema_version)
        repositories = tuple(
            _object(item, "repository_delta")
            for item in _list(_required(obj, "repository_deltas"), "repository_deltas")
        )
        return cls(
            _string(_required(obj, "delta_id"), "delta_id"),
            _timestamp(_required(obj, "computed_at"), "computed_at"),
            _string(_required(obj, "from_snapshot"), "from_snapshot"),
            _string(_required(obj, "to_snapshot"), "to_snapshot"),
            _object(_required(obj, "history_store"), "history_store"),
            CollectionOutcome.from_dict(_required(obj, "outcome")),
            repositories,
        )


@dataclass(frozen=True)
class Event:
    event: str
    event_key: str
    certainty: Certainty
    evidence: Mapping[str, Any] = field(default_factory=dict)
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _string(self.event, "event")
        _string(self.event_key, "event_key")
        _object(self.evidence, "evidence")
        _object(self.details, "details")

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "event_key": self.event_key,
            "certainty": self.certainty.value,
            "evidence": _copy_json(self.evidence, "evidence"),
            "details": _copy_json(self.details, "details"),
        }

    @classmethod
    def from_dict(cls, value: Any) -> Event:
        obj = _object(value, "event")
        return cls(
            _string(_required(obj, "event"), "event"),
            _string(_required(obj, "event_key"), "event_key"),
            Certainty.parse(_required(obj, "certainty")),
            _object(_required(obj, "evidence"), "evidence"),
            _object(_required(obj, "details"), "details"),
        )


T = TypeVar("T", SnapshotEnvelope, DeltaEnvelope)


def _envelope(value: Any, schema: str, version: int) -> Mapping[str, Any]:
    obj = _object(value, "document")
    if _required(obj, "schema") != schema:
        raise ContractError(f"expected schema {schema!r}")
    if _required(obj, "schema_version") != version:
        raise ContractError(f"unsupported {schema} schema version")
    return obj


def dumps(document: SnapshotEnvelope | DeltaEnvelope, *, indent: int | None = None) -> str:
    """Serialize a supported envelope deterministically as JSON."""
    if not isinstance(document, (SnapshotEnvelope, DeltaEnvelope)):
        raise ContractError("document must be a SnapshotEnvelope or DeltaEnvelope")
    return json.dumps(
        document.to_dict(),
        sort_keys=True,
        indent=indent,
        separators=(",", ":") if indent is None else None,
    )


def loads(value: str | bytes, *, kind: str | None = None) -> SnapshotEnvelope | DeltaEnvelope:
    """Parse a snapshot or delta envelope, rejecting unknown major versions."""
    try:
        document = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ContractError("document must be valid JSON") from exc
    schema = _object(document, "document").get("schema")
    if kind not in {None, "snapshot", "delta"}:
        raise ContractError(f"unsupported history document kind: {kind!r}")
    if kind == "snapshot" and schema != SnapshotEnvelope.schema:
        raise ContractError("document schema does not match requested kind")
    if kind == "delta" and schema != DeltaEnvelope.schema:
        raise ContractError("document schema does not match requested kind")
    if schema == SnapshotEnvelope.schema:
        return SnapshotEnvelope.from_dict(document)
    if schema == DeltaEnvelope.schema:
        return DeltaEnvelope.from_dict(document)
    raise ContractError("unsupported history document schema")


__all__ = [
    "Backend",
    "Certainty",
    "CollectionError",
    "CollectionOutcome",
    "CollectionState",
    "ContractError",
    "DeltaEnvelope",
    "Event",
    "HistoryBoundary",
    "HistoryBoundaryState",
    "HistoryStore",
    "IntegrityState",
    "ObjectId",
    "Placement",
    "RepositoryMode",
    "Retention",
    "SnapshotEnvelope",
    "WriterPolicy",
    "dumps",
    "loads",
]
