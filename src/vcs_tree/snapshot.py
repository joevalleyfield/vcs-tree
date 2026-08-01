"""Snapshot orchestration over native adapters and the local history ledger."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .git_adapter import GitAdapter, GitObservation
from .jj_adapter import JjAdapter, JjObservation
from .ledger import HistoryLedger
from .models import (
    CollectionError,
    CollectionOutcome,
    CollectionState,
    HistoryBoundary,
    HistoryBoundaryState,
    HistoryStore,
    IntegrityState,
    SnapshotEnvelope,
)

AdapterFactory = Callable[[Path], Any]


@dataclass(frozen=True)
class SnapshotResult:
    envelope: SnapshotEnvelope
    generation: int


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _complete() -> CollectionOutcome:
    return CollectionOutcome(CollectionState.COMPLETE)


def _as_objects(repository_key: str, records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    objects = []
    for record in records:
        item = dict(record)
        item["repository_key"] = repository_key
        objects.append(item)
    return objects


def _dedupe_dicts(
    records: Iterable[dict[str, Any]], key: Callable[[dict[str, Any]], str]
) -> tuple[dict[str, Any], ...]:
    seen: dict[str, dict[str, Any]] = {}
    for record in records:
        seen.setdefault(key(record), record)
    return tuple(seen[name] for name in sorted(seen))


def _discover(root: Path) -> tuple[tuple[Path, ...], tuple[CollectionError, ...]]:
    """Discover canonical repository roots without following metadata/symlink trees."""
    candidates: set[Path] = set()
    errors: list[CollectionError] = []

    def onerror(error: OSError) -> None:
        errors.append(CollectionError("discovery_error", "discovery", str(error)))

    if not root.is_dir():
        return (), (CollectionError("not_directory", "discovery", str(root)),)
    for directory, names, _files in os.walk(root, followlinks=False, onerror=onerror):
        current = Path(directory).resolve()
        marker_names = {name for name in names if name in {".git", ".jj"}}
        if marker_names:
            candidates.add(current)
        names[:] = [name for name in names if name not in {".git", ".jj"}]
    return tuple(sorted(candidates, key=str)), tuple(errors)


def discover_repository_roots(path: str | Path) -> tuple[Path, ...]:
    """Return canonical nested repository roots in deterministic order."""
    return _discover(Path(path).resolve())[0]


def _workspace_key(workspace: dict[str, Any]) -> str:
    path = workspace.get("path")
    if path:
        return str(Path(path).resolve())
    return str(workspace.get("workspace_key", workspace.get("name", "")))


def _merge_workspaces(
    git: GitObservation | None, jj: JjObservation | None
) -> tuple[dict[str, Any], ...]:
    """Merge colocated Git worktrees and jj workspaces by canonical path."""
    merged: dict[str, dict[str, Any]] = {}
    for workspace in [*(git.workspaces if git else ()), *(jj.workspaces if jj else ())]:
        key = _workspace_key(workspace)
        merged[key] = {**merged.get(key, {}), **workspace}
    return tuple(merged[key] for key in sorted(merged))


class SnapshotCollector:
    """Collect one repository observation and publish a durable snapshot."""

    def __init__(
        self,
        ledger: HistoryLedger,
        *,
        git_factory: AdapterFactory = GitAdapter,
        jj_factory: AdapterFactory = JjAdapter,
        clock: Callable[[], str] = _now,
        snapshot_id_factory: Callable[[], str] | None = None,
    ):
        self.ledger = ledger
        self.git_factory = git_factory
        self.jj_factory = jj_factory
        self.clock = clock
        self.snapshot_id_factory = snapshot_id_factory or (lambda: f"snapshot-{uuid4().hex}")

    def collect(self, path: str | Path) -> SnapshotResult:
        root = Path(path).resolve()
        roots, discovery_errors = _discover(root)
        repositories = []
        objects: list[dict[str, Any]] = []
        for repository_root in roots:
            git_observation = (
                self.git_factory(repository_root).collect()
                if (repository_root / ".git").is_dir()
                else None
            )
            jj_observation = (
                self.jj_factory(repository_root).collect()
                if (repository_root / ".jj").is_dir()
                else None
            )
            repository = self._repository(
                root, git_observation, jj_observation, repository_root=repository_root
            )
            objects.extend(
                _as_objects(repository["repository_key"], repository.pop("_history_objects"))
            )
            repositories.append(repository)
        self.ledger.append_objects(objects, writer_id=self.ledger.writer_id)
        generation = self.ledger.commit_generation(writer_id=self.ledger.writer_id)
        store = HistoryStore(
            self.ledger.store_id,
            generation,
            writer_id=self.ledger.writer_id,
            integrity=IntegrityState.OK,
        )
        scan_outcome = CollectionOutcome(
            CollectionState.PARTIAL if discovery_errors else CollectionState.COMPLETE,
            discovery_errors,
        )
        envelope = SnapshotEnvelope(
            self.snapshot_id_factory(),
            self.clock(),
            {"name": "vcs-tree", "version": "0.1.0"},
            store,
            {"root": str(root), "outcome": scan_outcome.to_dict()},
            tuple(repositories),
        )
        self.ledger.record_snapshot(
            envelope.snapshot_id,
            generation,
            manifest=envelope.to_dict(),
            writer_id=self.ledger.writer_id,
        )
        return SnapshotResult(envelope, generation)

    def _repository(
        self,
        root: Path,
        git: GitObservation | None,
        jj: JjObservation | None,
        repository_root: Path | None = None,
    ) -> dict[str, Any]:
        repository_root = repository_root or root
        mode = "colocated" if git and jj else "git" if git else "jj"
        continuity = str(repository_root)
        repository_key = self.ledger.repository_key(continuity, writer_id=self.ledger.writer_id)
        observations = [item for item in (git, jj) if item is not None]
        history = [record for item in observations for record in item.history]
        workspaces = _merge_workspaces(git, jj)
        git_refs = git.refs if git else ()
        jj_refs = jj.bookmarks if jj else ()
        refs = _dedupe_dicts(
            [*git_refs, *jj_refs],
            lambda item: f"{item.get('name')}:{item.get('remote')}:{item.get('authority', '')}",
        )
        roots = []
        for ref in refs:
            for field in ("peeled_object_id", "object_id", "targets"):
                value = ref.get(field)
                targets = [value] if isinstance(value, dict) else value or []
                roots.extend(target for target in targets if target)
        for workspace in workspaces:
            current = workspace.get("current") or {}
            if current.get("object_id"):
                roots.append(current["object_id"])
        roots = list(_dedupe_dicts(roots, lambda item: f"{item['algorithm']}:{item['value']}"))
        collection = self._collection(git, jj)
        boundary = self._boundary(git, jj)
        return {
            "repository_key": repository_key,
            "mode": mode,
            "store": {
                "backend": "git",
                "object_format": "sha1",
                "native_hint": jj.store_hint if jj else None,
            },
            "locations": [
                {
                    "path": str(repository_root),
                    "relative_path": "."
                    if repository_root == root
                    else repository_root.relative_to(root).as_posix(),
                    "role": "primary",
                }
            ],
            "collection": collection,
            "history_boundary": boundary.to_dict(),
            "workspaces": list(workspaces),
            "refs": list(refs),
            "roots": roots,
            "_history_objects": history,
        }

    def _collection(
        self,
        git: GitObservation | None,
        jj: JjObservation | None,
    ) -> dict[str, dict[str, Any]]:
        result: dict[str, CollectionOutcome] = {}
        for observation in (git, jj):
            if observation:
                result.update(observation.collection)
        if git and jj:
            result["workspaces"] = jj.collection.get("workspaces", _complete())
            result["refs"] = git.collection.get("refs", _complete())
            result["history"] = CollectionOutcome(
                CollectionState.PARTIAL
                if any(
                    item.state is CollectionState.PARTIAL
                    for item in (
                        git.collection.get("history", _complete()),
                        jj.collection.get("history", _complete()),
                    )
                )
                else CollectionState.COMPLETE
            )
        return {name: outcome.to_dict() for name, outcome in sorted(result.items())}

    def _boundary(self, git: GitObservation | None, jj: JjObservation | None) -> HistoryBoundary:
        boundaries = [item.history_boundary for item in (git, jj) if item]
        if any(item.state is HistoryBoundaryState.SHALLOW for item in boundaries):
            return next(item for item in boundaries if item.state is HistoryBoundaryState.SHALLOW)
        if any(item.state is HistoryBoundaryState.UNKNOWN for item in boundaries):
            return HistoryBoundary(HistoryBoundaryState.UNKNOWN)
        return HistoryBoundary(HistoryBoundaryState.COMPLETE)


__all__ = ["SnapshotCollector", "SnapshotResult", "discover_repository_roots"]
