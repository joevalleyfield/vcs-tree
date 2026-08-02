import json

import pytest

from vcs_tree.models import (
    Backend,
    Certainty,
    CollectionError,
    CollectionOutcome,
    CollectionState,
    ContractError,
    DeltaEnvelope,
    Event,
    HistoryBoundary,
    HistoryBoundaryState,
    HistoryStore,
    IntegrityState,
    ObjectId,
    Placement,
    PulseEnvelope,
    RepositoryMode,
    Retention,
    SnapshotEnvelope,
    WriterPolicy,
    dumps,
    loads,
)


def snapshot() -> SnapshotEnvelope:
    return SnapshotEnvelope(
        "snapshot-a",
        "2026-07-29T13:00:00Z",
        {"name": "vcs-tree", "version": "0.1.0"},
        HistoryStore("local-ledger-01", 42, writer_id="writer-machine-a"),
        {"root": "/workspace", "outcome": CollectionOutcome(CollectionState.COMPLETE).to_dict()},
        ({"repository_key": "repo-01", "mode": "git"},),
    )


def delta() -> DeltaEnvelope:
    return DeltaEnvelope(
        "delta-a-b",
        "2026-07-29T13:01:00+00:00",
        "snapshot-a",
        "snapshot-b",
        {"store_id": "local-ledger-01", "from_generation": 1, "to_generation": 2},
        CollectionOutcome(
            CollectionState.PARTIAL, (CollectionError("timeout", "git.refs", "late"),)
        ),
        ({"repository_key": "repo-01", "events": []},),
    )


def pulse() -> PulseEnvelope:
    return PulseEnvelope(
        "pulse-snapshot-b",
        "2026-07-29T13:02:00Z",
        {"root": "/workspace"},
        {"snapshot_id": "snapshot-b", "generation": 43, "captured_at": "2026-07-29T13:01:00Z"},
        {
            "state": "selected",
            "selection": "automatic",
            "source_snapshot_id": "snapshot-a",
            "source_generation": 42,
        },
        CollectionOutcome(CollectionState.COMPLETE),
        {"state": "observed", "repository_count": 1},
        (
            {
                "repository_key": "repo-01",
                "path": ".",
                "mode": "git",
                "events": [],
                "descriptions": [],
                "path_evidence": [],
                "task_path_events": [],
                "warning_keys": [],
            },
        ),
        (),
        {
            "observed_repositories": 1,
            "movement_repositories": 1,
            "no_op_repositories": 0,
            "task_path_events": 0,
            "new_warnings": 0,
            "persistent_warnings": 0,
            "recovered_warnings": 0,
        },
    )


def test_enums_parse_and_reject_invalid_values():
    enums = (
        (CollectionState, "complete"),
        (IntegrityState, "ok"),
        (HistoryBoundaryState, "shallow"),
        (RepositoryMode, "colocated"),
        (Backend, "git"),
        (Placement, "machine_local"),
        (WriterPolicy, "single_writer"),
        (Retention, "indefinite"),
        (Certainty, "observed"),
    )
    for enum, value in enums:
        assert enum.parse(value).value == value
        with pytest.raises(ContractError):
            enum.parse("invalid")
        with pytest.raises(ContractError):
            enum.parse(None)


def test_object_id_normalizes_hex_and_round_trips():
    identifier = ObjectId("sha1", "ABCDEF")
    assert identifier.value == "abcdef"
    assert ObjectId.from_dict(identifier.to_dict()) == identifier
    assert ObjectId("custom", "MiXeD").value == "MiXeD"


@pytest.mark.parametrize(
    "value", [None, {}, {"algorithm": "sha1"}, {"algorithm": "", "value": "a"}]
)
def test_object_id_rejects_malformed_values(value):
    with pytest.raises(ContractError):
        ObjectId.from_dict(value)


def test_collection_outcome_and_boundary_round_trip_and_guards():
    error = CollectionError("timeout", "git.refs", "timed out", 2)
    outcome = CollectionOutcome(CollectionState.PARTIAL, (error,))
    assert CollectionOutcome.from_dict(outcome.to_dict()) == outcome
    assert CollectionError.from_dict({**error.to_dict(), "exit_code": None}).exit_code is None
    boundary = HistoryBoundary(HistoryBoundaryState.SHALLOW, (ObjectId("sha1", "ABC"),))
    assert HistoryBoundary.from_dict(boundary.to_dict()) == boundary
    with pytest.raises(ContractError):
        CollectionOutcome(CollectionState.COMPLETE, (error,))
    with pytest.raises(ContractError):
        HistoryBoundary(HistoryBoundaryState.COMPLETE, boundary.boundary_objects)
    with pytest.raises(ContractError):
        CollectionError.from_dict({**error.to_dict(), "exit_code": "2"})


