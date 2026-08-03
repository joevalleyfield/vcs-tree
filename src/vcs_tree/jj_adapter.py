"""Read-only Jujutsu history collection for the v1 snapshot boundary."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .models import (
    CollectionError,
    CollectionOutcome,
    CollectionState,
    HistoryBoundary,
    HistoryBoundaryState,
)

Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]
NULL_COMMIT = "0" * 40


@dataclass(frozen=True)
class JjObservation:
    """Normalized factual jj observation, including the visible change graph."""

    root: Path
    store_hint: str | None
    workspaces: tuple[dict, ...]
    bookmarks: tuple[dict, ...]
    visible_heads: tuple[dict, ...]
    history: tuple[dict, ...]
    history_boundary: HistoryBoundary
    collection: dict[str, CollectionOutcome]

    def to_dict(self) -> dict:
        return {
            "root": str(self.root),
            "store_hint": self.store_hint,
            "workspaces": list(self.workspaces),
            "bookmarks": list(self.bookmarks),
            "visible_heads": list(self.visible_heads),
            "history": list(self.history),
            "history_boundary": self.history_boundary.to_dict(),
            "collection": {name: outcome.to_dict() for name, outcome in self.collection.items()},
        }


def _error(kind: str, stage: str, message: str, exit_code: int | None = None) -> CollectionError:
    return CollectionError(kind, stage, message or kind, exit_code)


def _outcome(state: CollectionState, *errors: CollectionError) -> CollectionOutcome:
    return CollectionOutcome(state, tuple(errors))


def _id(value: str, algorithm: str = "jj") -> dict[str, str]:
    return {"algorithm": algorithm, "value": value.lower()}


def _targets(value: str) -> list[dict[str, str]]:
    return [_id(item) for item in value.split(",") if item]


def _parse_history(line: str) -> dict:
    fields = line.split("\x00")
    if len(fields) != 10 or not fields[0]:
        raise ValueError("malformed jj history record")
    (
        commit,
        change,
        parents,
        author,
        email,
        authored,
        committer,
        committer_email,
        committed,
        description,
    ) = fields
    if commit == NULL_COMMIT:
        return {
            "kind": "virtual_root",
            "object_id": _id(commit),
            "change_id": None,
            "parents": [],
            "summary": "",
        }
    return {
        "kind": "commit",
        "object_id": _id(commit),
        "change_id": change,
        "parents": [_id(parent) for parent in parents.split() if parent],
        "author": {"name": author, "email": email, "timestamp": authored},
        "committer": {"name": committer, "email": committer_email, "timestamp": committed},
        "summary": description,
    }


def _parse_bookmark(line: str) -> dict:
    fields = line.split("\x00")
    if len(fields) != 7 or not fields[0]:
        raise ValueError("malformed jj bookmark record")
    name, remote, state, normal, removed, added, tracking = fields
    return {
        "name": name,
        "remote": remote or None,
        "state": state or "normal",
        "targets": _targets(normal),
        "removed_targets": _targets(removed),
        "added_targets": _targets(added),
        "tracking": tracking or None,
    }


def _parse_workspace(line: str) -> dict:
    fields = line.split("\x00")
    if len(fields) != 6 or not fields[0]:
        raise ValueError("malformed jj workspace record")
    name, path, commit, change, state, summary = fields
    return {
        "workspace_key": name,
        "native_name": name,
        "path": path,
        "is_primary": name == "default",
        "current": {"object_id": _id(commit), "change_id": change} if commit else None,
        "working_copy": {"state": state or "unknown", "summary": summary},
    }


class JjAdapter:
    """Collect jj-native surfaces without changing the repository."""

    def __init__(self, path: str | Path, *, timeout: float = 8.0, runner: Runner | None = None):
        self.path = Path(path)
        self.timeout = timeout
        self._runner = runner or self._run

    def _run(self, command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["jj", *command],
            cwd=self.path,
            text=True,
            capture_output=True,
            timeout=self.timeout,
            check=False,
        )

    def _call(self, command: Sequence[str], stage: str) -> tuple[str, CollectionError | None]:
        try:
            result = self._runner(command)
        except subprocess.TimeoutExpired:
            return "", _error("timeout", stage, "command timed out")
        except OSError as exc:
            return "", _error("process_error", stage, str(exc))
        if result.returncode:
            return "", _error("command_error", stage, result.stderr.strip(), result.returncode)
        return result.stdout, None

    def collect(self) -> JjObservation:
        root_output, root_error = self._call(("root", "--ignore-working-copy"), "jj.identity")
        if root_error:
            return JjObservation(
                self.path,
                None,
                (),
                (),
                (),
                (),
                HistoryBoundary(HistoryBoundaryState.UNKNOWN),
                {"identity": _outcome(CollectionState.ERROR, root_error)},
            )
        root = Path(root_output.strip())
        workspaces, workspace_outcome = self._workspaces()
        bookmarks, bookmark_outcome = self._bookmarks()
        visible, visible_outcome = self._visible_heads()
        history, history_outcome = self._history()
        history = _annotate_graph(history, visible, workspaces, bookmarks, history_outcome)
        return JjObservation(
            root,
            self._store_hint(),
            workspaces,
            bookmarks,
            visible,
            history,
            HistoryBoundary(HistoryBoundaryState.COMPLETE),
            {
                "identity": _outcome(CollectionState.COMPLETE),
                "workspaces": workspace_outcome,
                "bookmarks": bookmark_outcome,
                "visible_heads": visible_outcome,
                "history": history_outcome,
            },
        )

    def _store_hint(self) -> str | None:
        pointer = self.path / ".jj" / "repo"
        try:
            return pointer.read_text(encoding="utf-8").strip() or str(pointer)
        except OSError:
            return str(pointer) if pointer.exists() else None

    def _workspaces(self) -> tuple[tuple[dict, ...], CollectionOutcome]:
        template = (
            'self.name() ++ "\\x00" ++ self.root() ++ "\\x00" ++ self.target().commit_id() ++ '
            '"\\x00" ++ self.target().change_id() ++ "\\x00" ++ "unknown" ++ "\\x00" ++ '
            'self.target().description().first_line() ++ "\\n"'
        )
        output, error = self._call(
            ("workspace", "list", "--ignore-working-copy", "-T", template),
            "jj.workspaces",
        )
        if error:
            return (), _outcome(CollectionState.ERROR, error)
        records = []
        errors = []
        for line in output.splitlines():
            if not line:
                continue
            try:
                records.append(_parse_workspace(line))
            except ValueError as exc:
                errors.append(_error("parse_error", "jj.workspaces", str(exc)))
        return tuple(records), _outcome(
            CollectionState.PARTIAL if errors else CollectionState.COMPLETE, *errors
        )

    def _bookmarks(self) -> tuple[tuple[dict, ...], CollectionOutcome]:
        template = (
            'self.name() ++ "\\x00" ++ self.remote() ++ "\\x00" ++ self.conflict() ++ "\\x00" ++ '
            'self.normal_target().commit_id() ++ "\\x00" ++ '
            'self.removed_targets().map(|c| c.commit_id()).join(",") ++ "\\x00" ++ '
            'self.added_targets().map(|c| c.commit_id()).join(",") ++ "\\x00" ++ '
            'self.tracked() ++ "\\n"'
        )
        output, error = self._call(
            ("bookmark", "list", "--all-remotes", "--ignore-working-copy", "-T", template),
            "jj.bookmarks",
        )
        if error:
            return (), _outcome(CollectionState.ERROR, error)
        records = []
        errors = []
        for line in output.splitlines():
            if not line:
                continue
            try:
                records.append(_parse_bookmark(line))
            except ValueError as exc:
                errors.append(_error("parse_error", "jj.bookmarks", str(exc)))
        return tuple(
            sorted(records, key=lambda item: (item["name"], item["remote"] or ""))
        ), _outcome(CollectionState.PARTIAL if errors else CollectionState.COMPLETE, *errors)

    def _visible_heads(self) -> tuple[tuple[dict, ...], CollectionOutcome]:
        output, error = self._call(
            (
                "log",
                "-r",
                "visible_heads()",
                "--no-graph",
                "--ignore-working-copy",
                "-T",
                'commit_id ++ "\\x00" ++ change_id ++ "\\n"',
            ),
            "jj.visible_heads",
        )
        if error:
            return (), _outcome(CollectionState.ERROR, error)
        heads = []
        errors = []
        for line in output.splitlines():
            fields = line.split("\x00")
            if len(fields) != 2 or not fields[0]:
                errors.append(
                    _error("parse_error", "jj.visible_heads", "malformed visible head record")
                )
                continue
            heads.append(
                {"object_id": _id(fields[0]), "change_id": fields[1], "authority": "visible_head"}
            )
        return tuple(sorted(heads, key=lambda item: item["object_id"]["value"])), _outcome(
            CollectionState.PARTIAL if errors else CollectionState.COMPLETE, *errors
        )

    def _history(self) -> tuple[tuple[dict, ...], CollectionOutcome]:
        template = (
            "commit_id++\\x00++change_id++\\x00++parents.map(|p| p.commit_id()).join(' ')++"
            "\\x00++author.name()++\\x00++author.email()++\\x00++author.timestamp()++"
            "\\x00++committer.name()++\\x00++committer.email()++\\x00++description.first_line()++\\n"
        )
        output, error = self._call(
            ("log", "-r", "all()", "--no-graph", "--ignore-working-copy", "-T", template),
            "jj.history",
        )
        if error:
            return (), _outcome(CollectionState.ERROR, error)
        history = []
        errors = []
        for line in output.splitlines():
            if not line:
                continue
            try:
                history.append(_parse_history(line))
            except ValueError as exc:
                errors.append(_error("parse_error", "jj.history", str(exc)))
        return tuple(history), _outcome(
            CollectionState.PARTIAL if errors else CollectionState.COMPLETE, *errors
        )


def _annotate_graph(
    history: tuple[dict, ...],
    visible_heads: tuple[dict, ...],
    workspaces: tuple[dict, ...],
    bookmarks: tuple[dict, ...],
    outcome: CollectionOutcome,
) -> tuple[dict, ...]:
    """Attach visibility, authorities, and parent change edges to each version."""
    by_commit = {
        item["object_id"]["value"]: item for item in history if item.get("kind") == "commit"
    }
    visible = {item["object_id"]["value"] for item in visible_heads}
    workspace_ids = {
        (workspace.get("current") or {}).get("object_id", {}).get("value")
        for workspace in workspaces
    }
    workspace_ids.discard(None)
    authorities: dict[str, set[str]] = {key: set() for key in by_commit}
    for item in visible_heads:
        key = item["object_id"]["value"]
        if key in authorities:
            authorities[key].add("visible_head")
    for key in workspace_ids:
        if key in authorities:
            authorities[key].add("workspace_head")
    for bookmark in bookmarks:
        authority = "jj_remote_bookmark" if bookmark.get("remote") else "jj_local_bookmark"
        for target in [*bookmark.get("targets", ()), *bookmark.get("added_targets", ())]:
            key = target.get("value")
            if key in authorities:
                authorities[key].add(authority)
    annotated = []
    for item in history:
        record = dict(item)
        if item.get("kind") == "virtual_root":
            annotated.append(record)
            continue
        object_id = item["object_id"]["value"]
        record["visibility"] = (
            "unknown"
            if outcome.state is not CollectionState.COMPLETE
            else "visible"
            if object_id in visible
            else "hidden"
        )
        record["authorities"] = sorted(authorities.get(object_id, ()))
        parent_changes = []
        for parent in item.get("parents", ()):
            parent_record = by_commit.get(parent.get("value"))
            parent_changes.append(
                {
                    "object_id": parent,
                    "change_id": parent_record.get("change_id") if parent_record else None,
                }
            )
        record["parent_changes"] = parent_changes
        annotated.append(record)
    return tuple(annotated)


__all__ = ["JjAdapter", "JjObservation", "NULL_COMMIT"]
