"""Read-only orchestration for recurring movement pulses."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .delta import HistoryDeltaCalculator
from .enrichment import EnrichmentResult, PulseEnricher
from .ledger import HistoryLedger
from .models import (
    CollectionOutcome,
    CollectionState,
    ContractError,
    PulseEnvelope,
    SnapshotEnvelope,
)
from .pulse_semantics import classify_task_paths, classify_warning_lifecycles
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
        enricher_factory: Callable[[HistoryLedger], PulseEnricher] = PulseEnricher,
        clock: Callable[[], str] = _now,
        pulse_id_factory: Callable[[str], str] | None = None,
    ):
        self.ledger = ledger
        self.collector_factory = collector_factory
        self.delta_factory = delta_factory
        self.enricher_factory = enricher_factory
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
        try:
            enrichment = self.enricher_factory(self.ledger).enrich(delta)
        except AttributeError:
            enrichment = EnrichmentResult(
                tuple(delta.repository_deltas), CollectionOutcome(CollectionState.COMPLETE)
            )
        return self._selected(source, target, delta, enrichment, selection)

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
        enrichment: Any,
        selection: str,
    ) -> PulseEnvelope:
        source_warnings = _snapshot_warnings(source)
        target_warnings = _snapshot_warnings(target)
        comparison_warnings = _delta_warnings(delta)
        enrichment_warnings = tuple(
            {**warning, "repository_key": "@scan", "component": "enrichment"}
            for warning in enrichment.warnings
        )
        lifecycle = classify_warning_lifecycles(
            source_warnings,
            target_warnings,
            (*comparison_warnings, *enrichment_warnings),
        )
        enriched_by_key = {
            str(item.get("repository_key")): item for item in enrichment.repositories
        }
        repositories = tuple(
            sorted(
                (
                    _pulse_repository(
                        enriched_by_key.get(str(item.get("repository_key")), item),
                        item.get("events", ()),
                        lifecycle,
                    )
                    for item in delta.repository_deltas
                ),
                key=lambda item: (str(item.get("path", "")), str(item.get("repository_key", ""))),
            )
        )
        movement_count = sum(
            any(event.get("event") != "comparison_incomplete" for event in item["events"])
            for item in repositories
        )
        outcome = _combine_outcomes(target, delta.outcome, enrichment.outcome)
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
            lifecycle,
            _summary(
                len(repositories),
                movement_count,
                sum(
                    not any(
                        event.get("event") != "comparison_incomplete" for event in item["events"]
                    )
                    for item in repositories
                ),
                sum(len(item["task_path_events"]) for item in repositories),
                lifecycle,
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


def _combine_outcomes(
    target: SnapshotEnvelope, delta: CollectionOutcome, enrichment: CollectionOutcome | None = None
) -> CollectionOutcome:
    scan = _scan_outcome(target)
    outcomes = (scan, delta, enrichment) if enrichment is not None else (scan, delta)
    if any(item.state is CollectionState.ERROR for item in outcomes):
        return CollectionOutcome(
            CollectionState.ERROR, tuple(error for item in outcomes for error in item.errors)
        )
    if any(item.state is CollectionState.PARTIAL for item in outcomes):
        return CollectionOutcome(
            CollectionState.PARTIAL, tuple(error for item in outcomes for error in item.errors)
        )
    return CollectionOutcome(CollectionState.COMPLETE)


def _pulse_repository(
    repository: Mapping[str, Any],
    events: Iterable[Mapping[str, Any]],
    warnings: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    path = repository.get("path")
    if path is None:
        locations = repository.get("locations", ())
        if locations and isinstance(locations[0], Mapping):
            path = locations[0].get("relative_path", locations[0].get("path"))
    path_evidence = list(repository.get("path_evidence", ()))
    task_events = list(classify_task_paths(path_evidence))
    warning_items = [
        item
        for item in warnings
        if item.get("repository_key") in {None, repository.get("repository_key")}
    ]
    return {
        "repository_key": repository.get("repository_key"),
        "path": path,
        "mode": repository.get("mode"),
        "events": list(events),
        "descriptions": list(repository.get("descriptions", ())),
        "path_evidence": path_evidence,
        "task_path_events": task_events,
        "warning_keys": sorted(item["warning_key"] for item in warning_items),
    }


def _summary(
    observed: int,
    movement: int,
    no_ops: int,
    task_events: int,
    warnings: Iterable[Mapping[str, Any]] = (),
) -> dict[str, int]:
    return {
        "observed_repositories": observed,
        "movement_repositories": movement,
        "no_op_repositories": no_ops,
        "task_path_events": task_events,
        "new_warnings": sum(item.get("lifecycle") == "new" for item in warnings),
        "persistent_warnings": sum(item.get("lifecycle") == "persistent" for item in warnings),
        "recovered_warnings": sum(item.get("lifecycle") == "recovered" for item in warnings),
    }


def _snapshot_warnings(snapshot: SnapshotEnvelope) -> tuple[dict[str, Any], ...]:
    warnings = []
    for repository in snapshot.repositories:
        key = repository.get("repository_key")
        for component, outcome in repository.get("collection", {}).items():
            if outcome.get("state") in {"complete", "not_requested"}:
                continue
            for error in outcome.get("errors", ()):
                warnings.append(
                    {
                        "repository_key": key,
                        "component": component,
                        "kind": error.get("kind", "collection_error"),
                        "stage": error.get("stage", component),
                        "affected_event_class": component,
                        "message": error.get("message"),
                    }
                )
        boundary = repository.get("history_boundary", {}).get("state", "complete")
        if boundary != "complete":
            warnings.append(
                {
                    "repository_key": key,
                    "component": "history",
                    "kind": "boundary",
                    "stage": boundary,
                    "affected_event_class": "ancestry",
                }
            )
    return tuple(warnings)


def _delta_warnings(delta: Any) -> tuple[dict[str, Any], ...]:
    warnings = []
    for repository in delta.repository_deltas:
        key = repository.get("repository_key")
        for event in repository.get("events", ()):
            if event.get("event") == "comparison_incomplete":
                details = event.get("details", {})
                warnings.append(
                    {
                        "repository_key": key,
                        "component": details.get("component", "delta"),
                        "kind": "comparison_incomplete",
                        "stage": "delta",
                        "affected_event_class": ",".join(
                            sorted(details.get("suppressed_events", ()))
                        )
                        or "-",
                    }
                )
    return tuple(warnings)


__all__ = ["PulseOrchestrator", "PulseSelectionError"]
