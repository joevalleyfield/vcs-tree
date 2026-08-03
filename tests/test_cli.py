import json
import runpy
from unittest.mock import Mock

import pytest

from vcs_tree import cli
from vcs_tree.ledger import HistoryLedger, LedgerError


def test_main_forwards_cli_options(monkeypatch):
    scan = Mock()
    monkeypatch.setattr(cli, "vcs_tree", scan)

    assert cli.main(["somewhere", "--flat", "--text-symbols"]) == 0
    scan.assert_called_once_with("somewhere", tree_mode=False, text_symbols=True)


def test_parser_defaults_to_current_directory(monkeypatch):
    scan = Mock()
    monkeypatch.setattr(cli, "vcs_tree", scan)

    assert cli.main([]) == 0
    scan.assert_called_once_with(".", tree_mode=True, text_symbols=False)


def test_help_exits_successfully(capsys):
    with pytest.raises(SystemExit, match="0"):
        cli.main(["--help"])

    assert "Parallel VCS repo scanner" in capsys.readouterr().out


def test_module_launcher_exits_with_main_result(monkeypatch):
    monkeypatch.setattr(cli, "main", lambda: 7)

    with pytest.raises(SystemExit, match="7"):
        runpy.run_module("vcs_tree.__main__", run_name="__main__")


def test_history_init_and_inspect_report_machine_local_warning(tmp_path, capsys):
    assert (
        cli.main(["history", "init", "--state-root", str(tmp_path), "--writer-id", "writer"]) == 0
    )
    initialized = json.loads(capsys.readouterr().out)
    assert initialized["writer_id"] == "writer"
    assert "machine-local" in " ".join(initialized["warnings"])
    assert cli.main(["history", "inspect", "--state-root", str(tmp_path)]) == 0
    inspected = json.loads(capsys.readouterr().out)
    assert inspected["status"] == "ok"
    assert inspected["writer_policy"] == "single_writer"


