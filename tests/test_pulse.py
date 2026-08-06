from dataclasses import dataclass

import pytest

from vcs_tree.enrichment import EnrichmentResult
from vcs_tree.models import CollectionOutcome, CollectionState, HistoryStore, SnapshotEnvelope
from vcs_tree.pulse import (
    PulseOrchestrator,
    PulseSelectionError,
    _now,
    _pulse_repository,
    _snapshot_warnings,
)
from vcs_tree.snapshot import SnapshotResult


def snapshot(sid, generation, root="/workspace", store="ledger"):
    return SnapshotEnvelope(
        sid,
        f"2026-08-02T12:{generation:02d}:00Z",
        {"name": "vcs-tree", "version": "0.1.0"},
        HistoryStore(store, generation, writer_id="writer"),
        {"root": root, "outcome": {"state": "complete", "errors": []}},
        ({"repository_key": "repo-1", "mode": "git", "locations": [{"relative_path": "."}]},),
    )


@dataclass
class FakeLedger:
    entries: list
    generation: int = 3
    store_id: str = "ledger"

    def read_snapshots(self):
        return self.entries


class FakeCollector:
    def __init__(self, target):
        self.target = target

    def collect(self, path):
        return SnapshotResult(self.target, self.target.history_store.generation)


class FakeDelta:
    def __init__(self, outcome=None, repositories=()):
        self.outcome = outcome or CollectionOutcome(CollectionState.COMPLETE)
        self.repository_deltas = repositories


def entry(document):
    return {
        "snapshot_id": document.snapshot_id,
        "generation": document.history_store.generation,
        "manifest": document.to_dict(),
    }


def orchestrator(ledger, target, delta=None, enrichment=None):
    return PulseOrchestrator(
        ledger,
        collector_factory=lambda _: FakeCollector(target),
        delta_factory=lambda _: type(
            "Delta", (), {"calculate": lambda self, source, target: delta or FakeDelta()}
        )(),
        enricher_factory=lambda _: type(
            "Enricher",
            (),
            {
                "enrich": lambda self, value: (
                    enrichment
                    or EnrichmentResult(
                        tuple(value.repository_deltas),
                        CollectionOutcome(CollectionState.COMPLETE),
                    )
                )
            },
        )(),
        clock=lambda: "2026-08-02T13:00:00Z",
        pulse_id_factory=lambda sid: f"pulse-{sid}",
    )


def test_first_observation_creates_baseline_without_delta():
    target = snapshot("target", 4)
    result = orchestrator(FakeLedger([]), target).run("/workspace")
    assert result.comparison["state"] == "baseline_created"
    assert result.movement["state"] == "baseline"
    assert result.summary["movement_repositories"] == 0
    assert _now().endswith("Z")


def test_automatic_selection_uses_latest_comparable_and_keeps_partial_delta():
    source = snapshot("source", 3)
    target = snapshot("target", 4)
    partial = FakeDelta(
        CollectionOutcome(CollectionState.PARTIAL),
        (
            {
                "repository_key": "repo-1",
                "path": ".",
                "mode": "git",
                "events": [{"event": "x"}],
            },
        ),
    )
    result = orchestrator(FakeLedger([entry(source)]), target, partial).run("/workspace")
    assert result.comparison["source_snapshot_id"] == "source"
    assert result.outcome.state is CollectionState.PARTIAL
    assert result.movement["state"] == "observed"


def test_explicit_selection_reports_failures_without_capture():
    target = snapshot("target", 4)
    ledger = FakeLedger([entry(snapshot("other", 3, "/other"))])
    with pytest.raises(PulseSelectionError, match="snapshot_not_found"):
        orchestrator(ledger, target).run("/workspace", from_snapshot="missing")
    with pytest.raises(PulseSelectionError, match="scope_mismatch"):
        orchestrator(ledger, target).run("/workspace", from_snapshot="other")


def test_store_mismatch_and_source_order_are_rejected():
    target = snapshot("target", 4)
    mismatched = snapshot("source", 3, store="other")
    with pytest.raises(PulseSelectionError, match="store_mismatch"):
        orchestrator(FakeLedger([entry(mismatched)]), target).run(
            "/workspace", from_snapshot="source"
        )
    future = snapshot("future", 5)
    with pytest.raises(PulseSelectionError, match="source_not_earlier"):
        orchestrator(FakeLedger([entry(future)], generation=4), target).run(
            "/workspace", from_snapshot="future"
        )
    same_generation = snapshot("same", 4)
    with pytest.raises(PulseSelectionError, match="source_not_earlier"):
        orchestrator(FakeLedger([entry(same_generation)], generation=4), target).run(
            "/workspace", from_snapshot="same"
        )


