"""Deterministic temporal projection of retained repository observations."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from .models import CollectionState, ContractError
from .snapshot_schema import normalize_snapshot, parse_snapshot

TEMPORAL_SCHEMA = "vcs-tree.temporal-facts"
TEMPORAL_SCHEMA_VERSION = 1


def _copy(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True))


def _part(value: Any) -> str:
    if isinstance(value, (dict, list, tuple)):
        value = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return quote(str(value), safe="")


def fact_key(fact_type: str, repository_key: str, *identity: Any) -> str:
    """Build a stable exact-assertion key from canonical identity parts."""
    if not fact_type or not repository_key:
        raise ContractError("fact type and repository key are required")
    return ":".join((fact_type, _part(repository_key), *(_part(item) for item in identity)))


@dataclass(frozen=True)
class AtomicFact:
    fact_key: str
    slot_key: str
    fact_type: str
    repository_key: str
    component: str
    component_key: str
    attributes: Mapping[str, Any]
    absence_authorized: bool = True

    def record(self) -> dict[str, Any]:
        return {
            "fact_key": self.fact_key,
            "slot_key": self.slot_key,
            "fact_type": self.fact_type,
            "repository_key": self.repository_key,
            "component": self.component,
            "component_key": self.component_key,
            "attributes": _copy(self.attributes),
            "absence_authorized": self.absence_authorized,
            "intervals": [],
        }


@dataclass(frozen=True)
class ComponentObservation:
    component_key: str
    repository_key: str | None
    component: str
    state: str
    attempted_at: str | None
    precision: str
    snapshot_id: str
    errors: tuple[Mapping[str, Any], ...]
    facts: tuple[AtomicFact, ...] = ()
    freshness: str | None = None
    absence_authorized: bool = True


def _identifier(value: Any) -> tuple[str, str] | None:
    if not isinstance(value, Mapping):
        return None
    algorithm = value.get("algorithm")
    identifier = value.get("value")
    if not isinstance(algorithm, str) or not isinstance(identifier, str) or not identifier:
        return None
    return algorithm, identifier.lower()


def _fact(
    fact_type: str,
    repository_key: str,
    component: str,
    identity: tuple[Any, ...],
    attributes: Mapping[str, Any],
    *,
    slot_identity: tuple[Any, ...] | None = None,
    absence_authorized: bool = True,
    component_key: str | None = None,
) -> AtomicFact:
    return AtomicFact(
        fact_key(fact_type, repository_key, *identity),
        fact_key(fact_type, repository_key, *(slot_identity or identity)),
        fact_type,
        repository_key,
        component,
        component_key or f"{repository_key}:{component}",
        attributes,
        absence_authorized,
    )


def _outcome(value: Any) -> tuple[str, str | None, str, tuple[Mapping[str, Any], ...]]:
    if not isinstance(value, Mapping):
        return "unknown", None, "unknown", ()
    state = str(value.get("state", "unknown"))
    attempted_at = value.get("attempted_at")
    if not isinstance(attempted_at, str):
        attempted_at = None
    precision = str(value.get("time_precision", "component" if attempted_at else "unknown"))
    errors = value.get("errors", ())
    return (
        state,
        attempted_at,
        precision,
        tuple(item for item in errors if isinstance(item, Mapping)),
    )


def _component_observation(
    repository_key: str,
    component: str,
    outcome: Any,
    snapshot_id: str,
    facts: Iterable[AtomicFact] = (),
    *,
    freshness: str | None = None,
    absence_authorized: bool = True,
) -> ComponentObservation:
    state, attempted_at, precision, errors = _outcome(outcome)
    return ComponentObservation(
        f"{repository_key}:{component}",
        repository_key,
        component,
        state,
        attempted_at,
        precision,
        snapshot_id,
        errors,
        tuple(sorted(facts, key=lambda item: item.fact_key)),
        freshness,
        absence_authorized,
    )


def _workspace_facts(repository: Mapping[str, Any], snapshot_id: str) -> list[ComponentObservation]:
    repository_key = str(repository["repository_key"])
    mode = repository.get("mode")
    topology = "jj_workspaces" if mode in {"jj", "colocated"} else "git_worktrees"
    topology_facts = []
    observations = []
    for workspace in repository.get("workspaces", ()):
        if not isinstance(workspace, Mapping):
            continue
        workspace_key = str(workspace.get("workspace_key", workspace.get("path", "unknown")))
        topology_facts.append(
            _fact(
                "workspace-exists",
                repository_key,
                topology,
                (workspace_key,),
                {"workspace_key": workspace_key},
            )
        )
        working_copy = workspace.get("working_copy")
        working_copy = working_copy if isinstance(working_copy, Mapping) else workspace
        current = workspace.get("current", working_copy.get("current"))
        current = current if isinstance(current, Mapping) else {}
        if not current and isinstance(workspace.get("head"), str):
            current = {
                "object_id": {"algorithm": "sha1", "value": workspace["head"]},
                "change_id": None,
            }
        object_id = _identifier(current.get("object_id"))
        if object_id:
            topology_facts.append(
                _fact(
                    "workspace-target",
                    repository_key,
                    topology,
                    (workspace_key, *object_id, current.get("change_id", "")),
                    {
                        "workspace_key": workspace_key,
                        "target": {"algorithm": object_id[0], "value": object_id[1]},
                        "change_id": current.get("change_id"),
                    },
                    slot_identity=(workspace_key,),
                )
            )
        working_component = f"working_copy/{workspace_key}"
        state = working_copy.get("recorded_state", working_copy.get("state"))
        state_facts = []
        if state in {"clean", "dirty", "conflicted"}:
            state_facts.append(
                _fact(
                    "working-copy-state",
                    repository_key,
                    working_component,
                    (workspace_key, state),
                    {"workspace_key": workspace_key, "state": state},
                    slot_identity=(workspace_key,),
                )
            )
        observations.append(
            _component_observation(
                repository_key,
                working_component,
                working_copy.get("outcome"),
                snapshot_id,
                state_facts,
                freshness=str(working_copy.get("freshness", "unknown")),
            )
        )
        refresh = working_copy.get("refresh")
        refresh = refresh if isinstance(refresh, Mapping) else {}
        refresh_state, attempted_at, precision, errors = _outcome(refresh)
        observations.append(
            ComponentObservation(
                f"{repository_key}:working_copy_refresh/{workspace_key}",
                repository_key,
                f"working_copy_refresh/{workspace_key}",
                refresh_state,
                attempted_at,
                precision,
                snapshot_id,
                errors,
                freshness=str(working_copy.get("freshness", "unknown")),
                absence_authorized=False,
            )
        )
        path_component = f"path_evidence/{workspace_key}"
        path_facts = []
        for entry in working_copy.get("entries", ()):
            if not isinstance(entry, Mapping) or not isinstance(entry.get("path"), str):
                continue
            status = str(entry.get("status", "unknown"))
            path = entry["path"]
            old_path = entry.get("old_path")
            path_facts.append(
                _fact(
                    "working-copy-path",
                    repository_key,
                    path_component,
                    (workspace_key, path, status, old_path or ""),
                    {
                        "workspace_key": workspace_key,
                        "path": path,
                        "status": status,
                        "old_path": old_path,
                    },
                    slot_identity=(workspace_key, path),
                )
            )
        observations.append(
            _component_observation(
                repository_key,
                path_component,
                working_copy.get("entries_outcome"),
                snapshot_id,
                path_facts,
            )
        )
    observations.append(
        _component_observation(
            repository_key,
            topology,
            repository.get("components", {}).get(topology),
            snapshot_id,
            topology_facts,
        )
    )
    return observations


def _git_ref_facts(repository: Mapping[str, Any]) -> list[AtomicFact]:
    repository_key = str(repository["repository_key"])
    raw = repository.get("facts", {})
    hints = raw.get("publication_hints")
    refs = hints.get("git_refs", ()) if isinstance(hints, Mapping) else raw.get("refs", ())
    facts = []
    for ref in refs:
        if not isinstance(ref, Mapping) or not isinstance(ref.get("name"), str):
            continue
        name = ref["name"]
        facts.append(_fact("git-ref-exists", repository_key, "git_refs", (name,), {"name": name}))
        for target_kind, field in (("direct", "object_id"), ("peeled", "peeled_object_id")):
            target = _identifier(ref.get(field))
            if target:
                facts.append(
                    _fact(
                        "git-ref-target",
                        repository_key,
                        "git_refs",
                        (name, target_kind, *target),
                        {
                            "name": name,
                            "target_kind": target_kind,
                            "target": {"algorithm": target[0], "value": target[1]},
                        },
                        slot_identity=(name, target_kind),
                    )
                )
    return facts


def _bookmark_facts(repository: Mapping[str, Any]) -> list[AtomicFact]:
    repository_key = str(repository["repository_key"])
    facts = []
    for bookmark in repository.get("facts", {}).get("bookmarks", ()):
        if not isinstance(bookmark, Mapping) or not isinstance(bookmark.get("name"), str):
            continue
        name = bookmark["name"]
        remote = str(bookmark.get("remote") or "")
        source = (name, remote)
        facts.append(
            _fact(
                "jj-bookmark-exists",
                repository_key,
                "jj_bookmarks",
                source,
                {"name": name, "remote": remote or None},
            )
        )
        targets = [*bookmark.get("targets", ()), *bookmark.get("added_targets", ())]
        for value in targets:
            target = _identifier(value)
            if target:
                facts.append(
                    _fact(
                        "jj-bookmark-target",
                        repository_key,
                        "jj_bookmarks",
                        (*source, *target),
                        {
                            "name": name,
                            "remote": remote or None,
                            "target": {"algorithm": target[0], "value": target[1]},
                        },
                        slot_identity=source,
                    )
                )
    return facts


def _jj_graph_facts(repository: Mapping[str, Any]) -> tuple[list[AtomicFact], list[AtomicFact]]:
    repository_key = str(repository["repository_key"])
    graph = repository.get("facts", {}).get("change_graph")
    graph = graph if isinstance(graph, Mapping) else {}
    head_facts = []
    for head in graph.get("visible_heads", ()):
        target = _identifier(head.get("object_id")) if isinstance(head, Mapping) else None
        if target:
            head_facts.append(
                _fact(
                    "jj-visible-head",
                    repository_key,
                    "jj_visible_heads",
                    target,
                    {"target": {"algorithm": target[0], "value": target[1]}},
                )
            )
    history_facts = []
    for change in graph.get("changes", ()):
        if not isinstance(change, Mapping) or not isinstance(change.get("change_id"), str):
            continue
        change_id = change["change_id"]
        history_facts.append(
            _fact(
                "jj-change-exists",
                repository_key,
                "jj_history",
                (change_id,),
                {"change_id": change_id},
            )
        )
        for version in change.get("versions", ()):
            if not isinstance(version, Mapping):
                continue
            target = _identifier(version.get("object_id"))
            if not target:
                continue
            history_facts.append(
                _fact(
                    "jj-change-version",
                    repository_key,
                    "jj_history",
                    (change_id, *target),
                    {
                        "change_id": change_id,
                        "target": {"algorithm": target[0], "value": target[1]},
                    },
                    slot_identity=(change_id,),
                )
            )
            for parent in version.get("parents", ()):
                if not isinstance(parent, Mapping):
                    continue
                parent_id = parent.get("change_id")
                parent_object = _identifier(parent.get("object_id"))
                if parent_id or parent_object:
                    identity = (
                        change_id,
                        target[0],
                        target[1],
                        parent_id or "",
                        *(parent_object or ("", "")),
                    )
                    history_facts.append(
                        _fact(
                            "jj-change-parent",
                            repository_key,
                            "jj_history",
                            identity,
                            {
                                "change_id": change_id,
                                "version": {"algorithm": target[0], "value": target[1]},
                                "parent_change_id": parent_id,
                                "parent_object_id": (
                                    {
                                        "algorithm": parent_object[0],
                                        "value": parent_object[1],
                                    }
                                    if parent_object
                                    else None
                                ),
                            },
                        )
                    )
    return head_facts, history_facts


def _object_facts(
    repository: Mapping[str, Any], objects: Mapping[str, Mapping[str, Any]]
) -> dict[str, list[AtomicFact]]:
    repository_key = str(repository["repository_key"])
    identifiers = []
    raw = repository.get("facts", {})
    for value in raw.get("roots", ()):
        identifier = _identifier(value)
        if identifier:
            identifiers.append(identifier)
    for workspace in raw.get("workspaces", ()):
        if not isinstance(workspace, Mapping):
            continue
        working_copy = workspace.get("working_copy")
        working_copy = working_copy if isinstance(working_copy, Mapping) else {}
        current = workspace.get("current", working_copy.get("current"))
        current = current if isinstance(current, Mapping) else {}
        if not current and isinstance(workspace.get("head"), str):
            current = {"object_id": {"algorithm": "sha1", "value": workspace["head"]}}
        identifier = _identifier(current.get("object_id"))
        if identifier:
            identifiers.append(identifier)
        for parent in workspace.get("parents", ()):
            identifier = _identifier(parent)
            if identifier:
                identifiers.append(identifier)
    result: dict[str, list[AtomicFact]] = {"git_history": [], "jj_history": []}
    for algorithm, value in sorted(set(identifiers)):
        component = "git_history" if algorithm.startswith("sha") else "jj_history"
        result[component].append(
            _fact(
                "native-object-exists",
                repository_key,
                component,
                (algorithm, value),
                {"object_id": {"algorithm": algorithm, "value": value}},
                absence_authorized=False,
            )
        )
        ledger_key = f"{repository_key}:commit:{algorithm}:{value}"
        record = objects.get(ledger_key)
        if not isinstance(record, Mapping):
            continue
        for parent in record.get("parents", ()):
            parent_id = _identifier(parent)
            if parent_id:
                result[component].append(
                    _fact(
                        "native-parent-edge",
                        repository_key,
                        component,
                        (algorithm, value, *parent_id),
                        {
                            "object_id": {"algorithm": algorithm, "value": value},
                            "parent": {"algorithm": parent_id[0], "value": parent_id[1]},
                        },
                        absence_authorized=False,
                    )
                )
    return result


def _repository_observations(
    repository: Mapping[str, Any], snapshot_id: str, objects: Mapping[str, Mapping[str, Any]]
) -> list[ComponentObservation]:
    repository_key = str(repository["repository_key"])
    components = repository.get("components", {})
    observations = _workspace_facts(repository, snapshot_id)
    git_refs = _git_ref_facts(repository)
    bookmarks = _bookmark_facts(repository)
    heads, history = _jj_graph_facts(repository)
    object_facts = _object_facts(repository, objects)
    observations.extend(
        (
            _component_observation(
                repository_key, "git_refs", components.get("git_refs"), snapshot_id, git_refs
            ),
            _component_observation(
                repository_key,
                "jj_bookmarks",
                components.get("jj_bookmarks"),
                snapshot_id,
                bookmarks,
            ),
            _component_observation(
                repository_key,
                "jj_visible_heads",
                components.get("jj_visible_heads"),
                snapshot_id,
                heads,
            ),
            _component_observation(
                repository_key,
                "git_history",
                components.get("git_history"),
                snapshot_id,
                object_facts["git_history"],
            ),
            _component_observation(
                repository_key,
                "jj_history",
                components.get("jj_history"),
                snapshot_id,
                [*history, *object_facts["jj_history"]],
            ),
        )
    )
    for name in ("identity", "path_evidence"):
        observations.append(
            _component_observation(
                repository_key, name, components.get(name), snapshot_id, absence_authorized=False
            )
        )
    return observations


def _evidence(observation: ComponentObservation) -> dict[str, Any]:
    return {
        "snapshot_id": observation.snapshot_id,
        "component": observation.component,
        "outcome": observation.state,
        "observed_at": observation.attempted_at,
        "time_precision": observation.precision,
    }


def _update_component(
    components: dict[str, dict[str, Any]], observation: ComponentObservation
) -> None:
    value = components.setdefault(
        observation.component_key,
        {
            "component_key": observation.component_key,
            "repository_key": observation.repository_key,
            "component": observation.component,
            "last_attempted_at": {"state": "never_observed"},
            "complete_as_of": {"state": "never_observed"},
            "last_outcome": "not_requested",
            "errors": [],
        },
    )
    value["last_outcome"] = observation.state
    value["errors"] = _copy(list(observation.errors))
    if observation.freshness is not None:
        value["freshness"] = observation.freshness
    if observation.attempted_at is not None:
        value["last_attempted_at"] = {
            "state": "observed",
            "at": observation.attempted_at,
            "time_precision": observation.precision,
            "snapshot_id": observation.snapshot_id,
        }
    if observation.state in {CollectionState.COMPLETE.value, "performed"}:
        value["complete_as_of"] = {
            "state": "observed",
            "at": observation.attempted_at,
            "time_precision": observation.precision,
            "snapshot_id": observation.snapshot_id,
        }


def _confirm(
    records: dict[str, dict[str, Any]], fact: AtomicFact, observation: ComponentObservation
) -> None:
    record = records.setdefault(fact.fact_key, fact.record())
    intervals = record["intervals"]
    evidence = _evidence(observation)
    if intervals and intervals[-1]["invalidated_at"] is None:
        intervals[-1]["last_confirmed_at"] = observation.attempted_at
        intervals[-1]["last_confirmed_by"] = evidence
        return
    intervals.append(
        {
            "episode": len(intervals) + 1,
            "prior_boundary": {
                "state": "never_observed" if not intervals else "tombstone",
                "origin": "negative_infinity" if not intervals else intervals[-1]["invalidated_at"],
            },
            "first_observed_at": observation.attempted_at,
            "last_confirmed_at": observation.attempted_at,
            "invalidated_at": None,
            "opened_by": evidence,
            "last_confirmed_by": evidence,
            "invalidated_by": None,
        }
    )


def _invalidate(record: dict[str, Any], observation: ComponentObservation) -> None:
    interval = record["intervals"][-1]
    interval["invalidated_at"] = observation.attempted_at
    interval["invalidated_by"] = _evidence(observation)


def _apply_observation(
    records: dict[str, dict[str, Any]],
    components: dict[str, dict[str, Any]],
    observation: ComponentObservation,
) -> None:
    _update_component(components, observation)
    if observation.attempted_at is None or observation.state not in {
        CollectionState.COMPLETE.value,
        CollectionState.PARTIAL.value,
    }:
        return
    present = {fact.fact_key for fact in observation.facts}
    for fact in observation.facts:
        _confirm(records, fact, observation)
    if observation.state != CollectionState.COMPLETE.value or not observation.absence_authorized:
        return
    for record in records.values():
        if (
            record["component_key"] == observation.component_key
            and record["absence_authorized"]
            and record["fact_key"] not in present
            and record["intervals"]
            and record["intervals"][-1]["invalidated_at"] is None
        ):
            _invalidate(record, observation)


def _snapshot_item(value: Any, position: int) -> tuple[int, Mapping[str, Any]] | None:
    if isinstance(value, Mapping) and "manifest" in value:
        manifest = value.get("manifest")
        if not isinstance(manifest, Mapping):
            return None
        generation = value.get("generation", position)
    elif isinstance(value, Mapping) and "schema" in value:
        manifest = value
        generation = position
    elif isinstance(value, Mapping):
        return None
    else:
        raise ContractError("snapshot input must be an object")
    if not isinstance(generation, int):
        raise ContractError("snapshot generation must be an integer")
    return generation, manifest


class TemporalIndexBuilder:
    """Build a canonical disposable index from retained compatible snapshots."""

    def build(
        self,
        snapshots: Iterable[Mapping[str, Any]],
        *,
        objects: Mapping[str, Mapping[str, Any]] | None = None,
        store_id: str | None = None,
        progress: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        report = progress or (lambda _message: None)
        report("temporal index: reading retained snapshots")
        items = []
        for position, value in enumerate(snapshots):
            item = _snapshot_item(value, position)
            if item is not None:
                generation, manifest = item
                document = parse_snapshot(manifest)
                if "schema" in value:
                    generation = document.history_store.generation
                items.append((generation, document.captured_at, document.snapshot_id, document))
        items.sort(key=lambda item: item[:3])
        report(f"temporal index: indexing {len(items)} snapshot(s)")
        store_ids = {item[3].history_store.store_id for item in items}
        if len(store_ids) > 1 or (store_id is not None and store_ids and store_id not in store_ids):
            raise ContractError("snapshots must use one matching history store")
        records: dict[str, dict[str, Any]] = {}
        components: dict[str, dict[str, Any]] = {}
        source_snapshots = []
        continuity_boundaries = []
        prior_locations: dict[tuple[str, str], str] = {}
        objects = objects or {}
        for position, (generation, _captured_at, snapshot_id, document) in enumerate(items, 1):
            report(f"temporal index: snapshot {position}/{len(items)} (generation {generation})")
            normalized = normalize_snapshot(document)
            source_snapshots.append(
                {
                    "snapshot_id": snapshot_id,
                    "generation": generation,
                    "schema_version": document.schema_version,
                }
            )
            scope = str(document.scan.get("root", ""))
            scan_outcome = document.scan.get("outcome", {})
            scan_state = str(scan_outcome.get("state", "unknown"))
            scan_errors = tuple(
                item for item in scan_outcome.get("errors", ()) if isinstance(item, Mapping)
            )
            scan_observed_at = document.captured_at if scan_state != "not_requested" else None
            repositories = normalized["repositories"]
            current_locations = {}
            repository_facts = []
            for repository in repositories:
                repository_key = str(repository["repository_key"])
                locations = repository.get("facts", {}).get("locations", ())
                path = ""
                if locations and isinstance(locations[0], Mapping):
                    path = str(locations[0].get("path", ""))
                if path:
                    previous = prior_locations.get((scope, path))
                    if previous is not None and previous != repository_key:
                        continuity_boundaries.append(
                            {
                                "snapshot_id": snapshot_id,
                                "scope": scope,
                                "path": path,
                                "before_repository_key": previous,
                                "after_repository_key": repository_key,
                            }
                        )
                    current_locations[path] = repository_key
                    prior_locations[(scope, path)] = repository_key
                repository_facts.append(
                    _fact(
                        "repository-exists",
                        repository_key,
                        "repository_identity",
                        (),
                        {"repository_key": repository_key, "scope": scope, "path": path or None},
                        component_key=f"scan:{_part(scope)}:repository_identity",
                    )
                )
                for observation in _repository_observations(repository, snapshot_id, objects):
                    _apply_observation(records, components, observation)
            continuity_lost = any(
                item["snapshot_id"] == snapshot_id and item["scope"] == scope
                for item in continuity_boundaries
            )
            scan_observation = ComponentObservation(
                f"scan:{_part(scope)}:repository_identity",
                None,
                "repository_identity",
                scan_state,
                scan_observed_at,
                "snapshot",
                snapshot_id,
                scan_errors,
                tuple(sorted(repository_facts, key=lambda item: item.fact_key)),
                absence_authorized=not continuity_lost,
            )
            _apply_observation(records, components, scan_observation)
        resolved_store = store_id
        if resolved_store is None and items:
            resolved_store = items[-1][3].history_store.store_id
        return {
            "schema": TEMPORAL_SCHEMA,
            "schema_version": TEMPORAL_SCHEMA_VERSION,
            "store_id": resolved_store,
            "source_generation": max((item[0] for item in items), default=0),
            "source_snapshots": source_snapshots,
            "components": [components[key] for key in sorted(components)],
            "facts": [records[key] for key in sorted(records)],
            "continuity_boundaries": sorted(
                continuity_boundaries,
                key=lambda item: (item["snapshot_id"], item["scope"], item["path"]),
            ),
        }

    def extend(
        self,
        previous: Mapping[str, Any],
        snapshot: Mapping[str, Any],
        *,
        objects: Mapping[str, Mapping[str, Any]] | None = None,
        store_id: str | None = None,
        progress: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        """Apply exactly one consecutive snapshot to a validated projection."""
        if (
            previous.get("schema") != TEMPORAL_SCHEMA
            or previous.get("schema_version") != TEMPORAL_SCHEMA_VERSION
        ):
            raise ContractError("incompatible temporal index")
        item = _snapshot_item(snapshot, 0)
        if item is None:
            raise ContractError("snapshot has no retained manifest")
        generation, manifest = item
        document = parse_snapshot(manifest)
        if document.history_store.store_id != (store_id or previous.get("store_id")):
            raise ContractError("snapshot store does not match temporal index")
        if generation != previous.get("source_generation", 0) + 1:
            raise ContractError("snapshot generation is not consecutive")
        report = progress or (lambda _message: None)
        report(f"temporal index: extending to generation {generation}")
        records = {item["fact_key"]: _copy(item) for item in previous.get("facts", ())}
        components = {item["component_key"]: _copy(item) for item in previous.get("components", ())}
        source_snapshots = _copy(list(previous.get("source_snapshots", ())))
        continuity_boundaries = _copy(list(previous.get("continuity_boundaries", ())))
        prior_locations: dict[tuple[str, str], str] = {}
        for record in records.values():
            if record.get("fact_type") != "repository-exists":
                continue
            attributes = record.get("attributes", {})
            if attributes.get("scope") and attributes.get("path"):
                prior_locations[(attributes["scope"], attributes["path"])] = record[
                    "repository_key"
                ]
        normalized = normalize_snapshot(document)
        snapshot_id = document.snapshot_id
        source_snapshots.append(
            {
                "snapshot_id": snapshot_id,
                "generation": generation,
                "schema_version": document.schema_version,
            }
        )
        scope = str(document.scan.get("root", ""))
        scan_outcome = document.scan.get("outcome", {})
        scan_state = str(scan_outcome.get("state", "unknown"))
        scan_errors = tuple(
            item for item in scan_outcome.get("errors", ()) if isinstance(item, Mapping)
        )
        scan_observed_at = document.captured_at if scan_state != "not_requested" else None
        repository_facts = []
        objects = objects or {}
        for repository in normalized["repositories"]:
            repository_key = str(repository["repository_key"])
            locations = repository.get("facts", {}).get("locations", ())
            path = ""
            if locations and isinstance(locations[0], Mapping):
                path = str(locations[0].get("path", ""))
            if path:
                previous_key = prior_locations.get((scope, path))
                if previous_key is not None and previous_key != repository_key:
                    continuity_boundaries.append(
                        {
                            "snapshot_id": snapshot_id,
                            "scope": scope,
                            "path": path,
                            "before_repository_key": previous_key,
                            "after_repository_key": repository_key,
                        }
                    )
                prior_locations[(scope, path)] = repository_key
            repository_facts.append(
                _fact(
                    "repository-exists",
                    repository_key,
                    "repository_identity",
                    (),
                    {"repository_key": repository_key, "scope": scope, "path": path or None},
                    component_key=f"scan:{_part(scope)}:repository_identity",
                )
            )
            for observation in _repository_observations(repository, snapshot_id, objects):
                _apply_observation(records, components, observation)
        continuity_lost = any(
            item["snapshot_id"] == snapshot_id and item["scope"] == scope
            for item in continuity_boundaries
        )
        _apply_observation(
            records,
            components,
            ComponentObservation(
                f"scan:{_part(scope)}:repository_identity",
                None,
                "repository_identity",
                scan_state,
                scan_observed_at,
                "snapshot",
                snapshot_id,
                scan_errors,
                tuple(sorted(repository_facts, key=lambda item: item.fact_key)),
                absence_authorized=not continuity_lost,
            ),
        )
        return {
            "schema": TEMPORAL_SCHEMA,
            "schema_version": TEMPORAL_SCHEMA_VERSION,
            "store_id": store_id or previous.get("store_id"),
            "source_generation": generation,
            "source_snapshots": source_snapshots,
            "components": [components[key] for key in sorted(components)],
            "facts": [records[key] for key in sorted(records)],
            "continuity_boundaries": sorted(
                continuity_boundaries,
                key=lambda item: (item["snapshot_id"], item["scope"], item["path"]),
            ),
        }


def fact_state(index: Mapping[str, Any], key: str) -> dict[str, Any]:
    """Return active/inactive state or explicit negative-infinity never-observed state."""
    record = next((item for item in index.get("facts", ()) if item.get("fact_key") == key), None)
    if record is None or not record.get("intervals"):
        return {"state": "never_observed", "origin": "negative_infinity", "fact_key": key}
    interval = record["intervals"][-1]
    return {
        "state": "active" if interval.get("invalidated_at") is None else "inactive",
        "origin": (
            interval.get("first_observed_at")
            if interval.get("invalidated_at") is None
            else interval.get("invalidated_at")
        ),
        "fact_key": key,
        "interval": _copy(interval),
    }


__all__ = [
    "TEMPORAL_SCHEMA",
    "TEMPORAL_SCHEMA_VERSION",
    "AtomicFact",
    "ComponentObservation",
    "TemporalIndexBuilder",
    "fact_key",
    "fact_state",
]