def test_history_inspect_uninitialized_returns_nonzero(tmp_path, capsys):
    assert cli.main(["history", "inspect", "--state-root", str(tmp_path)]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "uninitialized"


def test_history_snapshot_and_delta_commands(tmp_path, monkeypatch, capsys):
    state = tmp_path / "state"
    HistoryLedger.create(state, writer_id="writer")
    first = Mock()
    second = Mock()
    first.envelope.to_dict.return_value = {
        "snapshot_id": "one",
        "scan": {"outcome": {"state": "complete"}},
    }
    first.envelope.scan = {"outcome": {"state": "complete"}}
    first.envelope.snapshot_id = "one"
    second.envelope.to_dict.return_value = {
        "snapshot_id": "two",
        "scan": {"outcome": {"state": "complete"}},
    }
    second.envelope.scan = {"outcome": {"state": "complete"}}
    second.envelope.snapshot_id = "two"
    collector = Mock()
    collector.collect.side_effect = [first, second]
    monkeypatch.setattr(cli, "SnapshotCollector", lambda ledger, **kwargs: collector)
    assert cli.main(["history", "snapshot", "--state-root", str(state), str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["snapshot_id"] == "one"
    assert cli.main(["history", "snapshot", "--state-root", str(state), str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["snapshot_id"] == "two"


def test_history_delta_missing_snapshot_and_degraded_state(tmp_path, capsys):
    state = tmp_path / "state"
    HistoryLedger.create(state, writer_id="writer")
    assert (
        cli.main(
            [
                "history",
                "delta",
                "--format",
                "json",
                "--state-root",
                str(state),
                "--from",
                "a",
                "--to",
                "b",
            ]
        )
        == 2
    )
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "error"
    (state / "manifest.json").write_text("not-json")
    assert cli.main(["history", "inspect", "--state-root", str(state)]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "degraded"


def test_history_list_reports_deterministic_snapshot_index(tmp_path, capsys):
    state = tmp_path / "state"
    ledger = HistoryLedger.create(state, writer_id="writer")
    base = {
        "schema": "vcs-tree.history-snapshot",
        "history_store": {"store_id": ledger.store_id},
        "scan": {"root": "/top", "outcome": {"state": "complete"}},
    }
    ledger.commit_generation(writer_id="writer")
    ledger.commit_generation(writer_id="writer")
    ledger.record_snapshot(
        "later", 2, manifest={**base, "captured_at": "2026-08-02T00:00:00Z"}, writer_id="writer"
    )
    ledger.record_snapshot(
        "earlier", 1, manifest={**base, "captured_at": "2026-08-01T00:00:00Z"}, writer_id="writer"
    )
    ledger.record_snapshot("bare", 0, writer_id="writer")
    assert cli.main(["history", "list", "--state-root", str(state)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["store_id"] == ledger.store_id
    assert [item["snapshot_id"] for item in result["snapshots"]] == ["bare", "earlier", "later"]
    assert result["snapshots"][1]["top_path"] == "/top"


def test_history_list_reports_empty_initialized_index(tmp_path, capsys):
    state = tmp_path / "state"
    ledger = HistoryLedger.create(state, writer_id="writer")
    assert cli.main(["history", "list", "--state-root", str(state)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "ok"
    assert result["store_id"] == ledger.store_id
    assert result["snapshots"] == []


def test_history_list_explicitly_reports_uninitialized_and_corrupt_index(tmp_path, capsys):
    assert cli.main(["history", "list", "--state-root", str(tmp_path / "missing")]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "uninitialized"
    state = tmp_path / "state"
    HistoryLedger.create(state, writer_id="writer")
    (state / "snapshots.json").write_text("broken", encoding="utf-8")
    assert cli.main(["history", "list", "--state-root", str(state)]) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "degraded"
    assert not (state / "snapshots.json").read_text(encoding="utf-8").startswith("{")


def test_history_delta_renders_persisted_comparison(tmp_path, monkeypatch, capsys):
    state = tmp_path / "state"
    ledger = HistoryLedger.create(state, writer_id="writer")
    manifest = {"schema": "vcs-tree.history-snapshot", "snapshot_id": "one"}
    ledger.record_snapshot("one", 0, manifest=manifest, writer_id="writer")
    ledger.record_snapshot(
        "two", 0, manifest={**manifest, "snapshot_id": "two"}, writer_id="writer"
    )

    class FakeDelta:
        outcome = type("Outcome", (), {"state": type("State", (), {"value": "complete"})()})()

        def to_dict(self):
            return {"schema": "vcs-tree.history-delta", "repository_deltas": []}

    monkeypatch.setattr(
        cli,
        "HistoryDeltaCalculator",
        lambda ledger: type(
            "Calculator", (), {"calculate": lambda self, before, after: FakeDelta()}
        )(),
    )
    assert (
        cli.main(
            [
                "history",
                "delta",
                "--format",
                "json",
                "--state-root",
                str(state),
                "--from",
                "one",
                "--to",
                "two",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["schema"] == "vcs-tree.history-delta"


def test_delta_summary_suppresses_and_reveals_noops(capsys):
    document = {
        "from_snapshot": "before",
        "to_snapshot": "after",
        "outcome": {"state": "partial"},
        "repository_deltas": [
            {
                "repository_key": "repo-1",
                "path": "project",
                "mode": "git",
                "events": [
                    {
                        "event": "workspace_head_changed",
                        "certainty": "observed",
                        "details": {"relation": "unknown"},
                    }
                ],
            },
            {"repository_key": "repo-2", "path": "quiet", "mode": "jj", "events": []},
            {
                "repository_key": "repo-3",
                "path": "uncertain",
                "mode": "git",
                "events": [
                    {"event": "comparison_incomplete", "certainty": "indeterminate", "details": {}}
                ],
            },
        ],
    }
    cli._print_delta_summary(document, include_noops=False)
    compact = capsys.readouterr().out
    assert "project [git]" in compact
    assert "quiet [jj]" not in compact
    assert "use --all" in compact
    assert "comparison warning" in compact
    cli._print_delta_summary(document, include_noops=True)
    assert "quiet [jj] — no observed movement" in capsys.readouterr().out


def test_history_delta_events_only_json_filters_noops(tmp_path, monkeypatch, capsys):
    state = tmp_path / "state"
    ledger = HistoryLedger.create(state, writer_id="writer")
    ledger.record_snapshot("one", 0, manifest={"snapshot_id": "one"}, writer_id="writer")
    ledger.record_snapshot("two", 0, manifest={"snapshot_id": "two"}, writer_id="writer")

    class FakeDelta:
        outcome = type("Outcome", (), {"state": type("State", (), {"value": "complete"})()})()

        def to_dict(self):
            return {
                "schema": "vcs-tree.history-delta",
                "repository_deltas": [
                    {"repository_key": "one", "events": []},
                    {"repository_key": "two", "events": [{"event": "changed"}]},
                ],
            }

    monkeypatch.setattr(
        cli,
        "HistoryDeltaCalculator",
        lambda ledger: type(
            "Calculator", (), {"calculate": lambda self, before, after: FakeDelta()}
        )(),
    )
    assert (
        cli.main(
            [
                "history",
                "delta",
                "--events-only",
                "--state-root",
                str(state),
                "--from",
                "one",
                "--to",
                "two",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert len(result["repository_deltas"]) == 1
    assert result["presentation"]["omitted_noop_repositories"] == 1
    assert (
        cli.main(
            [
                "history",
                "delta",
                "--events-only",
                "--format",
                "json",
                "--state-root",
                str(state),
                "--from",
                "one",
                "--to",
                "two",
            ]
        )
        == 2
    )
    assert json.loads(capsys.readouterr().out)["status"] == "error"


def test_history_pulse_formats_and_exit_mapping(tmp_path, monkeypatch, capsys):
    state = tmp_path / "state"
    HistoryLedger.create(state, writer_id="writer")

    class FakePulse:
        def __init__(self, state):
            self.state = state

        def to_dict(self):
            return {
                "schema": "vcs-tree.history-pulse",
                "schema_version": 1,
                "pulse_id": "pulse",
                "generated_at": "2026-08-03T00:00:00Z",
                "scope": {"root": "/workspace"},
                "target_snapshot": {"generation": 2},
                "comparison": {"state": "selected", "source_generation": 1},
                "outcome": {"state": self.state, "errors": []},
                "movement": {"state": "observed" if self.state != "error" else "unknown"},
                "repositories": [],
                "warnings": [],
                "summary": {"new_warnings": 0, "persistent_warnings": 0, "recovered_warnings": 0},
            }

    def fake_orchestrator(ledger, **kwargs):
        kwargs["collector_factory"](ledger)
        return type(
            "Orchestrator", (), {"run": lambda self, path, from_snapshot=None: FakePulse("partial")}
        )()

    monkeypatch.setattr(cli, "PulseOrchestrator", fake_orchestrator)
    assert cli.main(["history", "pulse", "--state-root", str(state), "--format", "json"]) == 3
    assert json.loads(capsys.readouterr().out)["schema"] == "vcs-tree.history-pulse"


def test_history_pulse_help_and_selection_error(tmp_path, monkeypatch, capsys):
    with pytest.raises(SystemExit, match="0"):
        cli.main(["history", "pulse", "--help"])
    assert "max-enrichment-objects" in capsys.readouterr().out
    state = tmp_path / "state"
    HistoryLedger.create(state, writer_id="writer")
    monkeypatch.setattr(
        cli,
        "PulseOrchestrator",
        lambda ledger, **kwargs: type(
            "Orchestrator",
            (),
            {
                "run": lambda self, path, from_snapshot=None: (_ for _ in ()).throw(
                    cli.PulseSelectionError("scope_mismatch")
                )
            },
        )(),
    )
    assert cli.main(["history", "pulse", "--state-root", str(state)]) == 4
    assert json.loads(capsys.readouterr().out)["status"] == "error"


def test_history_delta_default_is_human_summary(tmp_path, monkeypatch, capsys):
    state = tmp_path / "state"
    ledger = HistoryLedger.create(state, writer_id="writer")
    ledger.record_snapshot("one", 0, manifest={"snapshot_id": "one"}, writer_id="writer")
    ledger.record_snapshot("two", 0, manifest={"snapshot_id": "two"}, writer_id="writer")

    class FakeDelta:
        outcome = type("Outcome", (), {"state": type("State", (), {"value": "complete"})()})()

        def to_dict(self):
            return {
                "from_snapshot": "one",
                "to_snapshot": "two",
                "outcome": {"state": "complete"},
                "repository_deltas": [
                    {"repository_key": "one", "path": "project", "mode": "git", "events": []}
                ],
            }

    monkeypatch.setattr(
        cli,
        "HistoryDeltaCalculator",
        lambda ledger: type(
            "Calculator", (), {"calculate": lambda self, before, after: FakeDelta()}
        )(),
    )
    assert (
        cli.main(["history", "delta", "--state-root", str(state), "--from", "one", "--to", "two"])
        == 0
    )
    assert "repositories unchanged" in capsys.readouterr().out


def test_history_command_reports_ledger_errors(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli.HistoryLedger, "open", Mock(side_effect=LedgerError("broken")))
    assert cli.main(["history", "snapshot", "--state-root", str(tmp_path)]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "error"


def test_entry_point_uses_process_arguments_for_history_help(monkeypatch, capsys):
    monkeypatch.setattr(cli.sys, "argv", ["vcs-tree", "history", "--help"])
    with pytest.raises(SystemExit, match="0"):
        cli.main()
    assert "Inspect durable history" in capsys.readouterr().out