def test_envelopes_have_deterministic_json_and_round_trip():
    snapshot_document = snapshot()
    encoded = dumps(snapshot_document)
    assert encoded == dumps(snapshot_document)
    assert list(json.loads(encoded)) == sorted(json.loads(encoded))
    assert loads(encoded) == snapshot_document
    assert loads(encoded, kind="snapshot") == snapshot_document

    delta_document = delta()
    pretty = dumps(delta_document, indent=2)
    assert "\n" in pretty
    assert loads(pretty, kind="delta") == delta_document
    assert loads(dumps(delta_document)) == delta_document
    pulse_document = pulse()
    assert loads(dumps(pulse_document), kind="pulse") == pulse_document


def test_event_round_trip_and_mapping_copy():
    event = Event(
        "ref_target_changed",
        "ref_target_changed:git:main",
        Certainty.OBSERVED,
        {"from": "refs"},
        {"old": 1},
    )
    assert Event.from_dict(event.to_dict()) == event
    encoded = event.to_dict()
    encoded["details"]["old"] = 9
    assert event.details["old"] == 1


@pytest.mark.parametrize(
    "value",
    [
        {},
        {"schema": SnapshotEnvelope.schema, "schema_version": 2},
        {"schema": "wrong", "schema_version": 1},
        [],
    ],
)
def test_snapshot_validation_rejects_bad_documents(value):
    with pytest.raises(ContractError):
        SnapshotEnvelope.from_dict(value)


def test_parsing_and_validation_errors_are_contract_errors():
    with pytest.raises(ContractError):
        loads("not json")
    with pytest.raises(ContractError):
        loads(json.dumps({"schema": "unknown"}))
    with pytest.raises(ContractError):
        loads(dumps(snapshot()), kind="delta")
    with pytest.raises(ContractError):
        loads(dumps(snapshot()), kind="pulse")
    with pytest.raises(ContractError):
        loads(dumps(delta()), kind="snapshot")
    with pytest.raises(ContractError):
        loads(dumps(snapshot()), kind="other")
    with pytest.raises(ContractError):
        dumps({})
    with pytest.raises(ContractError):
        SnapshotEnvelope("", "2026-07-29T13:00:00Z", {}, HistoryStore("s", 0, writer_id="w"), {})
    with pytest.raises(ContractError):
        SnapshotEnvelope("s", "2026-07-29T13:00:00", {}, HistoryStore("s", 0, writer_id="w"), {})
    with pytest.raises(ContractError):
        SnapshotEnvelope("s", "bad", {}, HistoryStore("s", 0, writer_id="w"), {})
    with pytest.raises(ContractError):
        HistoryStore("s", -1, writer_id="w")


def test_pulse_validation_rejects_invalid_state_and_order():
    document = pulse().to_dict()
    with pytest.raises(ContractError):
        PulseEnvelope.from_dict({**document, "comparison": {"state": "bad", "selection": "none"}})
    with pytest.raises(ContractError):
        PulseEnvelope.from_dict({**document, "movement": {"state": "bad", "repository_count": 0}})
    with pytest.raises(ContractError):
        PulseEnvelope.from_dict(
            {**document, "comparison": {"state": "selected", "selection": "bad"}}
        )
    with pytest.raises(ContractError):
        PulseEnvelope.from_dict({**document, "warnings": ["bad"]})
    assert PulseEnvelope.from_dict({**document, "warnings": [{}]}).warnings == ({},)
    with pytest.raises(ContractError):
        PulseEnvelope.from_dict(
            {
                **document,
                "repositories": [
                    document["repositories"][0],
                    {**document["repositories"][0], "path": ""},
                ],
            }
        )


def test_nested_payloads_must_be_json_and_objects():
    with pytest.raises(ContractError):
        SnapshotEnvelope(
            "s", "2026-07-29T13:00:00Z", {"bad": {1}}, HistoryStore("s", 0, writer_id="w"), {}
        ).to_dict()
    with pytest.raises(ContractError):
        SnapshotEnvelope.from_dict({**snapshot().to_dict(), "repositories": {}})
    with pytest.raises(ContractError):
        Event.from_dict(
            {"event": "x", "event_key": "x", "certainty": "observed", "evidence": [], "details": {}}
        )
