"""Read-only Git history collection for the v1 snapshot boundary."""

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
    ObjectId,
)

Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class GitObservation:
    """Normalized factual Git observation; persistence belongs to later tasks."""

    root: Path
    identity: CollectionOutcome
    workspaces: tuple[dict, ...]
    refs: tuple[dict, ...]
    history: tuple[dict, ...]
    history_boundary: HistoryBoundary
    collection: dict[str, CollectionOutcome]

    def to_dict(self) -> dict:
        return {
            "root": str(self.root),
            "identity": self.identity.to_dict(),
            "workspaces": list(self.workspaces),
            "refs": list(self.refs),
            "history": list(self.history),
            "history_boundary": self.history_boundary.to_dict(),
            "collection": {name: outcome.to_dict() for name, outcome in self.collection.items()},
        }


def _error(kind: str, stage: str, message: str, exit_code: int | None = None) -> CollectionError:
    return CollectionError(kind, stage, message or kind, exit_code)


def _outcome(state: CollectionState, *errors: CollectionError) -> CollectionOutcome:
    return CollectionOutcome(state, tuple(errors))


def _parse_ref(line: str) -> dict:
    fields = line.split("\x00")
    if len(fields) != 4 or not all(fields[:3]):
        raise ValueError("malformed for-each-ref record")
    name, object_id, object_type, peeled = fields
    namespace = (
        "local"
        if name.startswith("refs/heads/")
        else "remote"
        if name.startswith("refs/remotes/")
        else "tag"
    )
    record = {
        "name": name,
        "authority": namespace,
        "object_id": {"algorithm": "sha1", "value": object_id.lower()},
        "object_type": object_type,
        "peeled_object_id": None,
    }
    if peeled:
        record["peeled_object_id"] = {"algorithm": "sha1", "value": peeled.lower()}
    return record


def _parse_commit(line: str) -> dict:
    fields = line.split("\x00")
    if len(fields) != 9 or not fields[0]:
        raise ValueError("malformed commit record")
    (
        object_id,
        parents,
        author,
        author_email,
        author_time,
        committer,
        committer_email,
        committer_time,
        summary,
    ) = fields
    parent_ids = [
        {"algorithm": "sha1", "value": parent.lower()}
        for parent in parents.split()
        if parent
    ]
    return {
        "kind": "commit",
        "object_id": {"algorithm": "sha1", "value": object_id.lower()},
        "parents": parent_ids,
        "author": {"name": author, "email": author_email, "timestamp": author_time},
        "committer": {"name": committer, "email": committer_email, "timestamp": committer_time},
        "summary": summary,
    }


def _parse_worktrees(output: str) -> tuple[dict, ...]:
    records = []
    current: dict[str, str] = {}
    for line in output.splitlines() + [""]:
        if line:
            key, _, value = line.partition(" ")
            if key in {"worktree", "HEAD", "branch"}:  # pragma: no branch
                current[key] = value
            continue
        if current:
            records.append(
                {
                    "path": current.get("worktree", ""),
                    "head": current.get("HEAD"),
                    "branch": current.get("branch"),
                    "role": "primary" if not records else "linked",
                }
            )
            current = {}
    return tuple(records)


