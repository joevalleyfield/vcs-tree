import pytest

from vcs_tree.enrichment import PulseEnricher, _object_ids
from vcs_tree.models import CollectionOutcome, CollectionState, DeltaEnvelope


def delta(events):
    return DeltaEnvelope(
        "delta",
        "2026-08-03T12:00:00Z",
        "from",
        "to",
        {"store_id": "ledger", "from_generation": 1, "to_generation": 2},
        CollectionOutcome(CollectionState.COMPLETE),
        ({"repository_key": "repo-1", "path": ".", "mode": "git", "events": events},),
    )


def records():
    return {
        "one": {
            "kind": "commit",
            "object_id": {"algorithm": "sha1", "value": "one"},
            "parents": [{"algorithm": "sha1", "value": "root"}],
            "summary": "first change",
            "change_id": "change-one",
            "author": {"name": "A", "timestamp": "2026-08-03T11:00:00Z"},
            "committer": {"name": "C", "timestamp": "2026-08-03T11:01:00Z"},
            "path_evidence": [{"status": "modified", "path": "README.md"}],
        },
        "root": {"kind": "virtual_root", "object_id": {"algorithm": "jj", "value": "00000000"}},
    }


def test_enrichment_selects_delta_objects_and_preserves_native_facts():
    result = PulseEnricher(objects=records()).enrich(
        delta(
            [
                {
                    "event": "workspace_head_changed",
                    "details": {
                        "old_object_id": {"algorithm": "sha1", "value": "root"},
                        "new_object_id": {"algorithm": "sha1", "value": "one"},
                    },
                }
            ]
        )
    )
    assert result.outcome.state is CollectionState.PARTIAL
    repository = result.repositories[0]
    assert repository["descriptions"][0]["change_id"] == "change-one"
    assert repository["path_evidence"][0]["paths"][0]["path"] == "README.md"
    assert any(item["kind"] == "missing_object" for item in result.warnings)


def test_virtual_root_is_not_described_or_diffed():
    virtual = {
        "kind": "virtual_root",
        "object_id": {"algorithm": "jj", "value": "00000000"},
        "parents": [{"value": "x"}],
    }
    result = PulseEnricher(objects={"root": virtual}).enrich(
        delta([{"event": "workspace_head_changed", "details": {"new_object_id": "00000000"}}])
    )
    assert PulseEnricher()._paths("00000000", None, virtual) == ()
    assert result.repositories[0]["descriptions"] == []
    assert result.repositories[0]["path_evidence"] == []


def test_change_graph_version_ids_are_enrichment_candidates():
    result = PulseEnricher(objects=records()).enrich(
        delta(
            [
                {
                    "event": "change_versions_changed",
                    "details": {
                        "old_visible_commits": ["one"],
                        "new_visible_commits": ["one"],
                    },
                }
            ]
        )
    )
    assert result.repositories[0]["descriptions"][0]["object_id"]["value"] == "one"


def test_limits_are_explicit_and_path_loader_is_parent_relative():
    calls = []

    def loader(object_id, parent_id):
        calls.append((object_id, parent_id))
        return ({"status": "added", "path": "new.md"},)

    result = PulseEnricher(
        objects=records(), path_loader=loader, max_objects=1, max_paths=0
    ).enrich(
        delta(
            [
                {"event": "a", "details": {"new_object_id": {"value": "one"}}},
                {"event": "b", "details": {"new": {"targets": [{"value": "other"}]}}},
            ]
        )
    )
    assert result.outcome.state is CollectionState.PARTIAL
    assert {item["evidence_class"] for item in result.warnings} == {"objects", "paths"}
    assert calls == [("one", "root")]


def test_ledger_replay_and_corruption_are_safe(tmp_path):
    from vcs_tree.ledger import HistoryLedger

    ledger = HistoryLedger.create(tmp_path / "state", writer_id="writer")
    ledger.append_objects(
        [{"repository_key": "repo-1", **record} for record in records().values()],
        writer_id="writer",
    )
    result = PulseEnricher(ledger=ledger).enrich(delta([]))
    assert result.outcome.state is CollectionState.COMPLETE
    (tmp_path / "state" / "objects.json").write_text("broken", encoding="utf-8")
    result = PulseEnricher(ledger=HistoryLedger.open(tmp_path / "state")).enrich(
        delta([{"event": "x", "details": {"new_object_id": {"value": "one"}}}])
    )
    assert result.outcome.state is CollectionState.PARTIAL


def test_empty_sources_and_nested_object_shapes_are_safe():
    assert _object_ids({"value": "00000000"}) == set()
    assert _object_ids({"targets": {"value": "00000000"}}) == set()
    assert _object_ids({"targets": {"value": "other"}}) == {"other"}
    assert _object_ids([]) == set()
    assert _object_ids("scalar") == set()
    assert PulseEnricher().enrich(delta([])).outcome.state is CollectionState.COMPLETE
    result = PulseEnricher(objects={"key:two": {"kind": "commit"}}).enrich(
        delta([{"event": "x", "details": {"old": [{"object_id": {"value": "two"}}]}}])
    )
    assert result.repositories[0]["descriptions"][0]["object_id"]["value"] == "two"
    missing = PulseEnricher(objects={}).enrich(
        delta([{"event": "x", "details": {"new_object_id": {"value": "missing"}}}])
    )
    assert missing.repositories[0]["descriptions"] == []
    no_path_record = {
        key: value for key, value in records()["one"].items() if key != "path_evidence"
    }
    no_paths = PulseEnricher(objects={"one": no_path_record}).enrich(
        delta([{"event": "x", "details": {"new_object_id": {"value": "one"}}}])
    )
    assert no_paths.repositories[0]["path_evidence"] == []


def test_invalid_limits_are_rejected():
    with pytest.raises(ValueError):
        PulseEnricher(max_objects=-1)
    with pytest.raises(ValueError):
        PulseEnricher(max_paths=-1)
