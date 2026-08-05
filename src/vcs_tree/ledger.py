"""Machine-local, append-only observational history state.

The ledger is deliberately small and file based for v1. Each mutable component
is checksummed independently so a damaged object file cannot erase repository
identity or authorize an action against a source repository.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import ContractError
from .snapshot_schema import SnapshotDocument, parse_snapshot
from .temporal import TEMPORAL_SCHEMA, TEMPORAL_SCHEMA_VERSION, TemporalIndexBuilder


class LedgerError(RuntimeError):
    """Base error for safe ledger operations."""


class LedgerCorruptError(LedgerError):
    """Raised when a required control component cannot be trusted."""


class WriterMismatchError(LedgerError):
    """Raised when a non-enrolled writer attempts a mutation."""


@dataclass(frozen=True)
class StatePaths:
    state_root: Path
    config_root: Path
    cache_root: Path

    @property
    def warnings(self) -> tuple[str, ...]:
        return (
            "Authoritative vcs-tree state is machine-local and does not follow "
            "a cloud-synchronized repository tree.",
            f"Disposable renderer cache: {self.cache_root}",
        )

    def report(self) -> dict[str, str | tuple[str, ...]]:
        return {
            "state_root": str(self.state_root),
            "config_root": str(self.config_root),
            "cache_root": str(self.cache_root),
            "placement": "machine_local",
            "warnings": self.warnings,
        }


def _home() -> Path:
    return Path.home()


def _env_path(name: str, fallback: Path) -> Path:
    value = os.environ.get(name)
    return Path(value) if value else fallback


def resolve_paths(
    state_root: str | os.PathLike[str] | None = None,
    *,
    config_root: str | os.PathLike[str] | None = None,
    cache_root: str | os.PathLike[str] | None = None,
) -> StatePaths:
    """Resolve authoritative, configuration, and disposable cache locations."""
    home = _home()
    state = (
        Path(state_root)
        if state_root is not None
        else _env_path("XDG_STATE_HOME", home / ".local" / "state") / "vcs-tree"
    )
    config = (
        Path(config_root)
        if config_root is not None
        else _env_path("XDG_CONFIG_HOME", home / ".config") / "vcs-tree"
    )
    cache = (
        Path(cache_root)
        if cache_root is not None
        else _env_path("XDG_CACHE_HOME", home / ".cache") / "vcs-tree"
    )
    return StatePaths(state, config, cache)


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _checksum(value: Any) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _atomic_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"checksum": _checksum(value), "value": value}
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_json_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:  # pragma: no cover - exercised by filesystem-failure integration tests
        if os.path.exists(temporary):  # pragma: no cover
            os.unlink(temporary)  # pragma: no cover
        raise


def _read_checked(path: Path) -> Any:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or "checksum" not in payload or "value" not in payload:
            raise LedgerCorruptError(f"malformed ledger component: {path.name}")
        if payload["checksum"] != _checksum(payload["value"]):
            raise LedgerCorruptError(f"checksum mismatch: {path.name}")
        return payload["value"]
    except LedgerCorruptError:
        raise
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise LedgerCorruptError(f"unreadable ledger component: {path.name}") from exc


@dataclass(frozen=True)
class LedgerStatus:
    state: str
    store_id: str | None
    writer_id: str | None
    generation: int | None
    degraded_components: tuple[str, ...] = ()


class HistoryLedger:
    """A single-writer local store retaining observed history indefinitely."""

    _MANIFEST = "manifest.json"
    _REPOSITORIES = "repositories.json"
    _OBJECTS = "objects.json"
    _GENERATIONS = "generations.json"
    _SNAPSHOTS = "snapshots.json"
    _TEMPORAL = "temporal-facts.json"

    def __init__(self, paths: StatePaths, manifest: dict[str, Any], degraded: tuple[str, ...] = ()):
        self.paths = paths
        self.root = paths.state_root
        self._manifest = manifest
        self._degraded = degraded

    @classmethod
    def create(
        cls,
        state_root: str | os.PathLike[str] | None = None,
        *,
        writer_id: str | None = None,
        config_root: str | os.PathLike[str] | None = None,
        cache_root: str | os.PathLike[str] | None = None,
    ) -> HistoryLedger:
        paths = resolve_paths(state_root, config_root=config_root, cache_root=cache_root)
        paths.state_root.mkdir(parents=True, exist_ok=True)
        manifest = {
            "store_id": f"ledger-{uuid.uuid4().hex}",
            "writer_id": writer_id or f"writer-{uuid.uuid4().hex}",
            "writer_policy": "single_writer",
            "placement": "machine_local",
            "retention": "indefinite",
            "generation": 0,
        }
        _atomic_write(paths.state_root / cls._MANIFEST, manifest)
        for name, value in (
            (cls._REPOSITORIES, {}),
            (cls._OBJECTS, {}),
            (cls._GENERATIONS, []),
            (cls._SNAPSHOTS, []),
        ):
            _atomic_write(paths.state_root / name, value)
        return cls(paths, manifest)

    @classmethod
    def open(
        cls,
        state_root: str | os.PathLike[str] | None = None,
        *,
        config_root: str | os.PathLike[str] | None = None,
        cache_root: str | os.PathLike[str] | None = None,
    ) -> HistoryLedger:
        paths = resolve_paths(state_root, config_root=config_root, cache_root=cache_root)
        manifest = _read_checked(paths.state_root / cls._MANIFEST)
        if not isinstance(manifest, dict) or not isinstance(manifest.get("store_id"), str):
            raise LedgerCorruptError("invalid ledger manifest")
        if manifest.get("writer_policy") != "single_writer":
            raise LedgerCorruptError("unsupported writer policy")
        degraded = []
        for name in (cls._REPOSITORIES, cls._OBJECTS, cls._GENERATIONS, cls._SNAPSHOTS):
            try:
                _read_checked(paths.state_root / name)
            except LedgerCorruptError:
                degraded.append(name)
        return cls(paths, manifest, tuple(degraded))

    @property
    def store_id(self) -> str:
        return self._manifest["store_id"]

    @property
    def writer_id(self) -> str:
        return self._manifest["writer_id"]

    @property
    def generation(self) -> int:
        return int(self._manifest["generation"])

    def status(self) -> LedgerStatus:
        return LedgerStatus(
            "degraded" if self._degraded else "ok",
            self.store_id,
            self.writer_id,
            self.generation,
            self._degraded,
        )

    def _require_writer(self, writer_id: str | None) -> None:
        if writer_id != self.writer_id:
            raise WriterMismatchError("only the enrolled writer may mutate this ledger")

    def _require_healthy(self, component: str | None = None) -> None:
        if component and component in self._degraded:
            raise LedgerCorruptError(f"ledger component is degraded: {component}")
        if "manifest.json" in self._degraded:
            raise LedgerCorruptError("ledger manifest is degraded")

    def _load(self, filename: str) -> Any:
        try:
            return _read_checked(self.root / filename)
        except LedgerCorruptError:
            if filename not in self._degraded:
                self._degraded = (*self._degraded, filename)
            raise

    def repository_key(self, continuity_key: str, *, writer_id: str | None = None) -> str:
        """Return or assign a key local to this ledger."""
        self._require_writer(writer_id)
        self._require_healthy(self._REPOSITORIES)
        if not continuity_key:
            raise ContractError("continuity_key must be non-empty")
        repositories = self._load(self._REPOSITORIES)
        if not isinstance(repositories, dict):
            raise LedgerCorruptError("invalid repository registry")
        if continuity_key in repositories:
            return repositories[continuity_key]
        key = f"repo-{len(repositories) + 1:04d}"
        repositories[continuity_key] = key
        _atomic_write(self.root / self._REPOSITORIES, repositories)
        return key

    def append_objects(
        self, objects: list[dict[str, Any]], *, writer_id: str | None = None
    ) -> tuple[str, ...]:
        """Insert immutable object records, returning newly inserted keys."""
        self._require_writer(writer_id)
        self._require_healthy(self._OBJECTS)
        current = self._load(self._OBJECTS)
        if not isinstance(current, dict):
            raise LedgerCorruptError("invalid object ledger")
        inserted = []
        for record in objects:
            if not isinstance(record, dict):
                raise ContractError("history object must be an object")
            for field in ("repository_key", "kind", "object_id"):
                if not record.get(field):
                    raise ContractError(f"history object missing {field}")
            object_id = record["object_id"]
            if (
                not isinstance(object_id, dict)
                or not object_id.get("algorithm")
                or not object_id.get("value")
            ):
                raise ContractError("history object object_id must be an ID object")
            key = ":".join(
                (
                    record["repository_key"],
                    record["kind"],
                    object_id["algorithm"],
                    object_id["value"],
                )
            )
            if key not in current:
                current[key] = json.loads(json.dumps(record, sort_keys=True))
                inserted.append(key)
        _atomic_write(self.root / self._OBJECTS, current)
        return tuple(inserted)

    def commit_generation(self, *, writer_id: str | None = None) -> int:
        self._require_writer(writer_id)
        self._require_healthy(self._GENERATIONS)
        generations = self._load(self._GENERATIONS)
        if not isinstance(generations, list):
            raise LedgerCorruptError("invalid generation ledger")
        next_generation = self.generation + 1
        generations.append(
            {"generation": next_generation, "object_count": len(self._load(self._OBJECTS))}
        )
        _atomic_write(self.root / self._GENERATIONS, generations)
        self._manifest["generation"] = next_generation
        _atomic_write(self.root / self._MANIFEST, self._manifest)
        return next_generation

    def record_snapshot(
        self,
        snapshot_id: str,
        generation: int,
        *,
        manifest: dict[str, Any] | None = None,
        writer_id: str | None = None,
    ) -> None:
        self._require_writer(writer_id)
        self._require_healthy(self._SNAPSHOTS)
        if not snapshot_id or generation < 0:
            raise ContractError("snapshot_id and generation are required")
        snapshots = self._load(self._SNAPSHOTS)
        if not isinstance(snapshots, list):
            raise LedgerCorruptError("invalid snapshot index")
        if generation > self.generation:
            raise ContractError("snapshot generation cannot exceed ledger generation")
        if not any(item.get("snapshot_id") == snapshot_id for item in snapshots):
            entry = {"snapshot_id": snapshot_id, "generation": generation}
            if manifest is not None:
                entry["manifest"] = json.loads(json.dumps(manifest, sort_keys=True))
            snapshots.append(entry)
            _atomic_write(self.root / self._SNAPSHOTS, snapshots)

    def read_objects(self) -> dict[str, dict[str, Any]]:
        """Read immutable objects; corruption is reported and never repaired."""
        value = self._load(self._OBJECTS)
        if not isinstance(value, dict):
            raise LedgerCorruptError("invalid object ledger")
        return value

    def read_snapshots(self) -> list[dict[str, Any]]:
        """Read the authoritative retained-snapshot index without repairing it."""
        value = self._load(self._SNAPSHOTS)
        if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
            raise LedgerCorruptError("invalid snapshot index")
        return value

    def read_snapshot_envelopes(self) -> list[SnapshotDocument]:
        """Read and validate all retained manifests without rewriting the index."""
        documents = []
        for entry in self.read_snapshots():
            manifest = entry.get("manifest")
            if manifest is None:
                continue
            try:
                documents.append(parse_snapshot(manifest))
            except ContractError as exc:
                raise LedgerCorruptError("invalid retained snapshot manifest") from exc
        return documents

    def rebuild_temporal_index(self) -> dict[str, Any]:
        """Replace the disposable temporal projection from authoritative observations."""
        index = TemporalIndexBuilder().build(
            self.read_snapshots(), objects=self.read_objects(), store_id=self.store_id
        )
        index["source_generation"] = self.generation
        _atomic_write(self.root / self._TEMPORAL, index)
        return index

    def read_temporal_index(self) -> dict[str, Any]:
        """Read a current derived index, rebuilding missing, corrupt, or stale data."""
        try:
            value = _read_checked(self.root / self._TEMPORAL)
            if (
                not isinstance(value, dict)
                or value.get("schema") != TEMPORAL_SCHEMA
                or value.get("schema_version") != TEMPORAL_SCHEMA_VERSION
                or value.get("store_id") != self.store_id
                or value.get("source_generation") != self.generation
            ):
                raise LedgerCorruptError("invalid temporal fact index")
            return value
        except LedgerCorruptError:
            return self.rebuild_temporal_index()


__all__ = [
    "HistoryLedger",
    "LedgerCorruptError",
    "LedgerError",
    "LedgerStatus",
    "StatePaths",
    "WriterMismatchError",
    "resolve_paths",
]
