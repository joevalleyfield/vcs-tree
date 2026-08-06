import json
import runpy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from vcs_tree import cli, query_cli
from vcs_tree.ledger import HistoryLedger, LedgerError
from vcs_tree.predicate_models import HistoryQuery


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


def _query_document():
    return {
        "schema": "vcs-tree.history-query",
        "schema_version": 1,
        "scope": {"all": True},
        "where": {
            "fact": {"type": "repository-exists", "attributes": {}, "state": "ever_observed"}
        },
    }


def test_query_input_inline_file_stdin_and_validation(tmp_path, monkeypatch):
    assert query_cli.read_query(json.dumps(_query_document()), None).to_dict() == _query_document()
    query_file = tmp_path / "query.json"
    query_file.write_text(json.dumps(_query_document()))
    assert query_cli.read_query(None, str(query_file)).to_dict() == _query_document()
    monkeypatch.setattr(
        "sys.stdin", type("Input", (), {"read": lambda self: json.dumps(_query_document())})()
    )
    assert query_cli.read_query(None, "-").to_dict() == _query_document()
    for where, where_file, expected in (
        (None, None, "exactly one"),
        ("{}", str(query_file), "exactly one"),
        ("not-json", None, "invalid query JSON"),
        ("{}", None, "invalid query schema"),
    ):
        with pytest.raises(ValueError, match=expected):
            query_cli.read_query(where, where_file)


def test_query_render_modes_and_execution_errors(monkeypatch):
    document = {
        "results": [
            {"repository_key": "b", "outcome": "false"},
            {"repository_key": "a", "outcome": "indeterminate"},
            {"repository_key": "c", "outcome": "true"},
        ],
        "capture": {"snapshot_id": "s"},
    }
    assert "omitted" in query_cli.render_query(document, "summary")
    assert '"repository_key": "b"' in query_cli.render_query(document, "audit")
    assert query_cli.render_query(document, "json").startswith("{")

    class FakeCollector:
        def collect(self, path):
            return type(
                "Result", (), {"envelope": type("Envelope", (), {"snapshot_id": "captured"})()}
            )()

    class FakeLedger:
        def read_temporal_index(self):
            return {
                "schema": "vcs-tree.temporal-facts",
                "schema_version": 1,
                "facts": [],
                "components": [],
            }

        def read_snapshots(self):
            return [{"snapshot_id": "retained", "generation": 1}]

    monkeypatch.setattr(
        query_cli.PredicateEvaluator, "evaluate", lambda self, *args, **kwargs: {"results": []}
    )
    result, target = query_cli.execute_query(
        FakeLedger(),
        HistoryQuery.from_dict(_query_document()),
        collector=FakeCollector(),
        capture=True,
    )
    assert target == "captured" and result["capture"]["performed"]
    monkeypatch.setattr(
        query_cli,
        "_index_for_snapshot",
        lambda ledger, snapshot: (
            {
                "schema": "vcs-tree.temporal-facts",
                "schema_version": 1,
                "facts": [],
                "components": [],
            },
            snapshot,
        ),
    )
    result, target = query_cli.execute_query(
        FakeLedger(), HistoryQuery.from_dict(_query_document()), snapshot_id="retained"
    )
    assert target == "retained" and not result["capture"]["performed"]
    result, target = query_cli.execute_query(
        FakeLedger(), HistoryQuery.from_dict(_query_document())
    )
    assert target == "retained" and not result["capture"]["performed"]
    with pytest.raises(ValueError, match="cannot be combined"):
        query_cli.execute_query(
            FakeLedger(),
            HistoryQuery.from_dict(_query_document()),
            snapshot_id="retained",
            capture=True,
        )

    def fail(*args, **kwargs):
        raise ValueError("bad evaluation")

    monkeypatch.setattr(query_cli.PredicateEvaluator, "evaluate", fail)
    with pytest.raises(query_cli.QueryExecutionError, match="bad evaluation") as error:
        query_cli.execute_query(
            FakeLedger(),
            HistoryQuery.from_dict(_query_document()),
            collector=FakeCollector(),
            capture=True,
        )
    assert error.value.snapshot_id == "captured"


