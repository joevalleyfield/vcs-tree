"""Command-line interface for vcs-tree."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from vcs_tree.delta import HistoryDeltaCalculator
from vcs_tree.ledger import HistoryLedger, LedgerError, resolve_paths
from vcs_tree.scanner import vcs_tree
from vcs_tree.snapshot import SnapshotCollector


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="vcs-tree",
        description="Parallel VCS repo scanner with stall-detection display.",
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
    ):
        sub = history_sub.add_parser(name, help=help_text)
        sub.add_argument("--state-root", help="Authoritative state directory")
    history_sub.choices["init"].add_argument("--writer-id", help="Enroll this writer identity")
    history_sub.choices["snapshot"].add_argument("path", nargs="?", default=".")
    delta = history_sub.choices["delta"]
    delta.add_argument("--from", dest="from_snapshot", required=True)
    delta.add_argument("--to", dest="to_snapshot", required=True)
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
    try:
        ledger = HistoryLedger.open(state_root)
        if args.history_command == "snapshot":
            result = SnapshotCollector(ledger).collect(Path(args.path))
            _print_json(result.envelope.to_dict())
            return 0 if result.envelope.scan.get("outcome", {}).get("state") == "complete" else 2
        snapshots = ledger._load(ledger._SNAPSHOTS)
        entries = {item.get("snapshot_id"): item for item in snapshots if item.get("manifest")}
        before = entries.get(args.from_snapshot)
        after = entries.get(args.to_snapshot)
        if before is None or after is None:
            _print_json({"status": "error", "error": "snapshot not found"})
            return 2
        delta = HistoryDeltaCalculator(ledger).calculate(before["manifest"], after["manifest"])
        _print_json(delta.to_dict())
        return 0 if delta.outcome.state.value == "complete" else 2
    except (LedgerError, ValueError, OSError) as exc:
        _print_json({"status": "error", "error": str(exc)})
        return 2
