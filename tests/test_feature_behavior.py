"""Feature-level behavioral matrix for the v1 package boundaries."""

import json
import subprocess

import pytest

from vcs_tree import (
    CollectionState,
    ContractError,
    HistoryDeltaCalculator,
    HistoryLedger,
    HistoryStore,
    SnapshotEnvelope,
    dumps,
    loads,
    resolve_paths,
)
from vcs_tree.git_adapter import GitAdapter
from vcs_tree.jj_adapter import JjAdapter


def _snapshot(snapshot_id, generation, repository):
    return SnapshotEnvelope(
        snapshot_id,
        "2026-08-01T15:00:00Z",
        {"name": "vcs-tree", "version": "0.1.0"},
        HistoryStore("ledger-test", generation, writer_id="writer-test"),
        {"root": "/fixture", "outcome": {"state": "complete", "errors": []}},
        (repository,),
    )


def _repository(refs=(), history=(), *, refs_state="complete", history_state="complete"):
    return {
        "repository_key": "repo-0001",
        "mode": "git",
        "refs": list(refs),
        "workspaces": [],
        "history": list(history),
        "history_boundary": {"state": "complete", "boundary_objects": []},
        "collection": {
            "identity": {"state": "complete", "errors": []},
            "refs": {"state": refs_state, "errors": []},
            "workspaces": {"state": "complete", "errors": []},
            "history": {"state": history_state, "errors": []},
        },
    }


def test_contract_boundary_is_deterministic_and_fail_closed():
    document = dumps(_snapshot("snapshot-a", 1, _repository()))
    assert document == dumps(loads(document, kind="snapshot"))
    malformed = json.loads(document)
    malformed["schema_version"] = 99
    with pytest.raises(ContractError):
        loads(json.dumps(malformed))


def test_ledger_policy_report_and_corruption_preserve_source_registry(tmp_path):
    root = tmp_path / "state"
    ledger = HistoryLedger.create(root, writer_id="writer-test")
    ledger.repository_key("fixture", writer_id="writer-test")
    report = resolve_paths(root).report()
    assert report["placement"] == "machine_local"
    assert any("cloud-synchronized" in warning for warning in report["warnings"])
    (root / "objects.json").write_text("corrupt", encoding="utf-8")
    degraded = HistoryLedger.open(root)
    assert degraded.repository_key("fixture", writer_id="writer-test") == "repo-0001"
    with pytest.raises(RuntimeError):
        degraded.read_objects()


def test_adapters_use_read_only_command_surfaces(tmp_path):
    git_calls = []

    def git_runner(command):
        git_calls.append(command)
        responses = {
            ("rev-parse", "--show-toplevel"): str(tmp_path) + "\n",
            ("worktree", "list", "--porcelain"): "",
            ("status", "--porcelain=v1"): "",
            (
                "for-each-ref",
                "--format=%(refname)%00%(objectname)%00%(objecttype)%00%(objectname:peel)",
            ): "",
            ("rev-list", "--objects", "--all"): "",
        }
        return subprocess.CompletedProcess(command, 0, responses.get(tuple(command), ""), "")

    GitAdapter(tmp_path, runner=git_runner).collect()
    assert all(
        command[0] not in {"fetch", "reset", "checkout", "update-ref"} for command in git_calls
    )

    jj_calls = []

    def jj_runner(command):
        jj_calls.append(command)
        return subprocess.CompletedProcess(command, 0, str(tmp_path) + "\n", "")

    JjAdapter(tmp_path, runner=jj_runner).collect()
    assert all(
        command[0] not in {"new", "edit", "commit", "describe", "rebase"} for command in jj_calls
    )


def test_delta_orders_events_and_suppresses_partial_absence():
    old_ref = {"name": "main", "authority": "local", "object_id": {"value": "a"}}
    new_ref = {"name": "side", "authority": "remote", "object_id": {"value": "b"}}
    old = _snapshot(
        "before",
        1,
        _repository(refs=(old_ref,), history=({"object_id": {"value": "a"}, "parents": []},)),
    )
    new = _snapshot(
        "after",
        2,
        _repository(refs=(new_ref,), history=({"object_id": {"value": "b"}, "parents": []},)),
    )
    delta = HistoryDeltaCalculator(
        objects={"a": old.repositories[0]["history"][0], "b": new.repositories[0]["history"][0]},
        delta_id_factory=lambda: "delta-test",
        clock=lambda: "2026-08-01T15:01:00Z",
    ).calculate(old, new)
    names = [event["event"] for event in delta.repository_deltas[0]["events"]]
    assert names[0] == "ref_created"
    partial = _snapshot("partial", 3, _repository(refs=(), refs_state="partial"))
    guarded = HistoryDeltaCalculator().calculate(old, partial)
    assert [event["event"] for event in guarded.repository_deltas[0]["events"]] == [
        "comparison_incomplete"
    ]
    assert guarded.outcome.state is CollectionState.PARTIAL
