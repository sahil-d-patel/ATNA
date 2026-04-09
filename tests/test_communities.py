from __future__ import annotations

import pandas as pd
import networkx as nx

from metrics.leiden_communities import build_communities_frame, compute_leiden_communities


def test_leiden_partition_covers_all_nodes():
    # Skip if optional deps are not installed in the current environment.
    try:
        import igraph  # noqa: F401
        import leidenalg  # noqa: F401
    except Exception:
        return

    g = nx.DiGraph()
    g.add_edge(1, 2, weight=1.0)
    g.add_edge(2, 3, weight=1.0)
    g.add_node(4)  # isolated

    airport_to_comm = compute_leiden_communities(g)
    assert set(airport_to_comm.keys()) == {1, 2, 3, 4}
    assert all(isinstance(v, int) and v >= 0 for v in airport_to_comm.values())


def test_community_traffic_sum_on_two_node_internal_edge():
    # CommunityTraffic(C) = sum_{i,j in C} w(i,j) over directed edges with both ends in C.
    g = nx.DiGraph()
    g.add_edge(10, 20, weight=2.5)  # internal edge for community 0
    g.add_edge(20, 99, weight=9.0)  # cross-community, excluded
    g.add_node(99)

    airport_to_comm = {10: 0, 20: 0, 99: 1}
    metrics_df = pd.DataFrame(
        {
            "airport_id": [10, 20, 99],
            "hub_score": [1.0, 2.0, 3.0],
            "bridge_score": [3.0, 2.0, 1.0],
        }
    )

    comm = build_communities_frame(
        snapshot_id="2099-01",
        g=g,
        airport_to_comm=airport_to_comm,
        metrics_df=metrics_df,
        top_n=5,
    )

    c0 = comm[comm["leiden_community_id"] == 0].iloc[0]
    assert float(c0["community_traffic"]) == 2.5


def test_internal_density_handles_small_communities():
    g = nx.DiGraph()
    g.add_node(1)
    airport_to_comm = {1: 0}
    metrics_df = pd.DataFrame({"airport_id": [1], "hub_score": [0.0], "bridge_score": [0.0]})

    comm = build_communities_frame(
        snapshot_id="2099-01",
        g=g,
        airport_to_comm=airport_to_comm,
        metrics_df=metrics_df,
    )
    c0 = comm.iloc[0]
    assert int(c0["community_size"]) == 1
    assert float(c0["internal_density"]) == 0.0

