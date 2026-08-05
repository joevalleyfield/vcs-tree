"""Native working-copy parsing shared by Git and jj adapters."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkingCopyParse:
    state: str
    entries: tuple[dict, ...]
    current_object: str | None = None
    unborn: bool = False
    truncated: bool = False


def _status(xy: str) -> str:
    if "U" in xy:
        return "conflicted"
    for marker, status in (
        ("R", "renamed"),
        ("C", "copied"),
        ("A", "added"),
        ("D", "deleted"),
        ("T", "type_changed"),
        ("M", "modified"),
    ):
        if marker in xy:
            return status
    raise ValueError(f"unsupported Git status code: {xy!r}")


def parse_git_status(output: str, *, limit: int) -> WorkingCopyParse:
    """Parse `git status --porcelain=v2 --branch -z` deterministically."""
    if limit < 0:
        raise ValueError("entry limit must be non-negative")
    fields = output.split("\x00")
    if fields and fields[-1] == "":
        fields.pop()
    entries = []
    current_object = None
    unborn = False
    index = 0
    while index < len(fields):
        record = fields[index]
        index += 1
        if record.startswith("# branch.oid "):
            value = record.removeprefix("# branch.oid ")
            unborn = value == "(initial)"
            current_object = None if unborn else value
            continue
        if record.startswith("# ") or record.startswith("! "):
            continue
        if record.startswith("? "):
            entries.append({"status": "added", "path": record[2:]})
            continue
        parts = record.split(" ")
        if not parts or parts[0] not in {"1", "2", "u"}:
            raise ValueError("malformed Git status record")
        minimum = {"1": 9, "2": 10, "u": 11}[parts[0]]
        if len(parts) < minimum:
            raise ValueError("malformed Git status record")
        entry = {"status": _status(parts[1]), "path": " ".join(parts[minimum - 1 :])}
        if parts[0] == "2":
            if index >= len(fields):
                raise ValueError("renamed Git status record lacks old path")
            entry["old_path"] = fields[index]
            index += 1
        entries.append(entry)
    conflicted = any(entry["status"] == "conflicted" for entry in entries)
    truncated = len(entries) > limit
    return WorkingCopyParse(
        "conflicted" if conflicted else "dirty" if entries else "clean",
        tuple(entries[:limit]),
        current_object,
        unborn,
        truncated,
    )


def parse_jj_current(output: str) -> dict:
    """Parse one NUL-delimited `jj log -r @` working-copy record."""
    fields = output.rstrip("\n").split("\x00")
    if len(fields) != 6 or not fields[0]:
        raise ValueError("malformed jj working-copy record")
    commit, change, parents, empty, conflict, description = fields
    if empty not in {"true", "false"} or conflict not in {"true", "false"}:
        raise ValueError("malformed jj working-copy booleans")
    return {
        "current": {
            "object_id": {"algorithm": "jj", "value": commit.lower()},
            "change_id": change,
        },
        "parents": [
            {"algorithm": "jj", "value": parent.lower()} for parent in parents.split() if parent
        ],
        "empty": empty == "true",
        "conflicted": conflict == "true",
        "description": description,
    }


def parse_jj_summary(output: str, *, limit: int) -> WorkingCopyParse:
    """Parse bounded `jj diff --summary -r @` path evidence."""
    if limit < 0:
        raise ValueError("entry limit must be non-negative")
    status_by_code = {
        "A": "added",
        "M": "modified",
        "D": "deleted",
        "R": "renamed",
        "C": "conflicted",
    }
    entries = []
    for line in output.splitlines():
        if not line:
            continue
        code, separator, path = line.partition(" ")
        if not separator or code not in status_by_code or not path:
            raise ValueError("malformed jj diff summary record")
        entries.append({"status": status_by_code[code], "path": path})
    conflicted = any(entry["status"] == "conflicted" for entry in entries)
    return WorkingCopyParse(
        "conflicted" if conflicted else "dirty" if entries else "clean",
        tuple(entries[:limit]),
        truncated=len(entries) > limit,
    )


__all__ = ["WorkingCopyParse", "parse_git_status", "parse_jj_current", "parse_jj_summary"]
