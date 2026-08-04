"""Centrality metrics on the analysis DiGraph (spec §7.4)."""

from __future__ import annotations

import logging

import networkx as nx
import numpy as np
import pandas as pd
import scipy.linalg
import scipy.sparse.linalg

logger = logging.getLogger(__name__)


def _eigenvector_centrality_deterministic(
    G: nx.DiGraph, *, weight: str = "weight", max_iter: int = 50, tol: float = 0.0
) -> dict[int, float]:
    """``nx.eigenvector_centrality_numpy`` with a pinned ARPACK start vector.

    NetworkX calls ``scipy.sparse.linalg.eigs`` without ``v0``, so ARPACK chooses a
    random starting residual and successive runs disagree in the last few units in the
    last place. That was enough to make ``metrics.csv`` fail to reproduce byte for byte
    between two runs over identical inputs, which undermines the snapshot model.

    Fixing ``v0`` to a constant vector makes the result deterministic. The mathematics
    is otherwise identical to the NetworkX implementation, including the sign and norm
    convention applied to the recovered eigenvector.
    """
    if len(G) == 0:
        raise nx.NetworkXPointlessConcept("cannot compute centrality for the null graph")
    if not nx.is_strongly_connected(G):
        raise nx.AmbiguousSolution(
            "eigenvector centrality is not well defined for a graph that is not "
            "strongly connected"
        )

    nodelist = list(G)
    matrix = nx.to_scipy_sparse_array(G, nodelist=nodelist, weight=weight, dtype=float)
    _, eigenvector = scipy.sparse.linalg.eigs(
        matrix.T,
        k=1,
        which="LR",
        maxiter=max_iter,
        tol=tol,
        v0=np.ones(matrix.shape[0], dtype=float),
    )
    largest = eigenvector.flatten().real
    norm = float(np.sign(largest.sum()) * scipy.linalg.norm(largest))
    return dict(zip(nodelist, (largest / norm).tolist(), strict=True))


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
        ec = _eigenvector_centrality_deterministic(G, weight="weight")
        return pd.Series(ec, dtype=float).reindex(nodes)
    except Exception as exc:
        # Spec §7.4 keeps eigenvector as a secondary metric and tolerates an all-NaN
        # column, but a silent debug line makes an entirely empty column in metrics.csv
        # look like a data problem. Warn so the cause is visible in pipeline output.
        logger.warning(
            "eigenvector centrality unavailable for this snapshot (%s); "
            "the eigenvector column will be empty. This is expected when the directed "
            "graph is not strongly connected.",
            exc,
        )
        return pd.Series(np.nan, index=nodes, dtype=float)
