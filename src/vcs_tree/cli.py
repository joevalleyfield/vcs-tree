"""Command-line interface for vcs-tree."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from vcs_tree.candidate import project_current_workspaces
from vcs_tree.delta import HistoryDeltaCalculator
from vcs_tree.enrichment import PulseEnricher
from vcs_tree.ledger import HistoryLedger, LedgerError, resolve_paths
from vcs_tree.pulse import PulseOrchestrator, PulseSelectionError
from vcs_tree.pulse_render import render
from vcs_tree.query_cli import (
    QueryExecutionError,
    execute_queries,
    read_queries,
    render_query,
)
from vcs_tree.scanner import vcs_tree
from vcs_tree.snapshot import SnapshotCollector


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="vcs-tree",
        description="Parallel VCS repo scanner with stall-detection display.",
        epilog=(
            "History workflows are available with 'vcs-tree history --help': "
            "init, inspect, snapshot, delta, list, pulse, query, and candidates."
        ),
    )
    parser.add_argument("path", nargs="?", default=".", help="Directory to scan (default: .)")
    parser.add_argument("--flat", action="store_true", help="Flat mode (no directory hierarchy)")
    parser.add_argument(
        "--text-symbols",
        action="store_true",
        help="Spell out repo types (jj, git) instead of unicode",
    )
    return parser


def _build_history_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vcs-tree history", description="Inspect durable history")
    history_sub = parser.add_subparsers(dest="history_command", required=True)
    for name, help_text in (
        ("init", "Initialize the machine-local history store"),
        ("inspect", "Inspect history store locations and status"),
        ("snapshot", "Collect and persist a repository snapshot"),
        ("delta", "Compare two persisted snapshots"),
        ("list", "List retained snapshots"),
        ("pulse", "Capture and compare a movement pulse"),
        ("query", "Evaluate a mechanical history query"),
        ("candidates", "Project current workspace evidence"),
    ):
        sub = history_sub.add_parser(name, help=help_text)
        sub.add_argument("--state-root", help="Authoritative state directory")
    history_sub.choices["init"].add_argument("--writer-id", help="Enroll this writer identity")
    history_sub.choices["snapshot"].add_argument("path", nargs="?", default=".")
    delta = history_sub.choices["delta"]
    delta.add_argument("--from", dest="from_snapshot", required=True)
    delta.add_argument("--to", dest="to_snapshot", required=True)
    delta.add_argument("--format", choices=("summary", "json"), default="summary")
    delta.add_argument("--all", action="store_true", help="Include verified no-op repositories")
    delta.add_argument(
        "--events-only", action="store_true", help="Emit compact JSON for repositories with events"
    )
    pulse = history_sub.choices["pulse"]
    pulse.add_argument("path", nargs="?", default=".")
    pulse.add_argument("--from", dest="from_snapshot")
    pulse.add_argument("--format", choices=("summary", "audit", "json"), default="summary")
    pulse.add_argument("--max-enrichment-objects", type=int, default=256)
    pulse.add_argument("--max-changed-paths", type=int, default=10_000)
    query = history_sub.choices["query"]
    query.add_argument("path", nargs="?", default=".")
    query.add_argument("--where")
    query.add_argument("--where-file")
    query.add_argument("--snapshot")
    query.add_argument(
        "--capture", action="store_true", help="Capture a new observation before evaluating"
    )
    query.add_argument("--format", choices=("summary", "audit", "json"), default="summary")
    candidates = history_sub.choices["candidates"]
    candidates.add_argument("path", nargs="?", default=".")
    candidates.add_argument("--snapshot")
    candidates.add_argument("--max-entries", type=int, default=256)
    candidates.add_argument("--format", choices=("summary", "json"), default="json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line scanner."""
    values = list(argv) if argv is not None else sys.argv[1:]
    if values and values[0] == "history":
        return _history_main(_build_history_parser().parse_args(values[1:]))
    args = build_parser().parse_args(values)
    vcs_tree(args.path, tree_mode=not args.flat, text_symbols=args.text_symbols)
    return 0


