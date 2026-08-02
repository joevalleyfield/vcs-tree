"""Read-only orchestration for recurring movement pulses."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .delta import HistoryDeltaCalculator
from .ledger import HistoryLedger
from .models import (
    CollectionOutcome,
    CollectionState,
    ContractError,
    PulseEnvelope,
    SnapshotEnvelope,
)
from .snapshot import SnapshotCollector


class PulseSelectionError(ContractError):
    """Raised when an explicit or automatic pulse source is not comparable."""

    def __init__(self, reason: str, message: str | None = None):
        self.reason = reason
        super().__init__(message or reason)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _root(manifest: Mapping[str, Any] | SnapshotEnvelope) -> str:
    scan = manifest.scan if isinstance(manifest, SnapshotEnvelope) else manifest.get("scan", {})
    value = scan.get("root")
    return str(Path(value).resolve()) if isinstance(value, str) else ""


def _entry_manifest(entry: Mapping[str, Any]) -> SnapshotEnvelope:
    manifest = entry.get("manifest")
    if not isinstance(manifest, Mapping):
        raise PulseSelectionError("snapshot_not_found", "snapshot has no retained manifest")
    try:
        return SnapshotEnvelope.from_dict(manifest)
    except ContractError as exc:
        raise PulseSelectionError("unsupported_schema", str(exc)) from exc


class PulseOrchestrator:
    """Capture one target and compare it with one pre-capture source."""

    def __init__(
        self,
        ledger: HistoryLedger,
        *,
        collector_factory: Callable[[HistoryLedger], SnapshotCollector] = SnapshotCollector,
        delta_factory: Callable[[HistoryLedger], HistoryDeltaCalculator] = HistoryDeltaCalculator,
        clock: Callable[[], str] = _now,
        pulse_id_factory: Callable[[str], str] | None = None,
    ):
        self.ledger = ledger
        self.collector_factory = collector_factory
        self.delta_factory = delta_factory
        self.clock = clock
        self.pulse_id_factory = pulse_id_factory or (lambda snapshot_id: f"pulse-{snapshot_id}")

    def run(self, path: str | Path, *, from_snapshot: str | None = None) -> PulseEnvelope:
        scope = str(Path(path).resolve())
        entries = self.ledger.read_snapshots()
        candidates = self._candidates(entries, scope)
        source, selection = self._select(candidates, scope, from_snapshot)
        target_result = self.collector_factory(self.ledger).collect(scope)
        target = target_result.envelope
        if source is None:
            return self._baseline(target)
        if source.history_store.generation >= target.history_store.generation:
            raise PulseSelectionError("source_not_earlier")
        delta = self.delta_factory(self.ledger).calculate(source, target)
        return self._selected(source, target, delta, selection)

    def _candidates(
        self, entries: Iterable[Mapping[str, Any]], scope: str
    ) -> list[tuple[Mapping[str, Any], SnapshotEnvelope]]:
        result = []
        for entry in entries:
            try:
                manifest = _entry_manifest(entry)
            except PulseSelectionError:
                continue
            if manifest.history_store.store_id != self.ledger.store_id:
                continue
            if _root(manifest) != scope:
                continue
            result.append((entry, manifest))
        return result

    def _select(
        self,
        candidates: list[tuple[Mapping[str, Any], SnapshotEnvelope]],
        scope: str,
        requested: str | None,
    ) -> tuple[SnapshotEnvelope | None, str]:
        if requested is not None:
            all_entries = self.ledger.read_snapshots()
            entry = next(
                (item for item in all_entries if item.get("snapshot_id") == requested), None
            )
            if entry is None:
                raise PulseSelectionError("snapshot_not_found")
            manifest = _entry_manifest(entry)
            if manifest.history_store.store_id != self.ledger.store_id:
                raise PulseSelectionError("store_mismatch")
            if _root(manifest) != scope:
                raise PulseSelectionError("scope_mismatch")
            if manifest.history_store.generation > self.ledger.generation:
                raise PulseSelectionError("source_not_earlier")
            return manifest, "explicit"
        if not candidates:
            return None, "none"
        return max(
            (manifest for _entry, manifest in candidates),
            key=lambda item: (item.history_store.generation, item.captured_at, item.snapshot_id),
        ), "automatic"

    def _baseline(self, target: SnapshotEnvelope) -> PulseEnvelope:
        outcome = _scan_outcome(target)
        return PulseEnvelope(
            self.pulse_id_factory(target.snapshot_id),
            self.clock(),
            {"root": target.scan.get("root")},
            _target_info(target),
            {"state": "baseline_created", "selection": "none"},
            outcome,
            {"state": "baseline", "repository_count": len(target.repositories)},
            tuple(_pulse_repository(item, ()) for item in target.repositories),
            (),
            _summary(len(target.repositories), 0, 0, 0),
        )

    def _selected(
        self,
        source: SnapshotEnvelope,
        target: SnapshotEnvelope,
        delta: Any,
        selection: str,
    ) -> PulseEnvelope:
        repositories = tuple(
            sorted(
                (
                    _pulse_repository(item, item.get("events", ()))
                    for item in delta.repository_deltas
                ),
                key=lambda item: (str(item.get("path", "")), str(item.get("repository_key", ""))),
            )
        )
        movement_count = sum(bool(item["events"]) for item in repositories)
        outcome = _combine_outcomes(target, delta.outcome)
        movement_state = (
            "observed"
            if movement_count
            else ("unknown" if outcome.state is CollectionState.PARTIAL else "empty")
        )
        return PulseEnvelope(
            self.pulse_id_factory(target.snapshot_id),
            self.clock(),
            {"root": target.scan.get("root")},
            _target_info(target),
            {
                "state": "selected",
                "selection": selection,
                "source_snapshot_id": source.snapshot_id,
                "source_generation": source.history_store.generation,
            },
            outcome,
            {"state": movement_state, "repository_count": movement_count},
            repositories,
            (),
            _summary(
                len(repositories),
                movement_count,
                sum(not item["events"] for item in repositories),
                0,
            ),
        )


def _target_info(target: SnapshotEnvelope) -> dict[str, Any]:
    return {
        "snapshot_id": target.snapshot_id,
        "generation": target.history_store.generation,
        "captured_at": target.captured_at,
    }


def _scan_outcome(target: SnapshotEnvelope) -> CollectionOutcome:
    raw = target.scan.get("outcome", {"state": "complete", "errors": []})
    return CollectionOutcome.from_dict(raw)


def _combine_outcomes(target: SnapshotEnvelope, delta: CollectionOutcome) -> CollectionOutcome:
    scan = _scan_outcome(target)
    if scan.state is CollectionState.ERROR or delta.state is CollectionState.ERROR:
        return CollectionOutcome(CollectionState.ERROR, scan.errors + delta.errors)
    if scan.state is CollectionState.PARTIAL or delta.state is CollectionState.PARTIAL:
        return CollectionOutcome(CollectionState.PARTIAL, scan.errors + delta.errors)
    return CollectionOutcome(CollectionState.COMPLETE)


def _pulse_repository(
    repository: Mapping[str, Any], events: Iterable[Mapping[str, Any]]
) -> dict[str, Any]:
    path = repository.get("path")
    if path is None:
        locations = repository.get("locations", ())
        if locations and isinstance(locations[0], Mapping):
            path = locations[0].get("relative_path", locations[0].get("path"))
    return {
        "repository_key": repository.get("repository_key"),
        "path": path,
        "mode": repository.get("mode"),
        "events": list(events),
        "descriptions": [],
        "path_evidence": [],
        "task_path_events": [],
        "warning_keys": [],
    }


def _summary(observed: int, movement: int, no_ops: int, task_events: int) -> dict[str, int]:
    return {
        "observed_repositories": observed,
        "movement_repositories": movement,
        "no_op_repositories": no_ops,
        "task_path_events": task_events,
        "new_warnings": 0,
        "persistent_warnings": 0,
        "recovered_warnings": 0,
    }


__all__ = ["PulseOrchestrator", "PulseSelectionError"]
