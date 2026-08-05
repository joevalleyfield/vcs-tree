"""Read-only Git history collection for the v1 snapshot boundary."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
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
from .working_copy import parse_git_status

Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]
Clock = Callable[[], str]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
    observed_at: str | None = None

    def to_dict(self) -> dict:
        return {
            "root": str(self.root),
            "identity": self.identity.to_dict(),
            "workspaces": list(self.workspaces),
            "refs": list(self.refs),
            "history": list(self.history),
            "history_boundary": self.history_boundary.to_dict(),
            "collection": {name: outcome.to_dict() for name, outcome in self.collection.items()},
            "observed_at": self.observed_at,
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
        {"algorithm": "sha1", "value": parent.lower()} for parent in parents.split() if parent
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

    def __init__(
        self,
        path: str | Path,
        *,
        timeout: float = 8.0,
        runner: Runner | None = None,
        clock: Clock = _now,
        entry_limit: int = 256,
    ):
        self.path = Path(path)
        self.timeout = timeout
        self._runner = runner or self._run
        self.observed_at = clock()
        self.entry_limit = entry_limit

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
                self.observed_at,
            )
        root = Path(root_output.strip())
        if root.resolve() != self.path.resolve():
            error = _error(
                "boundary_error",
                "git.identity",
                f"Git resolved parent root {root} for requested root {self.path}",
            )
            return GitObservation(
                self.path,
                _outcome(CollectionState.ERROR, error),
                (),
                (),
                (),
                HistoryBoundary(HistoryBoundaryState.UNKNOWN),
                {"identity": _outcome(CollectionState.ERROR, error)},
                self.observed_at,
            )
        identity = _outcome(CollectionState.COMPLETE)
        workspaces, workspace_outcome = self._workspaces()
        working_copy_outcome, path_outcome = self._working_copy_outcomes(workspaces)
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
                "working_copy": working_copy_outcome,
                "path_evidence": path_outcome,
            },
            self.observed_at,
        )

    def _workspaces(self) -> tuple[tuple[dict, ...], CollectionOutcome]:
        output, error = self._call(("worktree", "list", "--porcelain"), "git.workspaces")
        if error:
            return (), _outcome(CollectionState.ERROR, error)
        records = _parse_worktrees(output)
        if not records:
            records = (
                {
                    "path": str(self.path),
                    "head": None,
                    "branch": None,
                    "role": "primary",
                },
            )
        for record in records:
            if Path(record["path"]).resolve() == self.path.resolve():
                record["working_copy"] = self._working_copy()
            else:
                record["working_copy"] = self._unobserved_working_copy()
        return records, _outcome(CollectionState.COMPLETE)

    def _working_copy(self) -> dict:
        output, error = self._call(
            (
                "--no-optional-locks",
                "status",
                "--porcelain=v2",
                "--branch",
                "-z",
                "--untracked-files=all",
            ),
            "git.working_copy",
        )
        refresh = {"state": "not_applicable", "errors": []}
        if error:
            outcome = _outcome(CollectionState.ERROR, error).to_dict()
            outcome["attempted_at"] = self.observed_at
            return {
                "state": "unreadable",
                "recorded_state": "unreadable",
                "unborn": None,
                "current": None,
                "outcome": outcome,
                "refresh": refresh,
                "freshness": "unknown",
                "entries_outcome": outcome,
                "entries_limit": self.entry_limit,
                "entries_truncated": False,
                "entries": [],
            }
        try:
            parsed = parse_git_status(output, limit=self.entry_limit)
        except ValueError as exc:
            parse_error = _error("parse_error", "git.working_copy", str(exc))
            outcome = _outcome(CollectionState.PARTIAL, parse_error).to_dict()
            outcome["attempted_at"] = self.observed_at
            return {
                "state": "unknown",
                "recorded_state": "unknown",
                "unborn": None,
                "current": None,
                "outcome": outcome,
                "refresh": refresh,
                "freshness": "unknown",
                "entries_outcome": outcome,
                "entries_limit": self.entry_limit,
                "entries_truncated": False,
                "entries": [],
            }
        outcome = _outcome(CollectionState.COMPLETE).to_dict()
        outcome["attempted_at"] = self.observed_at
        current = (
            {"object_id": {"algorithm": "sha1", "value": parsed.current_object.lower()}}
            if parsed.current_object
            else None
        )
        return {
            "state": parsed.state,
            "recorded_state": parsed.state,
            "unborn": parsed.unborn,
            "current": current,
            "outcome": outcome,
            "refresh": refresh,
            "freshness": "current",
            "entries_outcome": outcome,
            "entries_limit": self.entry_limit,
            "entries_truncated": parsed.truncated,
            "entries": list(parsed.entries),
        }

    def _unobserved_working_copy(self) -> dict:
        return {
            "state": "unknown",
            "recorded_state": "unknown",
            "unborn": None,
            "current": None,
            "outcome": {"state": "not_requested", "errors": []},
            "refresh": {"state": "not_applicable", "errors": []},
            "freshness": "not_applicable",
            "entries_outcome": {"state": "not_requested", "errors": []},
            "entries_limit": self.entry_limit,
            "entries_truncated": False,
            "entries": [],
        }

    def _working_copy_outcomes(
        self, workspaces: tuple[dict, ...]
    ) -> tuple[CollectionOutcome, CollectionOutcome]:
        for workspace in workspaces:
            working_copy = workspace.get("working_copy", {})
            if working_copy.get("outcome", {}).get("state") != "not_requested":
                return (
                    CollectionOutcome.from_dict(working_copy["outcome"]),
                    CollectionOutcome.from_dict(working_copy["entries_outcome"]),
                )
        not_requested = _outcome(CollectionState.NOT_REQUESTED)
        return not_requested, not_requested

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
            return (
                (),
                _outcome(CollectionState.COMPLETE),
                HistoryBoundary(HistoryBoundaryState.COMPLETE),
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
            return (
                (),
                _outcome(CollectionState.ERROR, error),
                HistoryBoundary(HistoryBoundaryState.UNKNOWN),
            )
        try:
            history = tuple(_parse_commit(line) for line in output.splitlines() if line)
        except ValueError as exc:
            return (
                (),
                _outcome(CollectionState.PARTIAL, _error("parse_error", "git.history", str(exc))),
                HistoryBoundary(HistoryBoundaryState.UNKNOWN),
            )
        shallow_file = self.path / ".git" / "shallow"
        boundaries = ()
        if shallow_file.is_file():
            boundaries = tuple(
                {"algorithm": "sha1", "value": line.strip().lower()}
                for line in shallow_file.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
        if boundaries:
            return (
                history,
                _outcome(CollectionState.COMPLETE),
                HistoryBoundary(
                    HistoryBoundaryState.SHALLOW,
                    tuple(ObjectId.from_dict(item) for item in boundaries),
                ),
            )
        return (
            history,
            _outcome(CollectionState.COMPLETE),
            HistoryBoundary(HistoryBoundaryState.COMPLETE),
        )


__all__ = ["GitAdapter", "GitObservation"]
