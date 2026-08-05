"""Evidence-preserving, three-valued evaluation of mechanical history queries."""

from __future__ import annotations

import json
import operator
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from .models import ContractError
from .predicate_models import HistoryQuery, PredicateNode
from .temporal import TEMPORAL_SCHEMA, TEMPORAL_SCHEMA_VERSION

RESULT_SCHEMA = "vcs-tree.history-query-result"
RESULT_SCHEMA_VERSION = 1

_DIRECT_COMPONENTS = {
    "git-ref-exists": ("git_refs",),
    "git-ref-target": ("git_refs",),
    "jj-bookmark-exists": ("jj_bookmarks",),
    "jj-bookmark-target": ("jj_bookmarks",),
    "jj-visible-head": ("jj_visible_heads",),
    "native-object-exists": ("git_history", "jj_history"),
    "native-parent-edge": ("git_history", "jj_history"),
    "jj-change-exists": ("jj_history",),
    "jj-change-version": ("jj_history",),
    "jj-change-parent": ("jj_history",),
    "workspace-exists": ("git_worktrees", "jj_workspaces"),
    "workspace-target": ("git_worktrees", "jj_workspaces"),
}
_RELATION_FUNCTIONS = {
    "eq": operator.eq,
    "ne": operator.ne,
    "lt": operator.lt,
    "lte": operator.le,
    "gt": operator.gt,
    "gte": operator.ge,
}
_NO_ABSENCE_FACTS = frozenset({"native-object-exists", "native-parent-edge"})


def _copy(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True))


def _timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{name} must be an RFC 3339 timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        result = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ContractError(f"{name} must be an RFC 3339 timestamp") from exc
    if result.tzinfo is None:
        raise ContractError(f"{name} must include a timezone")
    return result


def _relation(left: Any, relation: str, right: Any) -> bool:
    return _RELATION_FUNCTIONS[relation](left, right)


def _attributes_match(actual: Any, selected: Any) -> bool:
    if isinstance(selected, Mapping):
        return isinstance(actual, Mapping) and all(
            key in actual and _attributes_match(actual[key], value)
            for key, value in selected.items()
        )
    if isinstance(selected, list):
        return isinstance(actual, list) and actual == selected
    return actual == selected


def _component_names(fact_type: str, attributes: Mapping[str, Any]) -> tuple[str, ...]:
    workspace_key = attributes.get("workspace_key")
    if fact_type == "working-copy-state" and isinstance(workspace_key, str):
        return (f"working_copy/{workspace_key}",)
    if fact_type == "working-copy-path" and isinstance(workspace_key, str):
        return (f"path_evidence/{workspace_key}",)
    if fact_type == "repository-exists":
        return ("repository_identity",)
    return _DIRECT_COMPONENTS.get(fact_type, ())


