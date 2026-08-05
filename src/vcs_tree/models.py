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


class WorkingCopyState(_ValueEnum):
    CLEAN = "clean"
    DIRTY = "dirty"
    CONFLICTED = "conflicted"
    UNKNOWN = "unknown"
    UNREADABLE = "unreadable"


class RefreshState(_ValueEnum):
    PERFORMED = "performed"
    SKIPPED = "skipped"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


class Freshness(_ValueEnum):
    CURRENT = "current"
    RECORDED_MAYBE_STALE = "recorded_maybe_stale"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


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


def _v1_repository_view(value: Mapping[str, Any]) -> Mapping[str, Any]:
    """Strip v2 observation provenance from the legacy comparison presentation."""
    repository = _copy_json(value, "repository")
    for workspace in repository.get("workspaces", []):
        working_copy = workspace.get("working_copy")
        if not isinstance(working_copy, dict):
            continue
        for name in (
            "outcome",
            "refresh",
            "freshness",
            "entries_outcome",
            "entries_limit",
            "entries_truncated",
        ):
            working_copy.pop(name, None)
    return repository


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
class ObservationOutcome:
    """A v2 component outcome with explicit observer-time provenance."""

    state: CollectionState
    attempted_at: str | None = None
    errors: tuple[CollectionError, ...] = ()

    def __post_init__(self) -> None:
        if self.state is CollectionState.NOT_REQUESTED:
            if self.attempted_at is not None:
                raise ContractError("not_requested outcome cannot have attempted_at")
            if self.errors:
                raise ContractError("not_requested outcome cannot contain errors")
        elif self.attempted_at is None:
            raise ContractError("attempted outcome requires attempted_at")
        else:
            _timestamp(self.attempted_at, "outcome.attempted_at")
        if self.state is CollectionState.COMPLETE and self.errors:
            raise ContractError("complete outcome cannot contain errors")
        if self.state is CollectionState.ERROR and not self.errors:
            raise ContractError("error outcome requires an error")

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "state": self.state.value,
            "errors": [error.to_dict() for error in self.errors],
        }
        if self.attempted_at is not None:
            value["attempted_at"] = self.attempted_at
        return value

    @classmethod
    def from_dict(cls, value: Any) -> ObservationOutcome:
        obj = _object(value, "outcome")
        errors = tuple(
            CollectionError.from_dict(item)
            for item in _list(obj.get("errors", []), "outcome.errors")
        )
        attempted_at = obj.get("attempted_at")
        if attempted_at is not None:
            attempted_at = _timestamp(attempted_at, "outcome.attempted_at")
        return cls(CollectionState.parse(_required(obj, "state")), attempted_at, errors)


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
        candidate = _object(value, "document")
        if candidate.get("schema_version") == 2:
            versioned = SnapshotEnvelopeV2.from_dict(candidate)
            return cls(
                versioned.snapshot_id,
                versioned.captured_at,
                versioned.collector,
                versioned.history_store,
                versioned.scan,
                tuple(_v1_repository_view(item) for item in versioned.repositories),
            )
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


V2_REPOSITORY_COMPONENTS = (
    "identity",
    "git_worktrees",
    "jj_workspaces",
    "git_refs",
    "jj_bookmarks",
    "jj_visible_heads",
    "git_history",
    "jj_history",
    "path_evidence",
)

_ENTRY_STATUSES = {
    "added",
    "modified",
    "deleted",
    "renamed",
    "copied",
    "type_changed",
    "conflicted",
}


