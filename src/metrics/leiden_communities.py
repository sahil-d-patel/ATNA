"""Leiden community detection + community rollups (METR-05, spec §6.5 and §7.9).

This module keeps NetworkX as the source of truth for the analysis graph, and converts
to igraph/leidenalg only for Leiden partitioning (spec §15.2).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import networkx as nx

@dataclass(frozen=True)
class LeidenParams:
    """Configuration for Leiden partitioning.

    Notes:
    - We use `leidenalg.RBConfigurationVertexPartition` by default.
    - `resolution_parameter` default 1.0 is leidenalg's standard default.
    - If the installed leidenalg supports `seed`, we pass it for basic repeatability.
    """

    resolution: float = 1.0
    seed: int | None = 0


def compute_leiden_communities(
    g: nx.DiGraph,
    *,
    params: LeidenParams | None = None,
) -> dict[int, int]:
    """Return mapping: airport_id -> leiden_community_id (0..K-1 stable relabel).

    Disconnected / isolated structure policy:
    - Run Leiden on the full directed graph; isolated nodes naturally become singleton
      communities via the partition membership output.
    """

    params = params or LeidenParams()

    ig, vertex_ids = _to_igraph_directed_weighted(g)
    membership = _run_leiden_membership(
        ig,
        resolution=params.resolution,
        seed=params.seed,
    )

    # Build initial communities keyed by raw membership integer.
    comm_to_nodes: dict[int, list[int]] = {}
    for vidx, raw_comm in enumerate(membership):
        comm_to_nodes.setdefault(int(raw_comm), []).append(int(vertex_ids[vidx]))

    # Stable relabel: sort communities by their smallest airport_id, then map to 0..K-1.
    comm_items = sorted(
        comm_to_nodes.items(),
        key=lambda kv: (min(kv[1]) if kv[1] else 2**63 - 1, kv[0]),
    )
    raw_to_stable = {raw: stable for stable, (raw, _) in enumerate(comm_items)}

    airport_to_comm: dict[int, int] = {}
    for raw_comm, nodes in comm_to_nodes.items():
        stable = raw_to_stable[int(raw_comm)]
        for aid in nodes:
            airport_to_comm[int(aid)] = int(stable)

    _assert_partition_covers_nodes_exactly_once(g, airport_to_comm)
    return airport_to_comm


def _assert_partition_covers_nodes_exactly_once(
    g: nx.DiGraph, airport_to_comm: dict[int, int]
) -> None:
    nodes = [int(n) for n in g.nodes()]
    missing = [n for n in nodes if int(n) not in airport_to_comm]
    if missing:
        raise ValueError(f"Leiden partition missing {len(missing)} node(s), e.g. {missing[:5]}")
    if len(set(airport_to_comm.keys())) != len(airport_to_comm):
        raise ValueError("airport_to_comm mapping has duplicate keys (unexpected)")
    if set(airport_to_comm.keys()) != set(nodes):
        # Catch extra keys too.
        extra = sorted(set(airport_to_comm.keys()) - set(nodes))
        raise ValueError(
            f"Leiden partition keys do not match graph nodes. Extra keys: {extra[:5]}"
        )


def _to_igraph_directed_weighted(g: nx.DiGraph):
    """Convert NetworkX DiGraph -> igraph Graph(directed) with 'weight' edge attribute."""
    try:
        import igraph as ig  # type: ignore
    except Exception as e:  # pragma: no cover
        raise ImportError(
            "python-igraph is required for Leiden communities (pip install python-igraph)."
        ) from e

    vertex_ids = [int(n) for n in g.nodes()]
    id_to_idx = {aid: idx for idx, aid in enumerate(vertex_ids)}

    edges: list[tuple[int, int]] = []
    weights: list[float] = []
    for u, v, d in g.edges(data=True):
        edges.append((id_to_idx[int(u)], id_to_idx[int(v)]))
        weights.append(float(d.get("weight", 0.0)))

    ig_g = ig.Graph(n=len(vertex_ids), edges=edges, directed=True)
    ig_g.es["weight"] = weights
    return ig_g, vertex_ids


def _run_leiden_membership(
    ig_g,
    *,
    resolution: float,
    seed: int | None,
) -> list[int]:
    try:
        import leidenalg  # type: ignore
    except Exception as e:  # pragma: no cover
        raise ImportError(
            "leidenalg is required for Leiden communities (pip install leidenalg)."
        ) from e

    # Prefer RBConfigurationVertexPartition because it supports directed graphs.
    part_cls = getattr(leidenalg, "RBConfigurationVertexPartition")

    kwargs = {
        "weights": ig_g.es["weight"],
        "resolution_parameter": float(resolution),
    }
    if seed is not None:
        kwargs["seed"] = int(seed)

    try:
        part = leidenalg.find_partition(ig_g, part_cls, **kwargs)
    except TypeError:
        # Older leidenalg may not accept seed kwarg.
        kwargs.pop("seed", None)
        part = leidenalg.find_partition(ig_g, part_cls, **kwargs)

    return [int(x) for x in part.membership]

