"""Immutable graph edit primitives for scenario execution.

Both primitives default to returning a detached copy the caller may freely mutate.
Callers that only read the edited graph can pass ``copy=False`` to get a read-only
``restricted_view`` instead, which skips the ``O(V + E)`` duplication of the baseline
adjacency. The two modes are structurally identical for every read operation.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import networkx as nx

from scenarios.models import (
    AirportRemovalPayload,
    AirportSetRemovalPayload,
    RouteRemovalPayload,
    ScenarioEditResult,
    ScenarioType,
)


def remove_airport(
    baseline_graph: nx.DiGraph,
    payload: Mapping[str, Any],
    *,
    snapshot_id: str | None = None,
    copy: bool = True,
) -> tuple[nx.DiGraph, ScenarioEditResult]:
    """Return a graph with one airport removed.

    Args:
        copy: ``True`` (default) returns an independent, mutable copy. ``False``
            returns a read-only view over ``baseline_graph`` with the airport and its
            incident edges hidden — same reads, no adjacency duplication.
    """
    if not isinstance(baseline_graph, nx.DiGraph):
        raise TypeError("baseline_graph must be a networkx.DiGraph")
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping with 'airport_id'")

    if "airport_id" not in payload:
        raise KeyError("airport removal payload missing required key: 'airport_id'")

    airport = AirportRemovalPayload(airport_id=payload["airport_id"])
    if not baseline_graph.has_node(airport.airport_id):
        raise ValueError(f"airport_id {airport.airport_id} does not exist in baseline graph")

    if copy:
        edited = baseline_graph.copy()
        edited.remove_node(airport.airport_id)
    else:
        edited = nx.restricted_view(baseline_graph, [airport.airport_id], [])
    metadata = ScenarioEditResult(
        scenario_type=ScenarioType.AIRPORT_REMOVAL,
        snapshot_id=snapshot_id,
        removed_airport_id=airport.airport_id,
        removed_origin_id=None,
        removed_destination_id=None,
    )
    return edited, metadata


def remove_route(
    baseline_graph: nx.DiGraph,
    payload: Mapping[str, Any],
    *,
    snapshot_id: str | None = None,
    copy: bool = True,
) -> tuple[nx.DiGraph, ScenarioEditResult]:
    """Return a graph with one directed route removed.

    Args:
        copy: ``True`` (default) returns an independent, mutable copy. ``False``
            returns a read-only view over ``baseline_graph`` with the single directed
            edge hidden — same reads, no adjacency duplication.
    """
    if not isinstance(baseline_graph, nx.DiGraph):
        raise TypeError("baseline_graph must be a networkx.DiGraph")
    if not isinstance(payload, Mapping):
        raise TypeError(
            "payload must be a mapping with 'origin_id' and 'destination_id'"
        )

    required = ("origin_id", "destination_id")
    missing = [k for k in required if k not in payload]
    if missing:
        raise KeyError(f"route removal payload missing required key(s): {missing}")

    route = RouteRemovalPayload(
        origin_id=payload["origin_id"], destination_id=payload["destination_id"]
    )
    if not baseline_graph.has_edge(route.origin_id, route.destination_id):
        raise ValueError(
            f"route ({route.origin_id} -> {route.destination_id}) does not exist in baseline graph"
        )

    if copy:
        edited = baseline_graph.copy()
        edited.remove_edge(route.origin_id, route.destination_id)
    else:
        edited = nx.restricted_view(
            baseline_graph, [], [(route.origin_id, route.destination_id)]
        )
    metadata = ScenarioEditResult(
        scenario_type=ScenarioType.ROUTE_REMOVAL,
        snapshot_id=snapshot_id,
        removed_airport_id=None,
        removed_origin_id=route.origin_id,
        removed_destination_id=route.destination_id,
    )
    return edited, metadata


def remove_airports(
    baseline_graph: nx.DiGraph,
    payload: Mapping[str, Any],
    *,
    snapshot_id: str | None = None,
    copy: bool = True,
) -> tuple[nx.DiGraph, ScenarioEditResult]:
    """Return a graph with several airports removed at once.

    Args:
        copy: ``True`` (default) returns an independent, mutable copy. ``False``
            returns a read-only view with all named airports hidden.
    """
    if not isinstance(baseline_graph, nx.DiGraph):
        raise TypeError("baseline_graph must be a networkx.DiGraph")
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping with 'airport_ids'")
    if "airport_ids" not in payload:
        raise KeyError("airport-set removal payload missing required key: 'airport_ids'")

    airports = AirportSetRemovalPayload(airport_ids=tuple(payload["airport_ids"]))
    missing = [a for a in airports.airport_ids if not baseline_graph.has_node(a)]
    if missing:
        raise ValueError(f"airport_id(s) {missing} do not exist in baseline graph")

    if copy:
        edited = baseline_graph.copy()
        edited.remove_nodes_from(airports.airport_ids)
    else:
        edited = nx.restricted_view(baseline_graph, list(airports.airport_ids), [])

    metadata = ScenarioEditResult(
        scenario_type=ScenarioType.AIRPORT_SET_REMOVAL,
        snapshot_id=snapshot_id,
        removed_airport_id=None,
        removed_origin_id=None,
        removed_destination_id=None,
        removed_airport_ids=airports.airport_ids,
    )
    return edited, metadata
