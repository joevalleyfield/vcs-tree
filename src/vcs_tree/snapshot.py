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
    ObservationOutcome,
    SnapshotEnvelopeV2,
)

AdapterFactory = Callable[[Path], Any]


@dataclass(frozen=True)
class SnapshotResult:
    envelope: SnapshotEnvelopeV2
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
    git: GitObservation | None, jj: JjObservation | None, attempted_at: str
) -> tuple[dict[str, Any], ...]:
    """Merge colocated Git worktrees and jj workspaces by canonical path."""
    merged: dict[str, dict[str, Any]] = {}
    for observation in (git, jj):
        if observation is None:
            continue
        for workspace in observation.workspaces:
            item = dict(workspace)
            working_copy = item.get("working_copy")
            if not isinstance(working_copy, dict) or "outcome" not in working_copy:
                state = (
                    working_copy.get("state", "unknown")
                    if isinstance(working_copy, dict)
                    else "unknown"
                )
                has_evidence = isinstance(working_copy, dict)
                outcome = (
                    {
                        "state": "complete",
                        "attempted_at": observation.observed_at or attempted_at,
                        "errors": [],
                    }
                    if has_evidence
                    else _not_requested()
                )
                item["working_copy"] = {
                    "state": state,
                    "recorded_state": state,
                    "outcome": outcome,
                    "refresh": {"state": "not_applicable", "errors": []},
                    "freshness": "current" if has_evidence else "not_applicable",
                    "entries_outcome": _not_requested(),
                    "entries_limit": 0,
                    "entries_truncated": False,
                    "entries": [],
                }
            key = _workspace_key(item)
            merged[key] = {**merged.get(key, {}), **item}
    for key, workspace in merged.items():
        workspace.setdefault("workspace_key", key)
    return tuple(merged[key] for key in sorted(merged))


def _observation_outcome(outcome: CollectionOutcome, attempted_at: str) -> dict[str, Any]:
    return ObservationOutcome(
        outcome.state,
        None if outcome.state is CollectionState.NOT_REQUESTED else attempted_at,
        outcome.errors,
    ).to_dict()


def _not_requested() -> dict[str, Any]:
    return ObservationOutcome(CollectionState.NOT_REQUESTED).to_dict()


def _native_outcome(
    observation: GitObservation | JjObservation | None,
    name: str,
    fallback_at: str,
) -> dict[str, Any]:
    if observation is None:
        return _not_requested()
    outcome = observation.collection.get(name)
    if outcome is None:
        return _not_requested()
    return _observation_outcome(outcome, observation.observed_at or fallback_at)


def _combine_outcomes(outcomes: list[CollectionOutcome]) -> CollectionOutcome:
    if not outcomes:
        return CollectionOutcome(CollectionState.NOT_REQUESTED)
    errors = tuple(error for outcome in outcomes for error in outcome.errors)
    if any(outcome.state is CollectionState.ERROR for outcome in outcomes):
        return CollectionOutcome(CollectionState.ERROR, errors)
    if any(outcome.state is CollectionState.PARTIAL for outcome in outcomes):
        return CollectionOutcome(CollectionState.PARTIAL, errors)
    if all(outcome.state is CollectionState.NOT_REQUESTED for outcome in outcomes):
        return CollectionOutcome(CollectionState.NOT_REQUESTED)
    return CollectionOutcome(CollectionState.COMPLETE)


def _change_graph(jj: JjObservation | None) -> dict[str, Any] | None:
    """Build per-snapshot jj change membership without naming synthetic stacks."""
    if jj is None:
        return None
    changes: dict[str, dict[str, Any]] = {}
    for record in jj.history:
        change_id = record.get("change_id")
        if not change_id or record.get("kind") == "virtual_root":
            continue
        versions = changes.setdefault(change_id, {"change_id": change_id, "versions": []})[
            "versions"
        ]
        versions.append(
            {
                "object_id": record["object_id"],
                "visibility": record.get("visibility", "unknown"),
                "authorities": list(record.get("authorities", ())),
                "parents": list(record.get("parent_changes", ())),
            }
        )
    for change in changes.values():
        change["versions"] = sorted(change["versions"], key=lambda item: item["object_id"]["value"])
    return {
        "changes": [changes[key] for key in sorted(changes)],
        "visible_heads": list(jj.visible_heads),
        "outcome": jj.collection.get("history", _complete()).to_dict(),
    }


