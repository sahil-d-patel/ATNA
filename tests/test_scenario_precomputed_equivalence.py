"""Precomputed baseline inputs must not change any scenario result.

The batch scorer and the Streamlit app both hoist baseline-only quantities out of the
per-scenario path: undirected dependency weights, normalized neighbor shares, and the
baseline reachable-pair count. Those are pure caching optimizations, so every scenario
must produce byte-identical rows whether or not they are supplied. These tests pin that
guarantee so a future change to the caching path cannot silently move published scores.
"""

from __future__ import annotations

import networkx as nx
import pandas as pd
import pytest

from metrics.percentile import percentile_rank_0_100
from scenarios.connectivity import ConnectivityIndex
from scenarios.engine import run_scenario
from scenarios.graph_edits import remove_airport, remove_route
from scenarios.ripple import build_dependency_weights, normalize_neighbor_shares
from scenarios.scoring import node_strengths, weighted_reach
from scenarios.vulnerability import build_vulnerability_scores

SNAPSHOT_ID = "2025-12"
# created_at is wall-clock; pin it so only computed values are compared.
FIXED_CREATED_AT = "1970-01-01T00:00:00Z"


def _baseline_inputs(graph: nx.DiGraph):
    dependency = build_dependency_weights(graph)
    strengths = node_strengths(graph)
    return (
        dependency,
        normalize_neighbor_shares(dependency),
        strengths,
        weighted_reach(graph, strengths),
    )


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
    dependency, shares, strengths, pre_pairs = _baseline_inputs(fixture_graph)

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
        strengths=strengths,
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


@pytest.mark.parametrize("airport_id", [1, 2, 3, 4])
def test_post_connectivity_matches_measuring_the_edited_graph(fixture_graph, airport_id) -> None:
    """Index-derived post-removal counts must not move any score.

    The batch scorer supplies these counts instead of measuring each edited graph. That
    is only sound if the two agree exactly, since both feed the same locked formulas.
    """
    _, shares, strengths, pre_pairs = _baseline_inputs(fixture_graph)
    counts = ConnectivityIndex(fixture_graph).without_airport(airport_id)

    measured_row, measured_exposure = run_scenario(
        fixture_graph,
        snapshot_id=SNAPSHOT_ID,
        scenario_type="airport_removal",
        payload={"airport_id": airport_id},
        created_at=FIXED_CREATED_AT,
        precomputed_shares=shares,
        strengths=strengths,
        pre_reachable_pairs=pre_pairs,
    )
    indexed_row, indexed_exposure = run_scenario(
        fixture_graph,
        snapshot_id=SNAPSHOT_ID,
        scenario_type="airport_removal",
        payload={"airport_id": airport_id},
        created_at=FIXED_CREATED_AT,
        precomputed_shares=shares,
        strengths=strengths,
        pre_reachable_pairs=pre_pairs,
        post_connectivity=counts,
    )

    assert measured_row == indexed_row
    assert measured_exposure == indexed_exposure


def test_vulnerability_batch_is_unchanged_by_the_index(fixture_graph) -> None:
    """End-to-end guard on the artifact column the batch actually produces."""
    metrics = pd.DataFrame(
        {
            "snapshot_id": [SNAPSHOT_ID] * 4,
            "airport_id": [1, 2, 3, 4],
            "bridge_score": [25.0, 100.0, 75.0, 50.0],
        }
    )
    scores = build_vulnerability_scores(
        snapshot_id=SNAPSHOT_ID, baseline_graph=fixture_graph, metrics_df=metrics
    )

    # Recompute each impact the slow way and rebuild the blend independently.
    expected_impacts = []
    for airport_id in [1, 2, 3, 4]:
        row, _ = run_scenario(
            fixture_graph,
            snapshot_id=SNAPSHOT_ID,
            scenario_type="airport_removal",
            payload={"airport_id": airport_id},
            created_at=FIXED_CREATED_AT,
        )
        expected_impacts.append(row["impact_score"])

    expected = (
        0.60 * percentile_rank_0_100(pd.Series(expected_impacts))
        + 0.40 * percentile_rank_0_100(metrics["bridge_score"])
    )
    assert scores["vulnerability_score"].tolist() == pytest.approx(expected.tolist())
