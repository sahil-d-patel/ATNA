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
    largest_weakly_connected_component_size,
    reachable_pairs_count,
)


def _reference_counts(graph: nx.DiGraph, removed: int) -> tuple[int, int]:
    """Counts from the reference implementation, via a read-only view."""
    view = nx.restricted_view(graph, [removed], [])
    return largest_weakly_connected_component_size(view), reachable_pairs_count(view)


def _assert_index_matches_reference(graph: nx.DiGraph) -> None:
    index = ConnectivityIndex(graph)
    for node in graph.nodes():
        expected_lcc, expected_pairs = _reference_counts(graph, node)
        counts = index.without_airport(node)
        assert counts.lcc_size == expected_lcc, f"LCC mismatch removing {node}"
        assert counts.reachable_pairs == expected_pairs, f"pairs mismatch removing {node}"


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
    graph = nx.DiGraph(nx.gnp_random_graph(order, probability, seed=seed, directed=True))
    _assert_index_matches_reference(graph)


def test_matches_reference_with_isolated_nodes() -> None:
    """Isolated airports appear in nodes.csv, so the index must handle them."""
    graph = nx.DiGraph(nx.gnp_random_graph(10, 0.25, seed=7, directed=True))
    graph.add_nodes_from([90, 91, 92])
    _assert_index_matches_reference(graph)


def test_matches_reference_on_a_disconnected_pair_of_cycles() -> None:
    """Two components that never reach each other: the condensation path must hold."""
    graph = nx.DiGraph()
    nx.add_cycle(graph, [1, 2, 3])
    nx.add_cycle(graph, [10, 11, 12])
    _assert_index_matches_reference(graph)


def test_matches_reference_on_a_directed_chain() -> None:
    """A pure chain is the worst case: every node is its own component."""
    graph = nx.DiGraph()
    nx.add_path(graph, range(8))
    _assert_index_matches_reference(graph)


def test_single_node_graph_reports_empty_remainder() -> None:
    graph = nx.DiGraph()
    graph.add_node(5)
    counts = ConnectivityIndex(graph).without_airport(5)
    assert counts.lcc_size == 0
    assert counts.reachable_pairs == 0


def test_unknown_airport_is_rejected(fixture_graph: nx.DiGraph) -> None:
    with pytest.raises(ValueError, match="not present in the index"):
        ConnectivityIndex(fixture_graph).without_airport(9999)
