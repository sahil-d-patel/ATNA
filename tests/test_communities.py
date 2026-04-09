from __future__ import annotations

from pathlib import Path

import pandas as pd
import networkx as nx
import pytest

from metrics.leiden_communities import build_communities_frame, compute_leiden_communities
from metrics.config import load_config
from metrics.run_metrics import run


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


def test_run_writes_communities_csv_and_ids_align(tmp_path: Path):
    """End-to-end smoke: writes metrics.csv and communities.csv with aligned community IDs."""
    cfg = load_config()
    nodes_path = cfg.processed_dir / "nodes.csv"
    edges_path = cfg.processed_dir / "edges.csv"
    if not nodes_path.is_file() or not edges_path.is_file():
        pytest.skip("processed nodes/edges missing for configured snapshot")

    # Write to temp locations to avoid clobbering real processed artifacts during tests.
    cfg2 = type(cfg)(
        snapshot_id=cfg.snapshot_id,
        repo_root=cfg.repo_root,
        config_path=cfg.config_path,
        raw_on_time=cfg.raw_on_time,
        raw_t100=cfg.raw_t100,
        raw_master_airport=cfg.raw_master_airport,
        processed_dir=cfg.processed_dir,
        edges_csv=cfg.edges_csv,
        metrics_csv=(tmp_path / "metrics.csv").resolve(),
        communities_csv=(tmp_path / "communities.csv").resolve(),
        route_metrics_csv=cfg.route_metrics_csv,
    )

    metrics_path = run(cfg2)
    assert metrics_path.is_file()
    assert cfg2.communities_csv.is_file()

    metrics_df = pd.read_csv(metrics_path)
    comm_df = pd.read_csv(cfg2.communities_csv)

    # §6.5 communities.csv column order contract.
    assert list(comm_df.columns) == [
        "snapshot_id",
        "leiden_community_id",
        "community_size",
        "community_traffic",
        "internal_density",
        "top_hub_airport_ids",
        "top_bridge_airport_ids",
    ]

    # Community IDs in communities.csv must match unique set in metrics.csv.
    metric_ids = set(
        pd.to_numeric(metrics_df["leiden_community_id"], errors="raise").astype(int).unique()
    )
    comm_ids = set(pd.to_numeric(comm_df["leiden_community_id"], errors="raise").astype(int).unique())
    assert comm_ids == metric_ids

