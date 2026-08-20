"""Removing several airports at once.

A correlated outage - a carrier collapse, a regional weather system - takes out a set
of airports, and the combined effect is not the sum of the individual effects. The
ripple model must seed all of them into one propagation so exposure accumulates where
they share neighbours.
"""

from __future__ import annotations

import networkx as nx
import pytest

from scenarios.engine import run_scenario
from scenarios.graph_edits import remove_airports
from scenarios.ripple import airport_removal_exposure, airport_set_removal_exposure

SNAPSHOT_ID = "2025-12"
FIXED_CREATED_AT = "1970-01-01T00:00:00Z"


def test_removes_every_named_airport(fixture_graph: nx.DiGraph) -> None:
    edited, metadata = remove_airports(fixture_graph, {"airport_ids": [2, 3]})
    assert sorted(edited.nodes()) == [1, 4]
    assert metadata.removed_airport_ids == (2, 3)


def test_view_and_copy_agree(fixture_graph: nx.DiGraph) -> None:
    copied, _ = remove_airports(fixture_graph, {"airport_ids": [2, 3]}, copy=True)
    viewed, _ = remove_airports(fixture_graph, {"airport_ids": [2, 3]}, copy=False)
    assert sorted(copied.nodes()) == sorted(viewed.nodes())
    assert sorted(copied.edges()) == sorted(viewed.edges())


def test_baseline_survives_a_set_removal(fixture_graph: nx.DiGraph) -> None:
    before = sorted(fixture_graph.nodes())
    run_scenario(
        fixture_graph, snapshot_id=SNAPSHOT_ID, scenario_type="airport_set_removal",
        payload={"airport_ids": [2, 3]}, created_at=FIXED_CREATED_AT,
    )
    assert sorted(fixture_graph.nodes()) == before


def test_a_single_element_set_matches_single_removal(fixture_graph: nx.DiGraph) -> None:
    """The set path must not diverge from the single path on a one-element set."""
    single = airport_removal_exposure(fixture_graph, removed_airport_id=2)
    as_set = airport_set_removal_exposure(fixture_graph, removed_airport_ids=[2])
    assert single == as_set


def test_combined_exposure_exceeds_either_alone(fixture_graph: nx.DiGraph) -> None:
    """Shared neighbours accumulate shock from both removals."""
    both = airport_set_removal_exposure(fixture_graph, removed_airport_ids=[1, 3])
    only_first = airport_removal_exposure(fixture_graph, removed_airport_id=1)
    only_third = airport_removal_exposure(fixture_graph, removed_airport_id=3)

    shared = set(only_first) & set(only_third) - {1, 3}
    assert shared, "fixture should have a neighbour common to both removals"
    for airport in shared:
        combined = both[airport]["exposure_score"]
        assert combined > only_first[airport]["exposure_score"]
        assert combined > only_third[airport]["exposure_score"]


def test_seed_airports_are_not_their_own_exposure_rows(fixture_graph: nx.DiGraph) -> None:
    exposure = airport_set_removal_exposure(fixture_graph, removed_airport_ids=[2, 3])
    assert 2 not in exposure
    assert 3 not in exposure


def test_empty_set_is_rejected(fixture_graph: nx.DiGraph) -> None:
    with pytest.raises(ValueError, match="at least one airport"):
        remove_airports(fixture_graph, {"airport_ids": []})


def test_repeated_airport_is_rejected(fixture_graph: nx.DiGraph) -> None:
    with pytest.raises(ValueError, match="must not repeat"):
        remove_airports(fixture_graph, {"airport_ids": [2, 2]})


def test_unknown_airport_is_named(fixture_graph: nx.DiGraph) -> None:
    with pytest.raises(ValueError, match="do not exist"):
        remove_airports(fixture_graph, {"airport_ids": [2, 999]})


def test_missing_key_is_rejected(fixture_graph: nx.DiGraph) -> None:
    with pytest.raises(KeyError, match="airport_ids"):
        remove_airports(fixture_graph, {"airport_id": 2})


def test_scenario_row_lists_every_removed_airport(fixture_graph: nx.DiGraph) -> None:
    row, _ = run_scenario(
        fixture_graph, snapshot_id=SNAPSHOT_ID, scenario_type="airport_set_removal",
        payload={"airport_ids": [2, 3]}, created_at=FIXED_CREATED_AT,
    )
    assert row["edited_airports"] == "[2,3]"
    assert row["scenario_type"] == "airport_set_removal"
