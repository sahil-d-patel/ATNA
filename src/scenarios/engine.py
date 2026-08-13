"""Scenario orchestration from graph edit through normalized artifact records."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

import networkx as nx

from scenarios.connectivity import ConnectivityCounts
from scenarios.graph_edits import remove_airport, remove_route
from scenarios.models import ScenarioType
from scenarios.ripple import airport_removal_exposure, route_removal_exposure
from scenarios.scoring import aggregate_scenario_scores


def run_scenario(
    baseline_graph: nx.DiGraph,
    *,
    snapshot_id: str,
    scenario_type: str | ScenarioType,
    payload: Mapping[str, Any],
    created_at: str | None = None,
    precomputed_shares: Mapping[int, Mapping[int, float]] | None = None,
    precomputed_dependency: Mapping[int, Mapping[int, float]] | None = None,
    pre_reachable_pairs: int | None = None,
    post_connectivity: ConnectivityCounts | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run one scenario end-to-end and return normalized scenario and exposure rows.

    ``precomputed_shares``, ``precomputed_dependency``, and ``pre_reachable_pairs``
    let repeat callers reuse quantities derived solely from the unchanged baseline
    graph — normalized neighbor shares, undirected dependency weights, and the
    baseline reachable-pair count. ``post_connectivity`` additionally supplies the
    post-removal component size and reachable-pair count, which a sweep can obtain
    from :class:`scenarios.connectivity.ConnectivityIndex` far more cheaply than by
    measuring each edited graph. All default to ``None`` for identical single-run
    behavior.
    """
    if not isinstance(baseline_graph, nx.DiGraph):
        raise TypeError("baseline_graph must be a networkx.DiGraph")
    if not isinstance(snapshot_id, str) or not snapshot_id.strip():
        raise ValueError("snapshot_id must be a non-empty string")
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping")

    # ``post_graph`` is scored and discarded inside this function — it is never mutated
    # and never returned — so a read-only view is sufficient and avoids copying the
    # full baseline adjacency once per scenario.
    scenario_enum = ScenarioType(str(scenario_type))
    if scenario_enum is ScenarioType.AIRPORT_REMOVAL:
        post_graph, edit = remove_airport(
            baseline_graph, payload, snapshot_id=snapshot_id, copy=False
        )
        exposure_by_airport = airport_removal_exposure(
            baseline_graph,
            removed_airport_id=int(edit.removed_airport_id),
            precomputed_shares=precomputed_shares,
        )
        edited_airports = [int(edit.removed_airport_id)]
        edited_routes: list[dict[str, int]] = []
    else:
        post_graph, edit = remove_route(
            baseline_graph, payload, snapshot_id=snapshot_id, copy=False
        )
        exposure_by_airport = route_removal_exposure(
            baseline_graph,
            origin_id=int(edit.removed_origin_id),
            destination_id=int(edit.removed_destination_id),
            precomputed_dependency=precomputed_dependency,
        )
        edited_airports = []
        edited_routes = [
            {
                "origin_id": int(edit.removed_origin_id),
                "destination_id": int(edit.removed_destination_id),
            }
        ]

    scenario_id = make_scenario_id(
        snapshot_id=snapshot_id,
        scenario_type=scenario_enum.value,
        payload=payload,
    )
    scenario_created_at = created_at or utc_now_iso()
    scores = aggregate_scenario_scores(
        pre_graph=baseline_graph,
        post_graph=post_graph,
        exposure_by_airport=exposure_by_airport,
        total_airports=baseline_graph.number_of_nodes(),
        pre_reachable_pairs=pre_reachable_pairs,
        post_lcc_size=None if post_connectivity is None else post_connectivity.lcc_size,
        post_reachable_pairs=(
            None if post_connectivity is None else post_connectivity.reachable_pairs
        ),
    )
    scenario_row = {
        "scenario_id": scenario_id,
        "snapshot_id": snapshot_id,
        "scenario_type": scenario_enum.value,
        "edited_airports": json.dumps(edited_airports, separators=(",", ":")),
        "edited_routes": json.dumps(edited_routes, separators=(",", ":")),
        "impact_score": float(scores["impact_score"]),
        "network_health": float(scores["network_health"]),
        "lcc_loss": float(scores["lcc_loss"]),
        "reachability_loss": float(scores["reachability_loss"]),
        "ripple_severity": float(scores["ripple_severity"]),
        "created_at": scenario_created_at,
    }
    exposure_rows = normalize_exposure_rows(
        scenario_id=scenario_id,
        exposure_by_airport=exposure_by_airport,
    )
    return scenario_row, exposure_rows


def make_scenario_id(
    *,
    snapshot_id: str,
    scenario_type: str,
    payload: Mapping[str, Any],
) -> str:
    """Return deterministic scenario id based on snapshot/type/payload."""
    canonical = json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(
        f"{snapshot_id}|{scenario_type}|{canonical}".encode()
    ).hexdigest()
    return f"scn_{digest[:16]}"


def normalize_exposure_rows(
    *,
    scenario_id: str,
    exposure_by_airport: Mapping[int, Mapping[str, float | int]],
) -> list[dict[str, Any]]:
    """Return schema-aligned exposure rows with deterministic ranking."""
    ordered = sorted(
        (
            (
                int(airport_id),
                float(airport_data.get("exposure_score", 0.0)),
                int(airport_data.get("hop_level", 0)),
            )
            for airport_id, airport_data in exposure_by_airport.items()
            if float(airport_data.get("exposure_score", 0.0)) > 0.0
        ),
        key=lambda item: (-item[1], item[0]),
    )
    rows: list[dict[str, Any]] = []
    for idx, (airport_id, exposure_score, hop_level) in enumerate(ordered, start=1):
        rows.append(
            {
                "scenario_id": scenario_id,
                "airport_id": airport_id,
                "hop_level": hop_level,
                "exposure_score": exposure_score,
                "exposure_rank": idx,
            }
        )
    return rows


def utc_now_iso() -> str:
    """Return UTC timestamp in ISO-8601 format with ``Z`` suffix."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