def _print_json(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def _print_delta_summary(document: dict[str, object], *, include_noops: bool) -> None:
    entries = document["repository_deltas"]
    changed = [item for item in entries if item["events"]]
    noops = len(entries) - len(changed)
    outcome = document["outcome"]["state"]
    print(f"delta {document['from_snapshot']} -> {document['to_snapshot']} ({outcome})")
    for item in entries:
        events = item["events"]
        if not events and not include_noops:
            continue
        path = item.get("path") or f"[local:{item['repository_key']}]"
        mode = item.get("mode") or "unknown"
        if events:
            print(f"{path} [{mode}]")
            for event in events:
                certainty = event.get("certainty", "observed")
                marker = "?" if certainty == "indeterminate" else "*"
                details = event.get("details", {})
                relation = details.get("relation") if isinstance(details, dict) else None
                if event["event"] == "comparison_incomplete" and isinstance(details, dict):
                    suffix = (
                        f" (component: {details.get('component')}, "
                        f"state: {details.get('from_state')} -> {details.get('to_state')})"
                    )
                else:
                    suffix = f" (relation: {relation})" if relation else ""
                print(f"  {marker} {event['event']}{suffix}")
        else:
            print(f"{path} [{mode}] — no observed movement")
    if noops and not include_noops:
        print(f"{noops} repositories unchanged (use --all to inspect)")
    unknown = sum(
        1
        for item in changed
        for event in item["events"]
        if event.get("certainty") == "indeterminate"
    )
    if unknown:
        print(f"{unknown} comparison warning(s) suppress movement conclusions")


def _history_main(args: argparse.Namespace) -> int:
    state_root = args.state_root
    if args.history_command == "init":
        ledger = HistoryLedger.create(state_root, writer_id=args.writer_id)
        _print_json(
            {
                "status": "initialized",
                **ledger.paths.report(),
                "store_id": ledger.store_id,
                "writer_id": ledger.writer_id,
                "writer_policy": "single_writer",
            }
        )
        return 0
    paths = resolve_paths(state_root)
    if args.history_command == "inspect":
        report = paths.report()
        if not (paths.state_root / HistoryLedger._MANIFEST).exists():
            _print_json({"status": "uninitialized", **report})
            return 2
        try:
            ledger = HistoryLedger.open(state_root)
        except LedgerError as exc:
            _print_json({"status": "degraded", **report, "error": str(exc)})
            return 2
        _print_json(
            {
                "status": ledger.status().state,
                **report,
                "store_id": ledger.store_id,
                "writer_id": ledger.writer_id,
                "writer_policy": "single_writer",
                "generation": ledger.generation,
            }
        )
        return 0
    if args.history_command == "list":
        report = paths.report()
        if not (paths.state_root / HistoryLedger._MANIFEST).exists():
            _print_json({"status": "uninitialized", **report, "snapshots": []})
            return 2
        try:
            ledger = HistoryLedger.open(state_root)
            entries = ledger.read_snapshots()
        except LedgerError as exc:
            _print_json({"status": "degraded", **report, "error": str(exc), "snapshots": []})
            return 2
        snapshots = []
        for entry in entries:
            manifest = entry.get("manifest") if isinstance(entry.get("manifest"), dict) else {}
            scan = manifest.get("scan") if isinstance(manifest.get("scan"), dict) else {}
            outcome = scan.get("outcome") if isinstance(scan.get("outcome"), dict) else {}
            store = (
                manifest.get("history_store")
                if isinstance(manifest.get("history_store"), dict)
                else {}
            )
            snapshots.append(
                {
                    "snapshot_id": entry.get("snapshot_id"),
                    "top_path": scan.get("root"),
                    "captured_at": manifest.get("captured_at"),
                    "generation": entry.get("generation"),
                    "outcome": outcome.get("state"),
                    "store_id": store.get("store_id", ledger.store_id),
                }
            )
        snapshots.sort(
            key=lambda item: (
                item["generation"] or -1,
                item["captured_at"] or "",
                item["snapshot_id"] or "",
            )
        )
        _print_json({"status": "ok", **report, "store_id": ledger.store_id, "snapshots": snapshots})
        return 0
    try:
        ledger = HistoryLedger.open(state_root)
        if args.history_command == "candidates":
            entries = [
                item for item in ledger.read_snapshots() if isinstance(item.get("manifest"), dict)
            ]
            if args.snapshot is not None:
                selected = next(
                    (item for item in entries if item.get("snapshot_id") == args.snapshot), None
                )
            else:
                selected = max(
                    entries,
                    key=lambda item: (item.get("generation", -1), str(item.get("snapshot_id", ""))),
                    default=None,
                )
            if selected is None:
                raise ValueError("snapshot not found")
            document = project_current_workspaces(
                selected["manifest"], max_entries=args.max_entries
            )
            if args.format == "json":
                _print_json(document)
            else:
                print(
                    f"current workspace evidence {document['scope']['root']} "
                    f"generation {document['snapshot']['generation']}"
                )
                for repository in document["repositories"]:
                    print(f"{repository['path']} [{repository['mode']}]")
                    for workspace in repository["workspaces"]:
                        current = workspace["current"]
                        print(
                            f"  {workspace['workspace_key']}: "
                            f"{current.get('object_id') or 'unknown'} "
                            f"({workspace['working_copy']['recorded_state']})"
                        )
            return 0
        if args.history_command == "query":
            queries = read_queries(args.where, args.where_file)
            target = args.snapshot
            try:
                document, target = execute_queries(
                    ledger,
                    queries,
                    path=args.path,
                    snapshot_id=args.snapshot,
                    capture=args.capture,
                    progress=lambda message: print(f"[vcs-tree] {message}", file=sys.stderr),
                )
            except QueryExecutionError as exc:
                target = exc.snapshot_id
                payload = {"status": "error", "error": str(exc), "capture": {"snapshot_id": target}}
                _print_json(payload) if args.format == "json" else print(
                    f"query error (snapshot: {target}): {exc}"
                )
                return 4
            print(render_query(document, args.format))
            result_items = list(document.get("results", ()))
            for batch in document.get("queries", ()):
                result_items.extend(batch.get("results", ()))
            outcomes = [item.get("outcome") for item in result_items]
            return 3 if "indeterminate" in outcomes else 0
        if args.history_command == "pulse":

            def collector_factory(store):
                return SnapshotCollector(
                    store,
                    progress=lambda message: print(f"[vcs-tree] {message}", file=sys.stderr),
                )

            orchestrator = PulseOrchestrator(
                ledger,
                collector_factory=collector_factory,
                enricher_factory=lambda store: PulseEnricher(
                    store,
                    max_objects=args.max_enrichment_objects,
                    max_paths=args.max_changed_paths,
                ),
            )
            document = orchestrator.run(Path(args.path), from_snapshot=args.from_snapshot).to_dict()
            print(render(document, args.format))
            state = document["outcome"]["state"]
            return 4 if state == "error" else 3 if state == "partial" else 0
        if args.history_command == "snapshot":
            result = SnapshotCollector(
                ledger,
                progress=lambda message: print(f"[vcs-tree] {message}", file=sys.stderr),
            ).collect(Path(args.path))
            _print_json(result.envelope.to_dict())
            return 0 if result.envelope.scan.get("outcome", {}).get("state") == "complete" else 2
        snapshots = ledger.read_snapshots()
        entries = {item.get("snapshot_id"): item for item in snapshots if item.get("manifest")}
        before = entries.get(args.from_snapshot)
        after = entries.get(args.to_snapshot)
        if before is None or after is None:
            _print_json({"status": "error", "error": "snapshot not found"})
            return 2
        delta = HistoryDeltaCalculator(ledger).calculate(before["manifest"], after["manifest"])
        if args.events_only and args.format != "summary":
            raise ValueError("--events-only cannot be combined with --format json")
        document = delta.to_dict()
        if args.events_only:
            entries = document["repository_deltas"]
            document["repository_deltas"] = [item for item in entries if item["events"]]
            document["presentation"] = {
                "mode": "events-only",
                "omitted_noop_repositories": len(entries) - len(document["repository_deltas"]),
            }
            _print_json(document)
        elif args.format == "json":
            _print_json(document)
        else:
            _print_delta_summary(document, include_noops=args.all)
        return 0 if delta.outcome.state.value == "complete" else 2
    except (LedgerError, PulseSelectionError, ValueError, OSError) as exc:
        _print_json({"status": "error", "error": str(exc)})
        return 4 if isinstance(exc, PulseSelectionError) else 2
