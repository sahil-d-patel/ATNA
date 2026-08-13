"""Scenario aggregate scoring formulas (SCEN-03)."""

from __future__ import annotations

import math
from collections.abc import Mapping

import networkx as nx


def largest_weakly_connected_component_size(graph: nx.DiGraph) -> int:
    """Return largest weakly connected component size for directed graph."""
    if graph.number_of_nodes() == 0:
        return 0
    return len(max(nx.weakly_connected_components(graph), key=len))


def reachable_pairs_count(graph: nx.DiGraph) -> int:
    """Count reachable ordered pairs (excluding self pairs) on directed graph.

    Every node inside a strongly connected component reaches exactly the same set of
    nodes, so the count is derived from the SCC condensation instead of a breadth-first
    sweep per node: one ``O(V + E)`` Tarjan pass plus a reverse-topological bitset union
    over the condensation DAG, rather than ``V`` traversals of the whole graph. The
    result is identical to the per-node definition; only the cost changes.
    """
    if graph.number_of_nodes() == 0:
        return 0

    condensation = nx.condensation(graph)
    component_size = [0] * condensation.number_of_nodes()
    for component_id, members in condensation.nodes(data="members"):
        component_size[component_id] = len(members)

    # reachable_mask[c] has bit d set when component d is reachable from component c.
    # Successors are finalized before their predecessors, so each mask is one OR pass.
    reachable_mask = [0] * condensation.number_of_nodes()
    for component_id in reversed(list(nx.topological_sort(condensation))):
        mask = 1 << component_id
        for successor in condensation.successors(component_id):
            mask |= reachable_mask[successor]
        reachable_mask[component_id] = mask

    total = 0
    for component_id, mask in enumerate(reachable_mask):
        reached_nodes = 0
        remaining = mask
        while remaining:
            lowest_bit = remaining & -remaining
            reached_nodes += component_size[lowest_bit.bit_length() - 1]
            remaining ^= lowest_bit
        # Each member reaches every node in the union, minus itself.
        total += component_size[component_id] * (reached_nodes - 1)
    return int(total)


def lcc_loss(
    pre_graph: nx.DiGraph,
    post_graph: nx.DiGraph,
    *,
    post_lcc_size: int | None = None,
) -> float:
    """Compute LCC loss: ``100 * (1 - LCC_post / LCC_pre)``.

    ``post_lcc_size`` accepts a precomputed component size when a batch caller has
    already derived it (see :class:`scenarios.connectivity.ConnectivityIndex`);
    ``None`` measures ``post_graph`` directly for identical standalone behavior.
    """
    pre = float(largest_weakly_connected_component_size(pre_graph))
    post = (
        float(largest_weakly_connected_component_size(post_graph))
        if post_lcc_size is None
        else float(post_lcc_size)
    )
    if pre <= 0.0:
        return 0.0
    return _finite_percentage(100.0 * (1.0 - (post / pre)))


def reachability_loss(
    pre_graph: nx.DiGraph,
    post_graph: nx.DiGraph,
    *,
    pre_reachable_pairs: int | None = None,
    post_reachable_pairs: int | None = None,
) -> float:
    """Compute reachability loss with denominator guard for zero pre baseline.

    Both counts accept precomputed values so a batch caller can supply the invariant
    baseline and an index-derived post-removal count; ``None`` measures the graph
    directly for identical standalone behavior.
    """
    pre = (
        float(reachable_pairs_count(pre_graph))
        if pre_reachable_pairs is None
        else float(pre_reachable_pairs)
    )
    post = (
        float(reachable_pairs_count(post_graph))
        if post_reachable_pairs is None
        else float(post_reachable_pairs)
    )
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
    """Compute impact score using the specified blend weights."""
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
    pre_reachable_pairs: int | None = None,
    post_lcc_size: int | None = None,
    post_reachable_pairs: int | None = None,
) -> dict[str, float]:
    """Return the aggregate scorecards for scenario outputs.

    The three optional counts let a batch caller supply quantities it has already
    derived: the invariant baseline reachable-pair count, and the two post-removal
    counts from :class:`scenarios.connectivity.ConnectivityIndex`. Each defaults to
    ``None``, which measures the graphs directly exactly as before.
    """
    lcc = lcc_loss(pre_graph, post_graph, post_lcc_size=post_lcc_size)
    reach = reachability_loss(
        pre_graph,
        post_graph,
        pre_reachable_pairs=pre_reachable_pairs,
        post_reachable_pairs=post_reachable_pairs,
    )
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
