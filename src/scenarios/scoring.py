"""Scenario aggregate scoring formulas (SCEN-03)."""

from __future__ import annotations

import math
from collections.abc import Mapping

import networkx as nx


def largest_weakly_connected_component_size(graph: nx.DiGraph) -> int:
    """Return largest weakly connected component size, counted in airports.

    Retained as the structural reference; scoring uses
    :func:`largest_component_traffic`, which measures the same component by the
    traffic it carries (spec §9.1).
    """
    if graph.number_of_nodes() == 0:
        return 0
    return len(max(nx.weakly_connected_components(graph), key=len))


def largest_component_traffic(
    graph: nx.DiGraph, strengths: Mapping[int, float] | None = None
) -> float:
    """Traffic carried by the largest weakly connected component (spec §9.1).

    Counting airports treats losing ATL and losing ANC as the same event, which makes
    the term near-constant across a well-connected network. Summing strength instead
    lets the measure reflect what the component actually moves.
    """
    if graph.number_of_nodes() == 0:
        return 0.0
    if strengths is None:
        strengths = node_strengths(graph)
    return max(
        (
            sum(float(strengths.get(int(node), 0.0)) for node in component)
            for component in nx.weakly_connected_components(graph)
        ),
        default=0.0,
    )


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


def node_strengths(graph: nx.DiGraph) -> dict[int, float]:
    """Total strength per node: ``s_in + s_out`` over edge weights (spec §7.3)."""
    strengths: dict[int, float] = dict.fromkeys((int(n) for n in graph.nodes()), 0.0)
    for source, target, data in graph.edges(data=True):
        weight = float(data.get("weight", 0.0))
        strengths[int(source)] += weight
        strengths[int(target)] += weight
    return strengths


def weighted_reach(graph: nx.DiGraph, strengths: Mapping[int, float] | None = None) -> float:
    """Sum of ``s_total(i) * s_total(j)`` over reachable ordered pairs (spec §9.2).

    Weighting by endpoint traffic is what gives the reachability term any
    discrimination: counting pairs equally makes a transcontinental trunk worth the
    same as a link between two regional airports, and on a well-connected network the
    unweighted count is near-constant across every airport.

    Derived from the SCC condensation for the same reason as
    :func:`reachable_pairs_count`. Every member of a component reaches the same set,
    so the contribution of component ``C`` is ``S_C * S_reach(C)`` less the ``s_i^2``
    self-pairs the definition excludes.
    """
    if graph.number_of_nodes() == 0:
        return 0.0
    if strengths is None:
        strengths = node_strengths(graph)

    condensation = nx.condensation(graph)
    order = condensation.number_of_nodes()

    component_strength = [0.0] * order
    component_square = [0.0] * order
    for component_id, members in condensation.nodes(data="members"):
        for node in members:
            strength = float(strengths.get(int(node), 0.0))
            component_strength[component_id] += strength
            component_square[component_id] += strength * strength

    reachable_mask = [0] * order
    for component_id in reversed(list(nx.topological_sort(condensation))):
        mask = 1 << component_id
        for successor in condensation.successors(component_id):
            mask |= reachable_mask[successor]
        reachable_mask[component_id] = mask

    total = 0.0
    for component_id, mask in enumerate(reachable_mask):
        reached_strength = 0.0
        remaining = mask
        while remaining:
            lowest_bit = remaining & -remaining
            reached_strength += component_strength[lowest_bit.bit_length() - 1]
            remaining ^= lowest_bit
        total += component_strength[component_id] * reached_strength - component_square[component_id]
    return float(total)


def lcc_loss(
    pre_graph: nx.DiGraph,
    post_graph: nx.DiGraph,
    *,
    strengths: Mapping[int, float] | None = None,
    post_lcc_size: float | None = None,
) -> float:
    """Compute LCC loss over component traffic (spec §9.1).

    ``post_lcc_size`` accepts a precomputed component traffic total when a batch caller
    has already derived it (see :class:`scenarios.connectivity.ConnectivityIndex`);
    ``None`` measures ``post_graph`` directly for identical standalone behavior.
    """
    if strengths is None:
        strengths = node_strengths(pre_graph)
    pre = largest_component_traffic(pre_graph, strengths)
    post = (
        largest_component_traffic(post_graph, strengths)
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
    strengths: Mapping[int, float] | None = None,
    pre_reachable_pairs: float | None = None,
    post_reachable_pairs: float | None = None,
) -> float:
    """Compute reachability loss with denominator guard for zero pre baseline.

    Measured over traffic-weighted reachable pairs (spec §9.2). ``strengths`` are
    computed from ``pre_graph`` when omitted; a removal never changes the strength of
    the airports that remain, so the baseline strengths apply to both graphs.

    Both totals accept precomputed values so a batch caller can supply the invariant
    baseline and an index-derived post-removal total; ``None`` measures the graph
    directly for identical standalone behavior.
    """
    if strengths is None:
        strengths = node_strengths(pre_graph)
    pre = (
        weighted_reach(pre_graph, strengths)
        if pre_reachable_pairs is None
        else float(pre_reachable_pairs)
    )
    post = (
        weighted_reach(post_graph, strengths)
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
    strengths: Mapping[int, float] | None = None,
) -> float:
    """Traffic-weighted mean exposure across the network (spec §9.3).

    Counting airports above a fixed threshold discards both the magnitude of each
    exposure and the size of the airport it landed on. On a real snapshot that count
    produced nine distinct values across 348 airports and ranked regional airports
    above every hub in the country.

    Weighting by strength keeps both. ``Exposure`` is bounded by the shock, which is
    itself bounded by 100, so the result is already on the 0-100 scale.

    ``strengths`` falls back to counting when omitted, which preserves the previous
    behaviour for callers that have no graph to hand.
    """
    if total_airports <= 0:
        return 0.0

    if strengths is None:
        affected = sum(
            1
            for payload in exposure_by_airport.values()
            if float(payload.get("exposure_score", 0.0)) >= 10.0
        )
        return _finite_percentage(100.0 * (float(affected) / float(total_airports)))

    total_strength = float(sum(strengths.values()))
    if total_strength <= 0.0:
        return 0.0

    weighted = sum(
        float(payload.get("exposure_score", 0.0)) * float(strengths.get(int(airport), 0.0))
        for airport, payload in exposure_by_airport.items()
    )
    return _finite_percentage(weighted / total_strength)


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
    strengths: Mapping[int, float] | None = None,
    pre_reachable_pairs: float | None = None,
    post_lcc_size: float | None = None,
    post_reachable_pairs: float | None = None,
) -> dict[str, float]:
    """Return the aggregate scorecards for scenario outputs.

    The three optional counts let a batch caller supply quantities it has already
    derived: the invariant baseline reachable-pair count, and the two post-removal
    counts from :class:`scenarios.connectivity.ConnectivityIndex`. Each defaults to
    ``None``, which measures the graphs directly exactly as before.
    """
    lcc = lcc_loss(pre_graph, post_graph, strengths=strengths, post_lcc_size=post_lcc_size)
    reach = reachability_loss(
        pre_graph,
        post_graph,
        strengths=strengths,
        pre_reachable_pairs=pre_reachable_pairs,
        post_reachable_pairs=post_reachable_pairs,
    )
    ripple = ripple_severity(
        exposure_by_airport, total_airports=total_airports, strengths=strengths
    )
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
