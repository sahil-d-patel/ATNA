"""Precomputed baseline inputs must not change any scenario result.

The batch scorer and the Streamlit app both hoist baseline-only quantities out of the
per-scenario path: undirected dependency weights, normalized neighbor shares, and the
baseline reachable-pair count. Those are pure caching optimizations, so every scenario
must produce byte-identical rows whether or not they are supplied. These tests pin that
guarantee so a future change to the caching path cannot silently move published scores.
"""

from __future__ import annotations

import networkx as nx
import pytest

from scenarios.engine import run_scenario
from scenarios.graph_edits import remove_airport, remove_route
from scenarios.ripple import build_dependency_weights, normalize_neighbor_shares
from scenarios.scoring import reachable_pairs_count

SNAPSHOT_ID = "2025-12"
# created_at is wall-clock; pin it so only computed values are compared.
FIXED_CREATED_AT = "1970-01-01T00:00:00Z"


def _baseline_inputs(graph: nx.DiGraph):
    dependency = build_dependency_weights(graph)
    return dependency, normalize_neighbor_shares(dependency), reachable_pairs_count(graph)


@pytest.mark.parametrize(
    ("scenario_type", "payload"),
    [
        ("airport_removal", {"airport_id": 2}),
        ("airport_removal", {"airport_id": 4}),
        ("route_removal", {"origin_id": 2, "destination_id": 3}),
        ("route_removal", {"origin_id": 3, "destination_id": 4}),
    ],
)
def test_precomputed_inputs_match_cold_path(fixture_graph, scenario_type, payload) -> None:
    dependency, shares, pre_pairs = _baseline_inputs(fixture_graph)

    cold_row, cold_exposure = run_scenario(
        fixture_graph,
        snapshot_id=SNAPSHOT_ID,
        scenario_type=scenario_type,
        payload=payload,
        created_at=FIXED_CREATED_AT,
    )
    warm_row, warm_exposure = run_scenario(
        fixture_graph,
        snapshot_id=SNAPSHOT_ID,
        scenario_type=scenario_type,
        payload=payload,
        created_at=FIXED_CREATED_AT,
        precomputed_shares=shares,
        precomputed_dependency=dependency,
        pre_reachable_pairs=pre_pairs,
    )

    assert cold_row == warm_row
    assert cold_exposure == warm_exposure


@pytest.mark.parametrize(
    ("scenario_type", "payload"),
    [
        ("airport_removal", {"airport_id": 2}),
        ("route_removal", {"origin_id": 2, "destination_id": 3}),
    ],
)
def test_scenario_never_mutates_the_baseline_graph(fixture_graph, scenario_type, payload) -> None:
    """The engine edits via read-only views, so the shared baseline must survive intact.

    The Streamlit app caches one baseline graph across reruns, so a mutating edit would
    corrupt every later scenario in the session.
    """
    nodes_before = sorted(fixture_graph.nodes())
    edges_before = sorted(fixture_graph.edges(data="weight"))

    run_scenario(
        fixture_graph,
        snapshot_id=SNAPSHOT_ID,
        scenario_type=scenario_type,
        payload=payload,
        created_at=FIXED_CREATED_AT,
    )

    assert sorted(fixture_graph.nodes()) == nodes_before
    assert sorted(fixture_graph.edges(data="weight")) == edges_before


def test_view_and_copy_edits_are_structurally_identical(fixture_graph) -> None:
    """``copy=False`` returns a view; it must read exactly like the detached copy."""
    copied, _ = remove_airport(fixture_graph, {"airport_id": 2}, copy=True)
    viewed, _ = remove_airport(fixture_graph, {"airport_id": 2}, copy=False)
    assert sorted(copied.nodes()) == sorted(viewed.nodes())
    assert sorted(copied.edges(data="weight")) == sorted(viewed.edges(data="weight"))

    copied, _ = remove_route(fixture_graph, {"origin_id": 2, "destination_id": 3}, copy=True)
    viewed, _ = remove_route(fixture_graph, {"origin_id": 2, "destination_id": 3}, copy=False)
    assert sorted(copied.nodes()) == sorted(viewed.nodes())
    assert sorted(copied.edges(data="weight")) == sorted(viewed.edges(data="weight"))


def test_copy_edit_stays_detached_from_baseline(fixture_graph) -> None:
    """``copy=True`` must still hand back a graph the caller can mutate safely."""
    edited, _ = remove_airport(fixture_graph, {"airport_id": 4}, copy=True)
    edited.add_node(99)
    assert not fixture_graph.has_node(99)