def _validate_refresh(value: Any) -> None:
    refresh = _object(value, "working_copy.refresh")
    state = RefreshState.parse(_required(refresh, "state"))
    attempted_at = refresh.get("attempted_at")
    errors = tuple(
        CollectionError.from_dict(item)
        for item in _list(refresh.get("errors", []), "working_copy.refresh.errors")
    )
    if state is RefreshState.NOT_APPLICABLE:
        if attempted_at is not None or errors:
            raise ContractError("not_applicable refresh cannot have an attempt or errors")
    else:
        if attempted_at is None:
            raise ContractError("attempted refresh requires attempted_at")
        _timestamp(attempted_at, "working_copy.refresh.attempted_at")
    if state in {RefreshState.PERFORMED, RefreshState.SKIPPED} and errors:
        raise ContractError(f"{state.value} refresh cannot contain errors")
    if state is RefreshState.FAILED and not errors:
        raise ContractError("failed refresh requires an error")


def _validate_working_copy(value: Any) -> None:
    working_copy = _object(value, "working_copy")
    ObservationOutcome.from_dict(_required(working_copy, "outcome"))
    WorkingCopyState.parse(_required(working_copy, "recorded_state"))
    _validate_refresh(_required(working_copy, "refresh"))
    freshness = Freshness.parse(_required(working_copy, "freshness"))
    refresh_state = RefreshState.parse(_object(working_copy["refresh"], "refresh")["state"])
    if refresh_state is RefreshState.PERFORMED and freshness is not Freshness.CURRENT:
        raise ContractError("performed refresh requires current freshness")
    if refresh_state is RefreshState.FAILED and freshness not in {
        Freshness.RECORDED_MAYBE_STALE,
        Freshness.UNKNOWN,
    }:
        raise ContractError("failed refresh requires stale or unknown freshness")
    if refresh_state is RefreshState.SKIPPED and freshness not in {
        Freshness.RECORDED_MAYBE_STALE,
        Freshness.UNKNOWN,
    }:
        raise ContractError("skipped refresh requires stale or unknown freshness")
    if refresh_state is RefreshState.NOT_APPLICABLE and freshness not in {
        Freshness.CURRENT,
        Freshness.UNKNOWN,
        Freshness.NOT_APPLICABLE,
    }:
        raise ContractError(
            "not_applicable refresh requires current, unknown, or not_applicable freshness"
        )

    entries_outcome = ObservationOutcome.from_dict(_required(working_copy, "entries_outcome"))
    entries = _list(_required(working_copy, "entries"), "working_copy.entries")
    entries_limit = _required(working_copy, "entries_limit")
    truncated = _required(working_copy, "entries_truncated")
    if not isinstance(entries_limit, int) or isinstance(entries_limit, bool) or entries_limit < 0:
        raise ContractError("working_copy.entries_limit must be a non-negative integer")
    if not isinstance(truncated, bool):
        raise ContractError("working_copy.entries_truncated must be a boolean")
    if len(entries) > entries_limit:
        raise ContractError("working_copy.entries exceeds entries_limit")
    if entries_outcome.state is CollectionState.NOT_REQUESTED and (entries or truncated):
        raise ContractError("not_requested entries must be empty and untruncated")
    for item in entries:
        entry = _object(item, "working_copy.entry")
        status = _string(_required(entry, "status"), "working_copy.entry.status")
        if status not in _ENTRY_STATUSES:
            raise ContractError(f"invalid working-copy entry status: {status!r}")
        _string(_required(entry, "path"), "working_copy.entry.path")
        if entry.get("old_path") is not None:
            _string(entry["old_path"], "working_copy.entry.old_path")


def _validate_v2_repository(value: Any) -> None:
    repository = _object(value, "repository")
    _string(_required(repository, "repository_key"), "repository.repository_key")
    RepositoryMode.parse(_required(repository, "mode"))
    collection = _object(_required(repository, "collection"), "repository.collection")
    missing = [name for name in V2_REPOSITORY_COMPONENTS if name not in collection]
    if missing:
        raise ContractError(f"repository.collection missing components: {', '.join(missing)}")
    for name in V2_REPOSITORY_COMPONENTS:
        ObservationOutcome.from_dict(collection[name])
    for item in _list(_required(repository, "workspaces"), "repository.workspaces"):
        workspace = _object(item, "workspace")
        _string(_required(workspace, "workspace_key"), "workspace.workspace_key")
        _validate_working_copy(_required(workspace, "working_copy"))