def test_noop_complete_delta_is_empty_and_repositories_are_sorted():
    source = snapshot("source", 3)
    target = snapshot("target", 4)
    delta = FakeDelta(
        repositories=(
            {"repository_key": "b", "path": "z", "mode": "git", "events": []},
            {"repository_key": "a", "path": "a", "mode": "git", "events": []},
        )
    )
    result = orchestrator(FakeLedger([entry(source)]), target, delta).run(
        "/workspace", from_snapshot="source"
    )
    assert result.movement["state"] == "empty"
    assert result.comparison["selection"] == "explicit"
    assert [item["path"] for item in result.repositories] == ["a", "z"]


def test_invalid_candidates_are_ignored_and_error_outcome_is_preserved():
    target = snapshot("target", 4)
    ledger = FakeLedger([{"snapshot_id": "missing"}, {"manifest": {"schema": "bad"}}])
    result = orchestrator(ledger, target).run("/workspace")
    assert result.comparison["state"] == "baseline_created"
    error_target = SnapshotEnvelope(
        "target-error",
        "2026-08-02T12:04:00Z",
        {"name": "vcs-tree"},
        HistoryStore("ledger", 4, writer_id="writer"),
        {"root": "/workspace", "outcome": {"state": "error", "errors": []}},
        (),
    )
    source = snapshot("source", 3)
    delta = FakeDelta(CollectionOutcome(CollectionState.ERROR), ())
    result = orchestrator(FakeLedger([entry(source)]), error_target, delta).run("/workspace")
    assert result.outcome.state is CollectionState.ERROR


def test_pulse_repository_location_fallbacks():
    assert _pulse_repository({"repository_key": "a"}, ())["path"] is None
    assert (
        _pulse_repository({"repository_key": "a", "locations": [{"relative_path": "x"}]}, ())[
            "path"
        ]
        == "x"
    )


def test_pulse_repository_groups_change_events_with_native_evidence():
    repository = {
        "repository_key": "repo-1",
        "path": ".",
        "mode": "jj",
        "descriptions": [
            {"object_id": {"value": "v2"}, "change_id": "change-1", "summary": "rewrite"}
        ],
        "path_evidence": [
            {
                "object_id": {"value": "v2"},
                "parent_id": "v1",
                "paths": [{"status": "modified", "path": "tasks/open/item.md"}],
            },
            {
                "object_id": {"value": "v2"},
                "parent_id": "v1",
                "paths": [{"status": "modified", "path": "tasks/open/item.md"}],
            },
        ],
    }
    result = _pulse_repository(
        repository,
        [
            {
                "event": "change_versions_changed",
                "event_key": "change_versions_changed:change-1",
                "details": {
                    "change_id": "change-1",
                    "old_visible_commits": ["v1"],
                    "new_visible_commits": ["v2"],
                    "state": "rewritten",
                },
            },
            {"event": "comparison_incomplete", "details": {"component": "bookmarks"}},
        ],
    )
    assert len(result["movement_groups"]) == 1
    group = result["movement_groups"][0]
    assert group["change_id"] == "change-1"
    assert group["old_versions"] == ["v1"]
    assert group["new_versions"] == ["v2"]
    assert group["descriptions"][0]["summary"] == "rewrite"
    assert group["task_path_events"][0]["event"] == "task_path_modified"
    assert all(event["event"] != "comparison_incomplete" for event in group["events"])


def test_pulse_repository_groups_uncertainty_publication_and_malformed_detail():
    repository = {
        "repository_key": "repo-1",
        "descriptions": [{"object_id": "v1", "summary": ""}],
        "path_evidence": [{}, {"object_id": "v1", "parent_id": None, "paths": []}],
    }
    result = _pulse_repository(
        repository,
        [
            "ignored",
            {"event": "ref_target_changed", "details": {"old": {}, "new": {}}},
            {"event": "workspace_head_changed", "details": "opaque", "certainty": "indeterminate"},
        ],
    )
    assert [item["event"] for item in result["movement_groups"][0]["events"]] == [
        "ref_target_changed"
    ]
    uncertain = result["movement_groups"][1]
    assert uncertain["completeness"] == "partial"
    assert uncertain["uncertainty"] == ["workspace_head_changed"]


