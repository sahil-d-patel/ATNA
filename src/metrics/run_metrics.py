"""Compute Phase 2 metrics artifacts (metrics.csv baseline)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import networkx as nx

from metrics.centralities import compute_betweenness, compute_eigenvector, compute_pagerank
from metrics.config import MetricsConfig, load_config
from metrics.graph_builder import build_analysis_graph, load_edges
from metrics.hub_bridge import add_hub_bridge_scores
from metrics.leiden_communities import build_communities_frame, compute_leiden_communities
from metrics.route_criticality import build_route_metrics_frame, write_route_metrics_csv
from metrics.tables import assert_metr02_nodes_match_graph, load_nodes


_METRICS_COL_ORDER = [
    "snapshot_id",
    "airport_id",
    "pagerank",
    "betweenness",
    "eigenvector",
    "hub_score",
    "bridge_score",
    "vulnerability_score",
    "leiden_community_id",
]


def build_metrics_frame(cfg: MetricsConfig, *, g: "nx.DiGraph | None" = None) -> pd.DataFrame:
    """Compute per-airport metrics (includes Leiden communities, METR-05)."""
    nodes = load_nodes(cfg)
    edges = load_edges(cfg)

    if g is None:
        g = build_analysis_graph(edges)
        # Ensure the universe includes all airports in nodes.csv (including isolated nodes).
        g.add_nodes_from(nodes["airport_id"].astype(int).tolist())

    assert_metr02_nodes_match_graph(g, nodes)

    pr = compute_pagerank(g)
    bc = compute_betweenness(g)
    ev = compute_eigenvector(g)

    base = pd.DataFrame(
        {
            "snapshot_id": cfg.snapshot_id,
            "airport_id": nodes["airport_id"].astype(int),
            "strength_total": nodes["strength_total"].astype(float),
            "degree_total": nodes["degree_total"].astype(int),
        }
    )

    base = base.merge(pr.rename("pagerank"), left_on="airport_id", right_index=True, how="left")
    base = base.merge(
        bc.rename("betweenness"), left_on="airport_id", right_index=True, how="left"
    )
    base = base.merge(
        ev.rename("eigenvector"), left_on="airport_id", right_index=True, how="left"
    )

    # Missing centralities for isolated nodes should be zeros (not NaN) for percentile scaling.
    base["pagerank"] = base["pagerank"].fillna(0.0).astype(float)
    base["betweenness"] = base["betweenness"].fillna(0.0).astype(float)
    # eigenvector may be all-NaN by spec; keep as-is.

    scored = add_hub_bridge_scores(
        base[
            [
                "airport_id",
                "pagerank",
                "betweenness",
                "strength_total",
                "degree_total",
            ]
        ]
        .copy()
    )

    out = base.merge(scored[["airport_id", "hub_score", "bridge_score"]], on="airport_id", how="left")

    out["vulnerability_score"] = np.nan

    airport_to_comm = compute_leiden_communities(g)
    out["leiden_community_id"] = out["airport_id"].map(airport_to_comm).astype(int)

    out = out[_METRICS_COL_ORDER].copy()
    out["snapshot_id"] = out["snapshot_id"].astype(str)
    out["airport_id"] = out["airport_id"].astype(int)
    out["leiden_community_id"] = out["leiden_community_id"].astype(int)
    return out


def write_metrics_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_communities_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def run(cfg_or_path: MetricsConfig | Path | str | None = None) -> Path:
    cfg = cfg_or_path if isinstance(cfg_or_path, MetricsConfig) else load_config(cfg_or_path)

    # Rebuild graph once for both metrics and community rollups to guarantee ID alignment.
    nodes = load_nodes(cfg)
    edges = load_edges(cfg)
    g = build_analysis_graph(edges)
    g.add_nodes_from(nodes["airport_id"].astype(int).tolist())

    # Metrics frame (pagerank, betweenness, hub/bridge, etc.)
    df = build_metrics_frame(cfg, g=g)
    write_metrics_csv(df, cfg.metrics_csv)

    # communities.csv rollup (spec §6.5 / §7.9)
    airport_to_comm = dict(zip(df["airport_id"].astype(int), df["leiden_community_id"].astype(int)))
    comm = build_communities_frame(
        snapshot_id=cfg.snapshot_id,
        g=g,
        airport_to_comm=airport_to_comm,
        metrics_df=df,
        top_n=5,
    )
    write_communities_csv(comm, cfg.communities_csv)

    # route_metrics.csv (spec §6.6 / §7.10) — uses same snapshot edges + Leiden IDs from metrics.
    routes = build_route_metrics_frame(cfg, edges_df=edges, metrics_df=df)
    write_route_metrics_csv(routes, cfg.route_metrics_csv)
    return cfg.metrics_csv


if __name__ == "__main__":
    out = run()
    print(out)

