"""Centrality metrics on the analysis DiGraph (spec §7.4)."""

from __future__ import annotations

import logging

import networkx as nx
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def compute_pagerank(G: nx.DiGraph) -> pd.Series:
    """Directed **PageRank** using edge ``weight`` (analysis_weight)."""
    if G.number_of_nodes() == 0:
        return pd.Series(dtype=float)
    pr = nx.pagerank(G, weight="weight")
    return pd.Series(pr, dtype=float).sort_index()


def compute_betweenness(G: nx.DiGraph) -> pd.Series:
    """Betweenness on shortest paths where **distance** = ``1 / weight``.

    NetworkX treats ``weight`` as additive distance; higher ``analysis_weight`` means
    stronger capacity, so we map to distance inversely (same pattern as bridge-style
    structural analysis on flow-like weights).
    """
    if G.number_of_nodes() == 0:
        return pd.Series(dtype=float)
    H = nx.DiGraph()
    H.add_nodes_from(G.nodes())
    for u, v, data in G.edges(data=True):
        w = float(data.get("weight", 0.0))
        if w <= 0 or not np.isfinite(w):
            raise ValueError(f"edge ({u}, {v}) needs finite positive weight for betweenness")
        H.add_edge(u, v, weight=1.0 / w)
    bc = nx.betweenness_centrality(H, weight="weight", normalized=True)
    return pd.Series(bc, dtype=float).sort_index()


def compute_eigenvector(G: nx.DiGraph) -> pd.Series:
    """Eigenvector centrality when numerically stable; else all-NaN (spec §7.4)."""
    nodes = sorted(G.nodes())
    if not nodes:
        return pd.Series(dtype=float)
    try:
        ec = nx.eigenvector_centrality_numpy(G, weight="weight")
        return pd.Series(ec, dtype=float).reindex(nodes)
    except Exception as exc:  # noqa: BLE001 — spec: never crash; return NaNs
        logger.debug("eigenvector_centrality_numpy failed: %s", exc)
        return pd.Series(np.nan, index=nodes, dtype=float)
