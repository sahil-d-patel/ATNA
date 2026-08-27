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


def _inverse_distances(G: nx.DiGraph) -> list[float]:
    """Edge distances for betweenness: ``1 / weight``, validated.

    Shortest-path algorithms treat weight as additive cost, but ``analysis_weight``
    measures capacity: a heavily trafficked route is structurally *closer*. Inverting
    is what makes betweenness answer the bridge question rather than its opposite.
    """
    distances = []
    for u, v, data in G.edges(data=True):
        weight = float(data.get("weight", 0.0))
        if weight <= 0 or not np.isfinite(weight):
            raise ValueError(f"edge ({u}, {v}) needs finite positive weight for betweenness")
        distances.append(1.0 / weight)
    return distances


def _betweenness_reference(G: nx.DiGraph) -> pd.Series:
    """Betweenness via NetworkX. Kept as the reference the fast path is tested against."""
    graph = nx.DiGraph()
    graph.add_nodes_from(G.nodes())
    for (u, v), distance in zip(G.edges(), _inverse_distances(G), strict=True):
        graph.add_edge(u, v, weight=distance)
    return pd.Series(
        nx.betweenness_centrality(graph, weight="weight", normalized=True), dtype=float
    ).sort_index()


def compute_betweenness(G: nx.DiGraph) -> pd.Series:
    """Betweenness on shortest paths where **distance** = ``1 / weight`` (spec §7.4).

    Computed through igraph, which is already a dependency for Leiden partitioning
    (spec §15.2) and implements Brandes in C. NetworkX runs the same algorithm in pure
    Python and was the largest single cost in the metrics stage: on a real 348-airport
    snapshot, 0.365s against 0.010s here, for output identical to the last bit.

    :func:`_betweenness_reference` retains the NetworkX path, and
    ``tests/test_centralities.py`` pins the two together.

    **On exactness.** The two agree bit for bit whenever shortest paths are unique.
    They can disagree by around 1e-3 on graphs where many paths tie, because Brandes
    splits credit among tied shortest paths and the two implementations accumulate
    that split in different orders; neither answer is more correct than the other.

    This does not affect real snapshots. ``analysis_weight`` is ``log1p(flight_count)``,
    which yields hundreds of distinct edge distances, and both November and December
    2022 produce a maximum difference of exactly zero. Degenerate ties need weights
    drawn from a handful of values, which real traffic counts do not produce.
    """
    order = G.number_of_nodes()
    if order == 0:
        return pd.Series(dtype=float)

    distances = _inverse_distances(G)

    # Betweenness counts paths *through* a node, so fewer than three nodes leaves no
    # intermediate position to occupy, and the normalisation below divides by zero.
    if order < 3:
        return pd.Series(0.0, index=sorted(G.nodes()), dtype=float)

    try:
        import igraph
    except ImportError:  # pragma: no cover - igraph is a pinned dependency
        logger.warning("python-igraph unavailable; falling back to the NetworkX path.")
        return _betweenness_reference(G)

    nodes = list(G.nodes())
    position = {node: index for index, node in enumerate(nodes)}
    graph = igraph.Graph(
        n=len(nodes),
        edges=[(position[u], position[v]) for u, v in G.edges()],
        directed=True,
    )
    raw = graph.betweenness(weights=distances, directed=True)

    # igraph returns unnormalised path counts; NetworkX's normalized=True divides a
    # directed graph by (n-1)(n-2).
    scale = 1.0 / ((order - 1) * (order - 2))
    return pd.Series(
        {node: raw[position[node]] * scale for node in nodes}, dtype=float
    ).sort_index()


def compute_eigenvector(G: nx.DiGraph) -> pd.Series:
    """Eigenvector centrality, restricted to the largest strongly connected component.

    Eigenvector centrality is only well defined on a strongly connected graph: outside
    one, the dominant eigenvector concentrates on whichever terminal component the
    power iteration happens to reach, and the resulting values are not comparable.

    Rather than abandoning the whole column when the snapshot is not strongly
    connected, the score is computed on the largest strongly connected component and
    left undefined outside it. That component holds nearly every airport on a real
    snapshot, so an airport that could carry a meaningful value gets one; an airport
    that genuinely cannot is ``NaN`` rather than a number that would not mean what it
    appears to mean.

    The restriction is reported, since a reader comparing two snapshots needs to know
    that the population changed.
    """
    nodes = sorted(G.nodes())
    if not nodes:
        return pd.Series(dtype=float)

    target: nx.DiGraph = G
    if not nx.is_strongly_connected(G):
        largest = max(nx.strongly_connected_components(G), key=len)
        if len(largest) < 2:
            logger.warning(
                "eigenvector centrality is undefined for this snapshot: the largest "
                "strongly connected component holds %d airport(s), so the column is "
                "empty.",
                len(largest),
            )
            return pd.Series(np.nan, index=nodes, dtype=float)
        logger.info(
            "graph is not strongly connected; eigenvector centrality computed on the "
            "largest strongly connected component (%d of %d airports), and left "
            "undefined for the remaining %d.",
            len(largest), len(nodes), len(nodes) - len(largest),
        )
        target = G.subgraph(largest)

    try:
        centrality = _eigenvector_centrality_deterministic(target, weight="weight")
    except Exception as exc:
        logger.warning(
            "eigenvector centrality did not converge for this snapshot (%s); the "
            "column will be empty.",
            exc,
        )
        return pd.Series(np.nan, index=nodes, dtype=float)

    # Airports outside the component keep NaN through the reindex.
    return pd.Series(centrality, dtype=float).reindex(nodes)
