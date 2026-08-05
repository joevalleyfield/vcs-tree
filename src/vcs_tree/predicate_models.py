"""Typed contract for deterministic mechanical history queries."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .models import ContractError

QUERY_SCHEMA = "vcs-tree.history-query"
QUERY_SCHEMA_VERSION = 1

FACT_TYPES = frozenset(
    {
        "repository-exists",
        "workspace-exists",
        "workspace-target",
        "working-copy-state",
        "working-copy-path",
        "git-ref-exists",
        "git-ref-target",
        "jj-bookmark-exists",
        "jj-bookmark-target",
        "jj-visible-head",
        "native-object-exists",
        "native-parent-edge",
        "jj-change-exists",
        "jj-change-version",
        "jj-change-parent",
    }
)
FACT_STATES = frozenset({"active", "inactive", "ever_observed"})
ELAPSED_CLOCKS = frozenset(
    {"current_interval_started", "last_confirmed", "last_invalidated", "last_transition"}
)
RELATIONS = frozenset({"eq", "ne", "lt", "lte", "gt", "gte"})
COMPONENT_FIELDS = frozenset({"outcome", "complete_as_of", "freshness"})


def _object(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{name} must be an object")
    return value


def _exact_fields(value: Mapping[str, Any], required: set[str], name: str) -> None:
    missing = required - value.keys()
    extra = value.keys() - required
    if missing:
        raise ContractError(f"{name} missing required field: {sorted(missing)[0]}")
    if extra:
        raise ContractError(f"{name} has unknown field: {sorted(extra)[0]}")


def _choice(value: Any, choices: frozenset[str], name: str) -> str:
    if not isinstance(value, str) or value not in choices:
        raise ContractError(f"invalid {name}: {value!r}")
    return value


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{name} must be a non-empty string")
    return value


def _json_copy(value: Any, name: str) -> Any:
    try:
        return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{name} must contain JSON values") from exc


def _timestamp(value: Any, name: str) -> str:
    text = _string(value, name)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ContractError(f"{name} must be an RFC 3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"{name} must include a timezone")
    return text


@dataclass(frozen=True)
class FactSelector:
    fact_type: str
    attributes: Mapping[str, Any]

    @classmethod
    def from_dict(cls, value: Any, name: str = "fact selector") -> FactSelector:
        obj = _object(value, name)
        _exact_fields(obj, {"type", "attributes"}, name)
        fact_type = _choice(obj["type"], FACT_TYPES, f"{name}.type")
        attributes = _object(obj["attributes"], f"{name}.attributes")
        return cls(fact_type, _json_copy(attributes, f"{name}.attributes"))

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.fact_type, "attributes": _json_copy(self.attributes, "attributes")}


@dataclass(frozen=True)
class PredicateNode:
    kind: str
    value: Mapping[str, Any] | None = None
    children: tuple[PredicateNode, ...] = ()

    @classmethod
    def from_dict(cls, value: Any, name: str = "where") -> PredicateNode:
        obj = _object(value, name)
        if len(obj) != 1:
            raise ContractError(f"{name} must contain exactly one predicate operator")
        kind, raw = next(iter(obj.items()))
        if kind in {"all", "any"}:
            if not isinstance(raw, list) or not raw:
                raise ContractError(f"{name}.{kind} must be a non-empty array")
            return cls(
                kind,
                children=tuple(
                    cls.from_dict(item, f"{name}.{kind}[{position}]")
                    for position, item in enumerate(raw)
                ),
            )
        if kind == "not":
            return cls(kind, children=(cls.from_dict(raw, f"{name}.not"),))
        if kind == "fact":
            leaf = _object(raw, f"{name}.fact")
            _exact_fields(leaf, {"type", "attributes", "state"}, f"{name}.fact")
            selector = FactSelector.from_dict(
                {"type": leaf["type"], "attributes": leaf["attributes"]}, f"{name}.fact"
            )
            return cls(
                kind,
                {
                    "selector": selector,
                    "state": _choice(leaf["state"], FACT_STATES, f"{name}.fact.state"),
                },
            )
        if kind == "elapsed":
            leaf = _object(raw, f"{name}.elapsed")
            _exact_fields(leaf, {"fact", "clock", "relation", "seconds"}, f"{name}.elapsed")
            seconds = leaf["seconds"]
            if (
                isinstance(seconds, bool)
                or not isinstance(seconds, (int, float))
                or not math.isfinite(seconds)
                or seconds < 0
            ):
                raise ContractError(f"{name}.elapsed.seconds must be a finite non-negative number")
            return cls(
                kind,
                {
                    "selector": FactSelector.from_dict(leaf["fact"], f"{name}.elapsed.fact"),
                    "clock": _choice(leaf["clock"], ELAPSED_CLOCKS, f"{name}.elapsed.clock"),
                    "relation": _choice(leaf["relation"], RELATIONS, f"{name}.elapsed.relation"),
                    "seconds": seconds,
                },
            )
        if kind == "component":
            leaf = _object(raw, f"{name}.component")
            _exact_fields(leaf, {"name", "field", "relation", "value"}, f"{name}.component")
            field = _choice(leaf["field"], COMPONENT_FIELDS, f"{name}.component.field")
            relation = _choice(leaf["relation"], RELATIONS, f"{name}.component.relation")
            compared = leaf["value"]
            if not isinstance(compared, str) or not compared:
                raise ContractError(f"{name}.component.value must be a non-empty string")
            if field != "complete_as_of" and relation not in {"eq", "ne"}:
                raise ContractError(f"{name}.component {field} only supports eq and ne")
            if field == "complete_as_of":
                compared = _timestamp(compared, f"{name}.component.value")
            return cls(
                kind,
                {
                    "name": _string(leaf["name"], f"{name}.component.name"),
                    "field": field,
                    "relation": relation,
                    "value": compared,
                },
            )
        raise ContractError(f"unsupported predicate operator: {kind!r}")

    def to_dict(self) -> dict[str, Any]:
        if self.kind in {"all", "any"}:
            return {self.kind: [child.to_dict() for child in self.children]}
        if self.kind == "not":
            return {"not": self.children[0].to_dict()}
        assert self.value is not None
        if self.kind == "fact":
            selector = self.value["selector"]
            assert isinstance(selector, FactSelector)
            return {"fact": {**selector.to_dict(), "state": self.value["state"]}}
        if self.kind == "elapsed":
            selector = self.value["selector"]
            assert isinstance(selector, FactSelector)
            return {
                "elapsed": {
                    "fact": selector.to_dict(),
                    "clock": self.value["clock"],
                    "relation": self.value["relation"],
                    "seconds": self.value["seconds"],
                }
            }
        return {"component": dict(self.value)}


@dataclass(frozen=True)
class HistoryQuery:
    repository_keys: tuple[str, ...] | None
    where: PredicateNode
    schema: str = QUERY_SCHEMA
    schema_version: int = QUERY_SCHEMA_VERSION

    @classmethod
    def from_dict(cls, value: Any) -> HistoryQuery:
        obj = _object(value, "query")
        _exact_fields(obj, {"schema", "schema_version", "scope", "where"}, "query")
        if obj["schema"] != QUERY_SCHEMA:
            raise ContractError(f"unsupported query schema: {obj['schema']!r}")
        if isinstance(obj["schema_version"], bool) or obj["schema_version"] != QUERY_SCHEMA_VERSION:
            raise ContractError(f"unsupported query schema version: {obj['schema_version']!r}")
        scope = _object(obj["scope"], "query.scope")
        if set(scope) == {"all"}:
            if scope["all"] is not True:
                raise ContractError("query.scope.all must be true")
            keys = None
        elif set(scope) == {"repository_keys"}:
            raw_keys = scope["repository_keys"]
            if not isinstance(raw_keys, list) or not raw_keys:
                raise ContractError("query.scope.repository_keys must be a non-empty array")
            if any(not isinstance(item, str) or not item for item in raw_keys):
                raise ContractError("query.scope.repository_keys entries must be non-empty strings")
            if len(set(raw_keys)) != len(raw_keys):
                raise ContractError("query.scope.repository_keys must not contain duplicates")
            keys = tuple(sorted(raw_keys))
        else:
            raise ContractError("query.scope must contain exactly all or repository_keys")
        return cls(keys, PredicateNode.from_dict(obj["where"]))

    def to_dict(self) -> dict[str, Any]:
        scope = (
            {"all": True}
            if self.repository_keys is None
            else {"repository_keys": list(self.repository_keys)}
        )
        return {
            "schema": self.schema,
            "schema_version": self.schema_version,
            "scope": scope,
            "where": self.where.to_dict(),
        }


__all__ = [
    "COMPONENT_FIELDS",
    "ELAPSED_CLOCKS",
    "FACT_STATES",
    "FACT_TYPES",
    "QUERY_SCHEMA",
    "QUERY_SCHEMA_VERSION",
    "RELATIONS",
    "FactSelector",
    "HistoryQuery",
    "PredicateNode",
]
