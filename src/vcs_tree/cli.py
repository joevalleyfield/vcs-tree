"""Command-line interface for vcs-tree."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from vcs_tree.scanner import vcs_tree


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


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line scanner."""
    args = build_parser().parse_args(argv)
    vcs_tree(args.path, tree_mode=not args.flat, text_symbols=args.text_symbols)
    return 0
