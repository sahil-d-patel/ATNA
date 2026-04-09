"""Two-hop structural ripple propagation for scenario analysis (SCEN-02)."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Mapping

import networkx as nx

LAMBDA_DISCOUNT = 0.35
AIRPORT_REMOVAL_SHOCK = 100.0


def build_dependency_weights(graph: nx.DiGraph) -> dict[int, dict[int, float]]:
    """Build undirected structural dependency weights ``W(i,j)=w(i,j)+w(j,i)``."""
    if not isinstance(graph, nx.DiGraph):
        raise TypeError("graph must be a networkx.DiGraph")

    weights: dict[int, dict[int, float]] = defaultdict(dict)
    for u, v in graph.edges():
        w_uv = float(graph.get_edge_data(u, v, {}).get("weight", 0.0))
        w_vu = float(graph.get_edge_data(v, u, {}).get("weight", 0.0))
        undirected = w_uv + w_vu
        if undirected <= 0.0:
            continue
        weights[int(u)][int(v)] = undirected
        weights[int(v)][int(u)] = undirected
    return {k: dict(v) for k, v in weights.items()}


def normalize_neighbor_shares(
    dependency_weights: Mapping[int, Mapping[int, float]],
) -> dict[int, dict[int, float]]:
    """Normalize local dependency shares ``Share(i,j)=W(i,j)/sum_k W(i,k)``."""
    shares: dict[int, dict[int, float]] = {}
    for src, neighbors in dependency_weights.items():
        total = float(sum(max(float(w), 0.0) for w in neighbors.values()))
        if total <= 0.0:
            shares[int(src)] = {}
            continue
        shares[int(src)] = {int(dst): float(w) / total for dst, w in neighbors.items()}
    return shares


def airport_removal_exposure(
    graph: nx.DiGraph,
    removed_airport_id: int,
    *,
    lambda_discount: float = LAMBDA_DISCOUNT,
) -> dict[int, dict[str, float | int]]:
    """Compute 2-hop exposure after removing an airport from baseline topology."""
    if not graph.has_node(removed_airport_id):
        raise ValueError(f"removed airport {removed_airport_id} does not exist in graph")

    dependency = build_dependency_weights(graph)
    shares = normalize_neighbor_shares(dependency)
    seed = {int(removed_airport_id): AIRPORT_REMOVAL_SHOCK}
    return _propagate_two_hops(shares, seed, lambda_discount=lambda_discount)


def route_removal_exposure(
    graph: nx.DiGraph,
    origin_id: int,
    destination_id: int,
    *,
    lambda_discount: float = LAMBDA_DISCOUNT,
) -> dict[int, dict[str, float | int]]:
    """Compute 2-hop exposure after removing a route using endpoint 50/50 seeding."""
    dependency = build_dependency_weights(graph)
    shares = normalize_neighbor_shares(dependency)

    route_weight = float(dependency.get(int(origin_id), {}).get(int(destination_id), 0.0))
    max_weight = _max_route_weight(dependency)
    route_shock = 0.0 if max_weight <= 0.0 else 100.0 * route_weight / max_weight
    seeds = {int(origin_id): 0.5 * route_shock, int(destination_id): 0.5 * route_shock}
    return _propagate_two_hops(shares, seeds, lambda_discount=lambda_discount)


def _max_route_weight(dependency: Mapping[int, Mapping[int, float]]) -> float:
    max_weight = 0.0
    for neighbors in dependency.values():
        for value in neighbors.values():
            max_weight = max(max_weight, float(value))
    return max_weight


def _propagate_two_hops(
    shares: Mapping[int, Mapping[int, float]],
    seeds: Mapping[int, float],
    *,
    lambda_discount: float,
) -> dict[int, dict[str, float | int]]:
    if lambda_discount < 0.0:
        raise ValueError("lambda_discount must be non-negative")

    hop1: Dict[int, float] = defaultdict(float)
    for seed_node, seed_value in seeds.items():
        for nbr, share in shares.get(int(seed_node), {}).items():
            hop1[int(nbr)] += float(seed_value) * float(share)

    hop2: Dict[int, float] = defaultdict(float)
    for mid, mid_exposure in hop1.items():
        for nbr, share in shares.get(int(mid), {}).items():
            hop2[int(nbr)] += lambda_discount * float(mid_exposure) * float(share)

    results: dict[int, dict[str, float | int]] = {}
    seed_nodes = {int(n) for n in seeds}
    all_nodes = set(hop1) | set(hop2)
    for node in sorted(all_nodes):
        if node in seed_nodes:
            # hop-0 seed nodes are tracked by scenario metadata, not exposure rows.
            continue
        e1 = float(hop1.get(node, 0.0))
        e2 = float(hop2.get(node, 0.0))
        total = e1 + e2
        if total <= 0.0:
            continue
        hop_level = 1 if e1 > 0.0 else 2
        results[int(node)] = {"exposure_score": total, "hop_level": hop_level}
    return results
