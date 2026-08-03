from vcs_tree.pulse_render import render, render_audit, render_json, render_summary


def document(baseline=False):
    return {
        "scope": {"root": "/workspace"},
        "outcome": {"state": "partial"},
        "comparison": {
            "state": "baseline_created" if baseline else "selected",
            "source_generation": 1,
        },
        "target_snapshot": {"generation": 2},
        "repositories": [
            {
                "path": "project",
                "mode": "colocated",
                "events": [
                    {"event": "change_versions_changed", "details": {"state": "rewritten"}},
                    {"event": "comparison_incomplete", "details": {}},
                ],
                "task_path_events": [{"event": "task_path_added", "new_path": "tasks/closed/x.md"}],
            },
            {"path": "quiet", "mode": "git", "events": [], "task_path_events": []},
        ],
        "warnings": [{"warning_key": "k", "lifecycle": "new"}],
        "summary": {
            "no_op_repositories": 1,
            "new_warnings": 1,
            "persistent_warnings": 2,
            "recovered_warnings": 3,
        },
    }


def test_summary_is_signal_first_and_baseline_is_explicit():
    summary = render_summary(document())
    assert "change_versions_changed (rewritten)" in summary
    assert "comparison_incomplete" not in summary
    assert "task path: task_path_added" in summary
    assert "1 repositories with no observed movement" in summary
    assert "baseline generation" in render_summary(document(True))


def test_audit_and_json_are_deterministic_and_dispatchable():
    value = document()
    assert render_json(value) == render(value, "json")
    assert '"change_versions_changed"' in render_audit(value)
    assert render(value, "audit").startswith("pulse ")
    assert render(value, "summary") == render_summary(value)


def test_renderers_cover_empty_detail_noop_and_warning_paths():
    value = document()
    value["repositories"][0]["events"].append({"event": "opaque", "details": "raw"})
    value["summary"]["no_op_repositories"] = 0
    value["warnings"] = []
    assert "opaque" in render_summary(value)
    assert "warnings:" in render_audit(value)
