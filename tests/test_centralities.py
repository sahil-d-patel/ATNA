from __future__ import annotations

import numpy as np
import pandas as pd
import networkx as nx

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
    except Exception:
        return
    g = build_analysis_graph(edges)
    pr = compute_pagerank(g)
    bc = compute_betweenness(g)
    assert pr.notna().all()
    assert bc.notna().all()
    assert np.isfinite(pr.sum())
    _ = compute_eigenvector(g)