def _publication_hints(git: GitObservation | None, jj: JjObservation | None) -> dict[str, Any]:
    """Keep Git refs and jj bookmarks as separate provenance-bearing hints."""
    git_refs = [
        {**ref, "publication_kind": "git_ref", "publication_hint": True}
        for ref in (git.refs if git else ())
    ]
    bookmarks = []
    for bookmark in jj.bookmarks if jj else ():
        bookmarks.append(
            {
                **bookmark,
                "publication_kind": "jj_bookmark",
                "publication_hint": True,
                "provenance": "observed_remote" if bookmark.get("remote") else "local",
            }
        )
    return {
        "git_refs": git_refs,
        "jj_bookmarks": bookmarks,
        "outcomes": {
            "git_refs": git.collection.get("refs", _complete()).to_dict()
            if git
            else _complete().to_dict(),
            "jj_bookmarks": jj.collection.get("bookmarks", _complete()).to_dict()
            if jj
            else _complete().to_dict(),
        },
    }


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
        progress: Callable[[str], None] | None = None,
    ):
        self.ledger = ledger
        self.git_factory = git_factory
        self.jj_factory = jj_factory
        self.clock = clock
        self.snapshot_id_factory = snapshot_id_factory or (lambda: f"snapshot-{uuid4().hex}")
        self.progress = progress or (lambda _message: None)

    def collect(self, path: str | Path) -> SnapshotResult:
        root = Path(path).resolve()
        captured_at = self.clock()
        self.progress(f"discovering repositories under {root}")
        roots, discovery_errors = _discover(root)
        self.progress(f"discovered {len(roots)} repository root(s)")
        repositories = []
        objects: list[dict[str, Any]] = []
        for repository_root in roots:
            self.progress(f"collecting {repository_root}")
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
                root,
                git_observation,
                jj_observation,
                repository_root=repository_root,
                captured_at=captured_at,
            )
            objects.extend(
                _as_objects(repository["repository_key"], repository.pop("_history_objects"))
            )
            repositories.append(repository)
        self.progress("persisting history objects and generation")
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
        envelope = SnapshotEnvelopeV2(
            self.snapshot_id_factory(),
            captured_at,
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
        self.progress(f"completed snapshot {envelope.snapshot_id} ({scan_outcome.state.value})")
        return SnapshotResult(envelope, generation)

    def _repository(
        self,
        root: Path,
        git: GitObservation | None,
        jj: JjObservation | None,
        repository_root: Path | None = None,
        captured_at: str | None = None,
    ) -> dict[str, Any]:
        repository_root = repository_root or root
        captured_at = captured_at or self.clock()
        mode = "colocated" if git and jj else "git" if git else "jj"
        continuity = str(repository_root)
        repository_key = self.ledger.repository_key(continuity, writer_id=self.ledger.writer_id)
        observations = [item for item in (git, jj) if item is not None]
        history = [record for item in observations for record in item.history]
        if git and jj:
            git_ids = {
                item["object_id"]["value"]: item["object_id"]
                for item in git.history
                if item.get("kind") != "virtual_root"
            }
            history = [
                {
                    **record,
                    **(
                        {"git_object_id": git_ids[record["object_id"]["value"]]}
                        if record.get("object_id", {}).get("value") in git_ids
                        and record.get("kind") != "virtual_root"
                        else {}
                    ),
                }
                for record in history
            ]
        workspaces = _merge_workspaces(git, jj, captured_at)
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
        collection = self._collection(git, jj, captured_at)
        boundary = self._boundary(git, jj)
        return {
            "repository_key": repository_key,
            "mode": mode,
            "store": {
                "backend": "git",
                "object_format": "sha1",
                "native_hint": jj.store_hint if jj else None,
            },
            "workspace_family": (
                jj.workspace_family
                if jj
                else {
                    "family_id": None,
                    "kind": "jj_operation_store",
                    "source": "config-id",
                    "outcome": _not_requested(),
                }
            ),
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
            "bookmarks": list(jj_refs),
            "roots": roots,
            "publication_hints": _publication_hints(git, jj),
            "change_graph": _change_graph(jj),
            "_history_objects": history,
        }

    def _collection(
        self,
        git: GitObservation | None,
        jj: JjObservation | None,
        captured_at: str,
    ) -> dict[str, dict[str, Any]]:
        result: dict[str, CollectionOutcome] = {}
        for observation in (git, jj):
            if observation:
                result.update(observation.collection)
        if git and jj:
            result["workspaces"] = jj.collection.get("workspaces", _complete())
            result["refs"] = git.collection.get("refs", _complete())
            result["history"] = _combine_outcomes(
                [
                    git.collection.get("history", _complete()),
                    jj.collection.get("history", _complete()),
                ]
            )
        presentation = {name: outcome.to_dict() for name, outcome in sorted(result.items())}
        identity = _combine_outcomes(
            [
                observation.collection["identity"]
                for observation in (git, jj)
                if observation is not None and "identity" in observation.collection
            ]
        )
        path_outcome = _combine_outcomes(
            [
                observation.collection["path_evidence"]
                for observation in (git, jj)
                if observation is not None and "path_evidence" in observation.collection
            ]
        )
        presentation.update(
            {
                "identity": _observation_outcome(identity, captured_at),
                "git_worktrees": _native_outcome(git, "workspaces", captured_at),
                "jj_workspaces": _native_outcome(jj, "workspaces", captured_at),
                "git_refs": _native_outcome(git, "refs", captured_at),
                "jj_bookmarks": _native_outcome(jj, "bookmarks", captured_at),
                "jj_visible_heads": _native_outcome(jj, "visible_heads", captured_at),
                "git_history": _native_outcome(git, "history", captured_at),
                "jj_history": _native_outcome(jj, "history", captured_at),
                "path_evidence": _observation_outcome(path_outcome, captured_at),
            }
        )
        return dict(sorted(presentation.items()))

    def _boundary(self, git: GitObservation | None, jj: JjObservation | None) -> HistoryBoundary:
        boundaries = [item.history_boundary for item in (git, jj) if item]
        if any(item.state is HistoryBoundaryState.SHALLOW for item in boundaries):
            return next(item for item in boundaries if item.state is HistoryBoundaryState.SHALLOW)
        if any(item.state is HistoryBoundaryState.UNKNOWN for item in boundaries):
            return HistoryBoundary(HistoryBoundaryState.UNKNOWN)
        return HistoryBoundary(HistoryBoundaryState.COMPLETE)


__all__ = ["SnapshotCollector", "SnapshotResult", "discover_repository_roots"]
