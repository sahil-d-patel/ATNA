"""Immutable graph edit primitives for scenario execution."""

from __future__ import annotations

from typing import Any, Mapping

import networkx as nx

from scenarios.models import (
    AirportRemovalPayload,
    RouteRemovalPayload,
    ScenarioEditResult,
    ScenarioType,
)


def remove_airport(
    baseline_graph: nx.DiGraph,
    payload: Mapping[str, Any],
    *,
    snapshot_id: str | None = None,
) -> tuple[nx.DiGraph, ScenarioEditResult]:
    """Return a copied graph with one airport removed."""
    if not isinstance(baseline_graph, nx.DiGraph):
        raise TypeError("baseline_graph must be a networkx.DiGraph")
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping with 'airport_id'")

    if "airport_id" not in payload:
        raise KeyError("airport removal payload missing required key: 'airport_id'")

    airport = AirportRemovalPayload(airport_id=payload["airport_id"])
    if not baseline_graph.has_node(airport.airport_id):
        raise ValueError(f"airport_id {airport.airport_id} does not exist in baseline graph")

    edited = baseline_graph.copy()
    edited.remove_node(airport.airport_id)
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
) -> tuple[nx.DiGraph, ScenarioEditResult]:
    """Return a copied graph with one directed route removed."""
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

    edited = baseline_graph.copy()
    edited.remove_edge(route.origin_id, route.destination_id)
    metadata = ScenarioEditResult(
        scenario_type=ScenarioType.ROUTE_REMOVAL,
        snapshot_id=snapshot_id,
        removed_airport_id=None,
        removed_origin_id=route.origin_id,
        removed_destination_id=route.destination_id,
    )
    return edited, metadata
