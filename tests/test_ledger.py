import hashlib
import json

import pytest

import vcs_tree.ledger as ledger_module
from vcs_tree.ledger import (
    HistoryLedger,
    LedgerCorruptError,
    LedgerError,
    WriterMismatchError,
    resolve_paths,
)
from vcs_tree.models import (
    V2_REPOSITORY_COMPONENTS,
    ContractError,
    HistoryStore,
    SnapshotEnvelope,
    SnapshotEnvelopeV2,
)


def record(value="a"):
    return {
        "repository_key": "repo-0001",
        "kind": "commit",
        "object_id": {"algorithm": "sha1", "value": value},
        "summary": "observed",
    }


def test_resolve_paths_separates_state_config_and_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    paths = resolve_paths()
    assert paths.state_root == tmp_path / "state" / "vcs-tree"
    assert paths.config_root == tmp_path / "config" / "vcs-tree"
    assert paths.cache_root == tmp_path / "cache" / "vcs-tree"
    assert paths.state_root != paths.cache_root
    assert paths.report()["placement"] == "machine_local"
    assert len(paths.warnings) == 2
    explicit = resolve_paths(tmp_path / "s", config_root=tmp_path / "c", cache_root=tmp_path / "x")
    assert explicit.state_root == tmp_path / "s"


def test_create_open_and_stable_repository_identity(tmp_path):
    ledger = HistoryLedger.create(
        tmp_path / "state", writer_id="writer-a", cache_root=tmp_path / "cache"
    )
    assert ledger.status().state == "ok"
    assert ledger.store_id.startswith("ledger-")
    key = ledger.repository_key("git:/workspace/project", writer_id="writer-a")
    assert key == "repo-0001"
    assert ledger.repository_key("git:/workspace/project", writer_id="writer-a") == key
    assert ledger.repository_key("git:/workspace/other", writer_id="writer-a") == "repo-0002"
    reopened = HistoryLedger.open(tmp_path / "state")
    assert reopened.writer_id == "writer-a"
    assert reopened.repository_key("git:/workspace/project", writer_id="writer-a") == key


def test_objects_are_immutable_deduplicated_and_retained(tmp_path):
    ledger = HistoryLedger.create(tmp_path / "state", writer_id="writer-a")
    first = ledger.append_objects([record(), record()], writer_id="writer-a")
    assert len(first) == 1
    assert ledger.append_objects([record()], writer_id="writer-a") == ()
    assert ledger.read_objects()[first[0]]["summary"] == "observed"
    second = ledger.append_objects([record("b")], writer_id="writer-a")
    assert len(second) == 1
    assert ledger.commit_generation(writer_id="writer-a") == 1
    assert ledger.commit_generation(writer_id="writer-a") == 2
    ledger.record_snapshot("snapshot-a", 2, writer_id="writer-a")
    ledger.record_snapshot("snapshot-a", 2, writer_id="writer-a")
    reopened = HistoryLedger.open(tmp_path / "state")
    assert reopened.generation == 2
    assert len(reopened.read_objects()) == 2
    assert reopened.read_snapshots()[0]["snapshot_id"] == "snapshot-a"


def test_mutations_require_enrolled_writer(tmp_path):
    ledger = HistoryLedger.create(tmp_path / "state", writer_id="writer-a")
    with pytest.raises(WriterMismatchError):
        ledger.repository_key("x", writer_id="writer-b")
    with pytest.raises(WriterMismatchError):
        ledger.append_objects([record()], writer_id="writer-b")
    with pytest.raises(WriterMismatchError):
        ledger.commit_generation(writer_id="writer-b")
    with pytest.raises(WriterMismatchError):
        ledger.record_snapshot("x", 0, writer_id="writer-b")
    with pytest.raises(WriterMismatchError):
        ledger.repository_key("x")


def test_input_validation_and_generation_snapshot_rules(tmp_path):
    ledger = HistoryLedger.create(tmp_path / "state", writer_id="writer-a")
    with pytest.raises(ContractError):
        ledger.repository_key("", writer_id="writer-a")
    with pytest.raises(ContractError):
        ledger.append_objects([{}], writer_id="writer-a")
    with pytest.raises(ContractError):
        ledger.append_objects([record() | {"object_id": {}}], writer_id="writer-a")
    with pytest.raises(ContractError):
        ledger.append_objects(
            [record() | {"object_id": {"algorithm": "sha1"}}], writer_id="writer-a"
        )
    with pytest.raises(ContractError):
        ledger.append_objects(["not an object"], writer_id="writer-a")
    with pytest.raises(ContractError):
        ledger.record_snapshot("", 0, writer_id="writer-a")
    with pytest.raises(ContractError):
        ledger.record_snapshot("snapshot", -1, writer_id="writer-a")
    with pytest.raises(ContractError):
        ledger.record_snapshot("snapshot", 1, writer_id="writer-a")


def test_corrupt_object_component_isolated_from_repository_registry(tmp_path):
    root = tmp_path / "state"
    ledger = HistoryLedger.create(root, writer_id="writer-a")
    ledger.repository_key("repo", writer_id="writer-a")
    (root / "objects.json").write_text("broken", encoding="utf-8")
    reopened = HistoryLedger.open(root)
    assert reopened.status().state == "degraded"
    assert "objects.json" in reopened.status().degraded_components
    assert reopened.repository_key("repo", writer_id="writer-a") == "repo-0001"
    with pytest.raises(LedgerCorruptError):
        reopened.read_objects()
    with pytest.raises(LedgerCorruptError):
        reopened.append_objects([record()], writer_id="writer-a")


