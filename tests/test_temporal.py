import copy
import json

import pytest

import vcs_tree.temporal as temporal_module
from vcs_tree.models import (
    V2_REPOSITORY_COMPONENTS,
    CollectionError,
    ContractError,
    HistoryStore,
    SnapshotEnvelope,
    SnapshotEnvelopeV2,
)
from vcs_tree.temporal import TemporalIndexBuilder, fact_key, fact_state

STORE = "store"


def timestamp(generation):
    return f"2026-08-04T12:0{generation}:00Z"


def outcome(state, generation, errors=()):
    value = {"state": state, "errors": [error.to_dict() for error in errors]}
    if state != "not_requested":
        value["attempted_at"] = timestamp(generation)
    return value


def working_copy(generation, *, state="clean", entries=(), entries_state="complete"):
    return {
        "outcome": outcome("complete", generation),
        "recorded_state": state,
        "refresh": {
            "state": "performed",
            "attempted_at": timestamp(generation),
            "errors": [],
        },
        "freshness": "current",
        "entries_outcome": outcome(entries_state, generation),
        "entries_limit": 20,
        "entries_truncated": False,
        "entries": list(entries),
    }


def repository(
    generation,
    *,
    repository_key="repo-1",
    path="/scope/repo",
    mode="git",
    refs=(),
    ref_state="complete",
    entries=(),
    entries_state="complete",
    bookmarks=(),
    graph=None,
    jj_history_state="not_requested",
    roots=(),
):
    components = {name: outcome("not_requested", generation) for name in V2_REPOSITORY_COMPONENTS}
    components.update(
        {
            "identity": outcome("complete", generation),
            "git_worktrees": outcome("complete" if mode == "git" else "not_requested", generation),
            "jj_workspaces": outcome(
                "complete" if mode in {"jj", "colocated"} else "not_requested", generation
            ),
            "git_refs": outcome(
                ref_state if mode in {"git", "colocated"} else "not_requested", generation
            ),
            "jj_bookmarks": outcome(
                "complete" if mode in {"jj", "colocated"} else "not_requested", generation
            ),
            "jj_visible_heads": outcome(
                "complete" if mode in {"jj", "colocated"} else "not_requested", generation
            ),
            "git_history": outcome(
                "complete" if mode in {"git", "colocated"} else "not_requested", generation
            ),
            "jj_history": outcome(jj_history_state, generation),
            "path_evidence": outcome(entries_state, generation),
        }
    )
    workspace_key = f"{repository_key}:default"
    workspace = {
        "workspace_key": workspace_key,
        "path": path,
        "current": {
            "object_id": {"algorithm": "sha1" if mode == "git" else "jj", "value": "head"},
            "change_id": None if mode == "git" else "change-head",
        },
        "working_copy": working_copy(
            generation,
            state="dirty" if entries else "clean",
            entries=entries,
            entries_state=entries_state,
        ),
    }
    return {
        "repository_key": repository_key,
        "mode": mode,
        "locations": [{"path": path, "relative_path": "repo", "role": "primary"}],
        "collection": components,
        "workspaces": [workspace],
        "refs": list(refs),
        "bookmarks": list(bookmarks),
        "publication_hints": {"git_refs": list(refs), "jj_bookmarks": list(bookmarks)},
        "change_graph": graph,
        "roots": list(roots),
    }


def snapshot(generation, repositories, *, scan_state="complete"):
    document = SnapshotEnvelopeV2(
        f"snapshot-{generation}",
        timestamp(generation),
        {"name": "vcs-tree"},
        HistoryStore(STORE, generation, writer_id="writer"),
        {
            "root": "/scope",
            "outcome": {"state": scan_state, "errors": []},
        },
        tuple(repositories),
    )
    return {
        "snapshot_id": document.snapshot_id,
        "generation": generation,
        "manifest": document.to_dict(),
    }


