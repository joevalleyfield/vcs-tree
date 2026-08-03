import pytest

from vcs_tree.pulse_semantics import (
    classify_task_paths,
    classify_warning_lifecycles,
    task_path_events,
    warning_key,
)


def paths(*entries):
    return ({"object_id": "commit", "parent_id": "parent", "paths": list(entries)},)


@pytest.mark.parametrize(
    ("status", "path", "old", "expected"),
    [
        ("added", "tasks/open/a.md", None, "task_path_added"),
        ("added", "tasks/closed/a.md", None, "task_path_added"),
        ("deleted", "tasks/open/a.md", None, "task_path_removed"),
        ("modified", "tasks/open/a.md", None, "task_path_modified"),
        ("type_changed", "tasks/closed/a.md", None, "task_path_modified"),
        ("renamed", "tasks/closed/a.md", "tasks/open/a.md", "task_path_moved"),
        ("renamed", "tasks/open/b.md", "tasks/open/a.md", "task_path_renamed"),
        ("renamed", "tasks/open/a.md", "outside.txt", "task_path_renamed"),
        ("copied", "tasks/closed/b.md", "tasks/open/a.md", "task_path_copied"),
        ("copied", "outside.txt", "tasks/open/a.md", "task_path_copied"),
    ],
)
def test_task_path_vocabulary_and_evidence(status, path, old, expected):
    item = {"status": status, "path": path}
    if old is not None:
        item["old_path"] = old
    result = classify_task_paths(paths(item))
    assert result[0]["event"] == expected
    assert result[0]["commit_id"] == "commit"
    assert result[0]["parent_id"] == "parent"
    assert result[0]["new_path"] == (None if status == "deleted" else path)


def test_task_paths_are_case_sensitive_and_ignore_unknown_or_outside_changes():
    result = classify_task_paths(
        paths(
            {"status": "added", "path": "Tasks/open/a.md"},
            {"status": "added", "path": "tasks/open/a.txt"},
            {"status": "deleted", "path": "tasks/closed/"},
            {"status": "unknown", "path": "tasks/open/a.md"},
            {"status": "modified", "path": "README.md"},
            "not-a-path-record",
            {"status": "copied", "path": "new.txt", "old_path": "old.txt"},
        )
    )
    assert result == ()
    assert classify_task_paths((None,)) == ()


def test_rename_outside_to_outside_is_not_a_task_event():
    assert (
        classify_task_paths(paths({"status": "renamed", "path": "new.txt", "old_path": "old.txt"}))
        == ()
    )


def test_task_path_alias_and_deterministic_order():
    result = task_path_events(
        (
            {
                "object_id": "b",
                "parent_id": None,
                "paths": [{"status": "added", "path": "tasks/open/z.md"}],
            },
            {
                "object_id": "a",
                "parent_id": None,
                "paths": [{"status": "added", "path": "tasks/open/a.md"}],
            },
        )
    )
    assert [item["commit_id"] for item in result] == ["a", "b"]


def test_warning_identity_uses_contract_fields_only():
    warning = {
        "repository_key": "repo",
        "component": "history",
        "kind": "boundary",
        "stage": "snapshot",
        "affected_event_class": "head",
        "message": "volatile",
    }
    assert warning_key(warning) == "repo|history|boundary|snapshot|head"
    assert warning_key("@scan|scan|error|-|-") == "@scan|scan|error|-|-"
    assert warning_key({"warning_key": "stable", "message": "changed"}) == "stable"


def test_warning_lifecycle_and_message_change():
    source = [
        {"warning_key": "repo|scan|error|read|-", "message": "old"},
        {"warning_key": "repo|scan|gone|read|-"},
    ]
    target = [
        {"warning_key": "repo|scan|error|read|-", "message": "new"},
        {"warning_key": "repo|scan|fresh|read|-"},
    ]
    result = classify_warning_lifecycles(source, target)
    by_key = {item["warning_key"]: item for item in result}
    assert by_key["repo|scan|error|read|-"]["lifecycle"] == "persistent"
    assert by_key["repo|scan|error|read|-"]["message"] == "new"
    assert by_key["repo|scan|gone|read|-"]["lifecycle"] == "recovered"
    assert by_key["repo|scan|fresh|read|-"]["lifecycle"] == "new"


def test_warning_normalization_defaults_and_comparison_only():
    result = classify_warning_lifecycles(
        source=[{"kind": "boundary", "component": "history", "stage": "snapshot"}],
        comparison_only=[
            {
                "repository_key": "repo",
                "component": "delta",
                "kind": "suppressed",
                "stage": "compare",
                "evidence_class": "head",
            }
        ],
    )
    assert result[0]["lifecycle"] == "new"
    assert result[0]["comparison_only"] is True
    assert result[0]["source_present"] is False
    assert result[0]["target_present"] is False
