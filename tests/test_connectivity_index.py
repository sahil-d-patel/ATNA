"""The batch connectivity index must agree exactly with the NetworkX reference.

:class:`ConnectivityIndex` exists purely to make the vulnerability sweep cheaper. It
feeds the same two integers into the same scoring formulas, so any disagreement with
:mod:`scenarios.scoring` would move published artifact values. These tests compare the
two implementations across graph shapes chosen to stress the condensation path.
"""

from __future__ import annotations

import networkx as nx
import pytest

from scenarios.connectivity import ConnectivityIndex
from scenarios.scoring import (
    largest_component_traffic,
    node_strengths,
    weighted_reach,
)


def _reference_counts(graph: nx.DiGraph, removed: int) -> tuple[float, float]:
    """Measures from the reference implementation, via a read-only view."""
    view = nx.restricted_view(graph, [removed], [])
    strengths = node_strengths(graph)
    return (
        largest_component_traffic(view, strengths),
        weighted_reach(view, strengths),
    )


def _weighted(graph: nx.DiGraph, seed: int) -> nx.DiGraph:
    """Give every edge a distinct positive weight so the measure is actually exercised."""
    for offset, (source, target) in enumerate(graph.edges()):
        graph[source][target]["weight"] = 1.0 + ((seed + offset) % 7) * 0.75
    return graph


def _assert_index_matches_reference(graph: nx.DiGraph) -> None:
    index = ConnectivityIndex(graph)
    for node in graph.nodes():
        expected_lcc, expected_pairs = _reference_counts(graph, node)
        counts = index.without_airport(node)
        assert counts.lcc_size == pytest.approx(expected_lcc, rel=1e-9), (
            f"component traffic mismatch removing {node}"
        )
        assert counts.reachable_pairs == pytest.approx(expected_pairs, rel=1e-9), (
            f"weighted reach mismatch removing {node}"
        )


def test_matches_reference_on_the_shared_fixture(fixture_graph: nx.DiGraph) -> None:
    _assert_index_matches_reference(fixture_graph)


@pytest.mark.parametrize(
    ("order", "probability", "seed"),
    [
        (12, 0.10, 1),   # sparse: many single-node components
        (18, 0.18, 2),   # mixed: several strongly connected components
        (25, 0.35, 3),   # dense: usually one giant component
        (30, 0.55, 4),   # very dense: strongly connected throughout
        (9, 0.05, 5),    # near-empty: almost every node isolated
    ],
)
def test_matches_reference_on_random_digraphs(order: int, probability: float, seed: int) -> None:
    graph = _weighted(nx.DiGraph(nx.gnp_random_graph(order, probability, seed=seed, directed=True)), seed)
    _assert_index_matches_reference(graph)


def test_matches_reference_with_isolated_nodes() -> None:
    """Isolated airports appear in nodes.csv, so the index must handle them."""
    graph = _weighted(nx.DiGraph(nx.gnp_random_graph(10, 0.25, seed=7, directed=True)), 7)
    graph.add_nodes_from([90, 91, 92])
    _assert_index_matches_reference(graph)


def test_matches_reference_on_a_disconnected_pair_of_cycles() -> None:
    """Two components that never reach each other: the condensation path must hold."""
    graph = nx.DiGraph()
    nx.add_cycle(graph, [1, 2, 3])
    nx.add_cycle(graph, [10, 11, 12])
    graph = _weighted(graph, 3)
    _assert_index_matches_reference(graph)


def test_matches_reference_on_a_directed_chain() -> None:
    """A pure chain is the worst case: every node is its own component."""
    graph = nx.DiGraph()
    nx.add_path(graph, range(8))
    graph = _weighted(graph, 8)
    _assert_index_matches_reference(graph)


def test_single_node_graph_reports_empty_remainder() -> None:
    graph = nx.DiGraph()
    graph.add_node(5)
    counts = ConnectivityIndex(graph).without_airport(5)
    assert counts.lcc_size == 0.0
    assert counts.reachable_pairs == 0.0


def test_unknown_airport_is_rejected(fixture_graph: nx.DiGraph) -> None:
    with pytest.raises(ValueError, match="not present in the index"):
        ConnectivityIndex(fixture_graph).without_airport(9999)