def ref(name, target):
    return {
        "name": name,
        "authority": "local",
        "object_id": {"algorithm": "sha1", "value": target},
        "peeled_object_id": None,
    }


def facts_by_key(index):
    return {item["fact_key"]: item for item in index["facts"]}


def components_by_key(index):
    return {item["component_key"]: item for item in index["components"]}


def test_ref_confirmation_invalidation_target_change_and_reappearance():
    snapshots = [
        snapshot(1, [repository(1, refs=[ref("main", "a"), ref("side", "s")])]),
        snapshot(2, [repository(2, refs=[ref("main", "a")], ref_state="partial")]),
        snapshot(3, [repository(3, refs=[ref("main", "b")])]),
        snapshot(4, [repository(4, refs=[])]),
        snapshot(5, [repository(5, refs=[ref("main", "b")])]),
    ]
    index = TemporalIndexBuilder().build(reversed(snapshots), store_id=STORE)
    facts = facts_by_key(index)
    main = facts[fact_key("git-ref-exists", "repo-1", "main")]
    old_target = facts[fact_key("git-ref-target", "repo-1", "main", "direct", "sha1", "a")]
    new_target = facts[fact_key("git-ref-target", "repo-1", "main", "direct", "sha1", "b")]
    side = facts[fact_key("git-ref-exists", "repo-1", "side")]

    assert main["intervals"][0]["first_observed_at"] == timestamp(1)
    assert main["intervals"][0]["last_confirmed_at"] == timestamp(3)
    assert main["intervals"][0]["invalidated_at"] == timestamp(4)
    assert main["intervals"][1]["prior_boundary"] == {
        "state": "tombstone",
        "origin": timestamp(4),
    }
    assert old_target["intervals"][0]["last_confirmed_at"] == timestamp(2)
    assert old_target["intervals"][0]["invalidated_at"] == timestamp(3)
    assert len(new_target["intervals"]) == 2
    assert side["intervals"][0]["invalidated_at"] == timestamp(3)
    assert main["fact_type"] != old_target["fact_type"]
    assert index == TemporalIndexBuilder().build(reversed(snapshots), store_id=STORE)


def test_never_observed_is_explicit_negative_infinity():
    index = TemporalIndexBuilder().build([], store_id=STORE)
    key = fact_key("git-ref-exists", "repo-1", "missing")
    assert fact_state(index, key) == {
        "state": "never_observed",
        "origin": "negative_infinity",
        "fact_key": key,
    }
    with pytest.raises(ContractError):
        fact_key("", "repo-1")
    with pytest.raises(ContractError):
        fact_key("kind", "")
    assert "%7B" in fact_key("kind", "repo-1", {"b": 2, "a": 1})


def test_partial_path_evidence_reconfirms_positive_without_tombstones():
    first = [
        {"status": "modified", "path": "a.txt"},
        {"status": "deleted", "path": "b.txt"},
    ]
    snapshots = [
        snapshot(1, [repository(1, entries=first)]),
        snapshot(
            2,
            [
                repository(
                    2,
                    entries=[{"status": "modified", "path": "a.txt"}],
                    entries_state="partial",
                )
            ],
        ),
        snapshot(3, [repository(3, entries=[], entries_state="partial")]),
        snapshot(4, [repository(4, entries=[{"status": "modified", "path": "a.txt"}])]),
    ]
    index = TemporalIndexBuilder().build(snapshots)
    facts = facts_by_key(index)
    a_key = fact_key("working-copy-path", "repo-1", "repo-1:default", "a.txt", "modified", "")
    b_key = fact_key("working-copy-path", "repo-1", "repo-1:default", "b.txt", "deleted", "")
    assert facts[a_key]["intervals"][0]["last_confirmed_at"] == timestamp(4)
    assert facts[b_key]["intervals"][0]["invalidated_at"] == timestamp(4)
    component = components_by_key(index)["repo-1:path_evidence/repo-1:default"]
    assert component["last_attempted_at"]["at"] == timestamp(4)
    assert component["complete_as_of"]["at"] == timestamp(4)
    assert component["freshness"] if "freshness" in component else True


