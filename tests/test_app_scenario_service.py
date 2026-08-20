"""The application's bridge between UI input and the scenario engine.

Everything reaching the engine from the interface passes through here, so payload
validation is the boundary that keeps malformed input from becoming a traceback
mid-render. The service must also produce exactly what the engine produces directly:
it exists to cache baseline work, not to alter results.
"""

from __future__ import annotations

import networkx as nx
import pandas as pd
import pytest

from app.scenario_service import _normalize_payload, run_ui_scenario
from scenarios.engine import run_scenario
from scenarios.models import ScenarioType

SNAPSHOT_ID = "2025-12"


class _StubConfig:
    """Minimal stand-in for AppConfig: the service only reads these three fields."""

    def __init__(self, snapshot_id: str = SNAPSHOT_ID) -> None:
        self.snapshot_id = snapshot_id
        self.edges_csv = f"/nonexistent/{snapshot_id}/edges.csv"


def test_airport_payload_is_coerced_to_int() -> None:
    """Streamlit widgets hand back numpy scalars and strings; the engine wants ints."""
    assert _normalize_payload(ScenarioType.AIRPORT_REMOVAL, {"airport_id": "10397"}) == {
        "airport_id": 10397
    }


def test_route_payload_is_coerced_to_int() -> None:
    payload = _normalize_payload(
        ScenarioType.ROUTE_REMOVAL, {"origin_id": "10397", "destination_id": 13930}
    )
    assert payload == {"origin_id": 10397, "destination_id": 13930}


def test_airport_payload_requires_its_field() -> None:
    with pytest.raises(ValueError, match="requires airport_id"):
        _normalize_payload(ScenarioType.AIRPORT_REMOVAL, {})


def test_route_payload_names_every_missing_field() -> None:
    with pytest.raises(ValueError, match="missing required field") as excinfo:
        _normalize_payload(ScenarioType.ROUTE_REMOVAL, {})
    assert "origin_id" in str(excinfo.value)
    assert "destination_id" in str(excinfo.value)


def test_self_loop_route_is_rejected() -> None:
    """A route from an airport to itself is not a route, and the engine has no edge for it."""
    with pytest.raises(ValueError, match="must be different"):
        _normalize_payload(
            ScenarioType.ROUTE_REMOVAL, {"origin_id": 10397, "destination_id": 10397}
        )


def test_non_numeric_input_is_rejected_by_field_name() -> None:
    with pytest.raises(ValueError, match="airport_id must be an integer"):
        _normalize_payload(ScenarioType.AIRPORT_REMOVAL, {"airport_id": "ATL"})


def test_non_mapping_payload_is_rejected() -> None:
    with pytest.raises(TypeError, match="payload must be a dictionary"):
        _normalize_payload(ScenarioType.AIRPORT_REMOVAL, ["airport_id", 1])


def test_ui_scenario_matches_the_engine(monkeypatch, fixture_graph: nx.DiGraph) -> None:
    """The service caches baseline work; it must not change a single score.

    The baseline graph is stubbed so this exercises the service's own path rather than
    artifact loading, which ``test_app_data_loader`` covers.
    """
    import app.scenario_service as service

    monkeypatch.setattr(service, "load_baseline_graph", lambda config=None: fixture_graph)
    config = _StubConfig()

    scenario_row, exposure_df = run_ui_scenario(
        scenario_type="airport_removal", payload={"airport_id": 2}, config=config
    )
    expected_row, expected_rows = run_scenario(
        fixture_graph,
        snapshot_id=SNAPSHOT_ID,
        scenario_type="airport_removal",
        payload={"airport_id": 2},
        created_at=scenario_row["created_at"],
    )

    assert scenario_row == expected_row
    assert exposure_df["airport_id"].tolist() == [row["airport_id"] for row in expected_rows]


def test_exposure_frame_is_ranked(monkeypatch, fixture_graph: nx.DiGraph) -> None:
    """Pages render this frame directly, so ordering is part of the contract."""
    import app.scenario_service as service

    monkeypatch.setattr(service, "load_baseline_graph", lambda config=None: fixture_graph)

    _, exposure_df = run_ui_scenario(
        scenario_type="airport_removal", payload={"airport_id": 2}, config=_StubConfig()
    )
    assert not exposure_df.empty
    assert exposure_df["exposure_rank"].tolist() == sorted(exposure_df["exposure_rank"])
    assert exposure_df["exposure_score"].is_monotonic_decreasing


def test_route_scenario_runs_through_the_service(
    monkeypatch, fixture_graph: nx.DiGraph
) -> None:
    import app.scenario_service as service

    monkeypatch.setattr(service, "load_baseline_graph", lambda config=None: fixture_graph)

    scenario_row, _ = run_ui_scenario(
        scenario_type="route_removal",
        payload={"origin_id": 2, "destination_id": 3},
        config=_StubConfig(),
    )
    assert scenario_row["scenario_type"] == "route_removal"
    assert isinstance(scenario_row["impact_score"], float)


def test_unknown_scenario_type_is_rejected(monkeypatch, fixture_graph: nx.DiGraph) -> None:
    import app.scenario_service as service

    monkeypatch.setattr(service, "load_baseline_graph", lambda config=None: fixture_graph)

    with pytest.raises(ValueError):
        run_ui_scenario(
            scenario_type="airport_upgrade", payload={"airport_id": 2}, config=_StubConfig()
        )


def test_exposure_frame_is_empty_when_nothing_propagates() -> None:
    """An isolated airport spreads no shock, and the empty frame must still be a frame."""
    import app.scenario_service as service

    graph = nx.DiGraph()
    graph.add_edge(1, 2, weight=1.0)
    graph.add_edge(2, 1, weight=1.0)
    graph.add_node(99)  # isolated

    original = service.load_baseline_graph
    service.load_baseline_graph = lambda config=None: graph  # type: ignore[assignment]
    try:
        _, exposure_df = run_ui_scenario(
            scenario_type="airport_removal", payload={"airport_id": 99}, config=_StubConfig()
        )
    finally:
        service.load_baseline_graph = original  # type: ignore[assignment]

    assert isinstance(exposure_df, pd.DataFrame)
    assert exposure_df.empty
