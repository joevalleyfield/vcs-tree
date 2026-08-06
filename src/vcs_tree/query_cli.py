"""Command orchestration and deterministic renderers for history queries."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .ledger import HistoryLedger
from .predicate_evaluator import PredicateEvaluator
from .predicate_models import HistoryQuery
from .snapshot import SnapshotCollector
from .temporal import TemporalIndexBuilder


class QueryExecutionError(RuntimeError):
    """Evaluation failed after an optional capture; target remains observable."""

    def __init__(self, message: str, *, snapshot_id: str | None):
        super().__init__(message)
        self.snapshot_id = snapshot_id


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_query(where: str | None, where_file: str | None) -> HistoryQuery:
    if (where is None) == (where_file is None):
        raise ValueError("exactly one of --where or --where-file is required")
    text = (
        where
        if where is not None
        else (__import__("sys").stdin.read() if where_file == "-" else Path(where_file).read_text())
    )
    try:
        value = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid query JSON: {exc}") from exc
    try:
        return HistoryQuery.from_dict(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid query schema: {exc}") from exc


def _cache_path(ledger: HistoryLedger, generation: int) -> Path | None:
    paths = getattr(ledger, "paths", None)
    cache_root = getattr(paths, "cache_root", None)
    store_id = getattr(ledger, "store_id", None)
    if cache_root is None or not store_id:
        return None
    token = hashlib.sha256(str(store_id).encode()).hexdigest()[:16]
    return Path(cache_root) / "temporal-index" / f"{token}-{generation}.json"


def _cached_index(path: Path | None, store_id: str, generation: int) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return None
    if (
        isinstance(value, dict)
        and value.get("schema") == "vcs-tree.temporal-facts"
        and value.get("schema_version") == 1
        and value.get("store_id") == store_id
        and value.get("source_generation") == generation
    ):
        return value
    return None


def _store_cached_index(path: Path | None, index: dict[str, Any]) -> None:
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_text(json.dumps(index, sort_keys=True), encoding="utf-8")
        temporary.replace(path)
    except OSError:
        return


def _index_for_snapshot(
    ledger: HistoryLedger,
    snapshot_id: str | None,
    *,
    progress: Callable[[str], None] | None = None,
) -> tuple[dict[str, Any], str | None]:
    if snapshot_id is None:
        return ledger.read_temporal_index(), None
    entries = ledger.read_snapshots()
    selected = next((item for item in entries if item.get("snapshot_id") == snapshot_id), None)
    if selected is None:
        raise ValueError(f"snapshot not found: {snapshot_id}")
    manifest = selected.get("manifest")
    if not isinstance(manifest, dict):
        raise ValueError(f"snapshot has no retained manifest: {snapshot_id}")
    store = manifest.get("history_store")
    if not isinstance(store, dict) or store.get("store_id") != ledger.store_id:
        raise ValueError("snapshot belongs to a different history store")
    if manifest.get("schema") != "vcs-tree.history-snapshot" or manifest.get(
        "schema_version"
    ) not in (1, 2):
        raise ValueError("unsupported retained snapshot schema")
    generation = selected.get("generation")
    if not isinstance(generation, int):
        raise ValueError("snapshot has no valid generation")
    eligible = [
        item
        for item in entries
        if isinstance(item.get("generation"), int) and item["generation"] <= generation
    ]
    cache = _cache_path(ledger, generation)
    index = _cached_index(cache, ledger.store_id, generation)
    if index is not None:
        if progress:
            progress(f"temporal index: cache hit for generation {generation}")
    else:
        if progress:
            progress(f"temporal index: cache miss for generation {generation}")
        index = TemporalIndexBuilder().build(
            eligible,
            objects=ledger.read_objects(),
            store_id=ledger.store_id,
            progress=progress,
        )
        _store_cached_index(cache, index)
    index["source_generation"] = generation
    return index, snapshot_id


def execute_query(
    ledger: HistoryLedger,
    query: HistoryQuery,
    *,
    path: str | Path = ".",
    snapshot_id: str | None = None,
    capture: bool = False,
    evaluated_at: str | None = None,
    collector: SnapshotCollector | None = None,
    progress: Callable[[str], None] | None = None,
) -> tuple[dict[str, Any], str | None]:
    if capture and snapshot_id is not None:
        raise ValueError("--capture cannot be combined with --snapshot")
    target = snapshot_id
    performed = capture
    if capture:
        result = (collector or SnapshotCollector(ledger)).collect(Path(path).resolve())
        target = result.envelope.snapshot_id
        index = (
            ledger.read_temporal_index(progress=progress)
            if progress
            else ledger.read_temporal_index()
        )
    elif snapshot_id is not None:
        index, _ = (
            _index_for_snapshot(ledger, snapshot_id, progress=progress)
            if progress
            else _index_for_snapshot(ledger, snapshot_id)
        )
    else:
        entries = ledger.read_snapshots()
        retained = [item for item in entries if isinstance(item.get("generation"), int)]
        target = max(
            retained,
            key=lambda item: (item["generation"], str(item.get("snapshot_id", ""))),
            default={},
        ).get("snapshot_id")
        index = (
            ledger.read_temporal_index(progress=progress)
            if progress
            else ledger.read_temporal_index()
        )
    try:
        evaluated = PredicateEvaluator().evaluate(query, index, evaluated_at=evaluated_at or _now())
    except Exception as exc:
        raise QueryExecutionError(str(exc), snapshot_id=target) from exc
    evaluated["capture"] = {"snapshot_id": target, "performed": performed}
    return evaluated, target


def render_query(document: dict[str, Any], mode: str) -> str:
    if mode == "json":
        return json.dumps(document, indent=2, sort_keys=True)
    results = document.get("results", [])
    counts = {
        state: sum(item.get("outcome") == state for item in results)
        for state in ("true", "false", "indeterminate")
    }
    lines = [
        "history query ("
        f"{counts['true']} true, {counts['false']} false, "
        f"{counts['indeterminate']} indeterminate)",
        f"snapshot: {document.get('capture', {}).get('snapshot_id')}",
    ]
    if mode == "summary":
        if counts["false"]:
            lines.append(
                f"{counts['false']} false repository result(s) omitted; use --format audit"
            )
        for item in results:
            if item.get("outcome") != "false":
                lines.append(f"{item.get('repository_key')}: {item.get('outcome')}")
        return "\n".join(lines)
    for item in results:
        lines.append(f"{item.get('repository_key')}: {item.get('outcome')}")
        lines.append(json.dumps(item, sort_keys=True))
    return "\n".join(lines)


__all__ = ["QueryExecutionError", "execute_query", "read_query", "render_query"]