def test_component_partial_attempt_does_not_advance_complete_clock():
    index = TemporalIndexBuilder().build(
        [
            snapshot(1, [repository(1, refs=[ref("main", "a")])]),
            snapshot(2, [repository(2, refs=[ref("main", "a")], ref_state="partial")]),
        ]
    )
    component = components_by_key(index)["repo-1:git_refs"]
    assert component["last_outcome"] == "partial"
    assert component["last_attempted_at"]["at"] == timestamp(2)
    assert component["complete_as_of"]["at"] == timestamp(1)
    assert component["last_attempted_at"]["time_precision"] == "component"


def test_workspace_bookmark_head_change_and_parent_vocabularies_are_independent():
    graph = {
        "changes": [
            {
                "change_id": "change-head",
                "versions": [
                    {
                        "object_id": {"algorithm": "jj", "value": "version"},
                        "parents": [
                            {
                                "change_id": "parent-change",
                                "object_id": {"algorithm": "jj", "value": "parent-version"},
                            }
                        ],
                    }
                ],
            }
        ],
        "visible_heads": [
            {"object_id": {"algorithm": "jj", "value": "version"}, "change_id": "change-head"}
        ],
        "outcome": outcome("complete", 1),
    }
    bookmark = {
        "name": "topic",
        "remote": "origin",
        "targets": [{"algorithm": "jj", "value": "version"}],
        "added_targets": [{"algorithm": "jj", "value": "other-version"}],
    }
    index = TemporalIndexBuilder().build(
        [
            snapshot(
                1,
                [
                    repository(
                        1,
                        mode="jj",
                        bookmarks=[bookmark],
                        graph=graph,
                        jj_history_state="complete",
                    )
                ],
            )
        ]
    )
    types = {item["fact_type"] for item in index["facts"]}
    assert {
        "repository-exists",
        "workspace-exists",
        "workspace-target",
        "working-copy-state",
        "jj-bookmark-exists",
        "jj-bookmark-target",
        "jj-visible-head",
        "jj-change-exists",
        "jj-change-version",
        "jj-change-parent",
        "native-object-exists",
    } <= types
    facts = facts_by_key(index)
    entity = facts[fact_key("jj-bookmark-exists", "repo-1", "topic", "origin")]
    edge = facts[fact_key("jj-bookmark-target", "repo-1", "topic", "origin", "jj", "version")]
    assert entity["slot_key"] != edge["slot_key"]
    refresh = components_by_key(index)["repo-1:working_copy_refresh/repo-1:default"]
    assert refresh["last_outcome"] == "performed"
    assert refresh["complete_as_of"]["at"] == timestamp(1)
    assert refresh["freshness"] == "current"


def test_complete_scan_tombstones_missing_repository_when_continuity_is_stable():
    index = TemporalIndexBuilder().build([snapshot(1, [repository(1)]), snapshot(2, [])])
    key = fact_key("repository-exists", "repo-1")
    assert fact_state(index, key)["state"] == "inactive"
    assert fact_state(index, key)["origin"] == timestamp(2)


def test_repository_continuity_loss_prevents_cross_boundary_tombstones():
    index = TemporalIndexBuilder().build(
        [
            snapshot(1, [repository(1, repository_key="old")]),
            snapshot(2, [repository(2, repository_key="new")]),
        ]
    )
    old_key = fact_key("repository-exists", "old")
    new_key = fact_key("repository-exists", "new")
    facts = facts_by_key(index)
    assert facts[old_key]["intervals"][0]["invalidated_at"] is None
    assert fact_state(index, new_key)["state"] == "active"
    assert index["continuity_boundaries"] == [
        {
            "snapshot_id": "snapshot-2",
            "scope": "/scope",
            "path": "/scope/repo",
            "before_repository_key": "old",
            "after_repository_key": "new",
        }
    ]


