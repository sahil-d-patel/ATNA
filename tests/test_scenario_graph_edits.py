from __future__ import annotations

import networkx as nx
import pytest

from scenarios.graph_edits import remove_airport, remove_route


def _make_graph() -> nx.DiGraph:
    g = nx.DiGraph()
    g.add_edge(1, 2, weight=1.0)
    g.add_edge(2, 3, weight=2.0)
    g.add_edge(3, 1, weight=3.0)
    g.add_edge(1, 3, weight=4.0)
    return g


def test_remove_airport_drops_node_and_incident_edges_only_in_copy() -> None:
    baseline = _make_graph()
    baseline_nodes = baseline.number_of_nodes()
    baseline_edges = baseline.number_of_edges()

    edited, metadata = remove_airport(
        baseline, {"airport_id": 2}, snapshot_id="2025-12"
    )

    assert edited is not baseline
    assert not edited.has_node(2)
    assert edited.number_of_nodes() == baseline_nodes - 1
    # Removed 1->2 and 2->3 only.
    assert edited.number_of_edges() == baseline_edges - 2
    assert metadata.scenario_type.value == "airport_removal"
    assert metadata.snapshot_id == "2025-12"
    assert metadata.removed_airport_id == 2
    assert baseline.has_node(2)
    assert baseline.number_of_nodes() == baseline_nodes
    assert baseline.number_of_edges() == baseline_edges


def test_remove_route_drops_only_targeted_directed_edge() -> None:
    baseline = _make_graph()
    baseline_nodes = baseline.number_of_nodes()
    baseline_edges = baseline.number_of_edges()

    edited, metadata = remove_route(
        baseline, {"origin_id": 1, "destination_id": 3}, snapshot_id="2025-12"
    )

    assert edited is not baseline
    assert not edited.has_edge(1, 3)
    assert edited.has_edge(3, 1)  # reverse edge remains
    assert edited.number_of_nodes() == baseline_nodes
    assert edited.number_of_edges() == baseline_edges - 1
    assert metadata.scenario_type.value == "route_removal"
    assert metadata.removed_origin_id == 1
    assert metadata.removed_destination_id == 3
    assert baseline.has_edge(1, 3)
    assert baseline.number_of_nodes() == baseline_nodes
    assert baseline.number_of_edges() == baseline_edges


def test_invalid_payloads_raise_clear_exceptions() -> None:
    baseline = _make_graph()

    with pytest.raises(KeyError, match="airport_id"):
        remove_airport(baseline, {})
    with pytest.raises(TypeError, match="airport_id must be an integer"):
        remove_airport(baseline, {"airport_id": "2"})
    with pytest.raises(ValueError, match="does not exist"):
        remove_airport(baseline, {"airport_id": 999})

    with pytest.raises(KeyError, match="missing required key"):
        remove_route(baseline, {"origin_id": 1})
    with pytest.raises(TypeError, match="must be integers"):
        remove_route(baseline, {"origin_id": 1, "destination_id": "3"})
    with pytest.raises(ValueError, match="must be different airports"):
        remove_route(baseline, {"origin_id": 1, "destination_id": 1})
    with pytest.raises(ValueError, match="does not exist"):
        remove_route(baseline, {"origin_id": 8, "destination_id": 9})
