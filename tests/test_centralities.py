from __future__ import annotations

import networkx as nx
import numpy as np
import pandas as pd
import pytest

from metrics.centralities import (
    compute_betweenness,
    compute_eigenvector,
    compute_pagerank,
)
from metrics.percentile import percentile_rank_0_100


def test_percentile_monotone_non_decreasing():
    s = pd.Series([0.0, 1.0, 2.0, 3.0], index=[10, 11, 12, 13])
    p = percentile_rank_0_100(s)
    assert list(p.index) == [10, 11, 12, 13]
    assert np.all(np.diff(p.to_numpy()) >= 0)
    assert p.iloc[-1] == 100.0


def test_percentile_small_set_with_ties_max_rule():
    # Values: [0, 0, 2, 10] with method="max" ranks -> [2, 2, 3, 4] out of 4.
    s = pd.Series([0.0, 0.0, 2.0, 10.0], index=[1, 2, 3, 4])
    p = percentile_rank_0_100(s)
    expected = pd.Series([50.0, 50.0, 75.0, 100.0], index=[1, 2, 3, 4])
    np.testing.assert_allclose(p.to_numpy(), expected.to_numpy(), rtol=0, atol=1e-12)


def _toy_digraph() -> nx.DiGraph:
    """3-node directed weighted triangle: 0->1->2->0."""
    g = nx.DiGraph()
    g.add_edge(0, 1, weight=1.0)
    g.add_edge(1, 2, weight=2.0)
    g.add_edge(2, 0, weight=1.0)
    return g


def test_pagerank_toy_sum_normalizes():
    g = _toy_digraph()
    pr = compute_pagerank(g)
    assert set(pr.index) == {0, 1, 2}
    assert np.isclose(pr.sum(), 1.0, atol=1e-9)


def test_betweenness_toy_finite():
    g = _toy_digraph()
    bc = compute_betweenness(g)
    assert np.all(np.isfinite(bc.to_numpy()))


def test_eigenvector_toy_no_exception():
    g = _toy_digraph()
    ev = compute_eigenvector(g)
    assert len(ev) == 3


def test_optional_real_snapshot_graph():
    from metrics.graph_builder import build_analysis_graph, load_edges

    try:
        edges = load_edges()
    except (FileNotFoundError, ValueError) as exc:
        pytest.skip(f"processed edges unavailable for configured snapshot: {exc}")
    g = build_analysis_graph(edges)
    pr = compute_pagerank(g)
    bc = compute_betweenness(g)
    assert pr.notna().all()
    assert bc.notna().all()
    assert np.isfinite(pr.sum())
    _ = compute_eigenvector(g)



def test_eigenvector_is_bitwise_reproducible_across_calls():
    """Repeated calls on the same graph must return bit-identical values.

    NetworkX computes eigenvector centrality through ARPACK without pinning the
    starting residual vector, so successive runs differed in the last few ulps. That
    was enough to make metrics.csv fail to reproduce byte for byte over identical
    inputs, which defeats the point of a frozen snapshot.
    """
    graph = _toy_digraph()
    first = compute_eigenvector(graph)
    for _ in range(4):
        repeat = compute_eigenvector(graph)
        assert list(repeat.index) == list(first.index)
        # Exact equality, not approximate: reproducibility is the property under test.
        assert repeat.to_numpy().tolist() == first.to_numpy().tolist()


def test_eigenvector_matches_networkx_reference():
    """The pinned start vector must not change the answer, only its stability."""
    graph = _toy_digraph()
    if not nx.is_strongly_connected(graph):
        pytest.skip("reference implementation rejects graphs that are not strongly connected")

    reference = pd.Series(nx.eigenvector_centrality_numpy(graph, weight="weight"), dtype=float)
    ours = compute_eigenvector(graph)
    np.testing.assert_allclose(
        ours.reindex(sorted(graph.nodes())).to_numpy(),
        reference.reindex(sorted(graph.nodes())).to_numpy(),
        atol=1e-12,
    )


def test_eigenvector_restricts_to_the_largest_strong_component():
    """Airports that can carry a value get one; the rest are left undefined.

    Eigenvector centrality is meaningful only inside a strongly connected component,
    so abandoning the whole column costs every airport that sits in the giant one.
    """
    graph = nx.DiGraph()
    nx.add_cycle(graph, [1, 2, 3, 4, 5])
    for source, target in list(graph.edges()):
        graph[source][target]["weight"] = 1.0
    graph.add_edge(5, 99, weight=1.0)  # reachable, but never returns

    result = compute_eigenvector(graph)
    assert result.loc[[1, 2, 3, 4, 5]].notna().all(), "the giant component must be scored"
    assert pd.isna(result.loc[99]), "a node outside the component has no defined value"


def test_eigenvector_is_empty_when_no_component_qualifies():
    """A graph with no cycle has no component larger than one airport."""
    graph = nx.DiGraph()
    graph.add_edge(1, 2, weight=1.0)  # no path back from 2 to 1
    result = compute_eigenvector(graph)
    assert list(result.index) == [1, 2]
    assert result.isna().all()