def test_native_objects_and_parent_edges_are_derived_without_rewriting_corpus():
    objects = {}
    for number in range(34_819):
        value = f"{number:040x}"
        objects[f"repo-1:commit:sha1:{value}"] = {
            "repository_key": "repo-1",
            "kind": "commit",
            "object_id": {"algorithm": "sha1", "value": value},
            "parents": [],
        }
    child = f"{34_818:040x}"
    parent = f"{34_817:040x}"
    objects[f"repo-1:commit:sha1:{child}"]["parents"] = [
        None,
        {"algorithm": "sha1", "value": parent},
    ]
    original = copy.deepcopy(objects)
    index = TemporalIndexBuilder().build(
        [snapshot(1, [repository(1, roots=[{"algorithm": "sha1", "value": child}])])],
        objects=objects,
    )
    facts = facts_by_key(index)
    assert len(objects) == 34_819
    assert all("first_observed" not in item for item in objects.values())
    assert objects == original
    assert fact_key("native-object-exists", "repo-1", "sha1", child) in facts
    parent_key = fact_key("native-parent-edge", "repo-1", "sha1", child, "sha1", parent)
    assert facts[parent_key]["absence_authorized"] is False


def test_fact_state_reports_inactive_interval():
    index = TemporalIndexBuilder().build(
        [
            snapshot(1, [repository(1, refs=[ref("main", "a")])]),
            snapshot(2, [repository(2, refs=[])]),
        ]
    )
    state = fact_state(index, fact_key("git-ref-exists", "repo-1", "main"))
    assert state["state"] == "inactive"
    assert state["origin"] == timestamp(2)
    state["interval"]["episode"] = 99
    assert facts_by_key(index)[state["fact_key"]]["intervals"][0]["episode"] == 1


def v1_masked_jj(generation):
    error = CollectionError("command", "jj.history", "failed")
    repository_value = {
        "repository_key": "repo-1",
        "mode": "colocated",
        "locations": [{"path": "/scope/repo"}],
        "collection": {
            "identity": {"state": "complete", "errors": []},
            "workspaces": {"state": "complete", "errors": []},
            "refs": {"state": "complete", "errors": []},
            "history": {"state": "complete", "errors": []},
        },
        "workspaces": [],
        "refs": [],
        "bookmarks": [],
        "change_graph": {
            "changes": [],
            "visible_heads": [],
            "outcome": {"state": "error", "errors": [error.to_dict()]},
        },
        "publication_hints": {"outcomes": {"jj_bookmarks": {"state": "complete", "errors": []}}},
        "roots": [],
    }
    document = SnapshotEnvelope(
        f"snapshot-{generation}",
        timestamp(generation),
        {},
        HistoryStore(STORE, generation, writer_id="writer"),
        {"root": "/scope", "outcome": {"state": "complete", "errors": []}},
        (repository_value,),
    )
    return {"generation": generation, "manifest": document.to_dict()}


def test_v1_masked_jj_error_does_not_authorize_graph_tombstone():
    graph = {
        "changes": [
            {
                "change_id": "change",
                "versions": [
                    {
                        "object_id": {"algorithm": "jj", "value": "version"},
                        "parents": [],
                    }
                ],
            }
        ],
        "visible_heads": [],
        "outcome": outcome("complete", 1),
    }
    first = snapshot(
        1,
        [
            repository(
                1,
                mode="colocated",
                graph=graph,
                jj_history_state="complete",
            )
        ],
    )
    index = TemporalIndexBuilder().build([first, v1_masked_jj(2)])
    key = fact_key("jj-change-exists", "repo-1", "change")
    assert fact_state(index, key)["state"] == "active"
    component = components_by_key(index)["repo-1:jj_history"]
    assert component["last_outcome"] == "error"
    assert component["last_attempted_at"]["at"] == timestamp(2)
    assert component["last_attempted_at"]["time_precision"] == "snapshot"
    assert component["complete_as_of"]["at"] == timestamp(1)


