from __future__ import annotations

import math

import networkx as nx

from scenarios.graph_edits import remove_airport
from scenarios.ripple import airport_removal_exposure
from scenarios.scoring import aggregate_scenario_scores, reachability_loss


def test_hop2_discounted_and_weaker_than_hop1(fixture_graph: nx.DiGraph) -> None:
    exposure = airport_removal_exposure(fixture_graph, removed_airport_id=1)

    # Node 2 gets direct hop-1 effect from node 1; node 3 only via hop-2 path.
    assert exposure[2]["hop_level"] == 1
    assert exposure[3]["hop_level"] == 2
    assert float(exposure[3]["exposure_score"]) < float(exposure[2]["exposure_score"])


def test_ripple_never_exceeds_two_hops(fixture_graph: nx.DiGraph) -> None:
    exposure = airport_removal_exposure(fixture_graph, removed_airport_id=1)
    assert exposure
    assert all(int(payload["hop_level"]) <= 2 for payload in exposure.values())


def test_reachability_loss_zero_when_pre_denominator_zero() -> None:
    pre = nx.DiGraph()
    pre.add_nodes_from([1, 2, 3])  # no edges => zero reachable ordered pairs
    post = nx.DiGraph()
    post.add_nodes_from([1, 2, 3])
    assert reachability_loss(pre, post) == 0.0


def test_larger_disruption_higher_impact_and_lower_health(fixture_graph: nx.DiGraph) -> None:
    baseline = fixture_graph
    total_airports = baseline.number_of_nodes()

    # Both scenarios are genuine airport removals so the post-graph edit and the
    # ripple exposure describe the SAME disruption. Mild removes a peripheral leaf
    # airport (node 4); severe removes a central hub airport (node 2).
    mild_post, _ = remove_airport(baseline, {"airport_id": 4}, snapshot_id="2025-12")
    mild_exposure = airport_removal_exposure(baseline, removed_airport_id=4)

    severe_post, _ = remove_airport(baseline, {"airport_id": 2}, snapshot_id="2025-12")
    severe_exposure = airport_removal_exposure(baseline, removed_airport_id=2)

    mild = aggregate_scenario_scores(
        pre_graph=baseline,
        post_graph=mild_post,
        exposure_by_airport=mild_exposure,
        total_airports=total_airports,
    )
    severe = aggregate_scenario_scores(
        pre_graph=baseline,
        post_graph=severe_post,
        exposure_by_airport=severe_exposure,
        total_airports=total_airports,
    )

    assert severe["impact_score"] > mild["impact_score"]
    assert severe["network_health"] < mild["network_health"]
    for value in (*mild.values(), *severe.values()):
        assert math.isfinite(value)