def test_query_snapshot_selection_errors_and_no_false_summary(monkeypatch):
    class Ledger:
        store_id = "store"
        entries = []

        def read_temporal_index(self):
            return {
                "schema": "vcs-tree.temporal-facts",
                "schema_version": 1,
                "facts": [],
                "components": [],
            }

        def read_snapshots(self):
            return self.entries

        def read_objects(self):
            return {}

    ledger = Ledger()
    with pytest.raises(ValueError, match="snapshot not found"):
        query_cli._index_for_snapshot(ledger, "missing")
    for manifest, message in (
        (None, "no retained"),
        ({"history_store": {"store_id": "other"}}, "different"),
        (
            {"history_store": {"store_id": "store"}, "schema": "bad", "schema_version": 1},
            "unsupported",
        ),
    ):
        ledger.entries = [{"snapshot_id": "s", "generation": 1, "manifest": manifest}]
        with pytest.raises(ValueError, match=message):
            query_cli._index_for_snapshot(ledger, "s")
    ledger.entries = [
        {
            "snapshot_id": "s",
            "generation": "bad",
            "manifest": {
                "history_store": {"store_id": "store"},
                "schema": "vcs-tree.history-snapshot",
                "schema_version": 1,
            },
        }
    ]
    with pytest.raises(ValueError, match="valid generation"):
        query_cli._index_for_snapshot(ledger, "s")
    ledger.entries = [
        {
            "snapshot_id": "s",
            "generation": 1,
            "manifest": {
                "history_store": {"store_id": "store"},
                "schema": "vcs-tree.history-snapshot",
                "schema_version": 1,
            },
        },
        {"snapshot_id": "later", "generation": "bad"},
    ]
    monkeypatch.setattr(
        query_cli.TemporalIndexBuilder,
        "build",
        lambda self, *args, **kwargs: {
            "schema": "vcs-tree.temporal-facts",
            "schema_version": 1,
            "facts": [],
            "components": [],
        },
    )
    index, selected = query_cli._index_for_snapshot(ledger, "s")
    assert selected == "s" and index["source_generation"] == 1
    assert query_cli._index_for_snapshot(ledger, None)[0]["schema_version"] == 1
    assert "omitted" not in query_cli.render_query(
        {"results": [{"outcome": "true"}], "capture": {}}, "summary"
    )


def test_historical_query_index_cache_reuses_valid_generation_and_rebuilds_stale(
    monkeypatch, tmp_path
):
    class Ledger:
        store_id = "store"
        paths = SimpleNamespace(cache_root=tmp_path / "cache")
        entries = [
            {
                "snapshot_id": "s",
                "generation": 1,
                "manifest": {
                    "history_store": {"store_id": "store"},
                    "schema": "vcs-tree.history-snapshot",
                    "schema_version": 1,
                },
            }
        ]

        def read_snapshots(self):
            return self.entries

        def read_objects(self):
            return {}

    calls = []

    def build(self, *args, **kwargs):
        calls.append(kwargs.get("progress"))
        return {
            "schema": "vcs-tree.temporal-facts",
            "schema_version": 1,
            "store_id": "store",
            "source_generation": 1,
            "facts": [],
            "components": [],
        }

    monkeypatch.setattr(query_cli.TemporalIndexBuilder, "build", build)
    ledger = Ledger()
    first_progress = []
    second_progress = []
    first, _ = query_cli._index_for_snapshot(ledger, "s", progress=first_progress.append)
    second, _ = query_cli._index_for_snapshot(ledger, "s", progress=second_progress.append)
    assert first == second and len(calls) == 1
    assert "cache miss" in first_progress[0]
    assert "cache hit" in second_progress[0]
    query_cli._index_for_snapshot(ledger, "s")
    assert len(calls) == 1
    cache = next((tmp_path / "cache" / "temporal-index").glob("*.json"))
    cache.write_text(cache.read_text().replace('"source_generation": 1', '"source_generation": 0'))
    query_cli._index_for_snapshot(ledger, "s")
    assert len(calls) == 2
    monkeypatch.setattr(
        Path, "write_text", lambda *args, **kwargs: (_ for _ in ()).throw(OSError())
    )
    query_cli._store_cached_index(tmp_path / "cache.json", first)


def test_query_cli_success_and_indeterminate_exit(tmp_path, monkeypatch, capsys):
    state = tmp_path / "state"
    HistoryLedger.create(state, writer_id="writer")
    monkeypatch.setattr(
        cli,
        "execute_query",
        lambda *args, **kwargs: (
            {"results": [{"outcome": "indeterminate"}], "capture": {"snapshot_id": "s"}},
            "s",
        ),
    )
    monkeypatch.setattr(cli, "render_query", lambda document, mode: "rendered")
    assert (
        cli.main(
            [
                "history",
                "query",
                "--state-root",
                str(state),
                "--where",
                json.dumps(_query_document()),
            ]
        )
        == 3
    )
    assert capsys.readouterr().out.strip() == "rendered"
    monkeypatch.setattr(
        cli,
        "execute_query",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            query_cli.QueryExecutionError("failed", snapshot_id="captured")
        ),
    )
    assert (
        cli.main(
            [
                "history",
                "query",
                "--state-root",
                str(state),
                "--format",
                "json",
                "--where",
                json.dumps(_query_document()),
            ]
        )
        == 4
    )