def test_builder_rejects_malformed_inputs_and_skips_bare_index_entries():
    assert (
        TemporalIndexBuilder().build([{"snapshot_id": "bare"}, {"manifest": None}])["facts"] == []
    )
    with pytest.raises(ContractError):
        TemporalIndexBuilder().build(["bad"])
    with pytest.raises(ContractError):
        TemporalIndexBuilder().build(
            [{"generation": "one", "manifest": snapshot(1, [])["manifest"]}]
        )

    other = snapshot(2, [])["manifest"]
    other["history_store"]["store_id"] = "other"
    with pytest.raises(ContractError):
        TemporalIndexBuilder().build([snapshot(1, []), {"generation": 2, "manifest": other}])
    with pytest.raises(ContractError):
        TemporalIndexBuilder().build([snapshot(1, [])], store_id="other")


def test_index_is_canonical_json():
    index = TemporalIndexBuilder().build([snapshot(1, [repository(1)])])
    assert json.dumps(index, sort_keys=True, separators=(",", ":")) == json.dumps(
        index, sort_keys=True, separators=(",", ":")
    )
    direct = TemporalIndexBuilder().build([snapshot(1, [])["manifest"]])
    assert direct["source_generation"] == 1


def test_defensive_extraction_ignores_malformed_optional_presentation():
    complete = {"state": "complete", "attempted_at": timestamp(1), "errors": []}
    repository_value = {
        "repository_key": "repo-1",
        "mode": "git",
        "components": {},
        "workspaces": [
            "bad",
            {
                "workspace_key": "head",
                "head": "ABC",
                "working_copy": {
                    "recorded_state": "unknown",
                    "outcome": complete,
                    "refresh": None,
                    "freshness": "unknown",
                    "entries_outcome": complete,
                    "entries": [None, {"path": 3}],
                },
            },
            {
                "workspace_key": "empty",
                "current": {},
                "working_copy": {
                    "recorded_state": "unreadable",
                    "outcome": complete,
                    "refresh": {},
                    "freshness": "unknown",
                    "entries_outcome": complete,
                    "entries": [],
                },
            },
        ],
        "facts": {
            "refs": [
                None,
                {"name": 3},
                {"name": "main", "object_id": {"algorithm": 3, "value": "bad"}},
            ],
            "bookmarks": [
                None,
                {"name": 3},
                {"name": "topic", "targets": [None, {"algorithm": "jj", "value": ""}]},
            ],
            "change_graph": {
                "visible_heads": [None, {"object_id": {}}],
                "changes": [
                    None,
                    {"change_id": 3},
                    {
                        "change_id": "change",
                        "versions": [
                            None,
                            {},
                            {
                                "object_id": {"algorithm": "jj", "value": "version"},
                                "parents": [None, {}, {"change_id": "parent"}],
                            },
                        ],
                    },
                ],
            },
            "roots": [None, {"algorithm": 3, "value": "bad"}],
            "workspaces": [
                None,
                {
                    "head": "ABC",
                    "parents": [None, {"algorithm": "sha1", "value": "parent"}],
                },
                {"current": {}},
            ],
        },
    }
    observations = temporal_module._repository_observations(repository_value, "snapshot", {})
    assert any(item.component == "git_worktrees" for item in observations)
    assert temporal_module._identifier({"algorithm": "sha1", "value": ""}) is None
    assert temporal_module._outcome(None) == ("unknown", None, "unknown", ())


def test_missing_locations_and_not_requested_scan_do_not_fabricate_time():
    value = repository(1)
    value.pop("locations")
    document = snapshot(1, [value], scan_state="not_requested")
    index = TemporalIndexBuilder().build([document])
    component = components_by_key(index)["scan:%2Fscope:repository_identity"]
    assert component["last_attempted_at"] == {"state": "never_observed"}
