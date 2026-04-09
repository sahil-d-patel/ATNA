"""Scenario aggregate scoring formulas (SCEN-03)."""

from __future__ import annotations

import math
from typing import Mapping

import networkx as nx


def largest_weakly_connected_component_size(graph: nx.DiGraph) -> int:
    """Return largest weakly connected component size for directed graph."""
    if graph.number_of_nodes() == 0:
        return 0
    return len(max(nx.weakly_connected_components(graph), key=len))


def reachable_pairs_count(graph: nx.DiGraph) -> int:
    """Count reachable ordered pairs (excluding self pairs) on directed graph."""
    total = 0
    for node in graph.nodes():
        reachable = nx.single_source_shortest_path_length(graph, node)
        total += max(len(reachable) - 1, 0)
    return int(total)


def lcc_loss(pre_graph: nx.DiGraph, post_graph: nx.DiGraph) -> float:
    """Compute LCC loss: ``100 * (1 - LCC_post / LCC_pre)``."""
    pre = float(largest_weakly_connected_component_size(pre_graph))
    post = float(largest_weakly_connected_component_size(post_graph))
    if pre <= 0.0:
        return 0.0
    return _finite_percentage(100.0 * (1.0 - (post / pre)))


def reachability_loss(pre_graph: nx.DiGraph, post_graph: nx.DiGraph) -> float:
    """Compute reachability loss with denominator guard for zero pre baseline."""
    pre = float(reachable_pairs_count(pre_graph))
    post = float(reachable_pairs_count(post_graph))
    if pre <= 0.0:
        return 0.0
    return _finite_percentage(100.0 * (1.0 - (post / pre)))


def ripple_severity(
    exposure_by_airport: Mapping[int, Mapping[str, float | int]],
    *,
    total_airports: int,
    threshold: float = 10.0,
) -> float:
    """Compute share of airports with exposure >= threshold, scaled to 0-100."""
    if total_airports <= 0:
        return 0.0
    affected = 0
    for payload in exposure_by_airport.values():
        if float(payload.get("exposure_score", 0.0)) >= threshold:
            affected += 1
    return _finite_percentage(100.0 * (float(affected) / float(total_airports)))


def impact_score(
    *,
    lcc_loss_value: float,
    reachability_loss_value: float,
    ripple_severity_value: float,
) -> float:
    """Compute impact score using locked blend weights."""
    score = (
        0.40 * float(lcc_loss_value)
        + 0.30 * float(reachability_loss_value)
        + 0.30 * float(ripple_severity_value)
    )
    return _finite_percentage(score)


def network_health(impact_score_value: float) -> float:
    """Compute network health as ``100 - impact_score``."""
    return _finite_percentage(100.0 - float(impact_score_value))


def aggregate_scenario_scores(
    *,
    pre_graph: nx.DiGraph,
    post_graph: nx.DiGraph,
    exposure_by_airport: Mapping[int, Mapping[str, float | int]],
    total_airports: int,
) -> dict[str, float]:
    """Return locked aggregate cards for scenario outputs."""
    lcc = lcc_loss(pre_graph, post_graph)
    reach = reachability_loss(pre_graph, post_graph)
    ripple = ripple_severity(exposure_by_airport, total_airports=total_airports)
    impact = impact_score(
        lcc_loss_value=lcc,
        reachability_loss_value=reach,
        ripple_severity_value=ripple,
    )
    health = network_health(impact)
    return {
        "lcc_loss": lcc,
        "reachability_loss": reach,
        "ripple_severity": ripple,
        "impact_score": impact,
        "network_health": health,
    }


def _finite_percentage(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    if value < 0.0:
        return 0.0
    if value > 100.0:
        return 100.0
    return float(value)