def test_jj_graph_movement_enrichment_and_task_paths_survive_partial_publication():
    source = snapshot("source", 3)
    target = snapshot("target", 4)
    event_repo = {
        "repository_key": "repo-1",
        "path": ".",
        "mode": "colocated",
        "events": [
            {"event": "change_versions_changed", "details": {"state": "rewritten"}},
            {"event": "comparison_incomplete", "details": {"component": "jj_bookmarks"}},
        ],
    }
    delta = FakeDelta(CollectionOutcome(CollectionState.PARTIAL), (event_repo,))
    enrichment = EnrichmentResult(
        (
            {
                **event_repo,
                "descriptions": [{"object_id": {"value": "v2"}, "summary": "rewrite"}],
                "path_evidence": [
                    {
                        "object_id": {"value": "v2"},
                        "parent_id": "v1",
                        "paths": [{"status": "modified", "path": "tasks/open/example.md"}],
                    }
                ],
            },
        ),
        CollectionOutcome(CollectionState.PARTIAL),
        (
            {
                "warning_key": "repo-1|enrichment|missing_object|ledger|description",
                "repository_key": "repo-1",
            },
        ),
    )
    result = orchestrator(FakeLedger([entry(source)]), target, delta, enrichment).run("/workspace")
    assert result.movement["state"] == "observed"
    assert result.outcome.state is CollectionState.PARTIAL
    assert result.repositories[0]["descriptions"]
    assert result.repositories[0]["task_path_events"][0]["event"] == "task_path_modified"
    assert result.summary["task_path_events"] == 1
    assert result.warnings[0]["lifecycle"] == "new"


def test_warning_only_comparison_is_unknown_not_observed():
    source = snapshot("source", 3)
    target = snapshot("target", 4)
    repo_data = {
        "repository_key": "repo-1",
        "path": ".",
        "mode": "jj",
        "events": [{"event": "comparison_incomplete", "details": {"component": "bookmarks"}}],
    }
    result = orchestrator(
        FakeLedger([entry(source)]),
        target,
        FakeDelta(CollectionOutcome(CollectionState.PARTIAL), (repo_data,)),
    ).run("/workspace")
    assert result.movement["state"] == "unknown"
    assert result.summary["movement_repositories"] == 0


def test_snapshot_warning_extraction_and_default_fake_delta_fallback():
    document = SnapshotEnvelope(
        "warnings",
        "2026-08-02T12:00:00Z",
        {"name": "vcs-tree"},
        HistoryStore("ledger", 2, writer_id="writer"),
        {"root": "/workspace", "outcome": {"state": "complete", "errors": []}},
        (
            {
                "repository_key": "repo-1",
                "mode": "jj",
                "collection": {
                    "identity": {"state": "complete", "errors": []},
                    "bookmarks": {
                        "state": "partial",
                        "errors": [
                            {"kind": "parse_error", "stage": "jj.bookmarks", "message": "bad"}
                        ],
                    },
                },
                "history_boundary": {"state": "shallow"},
            },
        ),
    )
    warnings = _snapshot_warnings(document)
    assert len(warnings) == 2
    source = snapshot("source", 3)
    target = snapshot("target", 4)
    pulse = PulseOrchestrator(
        FakeLedger([entry(source)]),
        collector_factory=lambda _: FakeCollector(target),
        delta_factory=lambda _: type(
            "Delta",
            (),
            {
                "calculate": lambda self, old, new: FakeDelta(
                    CollectionOutcome(CollectionState.COMPLETE), ()
                )
            },
        )(),
    ).run("/workspace")
    assert pulse.movement["state"] == "empty"
    assert _pulse_repository({"repository_key": "a", "locations": [{}]}, ())["path"] is None


def test_pulse_repository_preserves_workspace_family_identity():
    result = _pulse_repository(
        {
            "repository_key": "repo-1",
            "mode": "jj",
            "path": "toas",
            "workspace_family": {
                "family_id": "jj-config-id:abc",
                "kind": "jj_operation_store",
                "source": "config-id",
                "outcome": {"state": "complete", "errors": []},
            },
        },
        (),
    )
    assert result["workspace_family"]["family_id"] == "jj-config-id:abc"
