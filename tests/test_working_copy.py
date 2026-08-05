import pytest

from vcs_tree.working_copy import parse_git_status, parse_jj_current, parse_jj_summary


def git_record(xy, path="file.txt"):
    return f"1 {xy} N... 100644 100644 100644 abc def {path}"


@pytest.mark.parametrize(
    ("xy", "status"),
    [
        (".M", "modified"),
        ("A.", "added"),
        ("D.", "deleted"),
        ("R.", "renamed"),
        ("C.", "copied"),
        ("T.", "type_changed"),
        ("UU", "conflicted"),
    ],
)
def test_git_status_codes_are_preserved(xy, status):
    parsed = parse_git_status(git_record(xy) + "\x00", limit=4)
    assert parsed.entries[0] == {"status": status, "path": "file.txt"}
    assert parsed.state == ("conflicted" if status == "conflicted" else "dirty")


def test_git_status_tracks_unborn_clean_untracked_rename_and_bounds():
    clean = parse_git_status(
        "# branch.oid (initial)\x00# branch.head main\x00! ignored\x00", limit=2
    )
    assert clean.unborn is True and clean.current_object is None and clean.state == "clean"

    renamed = (
        "# branch.oid ABCDEF\x00"
        "2 R. N... 100644 100644 100644 abc def R100 new name.txt\x00old name.txt\x00"
        "? untracked.txt\x00" + git_record(".M", "third.txt") + "\x00"
    )
    parsed = parse_git_status(renamed, limit=2)
    assert parsed.current_object == "ABCDEF"
    assert parsed.entries[0]["old_path"] == "old name.txt"
    assert parsed.entries[1]["status"] == "added"
    assert parsed.truncated is True
    assert parse_git_status("# branch.oid ABC", limit=0).state == "clean"


@pytest.mark.parametrize(
    "value",
    [
        "bad\x00",
        "1 .M too-short\x00",
        git_record("..") + "\x00",
        "2 R. N... 100644 100644 100644 abc def R100 new.txt\x00",
    ],
)
def test_git_status_rejects_malformed_records(value):
    with pytest.raises(ValueError):
        parse_git_status(value, limit=4)
    with pytest.raises(ValueError):
        parse_git_status("", limit=-1)


def test_git_unmerged_record_is_parsed():
    record = "u UU N... 100644 100644 100644 100644 a b c conflict.txt\x00"
    assert parse_git_status(record, limit=1).entries[0]["status"] == "conflicted"


def test_jj_current_preserves_boundary_and_recorded_facts():
    current = parse_jj_current("ABC\x00change\x00" + "000000 111111\x00false\x00true\x00draft\n")
    assert current["current"]["object_id"]["value"] == "abc"
    assert [item["value"] for item in current["parents"]] == ["000000", "111111"]
    assert current["empty"] is False
    assert current["conflicted"] is True
    assert current["description"] == "draft"


@pytest.mark.parametrize(
    "value",
    ["bad", "\x00change\x00parent\x00true\x00false\x00draft", "A\x00c\x00p\x00yes\x00false\x00d"],
)
def test_jj_current_rejects_malformed_records(value):
    with pytest.raises(ValueError):
        parse_jj_current(value)


def test_jj_summary_preserves_statuses_conflicts_and_bounds():
    parsed = parse_jj_summary("A added\nM modified\nD deleted\nR renamed\nC conflict\n", limit=4)
    assert [item["status"] for item in parsed.entries] == [
        "added",
        "modified",
        "deleted",
        "renamed",
    ]
    assert parsed.state == "conflicted"
    assert parsed.truncated is True
    assert parse_jj_summary("", limit=0).state == "clean"
    assert len(parse_jj_summary("M first\n\nM second\n", limit=2).entries) == 2


@pytest.mark.parametrize("value", ["bad", "X path", "M "])
def test_jj_summary_rejects_malformed_records(value):
    with pytest.raises(ValueError):
        parse_jj_summary(value, limit=1)
    with pytest.raises(ValueError):
        parse_jj_summary("", limit=-1)