def test_corrupt_registry_is_not_repaired_or_used(tmp_path):
    root = tmp_path / "state"
    HistoryLedger.create(root, writer_id="writer-a")
    (root / "repositories.json").write_text(json.dumps({"value": {}}), encoding="utf-8")
    reopened = HistoryLedger.open(root)
    assert reopened.status().state == "degraded"
    with pytest.raises(LedgerCorruptError):
        reopened.repository_key("new", writer_id="writer-a")
    assert reopened.read_objects() == {}


def test_missing_or_invalid_control_state_fails_closed(tmp_path):
    with pytest.raises(LedgerCorruptError):
        HistoryLedger.open(tmp_path / "missing")
    root = tmp_path / "state"
    HistoryLedger.create(root, writer_id="writer-a")
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    manifest["value"]["writer_policy"] = "multi_writer"
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(LedgerCorruptError):
        HistoryLedger.open(root)


def test_ledger_error_is_runtime_error():
    assert issubclass(LedgerCorruptError, LedgerError)


def checked(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return {"checksum": hashlib.sha256(encoded.encode()).hexdigest(), "value": value}


def test_corrupt_shapes_are_rejected_per_component(tmp_path):
    root = tmp_path / "state"
    HistoryLedger.create(root, writer_id="writer-a")
    (root / "repositories.json").write_text(json.dumps(checked([])), encoding="utf-8")
    (root / "objects.json").write_text(json.dumps(checked([])), encoding="utf-8")
    (root / "generations.json").write_text(json.dumps(checked({})), encoding="utf-8")
    (root / "snapshots.json").write_text(json.dumps(checked({})), encoding="utf-8")
    reopened = HistoryLedger.open(root)
    with pytest.raises(LedgerCorruptError):
        reopened.repository_key("repo", writer_id="writer-a")
    with pytest.raises(LedgerCorruptError):
        reopened.append_objects([record()], writer_id="writer-a")
    with pytest.raises(LedgerCorruptError):
        reopened.commit_generation(writer_id="writer-a")
    with pytest.raises(LedgerCorruptError):
        reopened.record_snapshot("snapshot", 0, writer_id="writer-a")
    with pytest.raises(LedgerCorruptError):
        reopened.read_objects()
    with pytest.raises(LedgerCorruptError):
        reopened.read_snapshots()


def test_open_rejects_invalid_manifest_shapes(tmp_path):
    root = tmp_path / "state"
    HistoryLedger.create(root, writer_id="writer-a")
    manifest = checked([])
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(LedgerCorruptError):
        HistoryLedger.open(root)
    HistoryLedger.create(root, writer_id="writer-a")
    manifest = checked({"store_id": "s", "writer_policy": "multi_writer"})
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(LedgerCorruptError):
        HistoryLedger.open(root)


def test_corrupt_component_is_marked_when_read_after_open(tmp_path):
    root = tmp_path / "state"
    ledger = HistoryLedger.create(root, writer_id="writer-a")
    (root / "objects.json").write_text("broken", encoding="utf-8")
    with pytest.raises(LedgerCorruptError):
        ledger.read_objects()
    assert "objects.json" in ledger.status().degraded_components
    ledger._degraded = ("manifest.json",)
    with pytest.raises(LedgerCorruptError):
        ledger.repository_key("repo", writer_id="writer-a")


def test_atomic_write_removes_temporary_file_on_replace_failure(monkeypatch, tmp_path):
    root = tmp_path / "state"
    root.mkdir()
    destination = root / "value.json"

    def fail_replace(temporary, _destination):
        ledger_module.os.unlink(temporary)
        raise OSError("simulated replace failure")

    monkeypatch.setattr(ledger_module.os, "replace", fail_replace)
    with pytest.raises(OSError):
        ledger_module._atomic_write(destination, {"value": 1})
    assert not list(root.glob(".*"))


def test_mixed_snapshot_manifests_read_without_rewriting_v1(tmp_path):
    ledger = HistoryLedger.create(tmp_path / "state", writer_id="writer-a")
    store = HistoryStore(ledger.store_id, 0, writer_id="writer-a")
    v1 = SnapshotEnvelope("v1", "2026-08-04T12:00:00Z", {}, store, {}, ())
    timestamp = "2026-08-04T12:01:00Z"
    complete = {"state": "complete", "attempted_at": timestamp, "errors": []}
    repository = {
        "repository_key": "repo-1",
        "mode": "git",
        "collection": {name: complete for name in V2_REPOSITORY_COMPONENTS},
        "workspaces": [],
    }
    v2 = SnapshotEnvelopeV2("v2", timestamp, {}, store, {}, (repository,))
    original_v1 = v1.to_dict()
    ledger.record_snapshot("bare", 0, writer_id="writer-a")
    ledger.record_snapshot("v1", 0, manifest=original_v1, writer_id="writer-a")
    ledger.record_snapshot("v2", 0, manifest=v2.to_dict(), writer_id="writer-a")
    documents = HistoryLedger.open(tmp_path / "state").read_snapshot_envelopes()
    assert [document.schema_version for document in documents] == [1, 2]
    assert ledger.read_snapshots()[1]["manifest"] == original_v1


def test_invalid_retained_snapshot_manifest_is_corrupt(tmp_path):
    ledger = HistoryLedger.create(tmp_path / "state", writer_id="writer-a")
    ledger.record_snapshot("invalid", 0, manifest={"schema": "wrong"}, writer_id="writer-a")
    with pytest.raises(LedgerCorruptError):
        ledger.read_snapshot_envelopes()