@dataclass(frozen=True)
class SnapshotEnvelopeV2(Mapping[str, Any]):
    """Snapshot v2 preserving validated native and working-copy evidence."""

    snapshot_id: str
    captured_at: str
    collector: Mapping[str, Any]
    history_store: HistoryStore
    scan: Mapping[str, Any]
    repositories: tuple[Mapping[str, Any], ...] = ()
    schema: ClassVar[str] = SnapshotEnvelope.schema
    schema_version: ClassVar[int] = 2

    def __post_init__(self) -> None:
        _string(self.snapshot_id, "snapshot_id")
        _timestamp(self.captured_at, "captured_at")
        _object(self.collector, "collector")
        _object(self.scan, "scan")
        for repository in self.repositories:
            _validate_v2_repository(repository)

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

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def __iter__(self):
        return iter(self.to_dict())

    def __len__(self) -> int:
        return len(self.to_dict())

    @classmethod
    def from_dict(cls, value: Any) -> SnapshotEnvelopeV2:
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
class PulseEnvelope:
    """Versioned, factual movement pulse assembled from retained observations."""

    pulse_id: str
    generated_at: str
    scope: Mapping[str, Any]
    target_snapshot: Mapping[str, Any]
    comparison: Mapping[str, Any]
    outcome: CollectionOutcome
    movement: Mapping[str, Any]
    repositories: tuple[Mapping[str, Any], ...] = ()
    warnings: tuple[Mapping[str, Any], ...] = ()
    summary: Mapping[str, Any] = field(default_factory=dict)
    schema: ClassVar[str] = "vcs-tree.history-pulse"
    schema_version: ClassVar[int] = 1

    def __post_init__(self) -> None:
        _string(self.pulse_id, "pulse_id")
        _timestamp(self.generated_at, "generated_at")
        _object(self.scope, "scope")
        _object(self.target_snapshot, "target_snapshot")
        _object(self.comparison, "comparison")
        _object(self.movement, "movement")
        _object(self.summary, "summary")
        if self.comparison.get("state") not in {"selected", "baseline_created"}:
            raise ContractError("comparison.state must be selected or baseline_created")
        if self.comparison.get("selection") not in {"automatic", "explicit", "none"}:
            raise ContractError("comparison.selection is invalid")
        if self.movement.get("state") not in {"observed", "empty", "unknown", "baseline"}:
            raise ContractError("movement.state is invalid")
        for repository in self.repositories:
            _object(repository, "repository")
        for warning in self.warnings:
            _object(warning, "warning")
        paths = [
            (str(item.get("path", "")), str(item.get("repository_key", "")))
            for item in self.repositories
        ]
        if paths != sorted(paths):
            raise ContractError("pulse repositories must be deterministically ordered")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "schema_version": self.schema_version,
            "pulse_id": self.pulse_id,
            "generated_at": self.generated_at,
            "scope": _copy_json(self.scope, "scope"),
            "target_snapshot": _copy_json(self.target_snapshot, "target_snapshot"),
            "comparison": _copy_json(self.comparison, "comparison"),
            "outcome": self.outcome.to_dict(),
            "movement": _copy_json(self.movement, "movement"),
            "repositories": _copy_json(list(self.repositories), "repositories"),
            "warnings": _copy_json(list(self.warnings), "warnings"),
            "summary": _copy_json(self.summary, "summary"),
        }

    @classmethod
    def from_dict(cls, value: Any) -> PulseEnvelope:
        obj = _envelope(value, cls.schema, cls.schema_version)
        return cls(
            _string(_required(obj, "pulse_id"), "pulse_id"),
            _timestamp(_required(obj, "generated_at"), "generated_at"),
            _object(_required(obj, "scope"), "scope"),
            _object(_required(obj, "target_snapshot"), "target_snapshot"),
            _object(_required(obj, "comparison"), "comparison"),
            CollectionOutcome.from_dict(_required(obj, "outcome")),
            _object(_required(obj, "movement"), "movement"),
            tuple(
                _object(item, "repository")
                for item in _list(obj.get("repositories", []), "repositories")
            ),
            tuple(_object(item, "warning") for item in _list(obj.get("warnings", []), "warnings")),
            _object(obj.get("summary", {}), "summary"),
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


T = TypeVar("T", SnapshotEnvelope, SnapshotEnvelopeV2, DeltaEnvelope, PulseEnvelope)


def _envelope(value: Any, schema: str, version: int) -> Mapping[str, Any]:
    obj = _object(value, "document")
    if _required(obj, "schema") != schema:
        raise ContractError(f"expected schema {schema!r}")
    if _required(obj, "schema_version") != version:
        raise ContractError(f"unsupported {schema} schema version")
    return obj


def dumps(
    document: SnapshotEnvelope | SnapshotEnvelopeV2 | DeltaEnvelope | PulseEnvelope,
    *,
    indent: int | None = None,
) -> str:
    """Serialize a supported envelope deterministically as JSON."""
    if not isinstance(
        document, (SnapshotEnvelope, SnapshotEnvelopeV2, DeltaEnvelope, PulseEnvelope)
    ):
        raise ContractError("document must be a supported history envelope")
    return json.dumps(
        document.to_dict(),
        sort_keys=True,
        indent=indent,
        separators=(",", ":") if indent is None else None,
    )


def loads(
    value: str | bytes, *, kind: str | None = None
) -> SnapshotEnvelope | SnapshotEnvelopeV2 | DeltaEnvelope | PulseEnvelope:
    """Parse a snapshot or delta envelope, rejecting unknown major versions."""
    try:
        document = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ContractError("document must be valid JSON") from exc
    schema = _object(document, "document").get("schema")
    if kind not in {None, "snapshot", "delta", "pulse"}:
        raise ContractError(f"unsupported history document kind: {kind!r}")
    if kind == "snapshot" and schema != SnapshotEnvelope.schema:
        raise ContractError("document schema does not match requested kind")
    if kind == "delta" and schema != DeltaEnvelope.schema:
        raise ContractError("document schema does not match requested kind")
    if kind == "pulse" and schema != PulseEnvelope.schema:
        raise ContractError("document schema does not match requested kind")
    if schema == SnapshotEnvelope.schema:
        version = _object(document, "document").get("schema_version")
        if version == SnapshotEnvelope.schema_version:
            return SnapshotEnvelope.from_dict(document)
        if version == SnapshotEnvelopeV2.schema_version:
            return SnapshotEnvelopeV2.from_dict(document)
        raise ContractError(f"unsupported {SnapshotEnvelope.schema} schema version")
    if schema == DeltaEnvelope.schema:
        return DeltaEnvelope.from_dict(document)
    if schema == PulseEnvelope.schema:
        return PulseEnvelope.from_dict(document)
    raise ContractError("unsupported history document schema")


__all__ = [
    "Backend",
    "Certainty",
    "CollectionError",
    "CollectionOutcome",
    "CollectionState",
    "ContractError",
    "DeltaEnvelope",
    "PulseEnvelope",
    "Event",
    "HistoryBoundary",
    "HistoryBoundaryState",
    "HistoryStore",
    "IntegrityState",
    "Freshness",
    "ObjectId",
    "Placement",
    "RepositoryMode",
    "ObservationOutcome",
    "RefreshState",
    "Retention",
    "SnapshotEnvelope",
    "SnapshotEnvelopeV2",
    "V2_REPOSITORY_COMPONENTS",
    "WorkingCopyState",
    "WriterPolicy",
    "dumps",
    "loads",
]