class GitAdapter:
    """Collect selected Git surfaces without changing the repository."""

    def __init__(self, path: str | Path, *, timeout: float = 8.0, runner: Runner | None = None):
        self.path = Path(path)
        self.timeout = timeout
        self._runner = runner or self._run

    def _run(self, command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *command],
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

    def collect(self) -> GitObservation:
        root_output, root_error = self._call(("rev-parse", "--show-toplevel"), "git.identity")
        if root_error:
            return GitObservation(
                self.path,
                _outcome(CollectionState.ERROR, root_error),
                (),
                (),
                (),
                HistoryBoundary(HistoryBoundaryState.UNKNOWN),
                {"identity": _outcome(CollectionState.ERROR, root_error)},
            )
        root = Path(root_output.strip())
        identity = _outcome(CollectionState.COMPLETE)
        workspaces, workspace_outcome = self._workspaces()
        refs, ref_outcome = self._refs()
        history, history_outcome, boundary = self._history(refs)
        return GitObservation(
            root,
            identity,
            workspaces,
            refs,
            history,
            boundary,
            {
                "identity": identity,
                "workspaces": workspace_outcome,
                "refs": ref_outcome,
                "history": history_outcome,
            },
        )

    def _workspaces(self) -> tuple[tuple[dict, ...], CollectionOutcome]:
        output, error = self._call(("worktree", "list", "--porcelain"), "git.workspaces")
        if error:
            return (), _outcome(CollectionState.ERROR, error)
        records = _parse_worktrees(output)
        if not records:
            status, status_error = self._call(("status", "--porcelain=v1"), "git.working_copy")
            if status_error:
                return (), _outcome(CollectionState.PARTIAL, status_error)
            records = (
                {
                    "path": str(self.path),
                    "head": None,
                    "branch": None,
                    "role": "primary",
                    "status": status,
                },
            )
        else:
            for record in records:
                if record["path"] == str(self.path):
                    status, status_error = self._call(
                        ("status", "--porcelain=v1"), "git.working_copy"
                    )
                    record["working_copy"] = {
                        "state": "unknown" if status_error else "dirty" if status else "clean",
                        "status": status,
                    }
        return records, _outcome(CollectionState.COMPLETE)

    def _refs(self) -> tuple[tuple[dict, ...], CollectionOutcome]:
        format_string = "%(refname)%00%(objectname)%00%(objecttype)%00%(*objectname)"
        output, error = self._call(
            (
                "for-each-ref",
                "--format=" + format_string,
                "refs/heads",
                "refs/remotes",
                "refs/tags",
            ),
            "git.refs",
        )
        if error:
            return (), _outcome(CollectionState.ERROR, error)
        try:
            refs = tuple(
                sorted(
                    (_parse_ref(line) for line in output.splitlines() if line),
                    key=lambda item: item["name"],
                )
            )
        except ValueError as exc:
            return (), _outcome(
                CollectionState.PARTIAL, _error("parse_error", "git.refs", str(exc))
            )
        return refs, _outcome(CollectionState.COMPLETE)

    def _history(
        self, refs: tuple[dict, ...]
    ) -> tuple[tuple[dict, ...], CollectionOutcome, HistoryBoundary]:
        roots = [ref["peeled_object_id"] or ref["object_id"] for ref in refs]
        values = [root["value"] for root in roots]
        if not values:
            return (), _outcome(CollectionState.COMPLETE), HistoryBoundary(
                HistoryBoundaryState.COMPLETE
            )
        output, error = self._call(
            (
                "log",
                "--format=%H%x00%P%x00%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI%x00%s",
                *values,
            ),
            "git.history",
        )
        if error:
            return (), _outcome(CollectionState.ERROR, error), HistoryBoundary(
                HistoryBoundaryState.UNKNOWN
            )
        try:
            history = tuple(_parse_commit(line) for line in output.splitlines() if line)
        except ValueError as exc:
            return (), _outcome(
                CollectionState.PARTIAL, _error("parse_error", "git.history", str(exc))
            ), HistoryBoundary(HistoryBoundaryState.UNKNOWN)
        shallow_file = self.path / ".git" / "shallow"
        boundaries = ()
        if shallow_file.is_file():
            boundaries = tuple(
                {"algorithm": "sha1", "value": line.strip().lower()}
                for line in shallow_file.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        if boundaries:
            return history, _outcome(CollectionState.COMPLETE), HistoryBoundary(
                HistoryBoundaryState.SHALLOW,
                tuple(ObjectId.from_dict(item) for item in boundaries),
            )
        return history, _outcome(CollectionState.COMPLETE), HistoryBoundary(
            HistoryBoundaryState.COMPLETE
        )


__all__ = ["GitAdapter", "GitObservation"]