class PredicateEvaluator:
    """Evaluate a query without consulting a clock or mutating its inputs."""

    def evaluate(
        self,
        query: HistoryQuery | Mapping[str, Any],
        index: Mapping[str, Any],
        *,
        evaluated_at: str,
    ) -> dict[str, Any]:
        document = query if isinstance(query, HistoryQuery) else HistoryQuery.from_dict(query)
        moment = _timestamp(evaluated_at, "evaluated_at")
        self._validate_index(index)
        repositories = self._repositories(document, index)
        results = [
            {
                "repository_key": repository_key,
                **self._evaluate_node(document.where, repository_key, index, moment),
            }
            for repository_key in repositories
        ]
        return {
            "schema": RESULT_SCHEMA,
            "schema_version": RESULT_SCHEMA_VERSION,
            "evaluated_at": evaluated_at,
            "query": document.to_dict(),
            "temporal_index": {
                "schema": index["schema"],
                "schema_version": index["schema_version"],
                "store_id": index.get("store_id"),
                "source_generation": index.get("source_generation", 0),
                "source_snapshots": _copy(index.get("source_snapshots", [])),
                "continuity_boundaries": _copy(index.get("continuity_boundaries", [])),
            },
            "results": results,
        }

    @staticmethod
    def _validate_index(index: Mapping[str, Any]) -> None:
        if not isinstance(index, Mapping):
            raise ContractError("temporal index must be an object")
        if index.get("schema") != TEMPORAL_SCHEMA:
            raise ContractError("unsupported temporal index schema")
        if index.get("schema_version") != TEMPORAL_SCHEMA_VERSION:
            raise ContractError("unsupported temporal index schema version")
        if not isinstance(index.get("facts"), list) or not isinstance(
            index.get("components"), list
        ):
            raise ContractError("temporal index facts and components must be arrays")

    @staticmethod
    def _repositories(query: HistoryQuery, index: Mapping[str, Any]) -> tuple[str, ...]:
        if query.repository_keys is not None:
            return query.repository_keys
        keys = {
            str(item["repository_key"])
            for collection in (index["facts"], index["components"])
            for item in collection
            if isinstance(item, Mapping) and isinstance(item.get("repository_key"), str)
        }
        return tuple(sorted(keys))

    def _evaluate_node(
        self,
        node: PredicateNode,
        repository_key: str,
        index: Mapping[str, Any],
        moment: datetime,
    ) -> dict[str, Any]:
        if node.kind in {"all", "any"}:
            children = [
                self._evaluate_node(child, repository_key, index, moment) for child in node.children
            ]
            outcomes = [child["outcome"] for child in children]
            if node.kind == "all":
                outcome = (
                    "false"
                    if "false" in outcomes
                    else "indeterminate"
                    if "indeterminate" in outcomes
                    else "true"
                )
            else:
                outcome = (
                    "true"
                    if "true" in outcomes
                    else "indeterminate"
                    if "indeterminate" in outcomes
                    else "false"
                )
            return {"predicate": node.to_dict(), "outcome": outcome, "children": children}
        if node.kind == "not":
            child = self._evaluate_node(node.children[0], repository_key, index, moment)
            outcome = {"true": "false", "false": "true", "indeterminate": "indeterminate"}[
                child["outcome"]
            ]
            return {"predicate": node.to_dict(), "outcome": outcome, "children": [child]}
        if node.kind == "component":
            return self._component(node, repository_key, index)
        if node.kind == "elapsed":
            return self._elapsed(node, repository_key, index, moment)
        return self._fact(node, repository_key, index)

    @staticmethod
    def _selected_facts(
        node: PredicateNode, repository_key: str, index: Mapping[str, Any]
    ) -> list[Mapping[str, Any]]:
        assert node.value is not None
        selector = node.value["selector"]
        return sorted(
            (
                item
                for item in index["facts"]
                if isinstance(item, Mapping)
                and item.get("repository_key") == repository_key
                and item.get("fact_type") == selector.fact_type
                and _attributes_match(item.get("attributes", {}), selector.attributes)
            ),
            key=lambda item: str(item.get("fact_key", "")),
        )

    @staticmethod
    def _selected_components(
        node: PredicateNode,
        repository_key: str,
        index: Mapping[str, Any],
        facts: list[Mapping[str, Any]],
    ) -> list[Mapping[str, Any]]:
        assert node.value is not None
        selector = node.value["selector"]
        names = set(_component_names(selector.fact_type, selector.attributes))
        if selector.fact_type == "working-copy-path":
            workspace_key = selector.attributes.get("workspace_key")
            if isinstance(workspace_key, str):
                names.add(f"working_copy/{workspace_key}")
        names.update(
            str(item["component"]) for item in facts if isinstance(item.get("component"), str)
        )
        return sorted(
            (
                item
                for item in index["components"]
                if isinstance(item, Mapping)
                and (
                    item.get("repository_key") == repository_key
                    or (
                        selector.fact_type == "repository-exists"
                        and item.get("repository_key") is None
                    )
                )
                and item.get("component") in names
            ),
            key=lambda item: str(item.get("component_key", "")),
        )

    @staticmethod
    def _fact_status(record: Mapping[str, Any]) -> str:
        intervals = record.get("intervals")
        if not isinstance(intervals, list) or not intervals:
            return "never_observed"
        return "active" if intervals[-1].get("invalidated_at") is None else "inactive"

    @staticmethod
    def _component_complete(component: Mapping[str, Any]) -> bool:
        clock = component.get("complete_as_of")
        freshness = component.get("freshness")
        return (
            isinstance(clock, Mapping)
            and clock.get("state") == "observed"
            and freshness not in {"recorded_maybe_stale", "unknown"}
        )

    @staticmethod
    def _continuity_uncertain(repository_key: str, index: Mapping[str, Any]) -> bool:
        return any(
            isinstance(item, Mapping)
            and repository_key
            in {item.get("before_repository_key"), item.get("after_repository_key")}
            for item in index.get("continuity_boundaries", ())
        )

    def _evidence(
        self,
        facts: list[Mapping[str, Any]],
        components: list[Mapping[str, Any]],
        index: Mapping[str, Any],
        repository_key: str,
    ) -> dict[str, Any]:
        boundaries = sorted(
            (
                item
                for item in index.get("continuity_boundaries", ())
                if isinstance(item, Mapping)
                and repository_key
                in {item.get("before_repository_key"), item.get("after_repository_key")}
            ),
            key=lambda item: (
                str(item.get("snapshot_id", "")),
                str(item.get("scope", "")),
                str(item.get("path", "")),
            ),
        )
        return {
            "facts": _copy(facts),
            "components": _copy(components),
            "source_snapshots": sorted(
                {
                    evidence["snapshot_id"]
                    for fact in facts
                    for interval in fact.get("intervals", ())
                    for evidence in (
                        interval.get("opened_by"),
                        interval.get("last_confirmed_by"),
                        interval.get("invalidated_by"),
                    )
                    if isinstance(evidence, Mapping)
                    and isinstance(evidence.get("snapshot_id"), str)
                }
            ),
            "completeness": [
                {
                    "component_key": item.get("component_key"),
                    "last_outcome": item.get("last_outcome"),
                    "complete_as_of": _copy(item.get("complete_as_of")),
                    "freshness": item.get("freshness"),
                }
                for item in components
            ],
            "continuity_boundaries": _copy(boundaries),
        }

    def _fact(
        self, node: PredicateNode, repository_key: str, index: Mapping[str, Any]
    ) -> dict[str, Any]:
        assert node.value is not None
        facts = self._selected_facts(node, repository_key, index)
        components = self._selected_components(node, repository_key, index, facts)
        states = [self._fact_status(item) for item in facts]
        requested = node.value["state"]
        if requested == "ever_observed":
            positive = any(state != "never_observed" for state in states)
        else:
            positive = requested in states
        if positive:
            outcome = "true"
        elif facts and requested in {"active", "inactive"}:
            outcome = "false"
        elif (
            components
            and all(self._component_complete(item) for item in components)
            and node.value["selector"].fact_type not in _NO_ABSENCE_FACTS
            and not self._continuity_uncertain(repository_key, index)
        ):
            outcome = "false"
        else:
            outcome = "indeterminate"
        return {
            "predicate": node.to_dict(),
            "outcome": outcome,
            "evidence": self._evidence(facts, components, index, repository_key),
        }

    def _elapsed(
        self,
        node: PredicateNode,
        repository_key: str,
        index: Mapping[str, Any],
        moment: datetime,
    ) -> dict[str, Any]:
        assert node.value is not None
        facts = self._selected_facts(node, repository_key, index)
        components = self._selected_components(node, repository_key, index, facts)
        clocks = [self._clock(item, node.value["clock"], moment) for item in facts]
        complete = (
            bool(components)
            and all(self._component_complete(item) for item in components)
            and node.value["selector"].fact_type not in _NO_ABSENCE_FACTS
            and not self._continuity_uncertain(repository_key, index)
        )
        if not clocks and complete:
            clocks = [
                {
                    "origin": {"state": "never_observed", "value": "negative_infinity"},
                    "elapsed": {"state": "positive_infinity"},
                }
            ]
        supported = [item for item in clocks if item["elapsed"]["state"] != "indeterminate"]
        matches = [
            self._compare_elapsed(item, node.value["relation"], node.value["seconds"])
            for item in supported
        ]
        if any(matches):
            outcome = "true"
        elif supported and len(supported) == len(clocks):
            outcome = "false"
        else:
            outcome = "indeterminate"
        evidence = self._evidence(facts, components, index, repository_key)
        evidence["clock"] = {
            "name": node.value["clock"],
            "evaluated_at": moment.isoformat(),
            "observations": clocks,
        }
        return {"predicate": node.to_dict(), "outcome": outcome, "evidence": evidence}

    @staticmethod
    def _clock(record: Mapping[str, Any], name: str, moment: datetime) -> dict[str, Any]:
        intervals = record.get("intervals", ())
        if not intervals:
            return {
                "fact_key": record.get("fact_key"),
                "origin": {"state": "never_observed", "value": "negative_infinity"},
                "elapsed": {"state": "positive_infinity"},
            }
        last = intervals[-1]
        if name == "current_interval_started":
            origin = last.get("first_observed_at")
        elif name == "last_confirmed":
            origin = last.get("last_confirmed_at")
        elif name == "last_invalidated":
            origin = next(
                (
                    item.get("invalidated_at")
                    for item in reversed(intervals)
                    if item.get("invalidated_at") is not None
                ),
                None,
            )
        else:
            transitions = [
                value
                for item in intervals
                for value in (item.get("first_observed_at"), item.get("invalidated_at"))
                if value is not None
            ]
            origin = transitions[-1] if transitions else None
        if origin is None:
            return {
                "fact_key": record.get("fact_key"),
                "origin": {"state": "never_observed", "value": "negative_infinity"},
                "elapsed": {"state": "positive_infinity"},
            }
        try:
            elapsed = (moment - _timestamp(origin, "clock origin")).total_seconds()
        except (ContractError, TypeError):
            return {
                "fact_key": record.get("fact_key"),
                "origin": {"state": "unsupported", "value": origin},
                "elapsed": {"state": "indeterminate"},
            }
        if elapsed < 0:
            return {
                "fact_key": record.get("fact_key"),
                "origin": {"state": "observed", "value": origin},
                "elapsed": {"state": "indeterminate"},
            }
        return {
            "fact_key": record.get("fact_key"),
            "origin": {"state": "observed", "value": origin},
            "elapsed": {"state": "finite", "seconds": elapsed},
        }

    @staticmethod
    def _compare_elapsed(clock: Mapping[str, Any], relation: str, seconds: float) -> bool:
        elapsed = clock["elapsed"]
        if elapsed["state"] == "positive_infinity":
            return relation in {"ne", "gt", "gte"}
        return _relation(elapsed["seconds"], relation, seconds)

    def _component(
        self, node: PredicateNode, repository_key: str, index: Mapping[str, Any]
    ) -> dict[str, Any]:
        assert node.value is not None
        key = f"{repository_key}:{node.value['name']}"
        components = sorted(
            (
                item
                for item in index["components"]
                if isinstance(item, Mapping)
                and item.get("repository_key") == repository_key
                and item.get("component_key") == key
            ),
            key=lambda item: str(item.get("component_key", "")),
        )
        outcome = "indeterminate"
        if components:
            component = components[0]
            field = node.value["field"]
            actual = component.get("last_outcome" if field == "outcome" else field)
            if field == "complete_as_of":
                if isinstance(actual, Mapping) and actual.get("state") == "observed":
                    try:
                        left = _timestamp(actual.get("at"), "complete_as_of")
                        right = _timestamp(node.value["value"], "component.value")
                    except ContractError:
                        outcome = "indeterminate"
                    else:
                        outcome = (
                            "true" if _relation(left, node.value["relation"], right) else "false"
                        )
            elif isinstance(actual, str):
                outcome = (
                    "true"
                    if _relation(actual, node.value["relation"], node.value["value"])
                    else "false"
                )
        return {
            "predicate": node.to_dict(),
            "outcome": outcome,
            "evidence": self._evidence([], components, index, repository_key),
        }


__all__ = [
    "RESULT_SCHEMA",
    "RESULT_SCHEMA_VERSION",
    "PredicateEvaluator",
]
